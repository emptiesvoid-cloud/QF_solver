"""No-solve checks for the prospective WP08 area-supported benchmark."""

from __future__ import annotations

import pytest

from scripts.prepare_wp08_area_supported_benchmark import (
    HEIGHT_M,
    TANGENTIAL_STIFFNESS_DENSITY_N_PER_M3,
    WIDTH_M,
    MESH_LEVELS,
    _surface_geometry,
    preflight_record,
)
from solveur.contact.measures import reference_surface_areas


def test_contact_patch_is_two_dimensional_and_disjoint_from_fixed_face() -> None:
    record = preflight_record()
    for level in record["levels"]:
        assert level["contact_support_affine_rank"] == 2
        assert level["fixed_contact_node_intersection_count"] == 0
        assert level["all_slave_nodes_project_inside_master_patch"] is True
        assert level["all_slave_nodes_have_positive_area"] is True
        assert level["contact_patch_area_m2"] == pytest.approx(WIDTH_M * HEIGHT_M)


def test_integrated_surface_stiffness_is_mesh_invariant_without_redistribution() -> None:
    record = preflight_record()
    expected = TANGENTIAL_STIFFNESS_DENSITY_N_PER_M3 * WIDTH_M * HEIGHT_M
    assert record["constant_target_integrated_stiffness_N_per_m"] == pytest.approx(expected)
    for level in record["levels"]:
        assert level["integrated_tangential_stiffness_N_per_m"] == pytest.approx(expected)
        level_spec = next(item for item in MESH_LEVELS if item.name == level["mesh"]["name"])
        nodes, _, faces, _, _ = _surface_geometry(level_spec)
        measured = reference_surface_areas(nodes, faces)
        assert {str(node): area for node, area in measured.items()} == pytest.approx(
            level["slave_tributary_areas_m2"]
        )


def test_meshes_are_positive_volume_and_first_normal_step_targets_contact() -> None:
    record = preflight_record()
    assert [level["mesh"]["name"] for level in record["levels"]] == [level.name for level in MESH_LEVELS]
    for level in record["levels"]:
        assert level["minimum_tet_volume_m3"] > 0.0
        assert level["total_volume_m3"] == pytest.approx(2.0 * WIDTH_M * HEIGHT_M)
        assert level["first_step_estimate_exceeds_gap"] is True
        assert level["master_normals"] == [[-1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]]


def test_load_cases_bracket_stick_and_slip_by_frozen_friction_capacity() -> None:
    record = preflight_record()
    for level in record["levels"]:
        load_cases = {case["case"]: case for case in level["load_cases"]}
        assert load_cases["stick_target"]["tangential_to_friction_capacity_ratio"] == pytest.approx(0.5)
        assert load_cases["slip_target"]["tangential_to_friction_capacity_ratio"] == pytest.approx(1.5)
        assert load_cases["stick_target"]["moment_about_origin_Nm"] == pytest.approx([-37.5, 250.0, -200.0])
        assert load_cases["slip_target"]["moment_about_origin_Nm"] == pytest.approx([-112.5, 250.0, 400.0])
        for case in load_cases.values():
            assert case["integrated_nodal_resultant_N"] == pytest.approx(case["resultant_N"])
            assert case["integrated_nodal_moment_about_origin_Nm"] == pytest.approx(
                case["moment_about_origin_Nm"]
            )
            assert len(case["nodal_loads"]) == level["contact_slave_node_count"]


def test_candidate_is_explicitly_preparation_only() -> None:
    record = preflight_record()
    assert record["status"] == "PREPARATION_ONLY_OWNER_REVIEW_REQUIRED"
    assert record["structural_solves_authorized"] is False
    assert record["production_mechanics_changed"] is False
