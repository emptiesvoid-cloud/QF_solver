"""Controlled contract checks for 026-G09 Contact Lot 2."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_g09_lot2 import _expected_penetration_failure


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "qualification" / "0_2_6"


def test_g09_lot2_contract_is_bounded_and_not_autonomous() -> None:
    contract = json.loads((DATA / "g09_lot2_requirements.json").read_text(encoding="utf-8"))
    gates = json.loads((DATA / "gates.json").read_text(encoding="utf-8"))
    gate = next(item for item in gates["gates"] if item["id"] == "026-G09")
    assert contract["lot"] == "LOT2"
    assert contract["status"] == "CONTRACT_READY_NOT_CLOSED"
    assert len(contract["requirements"]) == 5
    assert contract["scope"]["finite_sliding"] is False
    assert contract["penalty_policy"]["candidate_status"] == "OWNER_REVIEW_REQUIRED"
    assert contract["out_of_scope"][-1] == "official 026-G09 gate closure"
    assert gate["status"] == "PASS_WITH_LIMITATIONS"
    assert gate["lot2_gate_closure"] is True


def test_g09_lot2_registry_covers_cycles_rollback_and_failures() -> None:
    registry = json.loads((DATA / "g09_lot2_case_registry.json").read_text(encoding="utf-8"))
    names = {row["name"] for row in registry["cases"]}
    assert registry["status"] == "EVIDENCE_READY_NOT_CLOSED"
    assert "mesh_penalty_sensitivity" in names
    assert "recontact_cycle" in names
    assert "rollback_before_first_commit" in names
    assert "rollback_after_one_commit" in names
    assert "excessive_penetration" in names


def test_g09_lot2_excessive_penetration_is_fail_closed() -> None:
    result = _expected_penetration_failure()
    assert result["status"] == "EXPECTED_FAILURE"
    assert result["converged"] is False
    assert result["fail_closed"] is True
    assert result["reason"] == "CONTACT_PENETRATION_EXCESSIVE"
