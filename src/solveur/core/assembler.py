"""Sparse global stiffness assembly."""

from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from time import perf_counter
import warnings

from solveur.core.assembly_plan import AssemblyElementPlan, AssemblyPlan
from solveur.core.dofs import DOF_ORDER, DofManager
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.core.sparse_accumulator import SparseCsrAccumulator
from solveur.elements.registry import ElementRegistry
from solveur.loads.integration import DistributedLoadIntegrator, load_balance
from solveur.materials.factory import MaterialFactory


class GlobalAssembler:
    """Assemble sparse stiffness matrices and load vectors."""

    def __init__(self, chunk_size: int = 256) -> None:
        if chunk_size <= 0:
            raise ValueError("Assembly chunk_size must be positive.")
        self.chunk_size = int(chunk_size)
        self.last_diagnostics: dict[str, object] = {}
        self.last_load_diagnostics: dict[str, object] = {}
        self.last_load_vectors: list[np.ndarray] = []
        self.last_load_vector = np.zeros(0, dtype=float)

    def assemble_stiffness(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        *,
        plan: AssemblyPlan | None = None,
    ) -> csr_matrix:
        return self._assemble_matrix(model, dofs, "stiffness", plan=plan)

    def assemble_mass(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        *,
        plan: AssemblyPlan | None = None,
    ) -> csr_matrix:
        return self._assemble_matrix(model, dofs, "mass", plan=plan)

    def assemble_stiffness_and_mass(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        *,
        plan: AssemblyPlan | None = None,
    ) -> tuple[csr_matrix, csr_matrix, dict[str, object], dict[str, object]]:
        """Assemble K and M together while reusing each chunk's sparse motif.

        The local element matrices remain separate and are never cached. Only
        the DDL mapping and the temporary row/column buffers are shared; this
        keeps the optimization valid for geometry-, orientation- and
        state-dependent materials without retaining a global dense-like
        assembly pattern.
        """
        chunk_size = self._configured_chunk_size(model)
        plan_reused = plan is not None
        if plan is None:
            plan = self.prepare_plan(model, dofs)
        elif not plan.matches(model, dofs, chunk_size=chunk_size):
            raise InputValidationError("Assembly plan does not match the supplied model and DDL map.")
        planned_peak_entries = self._planned_peak_entries(plan, chunk_size)
        memory_estimate, memory_budget, budget_exceeded = self._assembly_memory_policy(
            model,
            planned_peak_entries,
            matrix_count=2,
            index_bytes=int(_assembly_index_dtype(dofs.ndof).itemsize),
        )
        stiffness_accumulator = SparseCsrAccumulator((dofs.ndof, dofs.ndof))
        mass_accumulator = SparseCsrAccumulator((dofs.ndof, dofs.ndof))
        material_cache: dict[str, object] = {}
        element_cache: dict[tuple[str, str], object] = {}
        total_entries = 0
        peak_chunk_entries = 0
        chunk_count = 0
        element_kernel_seconds = 0.0
        sparse_conversion_seconds = 0.0
        chunk_fusion_seconds = 0.0
        for start in range(0, len(plan.elements), chunk_size):
            entries = plan.elements[start : start + chunk_size]
            stiffness_chunk, mass_chunk, entry_count, kernel_seconds, conversion_seconds = (
                self._matrix_chunk_pair(
                    model,
                    dofs,
                    entries,
                    material_cache=material_cache,
                    element_cache=element_cache,
                )
            )
            element_kernel_seconds += kernel_seconds
            sparse_conversion_seconds += conversion_seconds
            fusion_started = perf_counter()
            stiffness_accumulator.add(stiffness_chunk)
            mass_accumulator.add(mass_chunk)
            chunk_fusion_seconds += perf_counter() - fusion_started
            total_entries += entry_count
            peak_chunk_entries = max(peak_chunk_entries, entry_count)
            chunk_count += 1
        finalize_started = perf_counter()
        stiffness = stiffness_accumulator.finalize()
        mass = mass_accumulator.finalize()
        sparse_finalize_seconds = perf_counter() - finalize_started
        discrete_started = perf_counter()
        discrete_stiffness = self._discrete_matrix(model, dofs, "stiffness")
        discrete_mass = self._discrete_matrix(model, dofs, "mass")
        if discrete_stiffness.nnz:
            stiffness = (stiffness + discrete_stiffness).tocsr()
        if discrete_mass.nnz:
            mass = (mass + discrete_mass).tocsr()
        for matrix in (stiffness, mass):
            matrix.sum_duplicates()
            matrix.eliminate_zeros()
        discrete_seconds = perf_counter() - discrete_started
        common = {
            "chunk_size": chunk_size,
            "chunk_count": chunk_count,
            "element_count": len(model.elements),
            "coefficient_entry_count": total_entries,
            "peak_chunk_entry_count": peak_chunk_entries,
            "assembly_peak_memory_estimate_bytes": memory_estimate,
            "assembly_memory_budget_bytes": memory_budget,
            "assembly_memory_budget_exceeded": budget_exceeded,
            "assembly_index_dtype": _assembly_index_dtype(dofs.ndof).name,
            "assembly_plan_reused": plan_reused,
            "paired_assembly": True,
            "shared_chunk_pattern": True,
            "assembly_phase_seconds": {
                "assembly_plan": 0.0 if plan_reused else plan.build_seconds,
                "element_kernel": element_kernel_seconds,
                "chunk_sparse_conversion": sparse_conversion_seconds,
                "chunk_fusion": chunk_fusion_seconds,
                "sparse_finalize": sparse_finalize_seconds,
                "discrete_merge": discrete_seconds,
            },
        }
        stiffness_diagnostics = {
            **common,
            "matrix": "stiffness",
            "accumulator_chunk_count": stiffness_accumulator.chunk_count,
            "accumulator_occupied_levels": stiffness_accumulator.occupied_levels,
            "final_nnz": int(stiffness.nnz),
            "spring_count": len(model.springs),
            "concentrated_mass_count": len(model.concentrated_masses),
        }
        mass_diagnostics = {
            **common,
            "matrix": "mass",
            "accumulator_chunk_count": mass_accumulator.chunk_count,
            "accumulator_occupied_levels": mass_accumulator.occupied_levels,
            "final_nnz": int(mass.nnz),
            "spring_count": len(model.springs),
            "concentrated_mass_count": len(model.concentrated_masses),
        }
        self.last_diagnostics = mass_diagnostics
        return stiffness, mass, stiffness_diagnostics, mass_diagnostics

    def prepare_plan(self, model: FiniteElementModel, dofs: DofManager) -> AssemblyPlan:
        """Build reusable element and DDL metadata for one model instance."""
        started = perf_counter()
        plan = AssemblyPlan.build(model, dofs, chunk_size=self._configured_chunk_size(model))
        return AssemblyPlan(
            model_token=plan.model_token,
            node_count=plan.node_count,
            ndof=plan.ndof,
            dof_signature=plan.dof_signature,
            elements=plan.elements,
            chunk_size=plan.chunk_size,
            fingerprint=plan.fingerprint,
            build_seconds=perf_counter() - started,
        )

    def assemble_loads(self, model: FiniteElementModel, dofs: DofManager) -> np.ndarray:
        total, _ = self._assemble_load_data(model, dofs, keep_vectors=False)
        return total

    def assemble_load_vectors(self, model: FiniteElementModel, dofs: DofManager) -> list[np.ndarray]:
        """Return individually integrated vectors in stable nodal/distributed order."""
        _, vectors = self._assemble_load_data(model, dofs, keep_vectors=True)
        return vectors

    def _assemble_load_data(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        *,
        keep_vectors: bool,
    ) -> tuple[np.ndarray, list[np.ndarray]]:
        vectors: list[np.ndarray] = []
        details: list[dict[str, object]] = []
        total = np.zeros(dofs.ndof, dtype=float)
        for index, load in enumerate(model.loads):
            vector = np.zeros(dofs.ndof, dtype=float)
            vector[dofs.index(load.node, load.dof)] = load.value
            resultant, moment = load_balance(model, dofs, vector)
            total += vector
            if keep_vectors:
                vectors.append(vector)
            details.append(
                {
                    "index": index,
                    "type": "nodal",
                    "node": load.node,
                    "dof": load.dof,
                    "resultant": resultant.tolist(),
                    "moment_about_origin": moment.tolist(),
                    "vector_norm": float(np.linalg.norm(vector)),
                    "nonzero_dof_count": int(abs(load.value) > 1.0e-30),
                }
            )
        integrator = DistributedLoadIntegrator()
        for offset, load in enumerate(model.distributed_loads, start=len(model.loads)):
            integrated = integrator.integrate_sparse(model, dofs, load, offset)
            total[integrated.indices] += integrated.values
            if keep_vectors:
                vector = np.zeros(dofs.ndof, dtype=float)
                vector[integrated.indices] = integrated.values
                vectors.append(vector)
            details.append(integrated.details)
        resultant, moment = load_balance(model, dofs, total)
        self.last_load_vector = total.copy()
        self.last_load_vectors = [vector.copy() for vector in vectors] if keep_vectors else []
        self.last_load_diagnostics = {
            "nodal_load_count": len(model.loads),
            "distributed_load_count": len(model.distributed_loads),
            "load_vector_count": len(vectors),
            "resultant": resultant.tolist(),
            "moment_about_origin": moment.tolist(),
            "contributions": details,
        }
        return total, vectors

    def fixed_indices(self, model: FiniteElementModel, dofs: DofManager) -> np.ndarray:
        fixed: set[int] = set()
        for condition in model.fixed_dofs:
            for dof in condition.dofs:
                fixed.add(dofs.index(condition.node, dof))
        return np.array(sorted(fixed), dtype=int)

    @staticmethod
    def ground_spring_internal_force(model: FiniteElementModel, dofs: DofManager, displacement: np.ndarray) -> np.ndarray:
        """Return the assembled internal force carried by springs connected to ground."""
        force = np.zeros(dofs.ndof, dtype=float)
        for spring in model.springs:
            if spring.node_b is not None:
                continue
            names = spring.active_dofs()
            components = [DOF_ORDER.index(name) for name in names]
            matrix = spring.nodal_stiffness()[np.ix_(components, components)]
            indices = dofs.node_indices(spring.node_a, names)
            force[indices] += matrix @ np.asarray(displacement, dtype=float)[indices]
        return force

    def _assemble_matrix(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        matrix_name: str,
        *,
        plan: AssemblyPlan | None,
    ) -> csr_matrix:
        chunk_size = self._configured_chunk_size(model)
        plan_reused = plan is not None
        if plan is None:
            plan = self.prepare_plan(model, dofs)
        elif not plan.matches(model, dofs, chunk_size=chunk_size):
            raise InputValidationError("Assembly plan does not match the supplied model and DDL map.")
        planned_peak_entries = self._planned_peak_entries(plan, chunk_size)
        memory_estimate, memory_budget, budget_exceeded = self._assembly_memory_policy(
            model,
            planned_peak_entries,
            matrix_count=1,
            index_bytes=int(_assembly_index_dtype(dofs.ndof).itemsize),
        )
        accumulator = SparseCsrAccumulator((dofs.ndof, dofs.ndof))
        material_cache: dict[str, object] = {}
        element_cache: dict[tuple[str, str], object] = {}
        total_entries = 0
        peak_chunk_entries = 0
        chunk_count = 0
        element_kernel_seconds = 0.0
        sparse_conversion_seconds = 0.0
        chunk_fusion_seconds = 0.0
        for start in range(0, len(plan.elements), chunk_size):
            definitions = plan.elements[start : start + chunk_size]
            chunk, entry_count, kernel_seconds, conversion_seconds = self._matrix_chunk(
                model,
                dofs,
                definitions,
                matrix_name,
                material_cache=material_cache,
                element_cache=element_cache,
            )
            element_kernel_seconds += kernel_seconds
            sparse_conversion_seconds += conversion_seconds
            fusion_started = perf_counter()
            accumulator.add(chunk)
            chunk_fusion_seconds += perf_counter() - fusion_started
            total_entries += entry_count
            peak_chunk_entries = max(peak_chunk_entries, entry_count)
            chunk_count += 1
        finalize_started = perf_counter()
        matrix = accumulator.finalize()
        sparse_finalize_seconds = perf_counter() - finalize_started
        discrete_started = perf_counter()
        discrete = self._discrete_matrix(model, dofs, matrix_name)
        if discrete.nnz:
            matrix = (matrix + discrete).tocsr()
        matrix.sum_duplicates()
        matrix.eliminate_zeros()
        discrete_seconds = perf_counter() - discrete_started
        self.last_diagnostics = {
            "matrix": matrix_name,
            "chunk_size": chunk_size,
            "chunk_count": chunk_count,
            "element_count": len(model.elements),
            "coefficient_entry_count": total_entries,
            "peak_chunk_entry_count": peak_chunk_entries,
            "assembly_peak_memory_estimate_bytes": memory_estimate,
            "assembly_memory_budget_bytes": memory_budget,
            "assembly_memory_budget_exceeded": budget_exceeded,
            "assembly_index_dtype": _assembly_index_dtype(dofs.ndof).name,
            "accumulator_chunk_count": accumulator.chunk_count,
            "accumulator_occupied_levels": accumulator.occupied_levels,
            "assembly_plan_reused": plan_reused,
            "assembly_phase_seconds": {
                "assembly_plan": 0.0 if plan_reused else plan.build_seconds,
                "element_kernel": element_kernel_seconds,
                "chunk_sparse_conversion": sparse_conversion_seconds,
                "chunk_fusion": chunk_fusion_seconds,
                "sparse_finalize": sparse_finalize_seconds,
                "discrete_merge": discrete_seconds,
            },
            "final_nnz": int(matrix.nnz),
            "spring_count": len(model.springs),
            "concentrated_mass_count": len(model.concentrated_masses),
        }
        return matrix

    @staticmethod
    def _discrete_matrix(
        model: FiniteElementModel,
        dofs: DofManager,
        matrix_name: str,
    ) -> csr_matrix:
        rows: list[int] = []
        cols: list[int] = []
        values: list[float] = []
        if matrix_name == "stiffness":
            for spring in model.springs:
                names = spring.active_dofs()
                components = [DOF_ORDER.index(name) for name in names]
                nodal = spring.nodal_stiffness()[np.ix_(components, components)]
                node_a = dofs.node_indices(spring.node_a, names)
                _append_dense_block(rows, cols, values, node_a, node_a, nodal)
                if spring.node_b is not None:
                    node_b = dofs.node_indices(spring.node_b, names)
                    _append_dense_block(rows, cols, values, node_b, node_b, nodal)
                    _append_dense_block(rows, cols, values, node_a, node_b, -nodal)
                    _append_dense_block(rows, cols, values, node_b, node_a, -nodal)
        elif matrix_name == "mass":
            for mass in model.concentrated_masses:
                names = mass.active_dofs()
                indices = dofs.node_indices(mass.node, names)
                _append_dense_block(rows, cols, values, indices, indices, mass.matrix())
        if not values:
            return csr_matrix((dofs.ndof, dofs.ndof), dtype=float)
        result = coo_matrix((values, (rows, cols)), shape=(dofs.ndof, dofs.ndof)).tocsr()
        result.sum_duplicates()
        result.eliminate_zeros()
        return result

    def _matrix_chunk(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        definitions: list[AssemblyElementPlan],
        matrix_name: str,
        *,
        material_cache: dict[str, object],
        element_cache: dict[tuple[str, str], object],
    ) -> tuple[csr_matrix, int, float, float]:
        entry_count = sum(definition.entry_count for definition in definitions)
        index_dtype = _assembly_index_dtype(dofs.ndof)
        rows = np.empty(entry_count, dtype=index_dtype)
        cols = np.empty(entry_count, dtype=index_dtype)
        values = np.empty(entry_count, dtype=float)
        offset = 0
        kernel_started = perf_counter()
        for entry in definitions:
            definition = entry.definition
            spec = entry.spec
            coords = entry.coordinates
            material_data = model.materials[definition.material]
            cacheable_material = "orientation_field" not in material_data
            if cacheable_material:
                material = material_cache.get(definition.material)
                if material is None:
                    material = MaterialFactory.create(material_data, coordinates=coords)
                    material_cache[definition.material] = material
            else:
                material = MaterialFactory.create(material_data, coordinates=coords)
            element_key = (str(definition.type), str(definition.material))
            if cacheable_material:
                element = element_cache.get(element_key)
                if element is None:
                    element = spec.factory(material)
                    element_cache[element_key] = element
            else:
                element = spec.factory(material)
            if matrix_name == "mass" and not hasattr(element, "mass"):
                raise InputValidationError(f"Element {definition.type} does not provide a mass matrix.")
            local = element.stiffness(coords) if matrix_name == "stiffness" else element.mass(coords)
            edofs = entry.global_dofs
            local_size = edofs.size
            next_offset = offset + local_size**2
            rows[offset:next_offset] = np.repeat(edofs, local_size)
            cols[offset:next_offset] = np.tile(edofs, local_size)
            values[offset:next_offset] = np.asarray(local, dtype=float).reshape(-1)
            offset = next_offset
        kernel_seconds = perf_counter() - kernel_started
        conversion_started = perf_counter()
        chunk = coo_matrix((values, (rows, cols)), shape=(dofs.ndof, dofs.ndof)).tocsr()
        chunk.sum_duplicates()
        conversion_seconds = perf_counter() - conversion_started
        return chunk, entry_count, kernel_seconds, conversion_seconds

    def _matrix_chunk_pair(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        definitions: tuple[AssemblyElementPlan, ...],
        *,
        material_cache: dict[str, object],
        element_cache: dict[tuple[str, str], object],
    ) -> tuple[csr_matrix, csr_matrix, int, float, float]:
        """Build stiffness and mass chunks with one row/column motif."""
        entry_count = sum(entry.entry_count for entry in definitions)
        index_dtype = _assembly_index_dtype(dofs.ndof)
        rows = np.empty(entry_count, dtype=index_dtype)
        cols = np.empty(entry_count, dtype=index_dtype)
        stiffness_values = np.empty(entry_count, dtype=float)
        mass_values = np.empty(entry_count, dtype=float)
        offset = 0
        kernel_started = perf_counter()
        for entry in definitions:
            definition = entry.definition
            spec = entry.spec
            coords = entry.coordinates
            material_data = model.materials[definition.material]
            cacheable_material = "orientation_field" not in material_data
            if cacheable_material:
                material = material_cache.get(definition.material)
                if material is None:
                    material = MaterialFactory.create(material_data, coordinates=coords)
                    material_cache[definition.material] = material
            else:
                material = MaterialFactory.create(material_data, coordinates=coords)
            element_key = (str(definition.type), str(definition.material))
            if cacheable_material:
                element = element_cache.get(element_key)
                if element is None:
                    element = spec.factory(material)
                    element_cache[element_key] = element
            else:
                element = spec.factory(material)
            if not hasattr(element, "mass"):
                raise InputValidationError(f"Element {definition.type} does not provide a mass matrix.")
            local_stiffness = np.asarray(element.stiffness(coords), dtype=float)
            local_mass = np.asarray(element.mass(coords), dtype=float)
            edofs = entry.global_dofs
            local_size = edofs.size
            next_offset = offset + local_size**2
            rows[offset:next_offset] = np.repeat(edofs, local_size)
            cols[offset:next_offset] = np.tile(edofs, local_size)
            stiffness_values[offset:next_offset] = local_stiffness.reshape(-1)
            mass_values[offset:next_offset] = local_mass.reshape(-1)
            offset = next_offset
        kernel_seconds = perf_counter() - kernel_started
        conversion_started = perf_counter()
        shape = (dofs.ndof, dofs.ndof)
        stiffness = coo_matrix((stiffness_values, (rows, cols)), shape=shape).tocsr()
        mass = coo_matrix((mass_values, (rows, cols)), shape=shape).tocsr()
        stiffness.sum_duplicates()
        mass.sum_duplicates()
        conversion_seconds = perf_counter() - conversion_started
        return stiffness, mass, entry_count, kernel_seconds, conversion_seconds

    def _configured_chunk_size(self, model: FiniteElementModel) -> int:
        raw = model.analysis.parameters.get("assembly_chunk_size", self.chunk_size)
        try:
            chunk_size = int(raw)
        except (TypeError, ValueError) as exc:
            raise InputValidationError("assembly_chunk_size must be a positive integer.") from exc
        if chunk_size <= 0:
            raise InputValidationError("assembly_chunk_size must be a positive integer.")
        return chunk_size

    @staticmethod
    def _planned_peak_entries(plan: AssemblyPlan, chunk_size: int) -> int:
        """Estimate the largest temporary COO chunk before allocating it."""
        return max(
            (
                sum(entry.entry_count for entry in plan.elements[start : start + chunk_size])
                for start in range(0, len(plan.elements), chunk_size)
            ),
            default=0,
        )

    @staticmethod
    def _assembly_memory_policy(
        model: FiniteElementModel,
        peak_entries: int,
        *,
        matrix_count: int,
        index_bytes: int,
    ) -> tuple[int, int | None, bool]:
        """Estimate chunk allocation and enforce an optional user budget."""
        if matrix_count <= 0:
            raise ValueError("matrix_count must be positive")
        if index_bytes not in {4, 8}:
            raise ValueError("assembly index storage must use 4 or 8 bytes")
        # COO indices, values and conversion workspaces are deliberately
        # estimated conservatively; this is a guard, not a platform profiler.
        estimate = int(peak_entries * (2 * index_bytes + 8 * matrix_count) * 2)
        raw_budget = model.analysis.parameters.get("assembly_memory_budget_mb")
        budget = None
        if raw_budget is not None:
            try:
                budget = int(float(raw_budget) * 1024**2)
            except (TypeError, ValueError) as exc:
                raise InputValidationError("assembly_memory_budget_mb must be positive.") from exc
            if budget <= 0:
                raise InputValidationError("assembly_memory_budget_mb must be positive.")
        exceeded = budget is not None and estimate > budget
        if exceeded:
            message = (
                "Estimated sparse assembly chunk memory exceeds assembly_memory_budget_mb: "
                f"estimated={estimate / 1024**2:.1f} MiB, budget={budget / 1024**2:.1f} MiB."
            )
            if bool(model.analysis.parameters.get("enforce_assembly_memory_budget", False)):
                raise InputValidationError(message)
            warnings.warn(message, RuntimeWarning, stacklevel=3)
        return estimate, budget, exceeded

    @staticmethod
    def _local_entry_count(definition: object) -> int:
        spec = ElementRegistry.get(definition.type)
        local_dof_count = len(definition.nodes) * len(spec.dofs)
        return local_dof_count**2

    @staticmethod
    def _element_dofs(nodes: tuple[int, ...], names: tuple[str, ...], dofs: DofManager) -> list[int]:
        indices: list[int] = []
        for node in nodes:
            indices.extend(dofs.node_indices(int(node), names))
        return indices


def _append_dense_block(
    rows: list[int],
    cols: list[int],
    values: list[float],
    row_dofs: list[int],
    col_dofs: list[int],
    block: np.ndarray,
) -> None:
    row_count, col_count = block.shape
    if row_count != len(row_dofs) or col_count != len(col_dofs):
        raise InputValidationError("Discrete matrix block does not match its active degrees of freedom.")
    for local_row, global_row in enumerate(row_dofs):
        for local_col, global_col in enumerate(col_dofs):
            value = float(block[local_row, local_col])
            if value:
                rows.append(global_row)
                cols.append(global_col)
                values.append(value)


def _assembly_index_dtype(ndof: int) -> np.dtype:
    """Use compact COO indices while the global DDL range is int32-safe."""

    return np.dtype(np.int32 if ndof <= np.iinfo(np.int32).max else np.int64)
