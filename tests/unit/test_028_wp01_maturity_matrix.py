"""Contracts for the 0.2.8 WP01 non-promotional maturity baseline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_REGISTRY = ROOT / "qualification" / "0_2_7" / "capability_registry_v2.json"
MATRIX = ROOT / "qualification" / "0_2_8" / "wp01_maturity_matrix.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp01_covers_each_active_027_combination_exactly_once() -> None:
    source = _load(SOURCE_REGISTRY)
    matrix = _load(MATRIX)
    source_ids = [
        str(record["capability_id"])
        for record in source["records"]  # type: ignore[index]
        if record["record_kind"] == "combination"
    ]
    matrix_ids = [str(record["source_record"]) for record in matrix["combinations"]]  # type: ignore[index]

    assert len(source_ids) == 46
    assert set(matrix_ids) == set(source_ids)
    assert len(matrix_ids) == len(set(matrix_ids))


def test_wp01_dispositions_are_exhaustive_and_non_promotional() -> None:
    matrix = _load(MATRIX)
    allowed = set(matrix["policy"]["allowed_dispositions"])  # type: ignore[index]
    records = matrix["combinations"]  # type: ignore[index]
    summary = matrix["summary"]  # type: ignore[index]

    assert {record["disposition"] for record in records} <= allowed
    assert sum(int(summary[state]) for state in allowed) == 46
    assert summary["PROMOTABLE_WITH_EXISTING_EVIDENCE"] == 0
    assert matrix["baseline"]["main_sha"] == "9a0d2ab8e8fc3509f0f7ea53bb93db0bd7d99ca5"  # type: ignore[index]
    assert matrix["baseline"]["source_registry_sha256"] == hashlib.sha256(SOURCE_REGISTRY.read_bytes()).hexdigest()  # type: ignore[index]


def test_wp01_candidate_records_define_a_future_gate_without_promoting() -> None:
    matrix = _load(MATRIX)
    plans = {plan["id"]: plan for plan in matrix["candidate_requirements"]}  # type: ignore[index]
    candidates = [
        record
        for record in matrix["combinations"]  # type: ignore[index]
        if record["disposition"] in {"NEEDS_MINOR_VNV", "NEEDS_MAJOR_VNV", "NOT_QUALIFIED_TO_CLOSE"}
    ]

    for record in candidates:
        plan = plans[record["candidate_plan"]]
        assert all(plan[field] for field in ("proof_missing", "tests_to_add", "oracle", "tolerance", "exit_gate", "risk"))
    assert plans["CAND-WEDGE6-STATIC"]["risk"] == "HIGH"
    assert plans["CAND-HEX8-BUCKLING"]["exit_gate"].startswith("Three-level refinement")
