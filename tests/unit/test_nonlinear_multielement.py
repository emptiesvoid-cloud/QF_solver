from __future__ import annotations

import numpy as np
import pytest

from solveur.verification.robustness_nonlinear_solids import (
    ELEMENT_TYPES,
    mesh_refinement_mesh,
    run_mesh_refinement_benchmark,
    run_multi_element_benchmark,
    run_energy_balance_benchmark,
    run_adversarial_rollback_benchmark,
    run_finite_kinematic_j2_benchmark,
    run_high_order_geometric_benchmark,
    run_large_rotation_geometric_benchmark,
    run_large_rotation_mesh_sensitivity_benchmark,
    run_linear_buckling_benchmark,
    run_buckling_mesh_sensitivity_benchmark,
    run_euler_buckling_benchmark,
    run_fem_arc_length_benchmark,
    run_finite_kinematic_arc_length_benchmark,
    run_common_fem_snap_through_benchmark,
    run_common_fem_snap_through_restart_benchmark,
    run_common_fem_snap_through_failure_rollback_benchmark,
    run_arc_length_benchmark,
    run_shallow_arch_arc_length_benchmark,
    run_common_contact_benchmark,
    run_contact_tangent_fd_benchmark,
    run_contact_penalty_sensitivity_benchmark,
    run_contact_surface_search_benchmark,
    run_multifamily_coupled_geometry_benchmark,
    run_multifamily_coupled_contact_benchmark,
    run_finite_kinematic_limit_recovery_benchmark,
    run_coupling_benchmark,
    run_geometric_contact_benchmark,
)


def test_common_j2_campaign_exercises_connected_multi_element_meshes() -> None:
    result = run_multi_element_benchmark()
    assert result["status"] == "PASS"
    assert {row["element"] for row in result["rows"]} == set(ELEMENT_TYPES)
    assert all(row["element_count"] == 2 for row in result["rows"])
    assert all(row["final_peeq"] > 0.0 for row in result["rows"])
    assert all(row["final_plastic_dissipation"] > 0.0 for row in result["rows"])
    assert all(row["maximum_relative_residual"] < 1.0e-6 for row in result["rows"])
    assert all(row["external_work"] > 0.0 for row in result["rows"])
    assert all(row["internal_work"] > 0.0 for row in result["rows"])
    assert all(row["maximum_work_imbalance"] < 1.0e-5 for row in result["rows"])


def test_mesh_refinement_topology_is_positive_and_shared_for_all_families() -> None:
    for family in ELEMENT_TYPES:
        nodes, elements = mesh_refinement_mesh(family, 2)
        assert nodes.shape[1] == 3
        assert len(elements) > 0
        if family in {"TET4", "TET10"}:
            assert all(
                float(np.linalg.det(np.column_stack((nodes[element[1]] - nodes[element[0]], nodes[element[2]] - nodes[element[0]], nodes[element[3]] - nodes[element[0]])))) > 0.0
                for element in elements
            )


def test_mesh_refinement_benchmark_records_internal_trends() -> None:
    result = run_mesh_refinement_benchmark(("TET4",), (1, 2))

    assert result["status"] == "PASS_INTERNAL_MESH_REFINEMENT"
    assert result["owner_acceptance_band_required"] is True
    row = result["rows"][0]
    assert [item["cells_x"] for item in row["levels"]] == [1, 2]
    assert row["levels"][-1]["element_count"] > row["levels"][0]["element_count"]


def test_energy_balance_reconstructs_elastic_and_plastic_terms() -> None:
    result = run_energy_balance_benchmark(("TET4",))

    assert result["status"] == "PASS_INTERNAL_ENERGY"
    row = result["rows"][0]
    assert row["solver_status"] == "PASS"
    assert row["total_external_work"] > 0.0
    assert row["elastic_strain_energy"] > 0.0
    assert row["plastic_dissipation"] > 0.0
    assert row["nonnegative_dissipation"] is True
    assert row["relative_balance_error"] < 1.0e-6


def test_adversarial_rollback_retries_from_clean_committed_state() -> None:
    result = run_adversarial_rollback_benchmark()

    assert result["status"] == "PASS_INTERNAL_ROLLBACK"
    assert result["solver_status"] == "PASS"
    assert result["clean_retry"] is True
    assert result["rejected_increments"] == 1
    assert result["rejection_log"][0]["retry_increment"] == 0.5
    assert np.isfinite(result["final_displacement_relative_error"])
    assert np.isfinite(result["final_peeq_absolute_error"])


