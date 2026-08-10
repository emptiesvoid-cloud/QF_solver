"""Static condensation helpers for the two internal MITC3+ rotations."""

from __future__ import annotations

import numpy as np


def condensation_transform(stiffness: np.ndarray, retained: int = 18) -> np.ndarray:
    """Return the Guyan transform from retained to complete element DOFs."""
    matrix = np.asarray(stiffness, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("Condensation requires a square stiffness matrix.")
    if retained <= 0 or retained >= matrix.shape[0]:
        raise ValueError("retained must split retained and internal DOFs.")
    kaa = matrix[retained:, retained:]
    kaq = matrix[retained:, :retained]
    scale = max(float(np.linalg.norm(matrix, ord=np.inf)), 1.0)
    if np.linalg.cond(kaa) > 1.0e14:
        raise ValueError("MITC3+ internal rotation stiffness is ill-conditioned.")
    try:
        recovery = -np.linalg.solve(kaa, kaq)
    except np.linalg.LinAlgError as exc:
        raise ValueError("MITC3+ internal rotation stiffness is singular.") from exc
    transform = np.vstack((np.eye(retained), recovery))
    residual = kaa @ recovery + kaq
    if float(np.linalg.norm(residual, ord=np.inf)) > 1.0e-10 * scale:
        raise ValueError("MITC3+ internal rotation condensation residual is too large.")
    return transform


def condense_matrix(matrix: np.ndarray, transform: np.ndarray) -> np.ndarray:
    """Project an element matrix through a previously computed transform."""
    result = np.asarray(transform, dtype=float).T @ np.asarray(matrix, dtype=float) @ transform
    return 0.5 * (result + result.T)


def recover_internal(retained_values: np.ndarray, transform: np.ndarray) -> np.ndarray:
    """Recover the two internal bubble rotations from retained element DOFs."""
    retained = np.asarray(retained_values)
    mapping = np.asarray(transform)
    if retained.ndim != 1 or retained.shape[0] != mapping.shape[1]:
        raise ValueError("Retained MITC3+ vector is incompatible with the condensation transform.")
    return mapping[mapping.shape[1] :, :] @ retained
