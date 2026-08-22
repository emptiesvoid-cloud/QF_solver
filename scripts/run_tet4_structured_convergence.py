"""Run the nested structured TET4 flexion convergence study."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.tet4_structured_convergence import (
    StructuredTet4ConvergencePlan,
    run_structured_tet4_study,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--factors", type=int, nargs="+", default=[1, 2, 4, 8])
    parser.add_argument("--base-nx", type=int, default=20)
    parser.add_argument("--base-ny", type=int, default=4)
    parser.add_argument("--base-nz", type=int, default=4)
    parser.add_argument("--chunk-size", type=int, default=65_536)
    parser.add_argument("--max-it", type=int, default=10_000)
    parser.add_argument("--solver-backend", choices=("matrix_free", "petsc"), default="matrix_free")
    parser.add_argument("--preconditioner", default="gamg")
    parser.add_argument("--study-id", default="VNV-TET4-STRUCTURED-FLEXION-001")
    parser.add_argument("--container-image")
    parser.add_argument("--container-digest")
    parser.add_argument("--decomposition", choices=("six", "centered"), default="six")
    parser.add_argument("--load-distribution", choices=("tributary", "surface_consistent"), default="tributary")
    args = parser.parse_args()
    plan = StructuredTet4ConvergencePlan(
        base_nx=args.base_nx,
        base_ny=args.base_ny,
        base_nz=args.base_nz,
        refinement_factors=tuple(args.factors),
        decomposition=args.decomposition,
        load_distribution=args.load_distribution,
    )
    summary = run_structured_tet4_study(
        args.output,
        plan=plan,
        chunk_size=args.chunk_size,
        maxiter=args.max_it,
        solver_backend=args.solver_backend,
        preconditioner=args.preconditioner,
        study_id=args.study_id,
        container_image=args.container_image,
        container_digest=args.container_digest,
    )
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS" else 4


if __name__ == "__main__":
    raise SystemExit(main())
