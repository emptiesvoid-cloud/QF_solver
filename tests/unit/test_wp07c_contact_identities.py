"""WP07-C lightweight identities for bounded frictionless contact."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.contact.evaluation import (
    UPDATED_SEARCH_RESTART,
    evaluate_penalty_contact,
    updated_search_restart_status,
)
from solveur.core.model import FiniteElementModel
from solveur.core.dofs import DofManager
from solveur.core.results import SolveResult
from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader


PENALTY = 1.0e5
ENERGY_GRADIENT_TOLERANCE = 1.0e-7
TANGENT_FROBENIUS_TOLERANCE = 1.0e-6
TANGENT_MAX_COLUMN_TOLERANCE = 5.0e-6
TANGENT_SYMMETRY_TOLERANCE = 1.0e-12
REPLAY_RELATIVE_TOLERANCE = 1.0e-12
REPLAY_ABSOLUTE_FLOOR = 1.0e-14


def _penalty_model() -> FiniteElementModel:
    return JsonModelReader().from_dict(
        {
            "analysis": {"type": "linear_static", "method": "direct"},
            "nodes": [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.25, 0.25, 0.1],
            ],
            "elements": [],
            "materials": {},
            "fixed_dofs": [],
            "loads": [],
            "springs": [{"node_a": 3, "dofs": ["UZ"], "stiffness": 1.0}],
            "contacts": [{"name": "plane", "slave_node": 3, "master_nodes": [0, 1, 2]}],
        }
    )


def _penalty_fixture() -> tuple[FiniteElementModel, DofManager, np.ndarray]:
    model = _penalty_model()
    dofs = model.dof_manager()
    vector = np.zeros(dofs.ndof, dtype=float)
    vector[dofs.index(3, "UZ")] = 1.0
    vector[dofs.index(0, "UZ")] = -0.5
    vector[dofs.index(1, "UZ")] = -0.25
    vector[dofs.index(2, "UZ")] = -0.25
    return model, dofs, vector


def _displacement_for_gap(dofs: DofManager, gap: float) -> np.ndarray:
    displacement = np.zeros(dofs.ndof, dtype=float)
    displacement[dofs.index(3, "UZ")] = gap - 0.1
    return displacement


def _contact_energy(model: FiniteElementModel, dofs: DofManager, displacement: np.ndarray) -> float:
    evaluation = evaluate_penalty_contact(model, dofs, displacement, penalty=PENALTY)
    gap = evaluation.gaps[0]
    return 0.5 * PENALTY * min(gap, 0.0) ** 2


def _relative_error(actual: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(actual - reference) / max(float(np.linalg.norm(reference)), 1.0))


def _active_set_model(load: float) -> FiniteElementModel:
    return JsonModelReader().from_dict(
        {
            "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
            "nodes": [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.25, 0.25, 0.1],
            ],
            "elements": [],
            "materials": {},
            "fixed_dofs": [
                {"node": 0, "dofs": ["UX", "UY", "UZ"]},
                {"node": 1, "dofs": ["UX", "UY", "UZ"]},
                {"node": 2, "dofs": ["UX", "UY", "UZ"]},
                {"node": 3, "dofs": ["UX", "UY"]},
            ],
            "springs": [{"node_a": 3, "dofs": ["UZ"], "stiffness": 1000.0}],
            "loads": [{"node": 3, "dof": "UZ", "value": load}],
            "contacts": [{"name": "plane", "slave_node": 3, "master_nodes": [0, 1, 2]}],
        }
    )


def _solve_active_set(load: float) -> SolveResult:
    return LinearStaticSolver().solve(_active_set_model(load))


def test_penalty_open_contact_has_zero_force_and_tangent() -> None:
    model, dofs, _ = _penalty_fixture()
    evaluation = evaluate_penalty_contact(model, dofs, _displacement_for_gap(dofs, 1.0e-6), penalty=PENALTY)

    assert evaluation.active_contacts == ()
    assert np.linalg.norm(evaluation.internal_force) / PENALTY <= 1.0e-12
    assert evaluation.tangent.nnz == 0
    assert np.all(evaluation.tangent.toarray() == 0.0)


def test_penalty_active_force_matches_k_gap_times_relative_gap_vector() -> None:
    model, dofs, relative_gap_vector = _penalty_fixture()
    displacement = _displacement_for_gap(dofs, -0.1)
    evaluation = evaluate_penalty_contact(model, dofs, displacement, penalty=PENALTY)

    gap = evaluation.gaps[0]
    expected = PENALTY * gap * relative_gap_vector

    assert gap < 0.0
    np.testing.assert_allclose(evaluation.internal_force, expected, rtol=0.0, atol=1.0e-12)


def test_penalty_energy_gradient_matches_contact_force_away_from_switching() -> None:
    model, dofs, _ = _penalty_fixture()
    displacement = _displacement_for_gap(dofs, -0.1)
    evaluation = evaluate_penalty_contact(model, dofs, displacement, penalty=PENALTY)
    step = 1.0e-7
    gradient = np.zeros(dofs.ndof, dtype=float)
    for index in range(dofs.ndof):
        perturbation = np.zeros(dofs.ndof, dtype=float)
        perturbation[index] = step
        gradient[index] = (
            _contact_energy(model, dofs, displacement + perturbation)
            - _contact_energy(model, dofs, displacement - perturbation)
        ) / (2.0 * step)

    error = _relative_error(gradient, evaluation.internal_force)
    assert error <= ENERGY_GRADIENT_TOLERANCE


def test_penalty_tangent_matches_force_finite_difference_and_is_symmetric() -> None:
    model, dofs, _ = _penalty_fixture()
    displacement = _displacement_for_gap(dofs, -0.1)
    evaluation = evaluate_penalty_contact(model, dofs, displacement, penalty=PENALTY)
    step = 1.0e-6
    finite_difference = np.zeros((dofs.ndof, dofs.ndof), dtype=float)
    for column in range(dofs.ndof):
        perturbation = np.zeros(dofs.ndof, dtype=float)
        perturbation[column] = step
        plus = evaluate_penalty_contact(model, dofs, displacement + perturbation, penalty=PENALTY)
        minus = evaluate_penalty_contact(model, dofs, displacement - perturbation, penalty=PENALTY)
        finite_difference[:, column] = (plus.internal_force - minus.internal_force) / (2.0 * step)

    tangent = evaluation.tangent.toarray()
    frobenius_error = _relative_error(tangent, finite_difference)
    column_errors = [
        _relative_error(tangent[:, column], finite_difference[:, column])
        for column in range(dofs.ndof)
        if np.linalg.norm(finite_difference[:, column]) > 0.0
    ]
    symmetry_error = _relative_error(tangent, tangent.T)

    assert frobenius_error <= TANGENT_FROBENIUS_TOLERANCE
    assert max(column_errors, default=0.0) <= TANGENT_MAX_COLUMN_TOLERANCE
    assert symmetry_error <= TANGENT_SYMMETRY_TOLERANCE


def test_penalty_activation_boundary_has_declared_piecewise_semantics() -> None:
    model, dofs, _ = _penalty_fixture()
    open_state = evaluate_penalty_contact(model, dofs, _displacement_for_gap(dofs, 1.0e-6), penalty=PENALTY)
    closed_state = evaluate_penalty_contact(model, dofs, _displacement_for_gap(dofs, -1.0e-6), penalty=PENALTY)
    boundary = evaluate_penalty_contact(model, dofs, _displacement_for_gap(dofs, 0.0), penalty=PENALTY)

    assert open_state.active_contacts == ()
    assert open_state.tangent.nnz == 0
    assert closed_state.active_contacts == (0,)
    assert closed_state.tangent.nnz > 0
    assert boundary.gaps[0] == pytest.approx(0.0, abs=1.0e-15)
    assert boundary.active_contacts == ()
    assert boundary.tangent.nnz == 0


def test_penalty_open_close_reopen_has_no_ghost_force_or_history() -> None:
    model, dofs, _ = _penalty_fixture()
    path = [1.0e-2, -1.0e-4, -0.1, -1.0e-2, 1.0e-2]
    evaluations = [
        evaluate_penalty_contact(model, dofs, _displacement_for_gap(dofs, gap), penalty=PENALTY)
        for gap in path
    ]
    reopened = evaluations[-1]
    reopened_replay = evaluate_penalty_contact(model, dofs, _displacement_for_gap(dofs, path[-1]), penalty=PENALTY)
    closed = evaluations[2]
    closed_replay = evaluate_penalty_contact(model, dofs, _displacement_for_gap(dofs, path[2]), penalty=PENALTY)

    assert evaluations[0].active_contacts == ()
    assert evaluations[1].active_contacts == (0,)
    assert np.linalg.norm(evaluations[2].internal_force) > np.linalg.norm(evaluations[1].internal_force)
    assert evaluations[3].active_contacts == (0,)
    assert reopened.active_contacts == ()
    assert np.linalg.norm(reopened.internal_force) / PENALTY <= 1.0e-12
    assert reopened.tangent.nnz == 0
    np.testing.assert_array_equal(reopened.internal_force, reopened_replay.internal_force)
    np.testing.assert_array_equal(closed.internal_force, closed_replay.internal_force)
    np.testing.assert_array_equal(closed.tangent.toarray(), closed_replay.tangent.toarray())


def test_active_set_open_contact_has_no_reaction() -> None:
    result = _solve_active_set(20.0)
    row = result.solver["contact"]["contacts"][0]
    f_char = 20.0

    assert row["active"] is False
    assert abs(float(row["pressure"])) / f_char <= 1.0e-12


def test_active_set_closed_contact_satisfies_scaled_gap_sign_and_complementarity() -> None:
    result = _solve_active_set(-200.0)
    row = result.solver["contact"]["contacts"][0]
    l_char = 0.1
    p_char = max(abs(float(row["pressure"])), 1.0)
    normalized_gap = abs(float(row["gap"])) / l_char
    wrong_sign_pressure = max(-float(row["pressure"]) / p_char, 0.0)
    normalized_complementarity = abs(float(row["gap"]) * float(row["pressure"])) / (l_char * p_char)

    assert row["active"] is True
    assert normalized_gap <= 1.0e-10
    assert wrong_sign_pressure <= 1.0e-12
    assert normalized_complementarity <= 1.0e-10


def test_active_set_equilibrium_diagnostics_are_scale_aware_and_finite() -> None:
    result = _solve_active_set(-200.0)

    assert result.audit is not None
    equilibrium = result.audit.equilibrium
    force_error = float(equilibrium["force_balance_relative_error"])
    moment_error = float(equilibrium["moment_balance_relative_error"])

    assert np.isfinite(force_error)
    assert np.isfinite(moment_error)
    assert force_error <= 1.0e-8
    assert moment_error <= 1.0e-8


def test_active_set_replay_reproduces_active_set_multiplier_and_result() -> None:
    first = _solve_active_set(-200.0)
    second = _solve_active_set(-200.0)
    first_row = first.solver["contact"]["contacts"][0]
    second_row = second.solver["contact"]["contacts"][0]

    assert first_row["active"] == second_row["active"]
    assert first_row["pressure"] == second_row["pressure"]
    np.testing.assert_array_equal(first.displacements, second.displacements)
    assert abs(float(first_row["gap"]) - float(second_row["gap"])) <= max(
        REPLAY_ABSOLUTE_FLOOR,
        REPLAY_RELATIVE_TOLERANCE * max(abs(float(first_row["gap"])), 1.0),
    )


def test_updated_search_remains_research_only_without_energy_claim() -> None:
    assert updated_search_restart_status() == UPDATED_SEARCH_RESTART
    assert UPDATED_SEARCH_RESTART == "UNQUALIFIED_RESTART"
