from __future__ import annotations

import json
from pathlib import Path

from scripts.package_internal_vnv_evidence import package_internal_vnv
from solveur.io.evidence_verifier import EvidenceBundleVerifier


def test_internal_vnv_package_sanitizes_and_verifies(tmp_path: Path) -> None:
    source = tmp_path / "linear_dynamic_families"
    family = source / "tet4"
    family.mkdir(parents=True)
    (family / "summary.json").write_text(
        json.dumps({"study_id": "VNV-TET4-001", "family": "TET4", "status": "PASS"}),
        encoding="utf-8",
    )
    (family / "report.md").write_text("# PASS\n", encoding="utf-8")
    # A raw runner manifest is intentionally not copied into the public bundle.
    (family / "vnv_manifest.json").write_text(
        json.dumps({"runtime": {"python": {"executable": "C:/private/python.exe"}}}),
        encoding="utf-8",
    )

    output = package_internal_vnv(source, tmp_path / "bundle")
    report = EvidenceBundleVerifier().verify(output)
    assert report.status == "PASS"
    assert (output / "tet4" / "summary.json").is_file()
    assert not (output / "tet4" / "vnv_manifest.json").exists()

    manifest = json.loads((output / "evidence_manifest.json").read_text(encoding="utf-8"))
    encoded = json.dumps(manifest)
    assert "private/python.exe" not in encoded
    assert "executable" not in manifest["runtime"]["python"]
    assert "processor" not in manifest["runtime"]["platform"]


def test_internal_vnv_package_rejects_non_pass_family(tmp_path: Path) -> None:
    source = tmp_path / "families" / "tet4"
    source.mkdir(parents=True)
    (source / "summary.json").write_text(
        json.dumps({"study_id": "VNV-TET4-001", "family": "TET4", "status": "WARNING"}),
        encoding="utf-8",
    )
    (source / "report.md").write_text("# WARNING\n", encoding="utf-8")

    try:
        package_internal_vnv(source.parent, tmp_path / "bundle")
    except ValueError as exc:
        assert "PASS family studies" in str(exc)
    else:
        raise AssertionError("non-PASS family must not enter the controlled bundle")
