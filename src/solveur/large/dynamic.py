"""PETSc/SLEPc modal and Newmark runners for large TET4 models.

The large static path remains the reference implementation.  This module
adds the two sparse operators needed to exercise the same generated TET4
model in modal and transient analyses without converting the global system to
NumPy or SciPy dense arrays.
"""

from __future__ import annotations

import math
import time
from typing import Any

import numpy as np

from solveur.core.errors import InfrastructureError, NumericalConvergenceError
from solveur.core.analyses.modal_options import validate_slepc_modal_scale
from solveur.large.assembler import (
    PetscTET4Assembler,
    PetscTET4MassAssembler,
    fixed_dof_indices,
    partition_range,
)
from solveur.large.distributed_model import DistributedLargeModel
from solveur.large.model import LargeModel


def solve_large_modal(
    model: LargeModel | DistributedLargeModel,
    *,
    mode_count: int = 6,
    chunk_size: int = 4096,
    matrix_format: str = "baij",
    tolerance: float = 1.0e-8,
    max_iterations: int = 10_000,
) -> dict[str, Any]:
    """Solve a generalized sparse TET4 eigenproblem with SLEPc.

    Constrained DOFs are retained as algebraic rows with a stiffness penalty
    far above the physical spectrum.  This keeps the global numbering and
    distributed PETSc ownership unchanged while preventing constrained modes
    from entering the requested low-frequency band.
    """
    if mode_count <= 0:
        raise ValueError("mode_count must be positive.")
    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive.")
    # This runner is intrinsically a SLEPc modal request.  Refuse oversized
    # jobs before importing/assembling PETSc matrices or starting shift-invert.
    validate_slepc_modal_scale(model.ndof, requested=True)
    petsc, slepc = _optional_slepc()
    comm = petsc.COMM_WORLD
    assembly_start = time.perf_counter()
    stiffness = PetscTET4Assembler(chunk_size=chunk_size, matrix_format=matrix_format).assemble(model)
    mass = PetscTET4MassAssembler(chunk_size=chunk_size, matrix_format=matrix_format).assemble(model)
    _set_modal_constraint_diagonal(stiffness, model, petsc)
    assembly_time = _comm_max(comm, time.perf_counter() - assembly_start, petsc)

    eps = slepc.EPS().create(comm=comm)
    try:
        eps.setOperators(stiffness, mass)
        eps.setProblemType(slepc.EPS.ProblemType.GHEP)
        eps.setType("krylovschur")
        eps.setDimensions(nev=int(mode_count), ncv=max(2 * int(mode_count) + 4, 20))
        # Generalized low-frequency modes require an explicit spectral
        # transformation.  The default ST can report Ritz values while the
        # returned vectors are still far from the physical residual tolerance.
        eps.setTarget(0.0)
        eps.setWhichEigenpairs(slepc.EPS.Which.TARGET_MAGNITUDE)
        spectral_transform = eps.getST()
        spectral_transform.setType("sinvert")
        spectral_transform.setShift(0.0)
        eps.setTolerances(tol=float(tolerance), max_it=int(max_iterations))
        eps.setFromOptions()
        solve_start = time.perf_counter()
        eps.solve()
        solve_time = _comm_max(comm, time.perf_counter() - solve_start, petsc)
        converged = min(int(eps.getConverged()), int(mode_count))
        if converged < mode_count:
            raise NumericalConvergenceError(
                f"SLEPc converged only {converged} of {mode_count} requested modes."
            )
        real, imaginary = stiffness.createVecs()
        eigenvalues: list[float] = []
        frequencies: list[float] = []
        residuals: list[float] = []
        slepc_error_estimates: list[float] = []
        try:
            for index in range(mode_count):
                value = eps.getEigenpair(index, real, imaginary)
                if isinstance(value, tuple):
                    value = value[0]
                eigenvalue = float(np.real(value))
                eigenvalues.append(eigenvalue)
                frequencies.append(math.sqrt(max(eigenvalue, 0.0)) / (2.0 * math.pi))
                try:
                    slepc_error = eps.computeError(index, slepc.EPS.ErrorType.RELATIVE)
                except (AttributeError, TypeError):
                    slepc_error = eps.computeError(index)
                residual = real.duplicate()
                mass_mode = real.duplicate()
                stiffness.mult(real, residual)
                mass.mult(real, mass_mode)
                residual.axpy(-eigenvalue, mass_mode)
                denominator = abs(eigenvalue) * max(float(mass_mode.norm()), np.finfo(float).tiny)
                residuals.append(float(residual.norm()) / denominator)
                residual.destroy()
                mass_mode.destroy()
                slepc_error_estimates.append(float(slepc_error))
        finally:
            real.destroy()
            imaginary.destroy()
        return {
            "status": "PASS",
            "analysis": "modal",
            "backend": "slepc",
            "mode_count": int(mode_count),
            "converged_modes": int(converged),
            "eigenvalues": eigenvalues,
            "frequencies_hz": frequencies,
            "relative_residuals": residuals,
            "slepc_error_estimates": slepc_error_estimates,
            "max_relative_residual": max(residuals, default=0.0),
            "tolerance": float(tolerance),
            "assembly_time_seconds": float(assembly_time),
            "solve_time_seconds": float(solve_time),
            "ndof": int(model.ndof),
            "element_count": int(model.element_count),
            "fixed_dof_count": int(fixed_dof_indices(model).size),
            "mpi_size": int(comm.getSize()),
            "distributed": bool(comm.getSize() > 1),
            "mass_formulation": "consistent_tet4",
            "constraint_treatment": "stiffness_penalty_above_physical_spectrum",
        }
    finally:
        eps.destroy()
        stiffness.destroy()
        mass.destroy()


