"""Run one curved MITC3+ load family against CalculiX S6."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.calculix_mitc3_curved_composite import (
    CalculixMitc3CurvedCompositeCorrelation,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--load-case", choices=("mixed", "transverse", "axial"), default="axial")
    parser.add_argument("--levels", type=int, nargs="+", default=[16, 32, 48, 64])
    parser.add_argument("--study-id", default="VNV-MITC3-LAMINATE-CURVED-PROJECTED-CALCULIX-S6-AXIAL-001")
    args = parser.parse_args()
    levels = tuple((value, max(1, value // 2)) for value in args.levels)
    campaign = CalculixMitc3CurvedCompositeCorrelation(
        args.output,
        load_case=args.load_case,
    )
    campaign.meshes = levels
    campaign.study_id = args.study_id
    summary = campaign.run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 4


if __name__ == "__main__":
    raise SystemExit(main())
