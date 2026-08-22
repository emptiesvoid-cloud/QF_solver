"""Run the multi-level MITC3+ dynamic correlation campaign."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_mitc3_dynamic_refinement import (
    CAMPAIGN_ID,
    CodeAsterMitc3DynamicRefinementCampaign,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results") / CAMPAIGN_ID)
    parser.add_argument("--levels", nargs="+", default=("8x2", "16x4", "24x6"))
    args = parser.parse_args()
    levels = tuple(tuple(int(value) for value in item.lower().split("x", 1)) for item in args.levels)
    summary = CodeAsterMitc3DynamicRefinementCampaign(args.output, levels=levels).run()
    print(f"{summary['study_id']}: {summary['status']}")
    print(f"evidence: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
