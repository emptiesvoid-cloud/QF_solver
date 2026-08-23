"""Portable launcher for QF_solver from an installed package or source tree."""

from __future__ import annotations

import sys
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parent / "src"
if SOURCE_ROOT.is_dir():
    sys.path.insert(0, str(SOURCE_ROOT))

from solveur.api import *  # noqa: E402,F403 - public facade after source path bootstrap
from solveur.api import __all__ as _PUBLIC_API  # noqa: E402
from solveur.cli.main import main  # noqa: E402
from solveur.version import __version__  # noqa: E402


__all__ = ["__version__", *_PUBLIC_API]


if __name__ == "__main__":
    raise SystemExit(main())
