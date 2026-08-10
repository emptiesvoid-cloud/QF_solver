"""Deprecated compatibility launcher for QF_solver."""

import sys

from solveur.cli.main import main
from solveur.version import LEGACY_LAUNCHER, legacy_entrypoint_warning


if __name__ == "__main__":
    print(legacy_entrypoint_warning(LEGACY_LAUNCHER), file=sys.stderr)
    raise SystemExit(main())
