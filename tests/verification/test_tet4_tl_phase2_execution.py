"""Regression checks for the executed TET4-TL Phase-2 probe."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_tet4_tl_large_phase2 import estimate_peak_memory


ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATHS = [
    ROOT / "results" / "VNV-TET4-TL-PHASE2-LARGE-011" / "summary.json",
    ROOT / "results" / "VNV-TET4-TL-PHASE2-LARGE-012" / "summary.json",
]


def test_large_tet4_tl_probe_is_not_presented_as_mechanical_pass() -> None:
    for path in SUMMARY_PATHS:
        summary = json.loads(path.read_text(encoding="utf-8"))
        assert summary["status"] == "RESOURCE_LIMIT_ABORTED"
        assert summary["mechanical_result_available"] is False
        assert summary["promotion_impact"] == "TET4 total-lagrangian remains research / more_evidence_required."


def test_large_tet4_tl_probe_memory_estimate_is_significant() -> None:
    estimated = estimate_peak_memory(1_152_000)
    assert estimated > 10 * 1_000_000_000
