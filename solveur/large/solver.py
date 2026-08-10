"""Large-scale linear static TET4 solver."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from solveur.core.errors import InfrastructureError, InputValidationError, MeshValidationError, NumericalConvergenceError
from solveur.core.linear_methods import LinearSystemSolver
from solveur.large.assembler import (
    ChunkedScipyAssembler,
    PetscTET4Assembler,
    assemble_loads,
    fixed_dof_indices,
    partition_range,
)
from solveur.large.dofs import dof_index
from solveur.large.distributed_model import DistributedLargeModel, inspect_distributed_large_model
from solveur.large.audit import LargeAuditReport, inspect_large_model
from solveur.large.matrix_free import solve_structured_matrix_free
from solveur.large.model import LargeModel
from solveur.large.mpi_diagnostics import petsc_ksp_diagnostics
from solveur.large.readiness import SCIPY_DEFAULT_MAX_DOFS


@dataclass(frozen=True)
class LargeSolveResult:
    """Summary of a large-scale solve with file-backed displacements."""

    status: str
    backend: str
    summary: dict[str, Any]
    audit: LargeAuditReport
    output_files: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "backend": self.backend,
            "summary": self.summary,
            "audit": self.audit.to_dict(),
            "output_files": self.output_files,
        }


def solve_large_model(
    model: LargeModel,
    output_dir: str | Path | None = None,
    *,
    solver_backend: str = "scipy",
    preconditioner: str = "jacobi",
    chunk_size: int = 4096,
    parameters: dict[str, Any] | None = None,
) -> LargeSolveResult:
    """Solve a large TET4 linear static model and optionally write file-backed outputs."""
    backend = solver_backend.lower()
    params = {**model.analysis.get("parameters", {}), **(parameters or {})}
    if isinstance(model, DistributedLargeModel):
        if backend != "petsc":
            raise InputValidationError("Distributed large models require the PETSc backend.")
        initial_audit = inspect_distributed_large_model(model, _mpi_comm())
    else:
        initial_audit = inspect_large_model(model)
    if initial_audit.status == "FAIL":
        raise MeshValidationError("Large model validation failed: " + "; ".join(initial_audit.errors))
    if backend == "scipy":
        _guard_scipy_size(model, params)
    if backend == "scipy":
        result, displacement = _solve_scipy(model, preconditioner=preconditioner, chunk_size=chunk_size, params=params)
    elif backend == "petsc":
        result, displacement = _solve_petsc(
            model,
            preconditioner=preconditioner,
            chunk_size=chunk_size,
            params=params,
            distributed_output_dir=Path(output_dir) if output_dir is not None and isinstance(model, DistributedLargeModel) else None,
        )
    elif backend == "matrix_free":
        result, displacement = _solve_matrix_free(model, chunk_size=chunk_size, params=params)
    else:
        raise InputValidationError(
            f"Unsupported large solver backend {solver_backend!r}; expected 'scipy', 'petsc' or 'matrix_free'."
        )
    files: dict[str, str] = {}
    if output_dir is not None:
        if backend == "petsc":
            comm = _mpi_comm()
            if comm.rank == 0:
                files = (
                    _write_distributed_outputs(result, Path(output_dir))
                    if isinstance(model, DistributedLargeModel)
                    else _write_outputs(model, result, displacement, Path(output_dir))
                )
            files = comm.bcast(files, root=0)
            comm.Barrier()
        else:
            files = _write_outputs(model, result, displacement, Path(output_dir))
        result = LargeSolveResult(result.status, result.backend, result.summary, result.audit, files)
    return result


def _solve_scipy(
    model: LargeModel,
    *,
    preconditioner: str,
    chunk_size: int,
    params: dict[str, Any],
) -> tuple[LargeSolveResult, np.ndarray]:
    assembly_start = time.perf_counter()
    assembly = ChunkedScipyAssembler(chunk_size=chunk_size).assemble(model)
    assembly_time = time.perf_counter() - assembly_start
    free = np.setdiff1d(np.arange(model.ndof, dtype=np.int64), assembly.fixed_dofs)
    if free.size == 0:
        raise MeshValidationError("No free degree of freedom remains after large-model boundary conditions.")
    reduced = assembly.stiffness[free, :][:, free]
    solve_params = {
        "preconditioner": preconditioner,
        "rtol": float(params.get("rtol", 1.0e-8)),
        "atol": float(params.get("atol", 0.0)),
        "maxiter": params.get("max_it", params.get("maxiter", 10000)),
    }
    method = str(params.get("method", model.analysis.get("method", "cg"))).lower()
    solve_start = time.perf_counter()
    solution, info = LinearSystemSolver().solve(reduced, assembly.loads[free], method=method, parameters=solve_params)
    solve_time = time.perf_counter() - solve_start
    if not info.converged:
        raise NumericalConvergenceError(f"Large SciPy solve did not converge; residual={info.residual_norm:.6e}.")
    displacement = np.zeros(model.ndof, dtype=float)
    displacement[free] = solution
    audit = inspect_large_model(model, stiffness=assembly.stiffness, loads=assembly.loads, displacement=displacement)
    summary = _summary(model, "scipy", info.to_dict(), assembly_time, solve_time, audit)
    return LargeSolveResult("PASS", "scipy", summary, audit), displacement


def _guard_scipy_size(model: LargeModel, params: dict[str, Any]) -> None:
    max_dofs = int(params.get("scipy_max_dofs", SCIPY_DEFAULT_MAX_DOFS))
    if model.ndof > max_dofs:
        raise InputValidationError(
            "SciPy large backend is intentionally limited to "
            f"{max_dofs} dofs to avoid memory explosion; model has {model.ndof} dofs. "
            "Use solver_backend='petsc' for qualification-scale runs."
        )


def _solve_petsc(
    model: LargeModel,
    *,
    preconditioner: str,
    chunk_size: int,
    params: dict[str, Any],
    distributed_output_dir: Path | None,
) -> tuple[LargeSolveResult, np.ndarray]:
    _require_mpi4py()
    petsc = _petsc()
    comm = _mpi_comm()
    _mpi_trace(comm, "assembly:start")
    assembly_start = time.perf_counter()
    matrix_format = str(params.get("matrix_format", "baij")).lower()
    matrix = PetscTET4Assembler(chunk_size=chunk_size, matrix_format=matrix_format).assemble(model)
    _mpi_trace(comm, "assembly:matrix-complete")
    rhs = matrix.createVecRight()
    if isinstance(model, DistributedLargeModel):
        load_start, load_stop = 0, model.load_values.size
    else:
        load_start, load_stop = partition_range(model.load_values.size, comm.rank, comm.size)
    if load_stop > load_start:
        load_indices = dof_index(
            model.load_nodes[load_start:load_stop],
            model.load_components[load_start:load_stop],
        ).astype(petsc.IntType)
        rhs.setValues(
            load_indices,
            model.load_values[load_start:load_stop],
            addv=petsc.InsertMode.ADD_VALUES,
        )
    rhs.assemble()
    _mpi_trace(comm, "assembly:rhs-complete")
    fixed = fixed_dof_indices(model).astype(petsc.IntType)
    row_start, row_stop = rhs.getOwnershipRange()
    local_fixed = fixed[(fixed >= row_start) & (fixed < row_stop)]
    _mpi_trace(comm, f"assembly:dirichlet-start local_count={local_fixed.size}")
    for dof in local_fixed:
        rhs.setValue(int(dof), 0.0, addv=petsc.InsertMode.INSERT_VALUES)
    rhs.assemble()
    _mpi_trace(comm, "assembly:dirichlet-complete")
    assembly_time = _mpi_max_time(comm, time.perf_counter() - assembly_start)
    solution = rhs.duplicate()
    restart_from = params.get("restart_from")
    restart_used = restart_from is not None
    initial_guess_norm = _load_petsc_restart(solution, Path(str(restart_from)), model) if restart_used else 0.0
    ksp = petsc.KSP().create()
    ksp.setOperators(matrix)
    ksp.setType(str(params.get("ksp_type", "cg")))
    requested_pc = str(params.get("pc_type", preconditioner or "gamg"))
    ksp.getPC().setType(requested_pc)
    if requested_pc.lower() == "hypre":
        ksp.getPC().setHYPREType(str(params.get("hypre_type", "boomeramg")))
    ksp.setTolerances(
        rtol=float(params.get("rtol", 1.0e-8)),
        atol=float(params.get("atol", 0.0)),
        max_it=int(params.get("max_it", 10000)),
    )
    ksp.setInitialGuessNonzero(restart_used)
    explicit_options = {str(key): value for key, value in dict(params.get("petsc_options", {})).items()}
    automatic_options = _automatic_petsc_options(
        requested_pc,
        comm.size,
        explicit_keys=set(explicit_options),
        existing_keys={key for key in ("pc_gamg_repartition",) if petsc.Options().hasName(key)},
    )
    for key, value in {**automatic_options, **explicit_options}.items():
        petsc.Options()[key] = value
    ksp.setFromOptions()
    _mpi_trace(comm, "solve:setup-start")
    setup_start = time.perf_counter()
    try:
        ksp.setUp()
    except Exception as exc:
        raise InfrastructureError(
            f"PETSc preconditioner setup failed for pc_type={ksp.getPC().getType()!r}: {exc}"
        ) from exc
    setup_time = _mpi_max_time(comm, time.perf_counter() - setup_start)
    _mpi_trace(comm, "solve:iterations-start")
    iteration_start = time.perf_counter()
    try:
        ksp.solve(rhs, solution)
    except Exception as exc:
        raise NumericalConvergenceError(f"PETSc KSP execution failed: {exc}") from exc
    iteration_time = _mpi_max_time(comm, time.perf_counter() - iteration_start)
    _mpi_trace(comm, "solve:complete")
    solve_time = setup_time + iteration_time
    converged = ksp.getConvergedReason() > 0
    if not converged:
        raise NumericalConvergenceError(f"PETSc solve did not converge; reason={ksp.getConvergedReason()}.")
    local_displacement = np.asarray(solution.getArray(readonly=True), dtype=float).copy()
    if not np.all(np.isfinite(local_displacement)):
        raise NumericalConvergenceError("PETSc solve produced non-finite displacements.")
    matrix_times_solution = rhs.duplicate()
    matrix.mult(solution, matrix_times_solution)
    residual_vector = matrix_times_solution.copy()
    residual_vector.axpy(-1.0, rhs)
    solution_metrics = {
        "displacement_norm": float(solution.norm()),
        "load_norm": float(rhs.norm()),
        "true_residual_norm": float(residual_vector.norm()),
        "strain_energy": 0.5 * float(solution.dot(matrix_times_solution)),
        "external_work": float(solution.dot(rhs)),
    }
    if isinstance(model, DistributedLargeModel):
        ownership_ranges = [list(values) for values in comm.allgather(solution.getOwnershipRange())]
        if distributed_output_dir is not None:
            _write_displacement_mpi(solution, model, distributed_output_dir, comm, ownership_ranges)
        displacement = np.empty(0, dtype=float)
    else:
        displacement, ownership_ranges = _gather_petsc_displacement(solution, model.ndof, comm)
    _mpi_trace(comm, "solution:gather-complete")
    solver_info = {
        "method": ksp.getType(),
        "preconditioner": ksp.getPC().getType(),
        "preconditioner_subtype": ksp.getPC().getHYPREType() if ksp.getPC().getType() == "hypre" else None,
        "iterations": int(ksp.getIterationNumber()),
        "residual_norm": float(ksp.getResidualNorm()),
        "converged": True,
        "mpi_size": int(comm.size),
        "distributed": bool(comm.size > 1),
        "ownership_ranges": ownership_ranges,
        "matrix_format": matrix_format,
        "setup_time_seconds": setup_time,
        "iteration_time_seconds": iteration_time,
        "automatic_petsc_options": automatic_options,
        "explicit_petsc_options": explicit_options,
        "preconditioner_diagnostics": petsc_ksp_diagnostics(ksp, matrix),
        "restart_used": restart_used,
        "restart_source": str(restart_from) if restart_used else None,
        "initial_guess_norm": initial_guess_norm,
    }
    if isinstance(model, DistributedLargeModel):
        audit = inspect_distributed_large_model(model, comm, solution_metrics=solution_metrics)
    else:
        audit_payload = None
        if comm.rank == 0:
            audit_payload = inspect_large_model(
                model,
                loads=assemble_loads(model),
                displacement=displacement,
            ).to_dict()
        audit = _audit_from_dict(comm.bcast(audit_payload, root=0))
    _mpi_trace(comm, "audit:broadcast-complete")
    summary = _summary(model, "petsc", solver_info, assembly_time, solve_time, audit)
    summary["mpi"] = {
        "size": int(comm.size),
        "distributed_assembly": bool(comm.size > 1),
        "element_partition": getattr(model, "partition_strategy", "contiguous"),
        "input_arrays_replicated_per_rank": not isinstance(model, DistributedLargeModel),
        "boundary_arrays_distributed": isinstance(model, DistributedLargeModel),
        "local_fixed_dof_count": int(fixed.size) if isinstance(model, DistributedLargeModel) else None,
        "local_load_count": int(model.load_values.size) if isinstance(model, DistributedLargeModel) else None,
        "local_fixed_dof_counts": [int(value) for value in comm.allgather(fixed.size)]
        if isinstance(model, DistributedLargeModel)
        else None,
        "local_load_counts": [int(value) for value in comm.allgather(model.load_values.size)]
        if isinstance(model, DistributedLargeModel)
        else None,
        "partitioned_hdf5_input": isinstance(model, DistributedLargeModel),
        "global_connectivity_replicated": not isinstance(model, DistributedLargeModel),
        "global_nodes_replicated": not isinstance(model, DistributedLargeModel),
        "displacement_gathered_on_root_only": not isinstance(model, DistributedLargeModel),
        "displacement_mpi_io": isinstance(model, DistributedLargeModel),
    }
    return LargeSolveResult("PASS", "petsc", summary, audit), displacement


def _gather_petsc_displacement(solution: Any, ndof: int, comm: Any) -> tuple[np.ndarray, list[list[int]]]:
    local = np.asarray(solution.getArray(readonly=True), dtype=np.float64)
    ownership = tuple(int(value) for value in solution.getOwnershipRange())
    ownership_ranges = [list(values) for values in comm.allgather(ownership)]
    counts = np.asarray([stop - start for start, stop in ownership_ranges], dtype=np.int32)
    offsets = np.zeros(comm.size, dtype=np.int32)
    if comm.size > 1:
        offsets[1:] = np.cumsum(counts[:-1])
    gathered = np.empty(ndof, dtype=np.float64) if comm.rank == 0 else np.empty(0, dtype=np.float64)
    receive = [gathered, counts, offsets, _mpi().DOUBLE] if comm.rank == 0 else None
    comm.Gatherv(local, receive, root=0)
    return gathered, ownership_ranges


def _load_petsc_restart(solution: Any, path: Path, model: LargeModel) -> float:
    source = path / "displacements.bin" if path.is_dir() else path
    metadata_path = source.with_name("displacements_metadata.json")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        shape = tuple(int(value) for value in metadata["shape"])
        dtype = np.dtype("<f8" if metadata.get("byte_order", "little") == "little" else ">f8")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"Invalid PETSc restart metadata: {exc}") from exc
    if shape != (model.node_count, 3) or metadata.get("dtype") != "float64":
        raise InputValidationError("PETSc restart displacement metadata is incompatible with the model.")
    if source.stat().st_size != model.ndof * dtype.itemsize:
        raise InputValidationError("PETSc restart displacement file size is incompatible with the model.")
    start, stop = solution.getOwnershipRange()
    local = np.fromfile(source, dtype=dtype, count=stop - start, offset=start * dtype.itemsize)
    if local.size != stop - start or not np.all(np.isfinite(local)):
        raise InputValidationError("PETSc restart displacement slice is incomplete or non-finite.")
    solution.getArray()[:] = local
    return float(solution.norm())


def _audit_from_dict(data: dict[str, Any]) -> LargeAuditReport:
    return LargeAuditReport(
        status=str(data["status"]),
        errors=tuple(str(value) for value in data.get("errors", [])),
        warnings=tuple(str(value) for value in data.get("warnings", [])),
        details=dict(data.get("details", {})),
    )


def _solve_matrix_free(
    model: LargeModel,
    *,
    chunk_size: int,
    params: dict[str, Any],
) -> tuple[LargeSolveResult, np.ndarray]:
    solve = solve_structured_matrix_free(
        model,
        chunk_size=chunk_size,
        rtol=float(params.get("rtol", 1.0e-8)),
        atol=float(params.get("atol", 0.0)),
        maxiter=int(params.get("max_it", params.get("maxiter", 10000))),
    )
    audit = inspect_large_model(model, loads=assemble_loads(model), displacement=solve.displacement)
    summary = _summary(model, "matrix_free", solve.solver_info, 0.0, solve.solve_time_seconds, audit)
    summary["estimated_core_memory_bytes"] = int(
        8 * (model.nodes.size + model.tet4.size + model.ndof) + solve.operator_memory_bytes
    )
    summary["matrix_free_operator_memory_bytes"] = solve.operator_memory_bytes
    return LargeSolveResult("PASS", "matrix_free", summary, audit), solve.displacement


def _summary(
    model: LargeModel,
    backend: str,
    solver_info: dict[str, Any],
    assembly_time: float,
    solve_time: float,
    audit: LargeAuditReport,
) -> dict[str, Any]:
    return {
        "analysis": model.analysis.get("type", ""),
        "node_count": model.node_count,
        "element_count": model.element_count,
        "ndof": model.ndof,
        "backend": backend,
        "solver": solver_info,
        "assembly_time_seconds": float(assembly_time),
        "solve_time_seconds": float(solve_time),
        "estimated_core_memory_bytes": int(8 * (model.nodes.size + model.tet4.size + model.ndof)),
        "audit_status": audit.status,
    }


def _write_outputs(model: LargeModel, result: LargeSolveResult, displacement: np.ndarray, directory: Path) -> dict[str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    displacements_path = directory / "displacements.h5"
    try:
        _write_displacements_hdf5(model, displacement, displacements_path)
    except ImportError:
        displacements_path = directory / "displacements.npz"
        np.savez_compressed(displacements_path, displacements=displacement.reshape((model.node_count, 3)))
    summary_path = directory / "summary.json"
    audit_path = directory / "audit_large.json"
    summary_path.write_text(json.dumps(result.summary, indent=2), encoding="utf-8")
    audit_path.write_text(json.dumps(result.audit.to_dict(), indent=2), encoding="utf-8")
    return {
        "summary": summary_path.name,
        "audit_large": audit_path.name,
        "displacements": displacements_path.name,
    }


def _write_distributed_outputs(result: LargeSolveResult, directory: Path) -> dict[str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    summary_path = directory / "summary.json"
    audit_path = directory / "audit_large.json"
    summary_path.write_text(json.dumps(result.summary, indent=2), encoding="utf-8")
    audit_path.write_text(json.dumps(result.audit.to_dict(), indent=2), encoding="utf-8")
    return {
        "summary": summary_path.name,
        "audit_large": audit_path.name,
        "displacements": "displacements.bin",
        "displacements_metadata": "displacements_metadata.json",
    }


def _write_displacement_mpi(
    solution: Any,
    model: DistributedLargeModel,
    directory: Path,
    comm: Any,
    ownership_ranges: list[list[int]],
) -> None:
    if comm.rank == 0:
        directory.mkdir(parents=True, exist_ok=True)
    comm.Barrier()
    path = directory / "displacements.bin"
    handle = _mpi().File.Open(comm, str(path), _mpi().MODE_CREATE | _mpi().MODE_WRONLY)
    handle.Set_size(model.ndof * np.dtype(np.float64).itemsize)
    start, _ = solution.getOwnershipRange()
    local = np.asarray(solution.getArray(readonly=True), dtype=np.float64)
    handle.Write_at_all(int(start) * np.dtype(np.float64).itemsize, local)
    handle.Close()
    if comm.rank == 0:
        metadata = {
            "format": "qf_solver_mpi_binary_v1",
            "dtype": "float64",
            "byte_order": "little" if np.little_endian else "big",
            "shape": [model.node_count, 3],
            "flat_size": model.ndof,
            "layout": "node_by_translation_component",
            "ownership_ranges": ownership_ranges,
        }
        (directory / "displacements_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    comm.Barrier()


def _write_displacements_hdf5(model: LargeModel, displacement: np.ndarray, path: Path) -> None:
    try:
        import h5py
    except ImportError as exc:
        raise InfrastructureError("HDF5 displacement output requires h5py.") from exc
    with h5py.File(path, "w") as handle:
        handle.create_dataset("displacements", data=displacement.reshape((model.node_count, 3)), chunks=True)
        handle.attrs["layout"] = "node_by_translation_component"


def _petsc() -> Any:
    try:
        from petsc4py import PETSc
    except ImportError as exc:
        raise InfrastructureError("PETSc backend requires optional dependency petsc4py.") from exc
    return PETSc


def _require_mpi4py() -> None:
    _mpi()


def _mpi() -> Any:
    try:
        from mpi4py import MPI
    except ImportError as exc:
        raise InfrastructureError("PETSc/MPI backend requires optional dependency mpi4py.") from exc
    return MPI


def _mpi_comm() -> Any:
    return _mpi().COMM_WORLD


def _mpi_trace(comm: Any, message: str) -> None:
    if os.environ.get("QF_SOLVER_MPI_TRACE") == "1":
        print(f"[QF_solver MPI rank={comm.rank}/{comm.size}] {message}", flush=True)


def _mpi_max_time(comm: Any, value: float) -> float:
    return float(comm.allreduce(float(value), op=_mpi().MAX))


def _automatic_petsc_options(
    pc_type: str,
    mpi_size: int,
    *,
    explicit_keys: set[str],
    existing_keys: set[str],
) -> dict[str, Any]:
    key = "pc_gamg_repartition"
    if pc_type.lower() == "gamg" and mpi_size >= 4 and key not in explicit_keys and key not in existing_keys:
        return {key: True}
    return {}
