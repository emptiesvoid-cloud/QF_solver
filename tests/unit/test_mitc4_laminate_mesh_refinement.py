from __future__ import annotations

import json
from pathlib import Path

from scripts.build_mitc4_laminate_mesh_refinement_report import build_report


CASE_IDS = ("cross_ply_0_90", "angle_ply_45", "off_axis_0_45_damped")
METRICS = ("modal_frequencies", "newmark_tip_history", "harmonic_tip_response")


def _write_summary(path: Path, value: float) -> None:
    cases = []
    for case_id in CASE_IDS:
        cases.append(
            {
                "id": case_id,
                "summary": {
                    "model": {"quad4_elements": 36},
                    "checks": [{"id": metric, "value": value} for metric in METRICS],
                },
            }
        )
    path.mkdir(parents=True)
    (path / "summary.json").write_text(json.dumps({"cases": cases}), encoding="utf-8")


def test_mesh_refinement_report_indexes_all_runs(tmp_path: Path) -> None:
    names = (
        "VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-021-20260809",
        "VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-021-20260809-h2",
        "VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-021-20260809-balanced",
        "VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-021-20260809-h4",
    )
    for index, name in enumerate(names, start=1):
        _write_summary(tmp_path / name, float(index) / 100.0)

    evidence, report = build_report(tmp_path)

    assert evidence["evidence_id"] == "VNV-MITC4-LAMINATE-MESH-REFINEMENT-022"
    assert len(evidence["rows"]) == len(CASE_IDS) * len(METRICS)
    assert "H4 équilibré" in report
