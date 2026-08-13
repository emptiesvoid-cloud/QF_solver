"""Finite element model assembly and linear solve."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix, diags
from scipy.sparse.linalg import cg, spsolve

from mitc4.constants import DOF_PER_NODE
from mitc4.element import MITC4Element
from mitc4.geometry import element_dofs, node_dofs
from mitc4.material import ShellMaterial


@dataclass
class ShellModel:
    nodes: np.ndarray
    quads: np.ndarray
    material: ShellMaterial
    element_type: type[MITC4Element] = MITC4Element
    fixed_dofs: set[int] = field(default_factory=set)
    loads: np.ndarray | None = None

    def __post_init__(self) -> None:
        self.nodes = np.asarray(self.nodes, dtype=float)
        self.quads = np.asarray(self.quads, dtype=int)
        if self.nodes.ndim != 2 or self.nodes.shape[1] != 3:
            raise ValueError("nodes must have shape (n, 3).")
        if self.quads.ndim != 2 or self.quads.shape[1] != 4:
            raise ValueError("quads must have shape (m, 4).")
        if self.loads is None:
            self.loads = np.zeros(self.ndof, dtype=float)
        else:
            self.loads = np.asarray(self.loads, dtype=float)
            if self.loads.shape != (self.ndof,):
                raise ValueError(f"loads must have shape ({self.ndof},).")

    @property
    def ndof(self) -> int:
        return self.nodes.shape[0] * DOF_PER_NODE

    def create_element(self) -> MITC4Element:
        return self.element_type(self.material)

    def assemble_stiffness(self, *, chunk_size: int | None = None) -> csr_matrix:
        """Assemble stiffness, optionally bounding temporary assembly memory."""
        if chunk_size is not None:
            if chunk_size <= 0:
                raise ValueError("chunk_size must be positive.")
            return self._assemble_stiffness_chunked(int(chunk_size))
        element = self.create_element()
        rows: list[int] = []
        cols: list[int] = []
        vals: list[float] = []
        for conn in self.quads:
            Ke = element.stiffness(self.nodes[conn])
            dofs = element_dofs(conn)
            rr, cc = np.meshgrid(dofs, dofs, indexing="ij")
            rows.extend(rr.ravel().tolist())
            cols.extend(cc.ravel().tolist())
            vals.extend(Ke.ravel().tolist())
        return coo_matrix((vals, (rows, cols)), shape=(self.ndof, self.ndof)).tocsr()

    def _assemble_stiffness_chunked(self, chunk_size: int) -> csr_matrix:
        element = self.create_element()
        levels: list[csr_matrix | None] = []
        for start in range(0, len(self.quads), chunk_size):
            connectivity = self.quads[start : start + chunk_size]
            local_size = 4 * DOF_PER_NODE
            entries = len(connectivity) * local_size**2
            rows = np.empty(entries, dtype=np.int64)
            cols = np.empty(entries, dtype=np.int64)
            values = np.empty(entries, dtype=float)
            offset = 0
            for conn in connectivity:
                local = element.stiffness(self.nodes[conn])
                dofs = element_dofs(conn)
                next_offset = offset + local_size**2
                rows[offset:next_offset] = np.repeat(dofs, local_size)
                cols[offset:next_offset] = np.tile(dofs, local_size)
                values[offset:next_offset] = local.reshape(-1)
                offset = next_offset
            carry = coo_matrix((values, (rows, cols)), shape=(self.ndof, self.ndof)).tocsr()
            carry.sum_duplicates()
            level = 0
            while level < len(levels) and levels[level] is not None:
                carry = (levels[level] + carry).tocsr()
                levels[level] = None
                level += 1
            if level == len(levels):
                levels.append(carry)
            else:
                levels[level] = carry
        stiffness = csr_matrix((self.ndof, self.ndof), dtype=float)
        for block in levels:
            if block is not None:
                stiffness = (stiffness + block).tocsr()
        stiffness.sum_duplicates()
        stiffness.eliminate_zeros()
        return stiffness

    def add_nodal_load(self, node: int, dof: int, value: float) -> None:
        self.loads[int(node) * DOF_PER_NODE + int(dof)] += float(value)

    def add_fixed_dof(self, node: int, dof: int) -> None:
        self.fixed_dofs.add(int(node) * DOF_PER_NODE + int(dof))

    def fix_node(self, node: int, dofs: Iterable[int] | None = None) -> None:
        if dofs is None:
            self.fixed_dofs.update(node_dofs(int(node)).tolist())
        else:
            for dof in dofs:
                self.add_fixed_dof(int(node), int(dof))

    def solve(self) -> np.ndarray:
        K = self.assemble_stiffness()
        fixed = np.array(sorted(self.fixed_dofs), dtype=int)
        all_dofs = np.arange(self.ndof, dtype=int)
        free = np.setdiff1d(all_dofs, fixed)
        U = np.zeros(self.ndof, dtype=float)
        U[free] = spsolve(K[free, :][:, free], self.loads[free])
        if not np.all(np.isfinite(U)):
            raise RuntimeError("Linear solve produced non-finite displacements.")
        return U

    def solve_iterative(
        self,
        *,
        chunk_size: int = 128,
        relative_tolerance: float = 1.0e-8,
        maximum_iterations: int = 20000,
    ) -> tuple[np.ndarray, dict[str, float | int | str]]:
        """Solve a large, symmetric static shell system using scaled CG."""
        stiffness = self.assemble_stiffness(chunk_size=chunk_size)
        fixed = np.array(sorted(self.fixed_dofs), dtype=int)
        free = np.setdiff1d(np.arange(self.ndof, dtype=int), fixed)
        if free.size == 0:
            raise RuntimeError("No free degree of freedom remains after boundary conditions.")
        reduced = stiffness[free, :][:, free].tocsr()
        rhs = self.loads[free]
        diagonal_scale = 1.0 / np.sqrt(np.maximum(np.abs(reduced.diagonal()), 1.0e-30))
        scaling = diags(diagonal_scale, format="csr")
        scaled = (scaling @ reduced @ scaling).tocsr()
        iterations = 0

        def count_iterations(_: np.ndarray) -> None:
            nonlocal iterations
            iterations += 1

        solution_scaled, info = cg(
            scaled,
            diagonal_scale * rhs,
            rtol=relative_tolerance,
            atol=0.0,
            maxiter=maximum_iterations,
            callback=count_iterations,
        )
        solution = diagonal_scale * solution_scaled
        residual = reduced @ solution - rhs
        relative_residual = float(np.linalg.norm(residual) / max(np.linalg.norm(rhs), 1.0))
        physical_tolerance = 2.0 * relative_tolerance
        if info != 0 or not np.all(np.isfinite(solution)) or relative_residual > physical_tolerance:
            raise RuntimeError(
                "Scaled CG did not converge: "
                f"info={info}, iterations={iterations}, residual={relative_residual:.6e}."
            )
        displacement = np.zeros(self.ndof, dtype=float)
        displacement[free] = solution
        return displacement, {
            "method": "scaled_cg",
            "iterations": iterations,
            "relative_residual": relative_residual,
            "matrix_nnz": int(stiffness.nnz),
            "free_dofs": int(free.size),
            "assembly_chunk_size": chunk_size,
        }
