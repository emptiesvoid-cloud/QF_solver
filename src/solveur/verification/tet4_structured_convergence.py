"""Contracts and analytical metrics for nested TET4 cantilever studies."""

from __future__ import annotations

from dataclasses import dataclass
from math import log
from pathlib import Path
from typing import Any

import numpy as np

from solveur.io.manifest import write_json_file
from solveur.large.generator import generate_tet4_cantilever_block
from solveur.large.io import load_large_model
from solveur.large.matrix_free import solve_structured_matrix_free
from solveur.large.solver import solve_large_model


@dataclass(frozen=True)
class StructuredTet4Level:
    """One deterministic level of a structured TET4 h-refinement sequence."""

    factor: int
    nx: int
    ny: int
    nz: int

    @property
    def element_count(self) -> int:
        return (12 if self._decomposition == "centered" else 6) * self.nx * self.ny * self.nz

    _decomposition: str = "six"

    @property
    def node_count(self) -> int:
        corner_nodes = (self.nx + 1) * (self.ny + 1) * (self.nz + 1)
        center_nodes = self.nx * self.ny * self.nz if self._decomposition == "centered" else 0
        return corner_nodes + center_nodes

    @property
    def ndof(self) -> int:
        return 3 * self.node_count


@dataclass(frozen=True)
class StructuredTet4ConvergencePlan:
    """Nested dimensions and size estimates for a TET4 cantilever campaign."""

    base_nx: int = 20
    base_ny: int = 4
    base_nz: int = 4
    refinement_factors: tuple[int, ...] = (1, 2, 4, 8)
    decomposition: str = "six"
    load_distribution: str = "tributary"

    def __post_init__(self) -> None:
        if min(self.base_nx, self.base_ny, self.base_nz) <= 0:
            raise ValueError("Structured TET4 base dimensions must be positive.")
        if not self.refinement_factors or any(factor <= 0 for factor in self.refinement_factors):
            raise ValueError("Structured TET4 refinement factors must be positive.")
        if tuple(sorted(set(self.refinement_factors))) != self.refinement_factors:
            raise ValueError("Structured TET4 refinement factors must be strictly increasing.")
        for previous, current in zip(self.refinement_factors[:-1], self.refinement_factors[1:], strict=True):
            if current % previous:
                raise ValueError("Adjacent structured TET4 levels must be nested integer refinements.")
        if self.decomposition not in {"six", "centered"}:
            raise ValueError("Structured TET4 decomposition must be 'six' or 'centered'.")
        if self.load_distribution not in {"tributary", "surface_consistent"}:
            raise ValueError("Structured TET4 load distribution must be 'tributary' or 'surface_consistent'.")

    @property
    def levels(self) -> tuple[StructuredTet4Level, ...]:
        return tuple(
            StructuredTet4Level(
                factor=factor,
                nx=self.base_nx * factor,
                ny=self.base_ny * factor,
                nz=self.base_nz * factor,
                _decomposition=self.decomposition,
            )
            for factor in self.refinement_factors
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "base_cells": [self.base_nx, self.base_ny, self.base_nz],
            "refinement_factors": list(self.refinement_factors),
            "nested": True,
            "decomposition": self.decomposition,
            "load_distribution": self.load_distribution,
            "levels": [
                {
                    "factor": level.factor,
                    "nx": level.nx,
                    "ny": level.ny,
                    "nz": level.nz,
                    "elements": level.element_count,
                    "nodes": level.node_count,
                    "dofs": level.ndof,
                }
                for level in self.levels
            ],
        }


def timoshenko_tip_displacement(
    force: float,
    length: float,
    width: float,
    height: float,
    young: float,
    poisson: float,
    *,
    shear_factor: float = 5.0 / 6.0,
) -> float:
    """Return the Euler-Bernoulli plus Timoshenko cantilever tip displacement."""
    if min(length, width, height, young, shear_factor) <= 0.0:
        raise ValueError("Cantilever dimensions, Young modulus and shear factor must be positive.")
    if not -1.0 < poisson < 0.5:
        raise ValueError("Poisson ratio must lie in (-1, 0.5).")
    area = width * height
    inertia = width * height**3 / 12.0
    shear_modulus = young / (2.0 * (1.0 + poisson))
    return float(force * length**3 / (3.0 * young * inertia) + force * length / (shear_factor * shear_modulus * area))


