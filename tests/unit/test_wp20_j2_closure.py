"""Targeted WP20 Owner-closure and J2 provenance checks."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "qualification/0_2_7/wp20_state.json"
REGISTRY_PATH = ROOT / "qualification/0_2_7/capability_registry_v2.json"
GATES_PATH = ROOT / "qualification/0_2_7/gates.json"
REQUIREMENTS_PATH = ROOT / "qualification/0_2_7/requirements.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp20_closes_existing_j2_scope_without_promotion() -> None:
    state = _load(STATE_PATH)
    assert state["status"] == "PASS_WITH_LIMITATIONS"
    assert state["owner_decision"] == "OWNER_APPROVED_BOUNDED_KEEP_EXISTING_SCOPE"
    assert state["maturity_actions"]["promotions"] == []
    assert state["maturity_actions"]["demotions"] == []
    assert all(state["maturity_actions"][family] == "KEEP" for family in ("TET4", "TET10", "HEX8", "HEX20"))
    assert state["maturity_actions"]["MAT-FINITE-J2"] == "KEEP_EXPERIMENTAL_NOT_QUALIFIED"


def test_wp20_preserves_evidence_and_external_scope() -> None:
    state = _load(STATE_PATH)
    assert state["evidence_source_sha"] == "94461602dfd1782be57c20e1801a0d5d8e262ef1"
    assert state["evidence_artifact_result_digest"] == "5e4825625d40f2363ecefb8f96baa43acac42f23db7195d000ca0c09717ef536"
    assert state["external_vnv"]["status"] == "PARTIAL_REUSED_CONTROLLED_EVIDENCE"
    assert state["external_vnv"]["new_external_run"] is False
    assert state["provenance"]["historical_wp11_evidence_not_rewritten"] is True
    assert state["provenance"]["no_new_tolerance"] is True


def test_wp20_active_governance_is_closed_and_registry_maturity_is_unchanged() -> None:
    state = _load(STATE_PATH)
    gates = _load(GATES_PATH)
    requirements = _load(REQUIREMENTS_PATH)
    registry = _load(REGISTRY_PATH)
    g20 = next(gate for gate in gates["level_up"]["gates"] if gate["id"] == "LUP-027-G20")
    g11 = next(gate for gate in gates["gates"] if gate["id"] == "027-G11")
    req20 = next(req for req in requirements["level_up_requirements"] if req["id"] == "027-LU-REQ-020")
    req12 = next(req for req in requirements["requirements"] if req["id"] == "027-REQ-012")
    j2 = next(record for record in registry["records"] if record["capability_id"] == "MAT-J2-SMALL")
    assert g20["status"] == state["status"]
    assert g11["owner_decision"] == state["owner_decision"]
    assert req20["status"] == state["status"]
    assert req12["owner_policy"] == state["owner_decision"]
    assert j2["qualification_state"] == "QUALIFIED_BOUNDED"
    assert j2["owner_decision"] == state["owner_decision"]


def test_wp20_has_no_numeric_or_finite_kinematic_promotion() -> None:
    state = _load(STATE_PATH)
    assert state["provenance"]["existing_fem_formulation_changed"] is False
    assert state["provenance"]["no_new_major_physics"] is True
    assert "finite-kinematic J2" in " ".join(state["limitations"])
