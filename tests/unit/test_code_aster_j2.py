"""Contracts for the Code_Aster VMIS_ISOT_LINE correlation."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.verification.code_aster_j2 import (
    CodeAsterJ2Campaign,
    code_aster_j2_commands,
    evaluate_code_aster_j2,
    unit_cube_tet4_mesh,
)


def test_code_aster_j2_commands_freeze_relation_and_small_strain_scope() -> None:
    nodes, _ = unit_cube_tet4_mesh()
    commands = code_aster_j2_commands(np.zeros_like(nodes))

    assert 'RELATION="VMIS_ISOT_LINE"' in commands
    assert 'DEFORMATION="PETIT"' in commands
    assert "ECRO_LINE" in commands
    assert 'getField("SIEF_ELGA"' in commands
    assert 'getField("VARI_ELGA"' in commands
    assert 'getValuesWithDescription("V1"' in commands


def test_code_aster_j2_evaluator_accepts_exact_independent_state() -> None:
    raw = {
        "stress_mpa": [300.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "stress_ranges_mpa": [[300.0, 300.0], [0.0, 0.0], [0.0, 0.0]] + [[0.0, 0.0]] * 3,
        "equivalent_plastic_strain": 0.001,
        "plastic_strain_range": [0.001, 0.001],
    }

    summary = evaluate_code_aster_j2(raw)

    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert summary["qf_solver"]["stress_mpa"][0] == pytest.approx(300.0)


def test_code_aster_j2_evaluator_rejects_non_homogeneous_stress() -> None:
    raw = {
        "stress_mpa": [300.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "stress_ranges_mpa": [[280.0, 320.0]] + [[0.0, 0.0]] * 5,
        "equivalent_plastic_strain": 0.001,
        "plastic_strain_range": [0.001, 0.001],
    }

    summary = evaluate_code_aster_j2(raw)

    assert summary["status"] == "FAIL"
    check = next(item for item in summary["checks"] if item["id"] == "code_aster_homogeneous_stress_range")
    assert check["status"] == "FAIL"


def test_code_aster_j2_cube_has_positive_tetrahedra() -> None:
    nodes, elements = unit_cube_tet4_mesh()
    determinants = np.linalg.det(nodes[elements[:, 1:]] - nodes[elements[:, :1]])

    assert elements.shape == (5, 4)
    assert np.all(determinants > 0.0)
    assert np.sum(determinants) / 6.0 == pytest.approx(1.0)


def test_code_aster_j2_theoretical_uniaxial_strains() -> None:
    campaign = CodeAsterJ2Campaign(".")
    axial, lateral = campaign._theoretical_strains()

    assert axial == pytest.approx(0.0024285714285714284)
    assert lateral == pytest.approx(-0.0009285714285714286)
    assert campaign.code_aster_tangent_mpa == pytest.approx(40_384.61538461538)
