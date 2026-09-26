"""Unit coverage for mixed open/closed active-slip root states."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.contact import slip_root
from solveur.contact.support import _proposed_active
from solveur.core.errors import NumericalConvergenceError


class _FakeOperator:
    """Minimal contact operator for root-state tests, not a structural model."""

    def __init__(self, index: int, context: dict[str, tuple[int, ...]]) -> None:
        self.index = index
        self.context = context
        self.has_friction = True
        self.tolerance = 1.0e-9
        self.tangential_stiffness = 1.0
        self.friction_coefficient = 0.5
        self.tangential_vectors = (
            np.array([1.0, 0.0]),
            np.array([0.0, 1.0]),
        )

    def tangential_displacement(self, displacement: np.ndarray) -> np.ndarray:
        return np.asarray(displacement[:2], dtype=float)

    def gap(self, _displacement: np.ndarray) -> float:
        return 0.0 if self.index in self.context["active"] else 1.0


def _root_fixture(
    monkeypatch,
    proposed_sequence: list[tuple[int, ...]],
    count: int = 2,
    zero_pressure_active: tuple[int, ...] = (),
):
    context: dict[str, tuple[int, ...]] = {"active": ()}
    operators = [_FakeOperator(index, context) for index in range(count)]
    dofs = SimpleNamespace(ndof=2)
    identity = csr_matrix(np.eye(2))
    fake_reduction = SimpleNamespace(matrix=identity, rhs=np.zeros(2))
    monkeypatch.setattr(
        slip_root.ConstraintReduction,
        "from_system",
        staticmethod(lambda *_args, **_kwargs: fake_reduction),
    )

    def solve_active_set(_reduction, _operators, active):
        context["active"] = tuple(active)
        return np.array([1.0, 0.0]), np.zeros(len(active))

    pressure_calls = {"count": 0}

    def pressures_for(active, _multipliers, count):
        pressure_calls["count"] += 1
        return np.array(
            [2.0 if index in active and index not in zero_pressure_active else 0.0 for index in range(count)]
        )

    proposed_calls = {"count": 0}

    def proposed_active(_operators, active, _gaps, _pressures):
        position = proposed_calls["count"]
        proposed_calls["count"] += 1
        if position >= len(proposed_sequence):
            return active
        return proposed_sequence[position]

    def tangential_force(_operators, _forces, size):
        return np.zeros(size)

    return (
        dofs,
        identity,
        operators,
        solve_active_set,
        pressures_for,
        proposed_active,
        tangential_force,
        pressure_calls,
    )


def _solve_fixture(
    monkeypatch,
    proposed_sequence: list[tuple[int, ...]],
    *,
    count: int = 2,
    observed_tangential_states: tuple[str, ...] | None = None,
    zero_pressure_active: tuple[int, ...] = (),
):
    fixture = _root_fixture(
        monkeypatch,
        proposed_sequence,
        count=count,
        zero_pressure_active=zero_pressure_active,
    )
    dofs, stiffness, operators, solve_active_set, pressures_for, proposed_active, tangential_force, _ = fixture
    trace_events: list[tuple[str, dict[str, object]]] = []
    solution = slip_root.solve_active_slip_root(
        dofs,
        stiffness,
        np.zeros(2),
        np.array([], dtype=int),
        operators,
        np.zeros((count, 2)),
        1.0e-10,
        solve_active_set=solve_active_set,
        pressures_for=pressures_for,
        proposed_active=proposed_active,
        tangential_force=tangential_force,
        trace=lambda phase, values: trace_events.append((phase, dict(values))),
        observed_tangential_states=observed_tangential_states,
    )
    return solution, trace_events


def test_mixed_open_contact_is_excluded_from_tangential_root(monkeypatch) -> None:
    """Only the compressed active frictional contact enters the root vector."""
    solution, events = _solve_fixture(monkeypatch, [(0,), (0,), (0,)])

    assert solution.closed_frictional_contacts == (0,)
    assert solution.open_frictional_contacts == (1,)
    assert solution.states == ("slip", "open")
    assert solution.forces.shape == (2, 2)
    assert np.all(solution.forces[1] == 0.0)
    assert np.array_equal(solution.references[1], np.zeros(2))
    subset = next(values for phase, values in events if phase == "active_slip_mixed_subset")
    assert subset["closed_frictional_contacts"] == [0]
    assert subset["open_frictional_contacts"] == [1]
    assert subset["tangential_unknown_dimension"] == 2


def test_post_root_normal_change_restarts_without_committing_trial_reference(monkeypatch) -> None:
    """A changed normal set rejects the trial root and deterministically retries."""
    solution, events = _solve_fixture(monkeypatch, [(0,), (0,), (1,), (1,)])

    assert solution.active == (1,)
    assert solution.states == ("open", "slip")
    assert np.array_equal(solution.references[0], np.zeros(2))
    changed = [values for phase, values in events if phase == "post_root_normal_set_changed"]
    assert len(changed) == 1
    assert changed[0]["convergence_cause"] == "POST_ROOT_NORMAL_SET_CHANGED"
    assert changed[0]["active_contacts_before_root"] == [0]
    assert changed[0]["post_root_normal_active_contacts"] == [1]
    assert changed[0]["next_active_contacts"] == [1]
    assert any(phase == "post_root_normal_set_stable" for phase, _ in events)


def test_stable_post_root_state_is_accepted_with_complementarity(monkeypatch) -> None:
    """A root with an unchanged normal set passes finite/open/complementarity checks."""
    solution, events = _solve_fixture(monkeypatch, [(0,), (0,), (0,)])

    assert solution.active == (0,)
    assert solution.max_complementarity == 0.0
    assert all(np.isfinite(solution.forces.ravel()))
    stable = [values for phase, values in events if phase == "post_root_normal_set_stable"]
    assert len(stable) == 1
    assert stable[0]["convergence_cause"] == "POST_ROOT_NORMAL_SET_STABLE"
    assert stable[0]["tangential_unknown_dimension"] == 2


def test_hybrid_ssk_uses_two_stick_contacts_and_one_slip_unknown(monkeypatch) -> None:
    """The direct SSK classification produces a one-contact slip root."""
    solution, events = _solve_fixture(
        monkeypatch,
        [(0, 1, 2), (0, 1, 2), (0, 1, 2)],
        count=3,
        observed_tangential_states=("stick", "stick", "slip"),
    )

    assert solution.states == ("stick", "stick", "slip")
    assert solution.stick_frictional_contacts == (0, 1)
    assert solution.slip_frictional_contacts == (2,)
    assert np.linalg.norm(solution.forces[0]) <= 1.0
    assert np.linalg.norm(solution.forces[1]) <= 1.0
    assert np.linalg.norm(solution.forces[2]) == pytest.approx(1.0)
    event = next(values for phase, values in events if phase == "active_slip_hybrid_subset")
    assert event["stick_frictional_contacts"] == [0, 1]
    assert event["slip_frictional_contacts"] == [2]
    assert event["tangential_unknown_dimension"] == 2


def test_hybrid_root_uses_consistent_jacobian_and_reuses_stick_matrix(monkeypatch) -> None:
    """The fixed stick block is assembled once and the exact root Jacobian is supplied."""
    matrix_builds = 0
    original_rank_one = slip_root._sparse_rank_one

    def counted_rank_one(vector: np.ndarray, factor: float):
        nonlocal matrix_builds
        matrix_builds += 1
        return original_rank_one(vector, factor)

    monkeypatch.setattr(slip_root, "_sparse_rank_one", counted_rank_one)

    def root_with_jacobian_check(function, initial, **kwargs):
        jacobian = kwargs.get("jac")
        assert callable(jacobian)
        point = np.asarray(initial, dtype=float)
        analytic = np.asarray(jacobian(point), dtype=float)
        finite_difference = np.empty_like(analytic)
        step = 1.0e-6
        for column in range(point.size):
            direction = np.zeros_like(point)
            direction[column] = step
            finite_difference[:, column] = (
                function(point + direction) - function(point - direction)
            ) / (2.0 * step)
        np.testing.assert_allclose(analytic, finite_difference, rtol=1.0e-8, atol=1.0e-9)
        assert matrix_builds == 4
        return SimpleNamespace(success=True, message="synthetic Jacobian check", x=point, nfev=1)

    monkeypatch.setattr(slip_root, "root", root_with_jacobian_check)
    solution, events = _solve_fixture(
        monkeypatch,
        [(0, 1, 2)],
        count=3,
        observed_tangential_states=("stick", "stick", "slip"),
    )

    assert solution.states == ("stick", "stick", "slip")
    assert matrix_builds == 4
    assert any(phase == "post_root_normal_set_stable" for phase, _ in events)


def test_active_slip_jacobian_matches_coupled_displacement_and_pressure_response(monkeypatch) -> None:
    """The analytic Jacobian includes force-driven displacement and pressure changes."""
    operator = _FakeOperator(0, {"active": (0,)})
    dofs = SimpleNamespace(ndof=2)
    stiffness = csr_matrix(np.array([[4.0, 0.5], [0.5, 3.0]], dtype=float))
    loads = np.array([10.0, 4.0], dtype=float)

    def reduction_from_system(_dofs, matrix, rhs, *_args):
        return SimpleNamespace(matrix=matrix, rhs=np.asarray(rhs, dtype=float).copy())

    monkeypatch.setattr(
        slip_root.ConstraintReduction,
        "from_system",
        staticmethod(reduction_from_system),
    )

    def solve_active_set(reduction, _operators, active):
        displacement = np.linalg.solve(reduction.matrix.toarray(), reduction.rhs)
        multipliers = np.full(len(active), 2.0 + 0.2 * displacement[0], dtype=float)
        return displacement, multipliers

    def pressures_for(active, multipliers, count):
        pressures = np.zeros(count, dtype=float)
        pressures[list(active)] = multipliers
        return pressures

    real_root = slip_root.root
    jacobian_comparison: dict[str, float] = {}

    def root_with_jacobian_check(function, initial, **kwargs):
        jacobian = kwargs.get("jac")
        assert callable(jacobian)
        point = np.asarray(initial, dtype=float)
        analytic = np.asarray(jacobian(point), dtype=float)
        finite_difference = np.empty_like(analytic)
        step = 1.0e-6
        for column in range(point.size):
            direction = np.zeros_like(point)
            direction[column] = step
            finite_difference[:, column] = (
                function(point + direction) - function(point - direction)
            ) / (2.0 * step)
        jacobian_comparison["max_abs_error"] = float(np.max(np.abs(analytic - finite_difference)))
        np.testing.assert_allclose(analytic, finite_difference, rtol=2.0e-7, atol=2.0e-8)
        return real_root(function, initial, **kwargs)

    monkeypatch.setattr(slip_root, "root", root_with_jacobian_check)
    solution = slip_root._solve_active_slip_on_active_set(
        dofs,
        stiffness,
        loads,
        np.array([], dtype=int),
        [operator],
        (0,),
        np.zeros((1, 2), dtype=float),
        1.0e-10,
        solve_active_set=solve_active_set,
        pressures_for=pressures_for,
        tangential_force=lambda _operators, _forces, size: np.zeros(size, dtype=float),
        trace=None,
        consistency_iteration=1,
        observed_tangential_states=("slip",),
    )

    assert solution.states == ("slip",)
    assert solution.history[0]["max_scaled_contact_residual"] <= 1.0e-10
    assert jacobian_comparison["max_abs_error"] < 2.0e-8


def test_zero_pressure_normal_active_contact_is_tangentially_open(monkeypatch) -> None:
    """A weakly active normal constraint at zero pressure must not inherit stale slip mode."""
    solution, events = _solve_fixture(
        monkeypatch,
        [(0, 1), (0, 1), (0, 1)],
        count=2,
        observed_tangential_states=("slip", "slip"),
        zero_pressure_active=(1,),
    )

    assert solution.active == (0, 1)
    assert solution.closed_frictional_contacts == (0,)
    assert solution.open_frictional_contacts == (1,)
    assert solution.states == ("slip", "open")
    assert np.all(solution.forces[1] == 0.0)
    assert np.array_equal(solution.references[1], np.zeros(2))
    subset = next(values for phase, values in events if phase == "active_slip_hybrid_subset")
    assert subset["closed_frictional_contacts"] == [0]
    assert subset["open_frictional_contacts"] == [1]


def test_post_root_positive_pressure_reclassifies_open_contact_and_retries(monkeypatch) -> None:
    """A contact compressed by the root response joins the next tangential solve."""
    operators = [_FakeOperator(index, {"active": (0, 1)}) for index in range(2)]
    reduction = SimpleNamespace(matrix=csr_matrix(np.eye(2)), rhs=np.zeros(2))

    def solution(states: tuple[str, str], pressures: tuple[float, float], forces: tuple[tuple[float, float], ...]):
        return slip_root.ActiveSlipSolution(
            displacement=np.array([1.0, 0.0]),
            multipliers=np.zeros(2),
            reduction=reduction,
            gaps=np.zeros(2),
            pressures=np.asarray(pressures, dtype=float),
            active=(0, 1),
            states=states,
            forces=np.asarray(forces, dtype=float),
            tangential_displacements=np.array([[1.0, 0.0], [1.0, 0.0]]),
            references=np.zeros((2, 2)),
            history=[{}],
            closed_frictional_contacts=tuple(i for i, p in enumerate(pressures) if p > 1.0e-9),
            open_frictional_contacts=tuple(i for i, p in enumerate(pressures) if p <= 1.0e-9),
            stick_frictional_contacts=(),
            slip_frictional_contacts=tuple(i for i, state in enumerate(states) if state == "slip"),
            max_complementarity=0.0,
        )

    first = solution(("slip", "open"), (2.0, 0.2), ((1.0, 0.0), (0.0, 0.0)))
    second = solution(("slip", "slip"), (2.0, 0.2), ((1.0, 0.0), (0.1, 0.0)))
    calls: list[dict[str, object]] = []

    def solve_one_iteration(*_args, **kwargs):
        calls.append(kwargs)
        return first if len(calls) == 1 else second

    monkeypatch.setattr(slip_root, "_normal_active_set", lambda *_args, **_kwargs: (0, 1))
    monkeypatch.setattr(slip_root, "_solve_active_slip_on_active_set", solve_one_iteration)
    trace_events: list[tuple[str, dict[str, object]]] = []

    result = slip_root.solve_active_slip_root(
        SimpleNamespace(ndof=2),
        csr_matrix(np.eye(2)),
        np.zeros(2),
        np.array([], dtype=int),
        operators,
        np.zeros((2, 2)),
        1.0e-10,
        solve_active_set=lambda *_args: (np.array([1.0, 0.0]), np.zeros(2)),
        pressures_for=lambda *_args: np.array([2.0, 0.0]),
        proposed_active=lambda _ops, active, _gaps, _pressures: active,
        tangential_force=lambda _ops, _forces, size: np.zeros(size),
        trace=lambda phase, values: trace_events.append((phase, dict(values))),
        observed_tangential_states=("slip", "slip"),
    )

    assert result is second
    assert len(calls) == 2
    assert calls[1]["observed_tangential_states"] == ("slip", "slip")
    assert calls[1]["forced_closed_frictional"] == frozenset({0, 1})
    assert calls[1]["initial_solution"] is first
    changed = [values for phase, values in trace_events if phase == "post_root_tangential_state_changed"]
    assert len(changed) == 1
    assert changed[0]["changed_contacts"] == [
        {
            "contact": 1,
            "root_state": "open",
            "post_root_state": "slip",
            "normal_pressure": 0.2,
            "gap": 0.0,
            "tangential_force": [0.0, 0.0],
            "reference": [0.0, 0.0],
        }
    ]


def test_coupled_projection_treats_zero_pressure_active_contact_as_open(monkeypatch) -> None:
    """Zero-capacity normal-active nodes do not fail tangential validation."""
    active = (0, 1)
    fixture = _root_fixture(
        monkeypatch,
        [active, active],
        count=2,
        zero_pressure_active=(1,),
    )
    dofs, stiffness, operators, solve_active_set, pressures_for, proposed_active, tangential_force, _ = fixture

    solution = slip_root.solve_coupled_contact_projection(
        dofs,
        stiffness,
        np.zeros(2),
        np.array([], dtype=int),
        operators,
        np.zeros((2, 2)),
        1.0e-10,
        solve_active_set=solve_active_set,
        pressures_for=pressures_for,
        proposed_active=proposed_active,
        tangential_force=tangential_force,
    )

    assert solution.active == active
    assert solution.states == ("stick", "open")
    assert solution.closed_frictional_contacts == (0,)
    assert solution.open_frictional_contacts == (1,)
    assert np.all(solution.forces[1] == 0.0)
    assert np.array_equal(solution.references[1], np.zeros(2))


def test_coupled_projection_tries_fifteen_contact_seed_without_enumeration(monkeypatch) -> None:
    """A valid M3-sized seed is solved once without enumerating 2^25 sets."""
    active_seed = tuple(range(15))
    fixture = _root_fixture(monkeypatch, [active_seed, active_seed], count=25)
    dofs, stiffness, operators, solve_active_set, pressures_for, proposed_active, tangential_force, _ = fixture
    events: list[tuple[str, dict[str, object]]] = []

    solution = slip_root.solve_coupled_contact_projection(
        dofs,
        stiffness,
        np.zeros(2),
        np.array([], dtype=int),
        operators,
        np.zeros((25, 2)),
        1.0e-10,
        solve_active_set=solve_active_set,
        pressures_for=pressures_for,
        proposed_active=proposed_active,
        tangential_force=tangential_force,
        trace=lambda phase, values: events.append((phase, dict(values))),
    )

    assert solution.active == active_seed
    assert solution.states == tuple("stick" if index in active_seed else "open" for index in range(25))
    assert solution.history[-1]["tangential_unknown_dimension"] == 30
    force_residual = solution.history[-1]["tangential_force_residual"]
    assert isinstance(force_residual, (int, float))
    assert force_residual <= 1.0e-10
    assert np.all(solution.forces[[index for index in range(25) if index not in active_seed]] == 0.0)
    accepted = [values for phase, values in events if phase == "coupled_contact_candidate_accepted"]
    assert len(accepted) == 1
    assert accepted[0]["candidate_index"] == 1
    assert accepted[0]["candidate_count"] == 2**25


def test_coupled_projection_refines_one_contact_hidden_by_global_residual(monkeypatch) -> None:
    """A successful global root status cannot mask one failed local Coulomb equation."""
    count = 20
    active = tuple(range(count))
    context: dict[str, tuple[int, ...]] = {"active": active}
    trial = np.asarray([108.3335661465846, 56.840914194715005], dtype=float)
    pressure = 39.365840286680516
    friction_limit = 0.30 * pressure
    local_error = 2.0834372780912926e-8
    operators = [_FakeOperator(index, context) for index in range(count)]
    for operator in operators:
        operator.friction_coefficient = 0.30
        operator.tangential_displacement = lambda _displacement, value=trial: value.copy()

    dofs = SimpleNamespace(ndof=2)
    stiffness = csr_matrix(np.eye(2))
    displacement = trial.copy()

    monkeypatch.setattr(
        slip_root.ConstraintReduction,
        "from_system",
        staticmethod(lambda *_args, **_kwargs: SimpleNamespace(matrix=stiffness, rhs=np.zeros(2))),
    )
    monkeypatch.setattr(slip_root, "_normal_active_set", lambda *_args, **_kwargs: active)

    def solve_active_set(_reduction, _operators, active_set):
        context["active"] = tuple(active_set)
        return displacement.copy(), np.full(len(active_set), pressure, dtype=float)

    def pressures_for(active_set, multipliers, size):
        values = np.zeros(size, dtype=float)
        values[list(active_set)] = multipliers
        return values

    def root_with_one_bad_local_equation(function, initial, **_kwargs):
        candidate = np.asarray(initial, dtype=float).copy()
        candidate[0] += local_error
        scaled = np.asarray(function(candidate), dtype=float).reshape((count, 2))
        per_contact = np.linalg.norm(scaled, axis=1)
        assert np.max(per_contact) == pytest.approx(local_error / friction_limit)
        # This is the old aggregate acceptance condition: it passes despite the
        # local Coulomb residual exceeding tolerance.
        assert local_error <= 1.0e-9 * np.linalg.norm(candidate)
        return SimpleNamespace(success=True, message="xtol satisfied", x=candidate, nfev=1)

    refinement: dict[str, float] = {}

    def semismooth_refinement(function, initial, tolerance, *, convergence_measure, **_kwargs):
        candidate = np.asarray(initial, dtype=float)
        refinement["initial_local_measure"] = convergence_measure(candidate, function(candidate))
        assert refinement["initial_local_measure"] > tolerance
        corrected = candidate.copy()
        corrected[0] -= local_error
        refinement["final_local_measure"] = convergence_measure(corrected, function(corrected))
        return corrected, 2, refinement["final_local_measure"]

    monkeypatch.setattr(slip_root, "root", root_with_one_bad_local_equation)
    monkeypatch.setattr(slip_root, "_semismooth_newton_solution", semismooth_refinement)

    solution = slip_root._solve_coupled_projection_on_active_set(
        dofs,
        stiffness,
        np.zeros(2),
        np.array([], dtype=int),
        operators,
        active,
        np.zeros((count, 2)),
        1.0e-9,
        solve_active_set=solve_active_set,
        pressures_for=pressures_for,
        tangential_force=lambda _operators, _forces, size: np.zeros(size, dtype=float),
    )

    assert refinement["initial_local_measure"] == pytest.approx(local_error / friction_limit)
    assert refinement["final_local_measure"] <= 1.0e-9
    assert solution.history[-1]["maximum_scaled_contact_residual"] <= 1.0e-9
    assert solution.history[-1]["tangential_force_residual"] < local_error


def test_coupled_projection_updates_normal_set_after_tangential_coupling(monkeypatch) -> None:
    """A penetration created by tangential coupling adds that normal constraint before acceptance."""
    count = 25
    seed_active = (0,)
    context: dict[str, tuple[int, ...]] = {"active": seed_active}
    operators = [_FakeOperator(index, context) for index in range(count)]
    dofs = SimpleNamespace(ndof=2)
    stiffness = csr_matrix(np.eye(2))
    calls: list[tuple[int, ...]] = []

    def synthetic_solution(active: tuple[int, ...]):
        calls.append(active)
        gaps = np.ones(count, dtype=float)
        gaps[list(active)] = 0.0
        if 1 not in active:
            # The normal-only seed is not admissible after coupled tangential forces.
            gaps[1] = -3.8220362995274753e-4
        pressures = np.zeros(count, dtype=float)
        pressures[list(active)] = 2.0
        forces = np.zeros((count, 2), dtype=float)
        states = tuple("stick" if index in active else "open" for index in range(count))
        return slip_root.ActiveSlipSolution(
            displacement=np.zeros(2),
            multipliers=np.zeros(len(active)),
            reduction=SimpleNamespace(),
            gaps=gaps,
            pressures=pressures,
            active=active,
            states=states,
            forces=forces,
            tangential_displacements=np.zeros((count, 2)),
            references=np.zeros((count, 2)),
            history=[],
            closed_frictional_contacts=active,
            open_frictional_contacts=tuple(index for index in range(count) if index not in active),
            stick_frictional_contacts=active,
            slip_frictional_contacts=(),
            max_complementarity=0.0,
        )

    monkeypatch.setattr(slip_root, "_normal_active_set", lambda *_args, **_kwargs: seed_active)

    def solve_coupled_candidate(*args, **_kwargs):
        return synthetic_solution(tuple(args[5]))

    monkeypatch.setattr(slip_root, "_solve_coupled_projection_on_active_set", solve_coupled_candidate)
    events: list[tuple[str, dict[str, object]]] = []

    solution = slip_root.solve_coupled_contact_projection(
        dofs,
        stiffness,
        np.zeros(2),
        np.array([], dtype=int),
        operators,
        np.zeros((count, 2)),
        1.0e-9,
        solve_active_set=lambda *_args: (np.zeros(2), np.zeros(0)),
        pressures_for=lambda *_args: np.zeros(count),
        proposed_active=_proposed_active,
        tangential_force=lambda _operators, _forces, size: np.zeros(size),
        trace=lambda phase, values: events.append((phase, dict(values))),
    )

    assert calls == [(0,), (0, 1)]
    assert solution.active == (0, 1)
    transition = next(values for phase, values in events if phase == "coupled_normal_active_set_transition")
    assert transition["added_contacts"] == [1]
    assert transition["removed_contacts"] == []
    accepted = [values for phase, values in events if phase == "coupled_contact_candidate_accepted"]
    assert len(accepted) == 1
    assert accepted[0]["candidate_index"] == 1
    assert accepted[0]["candidate_count"] == 2**count
    assert accepted[0]["normal_active_set_iterations"] == 2


def test_coupled_projection_fails_closed_on_normal_set_cycle_without_enumeration(monkeypatch) -> None:
    """A repeated normal set remains fail-closed and does not open exponential search."""
    count = 25
    seed_active = (0,)
    operators = [_FakeOperator(index, {"active": seed_active}) for index in range(count)]
    dofs = SimpleNamespace(ndof=2)
    stiffness = csr_matrix(np.eye(2))
    calls = 0

    def synthetic_solution(active: tuple[int, ...]):
        nonlocal calls
        calls += 1
        gaps = np.ones(count, dtype=float)
        pressures = np.zeros(count, dtype=float)
        forces = np.zeros((count, 2), dtype=float)
        gaps[list(active)] = 0.0
        pressures[list(active)] = 2.0
        if calls == 1:
            gaps[1] = -1.0e-3
        else:
            # The newly active contact is tensile, proposing the previously visited seed.
            pressures[1] = -2.0
        states = tuple("stick" if index in active else "open" for index in range(count))
        return slip_root.ActiveSlipSolution(
            displacement=np.zeros(2),
            multipliers=np.zeros(len(active)),
            reduction=SimpleNamespace(),
            gaps=gaps,
            pressures=pressures,
            active=active,
            states=states,
            forces=forces,
            tangential_displacements=np.zeros((count, 2)),
            references=np.zeros((count, 2)),
            history=[],
            closed_frictional_contacts=active,
            open_frictional_contacts=tuple(index for index in range(count) if index not in active),
            stick_frictional_contacts=active,
            slip_frictional_contacts=(),
            max_complementarity=0.0,
        )

    monkeypatch.setattr(slip_root, "_normal_active_set", lambda *_args, **_kwargs: seed_active)
    monkeypatch.setattr(
        slip_root,
        "_solve_coupled_projection_on_active_set",
        lambda *_args, **_kwargs: synthetic_solution(_args[5]),
    )

    with pytest.raises(NumericalConvergenceError, match="exceeds its deterministic contact-count limit") as captured:
        slip_root.solve_coupled_contact_projection(
            dofs,
            stiffness,
            np.zeros(2),
            np.array([], dtype=int),
            operators,
            np.zeros((count, 2)),
            1.0e-9,
            solve_active_set=lambda *_args: (np.zeros(2), np.zeros(0)),
            pressures_for=lambda *_args: np.zeros(count),
            proposed_active=_proposed_active,
            tangential_force=lambda _operators, _forces, size: np.zeros(size),
        )

    diagnostics = captured.value.diagnostics
    assert diagnostics is not None
    rejection = diagnostics["seed_candidate_rejection"]
    assert rejection["diagnostics"]["cause"] == "COUPLED_NORMAL_ACTIVE_SET_CYCLE"
    assert len(rejection["normal_active_set_history"]) == 2
    assert calls == 2
    assert diagnostics["attempted_candidate_count"] == 1


def test_coupled_projection_fails_closed_after_rejected_large_seed(monkeypatch) -> None:
    """A rejected seed above the search cap must not trigger exponential enumeration."""
    active_seed = (3, 7, 11)
    fixture = _root_fixture(monkeypatch, [active_seed, active_seed], count=12)
    dofs, stiffness, operators, solve_active_set, pressures_for, proposed_active, tangential_force, _ = fixture
    attempted: list[tuple[int, ...]] = []

    def reject_seed(*args, **_kwargs):
        active = tuple(args[5])
        attempted.append(active)
        raise NumericalConvergenceError(
            "synthetic inadmissible seed",
            diagnostics={"cause": "SYNTHETIC_SEED_REJECTED"},
        )

    monkeypatch.setattr(slip_root, "_solve_coupled_projection_on_active_set", reject_seed)

    with pytest.raises(NumericalConvergenceError, match="exceeds its deterministic contact-count limit") as captured:
        slip_root.solve_coupled_contact_projection(
            dofs,
            stiffness,
            np.zeros(2),
            np.array([], dtype=int),
            operators,
            np.zeros((12, 2)),
            1.0e-10,
            solve_active_set=solve_active_set,
            pressures_for=pressures_for,
            proposed_active=proposed_active,
            tangential_force=tangential_force,
        )

    assert attempted == [active_seed]
    assert captured.value.diagnostics is not None
    assert captured.value.diagnostics["cause"] == "COUPLED_SEARCH_CONTACT_LIMIT_EXCEEDED"
    assert captured.value.diagnostics["attempted_candidate_count"] == 1
    assert captured.value.diagnostics["seed_candidate_rejection"]["active_contacts"] == [3, 7, 11]


def test_per_contact_residual_gate_catches_global_norm_masking_one_contact() -> None:
    """Many-contact global scaling must not hide one locally inadmissible slip equation."""
    tolerance = 1.0e-9
    count = 25
    operators = [_FakeOperator(index, {"active": tuple(range(count))}) for index in range(count)]
    pressures = np.full(count, 34.0, dtype=float)  # mu * p = 17 force units per contact
    force_unknowns = np.full((count, 2), 5.0, dtype=float)
    residual = np.zeros((count, 2), dtype=float)
    residual[7, 0] = 2.0e-8

    # The historical aggregate criterion would accept this residual because
    # ||x|| makes its global allowance larger than the local Coulomb allowance.
    assert np.linalg.norm(residual) <= tolerance * max(np.linalg.norm(force_unknowns), 1.0)

    _, details, maximum_scaled = slip_root._scale_contact_residuals(
        residual.ravel(), tuple(range(count)), operators, pressures
    )

    assert maximum_scaled == pytest.approx(2.0e-8 / 17.0)
    assert maximum_scaled > tolerance
    assert details[7]["contact"] == 7
    assert details[7]["scaled_residual_norm"] == pytest.approx(maximum_scaled)


def test_semismooth_solver_does_not_stop_on_only_global_relative_residual() -> None:
    """The safeguarded root refinement honors the supplied local gate measure."""
    tolerance = 1.0e-9
    target = np.asarray([100.0 + 2.0e-8], dtype=float)
    initial = np.asarray([100.0], dtype=float)

    solution, evaluations, raw_residual_norm = slip_root._semismooth_newton_solution(
        lambda value: value - target,
        initial,
        tolerance,
        jacobian=lambda _value: np.eye(1),
        convergence_measure=lambda _value, residual: float(np.linalg.norm(residual)),
    )

    assert evaluations > 1
    assert solution == pytest.approx(target, abs=1.0e-12)
    assert raw_residual_norm <= tolerance


def test_scaled_contact_residual_jacobian_includes_pressure_dependent_scale() -> None:
    """The trust-region Jacobian differentiates both force residual and its scale."""
    operator = SimpleNamespace(friction_coefficient=0.5)
    physical_jacobian = np.asarray([[2.0, -0.25], [0.5, 3.0]])
    physical_residual = np.asarray([0.2, -0.1])
    pressure = 4.0
    pressure_sensitivity = np.asarray([[0.3, -0.2]])

    jacobian = slip_root._scale_contact_residual_jacobian(
        physical_jacobian,
        physical_residual,
        (0,),
        [operator],
        np.asarray([pressure]),
        pressure_sensitivity,
    )

    def scaled_at(vector: np.ndarray) -> np.ndarray:
        raw = physical_residual + physical_jacobian @ vector
        current_pressure = pressure + pressure_sensitivity[0] @ vector
        scale = max(operator.friction_coefficient * current_pressure, 1.0)
        return raw / scale

    step = 1.0e-6
    finite_difference = np.column_stack(
        tuple(
            (scaled_at(np.eye(2)[column] * step) - scaled_at(-np.eye(2)[column] * step)) / (2.0 * step)
            for column in range(2)
        )
    )
    assert jacobian == pytest.approx(finite_difference, rel=1.0e-8, abs=1.0e-10)


def test_failed_semismooth_attempt_preserves_its_best_finite_seed() -> None:
    """A later fallback starts from the best admissible iterate already found."""
    def residual(vector: np.ndarray) -> np.ndarray:
        return np.asarray(vector, dtype=float) - 1.0

    def measure(_vector: np.ndarray, values: np.ndarray) -> float:
        return float(np.linalg.norm(values))

    improved = slip_root._best_residual_seed(
        np.asarray([1.5]),
        {"last_candidate": [1.1]},
        residual,
        measure,
    )
    regressed = slip_root._best_residual_seed(
        np.asarray([1.1]),
        {"last_candidate": [1.5]},
        residual,
        measure,
    )

    assert improved == pytest.approx([1.1])
    assert regressed == pytest.approx([1.1])


def test_globalized_solution_polishes_xtol_candidate_against_physical_gate(monkeypatch) -> None:
    """An optimizer stop above the frozen residual gate is refined, never accepted as-is."""
    target = np.asarray([1.0])
    tolerance = 1.0e-9
    optimizer_candidate = np.asarray([1.0 - 1.5e-9])
    observed: dict[str, object] = {}

    def stopped_least_squares(function, initial, **kwargs):
        observed["initial"] = np.asarray(initial).copy()
        observed["jacobian"] = kwargs.get("jac")
        observed["xtol"] = kwargs.get("xtol")
        observed["ftol"] = kwargs.get("ftol")
        observed["gtol"] = kwargs.get("gtol")
        assert function(optimizer_candidate)[0] == pytest.approx(-1.5e-9)
        return SimpleNamespace(
            success=True,
            message="`xtol` termination condition is satisfied.",
            status=3,
            x=optimizer_candidate.copy(),
            nfev=1,
            cost=1.125e-18,
            optimality=1.5e-9,
            grad=np.asarray([1.5e-9]),
        )

    monkeypatch.setattr(slip_root, "least_squares", stopped_least_squares)
    solution, evaluations, residual_norm = slip_root._globalized_slip_solution(
        lambda vector: vector - target,
        optimizer_candidate,
        tolerance,
        objective_jacobian=lambda _vector: np.eye(1),
        refinement_jacobian=lambda _vector: np.eye(1),
        convergence_measure=lambda _vector, values: float(np.linalg.norm(values)),
    )

    assert observed["jacobian"] is not None
    assert 0.0 < observed["xtol"] < tolerance
    assert observed["ftol"] == observed["xtol"]
    assert observed["gtol"] == observed["xtol"]
    assert solution == pytest.approx(target, abs=1.0e-15)
    assert evaluations > 1
    assert residual_norm <= tolerance


def test_globalized_solution_keeps_xtol_candidate_fail_closed_if_polish_stalls(monkeypatch) -> None:
    """An unsuccessful local correction remains a failure with residual evidence."""
    tolerance = 1.0e-9
    candidate = np.asarray([2.0])

    monkeypatch.setattr(
        slip_root,
        "least_squares",
        lambda *_args, **_kwargs: SimpleNamespace(
            success=True,
            message="`xtol` termination condition is satisfied.",
            status=3,
            x=candidate.copy(),
            nfev=1,
        ),
    )
    with pytest.raises(NumericalConvergenceError) as captured:
        slip_root._globalized_slip_solution(
            lambda _vector: np.asarray([2.0e-9]),
            candidate,
            tolerance,
            objective_jacobian=lambda _vector: np.eye(1),
            refinement_jacobian=lambda _vector: np.eye(1),
            convergence_measure=lambda _vector, values: float(np.linalg.norm(values)),
            diagnostic_context=lambda _vector: {"worst_contact": 3},
        )

    diagnostics = captured.value.diagnostics or {}
    assert diagnostics["cause"] == "GLOBALIZED_SLIP_RESIDUAL_NOT_CONVERGED"
    assert diagnostics["scaled_contact_residual"] == pytest.approx(2.0e-9)
    assert diagnostics["optimizer_message"] == "`xtol` termination condition is satisfied."
    assert diagnostics["optimizer_xtol"] < tolerance
    assert diagnostics["optimizer_cost"] is None
    assert diagnostics["optimizer_optimality"] is None
    assert diagnostics["optimizer_gradient_inf_norm"] is None
    assert diagnostics["refinement_error"] is not None
    assert diagnostics["worst_contact"] == 3


@pytest.mark.parametrize("tangential_stiffness", [2.0, 2.5], ids=["stick", "slip"])
def test_coupled_projection_jacobian_matches_frozen_branch_finite_difference(
    monkeypatch, tangential_stiffness: float
) -> None:
    """The analytic coupled Jacobian matches the stick and slip residual branches."""
    context: dict[str, tuple[int, ...]] = {"active": (0,)}
    operator = _FakeOperator(0, context)
    operator.tangential_stiffness = tangential_stiffness
    dofs = SimpleNamespace(ndof=2)
    stiffness = csr_matrix(np.eye(2))
    monkeypatch.setattr(
        slip_root.ConstraintReduction,
        "from_system",
        staticmethod(lambda _dofs, _stiffness, rhs, *_args: SimpleNamespace(rhs=np.asarray(rhs, dtype=float))),
    )

    def solve_active_set(reduction, _operators, _active):
        rhs = np.asarray(reduction.rhs, dtype=float)
        displacement = np.asarray([0.15, 0.05]) + np.asarray([0.4 * rhs[0], 0.3 * rhs[1]])
        multiplier = np.asarray([4.0 + 0.2 * rhs[0] - 0.1 * rhs[1]])
        return displacement, multiplier

    def pressures_for(_active, multipliers, count):
        values = np.zeros(count, dtype=float)
        values[0] = multipliers[0]
        return values

    def tangential_force(_operators, forces, _size):
        return np.asarray(forces[0], dtype=float)

    class StopAfterJacobianCheck(Exception):
        pass

    def inspect_root(function, initial, *, jac, **_kwargs):
        vector = np.asarray(initial, dtype=float)
        analytic = jac(vector)
        step = 1.0e-6
        finite_difference = np.column_stack(
            tuple(
                (function(vector + np.eye(2)[column] * step) - function(vector - np.eye(2)[column] * step))
                / (2.0 * step)
                for column in range(2)
            )
        )
        assert analytic == pytest.approx(finite_difference, rel=2.0e-6, abs=2.0e-8)
        raise StopAfterJacobianCheck

    monkeypatch.setattr(slip_root, "root", inspect_root)
    with pytest.raises(StopAfterJacobianCheck):
        slip_root._solve_coupled_projection_on_active_set(
            dofs,
            stiffness,
            np.asarray([2.0, 0.3]),
            np.array([], dtype=int),
            [operator],
            (0,),
            np.zeros((1, 2)),
            1.0e-9,
            solve_active_set=solve_active_set,
            pressures_for=pressures_for,
            tangential_force=tangential_force,
        )


def test_hybrid_root_rejects_invalid_observed_state_classification(monkeypatch) -> None:
    """A hybrid root cannot silently reinterpret an active contact state."""
    with pytest.raises(NumericalConvergenceError, match="invalid direct tangential-state"):
        _solve_fixture(
            monkeypatch,
            [(0, 1, 2), (0, 1, 2)],
            count=3,
            observed_tangential_states=("stick", "open", "slip"),
        )


def test_failed_hybrid_root_does_not_commit_references(monkeypatch) -> None:
    """A failed hybrid candidate leaves the caller's committed references intact."""
    fixture = _root_fixture(monkeypatch, [(0, 1, 2), (0, 1, 2)], count=3)
    dofs, stiffness, operators, solve_active_set, pressures_for, proposed_active, tangential_force, _ = fixture
    references: np.ndarray = np.arange(6.0, dtype=float).reshape(3, 2)
    original = references.copy()

    class FailedRoot:
        success = False
        nfev = 1
        x = np.array([1.0, 0.0])

    monkeypatch.setattr(slip_root, "root", lambda *_args, **_kwargs: FailedRoot())
    monkeypatch.setattr(
        slip_root,
        "_semismooth_newton_solution",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(NumericalConvergenceError("forced hybrid failure")),
    )
    monkeypatch.setattr(
        slip_root,
        "_globalized_slip_solution",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(NumericalConvergenceError("forced hybrid failure")),
    )

    with pytest.raises(NumericalConvergenceError, match="forced hybrid failure"):
        slip_root.solve_active_slip_root(
            dofs,
            stiffness,
            np.zeros(2),
            np.array([], dtype=int),
            operators,
            references,
            1.0e-10,
            solve_active_set=solve_active_set,
            pressures_for=pressures_for,
            proposed_active=proposed_active,
            tangential_force=tangential_force,
            observed_tangential_states=("stick", "stick", "slip"),
        )
    assert np.array_equal(references, original)
