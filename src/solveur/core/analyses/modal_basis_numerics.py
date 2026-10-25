"""Numerical policy and validation helpers for WP04 modal bases."""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from typing import Any, cast

import numpy as np
from scipy.sparse import csr_matrix, diags, issparse
from scipy.sparse.linalg import ArpackNoConvergence, eigsh

from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.io.manifest import content_digest


SYMMETRY_TOL = 1.0e-12
SPD_MINIMUM_SCALED_EIGENVALUE = 1.0e-12
SPD_DENSE_MAX_DOFS = 256
SPD_EIGENSOLVER_TOL = 1.0e-10
SPD_EIGENSOLVER_MAXITER = 5000
SPD_RITZ_RESIDUAL_MAX = 1.0e-8
MODAL_RESIDUAL_MAX = 1.0e-8
MASS_ORTHOGONALITY_MAX = 1.0e-8
CLUSTER_RELATIVE_GAP = 1.0e-8
DEGENERATE_ROTATION_RELATIVE_SPAN = 1.0e-12
CLUSTER_ZETA_SPREAD_MAX = 1.0e-12
SUBSPACE_EQUIVALENCE_TOL = 1.0e-8
FLOAT_TINY: float = 2.2250738585072014e-308


def positive_definite_screen(matrix: csr_matrix, label: str) -> dict[str, object]:
    """Numerically screen SPD using diagonal congruence and bounded solvers."""
    diagonal = np.asarray(matrix.diagonal(), dtype=np.float64)
    if diagonal.size == 0 or not np.all(np.isfinite(diagonal)) or np.any(diagonal <= 0.0):
        raise InputValidationError(f"Prepared {label} matrix has a non-positive diagonal; SPD screen failed.")
    scale = diags(1.0 / np.sqrt(diagonal), format="csr")
    normalized = (scale @ matrix @ scale).tocsr()
    n = int(matrix.shape[0])
    if n <= SPD_DENSE_MAX_DOFS:
        dense = normalized.toarray()
        try:
            np.linalg.cholesky(dense)
            minimum = float(np.linalg.eigvalsh(dense)[0])
        except np.linalg.LinAlgError as exc:
            raise InputValidationError(f"Prepared {label} matrix failed the scaled dense Cholesky SPD screen.") from exc
        screen_method = "DIAGONALLY_SCALED_DENSE_CHOLESKY_AND_EIGVALSH"
        residual = 0.0
    else:
        try:
            smallest, vector = eigsh(
                normalized,
                k=1,
                which="SA",
                tol=SPD_EIGENSOLVER_TOL,
                maxiter=SPD_EIGENSOLVER_MAXITER,
            )
        except (ArpackNoConvergence, RuntimeError, ValueError) as exc:
            raise NumericalConvergenceError(
                f"Sparse smallest-eigenvalue SPD screen did not converge for prepared {label} matrix."
            ) from exc
        minimum = float(smallest[0])
        vector = np.asarray(vector[:, 0], dtype=np.float64)
        residual = float(np.linalg.norm(normalized @ vector - minimum * vector))
        screen_method = "DIAGONALLY_SCALED_SPARSE_SMALLEST_ALGEBRAIC_RITZ_SCREEN"
        if not math.isfinite(residual) or residual > SPD_RITZ_RESIDUAL_MAX:
            raise NumericalConvergenceError(
                f"Sparse smallest-eigenvalue Ritz residual for prepared {label} matrix is excessive: {residual:.3e}."
            )
    if not math.isfinite(minimum) or minimum <= SPD_MINIMUM_SCALED_EIGENVALUE:
        raise InputValidationError(
            f"Prepared {label} matrix is not numerically positive definite under the contracted scaled screen; "
            f"minimum estimate={minimum:.3e}, required>{SPD_MINIMUM_SCALED_EIGENVALUE:.3e}."
        )
    return {
        "method": screen_method,
        "minimum_scaled_eigenvalue_estimate": minimum,
        "ritz_residual": residual,
        "threshold": SPD_MINIMUM_SCALED_EIGENVALUE,
        "is_formal_proof": False,
        "interpretation": "Numerical method-domain screen; sparse Ritz estimate is not a formal proof of global SPD.",
    }


