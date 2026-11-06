"""Opt-in directional material tangent for the experimental Hencky law.

This module is deliberately separate from the Hencky response and all element,
material-factory, global-assembly, and Newton routes.  It returns only the
directional action ``delta_P`` for a supplied ``delta_F``; it does not expose a
flattened 9x9 tensor with an implicit component-order convention.
"""

from __future__ import annotations

from math import isfinite, log1p

import numpy as np

from solveur.materials.finite_strain_hencky import (
    ExperimentalHenckyElastic,
)

_LOG_SECOND_SERIES_RELATIVE_SPREAD = 0.25
_LOG_SECOND_SERIES_TERMS = 64


def _finite_matrix(value: object, name: str) -> np.ndarray:
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a finite real 3x3 array.") from error
    if raw.shape != (3, 3) or raw.dtype.kind not in "fiu":
        raise ValueError(f"{name} must be a finite real 3x3 array.")
    try:
        result = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be representable as float64.") from error
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values.")
    return result.copy()


def _log_first_divided_difference(left: float, right: float) -> float:
    """Stable ``log[x,y]`` for positive, binary64-resolved arguments."""
    low, high = (left, right) if left <= right else (right, left)
    if low == high:
        return 1.0 / low
    relative_gap = (high - low) / low
    if relative_gap < 1.0e-4:
        # log(1+r)/r = sum (-r)^k/(k+1), avoiding subtraction near a repeat.
        ratio = 1.0
        power = 1.0
        for order in range(1, 9):
            power *= -relative_gap
            ratio += power / (order + 1.0)
    else:
        ratio = log1p(relative_gap) / relative_gap
    return ratio / low


def _log_second_divided_difference(first: float, middle: float, last: float) -> float:
    """Stable symmetric second divided difference of log on positive nodes.

    For a tight eigenvalue cluster, a convergent Taylor series about the mean
    uses complete homogeneous polynomials and includes the confluent limits
    automatically.  Outside that cluster, the symmetric three-node divided
    difference uses stable first differences and separated outer nodes.
    Scaling all arguments by their maximum keeps intermediate values bounded;
    the second divided difference scales by the inverse square of that scale.
    """
    if not all(isfinite(value) and value > 0.0 for value in (first, middle, last)):
        raise ValueError("The logarithm divided difference requires positive finite eigenvalues.")
    scale = max(first, middle, last)
    x, y, z = sorted((first / scale, middle / scale, last / scale))
    center = (x + y + z) / 3.0
    relative_spread = (z - x) / center

    if relative_spread <= _LOG_SECOND_SERIES_RELATIVE_SPREAD:
        offsets = ((x - center) / center, (y - center) / center, (z - center) / center)
        elementary_1 = sum(offsets)
        elementary_2 = (
            offsets[0] * offsets[1]
            + offsets[0] * offsets[2]
            + offsets[1] * offsets[2]
        )
        elementary_3 = offsets[0] * offsets[1] * offsets[2]
        homogeneous = [1.0]
        total = -0.5  # n=0 term of log^[2] about the mean.
        for order in range(1, _LOG_SECOND_SERIES_TERMS + 1):
            previous_1 = homogeneous[order - 1]
            previous_2 = homogeneous[order - 2] if order >= 2 else 0.0
            previous_3 = homogeneous[order - 3] if order >= 3 else 0.0
            current = (
                elementary_1 * previous_1
                - elementary_2 * previous_2
                + elementary_3 * previous_3
            )
            homogeneous.append(current)
            sign = 1.0 if order % 2 else -1.0
            total += sign * current / (order + 2.0)
        normalized_value = total / center / center
    else:
        # log[x,y,z] = (log[x,y] - log[y,z]) / (x-z); sorted outer
        # eigenvalues are separated in this branch, while repeated adjacent
        # eigenvalues are handled by the confluent first-difference limit.
        normalized_value = (
            _log_first_divided_difference(x, y)
            - _log_first_divided_difference(y, z)
        ) / (x - z)

    with np.errstate(over="ignore", under="ignore", invalid="ignore", divide="ignore"):
        result = np.float64(normalized_value) / np.float64(scale) / np.float64(scale)
    value = float(result)
    if not isfinite(value):
        raise ValueError("The logarithm second divided difference is not representable in float64.")
    return value


