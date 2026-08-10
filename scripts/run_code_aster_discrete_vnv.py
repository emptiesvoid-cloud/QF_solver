"""Run the pinned Code_Aster SDOF spring-mass correlation."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.code_aster_discrete import CodeAsterDiscreteCampaign


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "qualification" / "vnv" / "external" / "code_aster_discrete" / "reference"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="results/VNV-DISCRETE-CODEASTER-SDOF-001")
    parser.add_argument(
        "--no-promote",
        action="store_true",
        help="Do not copy the completed Docker evidence into qualification/vnv/external.",
    )
    args = parser.parse_args()
    summary = CodeAsterDiscreteCampaign(Path(args.output)).run()
    if not args.no_promote:
        REFERENCE.mkdir(parents=True, exist_ok=True)
        shutil.copytree(Path(args.output), REFERENCE, dirs_exist_ok=True)
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 3


if __name__ == "__main__":
    raise SystemExit(main())
