from __future__ import annotations

import json

import matplotlib.image as mpimg

from solveur.api import run_mitc4_validation


def test_mitc4_quick_campaign_writes_reviewable_evidence(tmp_path) -> None:
    summary = run_mitc4_validation(tmp_path, quick=True)

    assert summary["status"] == "PASS_INTERNAL"
    assert summary["shear_locking"]["status"] == "PASS"
    assert summary["modal"]["status"] == "PASS"
    assert summary["newmark"]["status"] == "PASS"
    assert summary["abaqus_correlation"]["status"] == "PENDING"
    assert summary["abaqus_correlation"]["pinched_cylinder"]["status"] == "NOT_RUN"
    assert summary["review"]["decision"] == "accepted_with_reservations"
    assert summary["review"]["internal_validation_status"] == "validated_with_recommendations"
    expected = (
        "campaign_summary.json",
        "vnv_manifest.json",
        "VNV-MITC4-PATCH-001.md",
        "VNV-MITC4-SHEAR-LOCKING-001.md",
        "VNV-MITC4-SHEAR-LOCKING-001.png",
        "VNV-MITC4-MODAL-001.md",
        "VNV-MITC4-MODAL-001.png",
        "VNV-MITC4-NEWMARK-001.md",
        "VNV-MITC4-NEWMARK-001.png",
    )
    assert all((tmp_path / name).is_file() for name in expected)
    assert all((tmp_path / name).stat().st_size > 100 for name in expected)
    assert mpimg.imread(tmp_path / "VNV-MITC4-MODAL-001.png").std() > 0.0
    manifest = json.loads((tmp_path / "vnv_manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["files"]) >= len(expected) - 1
