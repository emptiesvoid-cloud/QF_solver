from __future__ import annotations

import json

from solveur.verification.composite_ply_stress import CompositePlyStressCampaign


def test_composite_ply_stress_campaign_passes(tmp_path):
    summary = CompositePlyStressCampaign(tmp_path).run()
    assert summary["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert summary["models"]["combined"][-1]["stress_l2_error"] < 1.0e-3
    assert summary["models"]["combined_distorted"][-1]["stress_l2_error"] < 2.0e-2
    for name in (
        "summary.json",
        "report.md",
        "ply_stress_convergence.png",
        "ply_stress_profile.png",
        "vnv_manifest.json",
    ):
        assert (tmp_path / name).is_file()
        assert (tmp_path / name).stat().st_size > 0
    manifest = json.loads((tmp_path / "vnv_manifest.json").read_text(encoding="utf-8"))
    assert manifest["study_id"] == CompositePlyStressCampaign.study_id
    assert len(manifest["files"]) == 4
