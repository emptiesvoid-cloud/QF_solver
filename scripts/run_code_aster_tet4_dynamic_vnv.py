"""Run the pinned TET4/Code_Aster TETRA4 dynamic correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_tet4_dynamic import CodeAsterTet4DynamicsCampaign


def main() -> int:
    """Run the bounded structural modal, Newmark and harmonic study."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results") / CodeAsterTet4DynamicsCampaign.study_id,
    )
    parser.add_argument("--mesh-size", type=float, default=0.60)
    args = parser.parse_args()
    summary = CodeAsterTet4DynamicsCampaign(args.output, mesh_size=args.mesh_size).run()
    print(f"{summary['study_id']}: {summary['status']}")
    print(f"evidence: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
