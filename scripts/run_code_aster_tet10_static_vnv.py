"""Run same-mesh Code_Aster TET10/TETRA10 static correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_tet10_static import CodeAsterTet10StaticCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tet4-summary", type=Path, default=None)
    parser.add_argument("--no-publish", action="store_true")
    args = parser.parse_args()
    summary = CodeAsterTet10StaticCampaign(
        args.model,
        args.output,
        tet4_summary_path=args.tet4_summary,
        publish_reference=not args.no_publish,
    ).run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 4


if __name__ == "__main__":
    raise SystemExit(main())
