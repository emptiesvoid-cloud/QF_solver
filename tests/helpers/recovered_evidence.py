"""Read hash-pinned historical evidence from the external evidence archive."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
    ROOT
    / "qualification"
    / "0_2_9"
    / "wp14"
    / "wp14_r23_recovered_evidence_manifest.json"
)


class RecoveredEvidenceError(ValueError):
    """Raised when archived evidence is absent, unbound, or has changed."""


def load_verified_evidence_bytes(
    repository_path: str,
    expected_sha256: str,
    *,
    manifest_path: Path = MANIFEST_PATH,
    archive_root: Path | None = None,
) -> bytes:
    """Load exact archived bytes only when path, size, and SHA-256 all agree."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    normalized_repo_path = PurePosixPath(repository_path).as_posix()
    matches = [
        entry
        for entry in manifest["files"]
        if entry["repository_path"] == normalized_repo_path
    ]
    if len(matches) != 1:
        raise RecoveredEvidenceError(
            f"Expected one archive manifest entry for {normalized_repo_path}; "
            f"found {len(matches)}"
        )

    entry: dict[str, Any] = matches[0]
    expected = expected_sha256.lower()
    if entry["sha256"].lower() != expected:
        raise RecoveredEvidenceError(
            f"Manifest digest for {normalized_repo_path} does not match caller"
        )

    relative_archive_path = PurePosixPath(entry["archive_path"])
    relative_archive_subdirectory = PurePosixPath(manifest["archive_subdirectory"])
    if any(
        path.is_absolute() or ".." in path.parts
        for path in (relative_archive_path, relative_archive_subdirectory)
    ):
        raise RecoveredEvidenceError("Archive path escapes its declared root")

    if archive_root is None:
        configured_root = os.environ.get("QF_SOLVER_EVIDENCE_ARCHIVE_ROOT")
        archive_root = (
            Path(configured_root)
            if configured_root
            else ROOT.parent / manifest["archive_root_default_relative_to_repository_parent"]
        )
    archive_base = (
        archive_root / Path(*relative_archive_subdirectory.parts)
    ).resolve()
    try:
        archive_base.relative_to(archive_root.resolve())
    except ValueError as exc:
        raise RecoveredEvidenceError("Archive subdirectory escapes its root") from exc
    try:
        archived_path = (archive_base / Path(*relative_archive_path.parts)).resolve(
            strict=True
        )
    except FileNotFoundError as exc:
        raise RecoveredEvidenceError(
            f"Archived evidence is unavailable for {normalized_repo_path}; "
            "provide the controlled archive with QF_SOLVER_EVIDENCE_ARCHIVE_ROOT"
        ) from exc
    try:
        archived_path.relative_to(archive_base)
    except ValueError as exc:
        raise RecoveredEvidenceError("Resolved archive path escapes its root") from exc

    payload = archived_path.read_bytes()
    actual = hashlib.sha256(payload).hexdigest()
    if len(payload) != entry["size_bytes"] or actual != expected:
        raise RecoveredEvidenceError(
            f"Archived evidence integrity mismatch for {normalized_repo_path}: "
            f"size={len(payload)}, sha256={actual}"
        )
    return payload
