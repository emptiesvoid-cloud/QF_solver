"""Regression tests for the extended MITC3+ linear-dynamics campaign."""

from __future__ import annotations

import json

from solveur.verification.mitc3_dynamic_extended import (
    CAMPAIGN_ID,
    Mitc3DynamicExtendedStudy,
    write_mitc3_dynamic_extended_evidence,
)


def test_extended_mitc3_dynamic_campaign_passes() -> None:
    summary = Mitc3DynamicExtendedStudy().run()

    assert summary["status"] == "PASS_INTERNAL"
    assert all(summary["checks"].values())
    assert summary["studies"]["free_free"]["metrics"]["rigid_to_first_elastic_ratio"] < 1.0e-8
    assert summary["studies"]["sparse_modal"]["large_sparse"]["dense_conversion_used"] is False
    assert summary["studies"]["curved_dynamic"]["newmark"][-1]["normalized_rms_error"] < 1.0e-2


def test_extended_mitc3_dynamic_writer_emits_reports_and_figures(tmp_path) -> None:
    summary = write_mitc3_dynamic_extended_evidence(tmp_path)

    assert summary["campaign"] == CAMPAIGN_ID
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "report.md").is_file()
    assert len(list(tmp_path.glob("*.png"))) == 3
    assert all(path.stat().st_size > 1024 for path in tmp_path.glob("*.png"))
    persisted = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert persisted["status"] == "PASS_INTERNAL"
