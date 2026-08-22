from __future__ import annotations

import json
from pathlib import Path

from solveur.verification.orthotropic_large_static import OrthotropicLargeStaticCampaign


def test_orthotropic_large_static_campaign_passes(tmp_path: Path) -> None:
    summary = OrthotropicLargeStaticCampaign(tmp_path / "study", nx=3, ny=2, nz=2).run()

    assert summary["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert all(item["status"] == "PASS" for item in summary["checks"])
    assert json.loads((tmp_path / "study" / "summary.json").read_text(encoding="utf-8"))["study_id"] == summary["study_id"]
    assert (tmp_path / "study" / "report.md").is_file()
    assert (tmp_path / "study" / "vnv_manifest.json").is_file()
