"""Contract checks for the non-closing 026-G04 blocker-closure evidence."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLOSURE = ROOT / "qualification" / "0_2_6" / "g04_targeted_blocker_closure.json"


def test_g04_targeted_closure_is_traceable_and_does_not_close_the_gate() -> None:
    evidence = json.loads(CLOSURE.read_text(encoding="utf-8"))
    assert evidence["source_sha"] == "171bc93803690fb70b8831f17db81f60f4401ea6"
    oracle = evidence["analytical_oracle_closure"]
    assert oracle["existing_executable_pass"] == 20
    assert oracle["new_executable_pass"] == 0
    assert oracle["not_applicable"] == 30
    assert oracle["fail"] == 0
    assert sum(len(record["case_ids"]) for record in oracle["records"]) == 30
    mesh = evidence["new_mesh_series"]
    assert len(mesh["case_linkage"]) >= 3
    assert mesh["policy_result"] == "PASS"
    assert mesh["final_adjacent_change"] <= mesh["threshold"]
    invalid = evidence["invalid_input_closure"]
    assert invalid["cases_total"] == invalid["pass"] == invalid["expected_failure"] == 6
    assert invalid["fail"] == 0
    assert evidence["discrete_and_rbe2"]["discrete_status"] == "NOT_APPLICABLE"
    assert evidence["discrete_and_rbe2"]["rbe2_status"] == "DIAGNOSTIC_ONLY"
    assert evidence["external"]["code_aster"] == "SKIPPED_UNAVAILABLE"
    assert evidence["external"]["calculix"] == "SKIPPED_UNAVAILABLE"
    assert evidence["proposed_gate_decision"] == "PASS_WITH_LIMITATIONS"
    assert evidence["official_closeout"] == "DEFERRED_TO_OWNER"
