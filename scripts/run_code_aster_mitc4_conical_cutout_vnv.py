"""Run the pinned MITC4/Code_Aster DKQ conical-cutout correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_mitc4_conical_cutout import CodeAsterMitc4ConicalCutoutCorrelation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("results") / CodeAsterMitc4ConicalCutoutCorrelation.study_id
    )
    args = parser.parse_args()
    summary = CodeAsterMitc4ConicalCutoutCorrelation(args.output).run()
    print(f"{summary['study_id']}: {summary['status']}")
    print(f"evidence: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
