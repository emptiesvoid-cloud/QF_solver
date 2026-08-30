"""Governance checks for the bounded 026-G09 Owner closeout."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "qualification" / "0_2_6"


def test_g09_owner_closeout_is_bounded_and_penalty_is_experimental() -> None:
    closeout = json.loads((DATA / "g09_owner_closeout.json").read_text(encoding="utf-8"))

    assert closeout["official_gate_status"] == "PASS_WITH_LIMITATIONS"
    assert closeout["owner_decision"] == "PASS_WITH_LIMITATIONS"
    assert closeout["penalty_policy"]["decision"] == "EXPERIMENTAL_ONLY"
    assert closeout["penalty_policy"]["approved_bounded_range"] is None
    assert closeout["penalty_policy"]["conditioning_cutoff"] == "NONE_APPROVED"
    assert closeout["qualified_bounded_scope"]["families"] == ["TET4"]
    assert "finite sliding" in closeout["explicit_exclusions"]
    assert closeout["requirement_aggregate"]["blocking"] == []


def test_g09_gate_references_owner_closeout_without_promoting_out_of_scope() -> None:
    closeout = json.loads((DATA / "g09_owner_closeout.json").read_text(encoding="utf-8"))
    gates = json.loads((DATA / "gates.json").read_text(encoding="utf-8"))
    gate = next(item for item in gates["gates"] if item["id"] == "026-G09")

    assert gate["status"] == closeout["official_gate_status"]
    assert gate["owner_closeout"] == "g09_owner_closeout.json"
    assert gate["lot1_gate_closure"] is True
    assert gate["lot2_gate_closure"] is True
    assert gate["lot3_gate_closure"] is True
    assert gate["penalty_policy_status"] == "EXPERIMENTAL_ONLY"
    assert "g09_owner_closeout.json" in gate["evidence_ids"]
    assert any("friction" in item for item in closeout["explicit_exclusions"])
