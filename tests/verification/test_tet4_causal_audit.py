"""Regression checks for the TET4 static causal audit evidence."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_tet4_causal_audit_records_the_refined_one_percent_gate() -> None:
    path = ROOT / "qualification/vnv/tet4_static_causal_audit_2026-08-21.json"
    audit = json.loads(path.read_text(encoding="utf-8"))

    assert audit["scope"] == "tet4-linear-static"
    assert audit["conclusion"]["time_step_cause"] is False
    assert audit["conclusion"]["implementation_agreement_with_code_aster"] == "confirmed"
    assert audit["gate"]["status"] == "PASS_TECHNICAL_OWNER_REVIEW"
    assert audit["gate"]["latest_relative_error"] <= audit["gate"]["relative_error_limit"]
    assert audit["evidence"]["structured_petsc_refinement"]["relative_residual"] < 1.0e-8
    external = audit["evidence"]["external_code_aster_tetra10"]
    assert external["qf_tet10_to_code_aster_tetra10_difference"] < 1.0e-10
    assert external["qf_tet4_to_code_aster_tetra10_difference"] > 0.01


def test_tet4_causal_audit_references_existing_evidence() -> None:
    path = ROOT / "qualification/vnv/tet4_static_causal_audit_2026-08-21.json"
    audit = json.loads(path.read_text(encoding="utf-8"))

    for item in audit["evidence"].values():
        evidence_path = ROOT / item["path"]
        assert evidence_path.is_file(), item["path"]
