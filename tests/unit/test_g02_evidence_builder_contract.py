"""Structural contracts for the refactored controlled G02 evidence builder."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def test_g02_builder_keeps_the_controlled_output_and_manifest_contract(tmp_path, monkeypatch) -> None:
    sys.path.insert(0, str(SCRIPTS))
    try:
        import build_g02_evidence as builder
        import g02_evidence_publication as publication
    finally:
        sys.path.remove(str(SCRIPTS))

    output = tmp_path / "out"
    output.mkdir()
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    monkeypatch.setattr(builder, "OUT", output)
    artifact = output / "summary.json"
    artifact.write_text("controlled evidence\n", encoding="utf-8")

    manifest = builder.manifest("source-sha", False, "2026-08-28T00:00:00Z")

    assert publication.OUT == ROOT / "results" / "vnv_0_2_5" / "g02_latest"
    assert manifest["command"] == "python scripts/build_g02_evidence.py"
    assert manifest["source_sha"] == "source-sha"
    assert manifest["dirty"] is False
    assert manifest["files"] == [
        {
            "path": str(Path("out") / "summary.json"),
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            "bytes": artifact.stat().st_size,
        }
    ]