def mass_normalize_and_handle_degenerate_subspaces(
    vectors: np.ndarray,
    values: np.ndarray,
    mass: csr_matrix,
    clusters: tuple[tuple[int, ...], ...],
) -> np.ndarray:
    result = np.asarray(vectors, dtype=np.float64).copy()
    for index in range(result.shape[1]):
        norm_squared = float(result[:, index] @ (mass @ result[:, index]))
        if not math.isfinite(norm_squared) or norm_squared <= 0.0:
            raise NumericalConvergenceError("A modal vector has non-positive generalized mass.")
        result[:, index] /= math.sqrt(norm_squared)
    for cluster in clusters:
        if len(cluster) < 2:
            continue
        cluster_values = values[np.asarray(cluster, dtype=int)]
        relative_span = float(np.ptp(cluster_values)) / max(float(np.max(np.abs(cluster_values))), FLOAT_TINY)
        if relative_span > DEGENERATE_ROTATION_RELATIVE_SPAN:
            # Near-degenerate but distinct eigenvectors are not rotated. Their
            # mass orthogonality is checked below to preserve eigenpair meaning.
            continue
        indices = np.asarray(cluster, dtype=int)
        block = result[:, indices]
        gram = np.asarray(block.T @ (mass @ block), dtype=np.float64)
        eigenvalues, eigenvectors = np.linalg.eigh(0.5 * (gram + gram.T))
        if np.any(eigenvalues <= 0.0) or not np.all(np.isfinite(eigenvalues)):
            raise NumericalConvergenceError("A degenerate modal subspace has singular mass Gram matrix.")
        inverse_sqrt = (eigenvectors / np.sqrt(eigenvalues)[None, :]) @ eigenvectors.T
        result[:, indices] = block @ inverse_sqrt
    return result


def detect_clusters(values: np.ndarray) -> tuple[tuple[int, ...], ...]:
    if values.size == 0:
        return ()
    clusters: list[list[int]] = [[0]]
    for index in range(1, values.size):
        left = float(values[index - 1])
        right = float(values[index])
        gap = abs(right - left) / max(abs(left), abs(right), FLOAT_TINY)
        if gap <= CLUSTER_RELATIVE_GAP:
            clusters[-1].append(index)
        else:
            clusters.append([index])
    return tuple(tuple(cluster) for cluster in clusters)


def mass_metric_subspace_equivalent(
    left_modes: np.ndarray,
    right_modes: np.ndarray,
    left_values: np.ndarray,
    right_values: np.ndarray,
    mass: csr_matrix,
    *,
    tolerance: float,
) -> bool:
    if left_modes.shape != right_modes.shape or left_values.shape != right_values.shape:
        return False
    if left_modes.shape[1] == 0:
        return False
    spectral_scale = np.maximum(np.maximum(np.abs(left_values), np.abs(right_values)), FLOAT_TINY)
    if np.any(np.abs(left_values - right_values) / spectral_scale > tolerance):
        return False
    cross_gram = left_modes.T @ (mass @ right_modes)
    singular_values = np.linalg.svd(cross_gram, compute_uv=False)
    return bool(
        np.all(np.isfinite(singular_values)) and np.max(np.abs(singular_values - 1.0), initial=0.0) <= tolerance
    )


def relative_modal_residual(k_matrix: csr_matrix, m_matrix: csr_matrix, value: float, vector: np.ndarray) -> float:
    kv = np.asarray(k_matrix @ vector, dtype=np.float64)
    mv = np.asarray(m_matrix @ vector, dtype=np.float64)
    residual = kv - value * mv
    denominator = float(np.linalg.norm(kv) + abs(value) * np.linalg.norm(mv))
    if denominator <= FLOAT_TINY:
        raise NumericalConvergenceError("Modal residual has a zero normalization denominator.")
    return float(np.linalg.norm(residual) / denominator)


def relative_sparse_symmetry_error(matrix: csr_matrix) -> float:
    return sparse_symmetry_metrics(matrix)[0]


def sparse_symmetry_metrics(matrix: csr_matrix) -> tuple[float, bool]:
    """Return relative symmetry error and exact stored symmetry from one diff."""
    difference = csr_matrix(matrix - matrix.T)
    difference.eliminate_zeros()
    denominator = max(sparse_frobenius_norm(matrix), FLOAT_TINY)
    error = sparse_frobenius_norm(difference) / denominator
    return error, difference.nnz == 0


def is_exactly_sparse_symmetric(matrix: csr_matrix) -> bool:
    """Return whether a sparse matrix equals its transpose at stored precision."""
    return sparse_symmetry_metrics(matrix)[1]


def project_exact_symmetric_bilinear(
    matrix: csr_matrix,
    modes: np.ndarray,
    *,
    exact_symmetry_validated: bool = False,
) -> np.ndarray:
    """Evaluate ``modes.T @ matrix @ modes`` using exact input symmetry.

    A single sparse-dense product forms ``matrix @ modes``. Each reduced
    upper-triangle entry is then evaluated as its own bilinear form, and the
    corresponding symmetric entry is assigned from that same scalar. This
    uses the identity implied by exactly symmetric input; it neither averages
    a completed projection nor modifies the input operator.
    """
    require_sparse_finite_square(matrix, "stiffness")
    vectors = np.asarray(modes, dtype=np.float64)
    if vectors.ndim != 2 or vectors.shape[0] != matrix.shape[0] or vectors.shape[1] == 0:
        raise InputValidationError("Symmetric bilinear projection modes have incompatible dimensions.")
    if not np.all(np.isfinite(vectors)):
        raise InputValidationError("Symmetric bilinear projection modes must be finite.")
    if not exact_symmetry_validated and not is_exactly_sparse_symmetric(matrix):
        raise InputValidationError("Symmetric bilinear projection requires exactly symmetric stored stiffness.")

    mode_count = vectors.shape[1]
    operator_modes = np.asarray(matrix @ vectors, dtype=np.float64)
    projected = np.zeros((mode_count, mode_count), dtype=np.float64)
    for i in range(mode_count):
        for j in range(i, mode_count):
            value = float(np.dot(vectors[:, i], operator_modes[:, j]))
            if not math.isfinite(value):
                raise NumericalConvergenceError("Symmetric bilinear projection produced non-finite values.")
            projected[i, j] = value
            projected[j, i] = value
    return projected


