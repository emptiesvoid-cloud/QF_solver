"""Owner-closeout contract for the bounded 026-G04 decision."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "qualification" / "0_2_6" / "g04_owner_closeout.json"


def test_g04_owner_closeout_is_bounded_and_requires_no_global_gate_mutation() -> None:
    closeout = json.loads(CLOSEOUT.read_text(encoding="utf-8"))
    assert closeout["start_sha"] == "cfed7ef8c4e473778c06e1d005a17651cf5b34ca"
    assert closeout["status"] == "PASS_WITH_LIMITATIONS"
    assert closeout["owner_decision"] == "PASS_WITH_LIMITATIONS"
    assert closeout["global_gate_update"] == "DEFERRED_TO_MULTI_AGENT_CONSOLIDATION"
    assert closeout["no_other_gate_changed"] is True
    requirements = {row["requirement_id"]: row for row in closeout["requirements"]}
    assert set(requirements) == {f"G04-LIN-{index:03d}" for index in range(1, 9)}
    assert requirements["G04-LIN-001"]["decision"] == "SATISFIED_BOUNDED"
    assert requirements["G04-LIN-002"]["decision"] == "SATISFIED_BOUNDED"
    assert requirements["G04-LIN-003"]["decision"] == "SATISFIED"
    assert requirements["G04-LIN-004"]["decision"] == "SATISFIED_BOUNDED"
    assert requirements["G04-LIN-005"]["decision"] == "DEFERRED_LIMITATION"
    assert requirements["G04-LIN-006"]["decision"] == "SATISFIED"
    assert requirements["G04-LIN-007"]["decision"] == "DEFERRED_LIMITATION"
    assert requirements["G04-LIN-008"]["decision"] == "SATISFIED"
    assert not any(row["decision"] == "BLOCKING" for row in requirements.values())
    assert closeout["external_evidence_status"]["Code_Aster"] == "SKIPPED_UNAVAILABLE"
    assert closeout["external_evidence_status"]["CalculiX"] == "SKIPPED_UNAVAILABLE"
    assert closeout["discrete_status"] == "NOT_APPLICABLE"
    assert closeout["rbe2_status"] == "DIAGNOSTIC_ONLY"
    assert closeout["functional_code_changed"] is False
    assert closeout["ready_for_multi_agent_integration"] is True
    assert closeout["ready_for_next_agent_b_gate"] is True
