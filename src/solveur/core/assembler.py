"""Sparse global stiffness assembly."""

from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix

from solveur.core.dofs import DOF_ORDER, DofManager
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.elements.registry import ElementRegistry
from solveur.loads.integration import DistributedLoadIntegrator, load_balance
from solveur.materials.factory import MaterialFactory


class GlobalAssembler:
    """Assemble sparse stiffness matrices and load vectors."""

    def __init__(self, chunk_size: int = 256) -> None:
        if chunk_size <= 0:
            raise ValueError("Assembly chunk_size must be positive.")
        self.chunk_size = int(chunk_size)
        self.last_diagnostics: dict[str, int | str] = {}
        self.last_load_diagnostics: dict[str, object] = {}
        self.last_load_vectors: list[np.ndarray] = []
        self.last_load_vector = np.zeros(0, dtype=float)

    def assemble_stiffness(self, model: FiniteElementModel, dofs: DofManager) -> csr_matrix:
        return self._assemble_matrix(model, dofs, "stiffness")

    def assemble_mass(self, model: FiniteElementModel, dofs: DofManager) -> csr_matrix:
        return self._assemble_matrix(model, dofs, "mass")

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

    def _assemble_matrix(self, model: FiniteElementModel, dofs: DofManager, matrix_name: str) -> csr_matrix:
        chunk_size = self._configured_chunk_size(model)
        accumulator = _CsrAccumulator((dofs.ndof, dofs.ndof))
        material_cache: dict[str, object] = {}
        element_cache: dict[tuple[str, str], object] = {}
        total_entries = 0
        peak_chunk_entries = 0
        chunk_count = 0
        for start in range(0, len(model.elements), chunk_size):
            definitions = model.elements[start : start + chunk_size]
            chunk, entry_count = self._matrix_chunk(
                model,
                dofs,
                definitions,
                matrix_name,
                material_cache=material_cache,
                element_cache=element_cache,
            )
            accumulator.add(chunk)
            total_entries += entry_count
            peak_chunk_entries = max(peak_chunk_entries, entry_count)
            chunk_count += 1
        matrix = accumulator.finalize()
        discrete = self._discrete_matrix(model, dofs, matrix_name)
        if discrete.nnz:
            matrix = (matrix + discrete).tocsr()
        matrix.sum_duplicates()
        matrix.eliminate_zeros()
        self.last_diagnostics = {
            "matrix": matrix_name,
            "chunk_size": chunk_size,
            "chunk_count": chunk_count,
            "element_count": len(model.elements),
            "coefficient_entry_count": total_entries,
            "peak_chunk_entry_count": peak_chunk_entries,
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
        definitions: list[object],
        matrix_name: str,
        *,
        material_cache: dict[str, object],
        element_cache: dict[tuple[str, str], object],
    ) -> tuple[csr_matrix, int]:
        entry_count = sum(self._local_entry_count(definition) for definition in definitions)
        rows = np.empty(entry_count, dtype=np.int64)
        cols = np.empty(entry_count, dtype=np.int64)
        values = np.empty(entry_count, dtype=float)
        offset = 0
        for definition in definitions:
            spec = ElementRegistry.get(definition.type)
            coords = model.nodes[list(definition.nodes)]
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
            edofs = np.asarray(self._element_dofs(definition.nodes, spec.dofs, dofs), dtype=np.int64)
            local_size = edofs.size
            next_offset = offset + local_size**2
            rows[offset:next_offset] = np.repeat(edofs, local_size)
            cols[offset:next_offset] = np.tile(edofs, local_size)
            values[offset:next_offset] = np.asarray(local, dtype=float).reshape(-1)
            offset = next_offset
        chunk = coo_matrix((values, (rows, cols)), shape=(dofs.ndof, dofs.ndof)).tocsr()
        chunk.sum_duplicates()
        return chunk, entry_count

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


class _CsrAccumulator:
    """Merge CSR chunks pairwise while keeping only logarithmically many blocks."""

    def __init__(self, shape: tuple[int, int]) -> None:
        self.shape = shape
        self.levels: list[csr_matrix | None] = []

    def add(self, matrix: csr_matrix) -> None:
        carry = matrix
        level = 0
        while level < len(self.levels) and self.levels[level] is not None:
            carry = (self.levels[level] + carry).tocsr()
            self.levels[level] = None
            level += 1
        if level == len(self.levels):
            self.levels.append(carry)
        else:
            self.levels[level] = carry

    def finalize(self) -> csr_matrix:
        result = csr_matrix(self.shape, dtype=float)
        for matrix in self.levels:
            if matrix is not None:
                result = (result + matrix).tocsr()
        return result


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
