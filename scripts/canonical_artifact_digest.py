"""Canonical digests for text and binary release-evidence artifacts."""

from __future__ import annotations

import hashlib
from pathlib import Path


# Evidence text is committed as UTF-8.  Binary artifacts deliberately bypass
# this policy and are hashed byte-for-byte.
TEXT_SUFFIXES = frozenset({
    ".comm",
    ".csv",
    ".json",
    ".mail",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
})


def canonical_artifact_bytes(path: Path) -> bytes:
    """Return the bytes used for a reproducible artifact digest."""
    raw = path.read_bytes()
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return raw
    text = raw.decode("utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def canonical_artifact_sha256(path: Path) -> str:
    """Hash text using UTF-8/LF and binary artifacts without transformation."""
    return hashlib.sha256(canonical_artifact_bytes(path)).hexdigest()
