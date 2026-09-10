"""Integrity contract for the final WP03 Owner-gate decision."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OWNER_GATE = ROOT / "qualification/0_2_8/wp03_owner_gate_final.json"
FINAL_MATRIX = ROOT / "qualification/0_2_8/wp03_maturity_matrix.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_wp03_owner_gate_pins_technical_evidence_and_finalizes_only_allowed_routes() -> None:
    owner = json.loads(OWNER_GATE.read_text(encoding="utf-8"))
    matrix = json.loads(FINAL_MATRIX.read_text(encoding="utf-8"))
    assert owner["audited_commit"] == "6895576206e163cfb9999ba74f5b4cbf081b1c98"
    assert owner["authorization"]["owner_identity"] is None
    assert owner["summary"] == {
        "approved_with_limitations": 7,
        "rejected_promotions": 1,
        "qualified_bounded_total": 7,
        "experimental_total": 1,
        "not_qualified_total": 0,
    }
    for item in owner["technical_evidence"]:
        assert _sha256(ROOT / item["path"]) == item["sha256"]
    decisions = owner["decisions"]
    assert decisions["DISCRETE_NEWMARK"] == {
        "owner_decision": "REJECT",
        "promotion_applied": False,
        "resulting_maturity": "EXPERIMENTAL",
        "rejected_gate": "coarse.max_phase_error_rad",
        "observed_value_rad": 0.012895220110156203,
        "predeclared_limit_rad": 0.012,
        "limitations": ["The gate and coarse time grid are retained unchanged. No promotion is authorized."],
    }
    approved = {name for name, decision in decisions.items() if decision["promotion_applied"]}
    assert len(approved) == 7
    assert all(decisions[name]["owner_decision"] == "APPROVE_WITH_LIMITATIONS" for name in approved)
    assert matrix["status"] == "OWNER_GATE_FINALIZED"
    assert matrix["summary"] == {
        "QUALIFIED_BOUNDED": 7,
        "EXPERIMENTAL": 1,
        "NOT_QUALIFIED": 0,
        "public_maturity_relabels_applied": 7,
    }
    matrix_by_source = {entry["source_record"]: entry for entry in matrix["decisions"]}
    assert matrix_by_source["COMB-DISCRETE-newmark_transient"]["owner_gate"] == "REJECTED"
    assert matrix_by_source["COMB-DISCRETE-newmark_transient"]["public_maturity"] == "EXPERIMENTAL"
    for source, entry in matrix_by_source.items():
        if source != "COMB-DISCRETE-newmark_transient":
            assert entry["decision"] == "QUALIFIED_BOUNDED"
            assert entry["public_maturity"] == "QUALIFIED_BOUNDED"
            assert entry["owner_gate"] == "APPROVED_WITH_LIMITATIONS"
