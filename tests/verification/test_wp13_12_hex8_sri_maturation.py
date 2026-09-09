"""Guards for the prospective WP13-12 HEX8-SRI maturity campaign."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load(relative: str) -> dict[str, object]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_wp13_12_contract_freezes_the_separate_sri_scope() -> None:
    contract = _load("qualification/0_2_8/wp13_12_hex8_sri_maturation_contract.json")
    assert contract["contract_id"] == "WP13-12-HEX8-SRI-MATURATION-001"
    assert contract["formulation"]["hourglass_control"] is False
    assert contract["formulation"]["standard_hex8_must_remain_unchanged"] is True
    assert contract["claim_policy"]["element_analysis_registry_46_changed"] is False
    assert contract["gates"]["post_observation_retuning"] is False


def test_wp13_12_final_evidence_retains_experimental_scope() -> None:
    evidence = _load("qualification/0_2_8/wp13_12_hex8_sri_maturation/manifest.json")
    assert evidence["technical_decision"] == "EXPERIMENTAL_BOUNDED_RETAIN"
    assert all(value == "PASS" for value in evidence["gates"].values())
    assert evidence["patch_and_rank"]["spurious_zero_modes"] == 0
    assert evidence["failure_contract"]["executed"] == evidence["failure_contract"]["required"] == 9
    assert evidence["replays"]["full_array_comparison"] == "PASS"
    assert evidence["integrity"]["element_formulation_changed"] is False
