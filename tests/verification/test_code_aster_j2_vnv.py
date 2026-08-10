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
    assert summary["external_solver"] == {
        "name": "Code_Aster",
        "version": "18.1.0",
        "relation": "VMIS_ISOT_LINE",
        "deformation": "PETIT",
    }
    assert len(summary["evidence_manifest_sha256"]) == 64
    assert all(check["status"] == "PASS" for check in summary["checks"])
