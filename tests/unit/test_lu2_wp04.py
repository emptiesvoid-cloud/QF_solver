"""Targeted contract checks for the LU2-WP04 Bronze evidence path."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_7"
CONTRACT = QUALIFICATION / "wp04_execution_contract.json"
RUNTIME = QUALIFICATION / "wp04_runtime"
RUNNER = ROOT / "scripts" / "run_lu2_wp04_bronze.py"
ASSEMBLER = ROOT / "src" / "solveur" / "large" / "assembler.py"


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
    assert index["acceptance"]["operator_build"] == "RANK_ZERO_LOCAL_PATH_REACHED"
    assert index["acceptance"]["petsc_initialization"] == "RANK_ZERO_LOCAL_PATH_REACHED"
    assert index["acceptance"]["gamg_readiness"] is False
    assert index["acceptance"]["bronze_pass"] is False
    assert audit["decision"] == "OWNER_INTERRUPTED_BEFORE_COMPLETION"
    assert audit["bronze_attempts"][0]["solve_executed"] is False
    assert audit["bronze_attempts"][1]["status"] == "NOT_RUN_AFTER_USER_INTERRUPT"
    assert audit["audit"]["resource_limited_proven"] is False
    assert state["status"] == "PASS"
    assert state["progress"]["level_up_2_acquired_percent"] == 37
    assert state["ready_for_lu2_wp05"] is True
    assert state["ready_for_wp04_retry"] is False
    assert state["ready_for_c1"] is False
    assert state["blockers"] == []
    corrected = _read(RUNTIME / "wp04_corrected_run_a_raw.json")
    assert corrected["status"] == "PASS"
    assert corrected["checks"]["gamg_ready"] is True
    assert corrected["petsc"]["global_readiness"]
    assert corrected["petsc"]["global_readiness"][-1]["pc_ready"] is True
    assert corrected["solve_executed"] is False
    assert corrected["telemetry_status"] == "ENABLED"
    assert forensic["status"] == "USER_INTERRUPTED_INCONCLUSIVE"
    assert forensic["termination"]["owner_interrupted"] is True
    assert forensic["termination"]["container_was_still_running_at_forensic_observation"] is True
    assert forensic["process_observations"]["all_ranks_active"] is True
    assert forensic["memory_observations"]["swap_pressure"] == "NOT_MEASURED"
    assert forensic["decision"]["resource_limited_proven"] is False
    assert forensic["decision"]["c1_trigger_confirmed"] is False
    assert forensic["retry_plan"]["recommendation"] == "YES"
    post_ready = _read(RUNTIME / "wp04_post_pc_ready_diagnostic.json")
    assert post_ready["root_cause"]["classification"] == "PROVEN_COLLECTIVE_ORDER_MISMATCH"
    assert post_ready["run_a"]["rank_zero_pc_ready_scope"] == "LOCAL"
    assert post_ready["classification"]["resource_limited_proven"] is False
    assert (RUNTIME / "wp04_5m_progress.jsonl").is_file()

    assert not list((RUNTIME / "raw").glob("*.json"))


def test_post_pc_ready_collectives_are_guarded_and_rank_zero_does_not_reduce_time() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    instrumented_source = source + ASSEMBLER.read_text(encoding="utf-8")
    required_markers = (
        "POST_INSERTION",
        "PRE_ASSEMBLE_1",
        "POST_ASSEMBLE_1",
        "PRE_CONSTRAINTS",
        "POST_CONSTRAINTS",
        "PRE_ASSEMBLE_2",
        "POST_ASSEMBLE_2",
        "PRE_RHS",
        "POST_RHS",
        "PRE_SETUP",
        "POST_SETUP",
        "PRE_OWNERSHIP_GATHER",
        "POST_OWNERSHIP_GATHER",
        "PRE_PC_READY",
        "PRE_MEMORY_GATHER",
        "POST_MEMORY_GATHER",
        "PC_READY_GLOBAL",
        "FINALIZE_ENTER",
        "FINALIZE_EXIT",
        "EXCEPTION",
    )
    assert all(marker in instrumented_source for marker in required_markers)
    assert 'telemetry.phase("PC_READY_GLOBAL")' in source
    assert source.index("total_seconds = _max_time") < source.index("if rank == 0:", source.index("record_error"))

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
            continue
        if not (
            isinstance(node.test.left, ast.Name)
            and node.test.left.id == "rank"
            and len(node.test.ops) == 1
            and isinstance(node.test.ops[0], ast.Eq)
            and len(node.test.comparators) == 1
            and isinstance(node.test.comparators[0], ast.Constant)
            and node.test.comparators[0].value == 0
        ):
            continue
        assert not any(
            isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "_max_time"
            for call in ast.walk(ast.Module(body=node.body, type_ignores=[]))
        )
