"""WP08 mixed-modal contract and bounded evidence guards."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_wp08_mixed_modal import _failure_contract, _interface_metrics, mixed_model


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "qualification/0_2_8/wp08_mixed_modal_contract.json"
EVIDENCE = ROOT / "qualification/0_2_8/wp08_mixed_modal_vnv.json"
MATRIX = ROOT / "qualification/0_2_8/wp08_mixed_modal_matrix.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp08_contract_is_frozen_and_keeps_the_mixed_registry_separate() -> None:
    contract = _load(CONTRACT)
    evidence = _load(EVIDENCE)
    matrix = _load(MATRIX)

    assert contract["status"] == "PREDECLARED_CAMPAIGN_CONTRACT"
    assert contract["baseline_sha"] == "65c816fee4a1497dd320358565a297c01bfcaff5"
    assert contract["tolerance_policy"]["fixed_before_execution"] is True
    assert contract["tolerance_policy"]["post_observation_retuning"] is False
    assert evidence["technical_decision"] == "SUPPORTED_WITH_LIMITATIONS"
    assert evidence["owner_gate_required"] is False
    assert matrix["summary"]["element_analysis_registry_total"] == 46
    assert matrix["summary"]["element_analysis_registry_changed"] is False
    assert matrix["registry_integrity"]["not_added_to_element_analysis_registry"] is True


def test_wp08_pairwise_campaign_passes_but_refinement_blocks_candidate() -> None:
    evidence = _load(EVIDENCE)

    assert evidence["mixed_mass_assembly"]["status"] == "PASS"
    assert all(row["status"] == "PASS" for row in evidence["pairwise_modal"].values() if isinstance(row, dict))
    assert evidence["pure_vs_mixed"]["status"] == "PASS"
    assert evidence["mesh_refinement"]["status"] == "FAIL"
    assert min(evidence["mesh_refinement"]["shared_node_mode_matching_minimum_mac"]) < 0.5
    assert evidence["replay_determinism"]["status"] == "PASS"
    assert evidence["historical_0_2_7_evidence_changed"] is False
    assert evidence["numerical_source_changed"] is False


def test_wp08_modal_interface_and_failure_contracts_pass() -> None:
    assert _interface_metrics(mixed_model())["status"] == "PASS"
    assert _failure_contract()["status"] == "PASS"
