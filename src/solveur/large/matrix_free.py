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
        "preconditioner": "diagonal",
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
        self.diagonal = self._build_diagonal()
        self.memory_bytes = int(
            sum(template.nbytes for template in self.templates) + self.diagonal.nbytes + self.free.nbytes
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
        indices = np.arange(self.model.element_count, dtype=np.int64)
        for local_index, template in enumerate(self.templates):
            selected = indices[local_index::6]
            for start in range(0, selected.size, self.chunk_size):
                element_ids = selected[start : start + self.chunk_size]
                nodes = self.model.tet4[element_ids]
                local_u = u_nodes[nodes].reshape((-1, 12))
                local_f = local_u @ template.T
                np.add.at(y_nodes, nodes, local_f.reshape((-1, 4, 3)))
        return y_nodes.ravel()

    def preconditioner(self) -> LinearOperator:
        inverse = np.divide(1.0, self.diagonal[self.free], out=np.ones(self.free.size), where=self.diagonal[self.free] > 0.0)
        return LinearOperator(
            shape=(self.free.size, self.free.size),
            matvec=lambda vector: inverse * vector,
            dtype=float,
        )

    def _build_diagonal(self) -> np.ndarray:
        diagonal_nodes = np.zeros((self.model.node_count, 3), dtype=float)
        indices = np.arange(self.model.element_count, dtype=np.int64)
        for local_index, template in enumerate(self.templates):
            local_diag = np.diag(template).reshape((4, 3))
            selected = indices[local_index::6]
            for start in range(0, selected.size, self.chunk_size):
                nodes = self.model.tet4[selected[start : start + self.chunk_size]]
                tiled = np.broadcast_to(local_diag, (nodes.shape[0], 4, 3))
                np.add.at(diagonal_nodes, nodes, tiled)
        return diagonal_nodes.ravel()


def _element_templates(model: LargeModel) -> tuple[np.ndarray, ...]:
    material = _single_material(model)
    element = Tet4Element(material)
    return tuple(element.stiffness(model.nodes[model.tet4[index]]) for index in range(6))


def _single_material(model: LargeModel) -> SolidConstitutiveMaterial:
    if len(model.material_names) != 1 or np.any(model.material_ids != 0):
        raise ValueError("Matrix-free backend supports one homogeneous material in v1.")
    data = model.materials[model.material_names[0]]
    return create_large_material(data)


def _validate_structured_model(model: LargeModel) -> None:
    metadata = dict(model.analysis.get("large_model", {}))
    if metadata.get("kind") != "structured_tet4_block":
        raise ValueError("Matrix-free backend supports generated structured_tet4_block models only.")
    expected = 6 * int(metadata["nx"]) * int(metadata["ny"]) * int(metadata["nz"])
    if model.element_count != expected:
        raise ValueError(f"Structured block metadata expects {expected} TET4 elements, got {model.element_count}.")
    if model.element_count < 6:
        raise ValueError("Structured matrix-free backend requires at least one full 6-TET cell.")
