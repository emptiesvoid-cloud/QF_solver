"""Resolve and invoke Git consistently for repository-audit checks."""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
import os
import shutil
import subprocess
from pathlib import Path


@lru_cache(maxsize=1)
def git_command() -> str:
    """Return an absolute Git executable path, or fail closed if Git is absent.

    The result is cached before a test campaign can temporarily alter ``PATH``.
    This is important on Windows, where resolving a bare ``git`` command can
    otherwise depend on the current process environment and ``ComSpec``.
    """
    configured = (
        os.environ.get("QF_SOLVER_GIT")
        or os.environ.get("GIT_EXECUTABLE")
        or shutil.which("git")
        or shutil.which("git.exe")
    )
    if configured:
        candidate = Path(configured)
        if candidate.is_file():
            return str(candidate.resolve())
    raise FileNotFoundError(
        "Git executable is required for repository-history verification but was not found."
    )


def git_run(
    args: Sequence[str],
    *,
    cwd: Path,
    check: bool = False,
    text: bool = False,
) -> subprocess.CompletedProcess:
    """Run Git from an explicit repository root with a controlled environment."""
    environment = os.environ.copy()
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        environment.pop(name, None)
    return subprocess.run(
        [git_command(), *args],
        cwd=Path(cwd),
        env=environment,
        check=check,
        capture_output=True,
        text=text,
    )


def git_blob(revision: str, relative: str, *, cwd: Path) -> tuple[str, bytes]:
    """Return a Git blob id and its immutable bytes for a repository path."""
    reference = f"{revision}:{relative}"
    blob = git_run(["rev-parse", reference], cwd=cwd, check=True, text=True).stdout.strip()
    content = git_run(["cat-file", "blob", blob], cwd=cwd, check=True).stdout
    return blob, content


def git_object_exists(reference: str, *, cwd: Path) -> bool:
    """Return whether a Git object or revision:path reference exists."""
    return git_run(["cat-file", "-e", reference], cwd=cwd).returncode == 0
