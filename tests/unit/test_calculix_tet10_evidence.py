from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_controlled_calculix_tet10_evidence_is_complete() -> None:
    reference = ROOT / "qualification" / "vnv" / "external" / "calculix_tet10" / "reference"
    summary = json.loads((reference / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((reference / "vnv_manifest.json").read_text(encoding="utf-8"))

    assert summary["study_id"] == "VNV-TET10-CALCULIX-C3D10-014"
    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert summary["full_displacement_relative_difference"] < 1.0e-4
    assert summary["twist_relative_difference"] < 1.0e-4
    for entry in manifest["files"]:
        artifact = reference / entry["path"]
        assert artifact.is_file(), entry["path"]
        assert artifact.stat().st_size == entry["size_bytes"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == entry["sha256"]
