"""Run the external structural TET10 J2 correlation with Code_Aster."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_tet10_j2_structural import CodeAsterTet10J2StructuralCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results") / CodeAsterTet10J2StructuralCampaign.study_id,
    )
    args = parser.parse_args()
    summary = CodeAsterTet10J2StructuralCampaign(args.output).run()
    print(f"TET10 J2 structural Code_Aster V&V: {summary['status']}")
    print(f"output: {Path(args.output).resolve()}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 4


if __name__ == "__main__":
    raise SystemExit(main())
