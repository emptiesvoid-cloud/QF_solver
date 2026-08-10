from __future__ import annotations

import json
from pathlib import Path

from solveur.verification.mitc3_campaign import Mitc3ValidationCampaign


def test_mitc3_quick_campaign_generates_reviewable_evidence(tmp_path: Path) -> None:
    summary = Mitc3ValidationCampaign(tmp_path, quick=True).run()

    assert summary["status"] == "PASS_WITH_WARNINGS"
    assert summary["failed_studies"] == []
    assert set(summary["warning_studies"]) == {
        "cook",
        "scordelis",
        "pinched",
    }
    assert summary["studies"]["shear_locking"]["status"] == "PASS"
    assert summary["studies"]["patch"]["constant_shear_interpolation_error"] <= 1.0e-10
    assert summary["studies"]["patch"]["affine_strain_error"] < 1.0e-12
    assert summary["studies"]["mixed_mesh"]["relative_error"] < 1.0e-12
    assert summary["studies"]["modal"]["max_relative_residual"] < 1.0e-8
    assert summary["studies"]["newmark"]["maximum_energy_drift"] < 1.0e-4
    assert summary["studies"]["harmonic"]["zero_frequency_static_error"] < 1.0e-8
    assert summary["studies"]["laminate"]["recovered_ply_points"] == 12

    stored = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert stored["campaign"] == "MITC3-PLUS-V1"
    assert (tmp_path / "vnv_manifest.json").is_file()
    for identifier in Mitc3ValidationCampaign.STUDY_IDS:
        assert (tmp_path / f"{identifier}.md").is_file()
