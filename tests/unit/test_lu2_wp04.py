"""Targeted contract checks for the LU2-WP04 Bronze evidence path."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_7"
CONTRACT = QUALIFICATION / "wp04_execution_contract.json"
RUNTIME = QUALIFICATION / "wp04_runtime"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp04_contract_is_predeclared_and_freeze_bound() -> None:
    contract = _read(CONTRACT)
    assert contract["status"] == "PREDECLARED"
    assert contract["freeze"]["freeze_id"] == "LU2-WP02-FREEZE-bfd1975b012453a3"
    assert contract["freeze"]["freeze_digest_sha256"] == "bfd1975b012453a3b492cc79c968ceeba6ae6951a293e3ce65ddda548d8339a1"
    assert contract["workload"]["expected_size"] == {"nodes": 1_670_880, "elements": 9_773_946, "true_dof": 5_012_640}
    assert contract["run_policy"]["required_runs"] == ["run1", "run2"]
    assert contract["run_policy"]["no_converged_solve"] is True


def test_wp04_forensic_reclassification_is_honest() -> None:
    summary = _read(RUNTIME / "wp04_summary.json")
    index = _read(RUNTIME / "wp04_evidence_index.json")
    audit = _read(RUNTIME / "wp04_resource_guard_audit.json")
    forensic = _read(RUNTIME / "wp04_forensic_audit.json")
    state = _read(QUALIFICATION / "lu2_wp04_state.json")

    assert summary["status"] == "USER_INTERRUPTED_INCONCLUSIVE"
    assert summary["runs"]["run1"]["status"] == "USER_INTERRUPTED_INCONCLUSIVE"
    assert summary["runs"]["run2"]["status"] == "NOT_RUN_AFTER_USER_INTERRUPT"
    assert summary["workload"]["true_dof"] == 5_012_640
    assert summary["workload"]["independent_builds"] == 2
    assert summary["workload"]["model_replay"] == "PASS"
    assert summary["checks"]["bronze"] == "FAIL"
    assert summary["checks"]["c1_matrix_free_trigger"] is False
    assert summary["time_guard"]["decision"] == "OWNER_INTERRUPT_OBSERVED"
    assert summary["time_guard"]["observed_elapsed_seconds"] > 2 * summary["time_guard"]["reference_mean_total_seconds"]
    assert summary["time_guard"]["absolute_wall_time_ceiling_seconds"] == 18_000
    assert summary["time_guard"]["effective_stop_threshold_seconds"] < summary["time_guard"]["absolute_wall_time_ceiling_seconds"]
    assert index["status"] == "USER_INTERRUPTED_INCONCLUSIVE"
    assert index["acceptance"]["operator_build"] is False
    assert index["acceptance"]["petsc_initialization"] is False
    assert index["acceptance"]["gamg_readiness"] is False
    assert index["acceptance"]["bronze_pass"] is False
    assert audit["decision"] == "OWNER_INTERRUPTED_BEFORE_COMPLETION"
    assert audit["bronze_attempts"][0]["solve_executed"] is False
    assert audit["bronze_attempts"][1]["status"] == "NOT_RUN_AFTER_USER_INTERRUPT"
    assert audit["audit"]["resource_limited_proven"] is False
    assert state["status"] == "USER_INTERRUPTED_INCONCLUSIVE"
    assert state["progress"]["level_up_2_acquired_percent"] == 22
    assert state["ready_for_lu2_wp05"] is False
    assert state["ready_for_wp04_retry"] is True
    assert state["ready_for_c1"] is False
    assert state["blockers"]
    assert forensic["status"] == "USER_INTERRUPTED_INCONCLUSIVE"
    assert forensic["termination"]["owner_interrupted"] is True
    assert forensic["termination"]["container_was_still_running_at_forensic_observation"] is True
    assert forensic["process_observations"]["all_ranks_active"] is True
    assert forensic["memory_observations"]["swap_pressure"] == "NOT_MEASURED"
    assert forensic["decision"]["resource_limited_proven"] is False
    assert forensic["decision"]["c1_trigger_confirmed"] is False
    assert forensic["retry_plan"]["recommendation"] == "YES"

    assert not list((RUNTIME / "raw").glob("*.json"))
