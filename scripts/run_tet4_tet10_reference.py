"""Run the structured TET4/TET10 three-dimensional reference campaign."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.tet4_tet10_reference import run_tet4_tet10_reference


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-nx", type=int, default=8)
    parser.add_argument("--base-ny", type=int, default=2)
    parser.add_argument("--base-nz", type=int, default=2)
    parser.add_argument("--factors", type=int, nargs="+", default=[1, 2, 4])
    parser.add_argument("--decomposition", choices=("six", "centered"), default="six")
    parser.add_argument("--load-distribution", choices=("tributary", "surface_consistent"), default="tributary")
    parser.add_argument("--study-id", default="VNV-TET4-TET10-3D-REFERENCE-001")
    args = parser.parse_args()
    summary = run_tet4_tet10_reference(
        args.output,
        base_nx=args.base_nx,
        base_ny=args.base_ny,
        base_nz=args.base_nz,
        refinement_factors=tuple(args.factors),
        decomposition=args.decomposition,
        load_distribution=args.load_distribution,
        study_id=args.study_id,
    )
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS" else 4


if __name__ == "__main__":
    raise SystemExit(main())
