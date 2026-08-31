"""Matrix-free solver for generated structured TET4 blocks."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.sparse.linalg import LinearOperator, cg

from solveur.core.errors import MeshValidationError, NumericalConvergenceError

from solveur.elements.solid.tet4 import Tet4Element
from solveur.large.assembler import assemble_loads, fixed_dof_indices
from solveur.large.materials import create_large_material
from solveur.large.model import LargeModel
from solveur.materials.solid import SolidConstitutiveMaterial


@dataclass(frozen=True)
class MatrixFreeResult:
    """Solution and solver diagnostics for matrix-free CG."""

    displacement: np.ndarray
    solver_info: dict[str, Any]
    solve_time_seconds: float
    operator_memory_bytes: int


def solve_structured_matrix_free(
    model: LargeModel,
    *,
    chunk_size: int = 8192,
    rtol: float = 1.0e-8,
    atol: float = 0.0,
    maxiter: int = 10000,
) -> MatrixFreeResult:
    """Solve a generated structured block without assembling the global stiffness matrix."""
    _validate_structured_model(model)
    loads = assemble_loads(model)
    fixed = fixed_dof_indices(model)
    free = np.setdiff1d(np.arange(model.ndof, dtype=np.int64), fixed)
    if free.size == 0:
        raise MeshValidationError("No free degree of freedom remains after boundary conditions.")
    operator = StructuredBlockOperator(model, free=free, chunk_size=chunk_size)
    rhs = loads[free]
    iterations = 0

    def callback(_: np.ndarray) -> None:
        nonlocal iterations
        iterations += 1

    solve_start = time.perf_counter()
    solution, info = cg(operator, rhs, M=operator.preconditioner(), rtol=rtol, atol=atol, maxiter=maxiter, callback=callback)
    solve_time = time.perf_counter() - solve_start
    residual = float(np.linalg.norm(rhs - operator @ solution))
    rhs_norm = float(np.linalg.norm(rhs))
    converged = int(info) == 0
    if not converged:
        raise NumericalConvergenceError(f"Matrix-free CG did not converge; info={info}, residual={residual:.6e}.")
    displacement = np.zeros(model.ndof, dtype=float)
    displacement[free] = solution
    solver_info = {
        "method": "matrix_free_cg",
        "preconditioner": "nodal_block_jacobi",
        "iterations": iterations,
        "residual_norm": residual,
        "relative_residual": residual / max(rhs_norm, 1.0),
        "converged": True,
    }
    return MatrixFreeResult(
        displacement=displacement,
        solver_info=solver_info,
        solve_time_seconds=solve_time,
        operator_memory_bytes=operator.memory_bytes,
    )


class StructuredBlockOperator(LinearOperator):
    """Free-dof linear operator for a generated structured TET4 block."""

    def __init__(self, model: LargeModel, *, free: np.ndarray, chunk_size: int = 8192) -> None:
        self.model = model
        self.free = np.asarray(free, dtype=np.int64)
        self.chunk_size = max(1, int(chunk_size))
        self.templates = _element_templates(model)
        self.element_ids_by_template = tuple(
            np.arange(local_index, model.element_count, len(self.templates), dtype=np.int64)
            for local_index in range(len(self.templates))
        )
        # Preserve the historical template/element order while avoiding a
        # repeated advanced-indexing gather in every matrix-vector product.
        self.nodes_by_template = tuple(
            model.tet4[element_ids] for element_ids in self.element_ids_by_template
        )
        self.flat_dofs_by_template = tuple(
            _flat_element_dofs(nodes) for nodes in self.nodes_by_template
        )
        self.diagonal = self._build_diagonal()
        self.block_inverse = self._build_block_inverse()
        self.memory_bytes = int(
            sum(template.nbytes for template in self.templates)
            + sum(nodes.nbytes for nodes in self.nodes_by_template)
            + sum(flat_dofs.nbytes for flat_dofs in self.flat_dofs_by_template)
            + self.diagonal.nbytes
            + self.block_inverse.nbytes
            + self.free.nbytes
        )
        super().__init__(dtype=float, shape=(self.free.size, self.free.size))

    def _matvec(self, vector: np.ndarray) -> np.ndarray:
        full = np.zeros(self.model.ndof, dtype=float)
        full[self.free] = vector
        internal = self.apply_full(full)
        return internal[self.free]

    def apply_full(self, displacement: np.ndarray) -> np.ndarray:
        u_nodes = displacement.reshape((self.model.node_count, 3))
        y_nodes = np.zeros_like(u_nodes)
        for template, nodes_by_template, flat_dofs_by_template in zip(
            self.templates, self.nodes_by_template, self.flat_dofs_by_template, strict=True
        ):
            for start in range(0, nodes_by_template.shape[0], self.chunk_size):
                stop = start + self.chunk_size
                nodes = nodes_by_template[start:stop]
                flat_dofs = flat_dofs_by_template[start * 12 : stop * 12]
                local_u = u_nodes[nodes].reshape((-1, 12))
                local_f = local_u @ template.T
                _accumulate_node_values(y_nodes, nodes, local_f.reshape((-1, 4, 3)), flat_dofs=flat_dofs)
        return y_nodes.ravel()

    def preconditioner(self) -> LinearOperator:
        def apply(vector: np.ndarray) -> np.ndarray:
            full = np.zeros(self.model.ndof, dtype=float)
            full[self.free] = vector
            values = full.reshape((self.model.node_count, 3))
            corrected = np.einsum("nij,nj->ni", self.block_inverse, values, optimize=True)
            return corrected.ravel()[self.free]

        return LinearOperator(
            shape=(self.free.size, self.free.size),
            matvec=apply,
            dtype=float,
        )

    def _build_diagonal(self) -> np.ndarray:
        diagonal_nodes = np.zeros((self.model.node_count, 3), dtype=float)
        for template, nodes_by_template, flat_dofs_by_template in zip(
            self.templates, self.nodes_by_template, self.flat_dofs_by_template, strict=True
        ):
            local_diag = np.diag(template).reshape((4, 3))
            for start in range(0, nodes_by_template.shape[0], self.chunk_size):
                stop = start + self.chunk_size
                nodes = nodes_by_template[start:stop]
                flat_dofs = flat_dofs_by_template[start * 12 : stop * 12]
                tiled = np.broadcast_to(local_diag, (nodes.shape[0], 4, 3))
                _accumulate_node_values(diagonal_nodes, nodes, tiled, flat_dofs=flat_dofs)
        return diagonal_nodes.ravel()

    def _build_block_inverse(self) -> np.ndarray:
        """Build a 3-by-3 nodal block-Jacobi inverse for faster CG convergence."""
        blocks = np.zeros((self.model.node_count, 3, 3), dtype=float)
        for template, nodes_by_template in zip(self.templates, self.nodes_by_template, strict=True):
            for local_node in range(4):
                node_block = template[3 * local_node : 3 * local_node + 3, 3 * local_node : 3 * local_node + 3]
                for row in range(3):
                    for column in range(3):
                        blocks[:, row, column] += np.bincount(
                            nodes_by_template[:, local_node],
                            weights=np.full(nodes_by_template.shape[0], node_block[row, column]),
                            minlength=self.model.node_count,
                        )
        try:
            return np.linalg.inv(blocks)
        except np.linalg.LinAlgError:
            inverse = np.zeros_like(blocks)
            for index, block in enumerate(blocks):
                inverse[index] = np.linalg.pinv(block, rcond=1.0e-12)
            return inverse


def _flat_element_dofs(nodes: np.ndarray) -> np.ndarray:
    components = np.arange(3, dtype=nodes.dtype)
    return (nodes[:, :, None] * 3 + components).reshape(-1)


def _accumulate_node_values(
    target: np.ndarray,
    nodes: np.ndarray,
    values: np.ndarray,
    *,
    flat_dofs: np.ndarray | None = None,
) -> None:
    """Accumulate all three components in one vectorized scatter operation."""
    if nodes.ndim != 2 or nodes.shape[1] != 4 or values.shape != (nodes.shape[0], 4, 3):
        raise ValueError("Structured TET4 accumulation expects nodes (n, 4) and values (n, 4, 3).")
    if flat_dofs is None:
        flat_dofs = _flat_element_dofs(nodes)
    target.ravel()[:] += np.bincount(
        flat_dofs,
        weights=values.reshape(-1),
        minlength=target.size,
    )


def _element_templates(model: LargeModel) -> tuple[np.ndarray, ...]:
    material = _single_material(model)
    element = Tet4Element(material)
    count = int(model.analysis.get("large_model", {}).get("tetrahedra_per_cell", 6))
    return tuple(element.stiffness(model.nodes[model.tet4[index]]) for index in range(count))


def _single_material(model: LargeModel) -> SolidConstitutiveMaterial:
    if len(model.material_names) != 1 or np.any(model.material_ids != 0):
        raise ValueError("Matrix-free backend supports one homogeneous material in v1.")
    data = model.materials[model.material_names[0]]
    return create_large_material(data)


def _validate_structured_model(model: LargeModel) -> None:
    metadata = dict(model.analysis.get("large_model", {}))
    if metadata.get("kind") != "structured_tet4_block":
        raise ValueError("Matrix-free backend supports generated structured_tet4_block models only.")
    tetrahedra_per_cell = int(metadata.get("tetrahedra_per_cell", 6))
    if tetrahedra_per_cell not in {6, 12}:
        raise ValueError("Structured block metadata supports six or twelve TET4 per cell.")
    expected = tetrahedra_per_cell * int(metadata["nx"]) * int(metadata["ny"]) * int(metadata["nz"])
    if model.element_count != expected:
        raise ValueError(f"Structured block metadata expects {expected} TET4 elements, got {model.element_count}.")
    if model.element_count < 6:
        raise ValueError("Structured matrix-free backend requires at least one full 6-TET cell.")