def _frechet_log_symmetric(
    eigenvalues: np.ndarray,
    eigenvectors: np.ndarray,
    direction: np.ndarray,
) -> np.ndarray:
    local = eigenvectors.T @ direction @ eigenvectors
    factors = np.empty((3, 3), dtype=np.float64)
    for row in range(3):
        for column in range(3):
            factors[row, column] = _log_first_divided_difference(
                float(eigenvalues[row]), float(eigenvalues[column])
            )
    result = eigenvectors @ (factors * local) @ eigenvectors.T
    return 0.5 * (result + result.T)


def _frechet_log_second_symmetric(
    eigenvalues: np.ndarray,
    eigenvectors: np.ndarray,
    first_direction: np.ndarray,
    second_direction: np.ndarray,
) -> np.ndarray:
    first_local = eigenvectors.T @ first_direction @ eigenvectors
    second_local = eigenvectors.T @ second_direction @ eigenvectors
    result_local = np.zeros((3, 3), dtype=np.float64)
    for row in range(3):
        for column in range(3):
            value = 0.0
            for inner in range(3):
                coefficient = _log_second_divided_difference(
                    float(eigenvalues[row]),
                    float(eigenvalues[inner]),
                    float(eigenvalues[column]),
                )
                value += coefficient * (
                    first_local[row, inner] * second_local[inner, column]
                    + second_local[row, inner] * first_local[inner, column]
                )
            result_local[row, column] = value
    result = eigenvectors @ result_local @ eigenvectors.T
    return 0.5 * (result + result.T)


def hencky_directional_tangent_3d(
    material: ExperimentalHenckyElastic,
    deformation_gradient: object,
    direction: object,
) -> np.ndarray:
    """Return the analytic first-Piola tangent action ``A(F)[direction]``.

    ``F`` and ``direction`` use reference/current Cartesian matrix components
    in the same convention as ``ExperimentalHenckyElastic.evaluate``. The
    output is ``delta_P`` in the first-Piola measure, with the same stress
    units as the material moduli. Any finite real ``direction`` is accepted;
    admissibility applies to the base ``F``. This material-point action is
    opt-in and is not used by the response, element adapters, or Newton solver.
    """
    if not isinstance(material, ExperimentalHenckyElastic):
        raise TypeError("material must be an ExperimentalHenckyElastic instance.")
    deformation = _finite_matrix(deformation_gradient, "F")
    delta_deformation = _finite_matrix(direction, "delta_F")

    # Reuse the established admissibility and stress-measure contract at the
    # base point; no perturbed state or element/global route is evaluated here.
    response = material.evaluate(deformation)
    deformation = response.deformation_gradient
    cauchy_green = response.right_cauchy_green
    eigenvalues, eigenvectors = np.linalg.eigh(cauchy_green)
    with np.errstate(over="ignore", under="ignore", invalid="ignore", divide="ignore"):
        delta_cauchy_green = (
            deformation.T @ delta_deformation + delta_deformation.T @ deformation
        )
        delta_cauchy_green = 0.5 * (delta_cauchy_green + delta_cauchy_green.T)

        delta_logarithmic_strain = 0.5 * _frechet_log_symmetric(
            eigenvalues, eigenvectors, delta_cauchy_green
        )
        delta_trace = float(np.trace(delta_logarithmic_strain))
        delta_deviator = delta_logarithmic_strain - (delta_trace / 3.0) * np.eye(3)
        delta_conjugate = (
            2.0 * material.mu * delta_deviator
            + material.kappa * delta_trace * np.eye(3)
        )

        conjugate = response.logarithmic_strain_conjugate_stress
        delta_second_piola = _frechet_log_symmetric(
            eigenvalues, eigenvectors, delta_conjugate
        ) + _frechet_log_second_symmetric(
            eigenvalues,
            eigenvectors,
            delta_cauchy_green,
            conjugate,
        )
        delta_first_piola = (
            delta_deformation @ response.second_piola_kirchhoff_stress
            + deformation @ delta_second_piola
        )
    if not all(
        np.all(np.isfinite(value))
        for value in (
            delta_cauchy_green,
            delta_logarithmic_strain,
            delta_conjugate,
            delta_second_piola,
            delta_first_piola,
        )
    ):
        raise ValueError("Hencky directional tangent action is non-finite.")
    result = np.array(delta_first_piola, dtype=np.float64, copy=True)
    result.setflags(write=False)
    return result


__all__ = ["hencky_directional_tangent_3d"]
