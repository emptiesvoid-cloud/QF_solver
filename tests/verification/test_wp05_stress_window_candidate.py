"""Tests for the non-binding WP05-D exact stress-window candidate."""

from __future__ import annotations

import json

import numpy as np
import pytest

from scripts.wp05_cd_structural_harness import CONTRACT_JSON, MESH_LEVELS, build_mesh
from scripts.wp05_stress_window_candidate import clipped_reference_window_sigma_xx_hex20
from solveur.materials.solid import SolidMaterial


ROOT = CONTRACT_JSON.parents[2]
CANDIDATE_JSON = ROOT / "qualification" / "0_2_9" / "wp05_cd_stress_window_remediation_candidate.json"


def _material() -> SolidMaterial:
    return SolidMaterial(E=1.0e6, nu=0.30)


def _uniform_axial_displacement(mesh, axial_strain: float) -> np.ndarray:
    displacement = np.zeros((mesh.nodes, 3), dtype=float)
    displacement[:, 0] = axial_strain * mesh.coordinates[:, 0]
    return displacement


def test_candidate_contract_preserves_inputs_and_frozen_stress_limit() -> None:
    frozen = json.loads(CONTRACT_JSON.read_text(encoding="utf-8"))
    candidate = json.loads(CANDIDATE_JSON.read_text(encoding="utf-8"))
    assert candidate["status"] == "CANDIDATE_REQUIRES_OWNER_APPROVAL_NO_QUALIFICATION_EXECUTION"
    assert candidate["preserves_historical_formal_evidence"] is True
    assert candidate["physical_inputs"]["geometry"] == frozen["benchmark"]["geometry"] | {"reference_volume": 1.0}
    assert candidate["observable"]["normalized_region"] == frozen["observables"]["representative_cauchy_sigma_xx"]["normalized_region"]
    assert candidate["unchanged_qualification_policy"]["h2_to_h3_representative_sigma_xx_relative_limit"] == 0.08


@pytest.mark.parametrize("level", MESH_LEVELS)
def test_exact_candidate_window_has_the_declared_reference_volume(level) -> None:
    mesh = build_mesh("HEX20", level)
    result = clipped_reference_window_sigma_xx_hex20(mesh, np.zeros((mesh.nodes, 3)), _material())
    assert result["status"] == "CANDIDATE_POSTPROCESS_ONLY_NOT_FORMAL"
    assert result["reference_volume"] == pytest.approx(0.03, abs=1.0e-14)
    assert result["reference_volume_absolute_error"] <= 1.0e-14
    assert result["representative_sigma_xx"] == pytest.approx(0.0, abs=1.0e-10)


def test_affine_deformation_observable_is_partition_invariant() -> None:
    values = []
    volumes = []
    for level in MESH_LEVELS:
        mesh = build_mesh("HEX20", level)
        result = clipped_reference_window_sigma_xx_hex20(mesh, _uniform_axial_displacement(mesh, 0.01), _material())
        values.append(result["representative_sigma_xx"])
        volumes.append(result["reference_volume"])
    np.testing.assert_allclose(values, [values[0]] * len(values), rtol=0.0, atol=1.0e-8)
    np.testing.assert_allclose(volumes, [0.03] * len(volumes), rtol=0.0, atol=1.0e-14)


def test_candidate_rejects_a_non_hex20_mesh() -> None:
    mesh = build_mesh("TET10", "H1")
    with pytest.raises(ValueError, match="HEX20"):
        clipped_reference_window_sigma_xx_hex20(mesh, np.zeros((mesh.nodes, 3)), _material())
