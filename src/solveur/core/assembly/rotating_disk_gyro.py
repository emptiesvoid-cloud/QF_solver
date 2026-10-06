"""Unit-speed gyroscopic matrix assembly for centered rigid disks."""

from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.linalg import norm as sparse_norm

from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.elements.discrete import RotatingDisk


class RotatingDiskGyroAssembler:
    """Assemble G only; prescribed spin speed is deliberately not an input."""

    def assemble(self, model: FiniteElementModel, dofs: DofManager) -> csr_matrix:
        rows: list[int] = []
        columns: list[int] = []
        values: list[float] = []
        for entity in model.concentrated_masses:
            if not isinstance(entity, RotatingDisk):
                raise InputValidationError(
                    f"Rotating gyroscopic assembly received unsupported entity {type(entity).__name__}."
                )
            indices = dofs.node_indices(entity.node, ("RX", "RY", "RZ"))
            block = entity.gyroscopic_matrix()[3:, 3:]
            for local_row, global_row in enumerate(indices):
                for local_column, global_column in enumerate(indices):
                    value = float(block[local_row, local_column])
                    if value != 0.0:
                        rows.append(global_row)
                        columns.append(global_column)
                        values.append(value)
        matrix = coo_matrix((values, (rows, columns)), shape=(dofs.ndof, dofs.ndof), dtype=float).tocsr()
        matrix.sum_duplicates()
        matrix.eliminate_zeros()
        if matrix.data.size and not np.all(np.isfinite(matrix.data)):
            raise InputValidationError("Assembled unit-speed gyroscopic matrix contains non-finite values.")
        denominator = max(float(sparse_norm(matrix)), np.finfo(float).tiny)
        skew_error = float(sparse_norm(matrix + matrix.T)) / denominator
        if not np.isfinite(skew_error) or skew_error > 1.0e-12:
            raise InputValidationError(
                "Assembled unit-speed gyroscopic matrix is not skew-symmetric within the frozen 1e-12 gate; "
                f"relative error={skew_error:.6e}."
            )
        return matrix
