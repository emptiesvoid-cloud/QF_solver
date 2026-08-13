"""Deterministic shell director frames and constraint compatibility."""

from __future__ import annotations

import numpy as np


def director_frame(e3: np.ndarray) -> np.ndarray:
    """Return a deterministic orthonormal frame whose third axis is ``e3``."""
    normal = np.asarray(e3, dtype=float)
    normal /= np.linalg.norm(normal)
    seed = np.array([1.0, 0.0, 0.0]) if abs(float(normal[0])) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = seed - float(seed @ normal) * normal
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(normal, e1)
    e2 /= np.linalg.norm(e2)
    return np.vstack((e1, e2, normal))


def rotation_subspace_is_invariant(
    frame: np.ndarray,
    fixed_flags: list[bool] | tuple[bool, bool, bool],
    *,
    tolerance: float = 1.0e-12,
) -> bool:
    """Check that fixed and free global rotations do not mix in ``frame``."""
    fixed = [index for index, value in enumerate(fixed_flags) if value]
    free = [index for index, value in enumerate(fixed_flags) if not value]
    if not fixed or not free:
        return True
    values = np.asarray(frame, dtype=float)
    coupling = max(
        float(np.max(np.abs(values[np.ix_(free, fixed)]), initial=0.0)),
        float(np.max(np.abs(values[np.ix_(fixed, free)]), initial=0.0)),
    )
    return coupling <= tolerance
