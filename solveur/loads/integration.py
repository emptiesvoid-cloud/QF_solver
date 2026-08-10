"""Consistent finite element integration of distributed mechanical loads."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from mitc4.element import MITC4Element
from mitc4.material import ShellMaterial

from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.elements.registry import ElementRegistry
from solveur.elements.beam.beam2 import Beam2Element
from solveur.elements.shell.mitc3 import Mitc3ShellElement
from solveur.elements.solid.quadrature import tetra_duffy_rule, triangle_duffy_rule, triangle_shape_functions
from solveur.elements.solid.tet4 import Tet4Element
from solveur.elements.solid.tet10 import Tet10Element
from solveur.loads.entities import BodyLoad, DistributedLoad, EdgeLoad, GravityLoad, LineLoad, SurfaceLoad
from solveur.materials.factory import MaterialFactory
from solveur.materials.laminate import LaminateShellMaterial
from solveur.mesh.topology import MITC3_EDGES, MITC4_EDGES, TET10_FACES, TET4_FACES

@dataclass(frozen=True)
class IntegratedLoad:
    """One assembled distributed load and its global balance."""

    vector: np.ndarray
    details: dict[str, object]


@dataclass(frozen=True)
class SparseIntegratedLoad:
    """Sparse contribution of one distributed load."""

    indices: np.ndarray
    values: np.ndarray
    details: dict[str, object]


class DistributedLoadIntegrator:
    """Integrate typed loads and scatter them through the global dof map."""

    def integrate(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        load: DistributedLoad,
        index: int,
    ) -> IntegratedLoad:
        sparse = self.integrate_sparse(model, dofs, load, index)
        vector = np.zeros(dofs.ndof, dtype=float)
        vector[sparse.indices] = sparse.values
        return IntegratedLoad(vector, sparse.details)

    def integrate_sparse(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        load: DistributedLoad,
        index: int,
    ) -> SparseIntegratedLoad:
        """Integrate a load without allocating a global dense vector."""
        contributions: list[tuple[int, np.ndarray]] = []
        if isinstance(load, (GravityLoad, BodyLoad)):
            element_indices = load.elements if load.elements is not None else tuple(range(len(model.elements)))
            for element_index in element_indices:
                local = self._body_vector(model, element_index, load)
                contributions.append((element_index, local))
        elif isinstance(load, SurfaceLoad):
            local = self._surface_vector(model, load)
            contributions.append((load.element, local))
            element_indices = (load.element,)
        elif isinstance(load, EdgeLoad):
            local = self._edge_vector(model, load)
            contributions.append((load.element, local))
            element_indices = (load.element,)
        elif isinstance(load, LineLoad):
            local = self._line_vector(model, load)
            contributions.append((load.element, local))
            element_indices = (load.element,)
        else:
            raise InputValidationError(f"Unsupported distributed load {type(load).__name__}.")
        indices, values = self._merge_contributions(model, dofs, contributions)
        resultant = np.zeros(3, dtype=float)
        moment = np.zeros(3, dtype=float)
        for element_index, local in contributions:
            local_resultant, local_moment = self._local_balance(model, element_index, local)
            resultant += local_resultant
            moment += local_moment
        details = {
            "index": index,
            "type": load.type,
            "element_indices": list(element_indices),
            "resultant": resultant.tolist(),
            "moment_about_origin": moment.tolist(),
            "vector_norm": float(np.linalg.norm(values)),
            "nonzero_dof_count": _significant_entry_count(values),
        }
        return SparseIntegratedLoad(indices, values, details)

    def _body_vector(
        self,
        model: FiniteElementModel,
        element_index: int,
        load: GravityLoad | BodyLoad,
    ) -> np.ndarray:
        definition = model.elements[element_index]
        material = MaterialFactory.create(model.materials[definition.material])
        coords = model.nodes[list(definition.nodes)]
        if isinstance(load, GravityLoad):
            density = float(getattr(material, "density", 0.0))
            if density <= 0.0:
                raise InputValidationError(
                    f"Gravity load requires positive density on element {element_index} ({definition.type})."
                )
            force_density = density * np.asarray(load.acceleration, dtype=float)
        else:
            force_density = np.asarray(load.value, dtype=float)
            if load.coordinate_system == "local":
                if definition.type not in {"MITC3", "MITC4"}:
                    raise InputValidationError("Local body_force coordinates are supported for shell elements only.")
                frame = (
                    Mitc3ShellElement.local_frame(coords)
                    if definition.type == "MITC3"
                    else MITC4Element.local_frame(coords)
                )
                force_density = frame.T @ force_density
        if definition.type == "TET4":
            volume = Tet4Element.signed_volume(coords)
            return np.tile(force_density * volume / 4.0, 4)
        if definition.type == "TET10":
            return _tet10_body_vector(coords, force_density)
        if definition.type == "MITC4" and isinstance(material, (ShellMaterial, LaminateShellMaterial)):
            return _mitc4_surface_vector(coords, force_density * material.t, pressure=None)
        if definition.type == "MITC3" and isinstance(material, (ShellMaterial, LaminateShellMaterial)):
            return _mitc3_surface_vector(coords, force_density * material.t, pressure=None)
        raise InputValidationError(f"Body loads are unsupported for element {definition.type}.")

    @staticmethod
    def _surface_vector(model: FiniteElementModel, load: SurfaceLoad) -> np.ndarray:
        definition = model.elements[load.element]
        coords = model.nodes[list(definition.nodes)]
        pressure = float(load.value) if load.kind == "pressure" else None
        traction = None if pressure is not None else np.asarray(load.value, dtype=float)
        if definition.type == "TET4":
            return _solid_face_vector(coords, TET4_FACES[int(load.face)], traction, pressure, load.coordinate_system)
        if definition.type == "TET10":
            return _solid_face_vector(coords, TET10_FACES[int(load.face)], traction, pressure, load.coordinate_system)
        if definition.type == "MITC4":
            if traction is not None and load.coordinate_system == "local":
                traction = MITC4Element.local_frame(coords).T @ traction
            return _mitc4_surface_vector(coords, traction, pressure)
        if definition.type == "MITC3":
            if traction is not None and load.coordinate_system == "local":
                traction = Mitc3ShellElement.local_frame(coords).T @ traction
            return _mitc3_surface_vector(coords, traction, pressure)
        raise InputValidationError(f"Surface loads are unsupported for element {definition.type}.")

    @staticmethod
    def _edge_vector(model: FiniteElementModel, load: EdgeLoad) -> np.ndarray:
        definition = model.elements[load.element]
        if definition.type not in {"MITC3", "MITC4"}:
            raise InputValidationError("edge_traction is supported for shell elements only.")
        coords = model.nodes[list(definition.nodes)]
        traction = np.asarray(load.value, dtype=float)
        if load.coordinate_system == "local":
            frame = (
                Mitc3ShellElement.local_frame(coords)
                if definition.type == "MITC3"
                else MITC4Element.local_frame(coords)
            )
            traction = frame.T @ traction
        edges = MITC3_EDGES if definition.type == "MITC3" else MITC4_EDGES
        first, second = edges[load.edge]
        length = float(np.linalg.norm(coords[second] - coords[first]))
        local = np.zeros(len(definition.nodes) * 6, dtype=float)
        local[6 * first : 6 * first + 3] = 0.5 * length * traction
        local[6 * second : 6 * second + 3] = 0.5 * length * traction
        return local

    @staticmethod
    def _line_vector(model: FiniteElementModel, load: LineLoad) -> np.ndarray:
        definition = model.elements[load.element]
        if definition.type != "BEAM2":
            raise InputValidationError("line_load is supported for BEAM2 only.")
        coords = model.nodes[list(definition.nodes)]
        material = MaterialFactory.create(model.materials[definition.material], coordinates=coords)
        element = Beam2Element(material)
        length = element.length(coords)
        traction = np.asarray(load.value, dtype=float)
        rotation = element.local_frame(coords)
        local_traction = traction if load.coordinate_system == "local" else rotation @ traction
        qx, qy, qz = local_traction
        local = np.zeros(12, dtype=float)
        local[[0, 6]] = 0.5 * length * qx
        local[[1, 7]] = 0.5 * length * qy
        local[[2, 8]] = 0.5 * length * qz
        local[5] = qy * length**2 / 12.0
        local[11] = -local[5]
        local[4] = -qz * length**2 / 12.0
        local[10] = -local[4]
        return element.transformation(coords).T @ local

    @staticmethod
    def _scatter(
        model: FiniteElementModel,
        dofs: DofManager,
        element_index: int,
        local: np.ndarray,
        global_vector: np.ndarray,
    ) -> None:
        definition = model.elements[element_index]
        spec = ElementRegistry.get(definition.type)
        indices = [index for node in definition.nodes for index in dofs.node_indices(node, spec.dofs)]
        global_vector[np.asarray(indices, dtype=int)] += local

    @staticmethod
    def _merge_contributions(
        model: FiniteElementModel,
        dofs: DofManager,
        contributions: list[tuple[int, np.ndarray]],
    ) -> tuple[np.ndarray, np.ndarray]:
        raw_indices = []
        raw_values = []
        for element_index, local in contributions:
            definition = model.elements[element_index]
            spec = ElementRegistry.get(definition.type)
            indices = [
                index
                for node in definition.nodes
                for index in dofs.node_indices(node, spec.dofs)
            ]
            raw_indices.extend(indices)
            raw_values.extend(np.asarray(local, dtype=float))
        if not raw_indices:
            return np.zeros(0, dtype=int), np.zeros(0, dtype=float)
        indices = np.asarray(raw_indices, dtype=int)
        unique, inverse = np.unique(indices, return_inverse=True)
        values = np.zeros(unique.size, dtype=float)
        np.add.at(values, inverse, np.asarray(raw_values, dtype=float))
        significant = np.abs(values) > 1.0e-30
        return unique[significant], values[significant]

    @staticmethod
    def _local_balance(
        model: FiniteElementModel,
        element_index: int,
        local: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        definition = model.elements[element_index]
        names = ElementRegistry.get(definition.type).dofs
        width = len(names)
        resultant = np.zeros(3, dtype=float)
        moment = np.zeros(3, dtype=float)
        force_names = ("UX", "UY", "UZ")
        moment_names = ("RX", "RY", "RZ")
        for local_node, node in enumerate(definition.nodes):
            block = np.asarray(local[local_node * width : (local_node + 1) * width])
            force = np.asarray(
                [block[names.index(name)] if name in names else 0.0 for name in force_names]
            )
            nodal_moment = np.asarray(
                [block[names.index(name)] if name in names else 0.0 for name in moment_names]
            )
            resultant += force
            moment += np.cross(model.nodes[node], force) + nodal_moment
        return resultant, moment


def _tet10_body_vector(coords: np.ndarray, force_density: np.ndarray) -> np.ndarray:
    local = np.zeros(30, dtype=float)
    for point, weight in tetra_duffy_rule(5):
        shape = Tet10Element.shape_functions(point)
        derivatives = Tet10Element.shape_derivatives_reference(point)
        det_j = float(np.linalg.det(derivatives.T @ coords))
        if det_j <= 1.0e-14:
            raise InputValidationError(f"Invalid TET10 Jacobian {det_j:.6e} during body load integration.")
        for node, value in enumerate(shape):
            local[3 * node : 3 * node + 3] += weight * det_j * value * force_density
    return local


def _solid_face_vector(
    coords: np.ndarray,
    face_nodes: tuple[int, ...],
    traction: np.ndarray | None,
    pressure: float | None,
    coordinate_system: str,
) -> np.ndarray:
    local = np.zeros(coords.shape[0] * 3, dtype=float)
    face_coords = coords[list(face_nodes)]
    for barycentric, weight in triangle_duffy_rule(5):
        shape, derivatives = triangle_shape_functions(len(face_nodes), barycentric)
        tangent_u = derivatives[:, 0] @ face_coords
        tangent_v = derivatives[:, 1] @ face_coords
        area_vector = np.cross(tangent_u, tangent_v)
        measure = float(np.linalg.norm(area_vector))
        if measure <= 1.0e-14:
            raise InputValidationError("Degenerate face encountered during surface load integration.")
        if pressure is not None:
            weighted_traction = -pressure * area_vector * weight
        else:
            applied = np.asarray(traction, dtype=float)
            if coordinate_system == "local":
                e1 = tangent_u / np.linalg.norm(tangent_u)
                e3 = area_vector / measure
                e2 = np.cross(e3, e1)
                applied = np.column_stack((e1, e2, e3)) @ applied
            weighted_traction = applied * measure * weight
        for face_node, value in zip(face_nodes, shape):
            local[3 * face_node : 3 * face_node + 3] += value * weighted_traction
    return local


def _mitc4_surface_vector(
    coords: np.ndarray,
    traction: np.ndarray | None,
    pressure: float | None,
) -> np.ndarray:
    local = np.zeros(24, dtype=float)
    point = 1.0 / math.sqrt(3.0)
    for xi, eta in ((-point, -point), (point, -point), (point, point), (-point, point)):
        shape, derivatives = MITC4Element.shape_functions(xi, eta)
        tangent_xi = derivatives[:, 0] @ coords
        tangent_eta = derivatives[:, 1] @ coords
        area_vector = np.cross(tangent_xi, tangent_eta)
        measure = float(np.linalg.norm(area_vector))
        if measure <= 1.0e-14:
            raise InputValidationError("Degenerate MITC4 surface load geometry.")
        weighted_traction = -pressure * area_vector if pressure is not None else np.asarray(traction) * measure
        for node, value in enumerate(shape):
            local[6 * node : 6 * node + 3] += value * weighted_traction
    return local


def _mitc3_surface_vector(
    coords: np.ndarray,
    traction: np.ndarray | None,
    pressure: float | None,
) -> np.ndarray:
    """Return the exact consistent vector for a constant load on a flat TRI3."""
    local = np.zeros(18, dtype=float)
    area_vector = 0.5 * np.cross(coords[1] - coords[0], coords[2] - coords[0])
    area = float(np.linalg.norm(area_vector))
    if area <= 1.0e-14:
        raise InputValidationError("Degenerate MITC3 surface load geometry.")
    total_force = -float(pressure) * area_vector if pressure is not None else np.asarray(traction) * area
    for node in range(3):
        local[6 * node : 6 * node + 3] = total_force / 3.0
    return local


def load_balance(model: FiniteElementModel, dofs: DofManager, vector: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return global force and moment about the origin for one nodal vector."""
    resultant = np.zeros(3, dtype=float)
    moment = np.zeros(3, dtype=float)
    for node, position in enumerate(model.nodes):
        force = np.array(
            [vector[dofs.index(node, name)] if dofs.has(node, name) else 0.0 for name in ("UX", "UY", "UZ")]
        )
        couple = np.array(
            [vector[dofs.index(node, name)] if dofs.has(node, name) else 0.0 for name in ("RX", "RY", "RZ")]
        )
        resultant += force
        moment += np.cross(position, force) + couple
    return resultant, moment


def _significant_entry_count(vector: np.ndarray) -> int:
    scale = float(np.max(np.abs(vector), initial=0.0))
    tolerance = max(1.0e-30, scale * 1.0e-12)
    return int(np.count_nonzero(np.abs(vector) > tolerance))
