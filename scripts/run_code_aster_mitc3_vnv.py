"""Run the pinned MITC3+/Code_Aster DKT same-mesh correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_mitc3 import CodeAsterMitc3Correlation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results") / CodeAsterMitc3Correlation.study_id,
    )
    parser.add_argument("--nx", type=int, default=32)
    parser.add_argument("--ny", type=int, default=8)
    args = parser.parse_args()
    summary = CodeAsterMitc3Correlation(args.output, nx=args.nx, ny=args.ny).run()
    print(f"{summary['study_id']}: {summary['status']}")
    print(f"evidence: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
