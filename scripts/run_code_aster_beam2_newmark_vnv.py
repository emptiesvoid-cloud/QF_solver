"""Run and promote the pinned Code_Aster BEAM2 axial Newmark correlation."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.code_aster_beam2_newmark import CodeAsterBeam2NewmarkCampaign


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "qualification" / "vnv" / "external" / "code_aster_beam2_newmark" / "reference"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="results/VNV-BEAM2-NEWMARK-CODEASTER-POUDE-003")
    parser.add_argument("--no-promote", action="store_true")
    args = parser.parse_args()
    output = Path(args.output)
    summary = CodeAsterBeam2NewmarkCampaign(output).run()
    if not args.no_promote:
        REFERENCE.mkdir(parents=True, exist_ok=True)
        shutil.copytree(output, REFERENCE, dirs_exist_ok=True)
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 3


if __name__ == "__main__":
    raise SystemExit(main())
