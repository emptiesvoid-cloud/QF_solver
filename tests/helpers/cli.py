"""CLI subprocess helpers for integration tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_solver_cli(*args: object, cwd: Path = PROJECT_ROOT) -> subprocess.CompletedProcess[str]:
    """Run the historical solver launcher with standard test capture settings."""
    return subprocess.run(
        [sys.executable, "main_solveur.py", *(str(arg) for arg in args)],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
