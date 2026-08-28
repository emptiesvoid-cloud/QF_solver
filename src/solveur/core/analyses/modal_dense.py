"""Bounded dense helpers for modal analysis."""

from __future__ import annotations

import numpy as np
from scipy.linalg import eigh


def dense_generalized_eigh(
    stiffness: object,
    mass: object,
    mode_count: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Solve a bounded dense generalized eigenproblem after scaling."""
    dense_stiffness = np.asarray(stiffness.toarray(), dtype=float)
    dense_mass = np.asarray(mass.toarray(), dtype=float)
    mass_diagonal = np.maximum(np.abs(np.diag(dense_mass)), 1.0e-30)
    inverse_mass_scale = 1.0 / np.sqrt(mass_diagonal)
    dense_stiffness = inverse_mass_scale[:, None] * dense_stiffness * inverse_mass_scale[None, :]
    dense_mass = inverse_mass_scale[:, None] * dense_mass * inverse_mass_scale[None, :]
    stiffness_scale = max(float(np.max(np.abs(dense_stiffness), initial=0.0)), 1.0)
    mass_scale = max(float(np.max(np.abs(dense_mass), initial=0.0)), 1.0)
    values, vectors = eigh(dense_stiffness / stiffness_scale, dense_mass / mass_scale)
    values = values * stiffness_scale / mass_scale
    vectors = inverse_mass_scale[:, None] * vectors
    return values[:mode_count], vectors[:, :mode_count]
