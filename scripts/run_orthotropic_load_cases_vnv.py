"""Run the rotated and combined-load orthotropic verification campaign."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.orthotropic_load_cases import OrthotropicLoadCaseCampaign


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = OrthotropicLoadCaseCampaign(args.output).run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_TECHNICAL_VERIFICATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