def sparse_frobenius_norm(matrix: csr_matrix) -> float:
    return float(np.sqrt(np.sum(np.square(matrix.data, dtype=np.float64))))


def require_sparse_finite_square(matrix: object, label: str) -> None:
    if not issparse(matrix):
        raise InputValidationError(f"Prepared {label} operator must remain sparse.")
    sparse_matrix = cast(csr_matrix, matrix)
    shape = cast(tuple[int, ...], sparse_matrix.shape)
    if len(shape) != 2 or shape[0] != shape[1] or shape[0] == 0:
        raise InputValidationError(f"Prepared {label} operator must be non-empty and square.")
    if np.iscomplexobj(sparse_matrix.data) or not np.all(np.isfinite(sparse_matrix.data)):
        raise InputValidationError(f"Prepared {label} operator must contain finite real coefficients.")


def require_small_symmetric(matrix: np.ndarray, label: str) -> None:
    error = float(np.linalg.norm(matrix - matrix.T, ord="fro")) / max(
        float(np.linalg.norm(matrix, ord="fro")), FLOAT_TINY
    )
    if not math.isfinite(error) or error > SYMMETRY_TOL:
        raise NumericalConvergenceError(f"{label} symmetry error {error:.3e} exceeds {SYMMETRY_TOL:.3e}.")


def validate_projected_damping(matrix: np.ndarray) -> None:
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or not np.all(np.isfinite(matrix)):
        raise InputValidationError("Projected damping matrix must be finite and square.")
    require_small_symmetric(matrix, "projected damping")


def modal_zeta_values(zeta: float | Sequence[float] | np.ndarray, mode_count: int) -> np.ndarray:
    if isinstance(zeta, (bool, complex, np.complexfloating)):
        raise InputValidationError("Modal damping ratio zeta must be finite, real and non-negative.")
    try:
        raw_values = np.asarray(zeta)
        if np.iscomplexobj(raw_values) or raw_values.dtype.kind == "b":
            raise InputValidationError("Modal damping ratios must be real and cannot be boolean.")
        values = np.asarray(raw_values, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise InputValidationError("Modal damping ratios must be finite real values.") from exc
    if values.ndim == 0:
        values = np.full(mode_count, float(values), dtype=np.float64)
    if values.shape != (mode_count,) or not np.all(np.isfinite(values)) or np.any(values < 0.0):
        raise InputValidationError(f"Modal damping ratios must be non-negative finite scalar or shape ({mode_count},).")
    return values


def finite_vector(value: object, size: int, label: str) -> np.ndarray:
    try:
        raw = np.asarray(value)
        if raw.shape != (size,):
            raise InputValidationError(f"{label} must have shape ({size},).")
        result = np.asarray(raw, dtype=np.complex128 if np.iscomplexobj(raw) else np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise InputValidationError(f"{label} must contain finite numeric values.") from exc
    if not np.all(np.isfinite(result)):
        raise InputValidationError(f"{label} must contain finite numeric values.")
    return result


def validate_positive_int(value: object, label: str) -> int:
    if not isinstance(value, (int, np.integer)) or isinstance(value, (bool, np.bool_)) or int(value) <= 0:
        raise InputValidationError(f"{label} must be a positive integer.")
    return int(value)


def finite_nonnegative(value: object, label: str) -> float:
    if isinstance(value, (bool, complex, np.complexfloating)):
        raise InputValidationError(f"{label} must be a finite non-negative real number.")
    try:
        result = float(cast(Any, value))
    except (TypeError, ValueError, OverflowError) as exc:
        raise InputValidationError(f"{label} must be a finite non-negative real number.") from exc
    if not math.isfinite(result) or result < 0.0:
        raise InputValidationError(f"{label} must be a finite non-negative real number.")
    return result


def readonly(value: np.ndarray, *, dtype: object) -> np.ndarray:
    result = np.asarray(value, dtype=dtype).copy()
    result.setflags(write=False)
    return result


def array_digest(values: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(values, dtype="<f8"))
    shape = np.asarray(array.shape, dtype="<i8").tobytes()
    return content_digest(b"qf-modal-array-f64/v1\0" + shape + array.tobytes())


def json_snapshot(value: object, label: str) -> dict[str, object]:
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        result = json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{label} must contain finite JSON-compatible values.") from exc
    if not isinstance(result, dict):
        raise InputValidationError(f"{label} must be a JSON object.")
    return cast(dict[str, object], result)
