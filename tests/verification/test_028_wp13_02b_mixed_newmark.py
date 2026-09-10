"""Contract and evidence guards for the WP13-02B mixed Newmark campaign."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[2]
EVIDENCE = ROOT / "qualification" / "0_2_8" / "wp13_02b_mixed_newmark_evidence.json"
CONTRACT = ROOT / "qualification" / "0_2_8" / "wp13_02a_newmark_contract.json"


def test_wp13_02b_evidence_preserves_frozen_contract_and_scope() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert evidence["contract_id"] == "WP13-02A-NEWMARK-MIXED-CONTRACT-001"
    assert evidence["contract_unchanged"] is True
    assert evidence["scope"]["connected_components"] == 1
    assert evidence["scope"]["family_counts"] == {"TET4": 3, "WEDGE6": 2, "HEX8": 1}
    assert contract["predeclared_gates"]["post_observation_retuning"] is False
    assert evidence["integrity"]["gates_changed"] is False
    assert evidence["integrity"]["numerical_source_changed"] is False


def test_wp13_02b_fine_levels_and_replays_pass_without_promotion() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    fine = [row for row in evidence["dt_campaign"] if row["fine_oracle_gate"] == "PASS"]

    assert [row["level"] for row in fine] == ["T1/80", "T1/160"]
    assert evidence["dt_convergence"]["status"].startswith("PASS_FINE_REFINEMENT")
    assert evidence["interfaces"]["maximum_force_transfer_relative"] <= 1.0e-8
    assert evidence["residual_energy"]["maximum_relative_energy_drift"] <= 1.0e-6
    assert evidence["replays"]["contract_status"] == "PASS_NUMERICAL_DETERMINISM"
    assert evidence["decision"]["claim_status"] == "CANDIDATE_ONLY_PENDING_WP13_02D_OWNER_GATE"
