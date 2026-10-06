"""Fail-closed input checks for the first bounded rotating-modal scope."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from solveur.core.analyses.rotation_config import RotationConfig
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.elements.discrete import ConcentratedMass, RotatingDisk


_GEOMETRY_RTOL = 1.0e-12


@dataclass(frozen=True)
class RotatingInput:
    rotation: RotationConfig
    length_reference: float
    requested_modes: int


class RotatingModalInputValidator:
    """Validate all route-specific data before DOF maps or matrices are built."""

    def validate(self, model: FiniteElementModel) -> RotatingInput:
        if model.analysis.type != "rotating_modal" or model.analysis.method != "dense_qep":
            raise InputValidationError("The rotating route requires analysis='rotating_modal' and method='dense_qep'.")
        parameters = model.analysis.parameters
        unknown = sorted(set(parameters) - {"rotation", "modes"})
        if unknown:
            raise InputValidationError(
                "rotating_modal has unsupported parameter(s): " + ", ".join(str(item) for item in unknown) + "."
            )
        rotation = RotationConfig.from_mapping(parameters.get("rotation"))
        raw_modes = parameters.get("modes", 6)
        if isinstance(raw_modes, bool) or not isinstance(raw_modes, (int, np.integer)) or raw_modes <= 0:
            raise InputValidationError("rotating_modal modes must be a positive integer.")

        if not model.elements:
            raise InputValidationError("rotating_modal requires at least one BEAM2 element.")
        if any(str(element.type).upper() != "BEAM2" for element in model.elements):
            raise InputValidationError("rotating_modal initially supports BEAM2 elements only.")
        if model.multipoint_constraints or model.rbe2 or model.rbe3:
            raise InputValidationError("rotating_modal does not support MPC, RBE2, or RBE3 constraints.")
        if model.contacts:
            raise InputValidationError("rotating_modal does not support contact.")
        if model.loads or model.distributed_loads:
            raise InputValidationError("rotating_modal requires an unprestressed, unloaded reference configuration.")

        length_reference, shaft_axis, beam_nodes = self._validate_shaft(model)
        if abs(float(np.dot(shaft_axis, rotation.axis_global))) < 1.0 - _GEOMETRY_RTOL:
            raise InputValidationError("The global spin axis must be parallel to the straight BEAM2 centerline.")
        self._validate_materials(model)
        self._validate_fixed_dofs(model, beam_nodes)
        self._validate_springs(model, beam_nodes)
        self._validate_discrete_entities(model, rotation, beam_nodes)
        return RotatingInput(rotation, length_reference, int(raw_modes))

    @staticmethod
    def _validate_shaft(model: FiniteElementModel) -> tuple[float, np.ndarray, set[int]]:
        coordinates = np.asarray(model.nodes, dtype=float)
        if not np.all(np.isfinite(coordinates)):
            raise InputValidationError("rotating_modal node coordinates must be finite.")
        adjacency: dict[int, set[int]] = {}
        beam_nodes: set[int] = set()
        first_axis: np.ndarray | None = None
        for index, element in enumerate(model.elements):
            if len(element.nodes) != 2:
                raise InputValidationError(f"BEAM2 element {index} must reference exactly two nodes.")
            first, second = (int(node) for node in element.nodes)
            if not (0 <= first < model.node_count and 0 <= second < model.node_count) or first == second:
                raise InputValidationError(f"BEAM2 element {index} has invalid connectivity.")
            delta = coordinates[second] - coordinates[first]
            length = float(np.linalg.norm(delta))
            if not np.isfinite(length) or length <= 0.0:
                raise InputValidationError(f"BEAM2 element {index} has zero or invalid length.")
            direction = delta / length
            if first_axis is None:
                first_axis = direction
            elif abs(float(np.dot(first_axis, direction))) < 1.0 - _GEOMETRY_RTOL:
                raise InputValidationError("rotating_modal requires a straight, collinear BEAM2 chain.")
            adjacency.setdefault(first, set()).add(second)
            adjacency.setdefault(second, set()).add(first)
            beam_nodes.update((first, second))

        if len(beam_nodes) != model.node_count:
            raise InputValidationError("Every model node must belong to the BEAM2 shaft in rotating_modal.")
        if any(len(neighbors) > 2 for neighbors in adjacency.values()):
            raise InputValidationError("rotating_modal does not support branched BEAM2 structures.")
        endpoints = [node for node, neighbors in adjacency.items() if len(neighbors) == 1]
        if len(endpoints) != 2 or len(model.elements) != len(beam_nodes) - 1:
            raise InputValidationError("rotating_modal requires one connected, unbranched BEAM2 path.")
        reached = {endpoints[0]}
        pending = [endpoints[0]]
        while pending:
            node = pending.pop()
            for neighbor in adjacency[node] - reached:
                reached.add(neighbor)
                pending.append(neighbor)
        if reached != beam_nodes:
            raise InputValidationError("rotating_modal BEAM2 elements must form one connected path.")

        assert first_axis is not None
        origin = coordinates[endpoints[0]]
        projected = (coordinates[list(beam_nodes)] - origin) @ first_axis
        length_reference = float(np.max(projected) - np.min(projected))
        if not np.isfinite(length_reference) or length_reference <= 0.0:
            raise InputValidationError("The BEAM2 chain must have a finite, positive end-to-end length.")
        offsets = coordinates - origin
        transverse = offsets - np.outer(offsets @ first_axis, first_axis)
        maximum_off_axis = float(np.max(np.linalg.norm(transverse[list(beam_nodes)], axis=1), initial=0.0))
        if maximum_off_axis > _GEOMETRY_RTOL * length_reference:
            raise InputValidationError("rotating_modal BEAM2 nodes are not collinear within the frozen geometry tolerance.")
        shaft_axis = first_axis / np.linalg.norm(first_axis)
        return length_reference, shaft_axis, beam_nodes

    @staticmethod
    def _validate_materials(model: FiniteElementModel) -> None:
        for index, element in enumerate(model.elements):
            material = model.materials.get(element.material)
            if not isinstance(material, dict) or str(material.get("type", "")).lower() != "beam_isotropic":
                raise InputValidationError(f"BEAM2 element {index} requires a beam_isotropic material.")
            try:
                values = {
                    "E": float(material["E"]),
                    "A": float(material["A"]),
                    "Iy": float(material["Iy"]),
                    "Iz": float(material["Iz"]),
                    "J": float(material["J"]),
                    "density": float(material.get("density", material.get("rho", 0.0))),
                }
            except (KeyError, TypeError, ValueError) as exc:
                raise InputValidationError(f"BEAM2 element {index} has incomplete circular-section data.") from exc
            if any(not np.isfinite(value) or value <= 0.0 for value in values.values()):
                raise InputValidationError(f"BEAM2 element {index} section properties and density must be finite and positive.")
            inertia_scale = max(abs(values["Iy"]), abs(values["Iz"]))
            if abs(values["Iy"] - values["Iz"]) > _GEOMETRY_RTOL * inertia_scale:
                raise InputValidationError(f"BEAM2 element {index} must use an isotropic circular section (Iy=Iz).")
            if abs(values["J"] - values["Iy"] - values["Iz"]) > _GEOMETRY_RTOL * max(abs(values["J"]), inertia_scale):
                raise InputValidationError(f"BEAM2 element {index} circular section must satisfy J=Iy+Iz.")

    @staticmethod
    def _validate_fixed_dofs(model: FiniteElementModel, beam_nodes: set[int]) -> None:
        seen: set[tuple[int, str]] = set()
        for boundary in model.fixed_dofs:
            if boundary.node not in beam_nodes:
                raise InputValidationError("rotating_modal fixed DOFs must reference BEAM2 shaft nodes.")
            for dof in boundary.dofs:
                key = (boundary.node, str(dof).upper())
                if key in seen:
                    raise InputValidationError(f"rotating_modal fixed DOF {key[1]} is declared more than once at node {key[0]}.")
                seen.add(key)

    @staticmethod
    def _validate_springs(model: FiniteElementModel, beam_nodes: set[int]) -> None:
        for index, spring in enumerate(model.springs):
            if spring.node_a not in beam_nodes or spring.node_b is not None:
                raise InputValidationError(f"Spring {index} must be a fixed-ground spring attached to a shaft node.")
            if spring.coordinate_system != "global":
                raise InputValidationError(f"Spring {index} must use global coordinates in the initial rotating scope.")
            try:
                matrix = spring.nodal_stiffness()
            except ValueError as exc:
                raise InputValidationError(f"Spring {index} is invalid for rotating_modal: {exc}") from exc
            if not np.all(np.isfinite(matrix)):
                raise InputValidationError(f"Spring {index} stiffness must be finite.")

    @staticmethod
    def _validate_discrete_entities(
        model: FiniteElementModel,
        rotation: RotationConfig,
        beam_nodes: set[int],
    ) -> None:
        disks: list[RotatingDisk] = []
        disk_nodes: set[int] = set()
        generic_masses = [item for item in model.concentrated_masses if isinstance(item, ConcentratedMass)]
        for item in model.concentrated_masses:
            if isinstance(item, RotatingDisk):
                if item.node not in beam_nodes:
                    raise InputValidationError("Every rotating disk must be centered on an existing BEAM2 node.")
                if float(np.dot(item.axis_global, rotation.axis_global)) < 1.0 - _GEOMETRY_RTOL:
                    raise InputValidationError(
                        f"Rotating disk at node {item.node} axis must match the directed global spin axis."
                    )
                item.matrix()  # validate its exact mass block before any global allocation
                disks.append(item)
                disk_nodes.add(item.node)
            elif not isinstance(item, ConcentratedMass):
                raise InputValidationError(f"Unsupported discrete mass entity {type(item).__name__} in rotating_modal.")
        if not disks:
            raise InputValidationError("rotating_modal requires at least one RotatingDisk entity.")
        for item in generic_masses:
            if item.node in disk_nodes:
                raise InputValidationError(
                    f"A generic concentrated mass duplicates the rotating disk mass owner at node {item.node}."
                )
            raise InputValidationError("rotating_modal does not support generic concentrated masses outside disk ownership.")