def relative_error(value: float, reference: float) -> float:
    """Return an absolute relative error and reject a zero reference."""
    if reference == 0.0:
        raise ValueError("A relative error requires a non-zero reference value.")
    return abs(float(value) - float(reference)) / abs(float(reference))


def observed_orders(values: tuple[float, ...], mesh_sizes: tuple[float, ...]) -> tuple[float, ...]:
    """Estimate local h-orders from positive errors and decreasing mesh sizes."""
    if len(values) != len(mesh_sizes) or len(values) < 2:
        raise ValueError("At least two error values and mesh sizes are required.")
    orders: list[float] = []
    for coarse, fine, coarse_h, fine_h in zip(
        values[:-1], values[1:], mesh_sizes[:-1], mesh_sizes[1:], strict=True
    ):
        if coarse <= 0.0 or fine <= 0.0 or coarse_h <= fine_h:
            raise ValueError("Orders require positive errors and strictly decreasing mesh sizes.")
        orders.append(log(coarse / fine) / log(coarse_h / fine_h))
    return tuple(orders)


def richardson_extrapolation(coarse_value: float, fine_value: float, refinement_ratio: float, order: float) -> float:
    """Estimate the zero-mesh-size value from two nested levels."""
    if refinement_ratio <= 1.0 or order <= 0.0:
        raise ValueError("Richardson refinement ratio must exceed one and order must be positive.")
    denominator = refinement_ratio**order - 1.0
    return float(fine_value + (fine_value - coarse_value) / denominator)


def run_structured_tet4_study(
    output_dir: str | Path,
    *,
    plan: StructuredTet4ConvergencePlan | None = None,
    length: float = 4.0,
    width: float = 0.4,
    height: float = 0.4,
    young: float = 70.0e9,
    poisson: float = 0.3,
    total_load: float = -1.0,
    relative_limit: float = 0.01,
    residual_limit: float = 1.0e-8,
    chunk_size: int = 8192,
    maxiter: int = 10_000,
    solver_backend: str = "matrix_free",
    preconditioner: str = "gamg",
    study_id: str = "VNV-TET4-STRUCTURED-FLEXION-001",
    container_image: str | None = None,
    container_digest: str | None = None,
) -> dict[str, Any]:
    """Run a bounded-memory nested TET4 flexion convergence study.

    ``matrix_free`` is the lightweight local path.  ``petsc`` is intended for
    the million-DOF campaign and is normally executed in the pinned large
    runtime.  Both paths use the same generated model and the same metrics.
    """
    if relative_limit <= 0.0 or residual_limit <= 0.0:
        raise ValueError("Convergence limits must be positive.")
    if solver_backend not in {"matrix_free", "petsc"}:
        raise ValueError("solver_backend must be 'matrix_free' or 'petsc'.")
    study_plan = plan or StructuredTet4ConvergencePlan()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    reference = timoshenko_tip_displacement(total_load, length, width, height, young, poisson)
    rows: list[dict[str, Any]] = []
    for level in study_plan.levels:
        level_dir = output / f"level_{level.factor}"
        model_path = level_dir / "model.h5"
        generate_tet4_cantilever_block(
            model_path,
            nx=level.nx,
            ny=level.ny,
            nz=level.nz,
            length=length,
            height=height,
            depth=width,
            young=young,
            poisson=poisson,
            total_load=total_load,
            decomposition=study_plan.decomposition,
            load_distribution=study_plan.load_distribution,
        )
        model = load_large_model(model_path)
        if solver_backend == "matrix_free":
            solved = solve_structured_matrix_free(
                model,
                chunk_size=chunk_size,
                rtol=residual_limit,
                maxiter=maxiter,
            )
            displacement = solved.displacement
            solver_info = dict(solved.solver_info)
            solve_time = solved.solve_time_seconds
            operator_memory = solved.operator_memory_bytes
        else:
            petsc_output = level_dir / "petsc_solution"
            solved_large = solve_large_model(
                model,
                petsc_output,
                solver_backend="petsc",
                preconditioner=preconditioner,
                chunk_size=chunk_size,
                parameters={"rtol": residual_limit, "max_it": maxiter},
            )
            displacement = _read_large_displacement(petsc_output, model.node_count)
            solver_info = dict(solved_large.summary["solver"])
            load_norm = float(np.linalg.norm(model.load_values))
            solver_info["relative_residual"] = float(
                solver_info["residual_norm"] / max(load_norm, 1.0)
            )
            solve_time = float(solved_large.summary["solve_time_seconds"])
            operator_memory = int(solved_large.summary.get("estimated_core_memory_bytes", 0))
        tip_nodes = np.flatnonzero(np.isclose(model.nodes[:, 0], length, atol=1.0e-12))
        tip_uz = float(np.mean(displacement.reshape((-1, 3))[tip_nodes, 2]))
        rows.append(
            {
                "factor": level.factor,
                "nx": level.nx,
                "ny": level.ny,
                "nz": level.nz,
                "elements": level.element_count,
                "nodes": level.node_count,
                "dofs": level.ndof,
                "tip_uz_m": tip_uz,
                "reference_tip_uz_m": reference,
                "relative_error": relative_error(tip_uz, reference),
                "relative_residual": float(solver_info.get("relative_residual", 0.0)),
                "iterations": int(solver_info["iterations"]),
                "solve_time_seconds": solve_time,
                "operator_memory_bytes": operator_memory,
            }
        )
    errors = tuple(float(row["relative_error"]) for row in rows)
    mesh_sizes = tuple(1.0 / float(row["factor"]) for row in rows)
    orders = observed_orders(errors, mesh_sizes) if len(rows) > 1 else ()
    checks = {
        "finite_results": all(np.isfinite(row["tip_uz_m"]) for row in rows),
        "residuals": all(row["relative_residual"] <= residual_limit for row in rows),
        "final_relative_error": bool(errors[-1] <= relative_limit),
    }
    summary: dict[str, Any] = {
        "study_id": study_id,
        "status": "PASS" if all(checks.values()) else "WARNING",
        "maturity": "stable_candidate",
        "reference": {
            "type": "Euler-Bernoulli plus Timoshenko diagnostic",
            "tip_uz_m": reference,
            "young": young,
            "poisson": poisson,
        },
        "plan": study_plan.to_dict(),
        "rows": rows,
        "observed_orders": list(orders),
        "criteria": {
            "relative_limit": relative_limit,
            "residual_limit": residual_limit,
            "checks": checks,
        },
        "solver": {
            "backend": solver_backend,
            "method": "matrix_free_cg" if solver_backend == "matrix_free" else "cg",
            "preconditioner": "nodal_block_jacobi" if solver_backend == "matrix_free" else preconditioner,
            "chunk_size": chunk_size,
            "maxiter": maxiter,
        },
        "runtime": {
            "container_image": container_image,
            "container_digest": container_digest,
        },
        "limitations": [
            "The one-dimensional beam formula is diagnostic and is not the final 3D acceptance oracle.",
            "External TETRA4 and higher-order 3D correlation are required before stable promotion.",
        ],
    }
    write_json_file(output / "summary.json", summary)
    (output / "report.md").write_text(_study_report(summary), encoding="utf-8")
    return summary


