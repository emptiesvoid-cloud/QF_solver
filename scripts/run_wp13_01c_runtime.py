"""Execute the WP13-01C mixed PETSc/MPI runtime gate.

This runner is deliberately scoped to the WP13-01C runtime experiment.  It
assembles one family-aware mixed partition per MPI rank through PETSc AIJ and
the existing TET4/WEDGE6/HEX8 element kernels.  It does not alter the legacy
large TET4 route or any element formulation.
"""

from __future__ import annotations

# The runner is executable directly from a checkout and therefore adds the
# repository ``src`` directory before importing the package under test.
# ruff: noqa: E402

import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import sys
import time
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel
from solveur.elements.registry import ElementRegistry
from solveur.large.generic_distributed import (
    GenericDistributedModel,
    dispatch_element,
    partition_generic_model,
)


MATERIAL = {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7_800.0}
TOLERANCES = {
    "displacement_relative_l2": 1.0e-10,
    "reaction_relative_l2": 1.0e-10,
    "free_residual_relative_l2": 1.0e-10,
    "equilibrium_relative": 1.0e-10,
    "energy_relative": 1.0e-10,
    "replay_digest_difference": 0,
}


def _mixed_geometry(segments: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    """Return the existing conforming TET4/WEDGE6/HEX8 chain geometry."""

    if segments <= 0:
        raise ValueError("segments must be positive")
    nodes: list[tuple[float, float, float]] = []
    wedge_layers: list[tuple[int, int, int]] = []
    outer_layers: list[tuple[int, int]] = []
    for index in range(segments + 1):
        z = float(index) / float(segments)
        wedge_layers.append((len(nodes), len(nodes) + 1, len(nodes) + 2))
        nodes.extend(((0.0, 0.0, z), (1.0, 0.0, z), (0.0, 1.0, z)))
    apex = len(nodes)
    nodes.append((0.0, 0.0, -1.0))
    for index in range(segments + 1):
        z = float(index) / float(segments)
        outer_layers.append((len(nodes), len(nodes) + 1))
        nodes.extend(((0.0, -1.0, z), (1.0, -1.0, z)))

    elements: list[dict[str, object]] = [
        {
            "type": "TET4",
            "nodes": [wedge_layers[0][0], wedge_layers[0][2], wedge_layers[0][1], apex],
            "material": "solid",
        }
    ]
    for index in range(segments):
        lower = wedge_layers[index]
        upper = wedge_layers[index + 1]
        elements.extend(
            (
                {
                    "type": "WEDGE6",
                    "nodes": [lower[0], lower[1], lower[2], upper[0], upper[1], upper[2]],
                    "material": "solid",
                },
                {
                    "type": "HEX8",
                    "nodes": [
                        outer_layers[index][0],
                        outer_layers[index][1],
                        lower[1],
                        lower[0],
                        outer_layers[index + 1][0],
                        outer_layers[index + 1][1],
                        upper[1],
                        upper[0],
                    ],
                    "material": "solid",
                },
            )
        )
    return np.asarray(nodes, dtype=float), elements


def _rows(elements: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {"type": str(row["type"]), "nodes": [int(node) for node in row["nodes"]], "material": "solid"}
        for row in elements
    ]


def _small_model() -> FiniteElementModel:
    from run_wp07_mixed_static import _manufactured_model

    model, _, _ = _manufactured_model(1)
    return model


def _staged_model(segments: int) -> FiniteElementModel:
    nodes, elements = _mixed_geometry(segments)
    fixed = [
        {"node": index, "dofs": ["UX", "UY", "UZ"]}
        for index, point in enumerate(nodes)
        if abs(float(point[0])) <= 1.0e-14
    ]
    end_nodes = [
        index
        for index, point in enumerate(nodes)
        if abs(float(point[0]) - 1.0) <= 1.0e-14 and abs(float(point[2]) - 1.0) <= 1.0e-14
    ]
    if not end_nodes:
        raise ValueError("staged mixed geometry has no loaded end nodes")
    load = 1.0e5 / float(len(end_nodes))
    loads = [{"node": node, "dof": "UX", "value": load} for node in end_nodes]
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=_rows(elements),
        materials={"solid": dict(MATERIAL)},
        fixed_dofs=fixed,
        loads=loads,
        analysis={"type": "linear_static", "method": "cg"},
        units={"system": "SI"},
    )


