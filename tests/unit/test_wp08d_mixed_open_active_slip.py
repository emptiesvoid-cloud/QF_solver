"""Unit coverage for mixed open/closed active-slip root states."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.contact import slip_root
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


def _root_fixture(monkeypatch, proposed_sequence: list[tuple[int, ...]], count: int = 2):
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
        return np.array([2.0 if index in active else 0.0 for index in range(count)])

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
):
    fixture = _root_fixture(monkeypatch, proposed_sequence, count=count)
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
    references = np.arange(6.0, dtype=float).reshape(3, 2)
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
