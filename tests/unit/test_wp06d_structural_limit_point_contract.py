"""No-solve contract checks for the WP06-D structural limit-point plan."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from scripts import prepare_wp06d_structural_limit_point as guard


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "qualification" / "0_2_9" / "wp06d_structural_limit_point_contract.json"


def _contract() -> dict[str, Any]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_wp06d_contract_is_phase0_and_fail_closed() -> None:
    contract = _contract()
    assert contract["phase"] == "PHASE_0_PREPARATION"
    assert contract["execution_guard"] == {
        "phase": "PHASE_0_PREPARATION",
        "structural_solves_enabled": False,
        "reference_solver_enabled": False,
        "external_solver_enabled": False,
        "owner_authorization_required_for_phase_1": True,
        "governing_branch_integration_required": True,
        "guard_module": "scripts/prepare_wp06d_structural_limit_point.py",
    }
    with pytest.raises(RuntimeError, match="Phase-0 preparation only"):
        guard.assert_phase0_guard()


def test_wp06d_mesh_series_has_exact_frozen_levels() -> None:
    levels = _contract()["mesh_series"]
    assert levels == [
        {
            "level": "M1",
            "parent_cells": "two parent TET4 elements",
            "nodes": 5,
            "elements": 2,
            "dofs": 15,
            "minimum_reference_tet_volume": 0.0008333333333333333,
            "resource_class": "TINY",
            "expected_accepted_steps": 80,
            "maximum_retries": 8,
        },
        {
            "level": "M2",
            "parent_cells": "one conforming 8-subtet red refinement of M1",
            "nodes": 14,
            "elements": 16,
            "dofs": 42,
            "minimum_reference_tet_volume": 0.00010416666666666667,
            "resource_class": "LIGHT",
            "expected_accepted_steps": 80,
            "maximum_retries": 8,
        },
        {
            "level": "M3",
            "parent_cells": "two conforming 8-subtet red refinements of M1",
            "nodes": 55,
            "elements": 128,
            "dofs": 165,
            "minimum_reference_tet_volume": 0.00001302083333333333,
            "resource_class": "LIGHT",
            "expected_accepted_steps": 80,
            "maximum_retries": 8,
        },
    ]


@pytest.mark.parametrize(
    ("level", "node_count", "element_count", "dof_count"),
    [("M1", 5, 2, 15), ("M2", 14, 16, 42), ("M3", 55, 128, 165)],
)
def test_wp06d_refinement_generates_positive_deterministic_meshes(
    level: str, node_count: int, element_count: int, dof_count: int
) -> None:
    nodes_a, elements_a = guard.generate_mesh(level)
    nodes_b, elements_b = guard.generate_mesh(level)
    assert nodes_a.shape == (node_count, 3)
    assert len(elements_a) == element_count
    assert nodes_a.size == dof_count
    assert np.array_equal(nodes_a, nodes_b)
    assert elements_a == elements_b
    assert np.all(np.isfinite(nodes_a))
    assert all(guard._signed_volume(nodes_a, element) > 0.0 for element in elements_a)


def test_wp06d_boundary_sets_are_deterministic_and_load_node_persists() -> None:
    expected_face_nodes = {
        "M1": (2, 3, 4),
        "M2": (2, 3, 4, 11, 12, 13),
        "M3": (2, 3, 4, 11, 12, 13, 22, 23, 26, 27, 30, 31, 52, 53, 54),
    }
    for level in ("M1", "M2", "M3"):
        nodes_a, _ = guard.generate_mesh(level)
        nodes_b, _ = guard.generate_mesh(level)
        face_a = guard.symmetry_face_nodes(nodes_a)
        assert face_a == guard.symmetry_face_nodes(nodes_b)
        assert face_a == expected_face_nodes[level]
        assert 4 in face_a
        assert face_a == tuple(sorted(face_a))
        assert tuple(index for index in (0, 1) if index < len(nodes_a)) == (0, 1)


@pytest.mark.parametrize("level", ["M1", "M2", "M3"])
def test_wp06d_point_load_has_frozen_resultant_and_origin_moment(level: str) -> None:
    nodes, _ = guard.generate_mesh(level)
    loads, resultant, moment = guard.assemble_reference_load(nodes)
    assert np.array_equal(np.flatnonzero(np.linalg.norm(loads, axis=1)), np.asarray([4]))
    assert np.array_equal(resultant, guard.TARGET_RESULTANT)
    assert np.array_equal(moment, np.zeros(3))


def test_wp06d_load_resultant_and_origin_moment_are_mesh_independent() -> None:
    load = _contract()["benchmark"]["reference_load"]
    assert load["resultant"] == [0.0, 0.0, -1.0]
    assert load["expected_origin_moment"] == [0.0, 0.0, 0.0]
    assert load["physical_load_region"] == "the zero-dimensional material point X=[0,0,0.25] represented by parent node 4"
    assert load["application"].startswith("fixed geometric point load")


def test_wp06d_thresholds_and_reference_are_predeclared() -> None:
    contract = _contract()
    thresholds = contract["metrics_and_thresholds"]
    assert thresholds["limit_point"] == {
        "displacement_error": 0.03,
        "lambda_error": 0.03,
        "post_limit_path_error": 0.05,
    }
    assert thresholds["mesh_m2_to_m3"]["u_monitor"] == 0.03
    assert thresholds["equilibrium"]["force_relative"] == 1.0e-8
    assert thresholds["equilibrium"]["moment_relative"] == 1.0e-8
    reference = contract["reference_path"]["primary"]
    assert reference["production_arclength_routines_called"] is False
    assert reference["production_mechanics_routines_called"] is False
    assert reference["status_before_phase_1"] == "PLAN_ONLY_NO_REFERENCE_RESULT"


def test_wp06d_path_parameter_is_cumulative_arc_measure() -> None:
    path = _contract()["path_comparison"]
    assert path["s0"] == 0.0
    assert path["load_scale"] == 1.0
    assert path["stations"] == [0.2, 0.4, 0.6, 0.8, 1.0]
    assert "cumulative" in path["parameter"]
    assert "s_i / s_final" in path["normalization"]
    assert path["q_limit"] == "q at the accepted state selected by the first local maximum lambda(q)"
    assert path["post_limit_displacement"] == "q at s_norm=1.0 minus q_limit"


def test_wp06d_continuation_and_solver_policy_are_bounded() -> None:
    contract = _contract()
    continuation = contract["continuation_policy"]
    assert continuation["formulation"] == "SPHERICAL_ARC_LENGTH_CUSTOM"
    assert continuation["adaptive_radius"] is False
    assert continuation["initial_radius"] == continuation["maximum_radius"] == 0.02
    assert continuation["minimum_radius"] == 2.0e-6
    assert continuation["maximum_accepted_steps"] == 80
    assert contract["linear_solver_policy"]["predictor_backend"] == "serial_sparse_direct"
    assert contract["linear_solver_policy"]["corrector_backend"] == "serial_sparse_direct"
    assert contract["linear_solver_policy"]["fallback_policy"] == "NONE; unsupported or failed augmented solve is typed and fail-closed"


def test_wp06d_validate_contract_only_reads_metadata() -> None:
    summary = guard.validate_contract()
    assert summary["record_id"] == "QF-0.2.9-WP06D-STRUCTURAL-LIMIT-POINT-CONTRACT-001"
    assert summary["mesh_levels"] == ["M1", "M2", "M3"]
    assert summary["structural_solves_enabled"] is False
    assert summary["external_solver_enabled"] is False
