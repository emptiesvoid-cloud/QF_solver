"""Controlled evidence contract for orthotropic singular-stress acceptance."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_controlled_orthotropic_singular_stress_digest_passes() -> None:
    path = (
        ROOT
        / "qualification"
        / "external_reference_digests"
        / "orthotropic_singular_stress_h8.json"
    )
    summary = json.loads(path.read_text(encoding="utf-8"))

    assert summary["study_id"] == "VNV-ORTHOTROPIC-SINGULAR-STRESS-005"
    assert summary["status"] == "PASS_STRESS_ACCEPTANCE"
    assert summary["acceptance_policy_revision"] == 2
    assert len(summary["evidence_manifest_sha256"]) == 64
    assert len(summary["cases"]) == 2
    for case in summary["cases"]:
        assert case["levels"] == 8
        assert case["assessment"]["status"] == "PASS"
        assert all(check["status"] == "PASS" for check in case["assessment"]["checks"])
        assert case["fine_code_aster_check"]["status"] == "PASS"

    reentrant = next(case for case in summary["cases"] if case["id"] == "reentrant_corner")
    assert reentrant["fine_mesh"]["elements"] > 200_000
    assert reentrant["fine_calculix_nodal_check"]["status"] == "WARNING"
