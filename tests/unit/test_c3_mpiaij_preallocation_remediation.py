"""Controlled-proof checks for the bounded C3 MPIAIJ remediation."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "qualification" / "0_2_7" / "c3_10m_mpiaij_preallocation_remediation.json"


def _load() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_c3_remediation_preserves_the_owner_terminated_10m_classification() -> None:
    evidence = _load()
    historical = evidence["historical_10m_replay"]

    assert evidence["artifact_classification"] == "CONTROLLED_PROOF"
    assert evidence["status"] == "PASS_WITH_LIMITATIONS"
    assert historical["status"] == "OWNER_TERMINATED_FOR_DIAGNOSTIC"
    assert historical["dominant_phase"] == "ASSEMBLE_1"
    assert historical["capacity_failure_proven"] is False
    assert historical["resource_limited_proven"] is False


def test_c3_remediation_records_exact_preallocation_and_equivalence() -> None:
    evidence = _load()
    preallocation = evidence["preallocation_contract"]
    medium = evidence["representative_mpi_evidence"]["medium"]

    assert preallocation["before"]["nnz"] == 120
    assert preallocation["after"]["diag_offdiag_preallocation"] == "EXACT_STRUCTURED_STENCIL"
    assert medium["matrix_relative_difference"] == 0.0
    assert medium["rhs_relative_difference"] == 0.0
    assert medium["iterations_before_after"][0] == medium["iterations_before_after"][1]
    assert medium["mallocs_before_after"] == [131670, 0]
    assert medium["nz_allocated_before_after"][1] == medium["nz_used_before_after"][1]
    assert medium["assemble_1_speedup"] > 100.0
