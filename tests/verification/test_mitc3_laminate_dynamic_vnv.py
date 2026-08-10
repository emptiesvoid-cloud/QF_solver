"""Regression tests for the bounded MITC3+ laminate V&V campaign."""

from __future__ import annotations

import json

from solveur.verification.mitc3_laminate_dynamic import (
    STUDY_ID,
    Mitc3LaminateDynamicStudy,
    write_mitc3_laminate_dynamic_evidence,
)


def test_mitc3_laminate_dynamic_campaign_passes_internal_invariants() -> None:
    summary = Mitc3LaminateDynamicStudy().run()

    assert summary["status"] == "PASS_INTERNAL"
    assert summary["maturity"] == "verified_development"
    assert all(summary["checks"].values())
    assert max(row["maximum_relative_displacement_error"] for row in summary["static"]["points"]) < 1.0e-10
    assert summary["modal"]["dynamic_reduction"]["condensed_drilling_dof_count"] > 0
    assert summary["newmark"]["points"][-1]["normalized_rms_error"] < 1.0e-2
    assert summary["harmonic"]["ply_count_at_first_frequency"] == 4


def test_mitc3_laminate_dynamic_evidence_is_complete(tmp_path) -> None:
    summary = write_mitc3_laminate_dynamic_evidence(tmp_path)

    assert summary["study_id"] == STUDY_ID
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / f"{STUDY_ID}.md").is_file()
    assert (tmp_path / f"{STUDY_ID}-newmark.png").stat().st_size > 1024
    assert (tmp_path / f"{STUDY_ID}-harmonic.png").stat().st_size > 1024
    assert (tmp_path / "vnv_manifest.json").is_file()
    persisted = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert persisted["checks"] == summary["checks"]
