"""Deprecated compatibility launcher for QF_solver."""

from __future__ import annotations

import sys
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parent / "src"
if SOURCE_ROOT.is_dir():
    sys.path.insert(0, str(SOURCE_ROOT))

from solveur.cli.main import main
from solveur.version import LEGACY_LAUNCHER, legacy_entrypoint_warning


if __name__ == "__main__":
    print(legacy_entrypoint_warning(LEGACY_LAUNCHER), file=sys.stderr)
    raise SystemExit(main())
