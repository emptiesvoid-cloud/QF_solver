"""Pure helpers shared by the bounded WP08 mixed-modal runner."""

from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment


def canonical_modes(modes: np.ndarray) -> np.ndarray:
    """Canonicalize eigenvector signs without changing mode ordering."""

    values = np.asarray(modes, dtype=float).copy()
    for index in range(values.shape[1]):
        pivot = int(np.argmax(np.abs(values[:, index])))
        if values[pivot, index] < 0.0:
            values[:, index] *= -1.0
    return values


def shared_node_mode_mac(coarse: dict[str, object], fine: dict[str, object]) -> float:
    """Compare shared coarse/fine nodes with global assignment and MAC."""

    coarse_model = coarse["_model"]
    fine_model = fine["_model"]
    coarse_result = coarse["_result"]
    fine_result = fine["_result"]
    fine_coordinates = {
        tuple(np.round(point, decimals=12)): index
        for index, point in enumerate(fine_model.nodes)
    }
    pairs = []
    for coarse_index, point in enumerate(coarse_model.nodes):
        fine_index = fine_coordinates.get(tuple(np.round(point, decimals=12)))
        if fine_index is not None:
            pairs.append((coarse_index, fine_index))
    coarse_dofs = coarse_model.dof_manager()
    fine_dofs = fine_model.dof_manager()
    count = min(coarse_result.modes.shape[1], fine_result.modes.shape[1])
    coarse_values = []
    fine_values = []
    for coarse_node, fine_node in pairs:
        for name in ("UX", "UY", "UZ"):
            coarse_values.append(coarse_result.modes[coarse_dofs.index(coarse_node, name), :count])
            fine_values.append(fine_result.modes[fine_dofs.index(fine_node, name), :count])
    if not coarse_values:
        return 0.0
    coarse_matrix = canonical_modes(np.asarray(coarse_values, dtype=float))
    fine_matrix = canonical_modes(np.asarray(fine_values, dtype=float))
    dot = coarse_matrix.T @ fine_matrix
    denominator = np.maximum(
        np.sum(coarse_matrix * coarse_matrix, axis=0)[:, None]
        * np.sum(fine_matrix * fine_matrix, axis=0)[None, :],
        1.0e-300,
    )
    mac = np.square(dot) / denominator
    rows, columns = linear_sum_assignment(-mac)
    return float(min((mac[row, column] for row, column in zip(rows, columns, strict=True)), default=0.0))


__all__ = ["canonical_modes", "shared_node_mode_mac"]
