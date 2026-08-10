from __future__ import annotations

import json

from solveur.verification.composite_analytic import CompositeAnalyticalCampaign


def test_composite_analytical_campaign_passes_and_writes_review_artifacts(tmp_path):
    summary = CompositeAnalyticalCampaign(tmp_path).run()
    assert summary["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert len(summary["cases"]) == 6
    assert all(check["status"] == "PASS" for check in summary["checks"])
    for name in ("summary.json", "report.md", "composite_failure_envelopes.png", "vnv_manifest.json"):
        assert (tmp_path / name).is_file()
        assert (tmp_path / name).stat().st_size > 0
    manifest = json.loads((tmp_path / "vnv_manifest.json").read_text(encoding="utf-8"))
    assert manifest["study_id"] == CompositeAnalyticalCampaign.study_id
    assert len(manifest["files"]) == 3