def test_finite_kinematic_j2_reports_element_tangent_fd() -> None:
    result = run_finite_kinematic_j2_benchmark(("TET4", "HEX8"))

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert all(row["tangent_fd_relative_error"] < 1.0e-6 for row in result["rows"])


def test_finite_kinematic_j2_high_order_rows_are_available() -> None:
    result = run_finite_kinematic_j2_benchmark(("TET10", "HEX20"))

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert {row["element"] for row in result["rows"]} == {"TET10", "HEX20"}
    assert all(row["minimum_det_f"] > 0.0 for row in result["rows"])
    assert all(row["tangent_fd_relative_error"] < 1.0e-6 for row in result["rows"])


def test_finite_kinematic_path_recovers_small_strain_limit() -> None:
    result = run_finite_kinematic_limit_recovery_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert {row["element"] for row in result["rows"]} == set(ELEMENT_TYPES)
    assert all(row["status"] == "PASS" for row in result["rows"])
    assert all(row["relative_displacement_error"] < 1.0e-8 for row in result["rows"])
    assert all(row["finite_kinematic_peeq"] == 0.0 for row in result["rows"])


def test_geometric_driver_composes_with_penalty_contact() -> None:
    result = run_geometric_contact_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["analysis"] == "geometric_nonlinear_static"
    assert result["contact"]["active_contacts"] == [0]
    assert result["contact"]["maximum_penetration"] < 1.0e-3
    assert result["maximum_relative_residual"] < 1.0e-7
    assert result["minimum_det_f"] > 0.0


def test_high_order_geometric_campaign_records_connected_mesh_rows() -> None:
    result = run_high_order_geometric_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert {row["element"] for row in result["rows"]} == {"TET10", "HEX20"}
    assert all(row["element_count"] > 0 for row in result["rows"])
    assert all(row["minimum_det_f"] > 0.0 for row in result["rows"])
    assert all(row["strain_energy"] > 0.0 for row in result["rows"])


def test_large_rotation_geometric_campaign_reaches_a_large_end_line_angle() -> None:
    result = run_large_rotation_geometric_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert {row["element"] for row in result["rows"]} == {"TET4", "HEX8"}
    assert all(row["end_line_angle_rad"] > 0.5 for row in result["rows"])
    assert all(row["minimum_det_f"] > 0.0 for row in result["rows"])
    assert all(row["maximum_relative_residual"] < 1.0e-7 for row in result["rows"])


def test_large_rotation_mesh_sensitivity_records_tet4_hex8_levels() -> None:
    result = run_large_rotation_mesh_sensitivity_benchmark(levels=(1, 2))

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["levels"] == [1, 2]
    assert {row["element"] for row in result["rows"]} == {"TET4", "HEX8"}
    assert all(len(row["levels"]) == 2 for row in result["rows"])
    assert all(level["minimum_det_f"] > 0.0 for row in result["rows"] for level in row["levels"])
    assert all(level["maximum_relative_residual"] < 1.0e-7 for row in result["rows"] for level in row["levels"])


def test_high_order_large_rotation_mesh_sensitivity_is_bounded_at_low_load() -> None:
    result = run_large_rotation_mesh_sensitivity_benchmark(
        ("TET10", "HEX20"),
        levels=(1, 2),
        load_increments=20,
        load_scale=0.25,
    )

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["load_scale"] == 0.25
    assert {row["element"] for row in result["rows"]} == {"TET10", "HEX20"}
    assert all(level["minimum_det_f"] > 0.0 for row in result["rows"] for level in row["levels"])
    assert all(level["maximum_relative_residual"] < 1.0e-7 for row in result["rows"] for level in row["levels"])


def test_bounded_buckling_campaign_records_sparse_tangent_factors() -> None:
    result = run_linear_buckling_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert {row["element"] for row in result["rows"]} == {"TET4", "HEX8"}
    assert all(row["critical_factor"] > 0.0 for row in result["rows"])
    assert all(row["initial_tangent_nnz"] > 0 for row in result["rows"])
    assert all(row["relative_bracket_width"] < 1.0e-3 for row in result["rows"])
    assert {row["eigen_formulation"] for row in result["rows"]} <= {
        "generalized_eigsh",
        "generalized_eigs_shift_invert",
        "bracketed_sparse_eigenvalue",
    }


