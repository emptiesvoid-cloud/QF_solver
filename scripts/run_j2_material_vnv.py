"""Run the controlled material-point J2 V&V campaign."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from solveur.verification.j2_material import J2MaterialVerificationCampaign  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate small-strain J2 material-point V&V evidence.")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "results" / "VNV-J2-MATERIAL-CYCLIC-001",
    )
    args = parser.parse_args()
    summary = J2MaterialVerificationCampaign(args.output).run()
    print(f"J2 material V&V: {summary['status']}")
    print(f"output: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_INTERNAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
