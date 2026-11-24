"""WP08-C local tangent, transition, energy and dissipation checks."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.contact.entities import FrictionlessContact
from solveur.contact.support import (
    _ContactOperator,
    _coulomb_is_stick,
    _dissipation_increment,
    _friction_system,
    _friction_update,
    _operator,
)
from solveur.contact.slip_root import _post_root_tangential_modes
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader


KT = 10000.0
PRESSURE = 100.0
FRICTION = 0.5
COULOMB_LIMIT = FRICTION * PRESSURE
ABSOLUTE_FLOOR = 1.0e-14
DISSIPATION_FLOOR = 1.0e-14


def _model(
    *,
    horizontal_load: float,
    vertical_load: float,
    history: list[list[float]] | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "analysis": {
            "type": "linear_static",
            "method": "direct",
            "contact_max_iterations": 16,
            "contact_friction_tolerance": 1.0e-11,
        },
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.25, 0.25, 0.1]],
        "elements": [],
        "materials": {},
        "fixed_dofs": [
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 1, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UY"]},
        ],
        "springs": [{"node_a": 3, "dofs": ["UX", "UZ"], "stiffness": [1000.0, 1000.0]}],
        "loads": [
            {"node": 3, "dof": "UX", "value": horizontal_load},
            {"node": 3, "dof": "UZ", "value": vertical_load},
        ],
        "contacts": [
            {
                "name": "rough_plane",
                "slave_node": 3,
                "master_nodes": [0, 1, 2],
                "friction_coefficient": FRICTION,
                "tangential_stiffness": KT,
            }
        ],
    }
    if history is not None:
        data["analysis"]["contact_load_history"] = history
    return data


def _operator_fixture() -> tuple[FiniteElementModel, DofManager, _ContactOperator]:
    model = JsonModelReader().from_dict(_model(horizontal_load=0.0, vertical_load=-1.0))
    dofs = model.dof_manager()
    operator = _operator(model.contacts[0], np.asarray(model.nodes, dtype=float), dofs)
    return model, dofs, operator


def _global_displacement(dofs: DofManager, size: int, local: np.ndarray) -> np.ndarray:
    displacement: np.ndarray = np.zeros(size, dtype=float)
    displacement[dofs.index(3, "UX")] = float(local[0])
    displacement[dofs.index(3, "UY")] = float(local[1])
    return displacement


def _local_update(
    operator: _ContactOperator,
    dofs: DofManager,
    local: np.ndarray,
    *,
    pressure: float = PRESSURE,
    state: str = "stick",
    references: np.ndarray | None = None,
) -> tuple[tuple[str, ...], np.ndarray, np.ndarray, np.ndarray]:
    displacement = _global_displacement(dofs, operator.vector.size, local)
    if references is None:
        references = np.zeros((1, 2), dtype=float)
    return _friction_update(
        [operator],
        (0,),
        displacement,
        np.array([pressure]),
        references,
        (state,),
    )


def _displacement_for_local_tangent(
    operator: _ContactOperator,
    dofs: DofManager,
    target: np.ndarray,
) -> np.ndarray:
    """Build slave-node translations that produce the requested local slip."""
    indices = [dofs.index(3, name) for name in ("UX", "UY", "UZ")]
    basis = np.asarray([vector[indices] for vector in operator.tangential_vectors], dtype=float)
    local_translation, *_ = np.linalg.lstsq(basis, np.asarray(target, dtype=float), rcond=None)
    displacement = np.zeros(operator.vector.size, dtype=float)
    displacement[indices] = local_translation
    np.testing.assert_allclose(operator.tangential_displacement(displacement), target, rtol=1e-12, atol=1e-14)
    return displacement


def _solve(
    horizontal_load: float,
    vertical_load: float,
    *,
    history: list[list[float]] | None = None,
) -> Any:
    model = JsonModelReader().from_dict(
        _model(horizontal_load=horizontal_load, vertical_load=vertical_load, history=history)
    )
    return LinearStaticSolver().solve(model)


def _relative_error(actual: np.ndarray, expected: np.ndarray) -> float:
    return float(np.linalg.norm(actual - expected)) / max(float(np.linalg.norm(expected)), ABSOLUTE_FLOOR)


def test_stick_analytical_global_tangent_is_exact_and_symmetric() -> None:
    _, _, operator = _operator_fixture()
    size = operator.vector.size
    base = csr_matrix((size, size), dtype=float)
    implemented, effective_loads = _friction_system(
        base,
        np.zeros(size),
        [operator],
        (0,),
        ("stick",),
        np.zeros((1, 2)),
        np.zeros((1, 2)),
    )
    expected = KT * sum(
        (np.outer(vector, vector) for vector in operator.tangential_vectors),
        start=np.zeros((size, size)),
    )
    actual = implemented.toarray()
    difference = actual - expected
    frobenius_error = _relative_error(actual, expected)
    max_column_error = max(
        (
            _relative_error(actual[:, column], expected[:, column])
            for column in range(size)
        ),
        default=0.0,
    )
    symmetry_error = _relative_error(actual - actual.T, np.zeros_like(actual))

    assert np.allclose(effective_loads, 0.0)
    assert frobenius_error <= 1.0e-12
    assert max_column_error <= 1.0e-12
    assert np.linalg.norm(difference) <= ABSOLUTE_FLOOR
    assert symmetry_error == 0.0


def test_stick_force_finite_difference_matches_fixed_branch_for_three_steps() -> None:
    _, dofs, operator = _operator_fixture()
    columns = [dofs.index(3, "UX"), dofs.index(3, "UY"), dofs.index(3, "UZ")]
    analytic = KT * np.vstack(
        (operator.tangential_vectors[0][columns], operator.tangential_vectors[1][columns])
    )
    base: np.ndarray = np.zeros(operator.vector.size, dtype=float)
    base[dofs.index(3, "UX")] = 0.001
    errors: list[tuple[float, float]] = []

    for step in (1.0e-4, 1.0e-6, 1.0e-8):
        finite_difference: np.ndarray = np.zeros((2, len(columns)), dtype=float)
        for position, column in enumerate(columns):
            plus = base.copy()
            minus = base.copy()
            plus[column] += step
            minus[column] -= step
            plus_state, plus_force, _, _ = _friction_update(
                [operator], (0,), plus, np.array([PRESSURE]), np.zeros((1, 2)), ("stick",)
            )
            minus_state, minus_force, _, _ = _friction_update(
                [operator], (0,), minus, np.array([PRESSURE]), np.zeros((1, 2)), ("stick",)
            )
            assert plus_state == minus_state == ("stick",)
            finite_difference[:, position] = (plus_force[0] - minus_force[0]) / (2.0 * step)
        errors.append(
            (
                _relative_error(finite_difference, analytic),
                max(
                    (
                        _relative_error(finite_difference[:, column], analytic[:, column])
                        for column in range(len(columns))
                    ),
                    default=0.0,
                ),
            )
        )

    assert all(frobenius <= 1.0e-7 and maximum <= 5.0e-7 for frobenius, maximum in errors)


def test_open_branch_has_zero_force_and_zero_tangent() -> None:
    _, dofs, operator = _operator_fixture()
    references = np.array([[0.2, -0.1]], dtype=float)
    states, forces, _, next_references = _friction_update(
        [operator], (), np.zeros(operator.vector.size), np.array([0.0]), references, ("slip",)
    )
    tangent, _ = _friction_system(
        csr_matrix((operator.vector.size, operator.vector.size), dtype=float),
        np.zeros(operator.vector.size),
        [operator],
        (),
        ("open",),
        np.zeros((1, 2)),
        references,
    )

    assert states == ("open",)
    np.testing.assert_array_equal(forces[0], np.zeros(2))
    # With no tangential contact force, the spring origin follows the current
    # relative displacement so motion during the open interval is not replayed
    # as elastic shear after reclosure.
    np.testing.assert_array_equal(next_references, np.zeros_like(references))
    assert tangent.nnz == 0
    assert dofs.ndof == operator.vector.size


def test_coulomb_classification_uses_force_tolerance_not_gap_tolerance() -> None:
    _, dofs, operator = _operator_fixture()
    trial_norm = COULOMB_LIMIT + 0.02
    displacement = _displacement_for_local_tangent(
        operator, dofs, np.asarray([trial_norm / KT, 0.0])
    )
    references = np.zeros((1, 2), dtype=float)

    classifications = []
    for gap_tolerance in (1.0e-12, 1.0):
        state, force, _, _ = _friction_update(
            [replace(operator, tolerance=gap_tolerance)],
            (0,),
            displacement,
            np.asarray([PRESSURE]),
            references,
            ("stick",),
            friction_tolerance=1.0e-3,
        )
        classifications.append(state[0])
        assert np.linalg.norm(force[0]) == pytest.approx(trial_norm)

    assert classifications == ["stick", "stick"]


def test_coulomb_force_tolerance_is_relative_and_preserves_slip_hysteresis() -> None:
    _, dofs, operator = _operator_fixture()
    references = np.zeros((1, 2), dtype=float)

    def classify(trial_norm: float, *, tolerance: float, prior: str = "stick") -> str:
        displacement = _displacement_for_local_tangent(
            operator, dofs, np.asarray([trial_norm / KT, 0.0])
        )
        state, _, _, _ = _friction_update(
            [operator],
            (0,),
            displacement,
            np.asarray([PRESSURE]),
            references,
            (prior,),
            friction_tolerance=tolerance,
        )
        return state[0]

    assert classify(COULOMB_LIMIT + 0.02, tolerance=1.0e-3) == "stick"
    assert classify(COULOMB_LIMIT + 0.02, tolerance=1.0e-4) == "slip"
    assert classify(COULOMB_LIMIT - 0.02, tolerance=1.0e-3, prior="slip") == "slip"
    assert classify(COULOMB_LIMIT - 0.10, tolerance=1.0e-3, prior="slip") == "stick"


def test_post_root_coulomb_classification_uses_the_same_force_band() -> None:
    _, _, operator = _operator_fixture()
    trial_norm = COULOMB_LIMIT + 0.02
    solution = SimpleNamespace(
        active=(0,),
        pressures=np.asarray([PRESSURE]),
        tangential_displacements=np.asarray([[trial_norm / KT, 0.0]]),
        states=("stick",),
    )
    references = np.zeros((1, 2), dtype=float)

    modes = [
        _post_root_tangential_modes(
            solution,
            [replace(operator, tolerance=gap_tolerance)],
            references,
            friction_tolerance=1.0e-3,
        )
        for gap_tolerance in (1.0e-12, 1.0)
    ]

    assert modes == [("stick",), ("stick",)]


@pytest.mark.parametrize("limit", [1e-12, 0.2, 1.0 - 1e-6, 1.0, 1.0 + 1e-6, 50.0, 1e6])
def test_coulomb_band_matches_projection_residual_across_force_scales(limit: float) -> None:
    tolerance = 1e-9
    scale = max(limit, 1.0)
    for multiplier, expected in ((0.5, True), (2.0, False)):
        trial = limit + multiplier * tolerance * scale
        assert _coulomb_is_stick(trial, limit, tolerance, was_sliding=False) == expected
        assert ((trial - limit) / scale <= tolerance) == expected


def test_numeric_force_floor_explains_unit_dependence_below_one() -> None:
    tolerance = 1e-9
    # Both pairs represent the same forces. Only the second uses mN.
    assert _coulomb_is_stick(0.1 + 0.5e-9, 0.1, tolerance, was_sliding=False)
    assert not _coulomb_is_stick(100.0 + 0.5e-6, 100.0, tolerance, was_sliding=False)
    # Above the floor in both force units, the relative classification agrees.
    assert _coulomb_is_stick(10.0 + 5e-9, 10.0, tolerance, was_sliding=False)
    assert _coulomb_is_stick(10000.0 + 5e-6, 10000.0, tolerance, was_sliding=False)


def test_zero_capacity_returns_zero_force_for_a_sub_tolerance_trial() -> None:
    _, dofs, operator = _operator_fixture()
    displacement = _displacement_for_local_tangent(operator, dofs, np.array([1e-14, 0.0]))
    arguments = (displacement, np.zeros(1), np.zeros((1, 2)), ("stick",))
    state, forces, _, _ = _friction_update([operator], (0,), *arguments)
    assert state == ("slip",)
    np.testing.assert_array_equal(forces, np.zeros((1, 2)))
    state, forces, _, _ = _friction_update([replace(operator, friction_coefficient=0.0)], (0,), *arguments)
    assert state == ("frictionless",)
    np.testing.assert_array_equal(forces, np.zeros((1, 2)))


@pytest.mark.parametrize("tolerance", [0.0, -1e-9, np.nan, np.inf, -np.inf, "invalid", True, False])
def test_friction_solver_rejects_invalid_tolerance(tolerance: object) -> None:
    data = _model(horizontal_load=2.0, vertical_load=-200.0)
    data["analysis"]["contact_friction_tolerance"] = tolerance

    with pytest.raises(InputValidationError, match="contact_friction_tolerance"):
        LinearStaticSolver().solve(JsonModelReader().from_dict(data))


@pytest.mark.parametrize("margin_multiplier, expected", [(0.5, "stick"), (2.0, "slip")])
def test_coulomb_boundary_is_invariant_under_length_conversion_with_fixed_force_unit(
    margin_multiplier: float, expected: str
) -> None:
    _, dofs, operator = _operator_fixture()
    tolerance = 1e-9
    trial = COULOMB_LIMIT * (1 + margin_multiplier * tolerance)
    displacement = _displacement_for_local_tangent(operator, dofs, np.array([trial / KT, 0.0]))
    references = np.zeros((1, 2))
    for length_factor in (1.0, 1000.0):
        scaled = replace(
            operator, tangential_stiffness=KT / length_factor, tolerance=operator.tolerance * length_factor,
        )
        states, _, _, _ = _friction_update(
            [scaled], (0,), displacement * length_factor,
            np.array([PRESSURE]), references, ("stick",), friction_tolerance=tolerance,
        )
        assert states == (expected,)


def test_slip_local_jacobian_matches_analytical_fixed_pressure_map() -> None:
    _, dofs, operator = _operator_fixture()
    columns = [dofs.index(3, "UX"), dofs.index(3, "UY"), dofs.index(3, "UZ")]
    base = _global_displacement(dofs, operator.vector.size, np.array([0.01, 0.005]))
    relative = operator.tangential_displacement(base)
    trial = KT * relative
    trial_norm = float(np.linalg.norm(trial))
    direction: np.ndarray = trial / trial_norm
    projector = (COULOMB_LIMIT / trial_norm) * (np.eye(2) - np.outer(direction, direction))
    analytic = projector @ (KT * np.vstack(
        (operator.tangential_vectors[0][columns], operator.tangential_vectors[1][columns])
    ))
    errors: list[tuple[float, float]] = []

    for step in (1.0e-5, 1.0e-7, 1.0e-9):
        finite_difference: np.ndarray = np.zeros((2, len(columns)), dtype=float)
        for position, column in enumerate(columns):
            plus = base.copy()
            minus = base.copy()
            plus[column] += step
            minus[column] -= step
            plus_state, plus_force, _, _ = _friction_update(
                [operator], (0,), plus, np.array([PRESSURE]), np.zeros((1, 2)), ("stick",)
            )
            minus_state, minus_force, _, _ = _friction_update(
                [operator], (0,), minus, np.array([PRESSURE]), np.zeros((1, 2)), ("stick",)
            )
            assert plus_state == minus_state == ("slip",)
            finite_difference[:, position] = (plus_force[0] - minus_force[0]) / (2.0 * step)
        errors.append(
            (
                _relative_error(finite_difference, analytic),
                max(
                    (
                        _relative_error(finite_difference[:, column], analytic[:, column])
                        for column in range(len(columns))
                    ),
                    default=0.0,
                ),
            )
        )

    assert all(frobenius <= 1.0e-6 and maximum <= 5.0e-6 for frobenius, maximum in errors)


def test_transition_is_force_continuous_but_not_claimed_differentiable() -> None:
    _, dofs, operator = _operator_fixture()
    cases = (
        ("strict_stick", 0.001),
        ("near_boundary_stick", 0.004999999),
        ("boundary", 0.005),
        ("just_above_boundary", 0.005000001),
        ("strict_slip", 0.01),
    )
    observations: list[tuple[str, str, float, float]] = []
    for name, value in cases:
        states, forces, relative, _ = _local_update(operator, dofs, np.array([value, 0.0]))
        observations.append(
            (name, states[0], float(np.linalg.norm(KT * relative[0])), float(np.linalg.norm(forces[0])))
        )

    assert [row[1] for row in observations] == ["stick", "stick", "stick", "slip", "slip"]
    assert observations[2][3] == pytest.approx(COULOMB_LIMIT)
    assert observations[3][3] == pytest.approx(COULOMB_LIMIT)
    assert abs(observations[3][3] - observations[2][3]) <= ABSOLUTE_FLOOR


def test_zero_pressure_slip_has_no_tangent_contribution() -> None:
    _, dofs, operator = _operator_fixture()
    states, forces, relative, references = _local_update(
        operator,
        dofs,
        np.array([0.1, 0.0]),
        pressure=0.0,
        state="slip",
    )
    tangent, _ = _friction_system(
        csr_matrix((operator.vector.size, operator.vector.size), dtype=float),
        np.zeros(operator.vector.size),
        [operator],
        (0,),
        ("slip",),
        np.zeros((1, 2)),
        np.zeros((1, 2)),
    )

    assert states == ("slip",)
    np.testing.assert_array_equal(forces[0], np.zeros(2))
    np.testing.assert_allclose(references[0], relative[0], rtol=0.0, atol=ABSOLUTE_FLOOR)
    assert tangent.nnz == 0


@pytest.mark.parametrize("pressure", [0.0, 1.0e-12, 1.0e-8, 1.0e-6])
def test_sliding_reference_and_force_are_continuous_as_capacity_vanishes(pressure: float) -> None:
    _, dofs, operator = _operator_fixture()
    relative = np.array([0.1, 0.0], dtype=float)
    state, forces, measured, references = _local_update(
        operator,
        dofs,
        relative,
        pressure=pressure,
        state="slip",
        references=np.zeros((1, 2), dtype=float),
    )

    expected_limit = FRICTION * pressure
    assert state == ("slip",)
    np.testing.assert_allclose(measured[0], relative, rtol=0.0, atol=ABSOLUTE_FLOOR)
    assert forces[0, 0] == pytest.approx(expected_limit, rel=1.0e-12, abs=0.0)
    assert forces[0, 1] == 0.0
    assert references[0, 0] == pytest.approx(relative[0] - expected_limit / KT, abs=ABSOLUTE_FLOOR)


def test_stick_energy_gradient_matches_tangential_force_for_three_steps() -> None:
    _, dofs, operator = _operator_fixture()
    local = np.array([0.001, 0.0005])
    references: np.ndarray = np.zeros(2, dtype=float)
    expected = KT * (local - references)

    def potential(value: np.ndarray) -> float:
        delta = value - references
        return 0.5 * KT * float(delta @ delta)

    errors: list[float] = []
    for step in (1.0e-4, 1.0e-6, 1.0e-8):
        finite_difference: np.ndarray = np.empty(2, dtype=float)
        for column in range(2):
            direction: np.ndarray = np.zeros(2, dtype=float)
            direction[column] = step
            finite_difference[column] = (potential(local + direction) - potential(local - direction)) / (2.0 * step)
        errors.append(_relative_error(finite_difference, expected))

    _, actual_force, _, _ = _local_update(operator, dofs, local)
    np.testing.assert_allclose(actual_force[0], expected, rtol=1.0e-12, atol=ABSOLUTE_FLOOR)
    assert all(error <= 1.0e-7 for error in errors)


def test_dissipation_sign_convention_and_reversal_are_finite_and_monotone() -> None:
    history = [[0.0, 1.0], [0.2, 1.0], [1.0, 1.0], [0.2, 1.0], [-0.2, 1.0], [-1.0, 1.0], [0.0, 1.0]]
    result = _solve(200.0, -200.0, history=history)
    steps = result.solver["contact"]["load_steps"]
    previous: np.ndarray = np.zeros(2, dtype=float)
    increments: list[float] = []
    cumulative: list[float] = []
    accumulated = 0.0

    for step in steps:
        reference = np.asarray(step["slip_references"][0], dtype=float)
        force = np.asarray(step["tangential_forces"][0], dtype=float)
        increment = _dissipation_increment(previous, reference, force)
        reported = float(step["local_dissipation_increment"])
        assert np.isfinite(reference).all()
        assert np.isfinite(force).all()
        assert np.isfinite(reported)
        np.testing.assert_allclose(reported, increment, rtol=1.0e-12, atol=ABSOLUTE_FLOOR)
        increments.append(increment)
        accumulated += reported
        cumulative.append(accumulated)
        previous = reference

    assert increments[0] == 0.0
    assert increments[1] == 0.0
    assert increments[2] > 0.0
    assert all(value >= -DISSIPATION_FLOOR for value in increments)
    assert all(b - a >= -DISSIPATION_FLOOR for a, b in zip(cumulative, cumulative[1:]))
    assert cumulative[-1] == pytest.approx(26.25)


def test_stick_open_and_zero_pressure_paths_have_zero_irreversible_work() -> None:
    stick = _solve(2.0, -200.0)
    assert stick.solver["contact"]["load_steps"][0]["local_dissipation_increment"] == 0.0

    _, dofs, operator = _operator_fixture()
    references: np.ndarray = np.zeros((1, 2), dtype=float)
    states, forces, _, free_references = _local_update(
        operator, dofs, np.array([0.1, 0.0]), pressure=0.0, state="slip", references=references
    )
    assert states == ("slip",)
    assert _dissipation_increment(references[0], free_references[0], forces[0]) == 0.0

    open_references = np.array([[0.2, -0.1]], dtype=float)
    _, open_forces, open_relative, retained = _friction_update(
        [operator], (), np.zeros(operator.vector.size), np.array([0.0]), open_references, ("slip",)
    )
    np.testing.assert_array_equal(retained, open_relative)
    assert _dissipation_increment(open_references[0], retained[0], open_forces[0]) == 0.0


def test_frictionless_open_path_does_not_mutate_friction_reference() -> None:
    _, dofs, operator = _operator_fixture()
    frictionless = replace(operator, friction_coefficient=0.0)
    references = np.array([[0.2, -0.1]], dtype=float)
    displacement = _global_displacement(dofs, operator.vector.size, np.array([0.0, 0.0]))

    states, forces, _, next_references = _friction_update(
        [frictionless], (), displacement, np.array([0.0]), references, ("slip",)
    )

    assert states == ("open",)
    np.testing.assert_array_equal(forces, np.zeros((1, 2)))
    np.testing.assert_array_equal(next_references, references)


@pytest.mark.parametrize("pressure", [np.nan, np.inf, -np.inf])
def test_nonfinite_pressure_fails_closed_with_typed_reason(pressure: float) -> None:
    _, dofs, operator = _operator_fixture()
    with pytest.raises(NumericalConvergenceError) as captured:
        _local_update(operator, dofs, np.array([0.01, 0.0]), pressure=pressure, state="slip")

    assert captured.value.reason is NonlinearFailureReason.NAN_DETECTED


def test_nonfinite_slip_reference_fails_closed_with_typed_reason() -> None:
    _, _, operator = _operator_fixture()
    with pytest.raises(NumericalConvergenceError) as captured:
        _friction_update(
            [operator],
            (0,),
            np.zeros(operator.vector.size),
            np.array([0.0]),
            np.array([[np.nan, 0.0]]),
            ("slip",),
        )

    assert captured.value.reason is NonlinearFailureReason.NAN_DETECTED


def test_direct_mu_validation_boundary_remains_explicitly_unqualified() -> None:
    negative = FrictionlessContact(slave_node=3, master_nodes=(0, 1, 2), friction_coefficient=-0.1)
    nonfinite = FrictionlessContact(slave_node=3, master_nodes=(0, 1, 2), friction_coefficient=float("nan"))

    assert negative.friction_coefficient == -0.1
    assert not np.isfinite(nonfinite.friction_coefficient)
