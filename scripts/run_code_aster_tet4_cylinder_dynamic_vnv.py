"""Run the circular-shaft TET4/Code_Aster dynamic correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_tet4_cylinder_dynamic import CodeAsterTet4CylinderDynamicsCampaign


def main() -> int:
    """Run the bounded circular-shaft study."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results") / CodeAsterTet4CylinderDynamicsCampaign.study_id,
    )
    parser.add_argument("--mesh-size", type=float, default=0.25)
    args = parser.parse_args()
    summary = CodeAsterTet4CylinderDynamicsCampaign(args.output, mesh_size=args.mesh_size).run()
    print(f"{summary['study_id']}: {summary['status']}")
    print(f"evidence: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())

