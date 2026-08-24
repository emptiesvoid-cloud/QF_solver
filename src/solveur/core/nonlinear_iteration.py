"""Newton iteration helpers shared by nonlinear drivers."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from solveur.core.dofs import DofManager
from solveur.core.errors import NumericalConvergenceError
from solveur.core.material_state import MaterialStateTable
from solveur.core.nonlinear_contracts import NonlinearFailureReason
from solveur.core.model import FiniteElementModel
from scipy.sparse import csr_matrix


def line_search_factor(
    assemble: Callable[..., tuple[np.ndarray, object, MaterialStateTable]],
    model: FiniteElementModel,
    dofs: DofManager,
    displacement: np.ndarray,
    free: np.ndarray,
    target_load: np.ndarray,
    material_states: MaterialStateTable,
    increment: np.ndarray,
    residual_norm: float,
    min_alpha: float,
    max_reductions: int,
    armijo: float,
) -> tuple[float, int]:
    """Find an Armijo factor while keeping trial assembly delegated to the driver."""
    alpha = 1.0
    for reductions in range(max_reductions + 1):
        trial = displacement.copy()
        trial[free] += alpha * increment
        trial_internal, _, _ = assemble(model, dofs, trial, material_states)
        trial_norm = float(np.linalg.norm((target_load - trial_internal)[free]))
        if trial_norm <= (1.0 - armijo * alpha) * residual_norm:
            return alpha, reductions
        alpha *= 0.5
        if alpha < min_alpha:
            break
    raise NumericalConvergenceError(
        "Newton line-search failed to reduce the residual.",
        reason=NonlinearFailureReason.LINE_SEARCH_FAILURE,
    )


def solve_arc_length_correction(
    tangent: csr_matrix,
    reference_load: np.ndarray,
    residual: np.ndarray,
    delta_u_step: np.ndarray,
    delta_lambda: float,
    constraint: float,
    load_scale: float,
) -> tuple[np.ndarray, float]:
    """Solve the small augmented correction system for arc-length continuation."""
    size = residual.size
    matrix = np.zeros((size + 1, size + 1), dtype=float)
    matrix[:size, :size] = tangent.toarray()
    matrix[:size, size] = -reference_load
    matrix[size, :size] = 2.0 * delta_u_step
    matrix[size, size] = 2.0 * load_scale**2 * delta_lambda
    rhs = np.zeros(size + 1, dtype=float)
    rhs[:size] = residual
    rhs[size] = -constraint
    try:
        solution = np.linalg.solve(matrix, rhs)
    except np.linalg.LinAlgError as exc:
        raise NumericalConvergenceError("Arc-length augmented system is singular.") from exc
    if not np.all(np.isfinite(solution)):
        raise NumericalConvergenceError("Arc-length correction produced non-finite values.")
    return solution[:size], float(solution[size])
