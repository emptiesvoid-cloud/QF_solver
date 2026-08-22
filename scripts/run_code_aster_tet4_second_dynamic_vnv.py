"""Run the second-geometry TET4/Code_Aster dynamic correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_tet4_thick_dynamic import CodeAsterTet4ThickDynamicsCampaign


def main() -> int:
    """Run the bounded short/thick cantilever study."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results") / CodeAsterTet4ThickDynamicsCampaign.study_id,
    )
    parser.add_argument("--mesh-size", type=float, default=0.24)
    args = parser.parse_args()
    summary = CodeAsterTet4ThickDynamicsCampaign(args.output, mesh_size=args.mesh_size).run()
    print(f"{summary['study_id']}: {summary['status']}")
    print(f"evidence: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())

