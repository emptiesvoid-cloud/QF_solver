from __future__ import annotations

import json
from pathlib import Path

from solveur.verification.observatory import read_observatory_record, validate_observatory_record

from scripts.collect_lu2_wp03_evidence import (
    ACCEPTANCE_TOLERANCE,
    FREEZE_DIGEST,
    FREEZE_ID,
    INPUT_DIGEST,
    ROOT,
    SOURCE_SHA,
)


RUNTIME = ROOT / "qualification" / "0_2_7" / "wp03_runtime"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp03_contract_and_freeze_are_exactly_predeclared() -> None:
    contract = _read(ROOT / "qualification/0_2_7/wp03_execution_contract.json")
    freeze = _read(ROOT / "qualification/0_2_7/wp02_runtime/wp02_config_freeze.json")

    assert contract["status"] == "PREDECLARED"
    assert contract["source_sha"] == SOURCE_SHA
    assert contract["freeze"]["freeze_id"] == FREEZE_ID
    assert contract["freeze"]["freeze_digest_sha256"] == FREEZE_DIGEST
    assert contract["workload_b"]["input_digest_sha256"] == INPUT_DIGEST
    assert contract["workload_b"]["expected_size"] == {
        "nodes": 1_000_000,
        "elements": 5_821_794,
        "true_dof": 3_000_000,
    }
    assert contract["run_policy"]["post_result_retuning"] is False
    assert contract["run_policy"]["required_runs"] == ["run1", "run2"]
    assert freeze["freeze_id"] == FREEZE_ID
    assert freeze["freeze_digest_sha256"] == FREEZE_DIGEST
    assert freeze["configuration"]["mpi_ranks"] == 8
    assert freeze["configuration"]["partition_strategy"] == "contiguous"
    assert freeze["configuration"]["ksp"] == "cg"
    assert freeze["configuration"]["preconditioner"] == "gamg"


def test_wp03_preflight_is_portable_and_resource_checked() -> None:
    preflight = _read(RUNTIME / "wp03_preflight.json")

    assert preflight["status"] == "PASS"
    assert preflight["workload"]["true_dof"] == 3_000_000
    assert preflight["workload"]["input_digest_sha256"] == INPUT_DIGEST
    assert preflight["checks"]["image_available"] is True
    assert preflight["checks"]["petsc_import"] is True
    assert preflight["checks"]["model_load"] is True
    assert preflight["checks"]["no_oom_injection"] is True
    assert not Path(preflight["checks"]["raw_root"]).is_absolute()


def test_wp03_observatory_replays_satisfy_the_frozen_numerical_contract() -> None:
    summary = _read(RUNTIME / "wp03_summary.json")
    replay = _read(RUNTIME / "wp03_replay_comparison.json")
    index = _read(RUNTIME / "wp03_evidence_index.json")

    assert summary["status"] == "PASS_WITH_LIMITATIONS"
    assert summary["gold_compute"] == "PASS"
    assert summary["numerical_contract"] == {
        "residual": "PASS",
        "equilibrium": "PASS",
        "energy": "PASS",
        "finite_outputs": "PASS",
        "no_nan_inf": True,
        "tolerances_changed": False,
        "post_result_retuning": False,
    }
    assert index["status"] == "PASS_WITH_LIMITATIONS"
    assert index["workload_b"]["true_dof"] == 3_000_000
    assert index["workload_b"]["input_digest_sha256"] == INPUT_DIGEST
    assert index["unmeasured_phases"] == ["preflight", "redistribution", "communication", "io"]

    assert replay["status"] == "PASS"
    assert replay["same_input_digest"] is True
    assert replay["same_configuration_digest"] is True
    assert replay["same_freeze_digest"] is True
    assert replay["same_iterations"] is True
    assert replay["tolerance"] == ACCEPTANCE_TOLERANCE
    assert max(replay["numeric_relative_deltas"].values()) <= ACCEPTANCE_TOLERANCE
    assert replay["post_result_retuning"] is False

    for run_id in ("run1", "run2"):
        record = read_observatory_record(RUNTIME / f"workload_b_{run_id}.json")
        validate_observatory_record(record)
        assert record["source"]["revision"] == SOURCE_SHA
        assert record["source"]["dirty"] is False
        assert record["result"]["classification"] == "PASS"
        assert record["workload"]["dof"] == 3_000_000
        assert record["workload"]["elements"] == 5_821_794
        assert record["execution"]["rank_count"] == 8
        assert record["artifacts"]["input_digest"] == INPUT_DIGEST
        assert record["artifacts"]["freeze_digest_sha256"] == FREEZE_DIGEST
        assert record["metrics"]["residual"] <= 1.0e-8
        assert record["metrics"]["equilibrium"] <= 1.0e-8
        assert record["metrics"]["energy"] <= 1.0e-8
        assert record["result"]["observables"]["finite_outputs"] is True
        assert record["result"]["observables"]["unmeasured_phase_fields"] == [
            "preflight",
            "redistribution",
            "communication",
            "io",
        ]
        timings = record["metrics"]["timings_seconds"]
        assert timings["preflight"] is None
        assert timings["redistribution"] is None
        assert timings["communication"] is None
        assert timings["io"] is None


def test_wp03_keeps_workload_a_control_separate_from_distinct_workload_b() -> None:
    summary = _read(RUNTIME / "wp03_summary.json")
    comparison = _read(RUNTIME / "wp03_workload_comparison.json")

    workload_a = summary["workload_a_control"]
    workload_b = summary["workload_b"]
    assert workload_a["status"] == "CONTROLLED_EXISTING_SILVER"
    assert workload_a["true_dof"] == workload_b["true_dof"] == 3_000_000
    assert workload_a["elements"] == workload_b["elements"] == 5_821_794
    assert workload_a["input_digest_sha256"] != workload_b["input_digest_sha256"]
    assert workload_b["materially_distinct_from_a"] is True
    assert comparison["status"] == "DESCRIPTIVE_PASS"
    assert comparison["comparison_policy"]["performance_comparison_authorized"] is False
    assert comparison["comparison_policy"]["materially_distinct_workloads"] is True


def test_wp03_state_and_governance_are_ready_for_wp04() -> None:
    state = _read(ROOT / "qualification/0_2_7/lu2_wp03_state.json")
    index = _read(ROOT / "qualification/0_2_7/level_up_2_index.json")

    assert state["status"] == "PASS_WITH_LIMITATIONS"
    assert state["gold_compute"] == "PASS"
    assert state["progress"]["level_up_2_acquired_percent"] == 22
    assert state["progress"]["current_global_progress_percent"] == 72
    assert state["progress"]["next_work_package"] == "LU2-WP04"
    assert state["blockers"] == []
    assert index["global_progress"]["current_percent"] == 100
    assert "LU2-WP03" in index["completed_work_packages"]
