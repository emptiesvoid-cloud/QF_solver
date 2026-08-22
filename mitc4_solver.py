"""Compatibility launcher for the MITC4 tooling."""

from __future__ import annotations

import sys
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parent / "src"
if SOURCE_ROOT.is_dir():
    sys.path.insert(0, str(SOURCE_ROOT))

from solveur.compat.mitc4.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
