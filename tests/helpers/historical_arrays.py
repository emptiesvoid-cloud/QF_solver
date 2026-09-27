"""Read historical arrays from exact local bytes or a hash-bound archive."""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import re

from tests.helpers.recovered_evidence import RecoveredEvidenceError, load_verified_evidence_bytes


class HistoricalArrayError(ValueError):
    """The original array bytes are unavailable or fail their frozen binding."""


def load_historical_array_bytes(
    repository_path: str,
    sha256: str,
    size_bytes: int,
    *,
    root: Path,
    manifest_path: Path | None = None,
    archive_root: Path | None = None,
) -> bytes:
    """Reject corruption; never regenerate data or fall back past local tampering."""
    relative = PurePosixPath(repository_path)
    if (
        relative.is_absolute() or any(part in ("", ".", "..") for part in repository_path.split("/"))
        or "\\" in repository_path or ":" in repository_path
        or not re.fullmatch(r"[0-9a-fA-F]{64}", sha256)
        or isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes < 1
    ):
        raise HistoricalArrayError("Invalid historical array binding.")
    path = root / Path(*relative.parts)
    if path.exists() or path.is_symlink():
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(root.resolve())
            if not resolved.is_file() or path.is_symlink():
                raise HistoricalArrayError("Non-regular historical array path.")
            payload = resolved.read_bytes()
        except (OSError, ValueError) as exc:
            raise HistoricalArrayError("Historical array path is invalid or escapes its root.") from exc
    else:
        try:
            if manifest_path is None:
                payload = load_verified_evidence_bytes(repository_path, sha256, archive_root=archive_root)
            else:
                payload = load_verified_evidence_bytes(repository_path, sha256, manifest_path=manifest_path, archive_root=archive_root)
        except (OSError, RecoveredEvidenceError) as exc:
            raise HistoricalArrayError(
                f"HISTORICAL_RAW_EVIDENCE_UNAVAILABLE: {repository_path}; "
                "restore the original hash-bound bytes, never substitute a new solve."
            ) from exc
    if len(payload) != size_bytes or hashlib.sha256(payload).hexdigest() != sha256.lower():
        raise HistoricalArrayError(f"HISTORICAL_RAW_EVIDENCE_HASH_MISMATCH: {repository_path}")
    return payload
