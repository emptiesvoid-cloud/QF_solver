"""Small shared helpers for 3D solid finite elements."""

from __future__ import annotations

import numpy as np


def validate_coords_shape(coords: np.ndarray, shape: tuple[int, int], element_name: str) -> np.ndarray:
    """Return coordinates as float array and validate the expected element shape."""
    values = np.asarray(coords, dtype=float)
    if values.shape != shape:
        raise ValueError(f"{element_name} coordinates must have shape {shape}.")
    return values


def strain_displacement_from_gradients(gradients: np.ndarray) -> np.ndarray:
    """Build the 3D Voigt strain-displacement matrix from shape gradients."""
    values = np.asarray(gradients, dtype=float)
    b = np.zeros((6, values.shape[0] * 3), dtype=float)
    for i, (gx, gy, gz) in enumerate(values):
        c = 3 * i
        b[0, c + 0] = gx
        b[1, c + 1] = gy
        b[2, c + 2] = gz
        b[3, c + 0] = gy
        b[3, c + 1] = gx
        b[4, c + 1] = gz
        b[4, c + 2] = gy
        b[5, c + 0] = gz
        b[5, c + 2] = gx
    return b


def symmetrize(matrix: np.ndarray) -> np.ndarray:
    """Return the symmetric part used for conservative element tangents."""
    return 0.5 * (matrix + matrix.T)


def von_mises_3d(stress: np.ndarray) -> float:
    """Return the 3D von Mises equivalent stress for Voigt stress ordering."""
    sx, sy, sz, txy, tyz, txz = np.asarray(stress, dtype=float)
    value = 0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2)
    value += 3.0 * (txy**2 + tyz**2 + txz**2)
    return float(np.sqrt(max(value, 0.0)))
