"""Targeted WP13 golden baseline and replay contracts."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_wp13_golden import replay, run
from solveur.verification.v2 import load_cases


ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "qualification/0_2_7/golden/cases.json"


def test_wp13_catalog_covers_the_declared_golden_set() -> None:
    cases = load_cases(CASES)
    assert len(cases) == 9
    assert len({case.case_id for case in cases}) == 9
    assert {case.element for case in cases} >= {"TET4", "TET10", "HEX8", "HEX20", "WEDGE6", "PYRAMID5"}
    assert all(case.provenance["source_snapshot"] == "eb2e6b89efbc6f3559a1ae439dad60d3cc47a210" for case in cases)
    assert all(case.provenance["artifact_classification"] == "CONTROLLED_PROOF" for case in cases)


def test_wp13_golden_run_and_replay_are_deterministic(tmp_path: Path) -> None:
    output = tmp_path / "golden-evidence.json"
    counts = run(output)
    assert counts == {"EXPECTED_FAILURE_PASS": 1, "PASS": 8}
    records = json.loads(output.read_text(encoding="utf-8"))
    assert len(records) == 9
    assert all(record["source_sha"] for record in records)
    assert all(record["result_digest"] for record in records)
    assert replay(output) == {"PASS": 9, "MISMATCH": 0}
