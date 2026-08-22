"""Controlled evidence contract for the Code_Aster J2 correlation."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_controlled_code_aster_j2_digest_passes() -> None:
    path = ROOT / "qualification" / "external_reference_digests" / "code_aster_j2.json"
    summary = json.loads(path.read_text(encoding="utf-8"))

    assert summary["study_id"] == "VNV-J2-CODEASTER-VMIS-ISOT-LINE-004"
    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert summary["external_solver"]["name"] == "Code_Aster"
    assert summary["external_solver"]["version"] == "18.1.0"
    assert summary["external_solver"]["relation"] == "VMIS_ISOT_LINE"
    assert summary["external_solver"]["deformation"] == "PETIT"
    assert summary["external_solver"]["image"].startswith("simvia/code_aster@sha256:")
    assert len(summary["evidence_manifest_sha256"]) == 64
    assert all(check["status"] == "PASS" for check in summary["checks"])


def test_tet4_structural_code_aster_evidence_is_archived() -> None:
    path = (
        ROOT
        / "qualification"
        / "vnv"
        / "external"
        / "code_aster_tet4_j2_complex"
        / "reference"
        / "summary.json"
    )
    summary = json.loads(path.read_text(encoding="utf-8"))

    assert summary["study_id"] == "VNV-TET4-J2-CODEASTER-COMPLEX-027"
    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert summary["external_solver"]["element"] == "TETRA4"
    assert summary["qf_solver"]["element"] == "TET4"
    assert summary["model"]["same_mesh"] is True
    assert summary["model"]["same_combined_loads"] is True
    assert summary["checks"][0]["value"] <= 0.01
    assert summary["checks"][1]["value"] <= 0.01
    assert summary["checks"][2]["value"] <= 0.01
    assert summary["checks"][4]["value"] <= 1e-7
    assert all(check["status"] == "PASS" for check in summary["checks"])
