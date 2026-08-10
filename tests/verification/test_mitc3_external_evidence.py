from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load(relative: str) -> dict[str, object]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_controlled_mitc3_code_aster_evidence_passes() -> None:
    summary = _load(
        "qualification/vnv/external/code_aster_mitc3/reference_v2/summary.json"
    )
    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    cases = {row["id"]: row for row in summary["cases"]}
    assert cases["membrane"]["difference"] < 1.0e-6
    assert cases["bending"]["difference"] < 1.0e-4


def test_controlled_mitc3_calculix_evidence_preserves_warning() -> None:
    summary = _load(
        "qualification/vnv/external/calculix_mitc3/reference_v2/summary.json"
    )
    assert summary["status"] == "WARNING"
    cases = {row["id"]: row for row in summary["cases"]}
    assert cases["membrane"]["difference"] < 1.0e-3
    assert cases["bending"]["difference"] > 1.0


def test_controlled_mitc3_external_manifests_match_files() -> None:
    for family in ("code_aster_mitc3", "calculix_mitc3"):
        root = ROOT / "qualification" / "vnv" / "external" / family / "reference_v2"
        manifest = json.loads((root / "vnv_manifest.json").read_text(encoding="utf-8"))
        for entry in manifest["files"]:
            path = root / entry["path"]
            assert path.is_file()
            assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]


def test_refined_curved_shell_evidence_is_controlled_and_converged() -> None:
    root = ROOT / "qualification" / "vnv" / "mitc3" / "refined_h20k"
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["cases"]["scordelis"]["mesh"]["elements"] == 20_000
    assert summary["cases"]["scordelis"]["relative_error"] < 0.01
    assert summary["cases"]["pinched"]["mesh"]["elements"] == 19_600
    assert summary["cases"]["pinched"]["relative_error"] < 0.03
    manifest = json.loads((root / "vnv_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        path = root / entry["path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
