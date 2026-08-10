"""Run the assembled total-Lagrangian TET4 verification campaign."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.tet4_total_lagrangian_assembly import TotalLagrangianAssemblyCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/VNV-TET4-TL-ASSEMBLY-002"),
        help="Campaign output directory.",
    )
    args = parser.parse_args()
    summary = TotalLagrangianAssemblyCampaign(args.output).run()
    print(f"{summary['campaign_id']}: {summary['status']}")
    return 1 if summary["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
