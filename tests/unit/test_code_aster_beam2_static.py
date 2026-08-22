"""Regression checks for the archived BEAM2 static external evidence."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "qualification" / "maturity_evidence_0_2_1" / "beam2_static_code_aster"


def test_beam2_static_code_aster_campaign_is_archived_and_converged() -> None:
    summary = json.loads((EVIDENCE / "summary.json").read_text(encoding="utf-8"))

    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert summary["external_solver"]["version"] == "18.1.0"
    assert summary["model"]["same_mesh"] is True
    assert [row["element_count"] for row in summary["rows"]] == [4, 8, 16]
    assert summary["fine_relative_difference"] <= 0.02
    assert summary["qf_final_mesh_increment"] <= 0.02
    assert summary["code_aster_final_mesh_increment"] <= 0.02
    assert all(row["finite_results"] for row in summary["rows"])


def test_beam2_static_campaign_publishes_reviewable_artifacts() -> None:
    summary = json.loads((EVIDENCE / "summary.json").read_text(encoding="utf-8"))
    required = (
        "summary.json",
        "report.md",
        "beam2_static_code_aster.png",
        "vnv_manifest.json",
    )

    assert all((EVIDENCE / name).is_file() for name in required)
    assert all(item["status"] == "PASS" for item in summary["checks"])
