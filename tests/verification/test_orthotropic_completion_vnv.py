from __future__ import annotations

import hashlib
import json
from pathlib import Path

from solveur.verification.orthotropic_performance import OrthotropicIsotropicPerformanceCampaign


ROOT = Path(__file__).resolve().parents[2]


def test_orthotropic_isotropic_performance_campaign_passes(tmp_path: Path) -> None:
    summary = OrthotropicIsotropicPerformanceCampaign(tmp_path).run()
    assert summary["status"] == "PASS_NON_REGRESSION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert (tmp_path / "report.md").is_file()
    assert (tmp_path / "vnv_manifest.json").is_file()


def test_controlled_orthotropic_convergence_evidence_is_complete() -> None:
    reference = ROOT / "qualification" / "vnv" / "orthotropic_solid_convergence" / "reference"
    summary = json.loads((reference / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((reference / "vnv_manifest.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert summary["covered_specifications"] == ["SPEC-COMP-SOLID-006"]
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert len(summary["families"]["TET4"]) == 6
    assert len(summary["families"]["TET10"]) == 4
    tet4_counts = [row["elements"] for row in summary["families"]["TET4"]]
    assert 4_500 <= tet4_counts[-2] <= 5_500
    assert 9_000 <= tet4_counts[-1] <= 11_000
    for entry in manifest["files"]:
        artifact = reference / entry["path"]
        assert artifact.is_file(), entry["path"]
        assert artifact.stat().st_size == entry["size_bytes"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == entry["sha256"]


def test_controlled_orthotropic_performance_evidence_is_complete() -> None:
    reference = ROOT / "qualification" / "vnv" / "orthotropic_isotropic_performance" / "reference"
    summary = json.loads((reference / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((reference / "vnv_manifest.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS_NON_REGRESSION"
    assert summary["covered_specifications"] == ["SPEC-COMP-SOLID-008"]
    assert all(check["status"] == "PASS" for check in summary["checks"])
    for entry in manifest["files"]:
        artifact = reference / entry["path"]
        assert artifact.is_file(), entry["path"]
        assert artifact.stat().st_size == entry["size_bytes"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == entry["sha256"]
