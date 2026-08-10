from __future__ import annotations

import json

from solveur.verification.composite_curved_assembly import CompositeCurvedAssemblyCampaign


def test_composite_curved_assembly_campaign_passes(tmp_path):
    summary = CompositeCurvedAssemblyCampaign(tmp_path).run()
    assert summary["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert summary["models"]["curved_panel_distorted"]["mesh_status"] in {"PASS", "WARNING"}
    assert summary["models"]["curved_panel_distorted"]["run_verdict"] == "FAIL"
    for name in (
        "summary.json",
        "report.md",
        "composite_curved_assembly_convergence.png",
        "composite_curved_assembly_meshes.png",
        "vnv_manifest.json",
    ):
        assert (tmp_path / name).is_file()
        assert (tmp_path / name).stat().st_size > 0
    manifest = json.loads((tmp_path / "vnv_manifest.json").read_text(encoding="utf-8"))
    assert manifest["study_id"] == CompositeCurvedAssemblyCampaign.study_id
    assert len(manifest["files"]) == 4
