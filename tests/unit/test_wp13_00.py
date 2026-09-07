"""WP13-00 foundation contract and baseline guards."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.wp13_00_guards import validate_baseline
from scripts.wp13_common import compare_replays, evaluate_tolerance, validate_vnv_contract


ROOT = Path(__file__).resolve().parents[2]


def test_wp13_baseline_is_frozen_and_separates_workflows() -> None:
    baseline = json.loads((ROOT / "qualification/0_2_8/wp13_00_baseline.json").read_text(encoding="utf-8"))
    assert baseline["start_sha_wp13"] == "30bff8d585b3988befaff9cc21e881098ff1b2df"
    assert baseline["maturity"]["element_analysis_registry"]["state_counts"] == {
        "QUALIFIED_BOUNDED": 32,
        "EXPERIMENTAL": 14,
        "NOT_QUALIFIED": 0,
    }
    assert len(baseline["mixed_workflow_registry"]["records"]) == 3
    assert baseline["element_analysis_registry"]["registry_boundary"].startswith("Element/analysis")


def test_wp13_guards_pass() -> None:
    assert validate_baseline() == []


def test_wp13_contract_requires_predeclared_gates_and_replays() -> None:
    contract = {
        "scope": {"capability": "example", "analysis": "linear_static"},
        "oracle": {"reference": "analytic", "independent": True},
        "tolerances": {"predeclared": True, "gates": [{"metric": "residual", "operator": "<=", "limit": 1e-8}]},
        "required_metrics": ["residual"],
        "replay_count": 2,
        "owner_gate": {"required": True},
        "abort_criteria": ["missing oracle"],
        "claim_limitations": ["bounded scope"],
        "source_sha": "30bff8d585b3988befaff9cc21e881098ff1b2df",
        "environment": {"python": "3.13"},
    }
    assert validate_vnv_contract(contract) == []
    contract["tolerances"]["predeclared"] = False
    assert "tolerances.predeclared must be true" in validate_vnv_contract(contract)


def test_wp13_replay_and_tolerance_helpers_are_fail_closed() -> None:
    assert compare_replays({"value": 1}, {"value": 1})["status"] == "PASS"
    assert compare_replays({"value": 1}, {"value": 2})["status"] == "FAIL"
    assert evaluate_tolerance(0.5, operator="<=", limit=1.0, tolerance_id="T-001")["status"] == "PASS"
    assert evaluate_tolerance(1.5, operator="<=", limit=1.0, tolerance_id="T-001")["status"] == "FAIL"
