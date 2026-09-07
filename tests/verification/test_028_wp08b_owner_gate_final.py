"""WP08B Owner-gate decision and mixed-workflow separation guards."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OWNER = ROOT / "qualification/0_2_8/wp08b_owner_gate_final.json"
MATRIX = ROOT / "qualification/0_2_8/wp08b_mixed_modal_matrix.json"
WP08 = ROOT / "qualification/0_2_8/wp08_mixed_modal_matrix.json"
WP08B_CONTRACT = ROOT / "qualification/0_2_8/wp08b_mixed_modal_contract.json"
WP08B_EVIDENCE = ROOT / "qualification/0_2_8/wp08b_mixed_modal_vnv.json"
REGISTRY = ROOT / "qualification/0_2_7/capability_registry_v2.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp08b_owner_gate_closes_only_the_bounded_mixed_modal_workflow() -> None:
    owner = _load(OWNER)
    matrix = _load(MATRIX)
    evidence = _load(WP08B_EVIDENCE)

    assert owner["status"] == "CLOSED_WITH_APPROVE_WITH_LIMITATIONS"
    assert owner["audited_commit"] == "35d2debbd414917ac31d2b2d945df1132737eae5"
    assert owner["decision"]["owner_decision"] == "APPROVE_WITH_LIMITATIONS"
    assert owner["decision"]["mixed_modal_final_status"] == "QUALIFIED_BOUNDED"
    assert matrix["status"] == "OWNER_APPROVED_WITH_LIMITATIONS"
    assert matrix["mixed_candidate"]["owner_gate"] == "APPROVE_WITH_LIMITATIONS"
    assert matrix["mixed_candidate"]["final_status"] == "QUALIFIED_BOUNDED"
    assert evidence["technical_decision"] == "QUALIFIED_BOUNDED_CANDIDATE"


def test_wp08b_owner_gate_preserves_the_original_gate_and_evidence() -> None:
    owner = _load(OWNER)
    wp08 = _load(WP08)
    contract = _load(WP08B_CONTRACT)
    evidence = _load(WP08B_EVIDENCE)

    assert wp08["mixed_candidate"]["final_status"] == "SUPPORTED_WITH_LIMITATIONS"
    assert wp08["evidence_summary"]["mesh_refinement"] == "FAIL_PREDECLARED_MODE_MATCHING_GATE"
    assert contract["tolerance_policy"]["fixed_before_execution"] is True
    assert contract["tolerance_policy"]["post_observation_retuning"] is False
    assert owner["integrity"]["wp08_initial_gate_changed"] is False
    assert owner["integrity"]["wp08_initial_evidence_rewritten"] is False
    assert evidence["wp08_evidence_changed"] is False
    assert evidence["historical_0_2_7_evidence_changed"] is False


def test_wp08b_owner_gate_reconciles_the_registry_without_adding_a_mixed_record() -> None:
    owner = _load(OWNER)
    registry = _load(REGISTRY)
    records = [record for record in registry["records"] if record.get("record_kind") == "combination"]
    counts = Counter(record["qualification_state"] for record in records)

    assert len(records) == 46
    assert counts == {"QUALIFIED_BOUNDED": 20, "EXPERIMENTAL": 25, "NOT_QUALIFIED": 1}
    assert owner["registry_separation"]["element_analysis_registry_total"] == 46
    assert owner["registry_separation"]["mixed_workflow_added_to_combination_registry"] is False
    assert owner["registry_separation"]["not_qualified_combination"] == "COMB-HEX8-linear_buckling"
    assert owner["integrity"]["numerical_source_changed"] is False