def test_bounded_buckling_campaign_exercises_high_order_research_rows() -> None:
    result = run_linear_buckling_benchmark(("TET10", "HEX20"))

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert {row["element"] for row in result["rows"]} == {"TET10", "HEX20"}
    assert all(row["critical_factor"] > 0.0 for row in result["rows"])
    assert all(row["initial_tangent_nnz"] > 0 for row in result["rows"])
    assert all(row["relative_bracket_width"] < 1.0e-3 for row in result["rows"])


def test_buckling_mesh_sensitivity_records_all_family_trends() -> None:
    result = run_buckling_mesh_sensitivity_benchmark(levels=(1, 2))

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["levels"] == [1, 2]
    assert {row["element"] for row in result["rows"]} == set(ELEMENT_TYPES)
    assert all(row["status"] == "PASS" for row in result["rows"])
    assert all(len(row["levels"]) == 2 for row in result["rows"])
    assert all(row["levels"][-1]["critical_factor_relative_change"] >= 0.0 for row in result["rows"])
    assert all(row["levels"][-1]["preload_residual"] < 1.0e-6 for row in result["rows"])


def test_euler_buckling_reference_is_recorded_as_bounded_research(tmp_path) -> None:
    result = run_euler_buckling_benchmark(tmp_path / "euler")

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["reference"]["type"] == "euler_clamped_free_column"
    assert len(result["levels"]) == 2
    assert result["levels"][-1]["euler_relative_error"] < 0.10
    assert all(check["status"] == "PASS" for check in result["checks"])


def test_arc_length_campaign_reaches_target_with_finite_residual_history() -> None:
    result = run_arc_length_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["method"] == "arc_length"
    assert result["reached_target"] is True
    assert result["monotone_load_factor"] is True
    assert result["maximum_relative_residual"] < 1.0e-8
    assert all(np.all(np.isfinite(history)) for history in result["residual_histories"])


def test_fem_arc_length_campaign_records_sparse_tet4_path() -> None:
    result = run_fem_arc_length_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["method"] == "trace_sparse_arc_length"
    assert result["step_count"] == 24
    assert result["maximum_relative_residual"] < 1.0e-7
    assert result["minimum_det_f"] > 0.99
    assert result["load_factor_range"][1] > result["load_factor_range"][0]


def test_finite_kinematic_arc_length_uses_common_adaptive_four_family_driver() -> None:
    result = run_finite_kinematic_arc_length_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["kinematics"] == "total_lagrangian_j2"
    assert result["final_load_factor"] >= 0.5 - 1.0e-6
    assert result["maximum_relative_residual"] < 1.0e-7
    assert np.isfinite(result["final_peeq"])
    assert result["elements"] == ["TET4", "TET10", "HEX8", "HEX20"]
    assert all(row["status"] == "PASS" for row in result["rows"])
    assert all(row["adaptive_arc_length"] for row in result["rows"])
    assert all(row["load_factor_range"][1] >= 0.5 - 1.0e-6 for row in result["rows"])
    assert all(row["radius_history"] for row in result["rows"])
    assert all(np.all(np.isfinite(row["radius_history"])) for row in result["rows"])
    assert result["load_factor_ranges"]["HEX20"][1] == pytest.approx(0.5)


def test_common_fem_arc_length_crosses_a_snap_through_turning_point() -> None:
    result = run_common_fem_snap_through_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["common_driver"] is True
    assert result["method"] == "arc_length"
    assert result["kinematics"] == "total_lagrangian"
    assert result["element_family"] == "TET4"
    assert result["branch_turn_count"] >= 1
    assert result["turning_point_step"] is not None
    assert result["load_factor_range"][0] < result["load_factor_range"][1] < 0.0
    assert result["maximum_relative_residual"] < 1.0e-7
    assert result["minimum_det_f"] > 0.0
    assert any(sign == 1 for sign in result["predictor_signs"])


@pytest.mark.parametrize("restart_position", ["before_turn", "after_turn"])
def test_common_fem_arc_length_restart_preserves_postcritical_branch(restart_position: str) -> None:
    result = run_common_fem_snap_through_restart_benchmark(restart_position=restart_position)

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["common_driver"] is True
    assert result["turning_point_crossed_after_restart"] is True
    assert result["resumed_restart_step"] == result["checkpoint_step"]
    assert result["suffix_load_factor_max_error"] <= 1.0e-14
    assert result["final_displacement_relative_error"] <= 1.0e-14
    assert result["material_state_match"] is True


