"""Run the MITC3+ curved projected-axis CalculiX correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.calculix_mitc3_curved_composite import CalculixMitc3CurvedCompositeCorrelation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Output evidence directory.")
    parser.add_argument("--nx", type=int, default=None)
    parser.add_argument("--ny", type=int, default=None)
    args = parser.parse_args()
    campaign = CalculixMitc3CurvedCompositeCorrelation(args.output)
    if args.nx is not None or args.ny is not None:
        if args.nx is None or args.ny is None:
            parser.error("--nx and --ny must be provided together.")
        campaign.meshes = ((int(args.nx), int(args.ny)),)
    summary = campaign.run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 4


if __name__ == "__main__":
    raise SystemExit(main())
