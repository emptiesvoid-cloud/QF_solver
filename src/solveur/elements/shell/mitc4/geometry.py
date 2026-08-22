"""Geometry and DOF helpers."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from .constants import DOF_PER_NODE


def node_dofs(node: int) -> np.ndarray:
    start = int(node) * DOF_PER_NODE
    return np.arange(start, start + DOF_PER_NODE, dtype=int)


def element_dofs(connectivity: Sequence[int]) -> np.ndarray:
    return np.concatenate([node_dofs(int(node)) for node in connectivity])


def rotation_matrix_xyz(ax: float, ay: float, az: float) -> np.ndarray:
    cx, sx = math.cos(ax), math.sin(ax)
    cy, sy = math.cos(ay), math.sin(ay)
    cz, sz = math.cos(az), math.sin(az)
    rx = np.array([[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]])
    ry = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]])
    rz = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]])
    return rz @ ry @ rx


def block_rotation_transform(Q: np.ndarray, node_count: int) -> np.ndarray:
    T6 = np.zeros((6, 6), dtype=float)
    T6[:3, :3] = Q
    T6[3:, 3:] = Q
    return np.kron(np.eye(node_count), T6)


def polygon_area_xy(coords_2d: np.ndarray) -> float:
    x = coords_2d[:, 0]
    y = coords_2d[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))