def test_common_fem_arc_length_rolls_back_after_failure_near_turning_point() -> None:
    result = run_common_fem_snap_through_failure_rollback_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["common_driver"] is True
    assert result["near_turning_point"] is True
    assert result["corrections_completed"] == 2
    assert result["retry_clean"] is True
    assert result["rejected_increments"] == 1
    assert result["rejection_log"][0]["rollback_before_retry"] is True
    assert result["rejection_log"][0]["failure_reason"] == "MAX_ITERATIONS"
    assert all(direction == 1 for direction in result["branch_directions_after_initial_step"])


def test_reduced_shallow_arch_arc_length_follows_a_limit_point() -> None:
    result = run_shallow_arch_arc_length_benchmark(steps=80, radius=0.05)

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["limit_point_observed"] is True
    assert result["branch_turn_count"] >= 1
    assert result["maximum_equilibrium_error"] < 1.0e-8
    assert result["load_factor_range"][1] > result["load_factor_range"][0]


def test_common_contact_campaign_records_unilateral_sparse_activation() -> None:
    result = run_common_contact_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["global_solver_status"] == "PASS"
    assert result["updated_global_solver_status"] == "PASS"
    assert result["open"]["active_contacts"] == []
    assert result["closed"]["active_contacts"] == [0]
    assert result["open_tangent_nnz"] == 0
    assert result["closed_tangent_nnz"] > 0


def test_contact_penalty_tangent_matches_finite_difference() -> None:
    result = run_contact_tangent_fd_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["active_contacts"] == [0]
    assert result["tangent_nnz"] > 0
    assert result["maximum_relative_error"] < 1.0e-8
    assert [row["direction_count"] for row in result["rows"]] == [12, 12, 12]


def test_contact_penalty_sensitivity_records_decreasing_penetration() -> None:
    result = run_contact_penalty_sensitivity_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["penetration_monotone_nonincreasing"] is True
    assert all(row["converged"] for row in result["rows"])
    assert all(row["maximum_penetration"] >= 0.0 for row in result["rows"])
    assert result["rows"][-1]["maximum_penetration"] < result["rows"][0]["maximum_penetration"]
    assert all(row["contact_tangent_nnz"] > 0 for row in result["rows"])


def test_contact_surface_search_selects_the_expected_master_faces() -> None:
    result = run_contact_surface_search_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["selected_face_indices"] == [0, 1]
    assert all(row["master_face_count"] == 2 for row in result["rows"])
    assert all(row["active_contacts"] == [] for row in result["rows"])


def test_coupling_campaign_uses_one_driver_for_material_geometry_and_contact() -> None:
    result = run_coupling_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["shared_driver"] is True
    assert result["shared_residual_and_tangent"] is True
    assert {row["case"] for row in result["rows"]} == {
        "j2_plus_geometry",
        "geometry_plus_contact",
        "j2_geometry_plus_updated_contact",
    }
    assert all(row["status"] == "PASS" for row in result["rows"])
    assert all(row["maximum_relative_residual"] < 1.0e-7 for row in result["rows"])


def test_multifamily_coupled_geometry_campaign_uses_the_common_driver() -> None:
    result = run_multifamily_coupled_geometry_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["shared_driver"] is True
    assert {row["element"] for row in result["rows"]} == set(ELEMENT_TYPES)
    assert all(row["kinematics"] == "total_lagrangian_j2" for row in result["rows"])
    assert all(row["contact_mode"] == "none" for row in result["rows"])
    assert all(row["maximum_relative_residual"] < 1.0e-6 for row in result["rows"])


def test_multifamily_coupled_contact_campaign_uses_the_common_driver() -> None:
    result = run_multifamily_coupled_contact_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["shared_driver"] is True
    assert {row["element"] for row in result["rows"]} == set(ELEMENT_TYPES)
    assert all(row["status"] == "PASS" for row in result["rows"])
    assert all(row["kinematics"] == "total_lagrangian_j2" for row in result["rows"])
    assert all(row["contact_search_mode"] == "updated" for row in result["rows"])
    assert all(row["active_step_count"] > 0 for row in result["rows"])
    assert all(row["initial_gap"] > 0.0 and row["final_gap"] < 0.0 for row in result["rows"])
    assert all(row["final_peeq"] > 0.0 for row in result["rows"])
    assert all(row["maximum_penetration"] < 1.0e-4 for row in result["rows"])
    assert all(row["maximum_relative_residual"] < 1.0e-7 for row in result["rows"])
