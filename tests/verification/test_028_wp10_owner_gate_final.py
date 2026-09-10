"""WP10 HEX8-SRI Owner-gate decision guards."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load(relative: str) -> dict[str, object]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_wp10_owner_gate_approves_only_separate_experimental_scope() -> None:
    owner = _load("qualification/0_2_8/wp10_hex8_sri_owner_gate_final.json")
    assert owner["source_sha"] == "a4eb1e0dd8eb5218aeb8d23e917ddeec44f88c6b"
    assert owner["decision"] == "APPROVE_EXPERIMENTAL_BOUNDED"
    assert owner["final_status"] == "EXPERIMENTAL_BOUNDED"
    assert owner["public_exposure"]["standard_hex8_replaced"] is False
    assert owner["public_exposure"]["element_analysis_registry_46_changed"] is False
    assert owner["audit"]["oracle"] == "SUFFICIENT_FOR_EXPERIMENTAL_SCOPE; independent Timoshenko oracle, no external correlation claimed"
    assert owner["audit"]["replays"] == "PASS_2_DETERMINISTIC"


def test_wp10_owner_gate_preserves_historical_integrity() -> None:
    owner = _load("qualification/0_2_8/wp10_hex8_sri_owner_gate_final.json")
    assert owner["integrity"] == {
        "numerical_source_changed": False,
        "hex8_standard_changed": False,
        "historical_0_2_7_evidence_changed": False,
        "wp07_wp09_claims_changed": False,
    }
