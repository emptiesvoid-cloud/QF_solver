"""Run the pinned TET10/Code_Aster TETRA10 dynamic correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_tet10_dynamic import CodeAsterTet10DynamicsCampaign


def main() -> int:
    """Run the bounded structural modal, Newmark and harmonic study."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results") / CodeAsterTet10DynamicsCampaign.study_id,
    )
    parser.add_argument("--mesh-size", type=float, default=0.60)
    args = parser.parse_args()
    summary = CodeAsterTet10DynamicsCampaign(args.output, mesh_size=args.mesh_size).run()
    print(f"{summary['study_id']}: {summary['status']}")
    print(f"evidence: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
