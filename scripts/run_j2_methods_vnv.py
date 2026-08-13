"""Run the nonlinear J2 methods comparison."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
for candidate in (SOURCE_ROOT, PROJECT_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from solveur.verification.j2_methods import J2NonlinearMethodsCampaign  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare nonlinear methods on the cyclic J2 bar.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "results" / "VNV-J2-NONLINEAR-METHODS-004")
    args = parser.parse_args()
    summary = J2NonlinearMethodsCampaign(args.output).run()
    print(f"J2 nonlinear methods V&V: {summary['status']}")
    print(f"output: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_CHARACTERIZATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
