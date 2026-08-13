"""Sparse structural helpers for total-Lagrangian V&V campaigns."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigsh, spsolve

from solveur.core.geometric_nonlinear_controls import GeometricNonlinearControls
from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly


@dataclass(frozen=True)
class ProportionalEquilibrium:
    """Converged equilibrium under a proportional dead load."""

    displacement: np.ndarray
    tangent: csr_matrix
    relative_residual: float
    newton_iterations: int
    minimum_det_f: float


def solve_proportional_dead_load(
    assembly: TotalLagrangianTet4Assembly,
    load: np.ndarray,
    fixed_dofs: np.ndarray,
    *,
    increments: int = 10,
    tolerance: float = 1.0e-9,
    max_iterations: int = 30,
    line_search: bool = True,
) -> ProportionalEquilibrium:
    """Solve a conservative proportional load with Newton and backtracking."""
    controls = GeometricNonlinearControls(load_increments=increments)
    target_load = np.asarray(load, dtype=float)
    if target_load.shape != (assembly.ndof,) or not np.all(np.isfinite(target_load)):
        raise ValueError(f"load must be a finite vector of size {assembly.ndof}.")
    fixed = np.unique(np.asarray(fixed_dofs, dtype=int))
    if fixed.size == 0 or fixed[0] < 0 or fixed[-1] >= assembly.ndof:
        raise ValueError("fixed_dofs must contain valid constrained indices.")
    free = np.setdiff1d(np.arange(assembly.ndof), fixed)
    displacement = np.zeros(assembly.ndof, dtype=float)
    total_iterations = 0
    relative = float("inf")
    for step in range(1, controls.load_increments + 1):
        step_load = (step / controls.load_increments) * target_load
        reference = max(float(np.linalg.norm(step_load[free])), 1.0)
        for _ in range(max_iterations):
            internal, tangent = assembly.assemble(displacement)
            assert tangent is not None
            residual = step_load - internal
            relative = float(np.linalg.norm(residual[free]) / reference)
            if relative <= tolerance:
                break
            correction = spsolve(tangent[free, :][:, free], residual[free])
            if line_search:
                displacement = _backtracked_update(
                    assembly,
                    displacement,
                    free,
                    correction,
                    step_load,
                    np.linalg.norm(residual[free]),
                )
            else:
                displacement[free] += correction
            total_iterations += 1
        else:
            raise RuntimeError(
                f"Total-Lagrangian dead-load solve failed at step {step}; residual={relative:.6e}."
            )
    _, tangent = assembly.assemble(displacement)
    assert tangent is not None
    return ProportionalEquilibrium(
        displacement=displacement,
        tangent=tangent,
        relative_residual=relative,
        newton_iterations=total_iterations,
        minimum_det_f=float(np.min(assembly.deformation_determinants(displacement))),
    )


def smallest_tangent_eigenpair(
    tangent: csr_matrix,
    free_dofs: np.ndarray,
    *,
    tolerance: float = 1.0e-7,
    initial_mode: np.ndarray | None = None,
) -> tuple[float, np.ndarray]:
    """Return the algebraically smallest constrained tangent eigenpair."""
    free = np.asarray(free_dofs, dtype=int)
    reduced = tangent[free, :][:, free]
    initial = None if initial_mode is None else np.asarray(initial_mode, dtype=float)[free]
    values, vectors = eigsh(
        reduced,
        k=1,
        which="SA",
        tol=tolerance,
        maxiter=max(10000, 5 * reduced.shape[0]),
        v0=initial,
    )
    mode = np.zeros(tangent.shape[0], dtype=float)
    mode[free] = vectors[:, 0]
    return float(values[0]), mode


@dataclass(frozen=True)
class ArcLengthPoint:
    """One converged point on a sparse spherical arc-length path."""

    step: int
    load_factor: float
    tip_axial_displacement: float
    tip_lateral_displacement: float
    relative_residual: float
    iterations: int
    minimum_det_f: float


def trace_sparse_arc_length(
    assembly: TotalLagrangianTet4Assembly,
    reference_load: np.ndarray,
    fixed_dofs: np.ndarray,
    tip_nodes: np.ndarray,
    *,
    steps: int = 100,
    initial_load_increment: float = 0.05,
    tolerance: float = 1.0e-8,
    max_iterations: int = 35,
) -> tuple[np.ndarray, list[ArcLengthPoint]]:
    """Trace an imperfect structure with a sparse spherical arc-length method."""
    if steps < 10:
        raise ValueError("Arc-length verification requires at least 10 continuation steps.")
    load = np.asarray(reference_load, dtype=float)
    fixed = np.unique(np.asarray(fixed_dofs, dtype=int))
    free = np.setdiff1d(np.arange(assembly.ndof), fixed)
    displacement = np.zeros(assembly.ndof, dtype=float)
    internal, tangent = assembly.assemble(displacement)
    assert tangent is not None
    predictor = spsolve(tangent[free, :][:, free], load[free])
    load_scale = max(float(np.linalg.norm(predictor)), 1.0e-12)
    radius = initial_load_increment * np.sqrt(float(predictor @ predictor) + load_scale**2)
    load_factor = 0.0
    previous_increment = np.zeros(free.size, dtype=float)
    history: list[ArcLengthPoint] = []
    for step in range(1, steps + 1):
        base_displacement = displacement.copy()
        base_factor = load_factor
        _, tangent = assembly.assemble(displacement)
        assert tangent is not None
        load_direction = spsolve(tangent[free, :][:, free], load[free])
        direction = 1.0
        if step > 1 and float(previous_increment @ load_direction) < 0.0:
            direction = -1.0
        delta_factor = direction * radius / np.sqrt(
            float(load_direction @ load_direction) + load_scale**2
        )
        displacement[free] += delta_factor * load_direction
        load_factor += delta_factor
        relative = float("inf")
        for iteration in range(1, max_iterations + 1):
            internal, tangent = assembly.assemble(displacement)
            assert tangent is not None
            residual = load_factor * load - internal
            delta_u = displacement[free] - base_displacement[free]
            delta_lambda = load_factor - base_factor
            constraint = float(
                delta_u @ delta_u + (load_scale * delta_lambda) ** 2 - radius**2
            )
            force_scale = max(float(np.linalg.norm(load_factor * load[free])), 1.0)
            relative = max(
                float(np.linalg.norm(residual[free]) / force_scale),
                abs(constraint) / max(radius**2, np.finfo(float).tiny),
            )
            if relative <= tolerance:
                break
            reduced = tangent[free, :][:, free]
            residual_direction = spsolve(reduced, residual[free])
            load_direction = spsolve(reduced, load[free])
            denominator = 2.0 * (
                float(delta_u @ load_direction) + load_scale**2 * delta_lambda
            )
            if abs(denominator) <= 1.0e-14:
                raise RuntimeError(f"Arc-length constraint is singular at step {step}.")
            factor_correction = (
                -constraint - 2.0 * float(delta_u @ residual_direction)
            ) / denominator
            displacement[free] += residual_direction + factor_correction * load_direction
            load_factor += factor_correction
        else:
            raise RuntimeError(
                f"Sparse arc-length failed at step {step}; relative residual={relative:.6e}."
            )
        previous_increment = displacement[free] - base_displacement[free]
        history.append(
            ArcLengthPoint(
                step=step,
                load_factor=float(load_factor),
                tip_axial_displacement=float(np.mean(displacement[3 * tip_nodes])),
                tip_lateral_displacement=float(np.mean(displacement[3 * tip_nodes + 2])),
                relative_residual=relative,
                iterations=iteration,
                minimum_det_f=float(np.min(assembly.deformation_determinants(displacement))),
            )
        )
    return displacement, history


def _backtracked_update(
    assembly: TotalLagrangianTet4Assembly,
    displacement: np.ndarray,
    free: np.ndarray,
    correction: np.ndarray,
    target_load: np.ndarray,
    residual_norm: float,
) -> np.ndarray:
    alpha = 1.0
    full_step: np.ndarray | None = None
    for _ in range(14):
        trial = displacement.copy()
        trial[free] += alpha * correction
        try:
            internal, _ = assembly.assemble(trial, tangent_required=False)
        except ValueError:
            alpha *= 0.5
            continue
        if full_step is None:
            full_step = trial
        if np.linalg.norm((target_load - internal)[free]) < residual_norm:
            return trial
        alpha *= 0.5
    if full_step is not None:
        return full_step
    raise RuntimeError("Total-Lagrangian line search failed.")
