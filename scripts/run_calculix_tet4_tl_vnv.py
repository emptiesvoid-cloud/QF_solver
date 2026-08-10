"""Run the same-mesh CalculiX correlation for the TET4-TL campaign."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.calculix_total_lagrangian import CalculixTotalLagrangianCorrelation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--qf-summary",
        type=Path,
        default=Path("results/VNV-TET4-TL-ASSEMBLY-002/summary.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/VNV-TET4-TL-CALCULIX-003"),
    )
    parser.add_argument("--image", default="qf-solver/calculix-nafems13h:2.20")
    args = parser.parse_args()
    summary = CalculixTotalLagrangianCorrelation(image=args.image).run(args.qf_summary, args.output)
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
