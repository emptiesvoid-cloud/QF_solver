"""WP12 runner: validation, synthetic checks, and gated one-unit execution."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
main = import_module("scripts.wp12_runner.cli").main


if __name__ == "__main__":
    raise SystemExit(main())
