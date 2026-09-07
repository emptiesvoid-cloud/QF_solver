"""WP04 Owner-gate and 46-combination reconciliation contracts."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "qualification" / "0_2_7" / "capability_registry_v2.json"
WP03_MATRIX = ROOT / "qualification" / "0_2_8" / "wp03_maturity_matrix.json"
WP04_MATRIX = ROOT / "qualification" / "0_2_8" / "wp04_maturity_matrix.json"
OWNER_GATE = ROOT / "qualification" / "0_2_8" / "wp04_owner_gate_final.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_wp04_owner_gate_reconciles_all_source_combinations() -> None:
    source = _load(SOURCE)
    wp03 = _load(WP03_MATRIX)
    wp04 = _load(WP04_MATRIX)
    owner = _load(OWNER_GATE)

    combinations = [row for row in source["records"] if row["record_kind"] == "combination"]
    assert len(combinations) == 46
    assert {row["capability_id"] for row in combinations} == set(source["combination_record_ids"])
    assert Counter(row["qualification_state"] for row in combinations) == Counter(
        {"QUALIFIED_BOUNDED": 20, "EXPERIMENTAL": 25, "NOT_QUALIFIED": 1}
    )

    final_states = {row["capability_id"]: row["qualification_state"] for row in combinations}
    for decision in wp03["decisions"]:
        final_states[decision["source_record"]] = decision["decision"]
    for decision in wp04["decisions"]:
        final_states[decision["source_record"]] = decision["public_maturity"]

    assert Counter(final_states.values()) == Counter(
        {"QUALIFIED_BOUNDED": 31, "EXPERIMENTAL": 14, "NOT_QUALIFIED": 1}
    )
    assert sum(Counter(final_states.values()).values()) == 46
    assert [key for key, value in final_states.items() if value == "NOT_QUALIFIED"] == [
        "COMB-HEX8-linear_buckling"
    ]
    assert final_states["COMB-WEDGE6-linear_static"] == "EXPERIMENTAL"

    owner_decisions = owner["decisions"]
    for decision in wp04["decisions"]:
        owner_decision = owner_decisions[decision["evidence_case"]]
        assert owner_decision["resulting_maturity"] == decision["public_maturity"]
        assert owner_decision["owner_decision"] == (
            "APPROVE_WITH_LIMITATIONS"
            if decision["owner_gate"] == "APPROVED_WITH_LIMITATIONS"
            else "REJECT"
        )

    assert sum(value["promotion_applied"] for value in owner_decisions.values()) == 4
    assert owner["registry_reconciliation"]["final_counts"] == {
        "QUALIFIED_BOUNDED": 31,
        "EXPERIMENTAL": 14,
        "NOT_QUALIFIED": 1,
        "TOTAL": 46,
    }
    assert owner["registry_reconciliation"]["wedge6_is_not_not_qualified"] is True


def test_wp04_owner_gate_evidence_digests_and_scope_are_intact() -> None:
    owner = _load(OWNER_GATE)
    assert owner["audited_commit"] == "0496467120997b0c23f6817eb2f6e76eeda698d8"
    assert owner["audit_checks"]["opportunistic_numerical_core_change"] == "NOT_FOUND"
    assert owner["audit_checks"]["historical_0_2_7_evidence_integrity"] == "PASS"
    for record in owner["technical_evidence"]:
        path = ROOT / record["path"]
        assert path.is_file(), record["path"]
        assert _sha256(path) == record["sha256"], record["path"]
