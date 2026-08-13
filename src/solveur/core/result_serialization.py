"""Shared serialization helpers for solver result DTOs."""

from __future__ import annotations

from typing import Any

import numpy as np

from solveur.core.dofs import DofManager

LEGACY_MITC4_DOFS = ("UX", "UY", "UZ", "RX", "RY", "RZ")


def nodal_state(dofs: DofManager, values: np.ndarray) -> list[dict[str, Any]]:
    """Serialize one real-valued vector by node and dof name."""
    rows: list[dict[str, Any]] = []
    for node, names in sorted(dofs.node_dofs.items()):
        rows.append({"node": node, "dofs": {name: float(values[dofs.index(node, name)]) for name in names}})
    return rows


def modal_shape(dofs: DofManager, modes: np.ndarray, mode_index: int) -> list[dict[str, Any]]:
    """Serialize one modal column by node and dof name."""
    return nodal_state(dofs, modes[:, mode_index])


def complex_nodal_state(dofs: DofManager, values: np.ndarray) -> list[dict[str, Any]]:
    """Serialize one complex-valued vector by node and dof name."""
    rows: list[dict[str, Any]] = []
    for node, names in sorted(dofs.node_dofs.items()):
        dof_values: dict[str, Any] = {}
        for name in names:
            value = values[dofs.index(node, name)]
            dof_values[name] = {
                "real": float(np.real(value)),
                "imag": float(np.imag(value)),
                "amplitude": float(abs(value)),
                "phase_degrees": float(np.degrees(np.angle(value))),
            }
        rows.append({"node": node, "dofs": dof_values})
    return rows


def legacy_six_dof_vector(dofs: DofManager, values: np.ndarray, node_count: int) -> np.ndarray:
    """Return the legacy six-dof-per-node vector expected by MITC4 plotting."""
    vector = np.zeros(node_count * len(LEGACY_MITC4_DOFS), dtype=float)
    for node, names in dofs.node_dofs.items():
        for local, name in enumerate(LEGACY_MITC4_DOFS):
            if name in names:
                vector[node * len(LEGACY_MITC4_DOFS) + local] = values[dofs.index(node, name)]
    return vector
