"""Tests for finite-strain TET4 stress recovery."""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest

from solveur.materials.solid import SolidMaterial
from solveur.verification.tet4_total_lagrangian_stress import (
    TotalLagrangianStressCampaign,
    analytical_svk_state,
)


def test_analytical_svk_state_matches_uniaxial_finite_strain_identity():
    material = SolidMaterial(E=210.0e9, nu=0.3)
    deformation = np.diag([1.1, 1.0, 1.0])
    state = analytical_svk_state(deformation, material)
    green_x = 0.5 * (1.1**2 - 1.0)
    lam = material.E * material.nu / ((1.0 + material.nu) * (1.0 - 2.0 * material.nu))
    mu = material.E / (2.0 * (1.0 + material.nu))

    assert state["green_lagrange_strain"][0, 0] == pytest.approx(green_x)
    assert state["second_piola_stress"][0, 0] == pytest.approx((lam + 2.0 * mu) * green_x)
    np.testing.assert_allclose(
        state["cauchy_stress"],
        deformation @ state["second_piola_stress"] @ deformation.T / 1.1,
    )


def test_analytical_svk_state_rejects_invalid_gradient():
    material = SolidMaterial(E=1.0e6, nu=0.3)
    with pytest.raises(ValueError, match="orientation-preserving"):
        analytical_svk_state(np.diag([-1.0, 1.0, 1.0]), material)


def test_stress_campaign_passes_and_writes_evidence(tmp_path):
    summary = TotalLagrangianStressCampaign(tmp_path).run()

    assert summary["status"] == "PASS_STRESS_ENERGY"
    assert max(row["pk2_l2_error"] for row in summary["levels"]) < 1.0e-12
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "report.md").is_file()
    assert (tmp_path / "stress_convergence.png").is_file()
    assert (tmp_path / "stress_deformation.png").is_file()
    manifest = json.loads((tmp_path / "vnv_manifest.json").read_text(encoding="utf-8"))
    assert manifest["study_id"] == TotalLagrangianStressCampaign.study_id
    for entry in manifest["files"]:
        assert hashlib.sha256((tmp_path / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
