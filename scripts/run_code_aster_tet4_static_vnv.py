"""Run the same-mesh TET4 static Code_Aster correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_tet4_static import CodeAsterTet4StaticCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh-size", type=float, default=None)
    parser.add_argument("--no-publish", action="store_true", help="Do not copy evidence to the qualification reference tree.")
    args = parser.parse_args()
    summary = CodeAsterTet4StaticCampaign(
        args.output, mesh_size=args.mesh_size, publish_reference=not args.no_publish
    ).run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 4


if __name__ == "__main__":
    raise SystemExit(main())
