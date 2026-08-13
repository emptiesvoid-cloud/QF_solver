"""Portable launcher for QF_solver from an installed package or source tree."""

from __future__ import annotations

import sys
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parent / "src"
if SOURCE_ROOT.is_dir():
    sys.path.insert(0, str(SOURCE_ROOT))

from solveur.cli.main import main


if __name__ == "__main__":
    raise SystemExit(main())
