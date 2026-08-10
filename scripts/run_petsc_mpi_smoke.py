"""Run a small PETSc solve under mpiexec and report each rank."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mpi4py import MPI
from petsc4py import PETSc

from solveur.api import load_large_model, solve_large_model


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--preconditioner", default="gamg")
    args = parser.parse_args()
    model = load_large_model(args.input)
    result = solve_large_model(model, solver_backend="petsc", preconditioner=args.preconditioner)
    report = {
        "rank": MPI.COMM_WORLD.rank,
        "size": MPI.COMM_WORLD.size,
        "status": result.status,
        "petsc_version": list(PETSc.Sys.getVersion()),
        "iterations": result.summary["solver"]["iterations"],
        "residual_norm": result.summary["solver"]["residual_norm"],
    }
    print(json.dumps(report), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
