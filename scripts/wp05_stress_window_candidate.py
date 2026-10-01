"""Candidate WP05-D stress observable with an exact reference-space window.

This is qualification tooling only.  It deliberately does not modify the
frozen WP05-C/D integration-point observable or its evidence.  The candidate
is intended for an Owner-approved *new* contract revision, after which the
full H1/H2/H3 qualification can be rerun from the frozen physical inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from scripts.wp05_cd_structural_harness import MeshData, StructuralBenchmarkContract
from solveur.core.nonlinear.contracts import evaluate_constitutive
from solveur.elements.solid.hex20 import Hex20Element


@dataclass(frozen=True)
class ExactReferenceWindowCandidate:
    """A non-binding, region-aligned replacement observable for WP05-D.

    The physical window, its reference-volume weighting and the frozen 8%
    threshold are intentionally unchanged.  Only the numerical realization of
    the region changes: cells are clipped to the physical box before stress is
    sampled, avoiding mesh-dependent inclusion/exclusion of whole Gauss rows.
    """

    quadrature_order: int = 5
    method_id: str = "EXACT_REFERENCE_WINDOW_CLIPPED_HEX20_TENSOR_GAUSS_5"

    def __post_init__(self) -> None:
        if self.quadrature_order < 2:
            raise ValueError("Candidate window quadrature requires order >= 2.")


def _stress_tensor(values: np.ndarray) -> np.ndarray:
    sx, sy, sz, txy, tyz, txz = np.asarray(values, dtype=float)
    return np.asarray(
        [[sx, txy, txz], [txy, sy, tyz], [txz, tyz, sz]],
        dtype=float,
    )


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


def _physical_bounds(contract: StructuralBenchmarkContract) -> tuple[np.ndarray, np.ndarray]:
    dimensions = np.asarray([contract.length, contract.height, contract.depth], dtype=float)
    normalized = np.asarray(contract.sample_region, dtype=float)
    return normalized[:, 0] * dimensions, normalized[:, 1] * dimensions


def _expected_volume(contract: StructuralBenchmarkContract) -> float:
    low, high = _physical_bounds(contract)
    return float(np.prod(high - low))


def _clipped_natural_bounds(
    coordinates: np.ndarray,
    physical_low: np.ndarray,
    physical_high: np.ndarray,
) -> tuple[np.ndarray, np.ndarray] | None:
    """Return the natural-space box for one straight-sided HEX20 intersection."""

    corner_coordinates = np.asarray(coordinates[:8], dtype=float)
    cell_low = np.min(corner_coordinates, axis=0)
    cell_high = np.max(corner_coordinates, axis=0)
    span = cell_high - cell_low
    if np.any(span <= 0.0):
        raise ValueError("Candidate stress window received a degenerate HEX20 cell.")
    clipped_low = np.maximum(cell_low, physical_low)
    clipped_high = np.minimum(cell_high, physical_high)
    if np.any(clipped_high <= clipped_low):
        return None
    natural_low = -1.0 + 2.0 * (clipped_low - cell_low) / span
    natural_high = -1.0 + 2.0 * (clipped_high - cell_low) / span
    return natural_low, natural_high


def _cauchy_sigma_xx(
    coordinates: np.ndarray,
    local_displacement: np.ndarray,
    material: Any,
    natural_point: np.ndarray,
) -> tuple[float, np.ndarray, float]:
    """Evaluate the existing total-Lagrangian material law at one point.

    This is a post-processing call: it neither assembles nor solves a system.
    The returned location validates that the clipped natural box still maps to
    the intended physical reference window.
    """

    derivatives = Hex20Element.shape_derivatives_reference(natural_point)
    jacobian = derivatives.T @ coordinates
    determinant_j0 = float(np.linalg.det(jacobian))
    if not np.isfinite(determinant_j0) or determinant_j0 <= 1.0e-14:
        raise ValueError("Candidate stress window encountered an invalid reference Jacobian.")
    gradients = derivatives @ np.linalg.inv(jacobian).T
    local = np.asarray(local_displacement, dtype=float).reshape(20, 3)
    deformation = np.eye(3) + local.T @ gradients
    determinant_f = float(np.linalg.det(deformation))
    if not np.isfinite(determinant_f) or determinant_f <= 1.0e-10:
        raise ValueError("Candidate stress window encountered an invalid deformation gradient.")
    green = 0.5 * (deformation.T @ deformation - np.eye(3))
    response = evaluate_constitutive(material, _strain_voigt(green))
    second = _stress_tensor(np.asarray(response.stress, dtype=float))
    cauchy = deformation @ second @ deformation.T / determinant_f
    location = Hex20Element.shape_functions(natural_point) @ coordinates
    return float(cauchy[0, 0]), location, determinant_j0


def clipped_reference_window_sigma_xx_hex20(
    mesh: MeshData,
    displacement: np.ndarray,
    material: Any,
    contract: StructuralBenchmarkContract | None = None,
    candidate: ExactReferenceWindowCandidate | None = None,
) -> dict[str, Any]:
    """Integrate Cauchy ``sigma_xx`` over the exact fixed reference window.

    This candidate supports the straight-sided, structured HEX20 benchmark only.
    It rejects a non-affine map rather than silently applying an approximate
    physical clipping rule to a curved element.
    """

    if mesh.family != "HEX20":
        raise ValueError("Exact clipped candidate is currently defined for WP05-D HEX20 only.")
    contract = contract or StructuralBenchmarkContract()
    candidate = candidate or ExactReferenceWindowCandidate()
    values = np.asarray(displacement, dtype=float)
    if values.shape == (3 * mesh.nodes,):
        values = values.reshape(mesh.nodes, 3)
    if values.shape != (mesh.nodes, 3) or not np.isfinite(values).all():
        raise ValueError("Candidate stress window displacement must be finite with shape (nodes, 3).")
    physical_low, physical_high = _physical_bounds(contract)
    gauss_points, gauss_weights = np.polynomial.legendre.leggauss(candidate.quadrature_order)
    weighted_sigma_xx = 0.0
    reference_volume = 0.0
    intersected_elements = 0
    quadrature_points = 0
    maximum_mapping_error = 0.0
    for connectivity in mesh.connectivity:
        nodes = np.asarray(connectivity, dtype=int)
        coordinates = np.asarray(mesh.coordinates[nodes], dtype=float)
        bounds = _clipped_natural_bounds(coordinates, physical_low, physical_high)
        if bounds is None:
            continue
        natural_low, natural_high = bounds
        midpoint = 0.5 * (natural_high + natural_low)
        half_width = 0.5 * (natural_high - natural_low)
        intersected_elements += 1
        for xi, weight_xi in zip(gauss_points, gauss_weights, strict=True):
            for eta, weight_eta in zip(gauss_points, gauss_weights, strict=True):
                for zeta, weight_zeta in zip(gauss_points, gauss_weights, strict=True):
                    canonical = np.asarray([xi, eta, zeta], dtype=float)
                    natural = midpoint + half_width * canonical
                    sigma_xx, location, determinant_j0 = _cauchy_sigma_xx(
                        coordinates,
                        values[nodes],
                        material,
                        natural,
                    )
                    # Validate affine geometry against the coordinate implied by each
                    # mapped natural point through the corner-cell interpolation.
                    corner_low = np.min(coordinates[:8], axis=0)
                    corner_high = np.max(coordinates[:8], axis=0)
                    affine_location = corner_low + 0.5 * (natural + 1.0) * (corner_high - corner_low)
                    mapping_error = float(np.max(np.abs(location - affine_location)))
                    maximum_mapping_error = max(maximum_mapping_error, mapping_error)
                    if mapping_error > 1.0e-12:
                        raise ValueError("Candidate stress window requires straight-sided affine HEX20 geometry.")
                    natural_weight = float(weight_xi * weight_eta * weight_zeta * np.prod(half_width))
                    reference_weight = natural_weight * determinant_j0
                    weighted_sigma_xx += reference_weight * sigma_xx
                    reference_volume += reference_weight
                    quadrature_points += 1
    if reference_volume <= 0.0 or not np.isfinite(reference_volume):
        raise ValueError("Candidate stress window has no positive reference volume.")
    expected_volume = _expected_volume(contract)
    return {
        "method": candidate.method_id,
        "quadrature_order_per_axis": candidate.quadrature_order,
        "representative_sigma_xx": float(weighted_sigma_xx / reference_volume),
        "reference_volume": float(reference_volume),
        "expected_reference_volume": expected_volume,
        "reference_volume_absolute_error": float(abs(reference_volume - expected_volume)),
        "intersected_element_count": intersected_elements,
        "quadrature_point_count": quadrature_points,
        "maximum_affine_mapping_error": maximum_mapping_error,
        "normalized_region": {
            "x_over_L": list(contract.sample_region[0]),
            "y_over_H": list(contract.sample_region[1]),
            "z_over_D": list(contract.sample_region[2]),
        },
        "status": "CANDIDATE_POSTPROCESS_ONLY_NOT_FORMAL",
    }
