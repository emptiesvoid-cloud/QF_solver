"""Independent NumPy reference for the WP05-D HEX20 stress observable.

This module intentionally has no imports from ``solveur`` or from the
production stress-window implementation.  It consumes only the raw
coordinates, connectivity and displacement written by a production run and
recomputes the clipped reference-window average with standalone formulas.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


_NODE_SIGNS = np.asarray(
    (
        (-1.0, -1.0, -1.0),
        (1.0, -1.0, -1.0),
        (1.0, 1.0, -1.0),
        (-1.0, 1.0, -1.0),
        (-1.0, -1.0, 1.0),
        (1.0, -1.0, 1.0),
        (1.0, 1.0, 1.0),
        (-1.0, 1.0, 1.0),
    ),
    dtype=float,
)
_EDGE_DATA = (
    (0, (1, 2), (-1.0, -1.0)),
    (1, (0, 2), (-1.0, -1.0)),
    (2, (0, 1), (-1.0, -1.0)),
    (1, (0, 2), (1.0, -1.0)),
    (2, (0, 1), (1.0, -1.0)),
    (0, (1, 2), (1.0, -1.0)),
    (2, (0, 1), (1.0, 1.0)),
    (2, (0, 1), (-1.0, 1.0)),
    (0, (1, 2), (-1.0, 1.0)),
    (1, (0, 2), (-1.0, 1.0)),
    (1, (0, 2), (1.0, 1.0)),
    (0, (1, 2), (1.0, 1.0)),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _shape_functions(point: np.ndarray) -> np.ndarray:
    values_point = np.asarray(point, dtype=float)
    if values_point.shape != (3,) or np.any(np.abs(values_point) > 1.0 + 1.0e-12):
        raise ValueError("Independent HEX20 point is outside [-1, 1].")
    values: np.ndarray = np.zeros(20, dtype=float)
    for index, signs in enumerate(_NODE_SIGNS):
        factors = 1.0 + signs * values_point
        values[index] = 0.125 * float(np.prod(factors)) * (float(signs @ values_point) - 2.0)
    for index, (free_axis, fixed_axes, fixed_signs) in enumerate(_EDGE_DATA, start=8):
        fixed_product = float(
            np.prod([1.0 + sign * values_point[axis] for axis, sign in zip(fixed_axes, fixed_signs)])
        )
        values[index] = 0.25 * fixed_product * (1.0 - values_point[free_axis] ** 2)
    return values


def _shape_derivatives(point: np.ndarray) -> np.ndarray:
    values_point = np.asarray(point, dtype=float)
    if values_point.shape != (3,) or np.any(np.abs(values_point) > 1.0 + 1.0e-12):
        raise ValueError("Independent HEX20 point is outside [-1, 1].")
    derivatives: np.ndarray = np.zeros((20, 3), dtype=float)
    for index, signs in enumerate(_NODE_SIGNS):
        factors = 1.0 + signs * values_point
        product = float(np.prod(factors))
        linear = float(signs @ values_point) - 2.0
        for axis in range(3):
            other_product = float(np.prod(np.delete(factors, axis)))
            derivatives[index, axis] = 0.125 * signs[axis] * (other_product * linear + product)
    for index, (free_axis, fixed_axes, fixed_signs) in enumerate(_EDGE_DATA, start=8):
        free_value = values_point[free_axis]
        fixed_factors = {
            axis: 1.0 + sign * values_point[axis]
            for axis, sign in zip(fixed_axes, fixed_signs)
        }
        fixed_product = float(np.prod(tuple(fixed_factors.values())))
        derivatives[index, free_axis] = -0.5 * fixed_product * free_value
        for axis, sign in zip(fixed_axes, fixed_signs):
            other = float(np.prod([fixed_factors[item] for item in fixed_axes if item != axis]))
            derivatives[index, axis] = 0.25 * sign * other * (1.0 - free_value**2)
    return derivatives


def _elasticity_matrix(young_modulus: float, poisson_ratio: float) -> np.ndarray:
    factor = young_modulus / ((1.0 + poisson_ratio) * (1.0 - 2.0 * poisson_ratio))
    lam = poisson_ratio * factor
    mu = young_modulus / (2.0 * (1.0 + poisson_ratio))
    matrix: np.ndarray = np.zeros((6, 6), dtype=float)
    matrix[:3, :3] = lam
    np.fill_diagonal(matrix[:3, :3], lam + 2.0 * mu)
    matrix[3, 3] = mu
    matrix[4, 4] = mu
    matrix[5, 5] = mu
    return matrix


def _stress_tensor(values: np.ndarray) -> np.ndarray:
    sx, sy, sz, txy, tyz, txz = np.asarray(values, dtype=float)
    return np.asarray([[sx, txy, txz], [txy, sy, tyz], [txz, tyz, sz]], dtype=float)


def _strain_voigt(tensor: np.ndarray) -> np.ndarray:
    return np.asarray(
        [
            tensor[0, 0],
            tensor[1, 1],
            tensor[2, 2],
            2.0 * tensor[0, 1],
            2.0 * tensor[1, 2],
            2.0 * tensor[0, 2],
        ],
        dtype=float,
    )


def _physical_bounds(contract: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    geometry = contract["physical_inputs"]["geometry"]
    dimensions = np.asarray([geometry["L"], geometry["H"], geometry["D"]], dtype=float)
    region = contract["observable"]["normalized_region"]
    normalized = np.asarray(
        [region["x_over_L"], region["y_over_H"], region["z_over_D"]],
        dtype=float,
    )
    return normalized[:, 0] * dimensions, normalized[:, 1] * dimensions


def _clipped_natural_bounds(
    coordinates: np.ndarray,
    physical_low: np.ndarray,
    physical_high: np.ndarray,
) -> tuple[np.ndarray, np.ndarray] | None:
    corners = np.asarray(coordinates[:8], dtype=float)
    cell_low = np.min(corners, axis=0)
    cell_high = np.max(corners, axis=0)
    span = cell_high - cell_low
    if np.any(span <= 0.0):
        raise ValueError("Independent reference received a degenerate HEX20 cell.")
    clipped_low = np.maximum(cell_low, physical_low)
    clipped_high = np.minimum(cell_high, physical_high)
    if np.any(clipped_high <= clipped_low):
        return None
    return (
        -1.0 + 2.0 * (clipped_low - cell_low) / span,
        -1.0 + 2.0 * (clipped_high - cell_low) / span,
    )


def _point_sigma_xx(
    coordinates: np.ndarray,
    local_displacement: np.ndarray,
    elasticity: np.ndarray,
    natural_point: np.ndarray,
) -> tuple[float, np.ndarray, float]:
    derivatives = _shape_derivatives(natural_point)
    jacobian = derivatives.T @ coordinates
    determinant_j0 = float(np.linalg.det(jacobian))
    if not np.isfinite(determinant_j0) or determinant_j0 <= 1.0e-14:
        raise ValueError("Independent reference encountered an invalid reference Jacobian.")
    gradients = derivatives @ np.linalg.inv(jacobian).T
    local = np.asarray(local_displacement, dtype=float).reshape(20, 3)
    deformation = np.eye(3) + local.T @ gradients
    determinant_f = float(np.linalg.det(deformation))
    if not np.isfinite(determinant_f) or determinant_f <= 1.0e-10:
        raise ValueError("Independent reference encountered an invalid deformation gradient.")
    green = 0.5 * (deformation.T @ deformation - np.eye(3))
    second = _stress_tensor(elasticity @ _strain_voigt(green))
    cauchy = deformation @ second @ deformation.T / determinant_f
    location = _shape_functions(natural_point) @ coordinates
    return float(cauchy[0, 0]), location, determinant_j0


def evaluate_raw(
    raw_path: Path,
    candidate_contract_path: Path,
) -> dict[str, Any]:
    """Recompute the candidate observable from one production raw artifact."""

    contract = json.loads(candidate_contract_path.read_text(encoding="utf-8"))
    geometry = contract["physical_inputs"]["geometry"]
    material = contract["physical_inputs"]["material"]
    expected_volume = float(contract["observable"]["expected_reference_volume"])
    physical_low, physical_high = _physical_bounds(contract)
    elasticity = _elasticity_matrix(float(material["E"]), float(material["nu"]))
    with np.load(raw_path, allow_pickle=False) as raw:
        coordinates = np.asarray(raw["coordinates"], dtype=float)
        connectivity = np.asarray(raw["connectivity"], dtype=int)
        displacement = np.asarray(raw["displacement"], dtype=float)
    if coordinates.ndim != 2 or coordinates.shape[1] != 3:
        raise ValueError("Independent reference coordinates must have shape (nodes, 3).")
    if connectivity.ndim != 2 or connectivity.shape[1] != 20:
        raise ValueError("Independent reference connectivity must have shape (elements, 20).")
    if displacement.shape != (3 * coordinates.shape[0],):
        raise ValueError("Independent reference displacement has an unexpected shape.")
    if not np.isfinite(coordinates).all() or not np.isfinite(displacement).all():
        raise ValueError("Independent reference input contains non-finite values.")

    gauss_points, gauss_weights = np.polynomial.legendre.leggauss(5)
    weighted_sigma_xx = 0.0
    reference_volume = 0.0
    intersected_elements = 0
    quadrature_points = 0
    maximum_mapping_error = 0.0
    values = displacement.reshape(-1, 3)
    for element_nodes in connectivity:
        nodes = np.asarray(element_nodes, dtype=int)
        element_coordinates = coordinates[nodes]
        bounds = _clipped_natural_bounds(element_coordinates, physical_low, physical_high)
        if bounds is None:
            continue
        natural_low, natural_high = bounds
        midpoint = 0.5 * (natural_high + natural_low)
        half_width = 0.5 * (natural_high - natural_low)
        intersected_elements += 1
        corner_low = np.min(element_coordinates[:8], axis=0)
        corner_high = np.max(element_coordinates[:8], axis=0)
        for xi, weight_xi in zip(gauss_points, gauss_weights, strict=True):
            for eta, weight_eta in zip(gauss_points, gauss_weights, strict=True):
                for zeta, weight_zeta in zip(gauss_points, gauss_weights, strict=True):
                    canonical = np.asarray([xi, eta, zeta], dtype=float)
                    natural = midpoint + half_width * canonical
                    sigma_xx, location, determinant_j0 = _point_sigma_xx(
                        element_coordinates,
                        values[nodes],
                        elasticity,
                        natural,
                    )
                    affine_location = corner_low + 0.5 * (natural + 1.0) * (corner_high - corner_low)
                    mapping_error = float(np.max(np.abs(location - affine_location)))
                    maximum_mapping_error = max(maximum_mapping_error, mapping_error)
                    if mapping_error > 1.0e-12:
                        raise ValueError("Independent reference requires affine HEX20 geometry.")
                    natural_weight = float(
                        weight_xi * weight_eta * weight_zeta * np.prod(half_width)
                    )
                    reference_weight = natural_weight * determinant_j0
                    weighted_sigma_xx += reference_weight * sigma_xx
                    reference_volume += reference_weight
                    quadrature_points += 1
    if not np.isfinite(reference_volume) or reference_volume <= 0.0:
        raise ValueError("Independent reference produced no positive reference volume.")
    return {
        "status": "PASS",
        "method": "INDEPENDENT_NUMPY_HEX20_CLIPPED_WINDOW_GAUSS_5",
        "source_raw_sha256": _sha256(raw_path),
        "representative_sigma_xx": float(weighted_sigma_xx / reference_volume),
        "reference_volume": float(reference_volume),
        "expected_reference_volume": expected_volume,
        "reference_volume_absolute_error": float(abs(reference_volume - expected_volume)),
        "intersected_element_count": intersected_elements,
        "quadrature_point_count": quadrature_points,
        "quadrature_order_per_axis": 5,
        "maximum_affine_mapping_error": maximum_mapping_error,
        "physical_window": {
            "low": physical_low.tolist(),
            "high": physical_high.tolist(),
        },
        "independence": {
            "imports_production_solver": False,
            "imports_production_stress_window": False,
            "uses_raw_coordinates_connectivity_displacement_only": True,
        },
        "geometry": geometry,
        "material": material,
    }