def _read_large_displacement(output_dir: Path, node_count: int) -> np.ndarray:
    """Read a file-backed PETSc displacement vector without JSON materialization."""
    npz_path = output_dir / "displacements.npz"
    if npz_path.is_file():
        return np.asarray(np.load(npz_path, allow_pickle=False)["displacements"], dtype=float).reshape((-1, 3))
    try:
        import h5py
    except ImportError as exc:
        raise RuntimeError("PETSc convergence evidence requires h5py or NPZ output.") from exc
    with h5py.File(output_dir / "displacements.h5", "r") as handle:
        values = np.asarray(handle["displacements"], dtype=float)
    if values.shape != (node_count, 3):
        raise ValueError(f"Unexpected displacement shape {values.shape}; expected {(node_count, 3)}.")
    return values


def _study_report(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut : **{summary['status']}**. Cette campagne ne ferme pas seule le scope stable.",
        "",
        "| Facteur | Elements | DDL | UZ TET4 [m] | Erreur | Residu relatif |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["rows"]:
        lines.append(
            f"| {row['factor']} | {row['elements']} | {row['dofs']} | "
            f"{row['tip_uz_m']:.9e} | {100.0 * row['relative_error']:.6g} % | "
            f"{row['relative_residual']:.3e} |"
        )
    lines.extend(
        [
            "",
            f"Ordres observes : `{summary['observed_orders']}`.",
            "",
            "La comparaison finale doit inclure une reference 3D TET10/TETRA10 et une correlation meme-maillage Code_Aster.",
            "",
        ]
    )
    return "\n".join(lines)
