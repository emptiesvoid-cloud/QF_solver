"""Run the MITC3+ curved projected-axis laminate Code_Aster correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_mitc3_curved_laminate import CodeAsterMitc3CurvedLaminateCampaign


CAMPAIGN_ID = "VNV-MITC3-LAMINATE-CURVED-PROJECTED-CODEASTER-DST-029"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--levels", type=int, nargs="+", default=[8, 16, 24, 32])
    parser.add_argument("--load-cases", nargs="+", choices=["mixed", "transverse", "axial"])
    parser.add_argument("--study-id", default=CAMPAIGN_ID)
    args = parser.parse_args()
    levels = tuple((value, max(1, value // 2)) for value in args.levels)
    campaign_kwargs = {"levels": levels, "study_id": args.study_id}
    if args.load_cases:
        campaign_kwargs["load_cases"] = tuple(args.load_cases)
    summary = CodeAsterMitc3CurvedLaminateCampaign(args.output, **campaign_kwargs).run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 4


if __name__ == "__main__":
    raise SystemExit(main())
