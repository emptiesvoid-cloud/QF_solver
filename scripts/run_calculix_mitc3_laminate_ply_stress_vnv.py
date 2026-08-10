"""Run the MITC3+ laminate per-ply stress correlation with CalculiX S6."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.calculix_mitc3_laminate_ply_stress import CalculixMitc3LaminatePlyStressCorrelation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Output evidence directory.")
    args = parser.parse_args()
    summary = CalculixMitc3LaminatePlyStressCorrelation(args.output).run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 4


if __name__ == "__main__":
    raise SystemExit(main())
