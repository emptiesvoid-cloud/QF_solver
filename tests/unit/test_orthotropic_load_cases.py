from __future__ import annotations

import json
from pathlib import Path

from solveur.verification.orthotropic_load_cases import OrthotropicLoadCaseCampaign


def test_rotated_biaxial_and_combined_shear_campaign_passes(tmp_path: Path) -> None:
    summary = OrthotropicLoadCaseCampaign(tmp_path).run()
    assert summary["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert len(summary["rows"]) == 15
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert (tmp_path / "report.md").is_file()
    assert (tmp_path / "vnv_manifest.json").is_file()


def test_rotated_load_case_artifact_is_machine_readable(tmp_path: Path) -> None:
    OrthotropicLoadCaseCampaign(tmp_path).run()
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["load_cases"] == ["biaxial", "combined_shear", "mixed"]
    assert summary["orientations_deg"] == [0.0, 17.0, 31.0, 45.0, 73.0]
