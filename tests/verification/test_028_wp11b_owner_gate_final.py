"""Owner-gate guards for the bounded WP11B HEX8 buckling exposure."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OWNER = ROOT / "qualification/0_2_8/wp11b_hex8_buckling_owner_gate_final.json"
MATRIX = ROOT / "qualification/0_2_8/wp11b_hex8_buckling_experimental_matrix.json"
REGISTRY = ROOT / "qualification/0_2_7/capability_registry_v2.json"
WP06 = ROOT / "qualification/0_2_8/wp06_hex8_buckling_vnv.json"
WP06B = ROOT / "qualification/0_2_8/wp06b_hex8_buckling_vnv.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp11b_owner_gate_approves_only_experimental_scope() -> None:
    owner = _load(OWNER)
    matrix = _load(MATRIX)
    assert owner["owner_decision"] == "APPROVE_EXPERIMENTAL"
    assert owner["final_status"] == "EXPERIMENTAL"
    assert owner["audit_checks"]["new_contract_predeclared"] == "PASS"
    assert owner["audit_checks"]["refinement_characterization"].startswith("PASS_WITH_LIMITATIONS")
    assert owner["audit_checks"]["external_oracle"].startswith("NOT_AVAILABLE")
    assert owner["limitations"]
    assert matrix["owner_decision"] == "APPROVE_EXPERIMENTAL"
    assert matrix["public_promotion_applied"] is True
    assert matrix["owner_gate_required"] is False


def test_wp11b_reconciles_46_and_preserves_wp06_records() -> None:
    owner = _load(OWNER)
    registry = _load(REGISTRY)
    wp06 = _load(WP06)
    wp06b = _load(WP06B)
    reconciliation = owner["registry_reconciliation"]
    assert len(registry["combination_record_ids"]) == 46
    assert reconciliation["state_after_wp11b"] == {
        "QUALIFIED_BOUNDED": 32,
        "EXPERIMENTAL": 14,
        "NOT_QUALIFIED": 0,
        "TOTAL": 46,
    }
    assert reconciliation["counts_consistent"] is True
    assert reconciliation["transition"] == "COMB-HEX8-linear_buckling: NOT_QUALIFIED -> EXPERIMENTAL"
    assert wp06["technical_decision"] == "NOT_QUALIFIED"
    assert wp06b["technical_decision"] == "NOT_QUALIFIED"
    assert owner["integrity"]["wp06_evidence_rewritten"] is False
    assert owner["integrity"]["wp06b_evidence_rewritten"] is False
    assert owner["integrity"]["historical_0_2_7_evidence_changed"] is False
