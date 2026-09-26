"""Prospective, solver-independent WP08-D mesh-refinement metrics.

These helpers post-process frozen meshes and serialized contact states. They
do not import or call production contact/mechanics routines.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import numpy as np


MACHINE_SCALE_MULTIPLIER = 64.0


def normalized_refinement_delta(
    coarse: float | Sequence[float],
    fine: float | Sequence[float],
    *,
    characteristic_scale: float,
) -> dict[str, float]:
    """Return the contract's relative delta with a dimensionally scaled floor.

    Scalars use absolute value; vectors use the Euclidean norm. The denominator
    floor is 64 machine epsilons times the declared characteristic scale.
    Missing, non-finite, shape-incompatible, or non-positive-scale inputs fail
    closed by raising ``ValueError``.
    """

    scale = float(characteristic_scale)
    if not np.isfinite(scale) or scale <= 0.0:
        raise ValueError("characteristic_scale must be finite and positive")
    try:
        coarse_array = np.asarray(coarse, dtype=float)
        fine_array = np.asarray(fine, dtype=float)
    except (TypeError, ValueError) as error:
        raise ValueError("refinement values must be finite numeric scalars or vectors") from error
    if coarse_array.shape != fine_array.shape or coarse_array.size == 0:
        raise ValueError("coarse and fine values must have the same non-empty shape")
    if not np.all(np.isfinite(coarse_array)) or not np.all(np.isfinite(fine_array)):
        raise ValueError("non-finite refinement value")

    scalar = coarse_array.ndim == 0
    coarse_norm = abs(float(coarse_array)) if scalar else float(np.linalg.norm(coarse_array))
    fine_norm = abs(float(fine_array)) if scalar else float(np.linalg.norm(fine_array))
    difference = (
        abs(float(fine_array) - float(coarse_array)) if scalar else float(np.linalg.norm(fine_array - coarse_array))
    )
    floor = float(MACHINE_SCALE_MULTIPLIER * np.finfo(float).eps * scale)
    denominator = max(coarse_norm, fine_norm, floor)
    delta = difference / denominator
    if not np.isfinite(delta):
        raise ValueError("normalized refinement delta is non-finite")
    return {
        "absolute_delta": difference,
        "denominator": denominator,
        "scale_floor": floor,
        "relative_delta": delta,
    }


def evaluate_refinement_gate(
    name: str,
    coarse: float | Sequence[float],
    fine: float | Sequence[float],
    *,
    characteristic_scale: float,
    threshold: float,
) -> dict[str, Any]:
    """Apply an already-declared limit to the prospective normalized delta."""

    limit = float(threshold)
    if not np.isfinite(limit) or limit < 0.0:
        raise ValueError("refinement threshold must be finite and non-negative")
    delta = normalized_refinement_delta(coarse, fine, characteristic_scale=characteristic_scale)
    delta_percent = 100.0 * delta["relative_delta"]
    return {
        "metric": name,
        **delta,
        "threshold": limit,
        "status": "PASS" if delta["relative_delta"] <= limit else "FAIL",
        "delta_percent": delta_percent,
    }


def lumped_slave_surface_areas(
    nodes: Sequence[Sequence[float]] | np.ndarray,
    bottom_triangles: Iterable[Sequence[int]],
    slave_nodes: Iterable[int],
) -> dict[int, float]:
    """Lump each T3 bottom-face area among its eligible slave vertices.

    For each face, its full area is divided equally by the number of eligible
    vertices on that face. This renormalizes the linear T3 lumped weights after
    excluding the clamped ``x=0`` row, so the eligible nodal weights partition
    the physical bottom patch instead of losing the excluded row's share.
    Every face is validated, including faces adjacent to the excluded row.
    """

    coordinates = np.asarray(nodes, dtype=float)
    if coordinates.ndim != 2 or coordinates.shape[1] != 3 or not np.all(np.isfinite(coordinates)):
        raise ValueError("nodes must be a finite N-by-3 coordinate array")
    raw_slaves = tuple(slave_nodes)
    if any(isinstance(node, (bool, np.bool_)) or not isinstance(node, (int, np.integer)) for node in raw_slaves):
        raise ValueError("slave node indices must be integers, not booleans")
    slaves = tuple(int(node) for node in raw_slaves)
    if not slaves or len(set(slaves)) != len(slaves):
        raise ValueError("slave_nodes must be non-empty and unique")
    if any(node < 0 or node >= len(coordinates) for node in slaves):
        raise ValueError("slave node index is outside the node array")
    slave_set = set(slaves)
    accumulated = {node: 0.0 for node in slaves}

    triangle_count = 0
    seen_faces: set[tuple[int, ...]] = set()
    for face in bottom_triangles:
        if any(isinstance(node, (bool, np.bool_)) or not isinstance(node, (int, np.integer)) for node in face):
            raise ValueError("bottom face indices must be integers")
        triangle = tuple(int(node) for node in face)
        if len(triangle) != 3 or len(set(triangle)) != 3:
            raise ValueError("each bottom face must contain three distinct node indices")
        if any(node < 0 or node >= len(coordinates) for node in triangle):
            raise ValueError("bottom-face node index is outside the node array")
        marker = tuple(sorted(triangle))
        if marker in seen_faces:
            raise ValueError("duplicate bottom face")
        seen_faces.add(marker)
        xyz = coordinates[list(triangle)]
        area = 0.5 * float(np.linalg.norm(np.cross(xyz[1] - xyz[0], xyz[2] - xyz[0])))
        if not np.isfinite(area) or area <= 0.0:
            raise ValueError("bottom face has non-positive or non-finite area")
        triangle_count += 1
        eligible_face_nodes = [node for node in triangle if node in slave_set]
        if not eligible_face_nodes:
            raise ValueError("bottom face has no eligible slave node to receive its area")
        contribution = area / len(eligible_face_nodes)
        for node in eligible_face_nodes:
            accumulated[node] += contribution

    if triangle_count == 0 or any(not np.isfinite(value) or value <= 0.0 for value in accumulated.values()):
        raise ValueError("bottom-face set is empty or does not cover every eligible slave node")
    return accumulated


def surface_region_resolution(nodes: np.ndarray, active_nodes: Sequence[int]) -> str:
    """Distinguish an area-supported nodal patch from edge/point closure.

    This is a geometric diagnostic, not reconstruction of continuum contact
    area or pressure. Equal area fractions do not prove spatial agreement.
    """
    if not active_nodes:
        return "OPEN_NO_CONTACT"
    xyz = np.asarray(nodes, dtype=float)[list(active_nodes)]
    if not np.isfinite(xyz).all():
        raise ValueError("non-finite active-node coordinates")
    return "AREA_SUPPORTED_NODAL_PATCH" if np.linalg.matrix_rank(xyz - xyz[0]) >= 2 else "EDGE_OR_POINT_ONLY"


def contact_region_area_fractions(
    contact_rows: Sequence[Mapping[str, Any]],
    slave_area_weights: Mapping[int, float],
) -> dict[str, Any]:
    """Compute area-weighted open/active/stick/slip fractions fail-closed."""

    if not slave_area_weights:
        raise ValueError("slave area weights are required")
    weights: dict[int, float] = {}
    for raw_weight_node, raw_weight in slave_area_weights.items():
        node = int(raw_weight_node)
        weight = float(raw_weight)
        if node in weights or not np.isfinite(weight) or weight <= 0.0:
            raise ValueError("slave area weights must have unique nodes and positive finite values")
        weights[node] = weight

    states: dict[int, tuple[bool, str]] = {}
    for row in contact_rows:
        if not isinstance(row, Mapping):
            raise ValueError("every contact row must be an object")
        raw_node = row.get("slave_node")
        raw_active = row.get("active")
        raw_state = row.get("tangential_state")
        if isinstance(raw_node, bool) or not isinstance(raw_node, (int, np.integer)):
            raise ValueError("contact row is missing a valid slave_node")
        node = int(raw_node)
        if node in states or node not in weights or not isinstance(raw_active, bool):
            raise ValueError("duplicate, unexpected, or invalid contact row")
        if not isinstance(raw_state, str) or raw_state.lower() not in {"open", "stick", "slip"}:
            raise ValueError("contact row has an unsupported tangential state")
        state = raw_state.lower()
        if (not raw_active and state != "open") or (raw_active and state not in {"stick", "slip"}):
            raise ValueError("normal activity and tangential state are inconsistent")
        states[node] = (raw_active, state)
    if set(states) != set(weights):
        raise ValueError("contact rows do not cover exactly the eligible slave nodes")

    total_area = float(sum(weights.values()))
    active_area = sum(weights[node] for node, (active, _) in states.items() if active)
    open_area = sum(weights[node] for node, (active, _) in states.items() if not active)
    stick_area = sum(weights[node] for node, (_, state) in states.items() if state == "stick")
    slip_area = sum(weights[node] for node, (_, state) in states.items() if state == "slip")
    partition_error = abs(total_area - open_area - stick_area - slip_area) / total_area
    partition_tolerance = MACHINE_SCALE_MULTIPLIER * np.finfo(float).eps * max(1, len(weights))
    if not np.isfinite(partition_error) or partition_error > partition_tolerance:
        raise ValueError("open/stick/slip area partition does not close to floating-point tolerance")
    return {
        "eligible_slave_area": total_area,
        "area_by_state": {
            "open": open_area,
            "stick": stick_area,
            "slip": slip_area,
        },
        "fraction_by_state": {
            "open": open_area / total_area,
            "stick": stick_area / total_area,
            "slip": slip_area / total_area,
        },
        "active_contact_region_fraction": active_area / total_area,
        "stick_slip_region_vector": [stick_area / total_area, slip_area / total_area],
        "area_partition_error": partition_error,
        "area_partition_tolerance": float(partition_tolerance),
    }
