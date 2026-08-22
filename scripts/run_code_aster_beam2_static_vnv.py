"""Run the pinned BEAM2/Code_Aster static correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_beam2_static import CodeAsterBeam2StaticCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = CodeAsterBeam2StaticCampaign(args.output).run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
