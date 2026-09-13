"""No-solve tests for the prospective WP07-D structural V&V contract."""

from __future__ import annotations

import copy

import numpy as np
import pytest

from scripts.prepare_wp07d_structural_vnv import (
    MESH_LEVELS,
    active_set_initial_state_check,
    accumulate_constant_t3_traction,
    actual_mesh_load_check,
    build_preflight,
    check_load_contract,
    mesh_contract_check,
    load_contract,
    no_contact_well_posedness_check,
    penalty_initial_state_check,
    resultant_and_moment,
    validate_contract,
)


def _top_surface() -> tuple[np.ndarray, tuple[tuple[int, int, int], ...]]:
    nodes = np.array(
        [
            [0.0, 0.0, 0.21],
            [1.0, 0.0, 0.21],
            [1.0, 0.5, 0.21],
            [0.0, 0.5, 0.21],
        ]
    )
    faces = ((0, 1, 2), (0, 2, 3))
    return nodes, faces


def test_contract_is_frozen_for_two_benchmarks_and_three_levels() -> None:
    contract = load_contract()

    validate_contract(contract)

    assert tuple(level["id"] for level in contract["mesh_levels"]) == MESH_LEVELS
    assert contract["structural_solves_run"] is False
    assert contract["external_solver_run"] is False
    assert contract["thresholds"]["status"] == "OWNER_CANDIDATE_PRE_RESULT"


def test_preflight_plans_all_cases_without_enabling_execution() -> None:
    preflight = build_preflight(load_contract(), source_sha="test-sha", worktree_dirty=False)

    assert preflight["status"] == "PREPARATION_ONLY"
    assert preflight["source_sha"] == "test-sha"
    assert preflight["worktree_dirty"] is False
    assert len(preflight["planned_cases"]) == 6
    assert {case["status"] for case in preflight["planned_cases"]} == {"NOT_EXECUTED"}
    assert all(case["output_path"].startswith("qualification/0_2_9/wp07d_runs/") for case in preflight["planned_cases"])
    assert preflight["execution_guard"] == {
        "structural_solves_enabled": False,
        "external_solver_enabled": False,
        "reason": "WP07-D contract preparation waits for WP04 M3 completion.",
    }


def test_consistent_t3_traction_preserves_resultant_and_origin_moment() -> None:
    nodes, faces = _top_surface()
    forces = accumulate_constant_t3_traction(nodes, faces, [0.0, 0.0, -100000.0])

    resultant, moment = resultant_and_moment(nodes, forces)

    np.testing.assert_allclose(resultant, [0.0, 0.0, -50000.0], rtol=0.0, atol=1.0e-12)
    np.testing.assert_allclose(moment, [-12500.0, 25000.0, 0.0], rtol=0.0, atol=1.0e-12)


def test_load_contract_reports_mesh_independent_invariants() -> None:
    nodes, faces = _top_surface()
    result = check_load_contract(
        nodes,
        faces,
        [0.0, 0.0, -100000.0],
        [0.0, 0.0, -50000.0],
        [-12500.0, 25000.0, 0.0],
    )

    assert result["pass"] is True
    assert result["resultant_error"] <= 1.0e-12
    assert result["moment_error"] <= 1.0e-12


def test_contract_validation_fails_closed_if_execution_is_enabled() -> None:
    contract = copy.deepcopy(load_contract())
    contract["execution_policy"] = {"structural_solves_allowed": True, "external_solver_allowed": False}

    with pytest.raises(ValueError, match="Structural solves"):
        validate_contract(contract)


def test_contract_validation_requires_all_three_levels() -> None:
    contract = copy.deepcopy(load_contract())
    contract["mesh_levels"] = contract["mesh_levels"][:2]

    with pytest.raises(ValueError, match="exactly M1, M2 and M3"):
        validate_contract(contract)


@pytest.mark.parametrize("level", MESH_LEVELS)
def test_actual_mesh_contract_passes_for_every_declared_level(level: str) -> None:
    result = mesh_contract_check(load_contract(), level)

    assert result["status"] == "PASS"
    assert result["finite_coordinates_and_volumes"] is True
    assert result["positive_reference_volumes"] is True
    assert result["deterministic_connectivity"] is True
    assert result["master_coverage"] is True


@pytest.mark.parametrize("level", MESH_LEVELS)
def test_actual_mesh_load_contract_preserves_resultant_and_moment(level: str) -> None:
    result = actual_mesh_load_check(load_contract(), level)

    assert result["status"] == "PASS"
    np.testing.assert_allclose(
        result["resultant"],
        [0.0, 0.0, -50000.0],
        rtol=1.0e-12,
        atol=result["resultant_error"]["absolute_floor"],
    )
    np.testing.assert_allclose(
        result["moment_about_origin"],
        [-12500.0, 25000.0, 0.0],
        rtol=1.0e-12,
        atol=result["moment_error"]["absolute_floor"],
    )
    assert result["resultant_error"]["relative_error"] <= 1.0e-12
    assert result["moment_error"]["relative_error"] <= 1.0e-12


def test_m1_no_contact_system_is_well_posed_without_contact_solve() -> None:
    result = no_contact_well_posedness_check()

    assert result["status"] == "PASS"
    assert result["contact_solve"] is False
    assert result["reduced_dof_count"] == 36
    assert result["finite_matrix"] is True
    assert result["nonzero_diagonal_count"] == result["reduced_dof_count"]
    assert result["smallest_eigenvalue"] > result["eigenvalue_zero_tolerance"]
    assert result["arbitrary_load_solution_finite"] is True


def test_m1_penalty_zero_state_has_no_contact_contribution() -> None:
    result = penalty_initial_state_check()

    assert result["status"] == "PASS"
    assert result["contact_solve"] is False
    assert result["active_count"] == 0
    assert result["force_norm"] == 0.0
    assert result["tangent_nnz"] == 0
    assert result["minimum_gap"] == pytest.approx(0.01, abs=1.0e-14)


def test_m1_active_set_initial_state_is_empty_and_finite() -> None:
    result = active_set_initial_state_check()

    assert result["status"] == "PASS"
    assert result["contact_solve"] is False
    assert result["initial_active_count"] == 0
    assert result["initial_active_set"] == []
    assert result["minimum_initial_gap"] > 0.0