def solve_large_newmark(
    model: LargeModel | DistributedLargeModel,
    *,
    steps: int = 20,
    time_step: float = 1.0e-4,
    beta: float = 0.25,
    gamma: float = 0.5,
    chunk_size: int = 4096,
    matrix_format: str = "baij",
    preconditioner: str = "gamg",
    tolerance: float = 1.0e-8,
    max_iterations: int = 10_000,
) -> dict[str, Any]:
    """Run a sparse implicit Newmark campaign with a reused effective matrix."""
    if steps <= 0 or time_step <= 0.0:
        raise ValueError("steps and time_step must be positive.")
    if beta <= 0.0 or gamma < 0.0:
        raise ValueError("Newmark beta must be positive and gamma non-negative.")
    petsc, _ = _optional_petsc()
    comm = petsc.COMM_WORLD
    assembly_start = time.perf_counter()
    stiffness = PetscTET4Assembler(chunk_size=chunk_size, matrix_format=matrix_format).assemble(model)
    mass = PetscTET4MassAssembler(chunk_size=chunk_size, matrix_format=matrix_format).assemble(model)
    assembly_time = _comm_max(comm, time.perf_counter() - assembly_start, petsc)

    a0 = 1.0 / (beta * time_step**2)
    a2 = 1.0 / (beta * time_step)
    a3 = 1.0 / (2.0 * beta) - 1.0
    effective = stiffness.copy()
    effective.axpy(a0, mass)
    effective.assemble()
    force = _load_vector(model, petsc, comm)
    displacement = force.duplicate()
    velocity = force.duplicate()
    acceleration = force.duplicate()
    displacement.set(0.0)
    velocity.set(0.0)
    acceleration.set(0.0)

    ksp = petsc.KSP().create(comm=comm)
    ksp.setOperators(effective)
    ksp.setType("cg")
    ksp.getPC().setType(str(preconditioner))
    ksp.setTolerances(rtol=float(tolerance), atol=0.0, max_it=int(max_iterations))
    ksp.setFromOptions()
    setup_start = time.perf_counter()
    ksp.setUp()
    setup_time = _comm_max(comm, time.perf_counter() - setup_start, petsc)
    iterations: list[int] = []
    residuals: list[float] = []
    relative_residuals: list[float] = []
    force_norm = max(float(force.norm()), np.finfo(float).tiny)
    solve_start = time.perf_counter()
    try:
        for step in range(1, steps + 1):
            load_factor = float(step) / float(steps)
            predictor = displacement.copy()
            predictor.scale(a0)
            predictor.axpy(a2, velocity)
            predictor.axpy(a3, acceleration)
            actual_force = force.copy()
            actual_force.scale(load_factor)
            right = actual_force.copy()
            inertial = right.duplicate()
            mass.mult(predictor, inertial)
            right.axpy(1.0, inertial)
            _zero_fixed_values(right, model, petsc)
            next_displacement = displacement.duplicate()
            ksp.solve(right, next_displacement)
            reason = int(ksp.getConvergedReason())
            if reason <= 0:
                raise NumericalConvergenceError(
                    f"PETSc Newmark step {step} did not converge; reason={reason}."
                )
            delta = next_displacement.copy()
            delta.axpy(-1.0, displacement)
            next_acceleration = delta.copy()
            next_acceleration.scale(a0)
            next_acceleration.axpy(-a2, velocity)
            next_acceleration.axpy(-a3, acceleration)
            next_velocity = velocity.copy()
            next_velocity.axpy(time_step * (1.0 - gamma), acceleration)
            next_velocity.axpy(time_step * gamma, next_acceleration)
            internal = next_displacement.duplicate()
            stiffness.mult(next_displacement, internal)
            mass.mult(next_acceleration, inertial)
            internal.axpy(1.0, inertial)
            internal.axpy(-1.0, actual_force)
            residual_norm = float(internal.norm())
            residuals.append(residual_norm)
            relative_residuals.append(residual_norm / max(float(actual_force.norm()), force_norm * np.finfo(float).eps))
            iterations.append(int(ksp.getIterationNumber()))
            displacement.destroy()
            velocity.destroy()
            acceleration.destroy()
            predictor.destroy()
            inertial.destroy()
            actual_force.destroy()
            right.destroy()
            delta.destroy()
            displacement = next_displacement
            velocity = next_velocity
            acceleration = next_acceleration
            internal.destroy()
    finally:
        solve_time = _comm_max(comm, time.perf_counter() - solve_start, petsc)
    final_energy = 0.5 * _dot(displacement, stiffness, displacement) + 0.5 * _dot(velocity, mass, velocity)
    result = {
        "status": "PASS",
        "analysis": "transient_dynamic",
        "method": "newmark_average_acceleration",
        "backend": "petsc",
        "steps": int(steps),
        "time_step_seconds": float(time_step),
        "duration_seconds": float(steps * time_step),
        "newmark_beta": float(beta),
        "newmark_gamma": float(gamma),
        "assembly_time_seconds": float(assembly_time),
        "preconditioner_setup_seconds": float(setup_time),
        "solve_time_seconds": float(solve_time),
        "iterations_total": int(sum(iterations)),
        "iterations_max": int(max(iterations, default=0)),
        "residual_norm_max": float(max(residuals, default=0.0)),
        "residual_norm_final": float(residuals[-1]) if residuals else 0.0,
        "relative_residual_norm_max": float(max(relative_residuals, default=0.0)),
        "relative_residual_norm_final": float(relative_residuals[-1]) if relative_residuals else 0.0,
        "force_norm": float(force_norm),
        "energy_final": float(final_energy),
        "ndof": int(model.ndof),
        "element_count": int(model.element_count),
        "fixed_dof_count": int(fixed_dof_indices(model).size),
        "mpi_size": int(comm.getSize()),
        "distributed": bool(comm.getSize() > 1),
        "mass_formulation": "consistent_tet4",
        "effective_matrix": "K + 1/(beta*dt^2)*M",
        "step_residuals": residuals,
        "step_relative_residuals": relative_residuals,
        "step_iterations": iterations,
    }
    for value in (force, displacement, velocity, acceleration, effective, stiffness, mass, ksp):
        try:
            value.destroy()
        except AttributeError:
            pass
    return result


