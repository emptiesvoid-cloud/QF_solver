"""Portable locations for source checkouts and installed distributions."""

from __future__ import annotations

import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
PACKAGE_PARENT = PACKAGE_ROOT.parent


def project_root() -> Path:
    """Return the repository root, or the installation prefix for a wheel."""
    for start in (PACKAGE_ROOT, Path.cwd().resolve()):
        for candidate in (start, *start.parents):
            if (candidate / "pyproject.toml").is_file() and (
                (candidate / "src" / "solveur").is_dir() or (candidate / "solveur").is_dir()
            ):
                return candidate
    return Path(sys.prefix).resolve()


def project_path(relative: str | Path) -> Path:
    """Resolve a controlled project resource in source and wheel layouts."""
    value = Path(relative)
    if value.is_absolute():
        return value
    candidates = (
        project_root() / value,
        Path(sys.prefix).resolve() / value,
        PACKAGE_PARENT / value,
    )
    return next((candidate for candidate in candidates if candidate.exists()), candidates[0])
