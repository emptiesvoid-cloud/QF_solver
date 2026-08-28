"""Environment and provenance capture for controlled V&V results."""

from __future__ import annotations

from importlib import metadata
import platform
from pathlib import Path
import subprocess
import sys
from typing import Any
from datetime import datetime, timezone

from solveur.version import __version__


_DEPENDENCIES = ("numpy", "scipy", "matplotlib", "pytest")


def capture_environment(project_root: Path) -> dict[str, Any]:
    """Capture portable environment metadata without importing optional HPC backends."""

    return {
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "solver_version": __version__,
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "dependencies": {name: _distribution_version(name) for name in _DEPENDENCIES},
        "source": git_source_state(project_root),
    }


def git_source_state(project_root: Path) -> dict[str, Any]:
    """Return source provenance, tolerating source archives without Git metadata."""

    return {
        "sha": _git(project_root, "rev-parse", "HEAD"),
        "short_sha": _git(project_root, "rev-parse", "--short", "HEAD"),
        "branch": _git(project_root, "branch", "--show-current"),
        "dirty": bool(_git(project_root, "status", "--porcelain")),
    }


def _distribution_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _git(project_root: Path, *arguments: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(project_root), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None
