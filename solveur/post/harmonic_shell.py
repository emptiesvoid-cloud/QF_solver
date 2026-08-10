"""Complex MITC3/MITC4 stress recovery for harmonic frequency responses."""

from __future__ import annotations

from typing import Any

import numpy as np

from mitc4.element import MITC4Element
from mitc4.material import ShellMaterial

from solveur.core.dofs import DofManager
from solveur.core.model import FiniteElementModel
from solveur.elements.registry import ElementRegistry
from solveur.elements.shell.mitc3 import Mitc3ShellElement
from solveur.materials.factory import MaterialFactory
from solveur.materials.laminate import LaminateShellMaterial


NATURAL_NODE_COORDINATES = ((-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0))
MITC3_NATURAL_NODE_COORDINATES = ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))
STRESS_COMPONENTS = ("S11", "S22", "S12")
ShellLikeMaterial = ShellMaterial | LaminateShellMaterial


class HarmonicShellStressPostProcessor:
    """Recover complex local shell stresses without discarding phase."""

    def frequency_results(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        frequencies_hz: np.ndarray,
        responses: list[np.ndarray],
    ) -> list[dict[str, Any]]:
        """Return element-center face stresses for every solved frequency."""
        if not any(definition.type in {"MITC3", "MITC4"} for definition in model.elements):
            return []
        return [
            {
                "index": index,
                "frequency_hz": float(frequency),
                **self._element_results(model, dofs, response),
            }
            for index, (frequency, response) in enumerate(
                zip(frequencies_hz, responses, strict=True)
            )
        ]

    def averaged_nodal_stress(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        response: np.ndarray,
        node: int,
        *,
        face: str = "top",
    ) -> np.ndarray:
        """Average complex nodal stress from coplanar adjacent shell facets."""
        if face not in {"top", "bottom"}:
            raise ValueError("Shell face must be 'top' or 'bottom'.")
        contributions: list[np.ndarray] = []
        reference_frame: np.ndarray | None = None
        for definition in model.elements:
            if definition.type not in {"MITC3", "MITC4"} or node not in definition.nodes:
                continue
            material = MaterialFactory.create(model.materials[definition.material])
            if not isinstance(material, (ShellMaterial, LaminateShellMaterial)):
                continue
            element, frame, coords_2d, local_u, global_u, coords = _local_state(
                model,
                dofs,
                response,
                definition.nodes,
                material,
                definition.type,
            )
            if reference_frame is None:
                reference_frame = frame
            elif not np.allclose(frame, reference_frame, rtol=0.0, atol=1.0e-8):
                raise ValueError(
                    "Nodal averaging of local shell stresses requires aligned adjacent frames."
                )
            local_node = definition.nodes.index(node)
            natural = (
                MITC3_NATURAL_NODE_COORDINATES
                if definition.type == "MITC3"
                else NATURAL_NODE_COORDINATES
            )
            xi, eta = natural[local_node]
            contributions.append(
                _face_stress(
                    element,
                    material,
                    coords,
                    coords_2d,
                    global_u,
                    local_u,
                    xi,
                    eta,
                    face,
                )
            )
        if not contributions:
            raise ValueError(f"Node {node} has no adjacent supported shell element.")
        return np.mean(np.asarray(contributions, dtype=complex), axis=0)

    def _element_results(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        response: np.ndarray,
    ) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        peak: dict[str, Any] = {
            "amplitude": 0.0,
            "element": None,
            "face": None,
            "component": None,
            "phase_degrees": 0.0,
        }
        for index, definition in enumerate(model.elements):
            if definition.type not in {"MITC3", "MITC4"}:
                continue
            material = MaterialFactory.create(model.materials[definition.material])
            if not isinstance(material, (ShellMaterial, LaminateShellMaterial)):
                continue
            element, frame, coords_2d, local_u, global_u, coords = _local_state(
                model,
                dofs,
                response,
                definition.nodes,
                material,
                definition.type,
            )
            faces = []
            ply_results: list[dict[str, Any]] = []
            for face in ("bottom", "top"):
                natural_center = (1.0 / 3.0, 1.0 / 3.0) if definition.type == "MITC3" else (0.0, 0.0)
                stress = _face_stress(
                    element,
                    material,
                    coords,
                    coords_2d,
                    global_u,
                    local_u,
                    *natural_center,
                    face,
                )
                encoded = _complex_vector(stress)
                faces.append({"face": face, "stress": encoded})
                amplitudes = np.abs(stress)
                component_index = int(np.argmax(amplitudes))
                amplitude = float(amplitudes[component_index])
                if amplitude > float(peak["amplitude"]):
                    peak = {
                        "amplitude": amplitude,
                        "element": index,
                        "face": face,
                        "component": STRESS_COMPONENTS[component_index],
                        "phase_degrees": float(np.degrees(np.angle(stress[component_index]))),
                    }
            if isinstance(material, LaminateShellMaterial):
                membrane_strain, curvature = _generalized_strains(
                    element,
                    coords,
                    coords_2d,
                    global_u,
                    local_u,
                    *natural_center,
                )
                ply_results = _complex_ply_results(material, membrane_strain, curvature)
            rows.append(
                {
                    "element": index,
                    "location": "center",
                    "local_frame": frame.tolist(),
                    "shell_faces": faces,
                    "ply_results": ply_results,
                }
            )
        return {"element_results": rows, "peak_component": peak}


