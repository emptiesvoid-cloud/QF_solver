"""WP07 Owner-gate decision and mixed-workflow registry separation guards."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OWNER = ROOT / "qualification/0_2_8/wp07_owner_gate_final.json"
MATRIX = ROOT / "qualification/0_2_8/wp07_mixed_static_matrix.json"
REGISTRY = ROOT / "qualification/0_2_7/capability_registry_v2.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp07_owner_gate_approves_only_the_bounded_mixed_workflow() -> None:
    owner = _load(OWNER)
    matrix = _load(MATRIX)

    assert owner["status"] == "CLOSED_WITH_APPROVE_WITH_LIMITATIONS"
    assert owner["audited_commit"] == "da310e8f3708c46d0a69a2980a2f47c4c7e9f4aa"
    assert owner["decision"]["TET4_WEDGE6"]["owner_decision"] == "APPROVE_WITH_LIMITATIONS"
    assert owner["decision"]["WEDGE6_HEX8"]["owner_decision"] == "APPROVE_WITH_LIMITATIONS"
    assert owner["decision"]["TET4_WEDGE6_HEX8"]["owner_decision"] == "APPROVE_WITH_LIMITATIONS"
    assert owner["decision"]["mixed_static_final_status"] == "QUALIFIED_BOUNDED"
    assert matrix["status"] == "OWNER_APPROVED_WITH_LIMITATIONS"
    assert matrix["mixed_workflow_qualification"]["status"] == "QUALIFIED_BOUNDED"


def test_wp07_owner_gate_preserves_the_46_combination_registry() -> None:
    owner = _load(OWNER)
    registry = _load(REGISTRY)
    records = [record for record in registry["records"] if record.get("record_kind") == "combination"]
    counts = Counter(record["qualification_state"] for record in records)

    assert len(records) == 46
    assert counts == {"QUALIFIED_BOUNDED": 20, "EXPERIMENTAL": 25, "NOT_QUALIFIED": 1}
    assert owner["registry_separation"]["element_analysis_registry_total"] == 46
    assert owner["registry_separation"]["mixed_workflow_added_to_combination_registry"] is False
    assert owner["registry_separation"]["not_qualified_combination"] == "COMB-HEX8-linear_buckling"
    assert owner["integrity"]["historical_0_2_7_evidence_changed"] is False