def _load_vector(model: LargeModel | DistributedLargeModel, petsc: Any, comm: Any) -> Any:
    vector = petsc.Vec().createMPI(model.ndof, comm=comm)
    vector.set(0.0)
    if isinstance(model, DistributedLargeModel):
        start, stop = 0, model.load_values.size
    else:
        start, stop = partition_range(model.load_values.size, comm.getRank(), comm.getSize())
    if stop > start:
        indices = (3 * model.load_nodes[start:stop] + model.load_components[start:stop]).astype(petsc.IntType)
        vector.setValues(indices, model.load_values[start:stop], addv=petsc.InsertMode.ADD_VALUES)
    vector.assemble()
    _zero_fixed_values(vector, model, petsc)
    return vector


def _zero_fixed_values(vector: Any, model: LargeModel | DistributedLargeModel, petsc: Any) -> None:
    fixed = fixed_dof_indices(model).astype(petsc.IntType)
    start, stop = vector.getOwnershipRange()
    owned = fixed[(fixed >= start) & (fixed < stop)]
    for dof in owned:
        vector.setValue(int(dof), 0.0, addv=petsc.InsertMode.INSERT_VALUES)
    vector.assemble()


def _set_modal_constraint_diagonal(matrix: Any, model: LargeModel | DistributedLargeModel, petsc: Any) -> None:
    material_scale = 1.0
    for data in model.materials.values():
        material_scale = max(material_scale, float(data.get("E", data.get("E1", 1.0))))
    diagonal = material_scale * 1.0e6
    fixed = fixed_dof_indices(model).astype(petsc.IntType)
    start, stop = matrix.getOwnershipRange()
    for dof in fixed[(fixed >= start) & (fixed < stop)]:
        matrix.setValue(int(dof), int(dof), diagonal, addv=petsc.InsertMode.INSERT_VALUES)
    matrix.assemble()


def _dot(vector: Any, matrix: Any, other: Any) -> float:
    product = vector.duplicate()
    matrix.mult(other, product)
    value = float(other.dot(product))
    product.destroy()
    return value


def _comm_max(comm: Any, value: float, petsc: Any) -> float:
    if hasattr(comm, "tompi4py"):
        mpi_comm = comm.tompi4py()
        try:
            from mpi4py import MPI
        except ImportError:
            return float(value)
        return float(mpi_comm.allreduce(float(value), op=MPI.MAX))
    if hasattr(comm, "allreduce"):
        return float(comm.allreduce(float(value)))
    return float(value)


def _optional_petsc() -> tuple[Any, Any]:
    try:
        from petsc4py import PETSc
    except ImportError as exc:
        raise InfrastructureError("petsc4py is required for large modal/Newmark runs.") from exc
    return PETSc, None


def _optional_slepc() -> tuple[Any, Any]:
    petsc, _ = _optional_petsc()
    try:
        from slepc4py import SLEPc
    except ImportError as exc:
        raise InfrastructureError("slepc4py is required for large modal runs.") from exc
    return petsc, SLEPc