def _local_state(
    model: FiniteElementModel,
    dofs: DofManager,
    response: np.ndarray,
    nodes: tuple[int, ...],
    material: ShellLikeMaterial,
    element_type: str,
) -> tuple[object, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    element = Mitc3ShellElement(material) if element_type == "MITC3" else MITC4Element(material)
    coords = model.nodes[list(nodes)]
    frame, coords_2d = element.project_to_local_midplane(coords)
    if isinstance(material, LaminateShellMaterial):
        material = material.oriented_for_frame(frame)
        element = Mitc3ShellElement(material) if element_type == "MITC3" else MITC4Element(material)
    transform = element.transform_dofs(frame)
    spec = ElementRegistry.get(element_type)
    element_dofs: list[int] = []
    for node in nodes:
        element_dofs.extend(dofs.node_indices(node, spec.dofs))
    global_u = np.asarray(response[element_dofs], dtype=complex)
    local_u = transform @ global_u
    return element, frame, coords_2d, local_u, global_u, coords


def _face_stress(
    element: object,
    material: ShellLikeMaterial,
    coords_3d: np.ndarray,
    coords_2d: np.ndarray,
    global_u: np.ndarray,
    local_u: np.ndarray,
    xi: float,
    eta: float,
    face: str,
) -> np.ndarray:
    membrane_strain, curvature = _generalized_strains(
        element,
        coords_3d,
        coords_2d,
        global_u,
        local_u,
        xi,
        eta,
    )
    if isinstance(material, LaminateShellMaterial):
        ply_results = _complex_ply_results(material, membrane_strain, curvature)
        ply_index = len(material.laminate.plies) - 1 if face == "top" else 0
        location = "upper" if face == "top" else "lower"
        point = next(
            item
            for item in ply_results
            if item["ply_index"] == ply_index and item["location"] == location
        )
        return _decode_complex_vector(point["stress_element"])
    z = 0.5 * material.t if face == "top" else -0.5 * material.t
    return (material.membrane_matrix / material.t) @ (membrane_strain + z * curvature)


def _generalized_strains(
    element: object,
    coords_3d: np.ndarray,
    coords_2d: np.ndarray,
    global_u: np.ndarray,
    local_u: np.ndarray,
    xi: float,
    eta: float,
) -> tuple[np.ndarray, np.ndarray]:
    if isinstance(element, Mitc3ShellElement):
        strains = element.generalized_strains(coords_3d, global_u, xi, eta)
        return strains["membrane"], strains["curvature"]
    if isinstance(element, MITC4Element):
        tying = element.shear_tying_vectors(coords_2d)
        matrices = element.strain_matrices_local(coords_2d, xi, eta, tying)
        return matrices.Bm @ local_u, matrices.Bb @ local_u
    raise TypeError("Unsupported shell element for harmonic stress recovery.")


def _complex_ply_results(
    material: LaminateShellMaterial,
    membrane_strain: np.ndarray,
    curvature: np.ndarray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    interfaces = material.laminate.interfaces
    for index, ply in enumerate(material.laminate.plies):
        lower = float(interfaces[index])
        upper = float(interfaces[index + 1])
        for location, z in (
            ("lower", lower),
            ("middle", 0.5 * (lower + upper)),
            ("upper", upper),
        ):
            strain_element = membrane_strain + z * curvature
            strain_material = _complex_strain_in_material_axes(strain_element, ply.angle_deg)
            stress_element = ply.transformed_stiffness @ strain_element
            stress_material = ply.material.reduced_stiffness @ strain_material
            rows.append(
                {
                    "ply_index": index,
                    "ply_name": ply.name,
                    "location": location,
                    "z": z,
                    "strain_element": _complex_vector(strain_element),
                    "stress_element": _complex_vector(stress_element),
                    "strain_material": _complex_vector(strain_material),
                    "stress_material": _complex_vector(stress_material),
                }
            )
    return rows


def _complex_vector(values: np.ndarray) -> dict[str, list[float]]:
    vector = np.asarray(values, dtype=complex)
    return {
        "real": vector.real.tolist(),
        "imag": vector.imag.tolist(),
        "amplitude": np.abs(vector).tolist(),
        "phase_degrees": np.degrees(np.angle(vector)).tolist(),
    }


def _decode_complex_vector(values: dict[str, list[float]]) -> np.ndarray:
    return np.asarray(values["real"], dtype=float) + 1j * np.asarray(values["imag"], dtype=float)


def _complex_strain_in_material_axes(strain: np.ndarray, angle_deg: float) -> np.ndarray:
    values = np.asarray(strain, dtype=complex)
    angle = np.deg2rad(float(angle_deg))
    transform = np.array(
        [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]],
        dtype=float,
    )
    tensor = np.array(
        [[values[0], 0.5 * values[2]], [0.5 * values[2], values[1]]],
        dtype=complex,
    )
    rotated = transform.T @ tensor @ transform
    return np.array(
        [rotated[0, 0], rotated[1, 1], 2.0 * rotated[0, 1]],
        dtype=complex,
    )