def _model_for_case(case: str, segments: int | None) -> FiniteElementModel:
    if case == "small":
        if segments is not None and segments != 1:
            raise ValueError("the small case is fixed at one mixed segment")
        return _small_model()
    defaults = {"stage-a": 3332, "stage-b": 19999, "stage-c": 66666}
    if case not in defaults:
        raise ValueError(f"unknown case {case!r}")
    return _staged_model(int(segments if segments is not None else defaults[case]))


def _fixed_indices(model: FiniteElementModel) -> np.ndarray:
    dofs = model.dof_manager()
    return np.asarray(
        sorted({dofs.index(condition.node, name) for condition in model.fixed_dofs for name in condition.dofs}),
        dtype=np.int64,
    )


def _load_vector(model: FiniteElementModel) -> np.ndarray:
    dofs = model.dof_manager()
    values = np.zeros(dofs.ndof, dtype=float)
    for load in model.loads:
        values[dofs.index(load.node, load.dof)] += float(load.value)
    return values


def _resultant(model: FiniteElementModel, vector: np.ndarray, *, fixed_only: bool) -> np.ndarray:
    dofs = model.dof_manager()
    fixed = set(_fixed_indices(model).tolist()) if fixed_only else None
    components: list[list[float]] = [[], [], []]
    names = ("UX", "UY", "UZ")
    for node, point in enumerate(model.nodes):
        for component, name in enumerate(names):
            index = dofs.index(node, name)
            if fixed is None or index in fixed:
                components[component].append(float(vector[index]))
    return np.asarray([math.fsum(values) for values in components], dtype=float)


