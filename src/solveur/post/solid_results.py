"""Reusable solid-element stress and strain recovery helpers."""

from __future__ import annotations

import numpy as np

from solveur.elements.solid.hex20 import Hex20Element
from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.tet10 import Tet10Element
from solveur.elements.solid.wedge6 import Wedge6Element
from solveur.materials.orthotropic import OrthotropicSolidMaterial
from solveur.materials.solid import SolidConstitutiveMaterial


def tet4_result(
    index: int,
    element_type: str,
    nodes: tuple[int, ...],
    material: SolidConstitutiveMaterial,
    coords: np.ndarray,
    local_u: np.ndarray,
    states: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Recover the constant-strain result for a TET4 element."""
    from solveur.elements.solid.tet4 import Tet4Element

    element = Tet4Element(material)
    strain = element.strain(coords, local_u)
    state = state_for_point(material, strain, states, 0)
    stress = stress_from_state(state, element.stress(coords, local_u))
    result = solid_result(strain, stress, state)
    result.update(orthotropic_fields(material, strain, stress))
    point_result = solid_point_result(
        index=0,
        location="centroid",
        barycentric=[0.25, 0.25, 0.25, 0.25],
        coordinates=np.mean(coords, axis=0),
        weight=abs(Tet4Element.signed_volume(coords)),
        strain=strain,
        stress=stress,
        von_mises=Tet4Element.von_mises(stress),
        state=state,
    )
    point_result.update(orthotropic_fields(material, strain, stress))
    return {
        "element": index,
        "type": element_type,
        **result,
        "von_mises": Tet4Element.von_mises(stress),
        "integration_points": [point_result],
        "nodal_results": solid_nodal_results(
            coords, nodes, result, Tet4Element.von_mises(stress), "constant_strain"
        ),
    }


def tet10_result(
    index: int,
    element_type: str,
    nodes: tuple[int, ...],
    material: SolidConstitutiveMaterial,
    coords: np.ndarray,
    local_u: np.ndarray,
    states: list[dict[str, object]] | None = None,
    nonlinear_quadrature: str = "hammer4",
) -> dict[str, object]:
    """Recover the quadrature and nodal result for a TET10 element."""
    element = Tet10Element(material, nonlinear_quadrature=nonlinear_quadrature)
    strain = element.strain(coords, local_u)
    stress = element.stress(coords, local_u)
    state = material_state(material, strain)
    integration_points: list[dict[str, object]] = []
    if states:
        quadrature = element.nonlinear_integration_rule()
        quadrature_name = element.nonlinear_quadrature
    else:
        quadrature = element.stiffness_integration_rule(coords)
        quadrature_name = "hammer" if len(quadrature) == 4 else "duffy_4"
    for point_index, (point, weight) in enumerate(quadrature):
        b_matrix, det_j = Tet10Element.b_matrix(coords, point)
        point_strain = b_matrix @ np.asarray(local_u, dtype=float)
        point_state = state_for_point(material, point_strain, states, point_index)
        point_stress = stress_from_state(point_state, material.stress_tangent(point_strain)[0])
        shape = Tet10Element.shape_functions(point)
        point_result = solid_point_result(
            index=point_index,
            location=quadrature_name,
            barycentric=list(point),
            coordinates=shape @ coords,
            weight=weight * det_j,
            strain=point_strain,
            stress=point_stress,
            von_mises=Tet10Element.von_mises(point_stress),
            state=point_state,
        )
        point_result.update(orthotropic_fields(material, point_strain, point_stress))
        integration_points.append(point_result)
    averaged_result = average_solid_points(integration_points)
    if states:
        result = averaged_result
        result["material_state"] = {
            "model": str(integration_points[0].get("material_state", {}).get("model", "path_dependent")),
            "source": "committed_integration_point_average",
        }
        result_stress = np.asarray(result["stress"], dtype=float)
        location = "integration_average"
    else:
        result = solid_result(strain, stress, state)
        result_stress = stress
        location = "center"
    result.update(orthotropic_fields(material, np.asarray(result["strain"]), result_stress))
    if states:
        nodal_results = solid_nodal_results(
            coords,
            nodes,
            averaged_result,
            float(np.mean([point["von_mises"] for point in integration_points])),
            "integration_average",
        )
    else:
        nodal_results = tet10_extrapolated_nodal_results(
            element, material, coords, nodes, integration_points
        )
    return {
        "element": index,
        "type": element_type,
        "location": location,
        **result,
        "von_mises": Tet10Element.von_mises(result_stress),
        "integration_points": integration_points,
        "nodal_results": nodal_results,
    }


def hex8_result(
    index: int,
    element_type: str,
    nodes: tuple[int, ...],
    material: SolidConstitutiveMaterial,
    coords: np.ndarray,
    local_u: np.ndarray,
    states: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Recover the integrated result for a HEX8 element."""
    element = Hex8Element(material)
    integration_points: list[dict[str, object]] = []
    for point_index, point in enumerate(Hex8Element.integration_points):
        b_matrix, determinant = element.b_matrix(coords, point)
        point_strain = b_matrix @ np.asarray(local_u, dtype=float)
        point_state = state_for_point(material, point_strain, states, point_index)
        point_stress = stress_from_state(point_state, material.stress_tangent(point_strain)[0])
        shape = element.shape_functions(point)
        point_result = solid_point_result(
            index=point_index,
            location="gauss",
            barycentric=list(point),
            coordinates=shape @ coords,
            weight=determinant,
            strain=point_strain,
            stress=point_stress,
            von_mises=Hex8Element.von_mises(point_stress),
            state=point_state,
        )
        point_result["natural_coordinates"] = list(point)
        point_result.update(orthotropic_fields(material, point_strain, point_stress))
        integration_points.append(point_result)
    averaged = average_solid_points(integration_points)
    averaged.update(orthotropic_fields(material, np.asarray(averaged["strain"]), np.asarray(averaged["stress"])))
    return {
        "element": index,
        "type": element_type,
        "location": "integration_average",
        **averaged,
        "von_mises": Hex8Element.von_mises(np.asarray(averaged["stress"])),
        "integration_points": integration_points,
        "nodal_results": solid_nodal_results(
            coords,
            nodes,
            averaged,
            Hex8Element.von_mises(np.asarray(averaged["stress"])),
            "volume_weighted_gauss_average",
        ),
    }


def hex20_result(
    index: int,
    element_type: str,
    nodes: tuple[int, ...],
    material: SolidConstitutiveMaterial,
    coords: np.ndarray,
    local_u: np.ndarray,
    states: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Recover the integrated result for a HEX20 element."""
    element = Hex20Element(material)
    integration_points: list[dict[str, object]] = []
    for point_index, (point, quadrature_weight) in enumerate(
        zip(Hex20Element.integration_points, Hex20Element.integration_weights)
    ):
        b_matrix, determinant = element.b_matrix(coords, point)
        point_strain = b_matrix @ np.asarray(local_u, dtype=float)
        point_state = state_for_point(material, point_strain, states, point_index)
        point_stress = stress_from_state(point_state, material.stress_tangent(point_strain)[0])
        shape = element.shape_functions(point)
        point_result = solid_point_result(
            index=point_index,
            location="gauss",
            barycentric=list(point),
            coordinates=shape @ coords,
            weight=quadrature_weight * determinant,
            strain=point_strain,
            stress=point_stress,
            von_mises=Hex20Element.von_mises(point_stress),
            state=point_state,
        )
        point_result["natural_coordinates"] = list(point)
        point_result.update(orthotropic_fields(material, point_strain, point_stress))
        integration_points.append(point_result)
    averaged = average_solid_points(integration_points)
    averaged.update(orthotropic_fields(material, np.asarray(averaged["strain"]), np.asarray(averaged["stress"])))
    return {
        "element": index,
        "type": element_type,
        "location": "integration_average",
        **averaged,
        "von_mises": Hex20Element.von_mises(np.asarray(averaged["stress"])),
        "integration_points": integration_points,
        "nodal_results": solid_nodal_results(
            coords,
            nodes,
            averaged,
            Hex20Element.von_mises(np.asarray(averaged["stress"])),
            "volume_weighted_gauss_average",
        ),
    }


def wedge6_result(
    index: int,
    element_type: str,
    nodes: tuple[int, ...],
    material: SolidConstitutiveMaterial,
    coords: np.ndarray,
    local_u: np.ndarray,
    states: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Recover production-rule strains and stresses for a WEDGE6 element."""
    element = Wedge6Element(material)
    integration_points: list[dict[str, object]] = []
    for point_index, (point, quadrature_weight, b_matrix, determinant) in enumerate(
        element.integration_data(coords)
    ):
        point_strain = b_matrix @ np.asarray(local_u, dtype=float)
        point_state = state_for_point(material, point_strain, states, point_index)
        point_stress = stress_from_state(point_state, material.stress_tangent(point_strain)[0])
        shape = element.shape_functions(point)
        point_result = solid_point_result(
            index=point_index,
            location="gauss",
            barycentric=list(point),
            coordinates=shape @ np.asarray(coords, dtype=float),
            weight=quadrature_weight * determinant,
            strain=point_strain,
            stress=point_stress,
            von_mises=element.von_mises(point_stress),
            state=point_state,
        )
        point_result["natural_coordinates"] = list(point)
        point_result.update(orthotropic_fields(material, point_strain, point_stress))
        integration_points.append(point_result)
    averaged = average_solid_points(integration_points)
    averaged.update(orthotropic_fields(material, np.asarray(averaged["strain"]), np.asarray(averaged["stress"])))
    averaged_stress = np.asarray(averaged["stress"], dtype=float)
    strain_energy = float(
        sum(
            0.5
            * float(np.asarray(point["strain"], dtype=float) @ np.asarray(point["stress"], dtype=float))
            * float(point["weight"])
            for point in integration_points
        )
    )
    return {
        "element": index,
        "type": element_type,
        "location": "integration_average",
        **averaged,
        "strain_energy": strain_energy,
        "von_mises": element.von_mises(averaged_stress),
        "integration_points": integration_points,
        "nodal_results": solid_nodal_results(
            coords,
            nodes,
            averaged,
            element.von_mises(averaged_stress),
            "volume_weighted_gauss_average",
        ),
    }


def solid_result(
    strain: np.ndarray, stress: np.ndarray, state: dict[str, object] | None = None
) -> dict[str, object]:
    strain_tensor = voigt_strain_tensor(strain)
    stress_tensor = voigt_stress_tensor(stress)
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
        "deviatoric_stress": stress_tensor_to_voigt(deviator).tolist(),
    }
    if state is not None:
        result["material_state"] = state
        for key in ("equivalent_plastic_strain", "plastic_multiplier", "yield_function", "yield_stress"):
            if key in state:
                result[key] = state[key]
        if "plastic_strain" in state:
            result["plastic_strain"] = state["plastic_strain"]
    return result


def solid_point_result(
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
        **solid_result(strain, stress, state),
        "von_mises": float(von_mises),
    }


def average_solid_points(points: list[dict[str, object]]) -> dict[str, object]:
    weights = np.asarray([float(point.get("weight", 1.0)) for point in points], dtype=float)
    if np.sum(weights) <= 0.0:
        weights = np.ones(len(points), dtype=float)
    strain = weighted_average([point["strain"] for point in points], weights)
    stress = weighted_average([point["stress"] for point in points], weights)
    result = solid_result(strain, stress)
    for key in ("equivalent_plastic_strain", "plastic_multiplier", "yield_function", "yield_stress"):
        if key in points[0]:
            result[key] = float(np.average([float(point[key]) for point in points], weights=weights))
    if "plastic_strain" in points[0]:
        result["plastic_strain"] = weighted_average(
            [point["plastic_strain"] for point in points], weights
        ).tolist()
    return result


def solid_nodal_results(
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
            **solid_state_subset(result),
        }
        row.update(material_axis_subset(result))
        rows.append(row)
    return rows


def tet10_extrapolated_nodal_results(
    element: Tet10Element,
    material: SolidConstitutiveMaterial,
    coords: np.ndarray,
    node_indices: tuple[int, ...],
    integration_points: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Recover a least-squares linear stress and strain field at TET10 nodes."""
    points = np.asarray([point["barycentric"] for point in integration_points], dtype=float)
    strains = element.extrapolate_integration_values(
        np.asarray([point["strain"] for point in integration_points], dtype=float), points
    )
    stresses = element.extrapolate_integration_values(
        np.asarray([point["stress"] for point in integration_points], dtype=float), points
    )
    recovery_method = (
        "linear_extrapolation_from_hammer"
        if len(integration_points) == Tet10Element.integration_point_count
        else "linear_barycentric_least_squares"
    )
    rows: list[dict[str, object]] = []
    for local_index, node in enumerate(node_indices):
        result = solid_result(strains[local_index], stresses[local_index])
        result.update(orthotropic_fields(material, strains[local_index], stresses[local_index]))
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


def material_state(material: SolidConstitutiveMaterial, strain: np.ndarray) -> dict[str, object] | None:
    if not hasattr(material, "internal_state"):
        return None
    return jsonable_state(material.internal_state(strain))


def state_for_point(
    material: SolidConstitutiveMaterial,
    strain: np.ndarray,
    states: list[dict[str, object]] | None,
    point_index: int,
) -> dict[str, object] | None:
    if states and point_index < len(states):
        return jsonable_state(states[point_index])
    return material_state(material, strain)


def stress_from_state(state: dict[str, object] | None, fallback: np.ndarray) -> np.ndarray:
    if state and "stress" in state:
        return np.asarray(state["stress"], dtype=float)
    return np.asarray(fallback, dtype=float)


def jsonable_state(state: dict[str, object]) -> dict[str, object]:
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


def solid_state_subset(result: dict[str, object]) -> dict[str, object]:
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


def orthotropic_fields(
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


def material_axis_subset(result: dict[str, object]) -> dict[str, object]:
    return {
        key: result[key]
        for key in ("material_strain", "material_stress", "material_orientation", "material_type")
        if key in result
    }


def weighted_average(values: list[object], weights: np.ndarray) -> np.ndarray:
    arrays = np.vstack([np.asarray(value, dtype=float).ravel() for value in values])
    return np.average(arrays, axis=0, weights=weights)


def voigt_stress_tensor(values: np.ndarray) -> np.ndarray:
    sx, sy, sz, txy, tyz, txz = np.asarray(values, dtype=float)
    return np.array([[sx, txy, txz], [txy, sy, tyz], [txz, tyz, sz]], dtype=float)


def voigt_strain_tensor(values: np.ndarray) -> np.ndarray:
    ex, ey, ez, gxy, gyz, gxz = np.asarray(values, dtype=float)
    return np.array(
        [[ex, 0.5 * gxy, 0.5 * gxz], [0.5 * gxy, ey, 0.5 * gyz], [0.5 * gxz, 0.5 * gyz, ez]],
        dtype=float,
    )


def stress_tensor_to_voigt(values: np.ndarray) -> np.ndarray:
    return np.array(
        [values[0, 0], values[1, 1], values[2, 2], values[0, 1], values[1, 2], values[0, 2]],
        dtype=float,
    )
