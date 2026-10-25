"""Fail-closed WP12 runner: static validation and synthetic self-tests only."""

from __future__ import annotations

from wp12_runner.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
