"""Stable JSON serialization for finite-element input models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.loads.entities import BodyLoad, EdgeLoad, GravityLoad, LineLoad, SurfaceLoad


class JsonModelWriter:
    """Write a FiniteElementModel in the strict input schema."""

    def write(self, model: FiniteElementModel, path: str | Path) -> None:
        write_json_file(path, model_to_dict(model))


def model_to_dict(model: FiniteElementModel) -> dict[str, Any]:
    """Return a JSON-compatible representation accepted by JsonModelReader."""
    return {
        "schema_version": model.schema_version,
        "units": model.units,
        "verification_profile": model.verification_profile,
        "analysis": {
            "type": model.analysis.type,
            "method": model.analysis.method,
            "parameters": model.analysis.parameters,
        },
        "nodes": model.nodes.tolist(),
        "elements": [
            {"type": element.type, "nodes": list(element.nodes), "material": element.material}
            for element in model.elements
        ],
        "materials": model.materials,
        "fixed_dofs": [{"node": condition.node, "dofs": list(condition.dofs)} for condition in model.fixed_dofs],
        "loads": [{"node": load.node, "dof": load.dof, "value": load.value} for load in model.loads],
        "distributed_loads": [_distributed_load(load) for load in model.distributed_loads],
        "springs": [_spring(spring) for spring in model.springs],
        "concentrated_masses": [_concentrated_mass(mass) for mass in model.concentrated_masses],
        "multipoint_constraints": [_constraint(constraint) for constraint in model.multipoint_constraints],
        "rbe2": [_rbe2(definition) for definition in model.rbe2],
        "rbe3": [_rbe3(definition) for definition in model.rbe3],
        "contacts": [_contact(contact) for contact in model.contacts],
    }


def _spring(spring: object) -> dict[str, Any]:
    item: dict[str, Any] = {
        "node_a": spring.node_a,
        "dofs": list(spring.dofs),
        "stiffness_matrix": [list(row) for row in spring.stiffness],
        "coordinate_system": spring.coordinate_system,
    }
    if spring.node_b is not None:
        item["node_b"] = spring.node_b
    if spring.orientation is not None:
        item["orientation"] = [list(row) for row in spring.orientation]
    return item


def _concentrated_mass(mass: object) -> dict[str, Any]:
    item: dict[str, Any] = {
        "node": mass.node,
        "mass": mass.mass,
        "center_of_mass": list(mass.center_of_mass),
    }
    if mass.inertia is not None:
        item["inertia"] = [list(row) for row in mass.inertia]
    return item


def _constraint(constraint: object) -> dict[str, Any]:
    return {
        "name": constraint.name,
        "value": constraint.value,
        "terms": [
            {"node": term.node, "dof": term.dof, "coefficient": term.coefficient}
            for term in constraint.terms
        ],
    }


def _rbe2(definition: object) -> dict[str, Any]:
    return {
        "name": definition.name,
        "master": definition.master,
        "slaves": list(definition.slaves),
        "tie_rotations": definition.tie_rotations,
    }


def _rbe3(definition: object) -> dict[str, Any]:
    return {
        "name": definition.name,
        "reference": definition.reference,
        "independents": [{"node": node, "weight": weight} for node, weight in definition.independents],
        "dofs": list(definition.dofs),
        "mode": definition.mode,
    }


def _contact(contact: object) -> dict[str, Any]:
    result = {
        "name": contact.name,
        "slave_node": contact.slave_node,
        "gap_tolerance": contact.gap_tolerance,
    }
    if contact.master_faces is None:
        result["master_nodes"] = list(contact.master_nodes)
    else:
        result["master_faces"] = [list(face) for face in contact.master_faces]
    if contact.friction_coefficient:
        result["friction_coefficient"] = contact.friction_coefficient
        result["tangential_stiffness"] = contact.tangential_stiffness
    return result


def _distributed_load(load: object) -> dict[str, Any]:
    if isinstance(load, GravityLoad):
        item: dict[str, Any] = {"type": load.type, "acceleration": list(load.acceleration)}
        if load.elements is not None:
            item["elements"] = list(load.elements)
        return item
    if isinstance(load, BodyLoad):
        item = {"type": load.type, "value": list(load.value), "coordinate_system": load.coordinate_system}
        if load.elements is not None:
            item["elements"] = list(load.elements)
        return item
    if isinstance(load, SurfaceLoad):
        value = load.value if isinstance(load.value, float) else list(load.value)
        item = {
            "type": load.type,
            "element": load.element,
            "value": value,
            "coordinate_system": load.coordinate_system,
            "follower": load.follower,
        }
        if load.face is not None:
            item["face"] = load.face
        return item
    if isinstance(load, EdgeLoad):
        return {
            "type": load.type,
            "element": load.element,
            "edge": load.edge,
            "value": list(load.value),
            "coordinate_system": load.coordinate_system,
        }
    if isinstance(load, LineLoad):
        return {
            "type": load.type,
            "element": load.element,
            "value": list(load.value),
            "coordinate_system": load.coordinate_system,
        }
    raise TypeError(f"Unsupported distributed load type {type(load).__name__}.")
