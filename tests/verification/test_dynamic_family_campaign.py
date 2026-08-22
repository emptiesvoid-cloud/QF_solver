"""End-to-end mechanical checks for each newly scoped linear dynamic family."""

from __future__ import annotations

import json

import pytest

from solveur.verification.dynamic_family_campaign import (
    SUPPORTED_FAMILIES,
    LinearDynamicFamilyCampaign,
)


@pytest.mark.parametrize("family", SUPPORTED_FAMILIES)
def test_linear_dynamic_family_campaign_is_reproducible(tmp_path, family: str) -> None:
    summary = LinearDynamicFamilyCampaign(family, tmp_path / family).run()

    assert summary["status"] == "PASS"
    assert all(study["status"] == "PASS" for study in summary["studies"].values())
    assert (tmp_path / family / "summary.json").is_file()
    assert (tmp_path / family / "report.md").is_file()
    assert (tmp_path / family / "vnv_manifest.json").is_file()
    stored = json.loads((tmp_path / family / "summary.json").read_text(encoding="utf-8"))
    assert stored["study_id"] == f"VNV-{family}-LINEAR-DYNAMICS-001"
    assert stored["studies"]["harmonic"]["zero_frequency_static_error"] <= 1.0e-8
    assert stored["studies"]["newmark"]["maximum_energy_drift"] <= 1.0e-4
    assert stored["studies"]["newmark"]["time_refinement_error_max"] <= 1.0e-2
    assert stored["studies"]["newmark"]["time_level_count"] == 4
