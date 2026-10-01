"""Verify and extract the hash-pinned WP14 R2.3 recovered evidence archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPOSITORY_ROOT / "qualification" / "0_2_9" / "wp14" / "wp14_r23_recovered_evidence_manifest.json"
EXPECTED_MANIFEST_SHA256 = "c1f6136f031288438d94fd00fa9a4c8a8d4a429d11aee9c576e0c85ec8ce8836"
EXPECTED_ARCHIVE_SHA256 = "0393475ea1e78dcae2725b4dfcd649a6353c7094a6735efbfe16033a5df58a42"


class RecoveredEvidenceArchiveError(ValueError):
    """Raised when the recovered archive or its manifest is not exact."""


def _safe_relative_path(value: Any, *, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise RecoveredEvidenceArchiveError(f"Invalid {label}: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise RecoveredEvidenceArchiveError(f"Unsafe {label}: {value!r}")
    return path


def prepare_archive(archive_path: Path, archive_root: Path) -> tuple[Path, ...]:
    """Verify the frozen ZIP and every manifest entry before extracting any bytes."""
    manifest_bytes = MANIFEST_PATH.read_bytes()
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
    if manifest_digest != EXPECTED_MANIFEST_SHA256:
        raise RecoveredEvidenceArchiveError(f"Recovered-evidence manifest SHA-256 mismatch: {manifest_digest}")

    archive_digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if archive_digest != EXPECTED_ARCHIVE_SHA256:
        raise RecoveredEvidenceArchiveError(f"Recovered-evidence ZIP SHA-256 mismatch: {archive_digest}")

    manifest = json.loads(manifest_bytes)
    if manifest.get("status") != "RECOVERED_POST_HOC_HASH_VERIFIED":
        raise RecoveredEvidenceArchiveError("Unexpected recovered-evidence manifest status")
    archive_subdirectory = _safe_relative_path(manifest.get("archive_subdirectory"), label="archive subdirectory")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise RecoveredEvidenceArchiveError("Manifest files must be a non-empty list")

    expected: dict[str, dict[str, Any]] = {}
    for entry in files:
        if not isinstance(entry, dict):
            raise RecoveredEvidenceArchiveError("Manifest file entry must be an object")
        relative_path = _safe_relative_path(entry.get("archive_path"), label="archive path")
        name = relative_path.as_posix()
        digest = entry.get("sha256")
        size = entry.get("size_bytes")
        if (
            name in expected
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest.lower())
            or not isinstance(size, int)
            or isinstance(size, bool)
            or size < 0
        ):
            raise RecoveredEvidenceArchiveError(f"Invalid or duplicate manifest entry: {name}")
        expected[name] = {"sha256": digest.lower(), "size_bytes": size}

    verified_payloads: list[tuple[PurePosixPath, bytes]] = []
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        names = [member.filename for member in members]
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise RecoveredEvidenceArchiveError("ZIP members do not exactly match the manifest")

        for member in members:
            relative_path = _safe_relative_path(member.filename, label="ZIP member")
            if member.is_dir() or member.flag_bits & 0x1:
                raise RecoveredEvidenceArchiveError(f"Unsupported ZIP member: {member.filename}")
            unix_mode = member.external_attr >> 16
            file_type = stat.S_IFMT(unix_mode)
            if file_type not in {0, stat.S_IFREG}:
                raise RecoveredEvidenceArchiveError(f"Non-regular ZIP member: {member.filename}")

            record = expected[relative_path.as_posix()]
            if member.file_size != record["size_bytes"]:
                raise RecoveredEvidenceArchiveError(f"ZIP size mismatch for {member.filename}: {member.file_size}")
            payload = archive.read(member)
            digest = hashlib.sha256(payload).hexdigest()
            if digest != record["sha256"]:
                raise RecoveredEvidenceArchiveError(f"ZIP payload SHA-256 mismatch for {member.filename}: {digest}")
            verified_payloads.append((relative_path, payload))

    root = archive_root.resolve()
    destination_base = (root / Path(*archive_subdirectory.parts)).resolve()
    try:
        destination_base.relative_to(root)
    except ValueError as error:
        raise RecoveredEvidenceArchiveError("Destination escapes the archive root") from error

    destinations: list[Path] = []
    for relative_path, payload in verified_payloads:
        destination = (destination_base / Path(*relative_path.parts)).resolve()
        try:
            destination.relative_to(destination_base)
        except ValueError as error:
            raise RecoveredEvidenceArchiveError("Extracted path escapes the archive directory") from error
        if destination.exists() and destination.read_bytes() != payload:
            raise RecoveredEvidenceArchiveError(f"Refusing to overwrite differing file: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            destination.write_bytes(payload)
        destinations.append(destination)

    return tuple(destinations)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--archive-root", required=True, type=Path)
    arguments = parser.parse_args()
    paths = prepare_archive(arguments.archive, arguments.archive_root)
    print(f"Verified and extracted {len(paths)} WP14 recovered-evidence files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
