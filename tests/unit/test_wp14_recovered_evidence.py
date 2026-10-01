from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from scripts import prepare_wp14_recovered_evidence as recovered


def _write_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    entries: dict[str, bytes],
) -> tuple[Path, Path, Path]:
    manifest_path = tmp_path / "manifest.json"
    archive_path = tmp_path / "evidence.zip"
    archive_root = tmp_path / "archive-root"
    manifest = {
        "status": "RECOVERED_POST_HOC_HASH_VERIFIED",
        "archive_subdirectory": "0_2_9/wp14/r23_engineering_source_evidence",
        "files": [
            {
                "repository_path": f"qualification/{name}",
                "archive_path": f"qualification/{name}",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
            for name, payload in entries.items()
        ],
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries.items():
            archive.writestr(f"qualification/{name}", payload)

    monkeypatch.setattr(recovered, "MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(
        recovered,
        "EXPECTED_MANIFEST_SHA256",
        hashlib.sha256(manifest_bytes).hexdigest(),
    )
    monkeypatch.setattr(
        recovered,
        "EXPECTED_ARCHIVE_SHA256",
        hashlib.sha256(archive_path.read_bytes()).hexdigest(),
    )
    return archive_path, archive_root, manifest_path


def test_prepare_archive_verifies_manifest_and_extracts_exact_payloads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payloads = {"first.json": b'{"result":"PASS"}', "second.json": b"evidence"}
    archive_path, archive_root, _ = _write_bundle(tmp_path, monkeypatch, payloads)

    extracted = recovered.prepare_archive(archive_path, archive_root)

    expected_root = archive_root / "0_2_9/wp14/r23_engineering_source_evidence/qualification"
    assert set(extracted) == {expected_root / name for name in payloads}
    assert {path.name: path.read_bytes() for path in extracted} == payloads


def test_prepare_archive_fails_before_extracting_when_payload_hash_differs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_path, archive_root, manifest_path = _write_bundle(tmp_path, monkeypatch, {"record.json": b"expected"})
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["sha256"] = hashlib.sha256(b"different").hexdigest()
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)
    monkeypatch.setattr(recovered, "EXPECTED_MANIFEST_SHA256", hashlib.sha256(manifest_bytes).hexdigest())

    with pytest.raises(recovered.RecoveredEvidenceArchiveError, match="payload SHA-256 mismatch"):
        recovered.prepare_archive(archive_path, archive_root)

    assert not archive_root.exists()


def test_prepare_archive_rejects_path_traversal_in_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    archive_path, archive_root, manifest_path = _write_bundle(tmp_path, monkeypatch, {"record.json": b"expected"})
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["archive_path"] = "../escape.json"
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)
    monkeypatch.setattr(recovered, "EXPECTED_MANIFEST_SHA256", hashlib.sha256(manifest_bytes).hexdigest())

    with pytest.raises(recovered.RecoveredEvidenceArchiveError, match="Unsafe archive path"):
        recovered.prepare_archive(archive_path, archive_root)

    assert not archive_root.exists()


def test_prepare_archive_rejects_unlisted_zip_members(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    archive_path, archive_root, _ = _write_bundle(tmp_path, monkeypatch, {"record.json": b"expected"})
    with zipfile.ZipFile(archive_path, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("qualification/unlisted.json", b"extra")
    monkeypatch.setattr(
        recovered,
        "EXPECTED_ARCHIVE_SHA256",
        hashlib.sha256(archive_path.read_bytes()).hexdigest(),
    )

    with pytest.raises(recovered.RecoveredEvidenceArchiveError, match="do not exactly match"):
        recovered.prepare_archive(archive_path, archive_root)

    assert not archive_root.exists()
