"""Measure Newmark effective-matrix factorization reuse.

This is a manual V&V campaign, separate from the fast CI suite.  It uses the
same deterministic TET4 block family as the assembly benchmarks and records
only numerical, timing and resource metrics.  The direct Newmark path should
factorize the effective matrix once and reuse it for every time step.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from solveur.core.model import FiniteElementModel
from solveur.api.public import solve_model
from solveur.large.generator import generate_tet4_block, recommended_block_for_dofs


_DOF_NAMES = ("UX", "UY", "UZ")


def run_campaign(
    sizes: list[int],
    output: Path | None = None,
    *,
    steps: int = 8,
    time_step: float = 1.0e-4,
) -> dict[str, object]:
    """Run a direct Newmark campaign for the requested approximate DDL sizes."""

    if steps <= 0:
        raise ValueError("steps must be positive")
    if time_step <= 0.0:
        raise ValueError("time_step must be positive")

    rows: list[dict[str, object]] = []
    for target_dofs in sizes:
        nx, ny, nz = recommended_block_for_dofs(target_dofs)
        generated = generate_tet4_block(
            Path("results") / "scaling_0_2_2" / f"newmark_factorization_{target_dofs}.npz",
            nx=nx,
            ny=ny,
            nz=nz,
            total_load=1000.0,
            load_component=2,
            load_distribution="tributary",
        )
        model = _dynamic_model(generated, steps=steps, time_step=time_step)
        started = time.perf_counter()
        result = solve_model(model)
        elapsed = time.perf_counter() - started
        solver_data = dict(result.solver)
        execution = dict(solver_data.get("linear_execution", {}))
        factorization_count = int(solver_data.get("effective_factorization_count", 0))
        solve_count = int(solver_data.get("effective_factorization_solve_count", 0))
        rows.append(
            {
                "target_dofs": int(target_dofs),
                "dofs": int(result.dofs.ndof),
                "nodes": int(result.node_count),
                "elements": int(result.element_count),
                "steps": int(steps),
                "time_step": float(time_step),
                "elapsed_seconds": float(elapsed),
                "assembly_seconds": _assembly_seconds(solver_data),
                "effective_nnz": int(execution.get("effective_matrix_nnz", 0)),
                "backend": str(execution.get("backend_used", ["scipy"])[0]),
                "used_method": str(execution.get("used_method", "unknown")),
                "factorization_count": factorization_count,
                "solve_count": solve_count,
                "factorization_reused": bool(solver_data.get("effective_factorization_reused", False)),
                "factorization_seconds": float(solver_data.get("effective_factorization_seconds", 0.0)),
                "solve_seconds_total": float(
                    solver_data.get("effective_factorization_solve_seconds_total", 0.0)
                ),
                "solve_seconds_last": float(
                    solver_data.get("effective_factorization_last_solve_seconds", 0.0)
                ),
                "reuse_count_ratio": float(solve_count / max(factorization_count, 1)),
                "max_relative_dynamic_residual": float(
                    max(solver_data.get("residual_history", [0.0]))
                ),
                "status": result.status,
            }
        )

    report: dict[str, object] = {
        "schema_version": 1,
        "campaign": "qf-solver-newmark-factorization-reuse-0.2.2-alpha",
        "comparison": "direct Newmark effective-matrix factorization reused across time steps",
        "environment": "local reproducibility sample; host identity intentionally omitted",
        "sizes": rows,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _dynamic_model(large_model: object, *, steps: int, time_step: float) -> FiniteElementModel:
    """Convert the deterministic large-model representation to the public API."""

    nodes = np.asarray(large_model.nodes, dtype=float)  # type: ignore[attr-defined]
    connectivity = np.asarray(large_model.tet4, dtype=np.int64)  # type: ignore[attr-defined]
    elements = [
        {"type": "TET4", "nodes": [int(node) for node in row], "material": "steel"}
        for row in connectivity
    ]
    fixed_nodes = np.asarray(large_model.fixed_nodes, dtype=np.int64)  # type: ignore[attr-defined]
    fixed_components = np.asarray(large_model.fixed_components, dtype=np.int8)  # type: ignore[attr-defined]
    fixed_dofs = [
        {"node": int(node), "dofs": [_DOF_NAMES[int(component)] for component in fixed_components[fixed_nodes == node]]}
        for node in np.unique(fixed_nodes)
    ]
    load_nodes = np.asarray(large_model.load_nodes, dtype=np.int64)  # type: ignore[attr-defined]
    load_components = np.asarray(large_model.load_components, dtype=np.int8)  # type: ignore[attr-defined]
    load_values = np.asarray(large_model.load_values, dtype=float)  # type: ignore[attr-defined]
    loads = [
        {"node": int(node), "dof": _DOF_NAMES[int(component)], "value": float(value)}
        for node, component, value in zip(load_nodes, load_components, load_values, strict=True)
    ]
    material = dict(large_model.materials["steel"])  # type: ignore[attr-defined]
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=elements,
        materials={"steel": material},
        fixed_dofs=fixed_dofs,
        loads=loads,
        analysis={
            "type": "transient_dynamic",
            "method": "newmark",
            "parameters": {
                "time_step": time_step,
                "steps": steps,
                "linear_method": "direct",
                "postprocess_mode": "summary",
                "rayleigh_alpha": 0.0,
                "rayleigh_beta": 0.0,
                "load_function": "linear_ramp",
            },
        },
    )


def _assembly_seconds(solver_data: dict[str, object]) -> float:
    assembly = dict(solver_data.get("assembly", {}))
    totals = []
    for matrix_data in assembly.values():
        phases = dict(dict(matrix_data).get("assembly_phase_seconds", {}))
        totals.append(sum(float(value) for value in phases.values()))
    return float(max(totals, default=0.0))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[1_000, 10_000])
    parser.add_argument("--steps", type=int, default=8)
    parser.add_argument("--time-step", type=float, default=1.0e-4)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/scaling_0_2_2/newmark_factorization.json"),
    )
    args = parser.parse_args()
    if any(size < 2 for size in args.sizes):
        parser.error("all target sizes must be at least 2 DOF")
    if args.steps <= 0 or args.time_step <= 0.0:
        parser.error("steps and time-step must be positive")
    print(json.dumps(run_campaign(args.sizes, args.output, steps=args.steps, time_step=args.time_step), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
