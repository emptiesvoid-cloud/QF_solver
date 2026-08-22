"""Regression checks for the archived MITC3+ dynamic refinement ledger."""

from __future__ import annotations

import json
from pathlib import Path

from solveur.verification.code_aster_mitc3_dynamic_refinement import load_refinement_summary


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "qualification" / "maturity_evidence_0_2_1" / "mitc3_dynamic_refinement" / "summary.json"
EVIDENCE = ROOT / "qualification" / "maturity_evidence_0_2_1" / "mitc3_dynamic_refinement"
EXTENDED_EVIDENCE = ROOT / "qualification" / "vnv" / "external" / "code_aster_mitc3_laminate_dynamic_refinement_022" / "reference"
LARGE_MESH_EVIDENCE = ROOT / "qualification" / "vnv" / "external" / "code_aster_mitc3_laminate_dynamic_refinement_037" / "reference"


def test_mitc3_dynamic_refinement_ledger_has_three_levels_and_passes() -> None:
    summary = load_refinement_summary(LEDGER)

    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert summary["comparison_basis"]["same_geometry"] is True
    assert len(summary["mesh_levels"]) >= 3
    assert all(level["status"] == "PASS_EXTERNAL_CORRELATION" for level in summary["mesh_levels"])
    assert all(check["status"] == "PASS" for check in summary["checks"])


def test_mitc3_dynamic_refinement_artifacts_are_present() -> None:
    summary = json.loads(LEDGER.read_text(encoding="utf-8"))

    assert (EVIDENCE / "report.md").is_file()
    assert (EVIDENCE / "mesh_frequency_refinement.png").stat().st_size > 0
    for level in summary["mesh_levels"]:
        directory = EVIDENCE / f"mesh_{level['nx']}x{level['ny']}"
        assert (directory / "summary.json").is_file()
        assert (directory / "comparison.png").stat().st_size > 0


def test_mitc3_laminate_dynamic_48x12_evidence_keeps_one_percent_gate() -> None:
    summary = json.loads((EXTENDED_EVIDENCE / "summary.json").read_text(encoding="utf-8"))

    assert summary["study_id"] == "VNV-MITC3-LAMINATE-DYNAMICS-REFINEMENT-CODEASTER-DST-022"
    assert summary["mesh_levels"][-1]["nx"] == 48
    assert summary["mesh_levels"][-1]["ny"] == 12
    assert summary["checks"][0]["status"] == "FAIL"
    assert summary["checks"][1]["status"] == "FAIL"
    assert summary["checks"][2]["status"] == "FAIL"
    assert all(check["status"] == "PASS" for check in summary["checks"][3:])
    assert (EXTENDED_EVIDENCE / "mitc3_laminate_dynamic_refinement.png").stat().st_size > 0


def test_mitc3_laminate_dynamic_64x16_diagnostic_does_not_promote_stable() -> None:
    summary = json.loads((LARGE_MESH_EVIDENCE / "summary.json").read_text(encoding="utf-8"))

    assert summary["model"]["mesh"] == [64, 16]
    assert summary["model"]["tria3_elements"] == 2048
    assert max(summary["modal"]["relative_differences"]) > 0.01
    assert summary["checks"][0]["value"] > 0.01
    assert summary["checks"][1]["value"] > 0.01
    assert summary["checks"][2]["value"] > 0.01
    report = (LARGE_MESH_EVIDENCE / "report.md").read_text(encoding="utf-8")
    assert "BLOCKED_OVER_1_PERCENT" in report
    assert (LARGE_MESH_EVIDENCE / "mitc3_laminate_code_aster_comparison.png").stat().st_size > 0
