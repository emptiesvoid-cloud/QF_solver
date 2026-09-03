"""Chunked large-model assembly backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix
from time import perf_counter

from solveur.core.errors import InfrastructureError
from solveur.core.assembly.sparse import SparseCsrAccumulator

from solveur.large.dofs import dof_index
from solveur.large.materials import create_large_material
from solveur.large.model import LargeModel
from solveur.large.telemetry import AssemblyTelemetry
from solveur.large.tet4_batch import (
    apply_homogeneous_constraints_batch,
    element_dofs_batch,
    petsc_block_values_batch,
    tet4_mass_batch,
    tet4_stiffness_batch,
)
from solveur.materials.solid import SolidConstitutiveMaterial


@dataclass(frozen=True)
class ScipyLargeAssembly:
    """Sparse matrix, load vector and fixed dofs assembled for a large model."""

    stiffness: csr_matrix
    loads: np.ndarray
    fixed_dofs: np.ndarray
    diagnostics: dict[str, object] | None = None


class ChunkedScipyAssembler:
    """Assemble large TET4 matrices in chunks for tests and medium models."""

    def __init__(self, chunk_size: int = 4096) -> None:
        self.chunk_size = max(1, int(chunk_size))

    def assemble(self, model: LargeModel) -> ScipyLargeAssembly:
        accumulator = SparseCsrAccumulator((model.ndof, model.ndof))
        materials = _material_cache(model)
        peak_chunk_entries = 0
        chunk_build_seconds = 0.0
        element_kernel_seconds = 0.0
        sparse_conversion_seconds = 0.0
        chunk_fusion_seconds = 0.0
        for start in range(0, model.element_count, self.chunk_size):
            stop = min(start + self.chunk_size, model.element_count)
            chunk, kernel_seconds, conversion_seconds = self._chunk_matrix(
                model,
                start,
                stop,
                materials,
            )
            element_kernel_seconds += kernel_seconds
            sparse_conversion_seconds += conversion_seconds
            chunk_build_seconds += kernel_seconds + conversion_seconds
            fusion_started = perf_counter()
            accumulator.add(chunk)
            chunk_fusion_seconds += perf_counter() - fusion_started
            peak_chunk_entries = max(peak_chunk_entries, int(chunk.nnz))
        finalize_started = perf_counter()
        stiffness = accumulator.finalize()
        sparse_finalize_seconds = perf_counter() - finalize_started
        return ScipyLargeAssembly(
            stiffness=stiffness,
            loads=assemble_loads(model),
            fixed_dofs=fixed_dof_indices(model),
            diagnostics={
                "chunk_size": int(self.chunk_size),
                "chunk_count": int(accumulator.chunk_count),
                "peak_chunk_nnz": int(peak_chunk_entries),
                "accumulator_occupied_levels": int(accumulator.occupied_levels),
                "final_nnz": int(stiffness.nnz),
                "sparse_memory_bytes": int(
                    stiffness.data.nbytes + stiffness.indices.nbytes + stiffness.indptr.nbytes
                ),
                "assembly_phase_seconds": {
                    "chunk_build": chunk_build_seconds,
                    "element_kernel": element_kernel_seconds,
                    "chunk_sparse_conversion": sparse_conversion_seconds,
                    "chunk_fusion": chunk_fusion_seconds,
                    "sparse_finalize": sparse_finalize_seconds,
                },
                "sparse_conversion_method": "csr_constructor",
                "material_cache_reused": True,
            },
        )

    @staticmethod
    def _chunk_matrix(
        model: LargeModel,
        start: int,
        stop: int,
        materials: dict[int, SolidConstitutiveMaterial],
    ) -> tuple[csr_matrix, float, float]:
        nodes = model.tet4[start:stop]
        edofs = element_dofs_batch(nodes)
        kernel_started = perf_counter()
        stiffness = _stiffness_batch(model, start, stop, materials)
        kernel_seconds = perf_counter() - kernel_started
        conversion_started = perf_counter()
        rows = np.repeat(edofs, 12, axis=1).ravel()
        cols = np.tile(edofs, (1, 12)).ravel()
        vals = stiffness.ravel()
        # The direct constructor preserves duplicate summation while avoiding
        # a separate intermediate COO object for each chunk.
        chunk = csr_matrix((vals, (rows, cols)), shape=(model.ndof, model.ndof))
        conversion_seconds = perf_counter() - conversion_started
        return chunk, kernel_seconds, conversion_seconds


class PetscTET4Assembler:
    """PETSc AIJ or block-BAIJ assembly for large TET4 models."""

    def __init__(
        self,
        chunk_size: int = 2048,
        matrix_format: str = "baij",
        telemetry: AssemblyTelemetry | None = None,
        rank_telemetry: Any | None = None,
        capture_diagnostics: bool = False,
    ) -> None:
        self.chunk_size = max(1, int(chunk_size))
        self.matrix_format = str(matrix_format).lower()
        if self.matrix_format not in {"aij", "baij"}:
            raise ValueError("PETSc matrix_format must be 'aij' or 'baij'.")
        self.telemetry = telemetry
        self.rank_telemetry = rank_telemetry
        self.capture_diagnostics = bool(capture_diagnostics)
        self.last_diagnostics: dict[str, Any] = {}

    def assemble(self, model: LargeModel) -> Any:
        petsc = _petsc()
        comm = petsc.COMM_WORLD
        if self.matrix_format == "baij":
            matrix = petsc.Mat().createBAIJ([model.ndof, model.ndof], bsize=3, nnz=40, comm=comm)
        else:
            matrix = petsc.Mat().createAIJ([model.ndof, model.ndof], nnz=120, comm=comm)
        matrix.setUp()
        matrix_info_after_setup = _safe_matrix_info(matrix) if self.capture_diagnostics else None
        row_start, row_stop = matrix.getOwnershipRange()
        materials = _material_cache(model)
        fixed = fixed_dof_indices(model).astype(petsc.IntType)
        fixed_mask = np.zeros(model.ndof, dtype=bool)
        fixed_mask[fixed] = True
        if _is_distributed_model(model):
            owned_start, owned_stop = 0, model.local_element_count
        else:
            owned_start, owned_stop = partition_range(model.element_count, comm.getRank(), comm.getSize())
        if self.telemetry is not None:
            self.telemetry.phase("MAT_ASSEMBLY")
        insertion_started = perf_counter()
        local_off_process_row_entries = 0
        for start in range(owned_start, owned_stop, self.chunk_size):
            stop = min(start + self.chunk_size, owned_stop)
            local_nodes = model.tet4[start:stop]
            global_nodes = model.global_tet4[start:stop] if _is_distributed_model(model) else local_nodes
            edofs = element_dofs_batch(global_nodes).astype(petsc.IntType)
            stiffness = _stiffness_batch(model, start, stop, materials)
            stiffness = apply_homogeneous_constraints_batch(stiffness, edofs, fixed_mask)
            blocked_values = petsc_block_values_batch(stiffness) if self.matrix_format == "baij" else None
            for local in range(stop - start):
                if self.matrix_format == "baij":
                    block_nodes = global_nodes[local].astype(petsc.IntType)
                    matrix.setValuesBlocked(
                        block_nodes,
                        block_nodes,
                        blocked_values[local],
                        addv=petsc.InsertMode.ADD_VALUES,
                    )
                else:
                    matrix.setValues(edofs[local], edofs[local], stiffness[local], addv=petsc.InsertMode.ADD_VALUES)
            if self.capture_diagnostics:
                owned_rows = (edofs >= row_start) & (edofs < row_stop)
                local_off_process_row_entries += int(np.count_nonzero(~owned_rows)) * 12
            if self.telemetry is not None:
                self.telemetry.checkpoint(stop - owned_start, elements_total=model.element_count)
        insertion_seconds = perf_counter() - insertion_started
        self._marker(
            "POST_INSERTION",
            phase="MAT_ASSEMBLY",
            context={"local_elements": int(owned_stop - owned_start)},
        )

        self._marker("PRE_ASSEMBLE_1", phase="MAT_ASSEMBLY")
        assemble_1_started = perf_counter()
        matrix.assemble()
        assemble_1_seconds = perf_counter() - assemble_1_started
        matrix_info_after_assemble_1 = _safe_matrix_info(matrix) if self.capture_diagnostics else None
        self._marker("POST_ASSEMBLE_1", phase="MAT_ASSEMBLY")

        owned_fixed = fixed[(fixed >= row_start) & (fixed < row_stop)]
        self._marker("PRE_CONSTRAINTS", phase="MAT_ASSEMBLY", context={"owned_fixed_dofs": int(owned_fixed.size)})
        constraints_started = perf_counter()
        for dof in owned_fixed:
            matrix.setValue(int(dof), int(dof), 1.0, addv=petsc.InsertMode.INSERT_VALUES)
        constraints_seconds = perf_counter() - constraints_started
        self._marker("POST_CONSTRAINTS", phase="MAT_ASSEMBLY", context={"owned_fixed_dofs": int(owned_fixed.size)})

        self._marker("PRE_ASSEMBLE_2", phase="MAT_ASSEMBLY")
        assemble_2_started = perf_counter()
        matrix.assemble()
        assemble_2_seconds = perf_counter() - assemble_2_started
        matrix_info_after_assemble_2 = _safe_matrix_info(matrix) if self.capture_diagnostics else None
        self._marker("POST_ASSEMBLE_2", phase="MAT_ASSEMBLY")
        if self.matrix_format == "baij":
            matrix.convert(petsc.Mat.Type.AIJ)
        if self.capture_diagnostics:
            local_elements = int(owned_stop - owned_start)
            self.last_diagnostics = {
                "matrix_format": self.matrix_format,
                "preallocation": {
                    "strategy": "uniform_nnz_per_row",
                    "requested_nnz_per_row": 120 if self.matrix_format == "aij" else 40,
                    "diag_offdiag_preallocation": "NOT_EXPLICIT",
                    "matrix_info_after_setup": matrix_info_after_setup,
                    "matrix_info_after_assemble_1": matrix_info_after_assemble_1,
                    "matrix_info_after_assemble_2": matrix_info_after_assemble_2,
                },
                "insertions": {
                    "local_elements": local_elements,
                    "matsetvalues_call_count": local_elements,
                    "scalar_values_submitted": local_elements * 12 * 12,
                    "off_process_row_entries_estimate": int(local_off_process_row_entries),
                    "local_row_entries_estimate": int(local_elements * 12 * 12 - local_off_process_row_entries),
                },
                "ownership_range": [int(row_start), int(row_stop)],
                "phase_timing_seconds": {
                    "element_insertion": insertion_seconds,
                    "assemble_1": assemble_1_seconds,
                    "constraints": constraints_seconds,
                    "assemble_2": assemble_2_seconds,
                    "total_assembler": insertion_seconds + assemble_1_seconds + constraints_seconds + assemble_2_seconds,
                },
            }
        return matrix

    def _marker(self, name: str, *, phase: str, context: dict[str, Any] | None = None) -> None:
        """Emit optional rank-local telemetry without affecting assembly."""
        if self.rank_telemetry is None:
            return
        try:
            self.rank_telemetry.marker(name, phase=phase, context=context)
        except Exception:
            # The telemetry implementation is fail-safe; retain the same property
            # when a caller supplies a compatible external marker sink.
            return


class PetscTET4MassAssembler:
    """Assemble the consistent translational mass matrix in PETSc chunks."""

    def __init__(self, chunk_size: int = 2048, matrix_format: str = "baij") -> None:
        self.chunk_size = max(1, int(chunk_size))
        self.matrix_format = str(matrix_format).lower()
        if self.matrix_format not in {"aij", "baij"}:
            raise ValueError("PETSc matrix_format must be 'aij' or 'baij'.")

    def assemble(self, model: LargeModel) -> Any:
        petsc = _petsc()
        comm = petsc.COMM_WORLD
        if self.matrix_format == "baij":
            matrix = petsc.Mat().createBAIJ([model.ndof, model.ndof], bsize=3, nnz=40, comm=comm)
        else:
            matrix = petsc.Mat().createAIJ([model.ndof, model.ndof], nnz=120, comm=comm)
        matrix.setUp()
        materials = _material_cache(model)
        fixed = fixed_dof_indices(model).astype(petsc.IntType)
        fixed_mask = np.zeros(model.ndof, dtype=bool)
        fixed_mask[fixed] = True
        if _is_distributed_model(model):
            owned_start, owned_stop = 0, model.local_element_count
        else:
            owned_start, owned_stop = partition_range(model.element_count, comm.getRank(), comm.getSize())
        for start in range(owned_start, owned_stop, self.chunk_size):
            stop = min(start + self.chunk_size, owned_stop)
            local_nodes = model.tet4[start:stop]
            global_nodes = model.global_tet4[start:stop] if _is_distributed_model(model) else local_nodes
            edofs = element_dofs_batch(global_nodes).astype(petsc.IntType)
            mass = _mass_batch(model, start, stop, materials)
            mass = apply_homogeneous_constraints_batch(mass, edofs, fixed_mask)
            blocked_values = petsc_block_values_batch(mass) if self.matrix_format == "baij" else None
            for local in range(stop - start):
                if self.matrix_format == "baij":
                    block_nodes = global_nodes[local].astype(petsc.IntType)
                    matrix.setValuesBlocked(
                        block_nodes,
                        block_nodes,
                        blocked_values[local],
                        addv=petsc.InsertMode.ADD_VALUES,
                    )
                else:
                    matrix.setValues(edofs[local], edofs[local], mass[local], addv=petsc.InsertMode.ADD_VALUES)
        matrix.assemble()
        row_start, row_stop = matrix.getOwnershipRange()
        for dof in fixed[(fixed >= row_start) & (fixed < row_stop)]:
            matrix.setValue(int(dof), int(dof), 1.0, addv=petsc.InsertMode.INSERT_VALUES)
        matrix.assemble()
        if self.matrix_format == "baij":
            matrix.convert(petsc.Mat.Type.AIJ)
        return matrix


def assemble_loads(model: LargeModel) -> np.ndarray:
    loads = np.zeros(model.ndof, dtype=float)
    indices = dof_index(model.load_nodes, model.load_components)
    np.add.at(loads, indices, model.load_values)
    return loads


def fixed_dof_indices(model: LargeModel) -> np.ndarray:
    if model.fixed_nodes.size == 0:
        return np.zeros(0, dtype=np.int64)
    return np.unique(dof_index(model.fixed_nodes, model.fixed_components).astype(np.int64))


def element_dofs(nodes: np.ndarray) -> np.ndarray:
    base = 3 * np.asarray(nodes, dtype=np.int64)
    return (base[:, None] + np.arange(3, dtype=np.int64)).ravel()


def partition_range(count: int, rank: int, size: int) -> tuple[int, int]:
    """Return a deterministic contiguous ownership interval."""
    if count < 0:
        raise ValueError("partition count must be non-negative")
    if size <= 0 or rank < 0 or rank >= size:
        raise ValueError("partition rank and size are inconsistent")
    return count * rank // size, count * (rank + 1) // size


def apply_homogeneous_element_constraints(
    stiffness: np.ndarray,
    element_dof_indices: np.ndarray,
    fixed_dofs: set[int],
) -> np.ndarray:
    """Zero constrained element rows and columns before distributed assembly."""
    constrained = [local for local, dof in enumerate(element_dof_indices) if int(dof) in fixed_dofs]
    if not constrained:
        return stiffness
    constrained_stiffness = stiffness.copy()
    constrained_stiffness[constrained, :] = 0.0
    constrained_stiffness[:, constrained] = 0.0
    return constrained_stiffness


def _material_cache(model: LargeModel) -> dict[int, SolidConstitutiveMaterial]:
    cache: dict[int, SolidConstitutiveMaterial] = {}
    for index, name in enumerate(model.material_names):
        data = model.materials[name]
        cache[index] = create_large_material(data)
    return cache


def _stiffness_batch(
    model: LargeModel,
    start: int,
    stop: int,
    materials: dict[int, SolidConstitutiveMaterial],
) -> np.ndarray:
    coordinates = model.nodes[model.tet4[start:stop]]
    material_ids = model.material_ids[start:stop]
    stiffness = np.empty((stop - start, 12, 12), dtype=float)
    for material_id in np.unique(material_ids):
        selected = material_ids == material_id
        stiffness[selected] = tet4_stiffness_batch(
            coordinates[selected],
            materials[int(material_id)].elasticity_matrix,
        )
    return stiffness


def _mass_batch(
    model: LargeModel,
    start: int,
    stop: int,
    materials: dict[int, SolidConstitutiveMaterial],
) -> np.ndarray:
    coordinates = model.nodes[model.tet4[start:stop]]
    material_ids = model.material_ids[start:stop]
    density = np.empty(stop - start, dtype=float)
    for material_id in np.unique(material_ids):
        selected = material_ids == material_id
        density[selected] = float(materials[int(material_id)].density)
    return tet4_mass_batch(coordinates, density)


def _safe_matrix_info(matrix: Any) -> dict[str, Any]:
    """Return best-effort PETSc allocation diagnostics after a shared phase."""
    try:
        info = matrix.getInfo()
    except Exception as exc:
        return {"available": False, "error_type": type(exc).__name__, "error_message": str(exc)}
    try:
        return {"available": True, "values": {str(key): float(value) for key, value in dict(info).items()}}
    except (TypeError, ValueError) as exc:
        return {"available": False, "error_type": type(exc).__name__, "error_message": str(exc)}


def _petsc() -> Any:
    try:
        from petsc4py import PETSc
    except ImportError as exc:
        raise InfrastructureError("PETSc large-model backend requires optional dependency petsc4py.") from exc
    return PETSc


def _is_distributed_model(model: object) -> bool:
    return hasattr(model, "global_tet4") and hasattr(model, "local_element_count")
