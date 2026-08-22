"""Resolve Git consistently for release-audit scripts on supported platforms."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def git_command() -> str:
    """Return a Git executable, including the standard Windows installation path."""
    detected = shutil.which("git")
    if detected:
        return detected
    if os.name == "nt":
        candidate = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "cmd" / "git.exe"
        if candidate.is_file():
            return str(candidate)
    return "git"
