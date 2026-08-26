"""Stress recovery for solved models."""

from __future__ import annotations

import numpy as np

from solveur.elements.shell.mitc4 import MITC4Element, ShellMaterial

from solveur.core.dofs import DofManager
from solveur.core.material_state import MaterialStateTable
from solveur.core.model import FiniteElementModel
from solveur.elements.registry import ElementRegistry
from solveur.elements.beam.beam2 import Beam2Element
from solveur.elements.shell.mitc3 import Mitc3ShellElement
from solveur.elements.solid.tet10 import Tet10Element
from solveur.elements.solid.tet4 import Tet4Element
from solveur.elements.solid.total_lagrangian_j2 import (
    TotalLagrangianJ2Hex8Element,
    TotalLagrangianJ2Hex20Element,
    TotalLagrangianJ2Tet10Element,
    TotalLagrangianJ2Tet4Element,
)
from solveur.materials.factory import MaterialFactory
from solveur.materials.beam import BeamSectionMaterial
from solveur.materials.laminate import LaminateShellMaterial
from solveur.materials.orthotropic import OrthotropicSolidMaterial
from solveur.materials.solid import SolidConstitutiveMaterial
from solveur.post.shell_results import (
    average_contributions as _average_contributions,
    laminate_failure_summary as _laminate_failure_summary,
    laminate_outer_faces as _laminate_outer_faces,
    laminate_ply_results as _laminate_ply_results,
    laminate_section_results as _laminate_section_results,
    shell_face_results as _shell_face_results,
    shell_nodal_results as _shell_nodal_results,
)
from solveur.post.solid_results import hex8_result as _hex8_result
from solveur.post.solid_results import hex20_result as _hex20_result


