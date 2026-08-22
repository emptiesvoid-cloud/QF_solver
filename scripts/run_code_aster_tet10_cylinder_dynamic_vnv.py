"""Run the circular-shaft TET10/Code_Aster dynamic correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_tet10_cylinder_dynamic import CodeAsterTet10CylinderDynamicsCampaign


def main() -> int:
    """Run the bounded circular quadratic-solid study."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results") / CodeAsterTet10CylinderDynamicsCampaign.study_id,
    )
    parser.add_argument("--mesh-size", type=float, default=0.32)
    args = parser.parse_args()
    summary = CodeAsterTet10CylinderDynamicsCampaign(args.output, mesh_size=args.mesh_size).run()
    print(f"{summary['study_id']}: {summary['status']}")
    print(f"evidence: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())

