"""Solid stress and state recovery helpers."""

from __future__ import annotations

import numpy as np

from solveur.elements.solid.tet10 import Tet10Element
from solveur.materials.orthotropic import OrthotropicSolidMaterial
from solveur.materials.solid import SolidConstitutiveMaterial


def _solid_result(strain: np.ndarray, stress: np.ndarray, state: dict[str, object] | None = None) -> dict[str, object]:
    strain_tensor = _voigt_strain_tensor(strain)
    stress_tensor = _voigt_stress_tensor(stress)
    mean_stress = float(np.trace(stress_tensor) / 3.0)
    deviator = stress_tensor - mean_stress * np.eye(3)
    result: dict[str, object] = {
        "strain": strain.tolist(),
        "stress": stress.tolist(),
        "principal_strain": np.linalg.eigvalsh(strain_tensor).tolist(),
        "principal_stress": np.linalg.eigvalsh(stress_tensor).tolist(),
        "strain_trace": float(np.trace(strain_tensor)),
        "stress_trace": float(np.trace(stress_tensor)),
        "hydrostatic_pressure": float(-mean_stress),
        "deviatoric_stress": _stress_tensor_to_voigt(deviator).tolist(),
    }
    if state is not None:
        result["material_state"] = state
        for key in ("equivalent_plastic_strain", "plastic_multiplier", "yield_function", "yield_stress"):
            if key in state:
                result[key] = state[key]
        if "plastic_strain" in state:
            result["plastic_strain"] = state["plastic_strain"]
    return result


def _solid_point_result(
    *,
    index: int,
    location: str,
    barycentric: list[float],
    coordinates: np.ndarray,
    weight: float,
    strain: np.ndarray,
    stress: np.ndarray,
    von_mises: float,
    state: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "index": int(index),
        "location": location,
        "barycentric": [float(value) for value in barycentric],
        "coordinates": np.asarray(coordinates, dtype=float).tolist(),
        "weight": float(weight),
        **_solid_result(strain, stress, state),
        "von_mises": float(von_mises),
    }


def _average_solid_points(points: list[dict[str, object]]) -> dict[str, object]:
    weights = np.asarray([float(point.get("weight", 1.0)) for point in points], dtype=float)
    if np.sum(weights) <= 0.0:
        weights = np.ones(len(points), dtype=float)
    strain = _weighted_average([point["strain"] for point in points], weights)
    stress = _weighted_average([point["stress"] for point in points], weights)
    result = _solid_result(strain, stress)
    for key in ("equivalent_plastic_strain", "plastic_multiplier", "yield_function", "yield_stress"):
        if key in points[0]:
            result[key] = float(np.average([float(point[key]) for point in points], weights=weights))
    if "plastic_strain" in points[0]:
        result["plastic_strain"] = _weighted_average([point["plastic_strain"] for point in points], weights).tolist()
    return result