class StressPostProcessor:
    """Recover element strains and stresses where implemented."""

    def element_results(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        displacement: np.ndarray,
        material_states: MaterialStateTable | None = None,
    ) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        for index, definition in enumerate(model.elements):
            spec = ElementRegistry.get(definition.type)
            edofs = []
            for node in definition.nodes:
                edofs.extend(dofs.node_indices(node, spec.dofs))
            local_u = displacement[edofs]
            coords = model.nodes[list(definition.nodes)]
            material = MaterialFactory.create(model.materials[definition.material], coordinates=coords)
            states = (material_states or {}).get(index)
            if (
                str(model.analysis.parameters.get("kinematics", "small_strain")).lower()
                == "total_lagrangian_j2"
                and definition.type in {"TET4", "TET10", "HEX8", "HEX20"}
                and isinstance(material, SolidConstitutiveMaterial)
            ):
                results.append(
                    self._total_lagrangian_j2_result(
                        index,
                        definition.type,
                        definition.nodes,
                        material,
                        coords,
                        local_u,
                        states,
                        nonlinear_quadrature=str(
                            model.analysis.parameters.get("tet10_nonlinear_quadrature", "hammer4")
                        ),
                    )
                )
            elif definition.type == "TET4" and isinstance(material, SolidConstitutiveMaterial):
                results.append(
                    self._tet4_result(index, definition.type, definition.nodes, material, coords, local_u, states)
                )
            elif definition.type == "TET10" and isinstance(material, SolidConstitutiveMaterial):
                results.append(
                    self._tet10_result(
                        index,
                        definition.type,
                        definition.nodes,
                        material,
                        coords,
                        local_u,
                        states,
                        nonlinear_quadrature=str(
                            model.analysis.parameters.get("tet10_nonlinear_quadrature", "hammer4")
                        ),
                    )
                )
            elif definition.type == "HEX8" and isinstance(material, SolidConstitutiveMaterial):
                results.append(
                    _hex8_result(index, definition.type, definition.nodes, material, coords, local_u, states)
                )
            elif definition.type == "HEX20" and isinstance(material, SolidConstitutiveMaterial):
                results.append(
                    _hex20_result(index, definition.type, definition.nodes, material, coords, local_u, states)
                )
            elif definition.type == "MITC4" and isinstance(material, ShellMaterial):
                results.append(self._mitc4_result(index, definition.type, definition.nodes, material, coords, local_u))
            elif definition.type == "MITC4" and isinstance(material, LaminateShellMaterial):
                results.append(self._mitc4_result(index, definition.type, definition.nodes, material, coords, local_u))
            elif definition.type == "MITC3" and isinstance(material, (ShellMaterial, LaminateShellMaterial)):
                results.append(self._mitc3_result(index, definition.type, definition.nodes, material, coords, local_u))
            elif definition.type == "BEAM2" and isinstance(material, BeamSectionMaterial):
                results.append(self._beam2_result(index, definition.type, definition.nodes, material, coords, local_u))
        return results

    @staticmethod
    def nodal_results(model: FiniteElementModel, element_results: list[dict[str, object]]) -> list[dict[str, object]]:
        """Average element-side recovered quantities onto connected nodes."""
        contributions: dict[int, list[dict[str, object]]] = {node: [] for node in range(model.node_count)}
        for result in element_results:
            for item in result.get("nodal_results", []):
                if isinstance(item, dict) and "node" in item:
                    contributions[int(item["node"])].append(item)
        rows: list[dict[str, object]] = []
        for node in range(model.node_count):
            node_contributions = contributions[node]
            if not node_contributions:
                continue
            row = _average_contributions(node, node_contributions)
            row["x"], row["y"], row["z"] = [float(value) for value in model.nodes[node]]
            rows.append(row)
        return rows

    @staticmethod
    def _total_lagrangian_j2_result(
        index: int,
        element_type: str,
        nodes: tuple[int, ...],
        material: SolidConstitutiveMaterial,
        coords: np.ndarray,
        local_u: np.ndarray,
        states: list[dict[str, object]] | None,
        *,
        nonlinear_quadrature: str = "hammer4",
    ) -> dict[str, object]:
        """Recover objective Green-Lagrange/J2 fields for the research path."""
        element_class = {
            "TET4": TotalLagrangianJ2Tet4Element,
            "TET10": TotalLagrangianJ2Tet10Element,
            "HEX8": TotalLagrangianJ2Hex8Element,
            "HEX20": TotalLagrangianJ2Hex20Element,
        }[element_type]
        if element_type == "TET10":
            element = element_class(
                material,
                nonlinear_quadrature=nonlinear_quadrature,
            )
        else:
            element = element_class(material)
        raw_points = element.integration_point_results(coords, local_u, states)
        points: list[dict[str, object]] = []
        for raw in raw_points:
            stress = np.asarray(raw["stress"], dtype=float)
            strain = np.asarray(raw["strain"], dtype=float)
            state = raw.get("material_state")
            state_dict = state if isinstance(state, dict) else None
            points.append(
                _solid_point_result(
                    index=int(raw["index"]),
                    location="gauss",
                    barycentric=[],
                    coordinates=np.mean(coords, axis=0),
                    weight=float(raw["weight"]),
                    strain=strain,
                    stress=stress,
                    von_mises=Tet4Element.von_mises(stress),
                    state=state_dict,
                )
            )
            points[-1].update(
                {
                    "deformation_gradient": raw["deformation_gradient"],
                    "green_lagrange_strain": raw["green_lagrange_strain"],
                    "second_piola_stress": raw["second_piola_stress"],
                    "cauchy_stress": raw["cauchy_stress"],
                    "det_f": raw["det_f"],
                }
            )
        weights = np.asarray([float(point["weight"]) for point in points], dtype=float)
        normalized = weights / max(float(np.sum(weights)), np.finfo(float).eps)
        strain = sum(normalized[i] * np.asarray(point["strain"], dtype=float) for i, point in enumerate(points))
        stress = sum(normalized[i] * np.asarray(point["stress"], dtype=float) for i, point in enumerate(points))
        aggregate_state: dict[str, object] = {
            "model": "total_lagrangian_j2_green_lagrange",
            "kinematics": "green_lagrange_second_piola",
            "equivalent_plastic_strain": float(
                sum(normalized[i] * float(point.get("equivalent_plastic_strain", 0.0)) for i, point in enumerate(points))
            ),
        }
        result = _solid_result(strain, stress, aggregate_state)
        result["kinematics"] = "green_lagrange_second_piola"
        result["von_mises"] = Tet4Element.von_mises(stress)
        return {
            "element": index,
            "type": f"{element_type}_TOTAL_LAGRANGIAN_J2",
            "location": "integration_average",
            **result,
            "integration_points": points,
            "nodal_results": _solid_nodal_results(
                coords, nodes, result, float(result["von_mises"]), "total_lagrangian_j2_average"
            ),
        }

    @staticmethod
    def _tet4_result(
        index: int,
        element_type: str,
        nodes: tuple[int, ...],
        material: SolidConstitutiveMaterial,
        coords: np.ndarray,
        local_u: np.ndarray,
        states: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        element = Tet4Element(material)
        strain = element.strain(coords, local_u)
        state = _state_for_point(material, strain, states, 0)
        stress = _stress_from_state(state, element.stress(coords, local_u))
        result = _solid_result(strain, stress, state)
        result.update(_orthotropic_fields(material, strain, stress))
        point_result = _solid_point_result(
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
        point_result.update(_orthotropic_fields(material, strain, stress))
        integration_points = [point_result]
        return {
            "element": index,
            "type": element_type,
            **result,
            "von_mises": Tet4Element.von_mises(stress),
            "integration_points": integration_points,
            "nodal_results": _solid_nodal_results(
                coords, nodes, result, Tet4Element.von_mises(stress), "constant_strain"
            ),
        }

    @staticmethod
    def _tet10_result(
        index: int,
        element_type: str,
        nodes: tuple[int, ...],
        material: SolidConstitutiveMaterial,
        coords: np.ndarray,
        local_u: np.ndarray,
        states: list[dict[str, object]] | None = None,
        nonlinear_quadrature: str = "hammer4",
    ) -> dict[str, object]:
        element = Tet10Element(material, nonlinear_quadrature=nonlinear_quadrature)
        strain = element.strain(coords, local_u)
        stress = element.stress(coords, local_u)
        state = _material_state(material, strain)
        integration_points = []
        if states:
            quadrature = element.nonlinear_integration_rule()
            quadrature_name = element.nonlinear_quadrature
        else:
            quadrature = element.stiffness_integration_rule(coords)
            quadrature_name = "hammer" if len(quadrature) == 4 else "duffy_4"
        for point_index, (point, weight) in enumerate(quadrature):
            b_matrix, det_j = Tet10Element.b_matrix(coords, point)
            point_strain = b_matrix @ np.asarray(local_u, dtype=float)
            point_state = _state_for_point(material, point_strain, states, point_index)
            point_stress = _stress_from_state(point_state, material.stress_tangent(point_strain)[0])
            shape = Tet10Element.shape_functions(point)
            point_result = _solid_point_result(
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
            point_result.update(_orthotropic_fields(material, point_strain, point_stress))
            integration_points.append(point_result)
        averaged_result = _average_solid_points(integration_points)
        if states:
            result = averaged_result
            result["material_state"] = {
                "model": str(integration_points[0].get("material_state", {}).get("model", "path_dependent")),
                "source": "committed_integration_point_average",
            }
            result_stress = np.asarray(result["stress"], dtype=float)
            location = "integration_average"
        else:
            result = _solid_result(strain, stress, state)
            result_stress = stress
            location = "center"
        result.update(_orthotropic_fields(material, np.asarray(result["strain"]), result_stress))
        if states:
            nodal_results = _solid_nodal_results(
                coords,
                nodes,
                averaged_result,
                float(np.mean([point["von_mises"] for point in integration_points])),
                "integration_average",
            )
        else:
            nodal_results = _tet10_extrapolated_nodal_results(element, material, coords, nodes, integration_points)
        return {
            "element": index,
            "type": element_type,
            "location": location,
            **result,
            "von_mises": Tet10Element.von_mises(result_stress),
            "integration_points": integration_points,
            "nodal_results": nodal_results,
        }

    @staticmethod
    def _mitc4_result(
        index: int,
        element_type: str,
        nodes: tuple[int, ...],
        material: ShellMaterial | LaminateShellMaterial,
        coords: np.ndarray,
        global_u: np.ndarray,
    ) -> dict[str, object]:
        element = MITC4Element(material)
        frame, coords_2d = element.project_to_local_midplane(coords)
        source_material = material
        if isinstance(material, LaminateShellMaterial):
            material = material.oriented_for_frame(frame)
        transform = element.transform_dofs(frame)
        local_u = transform @ np.asarray(global_u, dtype=float)
        tying = element.shear_tying_vectors(coords_2d)
        strains = element.strain_matrices_local(coords_2d, 0.0, 0.0, tying)
        membrane_strain = strains.Bm @ local_u
        curvature = strains.Bb @ local_u
        shear_strain = strains.Bs @ local_u
        coupling = getattr(material, "coupling_matrix", np.zeros((3, 3), dtype=float))
        membrane_force = material.membrane_matrix @ membrane_strain + coupling @ curvature
        bending_moment = coupling.T @ membrane_strain + material.bending_matrix @ curvature
        shear_force = material.shear_matrix @ shear_strain
        if isinstance(material, LaminateShellMaterial):
            ply_results = _laminate_ply_results(material, membrane_strain, curvature)
            shell_faces = _laminate_outer_faces(ply_results)
        else:
            ply_results = []
            shell_faces = _shell_face_results(material, membrane_strain, curvature)
        center_point: dict[str, object] = {
            "index": 0,
            "location": "center",
            "natural_coordinates": [0.0, 0.0],
            "coordinates": np.mean(coords, axis=0).tolist(),
            "weight": 4.0,
            "membrane_strain": membrane_strain.tolist(),
            "curvature": curvature.tolist(),
            "shear_strain": shear_strain.tolist(),
            "membrane_force": membrane_force.tolist(),
            "bending_moment": bending_moment.tolist(),
            "shear_force": shear_force.tolist(),
            "shell_faces": shell_faces,
        }
        result: dict[str, object] = {
            "element": index,
            "type": element_type,
            "location": "center",
            "local_frame": frame.tolist(),
            "membrane_strain": membrane_strain.tolist(),
            "curvature": curvature.tolist(),
            "shear_strain": shear_strain.tolist(),
            "membrane_force": membrane_force.tolist(),
            "bending_moment": bending_moment.tolist(),
            "shear_force": shear_force.tolist(),
            "shell_faces": shell_faces,
            "integration_points": [center_point],
            "nodal_results": _shell_nodal_results(nodes, coords, membrane_strain, curvature, shear_strain, shell_faces),
        }
        if isinstance(material, LaminateShellMaterial):
            center_point["ply_results"] = ply_results
            result["ply_results"] = ply_results
            sections = _laminate_section_results(ply_results)
            center_point["shell_sections"] = sections
            result["shell_sections"] = sections
            if source_material.reference_direction is not None:
                offset = source_material.orientation_angle_deg(frame)
                result["material_reference_direction"] = source_material.reference_direction.tolist()
                result["material_angle_offset_deg"] = offset
                result["ply_directions_global"] = [
                    (
                        np.cos(np.deg2rad(ply.angle_deg)) * frame[0] + np.sin(np.deg2rad(ply.angle_deg)) * frame[1]
                    ).tolist()
                    for ply in material.laminate.plies
                ]
            failure_summary = _laminate_failure_summary(ply_results)
            if failure_summary is not None:
                center_point["failure_summary"] = failure_summary
                result["failure_summary"] = failure_summary
        return result

    @staticmethod
    def _mitc3_result(
        index: int,
        element_type: str,
        nodes: tuple[int, ...],
        material: ShellMaterial | LaminateShellMaterial,
        coords: np.ndarray,
        global_u: np.ndarray,
    ) -> dict[str, object]:
        element = Mitc3ShellElement(material)
        frame, _ = element.project_to_local_midplane(coords)
        source_material = material
        if isinstance(material, LaminateShellMaterial):
            material = material.oriented_for_frame(frame)
        strains = element.generalized_strains(coords, global_u)
        membrane_strain = strains["membrane"]
        curvature = strains["curvature"]
        shear_strain = strains["shear"]
        coupling = getattr(material, "coupling_matrix", np.zeros((3, 3), dtype=float))
        membrane_force = material.membrane_matrix @ membrane_strain + coupling @ curvature
        bending_moment = coupling.T @ membrane_strain + material.bending_matrix @ curvature
        shear_force = material.shear_matrix @ shear_strain
        if isinstance(material, LaminateShellMaterial):
            ply_results = _laminate_ply_results(material, membrane_strain, curvature)
            shell_faces = _laminate_outer_faces(ply_results)
        else:
            ply_results = []
            shell_faces = _shell_face_results(material, membrane_strain, curvature)
        center_point: dict[str, object] = {
            "index": 0,
            "location": "centroid",
            "natural_coordinates": [1.0 / 3.0, 1.0 / 3.0],
            "coordinates": np.mean(coords, axis=0).tolist(),
            "weight": 0.5,
            "membrane_strain": membrane_strain.tolist(),
            "curvature": curvature.tolist(),
            "shear_strain": shear_strain.tolist(),
            "membrane_force": membrane_force.tolist(),
            "bending_moment": bending_moment.tolist(),
            "shear_force": shear_force.tolist(),
            "shell_faces": shell_faces,
        }
        result: dict[str, object] = {
            "element": index,
            "type": element_type,
            "location": "centroid",
            "local_frame": frame.tolist(),
            "membrane_strain": membrane_strain.tolist(),
            "curvature": curvature.tolist(),
            "shear_strain": shear_strain.tolist(),
            "drilling_strain": strains["drilling"].tolist(),
            "membrane_force": membrane_force.tolist(),
            "bending_moment": bending_moment.tolist(),
            "shear_force": shear_force.tolist(),
            "shell_faces": shell_faces,
            "integration_points": [center_point],
            "nodal_results": _shell_nodal_results(
                nodes, coords, membrane_strain, curvature, shear_strain, shell_faces
            ),
        }
        if isinstance(material, LaminateShellMaterial):
            center_point["ply_results"] = ply_results
            result["ply_results"] = ply_results
            sections = _laminate_section_results(ply_results)
            center_point["shell_sections"] = sections
            result["shell_sections"] = sections
            if source_material.reference_direction is not None:
                offset = source_material.orientation_angle_deg(frame)
                result["material_reference_direction"] = source_material.reference_direction.tolist()
                result["material_angle_offset_deg"] = offset
                result["ply_directions_global"] = [
                    (
                        np.cos(np.deg2rad(ply.angle_deg)) * frame[0]
                        + np.sin(np.deg2rad(ply.angle_deg)) * frame[1]
                    ).tolist()
                    for ply in material.laminate.plies
                ]
            failure_summary = _laminate_failure_summary(ply_results)
            if failure_summary is not None:
                center_point["failure_summary"] = failure_summary
                result["failure_summary"] = failure_summary
        return result

    @staticmethod
    def _beam2_result(
        index: int,
        element_type: str,
        nodes: tuple[int, ...],
        material: BeamSectionMaterial,
        coords: np.ndarray,
        global_u: np.ndarray,
    ) -> dict[str, object]:
        response = Beam2Element(material).response(coords, global_u)
        return {
            "element": index,
            "type": element_type,
            "nodes": [int(node) for node in nodes],
            "location": "element_local",
            **response,
        }


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
