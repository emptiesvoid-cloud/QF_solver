"""Deterministic structured HEX8 geometry generation and sampled quality metrics.

This module only creates coordinates/connectivity and evaluates geometric
Jacobians. It does not import element stiffness code, assemble a system, solve,
or calculate modes.
"""

from __future__ import annotations

import hashlib
from itertools import product
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
_GAUSS = 1.0 / np.sqrt(3.0)
_QUALITY_POINTS = ((0.0, 0.0, 0.0),) + tuple(
    (sx * _GAUSS, sy * _GAUSS, sz * _GAUSS) for sx, sy, sz in product((-1.0, 1.0), repeat=3)
)
_DISTORTIONS = {"regular", "moderate_skew", "severe_shear", "warped", "near_degenerate", "seeded"}


def _shape_derivatives(point: tuple[float, float, float]) -> np.ndarray:
    xi, eta, zeta = point
    signs = _NODE_SIGNS
    derivatives = np.empty((8, 3), dtype=float)
    derivatives[:, 0] = 0.125 * signs[:, 0] * (1.0 + signs[:, 1] * eta) * (1.0 + signs[:, 2] * zeta)
    derivatives[:, 1] = 0.125 * signs[:, 1] * (1.0 + signs[:, 0] * xi) * (1.0 + signs[:, 2] * zeta)
    derivatives[:, 2] = 0.125 * signs[:, 2] * (1.0 + signs[:, 0] * xi) * (1.0 + signs[:, 1] * eta)
    return derivatives


