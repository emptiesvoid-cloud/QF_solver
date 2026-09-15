"""WP08-B friction identities, zero-pressure safety and state transactions."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from solveur.contact.support import _ContactOperator, _friction_update, _operator
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.material_state import StateTransaction, state_digest
from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader


def _model(
    *,
    horizontal_load: float,
    vertical_load: float,
    friction: float = 0.5,
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
                "friction_coefficient": friction,
                "tangential_stiffness": 10000.0,
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


@pytest.mark.parametrize(
    "scale",
    [
        pytest.param(0.0, id="zero_increment"),
        pytest.param(0.1, id="positive_increment"),
        pytest.param(-0.1, id="reversed_increment"),
    ],
)
def test_zero_pressure_prior_slip_is_finite_and_recentered(scale: float) -> None:
    _, _, operator = _operator_fixture()
    displacement = operator.tangential_vectors[0] * scale
    references: np.ndarray = np.zeros((1, 2), dtype=float)

    with np.errstate(all="raise"):
        states, forces, relative, next_references = _friction_update(
            [operator],
            (0,),
            displacement,
            np.array([0.0]),
            references,
            ("slip",),
        )

    assert states == ("slip",)
    np.testing.assert_array_equal(forces[0], np.zeros(2))
    assert np.isfinite(forces).all()
    assert np.isfinite(next_references).all()
    np.testing.assert_allclose(next_references[0], relative[0], rtol=0.0, atol=1.0e-14)


def test_pressure_return_after_zero_pressure_free_slip_has_no_stored_force() -> None:
    _, _, operator = _operator_fixture()
    displacement = operator.tangential_vectors[0] * 0.1
    initial_references: np.ndarray = np.zeros((1, 2), dtype=float)

    free_states, free_forces, _, free_references = _friction_update(
        [operator], (0,), displacement, np.array([0.0]), initial_references, ("slip",)
    )
    returned_states, returned_forces, _, returned_references = _friction_update(
        [operator], (0,), displacement, np.array([100.0]), free_references, free_states
    )

    assert free_states == ("slip",)
    np.testing.assert_array_equal(free_forces[0], np.zeros(2))
    assert returned_states == ("stick",)
    np.testing.assert_array_equal(returned_forces[0], np.zeros(2))
    np.testing.assert_array_equal(returned_references[0], free_references[0])


def test_open_contact_has_zero_tangential_force_and_retains_reference() -> None:
    _, _, operator = _operator_fixture()
    references = np.array([[0.2, -0.1]], dtype=float)
    states, forces, _, next_references = _friction_update(
        [operator], (), np.zeros(operator.vector.size), np.array([0.0]), references, ("slip",)
    )

    assert states == ("open",)
    np.testing.assert_array_equal(forces[0], np.zeros(2))
    np.testing.assert_array_equal(next_references, references)


def test_positive_pressure_stick_force_identity_and_reference() -> None:
    result = _solve(2.0, -200.0)
    row = result.solver["contact"]["contacts"][0]
    force = np.asarray(row["tangential_force"], dtype=float)
    relative = np.asarray(row["tangential_displacement"], dtype=float)
    expected = 10000.0 * relative
    error = float(np.linalg.norm(force - expected)) / max(float(np.linalg.norm(expected)), 1.0e-14)

    assert row["tangential_state"] == "stick"
    assert error <= 1.0e-12
    assert np.isfinite(force).all()
    np.testing.assert_array_equal(result.solver["contact"]["slip_references"], [[0.0, 0.0]])


def test_positive_pressure_slip_satisfies_coulomb_radius_direction_and_reference() -> None:
    result = _solve(200.0, -200.0)
    row = result.solver["contact"]["contacts"][0]
    force = np.asarray(row["tangential_force"], dtype=float)
    relative = np.asarray(row["tangential_displacement"], dtype=float)
    trial = 10000.0 * relative
    limit = float(row["friction_limit"])
    trial_norm = np.linalg.norm(trial)
    force_norm = np.linalg.norm(force)
    expected = limit * trial / trial_norm
    radius_error = abs(force_norm - limit) / max(limit, 1.0e-14)
    direction_cosine = float(force @ trial) / (force_norm * trial_norm)
    direction_error = abs(1.0 - direction_cosine)
    expected_reference = relative - force / 10000.0

    assert row["tangential_state"] == "slip"
    assert radius_error <= 1.0e-12
    assert direction_error <= 1.0e-12
    np.testing.assert_allclose(
        np.asarray(result.solver["contact"]["slip_references"][0], dtype=float),
        expected_reference,
        rtol=1.0e-12,
        atol=1.0e-14,
    )
    np.testing.assert_allclose(force, expected, rtol=1.0e-12, atol=1.0e-14)


def test_transition_and_reversal_are_deterministic() -> None:
    history = [[0.0, 1.0], [0.2, 1.0], [1.0, 1.0], [0.2, 1.0], [-0.2, 1.0], [-1.0, 1.0], [0.0, 1.0]]
    first = _solve(200.0, -200.0, history=history)
    second = _solve(200.0, -200.0, history=history)
    first_steps = first.solver["contact"]["load_steps"]
    second_steps = second.solver["contact"]["load_steps"]
    states = [step["states"][0] for step in first_steps]
    forces = [float(step["tangential_forces"][0][0]) for step in first_steps]

    assert states == ["stick", "stick", "slip", "slip", "slip", "slip", "slip"]
    assert any(value > 0.0 for value in forces)
    assert any(value < 0.0 for value in forces)
    assert first_steps == second_steps
    np.testing.assert_array_equal(first.displacements, second.displacements)


def test_state_transaction_rolls_back_actual_friction_reference_after_failure() -> None:
    _, _, operator = _operator_fixture()
    displacement = operator.tangential_vectors[0] * 0.1
    _, _, _, candidate = _friction_update(
        [operator], (0,), displacement, np.array([0.0]), np.zeros((1, 2)), ("slip",)
    )
    committed: np.ndarray = np.zeros((1, 2), dtype=float)
    transaction = StateTransaction(committed)
    initial_digest = transaction.committed_digest
    transaction.begin_trial()[...] = candidate

    try:
        raise NumericalConvergenceError(
            "injected friction increment failure",
            reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
        )
    except NumericalConvergenceError:
        transaction.rollback()

    assert transaction.trial is None
    assert transaction.committed_digest == initial_digest
    np.testing.assert_array_equal(committed, np.zeros((1, 2)))


def test_state_transaction_commit_then_rejected_retry_targets_accepted_state() -> None:
    committed: np.ndarray = np.zeros((1, 2), dtype=float)
    transaction = StateTransaction(committed)
    accepted = np.array([[0.1, 0.2]], dtype=float)
    transaction.begin_trial()[...] = accepted
    transaction.commit()
    accepted_digest = transaction.committed_digest

    transaction.begin_trial()[...] = np.array([[0.3, 0.4]], dtype=float)
    transaction.rollback()

    assert transaction.committed_digest == accepted_digest
    np.testing.assert_array_equal(committed, accepted)


def test_friction_re_evaluation_after_rollback_is_deterministic() -> None:
    _, _, operator = _operator_fixture()
    displacement = operator.tangential_vectors[0] * 0.1
    references: np.ndarray = np.zeros((1, 2), dtype=float)
    first = _friction_update([operator], (0,), displacement, np.array([0.0]), references, ("slip",))
    transaction = StateTransaction(references.copy())
    transaction.begin_trial()[...] = first[3]
    transaction.rollback()
    second = _friction_update([operator], (0,), displacement, np.array([0.0]), references, ("slip",))

    assert first[0] == second[0]
    for first_value, second_value in zip(first[1:], second[1:]):
        np.testing.assert_array_equal(first_value, second_value)


def test_nonfinite_friction_state_fails_closed_with_typed_reason() -> None:
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
    assert "non-finite" in str(captured.value)


@pytest.mark.parametrize("coefficient", [-0.1, float("nan"), float("inf"), -float("inf")])
def test_public_input_rejects_invalid_friction_coefficient(coefficient: float) -> None:
    data = _model(horizontal_load=0.0, vertical_load=-1.0)
    data["contacts"][0]["friction_coefficient"] = coefficient

    with pytest.raises(InputValidationError, match="friction_coefficient"):
        JsonModelReader().from_dict(data)


def test_state_digest_is_stable_for_equal_friction_reference_states() -> None:
    first = np.array([[0.1, -0.2]], dtype=float)
    second = np.array([[0.1, -0.2]], dtype=float)

    assert state_digest(first) == state_digest(second)
