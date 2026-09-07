"""WP10 HEX8 selective reduced integration research-gate guards."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load(relative: str) -> dict[str, object]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_wp10_contract_is_predeclared_and_standard_hex8_is_excluded() -> None:
    contract = _load("qualification/0_2_8/wp10_hex8_sri_contract.json")
    assert contract["baseline_sha"] == "324e496c125d55d6925309ee791faaedcead3039"
    assert contract["status"] == "PREDECLARED_RESEARCH_GATE"
    assert contract["standard_hex8"]["must_remain_unchanged"] is True
    assert contract["formulation"]["public_registry"] is False
    assert contract["formulation"]["hourglass_control"] is False
    assert contract["predeclared_gates"]["post_observation_retuning"] is False


def test_wp10_campaign_gates_gain_and_replays_pass() -> None:
    evidence = _load("qualification/0_2_8/wp10_hex8_sri_vnv.json")
    campaign = evidence["campaign"]
    assert evidence["technical_decision"] == "EXPERIMENTAL_BOUNDED_CANDIDATE"
    assert all(value == "PASS" for value in campaign["gates"].values())
    assert campaign["locking_reduction"]["nearly_incompressible_nu04999"]["fine_level_error_reduction"] >= 0.50
    assert evidence["replays"]["status"] == "PASS"
    assert evidence["replays"]["deterministic"] is True
    assert evidence["integrity"]["hex8_standard_changed"] is False
    assert evidence["integrity"]["historical_0_2_7_evidence_changed"] is False


def test_wp10_matrix_keeps_candidate_out_of_public_maturity() -> None:
    matrix = _load("qualification/0_2_8/wp10_hex8_sri_matrix.json")
    assert matrix["technical_decision"] == "EXPERIMENTAL_BOUNDED_CANDIDATE"
    assert matrix["proposed_maturity"] == "EXPERIMENTAL_BOUNDED_CANDIDATE"
    assert matrix["public_promotion"] is False
    assert matrix["owner_gate_required"] is True
    assert matrix["registry_separation"]["hex8_sri_public_registry_entry"] is False
    assert matrix["registry_separation"]["element_analysis_registry_46_changed"] is False
