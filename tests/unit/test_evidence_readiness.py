from __future__ import annotations

import json
from pathlib import Path

from solveur.io.manifest import sha256
from solveur.verification.evidence_readiness import controlled_evidence_checks


def _write_bundle(root: Path) -> Path:
    bundle = root / "bundle"
    bundle.mkdir()
    payload = bundle / "summary.json"
    payload.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    manifest = {
        "manifest_schema_version": 2,
        "source": {"repository": ".", "revision": "test", "dirty": False},
        "runtime": {"python": {"version": "test"}},
        "locked_environments": [{"path": "requirements/test.txt", "sha256": "test"}],
        "command_line": ["test"],
        "input_sha256": "test-input",
        "traceability": {"scope": "test", "status": "READY_FOR_OWNER_REVIEW"},
        "file_count": 1,
        "files": [
            {
                "role": "summary",
                "path": "summary.json",
                "size_bytes": payload.stat().st_size,
                "sha256": sha256(payload),
            }
        ],
    }
    (bundle / "evidence_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return bundle


def test_controlled_evidence_check_passes_for_valid_bundle(tmp_path: Path) -> None:
    _write_bundle(tmp_path)

    checks = controlled_evidence_checks(
        {"evidence_bundles": [{"id": "sample", "path": "bundle", "required": True}]},
        tmp_path,
    )

    assert checks[0]["status"] == "PASS"
    assert checks[0]["checked_file_count"] == 1


def test_controlled_evidence_check_fails_for_missing_required_bundle(tmp_path: Path) -> None:
    checks = controlled_evidence_checks(
        {"evidence_bundles": [{"id": "missing", "path": "missing", "required": True}]},
        tmp_path,
    )

    assert checks[0]["status"] == "FAIL"
    assert checks[0]["manifest_status"] == "FAIL"
