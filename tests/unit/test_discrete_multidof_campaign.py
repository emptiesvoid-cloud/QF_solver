"""Tests for the independent multi-DOF discrete campaign."""

from __future__ import annotations

from pathlib import Path

from solveur.verification.discrete_multidof_campaign import (
    run_discrete_multidof_campaign,
    write_discrete_multidof_campaign,
)


def test_multidof_discrete_static_modal_newmark_harmonic_pass() -> None:
    report = run_discrete_multidof_campaign()
    assert report["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert report["model"]["free_translation_dofs"] == 6
    assert all(check["status"] == "PASS" for check in report["checks"])
    assert report["modal"]["reference_mass_positive"] is True
    assert report["modal"]["reference_stiffness_positive"] is True


def test_multidof_discrete_campaign_writes_traceable_artifacts(tmp_path: Path) -> None:
    report = write_discrete_multidof_campaign(tmp_path)
    assert report["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "report.md").is_file()
    assert (tmp_path / "discrete_multidof_results.png").stat().st_size > 1000
    assert (tmp_path / "vnv_manifest.json").is_file()
