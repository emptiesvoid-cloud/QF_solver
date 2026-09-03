"""Controlled-proof checks for the frozen C3 10M replay."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "qualification" / "0_2_7" / "c3_10m_runtime"
MARKERS = [
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
    "PC_READY",
    "PC_READY_GLOBAL",
    "PRE_MEMORY_GATHER",
    "POST_MEMORY_GATHER",
    "FINALIZE_ENTER",
    "FINALIZE_EXIT",
]


def _load(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_c3_frozen_bronze_replay_is_complete_and_preallocated() -> None:
    summary = _load("c3_10m_replay_summary.json")
    bronze = _load("c3_10m_bronze_run1_raw.json")

    assert summary["status"] == "PASS"
    assert summary["workload"]["dof"] == 10_125_000
    assert summary["workload"]["elements"] == 19_847_694
    assert summary["configuration"]["freeze_id"] == "LU2-WP02-FREEZE-bfd1975b012453a3"
    assert summary["configuration"]["tolerances_unchanged"] is True
    assert bronze["status"] == "PASS"
    assert bronze["petsc"]["global_readiness"]
    assert bronze["petsc"]["pc_ready"] is True
    assert bronze["checks"]["no_silent_fallback"] is True
    assert bronze["resources"]["peak_rss_per_rank_bytes"] > 0
    matrix = bronze["matrix"]["info"]
    assert matrix["mallocs"] == 0.0
    assert matrix["nz_allocated"] == matrix["nz_used"]
    assert matrix["nz_unneeded"] == 0.0


def test_c3_rank_telemetry_has_complete_order_without_exceptions() -> None:
    for path in sorted(EVIDENCE.glob("wp04_5m_progress.rank*.jsonl")):
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        suffixes = [event["event"].split("_", 2)[2] for event in events]
        assert suffixes == MARKERS
        assert not any(event["event"].endswith("_EXCEPTION") for event in events)
        assert all("rank" in event and "rank_count" in event for event in events)


def test_c3_optional_complete_solve_passed_without_changing_scope() -> None:
    summary = _load("c3_10m_replay_summary.json")
    solve = summary["optional_complete_solve"]

    assert solve["attempted"] is True
    assert solve["status"] == "PASS"
    assert solve["converged"] is True
    assert solve["finite_outputs"] is True
    assert solve["clean_exit"] is True
    assert summary["claims"]["excluded"]
