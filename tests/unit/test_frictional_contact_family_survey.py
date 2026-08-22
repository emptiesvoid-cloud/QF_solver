"""Tests for the three-family frictional-contact evidence survey."""

from __future__ import annotations

import json
from pathlib import Path

from solveur.verification.frictional_contact_family_survey import (
    FrictionalContactFamilySurvey,
)


def test_family_survey_exercises_three_geometries_and_sliding(tmp_path: Path) -> None:
    summary = FrictionalContactFamilySurvey(tmp_path).run()

    assert summary["status"] == "PASS_INTERNAL"
    assert summary["geometry_family_count"] == 3
    assert summary["mesh_policy"]["mesh_level_count_per_family"] == 3
    assert summary["mesh_policy"]["status"] == "PASS_INTERNAL"
    assert all(case["finite_response"] for case in summary["families"].values())
    assert any("slip" in case["states"] for case in summary["families"].values())
    assert all(check["status"] == "PASS" for check in summary["checks"])


def test_family_survey_writes_machine_readable_and_visual_evidence(tmp_path: Path) -> None:
    FrictionalContactFamilySurvey(tmp_path).run()

    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["campaign_id"] == "VNV-CONTACT-FRICTION-FAMILIES-004"
    assert (tmp_path / "report.md").is_file()
    assert (tmp_path / "frictional_contact_family_survey.png").stat().st_size > 0
    assert (tmp_path / "vnv_manifest.json").is_file()
