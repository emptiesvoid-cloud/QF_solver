"""Run the Scordelis-Lo benchmark with display/export options from the CLI."""

import sys
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src"
if SOURCE_ROOT.is_dir():
    sys.path.insert(0, str(SOURCE_ROOT))

from mitc4.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main(["scordelis"]))
