"""Source-tree launcher for the QF_solver technical site."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
for candidate in (SOURCE_ROOT, PROJECT_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from solveur.documentation.server import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