def _solid_nodal_results(
    coords: np.ndarray,
    node_indices: object,
    result: dict[str, object],
    von_mises: float,
    method: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for local_index, node in enumerate(node_indices):
        row = {
            "node": int(node),
            "local_node": int(local_index),
            "method": method,
            "coordinates": np.asarray(coords[local_index], dtype=float).tolist(),
            "strain": result["strain"],
            "stress": result["stress"],
            "principal_strain": result["principal_strain"],
            "principal_stress": result["principal_stress"],
            "strain_trace": result["strain_trace"],
            "stress_trace": result["stress_trace"],
            "hydrostatic_pressure": result["hydrostatic_pressure"],
            "von_mises": float(von_mises),
            **_solid_state_subset(result),
        }
        row.update(_material_axis_subset(result))
        rows.append(row)
    return rows


def _tet10_extrapolated_nodal_results(
    element: Tet10Element,
    material: SolidConstitutiveMaterial,
    coords: np.ndarray,
    node_indices: tuple[int, ...],
    integration_points: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Recover a least-squares linear stress and strain field at TET10 nodes."""
    points = np.asarray([point["barycentric"] for point in integration_points], dtype=float)
    strains = element.extrapolate_integration_values(
        np.asarray([point["strain"] for point in integration_points], dtype=float),
        points,
    )
    stresses = element.extrapolate_integration_values(
        np.asarray([point["stress"] for point in integration_points], dtype=float),
        points,
    )
    recovery_method = (
        "linear_extrapolation_from_hammer"
        if len(integration_points) == Tet10Element.integration_point_count
        else "linear_barycentric_least_squares"
    )
    rows: list[dict[str, object]] = []
    for local_index, node in enumerate(node_indices):
        result = _solid_result(strains[local_index], stresses[local_index])
        result.update(_orthotropic_fields(material, strains[local_index], stresses[local_index]))
        rows.append(
            {
                "node": int(node),
                "local_node": int(local_index),
                "method": recovery_method,
                "coordinates": np.asarray(coords[local_index], dtype=float).tolist(),
                **result,
                "von_mises": Tet10Element.von_mises(stresses[local_index]),
            }
        )
    return rows


def _material_state(material: SolidConstitutiveMaterial, strain: np.ndarray) -> dict[str, object] | None:
    if not hasattr(material, "internal_state"):
        return None
    state = material.internal_state(strain)
    return _jsonable_state(state)


def _state_for_point(
    material: SolidConstitutiveMaterial,
    strain: np.ndarray,
    states: list[dict[str, object]] | None,
    point_index: int,
) -> dict[str, object] | None:
    if states and point_index < len(states):
        return _jsonable_state(states[point_index])
    return _material_state(material, strain)


def _stress_from_state(state: dict[str, object] | None, fallback: np.ndarray) -> np.ndarray:
    if state and "stress" in state:
        return np.asarray(state["stress"], dtype=float)
    return np.asarray(fallback, dtype=float)


def _jsonable_state(state: dict[str, object]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in state.items():
        if key in {"strain", "plastic_dissipation"}:
            continue
        if isinstance(value, np.ndarray):
            output[key] = value.tolist()
        elif isinstance(value, (bool, str)):
            output[key] = value
        elif isinstance(value, (int, float)):
            output[key] = float(value)
        elif isinstance(value, list):
            output[key] = [float(item) if isinstance(item, (int, float)) else item for item in value]
    return output


def _solid_state_subset(result: dict[str, object]) -> dict[str, object]:
    return {
        key: result[key]
        for key in (
            "equivalent_plastic_strain",
            "plastic_multiplier",
            "yield_function",
            "yield_stress",
            "plastic_strain",
        )
        if key in result
    }


def _orthotropic_fields(
    material: SolidConstitutiveMaterial,
    strain: np.ndarray,
    stress: np.ndarray,
) -> dict[str, object]:
    if not isinstance(material, OrthotropicSolidMaterial):
        return {}
    return {
        "material_strain": material.strain_material_axes(strain).tolist(),
        "material_stress": material.stress_material_axes(stress).tolist(),
        "material_orientation": material.orientation.tolist(),
        "material_type": material.material_type,
        "material_metadata": material.metadata,
    }


def _material_axis_subset(result: dict[str, object]) -> dict[str, object]:
    return {
        key: result[key]
        for key in ("material_strain", "material_stress", "material_orientation", "material_type")
        if key in result
    }
def _weighted_average(values: list[object], weights: np.ndarray) -> np.ndarray:
    arrays = np.vstack([np.asarray(value, dtype=float).ravel() for value in values])
    return np.average(arrays, axis=0, weights=weights)


def _voigt_stress_tensor(values: np.ndarray) -> np.ndarray:
    sx, sy, sz, txy, tyz, txz = np.asarray(values, dtype=float)
    return np.array([[sx, txy, txz], [txy, sy, tyz], [txz, tyz, sz]], dtype=float)


def _voigt_strain_tensor(values: np.ndarray) -> np.ndarray:
    ex, ey, ez, gxy, gyz, gxz = np.asarray(values, dtype=float)
    return np.array([[ex, 0.5 * gxy, 0.5 * gxz], [0.5 * gxy, ey, 0.5 * gyz], [0.5 * gxz, 0.5 * gyz, ez]], dtype=float)


def _stress_tensor_to_voigt(values: np.ndarray) -> np.ndarray:
    return np.array([values[0, 0], values[1, 1], values[2, 2], values[0, 1], values[1, 2], values[0, 2]], dtype=float)
