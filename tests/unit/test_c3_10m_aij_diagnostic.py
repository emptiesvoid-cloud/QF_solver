"""Contracts for the non-blocking C3 10M AIJ diagnostic evidence."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "qualification" / "0_2_7" / "c3_10m_aij_diagnostic.json"
ASSEMBLER = ROOT / "src" / "solveur" / "large" / "assembler.py"
RUNNER = ROOT / "scripts" / "run_lu2_wp04_bronze.py"


def test_c3_owner_stop_remains_diagnostic_not_a_capacity_failure() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert evidence["status"] == "OWNER_TERMINATED_FOR_DIAGNOSTIC"
    assert evidence["owner_terminated_run"]["insertion_reached_100_percent"] is True
    assert evidence["owner_terminated_run"]["pc_ready_global_observed"] is False
    assert evidence["classification"] == {
        "capacity_failure_proven": False,
        "resource_limited_proven": False,
        "oom_proven": False,
        "petsc_mpi_failure_proven": False,
        "deadlock_proven": False,
        "numerical_failure_proven": False,
        "root_cause_proven": False,
    }


def test_c3_evidence_requires_phase_resolved_per_rank_instrumentation() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    markers = set(evidence["instrumentation"]["markers"])
    expected = {
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
        "PC_READY_GLOBAL",
        "FINALIZE_ENTER",
        "FINALIZE_EXIT",
        "EXCEPTION",
    }

    assert expected <= markers
    assert evidence["instrumentation"]["per_rank_independent"] is True
    assert evidence["instrumentation"]["fail_safe"] is True
    assert evidence["instrumentation"]["no_collective_marker_writes"] is True


def test_c3_source_contains_all_post_insertion_boundaries() -> None:
    source = ASSEMBLER.read_text(encoding="utf-8") + RUNNER.read_text(encoding="utf-8")

    for marker in json.loads(EVIDENCE.read_text(encoding="utf-8"))["instrumentation"]["markers"]:
        assert marker in source


def test_c3_diagnostic_does_not_claim_a_behavioral_fix() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert evidence["decision"]["behavioral_patch_applied"] is False
    assert evidence["execution"]["numerical_formulation_changed"] is False
    assert evidence["execution"]["wp02_freeze_changed"] is False
    assert evidence["decision"]["ready_for_luna_c3_10m_replay"] is True