def structured_hex8_mesh(
    element_counts: tuple[int, int, int] = (4, 2, 2),
    dimensions_m: tuple[float, float, float] = (20.0, 1.0, 1.0),
    *,
    distortion: str = "regular",
    seed: int = 20261026,
    perturbation_fraction: float = 0.02,
) -> tuple[np.ndarray, np.ndarray]:
    """Create a fixed-order structured mesh with optional reproducible geometry changes.

    ``near_degenerate`` compresses the z dimension to 5% of its requested
    size; it is a separate geometry family, not an equivalent physical model.
    ``seeded`` perturbs only interior nodes, leaving the exterior box fixed.
    """

    counts = np.asarray(element_counts, dtype=int)
    dimensions = np.asarray(dimensions_m, dtype=float)
    if counts.shape != (3,) or np.any(counts <= 0):
        raise ValueError("element_counts must contain three positive integers")
    if dimensions.shape != (3,) or not np.all(np.isfinite(dimensions)) or np.any(dimensions <= 0.0):
        raise ValueError("dimensions_m must contain three finite positive lengths")
    if distortion not in _DISTORTIONS:
        raise ValueError(f"unsupported distortion family: {distortion!r}")
    if not np.isfinite(perturbation_fraction) or perturbation_fraction < 0.0:
        raise ValueError("perturbation_fraction must be finite and non-negative")

    nx, ny, nz = (int(value) for value in counts)
    length, width, height = (float(value) for value in dimensions)
    nodes = np.asarray(
        [
            (length * i / nx, width * j / ny, height * k / nz)
            for i in range(nx + 1)
            for j in range(ny + 1)
            for k in range(nz + 1)
        ],
        dtype=float,
    )
    connectivity: list[list[int]] = []

    def node_id(i: int, j: int, k: int) -> int:
        return (i * (ny + 1) + j) * (nz + 1) + k

    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                connectivity.append(
                    [
                        node_id(i, j, k),
                        node_id(i + 1, j, k),
                        node_id(i + 1, j + 1, k),
                        node_id(i, j + 1, k),
                        node_id(i, j, k + 1),
                        node_id(i + 1, j, k + 1),
                        node_id(i + 1, j + 1, k + 1),
                        node_id(i, j + 1, k + 1),
                    ]
                )

    original = nodes.copy()
    x_ratio = original[:, 0] / length
    if distortion == "moderate_skew":
        nodes[:, 1] += 0.12 * x_ratio * (original[:, 2] - height / 2.0)
        nodes[:, 2] += 0.08 * x_ratio * (original[:, 1] - width / 2.0)
    elif distortion == "severe_shear":
        nodes[:, 1] += 4.0 * x_ratio * (original[:, 2] - height / 2.0)
    elif distortion == "warped":
        wave = np.sin(np.pi * x_ratio)
        nodes[:, 1] += 0.08 * wave * (original[:, 2] - height / 2.0)
        nodes[:, 2] += 0.06 * wave * (original[:, 1] - width / 2.0)
    elif distortion == "near_degenerate":
        nodes[:, 2] *= 0.05
    elif distortion == "seeded":
        rng = np.random.default_rng(seed)
        minimum_cell_size = float(np.min(dimensions / counts))
        displacements = rng.uniform(-1.0, 1.0, size=nodes.shape) * (perturbation_fraction * minimum_cell_size)
        indices = np.arange(nodes.shape[0])
        grid_i = indices // ((ny + 1) * (nz + 1))
        grid_j = (indices // (nz + 1)) % (ny + 1)
        grid_k = indices % (nz + 1)
        interior = (grid_i > 0) & (grid_i < nx) & (grid_j > 0) & (grid_j < ny) & (grid_k > 0) & (grid_k < nz)
        nodes[interior] += displacements[interior]

    return nodes, np.asarray(connectivity, dtype=np.int64)


def mesh_quality_metrics(nodes: np.ndarray, connectivity: np.ndarray) -> dict[str, Any]:
    """Measure sampled HEX8 Jacobian quality without invoking FEM operators.

    Positive Jacobians are checked at the centre and eight 2x2x2 Gauss points.
    This finite sample does not certify positivity throughout a distorted cell.
    """

    coordinates = np.asarray(nodes, dtype=float)
    cells = np.asarray(connectivity, dtype=np.int64)
    if coordinates.ndim != 2 or coordinates.shape[1] != 3 or not np.all(np.isfinite(coordinates)):
        raise ValueError("nodes must be a finite array with shape (n, 3)")
    if cells.ndim != 2 or cells.shape[1] != 8 or cells.size == 0:
        raise ValueError("connectivity must be a non-empty array with shape (m, 8)")
    if np.any(cells < 0) or np.any(cells >= coordinates.shape[0]):
        raise ValueError("connectivity contains an out-of-range node index")

    determinants: list[float] = []
    scaled_jacobians: list[float] = []
    column_aspect_ratios: list[float] = []
    max_column_cosines: list[float] = []
    for cell in cells:
        cell_coordinates = coordinates[cell]
        for point in _QUALITY_POINTS:
            jacobian = _shape_derivatives(point).T @ cell_coordinates
            determinant = float(np.linalg.det(jacobian))
            column_norms = np.linalg.norm(jacobian, axis=0)
            denominator = float(np.prod(column_norms))
            determinants.append(determinant)
            scaled_jacobians.append(determinant / denominator if denominator > 0.0 else float("nan"))
            column_aspect_ratios.append(
                float(np.max(column_norms) / np.min(column_norms)) if np.min(column_norms) > 0.0 else float("inf")
            )
            cosine_values = []
            for first, second in ((0, 1), (0, 2), (1, 2)):
                norm_product = column_norms[first] * column_norms[second]
                cosine_values.append(
                    abs(float(jacobian[:, first] @ jacobian[:, second])) / norm_product
                    if norm_product > 0.0
                    else float("inf")
                )
            max_column_cosines.append(max(cosine_values))

    det = np.asarray(determinants, dtype=float)
    scaled = np.asarray(scaled_jacobians, dtype=float)
    aspect = np.asarray(column_aspect_ratios, dtype=float)
    cosines = np.asarray(max_column_cosines, dtype=float)
    finite = bool(np.all(np.isfinite(det)) and np.all(np.isfinite(scaled)) and np.all(np.isfinite(aspect)))
    digest = hashlib.sha256(coordinates.tobytes() + cells.tobytes()).hexdigest()
    return {
        "node_count": int(coordinates.shape[0]),
        "element_count": int(cells.shape[0]),
        "dof_count": int(3 * coordinates.shape[0]),
        "geometry_sha256": digest,
        "sample_count_per_element": len(_QUALITY_POINTS),
        "jacobian_positivity_status": "SAMPLED_POSITIVE" if finite and bool(np.all(det > 0.0)) else "SAMPLED_INVALID",
        "positivity_certification": "NOT_CERTIFIED_BETWEEN_SAMPLES",
        "minimum_sampled_detJ_m3": float(np.min(det)),
        "maximum_sampled_detJ_m3": float(np.max(det)),
        "minimum_scaled_jacobian": float(np.min(scaled)),
        "maximum_directional_aspect_ratio": float(np.max(aspect)),
        "maximum_column_nonorthogonality_cosine": float(np.max(cosines)),
        "finite_metrics": finite,
    }
