"""Run the three-family frictional-contact promotion survey."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.frictional_contact_family_survey import FrictionalContactFamilySurvey


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = FrictionalContactFamilySurvey(args.output).run()
    print(f"{summary['campaign_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_INTERNAL" else 4


if __name__ == "__main__":
    raise SystemExit(main())
