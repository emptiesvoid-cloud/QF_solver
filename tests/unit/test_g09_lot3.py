"""Controlled contract and evidence checks for 026-G09 Contact Lot 3."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "qualification" / "0_2_6"


def test_g09_lot3_external_evidence_is_bounded_and_provenanced() -> None:
    evidence = json.loads((DATA / "g09_lot3_evidence.json").read_text(encoding="utf-8"))
    assert evidence["status"] == "PASS_WITH_LIMITATIONS"
    assert evidence["official_gate_status"] == "NOT_STARTED"
    assert evidence["source_sha"] == "c76d4af39dc270a05596a53ef2d93baa9171c29b"
    assert evidence["source_dirty"] is False
    assert evidence["penalty_governance"]["status"] == "OWNER_REVIEW_REQUIRED"
    assert evidence["cases"]["tet4_two_slave_curve"]["overall_gap_curve_error"] > 0.5
    assert evidence["cases"]["tet4_two_slave_curve"]["active_gap_curve_error"] < 1e-8


def test_g09_lot3_contract_preserves_external_limitations() -> None:
    contract = json.loads((DATA / "g09_lot3_requirements.json").read_text(encoding="utf-8"))
    registry = json.loads((DATA / "g09_lot3_case_registry.json").read_text(encoding="utf-8"))
    assert len(contract["requirements"]) == 5
    assert contract["penalty_policy"]["candidate_status"] == "OWNER_REVIEW_REQUIRED"
    assert contract["scope"]["finite_sliding"] is False
    assert contract["scope"]["surface_to_surface"] is False
    assert len(registry["cases"]) == 5
    assert registry["cases"][-1]["expected"] == "UNSUPPORTED_EXPLICIT"


def test_g09_lot3_keeps_official_gate_open_until_owner_action() -> None:
    gates = json.loads((DATA / "gates.json").read_text(encoding="utf-8"))
    gate = next(item for item in gates["gates"] if item["id"] == "026-G09")
    assert gate["status"] == "NOT_STARTED"
    assert gate["lot3_gate_closure"] is False
