"""Run a small, reproducible sparse-solver scaling campaign.

This script is intentionally separate from CI.  It measures the common sparse
linear layer on synthetic SPD systems and writes machine-readable metrics.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.sparse import diags

from solveur.core.linear_methods import LinearSystemSolver
from solveur.core.linear_policy import LinearSolverPolicy
from solveur.core.solver_backend import optional_backend_status


def run_campaign(sizes: list[int], output: Path | None = None) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    solver = LinearSystemSolver()
    for size in sizes:
        started = time.perf_counter()
        matrix = diags(
            [-np.ones(size - 1), np.full(size, 4.0), -np.ones(size - 1)],
            offsets=(-1, 0, 1),
            format="csr",
        )
        assembly_seconds = time.perf_counter() - started
        rhs = np.ones(size, dtype=float)
        parameters = {
            "assume_spd": True,
            "rtol": 1.0e-8,
            "atol": 0.0,
            "maxiter": max(500, min(10_000, size)),
            "preconditioner": "jacobi",
        }
        selection = LinearSolverPolicy.assess(matrix, "auto", parameters)
        solve_started = time.perf_counter()
        solution, info = solver.solve(matrix, rhs, method=selection.recommended_method, parameters=parameters)
        solve_seconds = time.perf_counter() - solve_started
        rows.append(
            {
                "dofs": size,
                "nnz": int(matrix.nnz),
                "assembly_seconds": assembly_seconds,
                "solve_seconds": solve_seconds,
                "total_seconds": assembly_seconds + solve_seconds,
                "solution_norm": float(np.linalg.norm(solution)),
                "method": info.method,
                "backend": info.backend,
                "iterations": info.iterations,
                "initial_residual_norm": info.initial_residual_norm,
                "residual_norm": info.residual_norm,
                "relative_residual_norm": info.relative_residual_norm,
                "sparse_memory_bytes": selection.sparse_memory_bytes,
                "direct_memory_estimate_bytes": selection.direct_memory_estimate_bytes,
                "dense_memory_estimate_bytes": selection.dense_memory_estimate_bytes,
            }
        )
    report: dict[str, object] = {
        "schema_version": 1,
        "campaign": "qf-solver-sparse-scaling-0.2.2-alpha",
        "environment": "local reproducibility sample; host identity intentionally omitted",
        "optional_backends": optional_backend_status(),
        "sizes": rows,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[1_000, 10_000, 100_000])
    parser.add_argument("--output", type=Path, default=Path("results/scaling_0_2_2/summary.json"))
    args = parser.parse_args()
    if any(size < 2 for size in args.sizes):
        parser.error("all sizes must be at least 2 DOF")
    report = run_campaign(args.sizes, args.output)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
