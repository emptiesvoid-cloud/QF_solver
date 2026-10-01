"""WP08-D Phase-0 contract and no-solve preparation checks."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.prepare_wp08d_structural_reference import (
    FRICTION_COEFFICIENT,
    GAP_TOLERANCE,
    MESH_LEVELS,
    TANGENTIAL_STIFFNESS,
    consistent_surface_traction,
    generate_mesh,
    load_contract,
    mesh_contract,
    no_contact_well_posedness,
    phase0_execution_guard,
)


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "qualification" / "0_2_9" / "wp08d_structural_reference_contract.json"


def test_three_mesh_levels_are_deterministic_and_well_formed() -> None:
    expected = (
        ("M1", 16, 12, 48, 4, 2, 4),
        ("M2", 49, 96, 147, 12, 2, 16),
        ("M3", 229, 768, 687, 40, 2, 64),
    )
    for level, expected_row in zip(MESH_LEVELS, expected):
        first = generate_mesh(level)
        second = generate_mesh(level)
        report = mesh_contract(first)
        assert (
            report["level"],
            report["nodes"],
            report["elements"],
            report["dofs"],
            report["contact_slave_count"],
            report["master_facet_count"],
            report["top_face_count"],
        ) == expected_row
        assert report["finite_coordinates"] is True
        assert report["positive_reference_volumes"] is True
        assert report["master_projection_coverage"] is True
        np.testing.assert_array_equal(first.nodes, second.nodes)
        assert first.elements == second.elements
        assert first.slave_face_map == second.slave_face_map


def test_consistent_surface_traction_preserves_resultants_and_moments() -> None:
    for level in MESH_LEVELS:
        mesh = generate_mesh(level)
        loads = load_contract(mesh)
        for name in ("normal", "tangential"):
            assert loads[name]["resultant"]["status"] == "PASS"
            assert loads[name]["moment"]["status"] == "PASS"
            direct = consistent_surface_traction(mesh, mesh.top_faces, loads[name]["resultant"]["expected"])
            np.testing.assert_allclose(direct["resultant"], loads[name]["resultant"]["expected"], rtol=0.0, atol=2.0e-13)


def test_load_contract_is_level_invariant() -> None:
    reports = [load_contract(generate_mesh(level)) for level in MESH_LEVELS]
    for name in ("normal", "tangential"):
        reference_resultant = reports[0][name]["resultant"]["expected"]
        reference_moment = reports[0][name]["moment"]["expected"]
        for report in reports:
            np.testing.assert_allclose(report[name]["resultant"]["observed"], reference_resultant, rtol=0.0, atol=2.0e-13)
            np.testing.assert_allclose(report[name]["moment"]["observed"], reference_moment, rtol=0.0, atol=2.0e-13)


def test_phase0_no_contact_precheck_is_well_posed_without_a_solve() -> None:
    result = no_contact_well_posedness(generate_mesh(MESH_LEVELS[0]))
    assert result["status"] == "PASS"
    assert result["reduced_dof"] == 24
    assert result["finite_matrix"] is True
    assert result["contact_terms_included"] is False
    assert result["solve_performed"] is False
    assert result["minimum_eigenvalue"] > result["numerical_zero_threshold"]


def test_phase0_execution_guard_defaults_disabled_and_fails_closed() -> None:
    phase0_execution_guard()
    with pytest.raises(RuntimeError, match="Phase-1 authorization"):
        phase0_execution_guard(structural_solves_enabled=True)
    with pytest.raises(RuntimeError, match="Phase-1 authorization"):
        phase0_execution_guard(external_solver_enabled=True)


def test_contract_freezes_scope_and_execution_guard() -> None:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["status"] == "PREPARATION_ONLY"
    assert payload["execution_guard"]["structural_solves_enabled"] is False
    assert payload["execution_guard"]["external_solver_enabled"] is False
    assert payload["scope"]["route"] == "linear_static"
    assert payload["scope"]["element_family"] == "TET4"
    assert payload["friction"]["mu"] == FRICTION_COEFFICIENT
    assert payload["friction"]["tangential_stiffness"] == TANGENTIAL_STIFFNESS
    assert payload["friction"]["gap_tolerance"] == GAP_TOLERANCE
    assert payload["preflight"]["structural_contact_results_generated"] is False
    assert payload["governance"]["wp08_d_formal_points"] == 0
