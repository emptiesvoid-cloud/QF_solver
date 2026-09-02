"""Targeted contract checks for the LU2-WP04 Bronze evidence path."""

from __future__ import annotations

import json
from pathlib import Path

from solveur.verification.observatory import read_observatory_record


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


def test_wp04_evidence_has_two_replays_and_no_solve() -> None:
    summary = _read(RUNTIME / "wp04_summary.json")
    replay = _read(RUNTIME / "wp04_replay_comparison.json")
    index = _read(RUNTIME / "wp04_evidence_index.json")
    assert summary["status"] == "PASS_WITH_LIMITATIONS"
    assert summary["bronze"] == "PASS"
    assert summary["workload"]["true_dof"] == 5_012_640
    assert summary["readiness"]["solve_executed"] is False
    assert summary["c1_matrix_free_trigger"] is False
    assert replay["status"] == "PASS"
    assert all(replay["checks"].values())
    assert index["status"] == "PASS_WITH_LIMITATIONS"

    for run_id in ("run1", "run2"):
        record = read_observatory_record(RUNTIME / f"workload_5m_{run_id}.json")
        assert record["result"]["classification"] == "PASS"
        assert record["workload"]["dof"] == 5_012_640
        assert record["workload"]["elements"] == 9_773_946
        assert record["execution"]["rank_count"] == 8
        assert record["execution"]["preconditioner"] == "GAMG"
        assert record["result"]["observables"]["pc_ready"] is True
        assert record["result"]["observables"]["solve_executed"] is False
        assert record["metrics"]["iterations"] is None
        assert record["metrics"]["timings_seconds"]["ksp_solve"] is None
