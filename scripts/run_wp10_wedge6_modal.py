"""Run the controlled WP10 WEDGE6 mass and modal evidence campaign."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.wedge6_modal import CATALOG, run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=CATALOG.parent / "wp10_evidence.json")
    parser.add_argument(
        "--skip-external",
        action="store_true",
        help="Record the external modal oracle as unavailable without invoking Docker.",
    )
    args = parser.parse_args()
    summary = run(args.output, run_external=not args.skip_external)
    print(
        {
            "cases": summary["summary"]["case_count"],
            "pass": summary["summary"]["pass"],
            "expected_failure_pass": summary["summary"]["expected_failure_pass"],
            "fail": summary["summary"]["fail"],
            "external": summary["external"].get("state"),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
