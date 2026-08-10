"""Run the MITC3+ laminate dynamics / Code_Aster same-mesh correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_mitc3_laminate_dynamic import CodeAsterMitc3LaminateDynamicsCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Output evidence directory.")
    parser.add_argument("--nx", type=int, default=12)
    parser.add_argument("--ny", type=int, default=3)
    args = parser.parse_args()
    summary = CodeAsterMitc3LaminateDynamicsCampaign(args.output, nx=args.nx, ny=args.ny).run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 4


if __name__ == "__main__":
    raise SystemExit(main())