def _digest_vectors(*vectors: np.ndarray) -> str:
    digest = hashlib.sha256()
    for vector in vectors:
        array = np.asarray(vector, dtype=np.float64)
        digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _model_digest(model: FiniteElementModel) -> str:
    rows = [
        {"type": item.type, "nodes": list(item.nodes), "material": item.material}
        for item in model.elements
    ]
    payload = {
        "nodes": np.asarray(model.nodes, dtype=np.float64).tolist(),
        "elements": rows,
        "fixed": [{"node": item.node, "dofs": list(item.dofs)} for item in model.fixed_dofs],
        "loads": [{"node": item.node, "dof": item.dof, "value": float(item.value)} for item in model.loads],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _family_counts(model: FiniteElementModel) -> dict[str, int]:
    counts = {"TET4": 0, "WEDGE6": 0, "HEX8": 0}
    for item in model.elements:
        counts[str(item.type).upper()] = counts.get(str(item.type).upper(), 0) + 1
    return counts


def _metrics(
    model: FiniteElementModel,
    displacement: np.ndarray,
    residual: np.ndarray,
    loads: np.ndarray,
    *,
    iterations: int | str,
    runtime_seconds: float,
    peak_memory_mb: float | None,
    energy: float,
) -> dict[str, Any]:
    fixed = _fixed_indices(model)
    free_mask = np.ones(model.dof_manager().ndof, dtype=bool)
    free_mask[fixed] = False
    free_residual = np.asarray(residual)[free_mask]
    load_free = np.asarray(loads)[free_mask]
    residual_relative = float(np.linalg.norm(free_residual) / max(float(np.linalg.norm(load_free)), 1.0))
    external_resultant = _resultant(model, loads, fixed_only=False)
    reaction_resultant = _resultant(model, residual, fixed_only=True)
    equilibrium_relative = float(
        np.linalg.norm(reaction_resultant + external_resultant) / max(float(np.linalg.norm(external_resultant)), 1.0)
    )
    internal = np.asarray(residual, dtype=float) + np.asarray(loads, dtype=float)
    external_work = float(np.dot(displacement, loads))
    energy_identity = float(abs(2.0 * energy - external_work) / max(abs(external_work), 1.0))
    return {
        "ndof": int(model.dof_manager().ndof),
        "element_count": int(len(model.elements)),
        "family_counts": _family_counts(model),
        "runtime_seconds": float(runtime_seconds),
        "iterations": iterations,
        "free_residual_relative": residual_relative,
        "equilibrium_relative": equilibrium_relative,
        "energy": float(energy),
        "energy_identity_relative": energy_identity,
        "displacement_norm": float(np.linalg.norm(displacement)),
        "reaction_norm": float(np.linalg.norm(residual[fixed])),
        "external_load_resultant": external_resultant.tolist(),
        "reaction_resultant": reaction_resultant.tolist(),
        "displacement_digest": _digest_vectors(displacement),
        "reaction_digest": _digest_vectors(residual[fixed]),
        "residual_digest": _digest_vectors(residual),
        "model_digest": _model_digest(model),
        "peak_memory_mb": peak_memory_mb,
        "internal_force_norm": float(np.linalg.norm(internal)),
    }


def _serial_run(model: FiniteElementModel) -> dict[str, Any]:
    started = time.perf_counter()
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    stiffness = assembler.assemble_stiffness(model, dofs)
    loads = assembler.assemble_loads(model, dofs)
    fixed = _fixed_indices(model)
    free = np.setdiff1d(np.arange(dofs.ndof, dtype=np.int64), fixed, assume_unique=True)
    from scipy.sparse.linalg import spsolve

    displacement = np.zeros(dofs.ndof, dtype=float)
    displacement[free] = np.asarray(spsolve(stiffness[free][:, free], loads[free]), dtype=float)
    internal = np.asarray(stiffness @ displacement, dtype=float)
    residual = internal - loads
    energy = 0.5 * float(np.dot(displacement, internal))
    result = _metrics(
        model,
        displacement,
        residual,
        loads,
        iterations="direct",
        runtime_seconds=time.perf_counter() - started,
        peak_memory_mb=float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024.0,
        energy=energy,
    )
    result.update(
        {
            "backend": "serial_global_assembler",
            "rank_count": 1,
            "matrix_nnz": int(stiffness.nnz),
            "reallocations": 0,
            "ghost_nodes": 0,
            "global_gather_present": False,
            "displacement": displacement.tolist(),
            "reaction_vector": residual[fixed].tolist(),
            "residual": residual.tolist(),
            "loads": loads.tolist(),
        }
    )
    return result


def _petsc_vec_gather(vector: Any, comm: Any, ndof: int) -> np.ndarray | None:
    start, stop = vector.getOwnershipRange()
    local = np.asarray(vector.getArray(readonly=True), dtype=float).copy()
    gathered = comm.gather((int(start), int(stop), local), root=0)
    if comm.Get_rank() != 0:
        return None
    values = np.zeros(ndof, dtype=float)
    for first, last, part in gathered:
        values[first:last] = part
    return values


def _reconstruct_reactions(
    solution: Any,
    contributions: list[Any],
    model: FiniteElementModel,
    comm: Any,
    petsc: Any,
) -> np.ndarray:
    """Reduce element internal forces on constrained DOFs only.

    The solution scatter is a result/post-processing exchange.  No matrix,
    connectivity or element-field gather is performed.  Reactions are then
    formed from the already-dispatched local element kernels, avoiding the
    loss of transverse digits caused by a global sparse MatMult cancellation.
    """

    scatter, sequential_solution = petsc.Scatter.toAll(solution)
    scatter.scatter(solution, sequential_solution)
    global_displacement = np.asarray(sequential_solution.getArray(readonly=True), dtype=float).copy()
    fixed = _fixed_indices(model)
    fixed_position = {int(dof): index for index, dof in enumerate(fixed)}
    local_values = np.zeros(fixed.size, dtype=float)
    for contribution in contributions:
        local_force = np.asarray(contribution.stiffness @ global_displacement[contribution.global_dofs], dtype=float)
        for local_index, global_dof in enumerate(contribution.global_dofs):
            position = fixed_position.get(int(global_dof))
            if position is not None:
                local_values[position] += float(local_force[local_index])
    from mpi4py import MPI

    reaction = np.zeros_like(local_values)
    comm.Allreduce(local_values, reaction, op=MPI.SUM)
    return reaction


def _petsc_row_pattern(generic: GenericDistributedModel, row_start: int, row_stop: int) -> tuple[np.ndarray, np.ndarray]:
    row_columns: list[set[int]] = [set() for _ in range(row_stop - row_start)]
    for element in generic.iter_elements():
        spec = ElementRegistry.get(element.family)
        edofs = np.asarray(
            [index for node in element.nodes for index in generic.dofs.node_indices(node, spec.dofs)],
            dtype=np.int64,
        )
        for row in edofs:
            if row_start <= int(row) < row_stop:
                row_columns[int(row) - row_start].update(int(column) for column in edofs)
    diag = np.asarray(
        [sum(row_start <= column < row_stop for column in columns) for columns in row_columns],
        dtype=np.int32,
    )
    offdiag = np.asarray(
        [sum(column < row_start or column >= row_stop for column in columns) for columns in row_columns],
        dtype=np.int32,
    )
    return diag, offdiag


def _petsc_run(model: FiniteElementModel, pc_type: str, ksp_type: str) -> dict[str, Any] | None:
    from mpi4py import MPI
    from petsc4py import PETSc

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    generic = GenericDistributedModel.from_finite_element_model(model)
    partitions = partition_generic_model(generic, size)
    partition = partitions[rank]
    ndof = generic.ndof
    base, remainder = divmod(ndof, size)
    row_start = rank * base + min(rank, remainder)
    row_stop = row_start + base + (1 if rank < remainder else 0)
    diag, offdiag = _petsc_row_pattern(generic, row_start, row_stop)
    petsc_diag = np.asarray(diag, dtype=PETSc.IntType)
    petsc_offdiag = np.asarray(offdiag, dtype=PETSc.IntType)

    started = time.perf_counter()
    matrix = PETSc.Mat().createAIJ(
        size=((row_stop - row_start, ndof), (row_stop - row_start, ndof)),
        nnz=(petsc_diag, petsc_offdiag),
        comm=PETSc.COMM_WORLD,
    )
    matrix.setUp()
    contributions = []
    for element in partition.elements:
        contribution = dispatch_element(generic, element)
        rows = np.asarray(contribution.global_dofs, dtype=PETSc.IntType)
        matrix.setValues(rows, rows, contribution.stiffness, addv=PETSc.InsertMode.ADD_VALUES)
        contributions.append(contribution)
    matrix.assemble()
    # MatGetInfo is collective on this PETSc build and is not reliable through
    # the image's mixed MPI ABI.  Keep the preallocation contract explicit and
    # report runtime malloc counters as unavailable rather than guessing.

    rhs = matrix.createVecRight()
    rhs.set(0.0)
    node_owner = partitions[0].node_owner
    dofs = model.dof_manager()
    for load in model.loads:
        if int(node_owner[int(load.node)]) == rank:
            rhs.setValue(dofs.index(load.node, load.dof), float(load.value), addv=PETSc.InsertMode.ADD_VALUES)
    rhs.assemble()
    rhs_original = rhs.duplicate()
    rhs.copy(rhs_original)

    fixed = _fixed_indices(model).astype(PETSc.IntType)
    work_matrix = matrix.copy()
    solver_rhs = rhs.duplicate()
    rhs.copy(solver_rhs)
    solver_rhs.assemble()
    solver_scale = 1.0 / float(MATERIAL["E"])
    work_matrix.scale(solver_scale)
    diagonal = work_matrix.createVecLeft()
    work_matrix.getDiagonal(diagonal)
    diagonal_values = np.asarray(diagonal.getArray(readonly=True), dtype=float).copy()
    if np.any(diagonal_values <= 0.0):
        raise RuntimeError("PETSc mixed stiffness has a non-positive free diagonal before scaling")
    diagonal_scale = diagonal.duplicate()
    diagonal_scale.set(0.0)
    scale_values = 1.0 / np.sqrt(diagonal_values)
    diagonal_scale.setArray(scale_values)
    row_start, row_stop = matrix.getOwnershipRange()
    local_fixed = fixed[(fixed >= row_start) & (fixed < row_stop)]
    for dof in local_fixed:
        scale_values[int(dof) - row_start] = 1.0
    diagonal_scale.setArray(scale_values)
    work_matrix.diagonalScale(diagonal_scale, diagonal_scale)
    solver_rhs.scale(solver_scale)
    scaled_rhs = solver_rhs.duplicate()
    solver_rhs.copy(scaled_rhs)
    scaled_rhs.pointwiseMult(diagonal_scale, scaled_rhs)
    solver_rhs = scaled_rhs
    work_matrix.zeroRowsColumns(fixed, diag=1.0)
    for dof in local_fixed:
        solver_rhs.setValue(int(dof), 0.0, addv=PETSc.InsertMode.INSERT_VALUES)
    solver_rhs.assemble()

    solution = rhs.duplicate()
    solution.set(0.0)
    ksp = PETSc.KSP().create(comm=PETSc.COMM_WORLD)
    ksp.setOperators(work_matrix)
    selected_ksp = "preonly" if ksp_type == "auto" and str(pc_type).lower() == "lu" else ksp_type
    if selected_ksp == "auto":
        selected_ksp = "cg"
    ksp.setType(selected_ksp)
    ksp.getPC().setType(str(pc_type))
    ksp.setTolerances(rtol=1.0e-13, atol=1.0e-14, max_it=10000)
    # The gate is on the physical free residual, not a preconditioned norm.
    # Make PETSc's stopping criterion use the same quantity.
    ksp.setNormType(PETSc.KSP.NormType.UNPRECONDITIONED)
    ksp.setFromOptions()
    ksp.solve(solver_rhs, solution)
    reason = int(ksp.getConvergedReason())
    if reason <= 0:
        raise RuntimeError(f"PETSc KSP did not converge: reason={reason}")
    physical_solution = solution.duplicate()
    solution.copy(physical_solution)
    physical_solution.pointwiseMult(diagonal_scale, physical_solution)
    solution = physical_solution
    internal = matrix.createVecRight()
    matrix.mult(solution, internal)
    residual = internal.duplicate()
    internal.copy(residual)
    residual.axpy(-1.0, rhs_original)
    refinement_steps = 0
    if selected_ksp == "preonly":
        # Direct factorization is accurate enough for the free equations, but
        # the global reaction resultant can lose digits when physical forces
        # are reconstructed from large stiffness coefficients.  Correct only
        # the algebraic residual, leaving the FE matrix and all gates fixed.
        for _ in range(2):
            correction_rhs = internal.duplicate()
            internal.copy(correction_rhs)
            correction_rhs.axpy(-1.0, rhs_original)
            correction_rhs.scale(-solver_scale)
            scaled_correction = correction_rhs.duplicate()
            correction_rhs.copy(scaled_correction)
            scaled_correction.pointwiseMult(diagonal_scale, scaled_correction)
            correction_rhs = scaled_correction
            for dof in local_fixed:
                correction_rhs.setValue(int(dof), 0.0, addv=PETSc.InsertMode.INSERT_VALUES)
            correction_rhs.assemble()
            correction_scaled = solution.duplicate()
            ksp.solve(correction_rhs, correction_scaled)
            correction_reason = int(ksp.getConvergedReason())
            if correction_reason <= 0:
                raise RuntimeError(f"PETSc residual correction did not converge: reason={correction_reason}")
            correction = correction_scaled.duplicate()
            correction_scaled.copy(correction)
            correction.pointwiseMult(diagonal_scale, correction)
            solution.axpy(1.0, correction)
            refinement_steps += 1
            matrix.mult(solution, internal)
    residual = internal.duplicate()
    internal.copy(residual)
    residual.axpy(-1.0, rhs_original)
    energy = 0.5 * float(solution.dot(internal))
    runtime = time.perf_counter() - started
    max_runtime = float(comm.allreduce(runtime, op=MPI.MAX))
    max_memory = float(comm.allreduce(float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024.0, op=MPI.MAX))
    ghost_nodes_global_sum = int(comm.allreduce(partition.ghost_node_ids.size, op=MPI.SUM))
    reconstructed_reactions = _reconstruct_reactions(solution, contributions, model, comm, PETSc)
    displacement = _petsc_vec_gather(solution, comm, ndof)
    residual_values = _petsc_vec_gather(residual, comm, ndof)
    loads = _petsc_vec_gather(rhs_original, comm, ndof)
    if rank != 0:
        return None
    assert displacement is not None and residual_values is not None and loads is not None
    residual_values[_fixed_indices(model)] = reconstructed_reactions
    result = _metrics(
        model,
        displacement,
        residual_values,
        loads,
        iterations=int(ksp.getIterationNumber()),
        runtime_seconds=max_runtime,
        peak_memory_mb=max_memory,
        energy=energy,
    )
    result.update(
        {
            "backend": "petsc_mixed_distributed",
            "rank_count": size,
            "matrix_nnz": None,
            "reallocations": "NOT_CAPTURED_MATGETINFO_MPI_ABI",
            "ghost_nodes_local": int(partition.ghost_node_ids.size),
            "ghost_nodes_global_sum": ghost_nodes_global_sum,
            "global_gather_present": False,
            "result_only_solution_scatter": True,
            "preallocation": {
                "strategy": "global_connectivity_exact_for_PETSc_owned_rows",
                "diag_nnz_sum": int(np.sum(diag, dtype=np.int64)),
                "offdiag_nnz_sum": int(np.sum(offdiag, dtype=np.int64)),
                "matrix_mallocs": "NOT_CAPTURED_MATGETINFO_MPI_ABI",
            },
            "solver_scaling": {
                "type": "uniform_plus_symmetric_diagonal",
                "uniform_factor": solver_scale,
                "diagonal_scale_min": float(np.min(scale_values)),
                "diagonal_scale_max": float(np.max(scale_values)),
            },
            "linear_solves": int(1 + refinement_steps),
            "residual_refinement_steps": refinement_steps,
            "family_counts": generic.element_counts(),
            "local_family_counts": partition.element_counts,
            "local_owned_nodes": int(partition.owned_node_ids.size),
            "local_ghost_nodes": int(partition.ghost_node_ids.size),
            "displacement": displacement.tolist() if ndof <= 1000 else None,
            "reaction_vector": residual_values[_fixed_indices(model)].tolist() if ndof <= 1000 else None,
            "residual": residual_values.tolist() if ndof <= 1000 else None,
            "loads": loads.tolist() if ndof <= 1000 else None,
        }
    )
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("small", "stage-a", "stage-b", "stage-c"), required=True)
    parser.add_argument("--backend", choices=("serial", "petsc"), required=True)
    parser.add_argument("--segments", type=int, default=None)
    parser.add_argument("--pc-type", default="jacobi")
    parser.add_argument("--ksp-type", default="auto")
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    model = _model_for_case(args.case, args.segments)
    if args.backend == "serial":
        if args.case != "small":
            raise SystemExit("serial backend is only defined for the 33-DOF reference case")
        result = _serial_run(model)
    else:
        result = _petsc_run(model, args.pc_type, args.ksp_type)
        if result is None:
            return 0
    payload = {
        "schema_version": 1,
        "case": args.case,
        "backend": args.backend,
        "segments": args.segments,
        "tolerances": TOLERANCES,
        "result": result,
    }
    encoded = json.dumps(payload, sort_keys=True, indent=2, allow_nan=False)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
