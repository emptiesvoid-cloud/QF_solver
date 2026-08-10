"""Run the MITC3+ pinched-hemisphere Code_Aster correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_mitc3_hemisphere import (
    CodeAsterMitc3HemisphereCampaign,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results") / "VNV-MITC3-PINCHED-HEMISPHERE-CODEASTER-015",
    )
    parser.add_argument("--levels", type=int, nargs="+", default=[4, 8, 12, 16, 24, 32])
    args = parser.parse_args()
    summary = CodeAsterMitc3HemisphereCampaign(
        args.output,
        levels=tuple(args.levels),
    ).run()
    print(f"MITC3+ pinched hemisphere: {summary['status']}")
    for row in summary["levels"]:
        print(
            f"N={row['level']:>2} triangles={row['quarter_triangles']:>4} "
            f"QF={row['qf_abs_ux']:.9f} Aster={abs(row['code_aster_ux']):.9f} "
            f"difference={100.0 * row['probe_difference']:.4f}%"
        )
    print(f"evidence: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
