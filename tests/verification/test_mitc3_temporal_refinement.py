"""Tests for the isolated MITC3+ Newmark temporal refinement campaign."""

from __future__ import annotations

import json

from solveur.verification.mitc3_temporal_refinement import (
    STUDY_ID,
    Mitc3TemporalRefinementStudy,
    write_mitc3_temporal_refinement_evidence,
)


def test_mitc3_temporal_refinement_passes_at_80_160_320() -> None:
    summary = Mitc3TemporalRefinementStudy().run()

    assert summary["study_id"] == STUDY_ID
    assert summary["status"] == "PASS_INTERNAL"
    assert summary["provenance"]["steps_per_period"] == [80, 160, 320]
    assert summary["checks"]["strictly_decreasing_error"]
    assert summary["time_levels"][-1]["normalized_rms_error"] <= 1.0e-2


def test_mitc3_temporal_refinement_rejects_insufficient_levels() -> None:
    try:
        Mitc3TemporalRefinementStudy(steps_per_period=(40, 80))
    except ValueError as error:
        assert "three" in str(error)
    else:
        raise AssertionError("three temporal levels are required")


def test_mitc3_temporal_refinement_writes_complete_bundle(tmp_path) -> None:
    summary = write_mitc3_temporal_refinement_evidence(tmp_path)

    assert summary["status"] == "PASS_INTERNAL"
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / f"{STUDY_ID}.md").is_file()
    assert (tmp_path / f"{STUDY_ID}-convergence.png").stat().st_size > 1024
    assert (tmp_path / "vnv_manifest.json").is_file()
    persisted = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert persisted["checks"] == summary["checks"]

