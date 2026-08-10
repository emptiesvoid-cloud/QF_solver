"""Run the three-layup MITC4 laminate dynamics / Code_Aster correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.mitc4_laminate_layups import Mitc4LaminateLayupCorrelationCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nx", type=int, default=12)
    parser.add_argument("--ny", type=int, default=3)
    args = parser.parse_args()
    summary = Mitc4LaminateLayupCorrelationCampaign(args.output, nx=args.nx, ny=args.ny).run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 4


if __name__ == "__main__":
    raise SystemExit(main())
