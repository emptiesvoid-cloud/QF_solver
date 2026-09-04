from __future__ import annotations

import json

from solveur.verification.observatory import read_observatory_record, validate_observatory_record

from scripts.collect_lu2_wp02_evidence import ROOT, _rss_imbalance


def test_wp02_contract_freezes_required_route_and_metrics() -> None:
    contract = json.loads((ROOT / "qualification/0_2_7/wp02_execution_contract.json").read_text(encoding="utf-8"))

    assert contract["status"] == "PREDECLARED"
    assert contract["fixed_solver_configuration"]["rank_targets"] == [2, 4, 8]
    assert contract["fixed_solver_configuration"]["petsc_options"]["ksp_rtol"] == 1e-10
    assert contract["mpi_v2"]["strong_scaling_workload"].startswith("same 3M")
    assert "communication" in contract["phase_metrics"]["required"]
    assert "communication" in contract["phase_metrics"]["unmeasured_values"]
    assert contract["acceptance"]["post_result_retuning"] is False
    assert contract["acceptance"]["silent_fallback"] is False


def test_wp02_rss_imbalance_is_deterministic() -> None:
    assert _rss_imbalance([100, 120, 110, 100]) == 120 / 107.5 - 1
    assert _rss_imbalance([]) is None


def test_wp02_controlled_records_are_valid_and_phase_gaps_are_explicit() -> None:
    runtime = ROOT / "qualification" / "0_2_7" / "wp02_runtime"
    index = json.loads((runtime / "wp02_evidence_index.json").read_text(encoding="utf-8"))

    assert len(index["runs"]) == 8
    assert {run["status"] for run in index["runs"]} == {"PASS"}
    assert {run["phase_metrics"]["communication"] for run in index["runs"]} == {None}
    assert {run["phase_metrics"]["redistribution"] for run in index["runs"]} == {None}

    for run in index["runs"]:
        record = read_observatory_record(ROOT / run["record"])
        validate_observatory_record(record)
        assert record["source"]["revision"] == "3cb817c9391ef7998c5950d3071c8d9ce1be5dd8"
        assert record["result"]["classification"] == "PASS"
        assert record["metrics"]["timings_seconds"]["communication"] is None
        assert record["metrics"]["timings_seconds"]["io"] is None
        assert record["metrics"]["post_timings_seconds"]["reactions"] is not None
        assert record["metrics"]["post_timings_seconds"]["energy"] is not None


def test_wp02_freeze_is_reproducible_and_bounded() -> None:
    runtime = ROOT / "qualification" / "0_2_7" / "wp02_runtime"
    freeze = json.loads((runtime / "wp02_config_freeze.json").read_text(encoding="utf-8"))
    state = json.loads((ROOT / "qualification" / "0_2_7" / "wp02_state.json").read_text(encoding="utf-8"))

    assert freeze["status"] == "FROZEN_FOR_LU2_WP03_WP04_WP05"
    assert freeze["configuration"]["backend"] == "petsc"
    assert freeze["configuration"]["ksp"] == "cg"
    assert freeze["configuration"]["preconditioner"] == "gamg"
    assert freeze["configuration"]["mpi_ranks"] == 8
    assert freeze["freeze_id"] == "LU2-WP02-FREEZE-bfd1975b012453a3"
    assert state["status"] == "PASS_WITH_LIMITATIONS"
    assert state["readiness"]["ready_for_lu2_wp03"] is True
