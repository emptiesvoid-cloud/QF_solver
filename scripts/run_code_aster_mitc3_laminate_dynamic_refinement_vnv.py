"""Run strict refinement for MITC3+ laminate dynamics."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_mitc3_laminate_dynamic_refinement import (
    DEFAULT_LEVELS,
    Mitc3LaminateDynamicRefinementCampaign,
)


CAMPAIGN_ID = "VNV-MITC3-LAMINATE-DYNAMICS-REFINEMENT-CODEASTER-DST-022"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--levels", nargs="+", default=[f"{nx}x{ny}" for nx, ny in DEFAULT_LEVELS])
    parser.add_argument("--modelisation", choices=("DST", "DKT"), default="DST")
    parser.add_argument("--campaign-id", default=None)
    args = parser.parse_args()
    levels = tuple(tuple(int(value) for value in item.lower().split("x", 1)) for item in args.levels)
    campaign_id = args.campaign_id or CAMPAIGN_ID
    summary = Mitc3LaminateDynamicRefinementCampaign(
        args.output, levels=levels, campaign_id=campaign_id, modelisation=args.modelisation
    ).run()
    print(f"{campaign_id}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 4


if __name__ == "__main__":
    raise SystemExit(main())
