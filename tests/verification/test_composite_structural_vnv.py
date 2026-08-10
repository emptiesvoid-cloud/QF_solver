from __future__ import annotations

import json

from solveur.verification.composite_structural import CompositeStructuralConvergenceCampaign


def test_composite_structural_convergence_campaign_passes(tmp_path):
    summary = CompositeStructuralConvergenceCampaign(tmp_path).run()
    assert summary["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert summary["reference_applicability"]["angle_ply_final_1d_reference_gap"] > 0.05
    assert summary["external_correlation"]["status"] == "PASS_SEPARATE_STUDY"
    for name in (
        "summary.json",
        "report.md",
        "composite_structural_convergence.png",
        "composite_bending_deformation.png",
        "vnv_manifest.json",
    ):
        assert (tmp_path / name).is_file()
        assert (tmp_path / name).stat().st_size > 0
    manifest = json.loads((tmp_path / "vnv_manifest.json").read_text(encoding="utf-8"))
    assert manifest["study_id"] == CompositeStructuralConvergenceCampaign.study_id
    assert len(manifest["files"]) == 4
