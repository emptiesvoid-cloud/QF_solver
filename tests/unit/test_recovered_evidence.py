from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tests.helpers.recovered_evidence import (
    RecoveredEvidenceError,
    load_verified_evidence_bytes,
)


def _fixture(tmp_path: Path, payload: bytes) -> tuple[Path, Path, str]:
    manifest_path = tmp_path / "manifest.json"
    archive_root = tmp_path / "archive"
    archive_subdirectory = Path("0_2_9/wp14/r23_engineering_source_evidence")
    relative_path = Path("qualification/0_2_9/example.json")
    archived_path = archive_root / archive_subdirectory / relative_path
    archived_path.parent.mkdir(parents=True)
    archived_path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    manifest_path.write_text(
        json.dumps(
            {
                "archive_subdirectory": archive_subdirectory.as_posix(),
                "files": [
                    {
                        "repository_path": relative_path.as_posix(),
                        "archive_path": relative_path.as_posix(),
                        "sha256": digest,
                        "size_bytes": len(payload),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest_path, archive_root, digest


def test_reads_only_manifested_bytes_with_matching_hash_and_size(tmp_path: Path) -> None:
    payload = b'{"historical": true}\n'
    manifest, archive, digest = _fixture(tmp_path, payload)

    observed = load_verified_evidence_bytes(
        "qualification/0_2_9/example.json",
        digest,
        manifest_path=manifest,
        archive_root=archive,
    )

    assert observed == payload


def test_rejects_caller_digest_different_from_manifest(tmp_path: Path) -> None:
    manifest, archive, _ = _fixture(tmp_path, b"evidence")

    with pytest.raises(RecoveredEvidenceError, match="does not match caller"):
        load_verified_evidence_bytes(
            "qualification/0_2_9/example.json",
            "0" * 64,
            manifest_path=manifest,
            archive_root=archive,
        )


def test_rejects_changed_archived_bytes(tmp_path: Path) -> None:
    manifest, archive, digest = _fixture(tmp_path, b"original")
    archived_path = (
        archive
        / "0_2_9/wp14/r23_engineering_source_evidence"
        / "qualification/0_2_9/example.json"
    )
    archived_path.write_bytes(b"changed")

    with pytest.raises(RecoveredEvidenceError, match="integrity mismatch"):
        load_verified_evidence_bytes(
            "qualification/0_2_9/example.json",
            digest,
            manifest_path=manifest,
            archive_root=archive,
        )


def test_rejects_archive_path_traversal(tmp_path: Path) -> None:
    manifest, archive, digest = _fixture(tmp_path, b"evidence")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["files"][0]["archive_path"] = "../../outside.json"
    manifest.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(RecoveredEvidenceError, match="escapes"):
        load_verified_evidence_bytes(
            "qualification/0_2_9/example.json",
            digest,
            manifest_path=manifest,
            archive_root=archive,
        )


def test_rejects_archive_subdirectory_traversal(tmp_path: Path) -> None:
    manifest, archive, digest = _fixture(tmp_path, b"evidence")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["archive_subdirectory"] = "../../outside"
    manifest.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(RecoveredEvidenceError, match="escapes"):
        load_verified_evidence_bytes(
            "qualification/0_2_9/example.json",
            digest,
            manifest_path=manifest,
            archive_root=archive,
        )
