"""Validation helpers for the bounded 0.2.8 mixed-solid static route."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np

from solveur.mesh.topology import HEX8_FACES, TET4_FACES, WEDGE6_FACES


MIXED_LINEAR_STATIC_FAMILIES = frozenset({"TET4", "WEDGE6", "HEX8"})
_FACE_MAP = {
    "TET4": TET4_FACES,
    "WEDGE6": WEDGE6_FACES,
    "HEX8": HEX8_FACES,
}
_NODE_COUNTS = {"TET4": 4, "WEDGE6": 6, "HEX8": 8}


@dataclass(frozen=True)
class MixedSolidFace:
    """One solid face in the local topology used by the mixed contract."""

    element_index: int
    element_type: str
    local_face: int
    nodes: tuple[int, ...]


def mixed_linear_static_scope_errors(model: Any) -> list[str]:
    """Return explicit errors for an out-of-contract mixed static model."""

    return _mixed_scope_errors(model, "linear_static")


def mixed_modal_scope_errors(model: Any) -> list[str]:
    """Return explicit errors for an out-of-contract mixed modal model."""

    return _mixed_scope_errors(model, "modal")


def _mixed_scope_errors(model: Any, analysis_type: str) -> list[str]:
    """Return explicit errors for an out-of-contract mixed solid model.

    The general solver remains family-generic.  When a supported analysis model
    uses more than one solid family, this contract requires the three WP07
    families, shared-node conforming interfaces and no hidden MPC/RBE coupling.
    Exact coincident faces with different node identities are rejected because
    they otherwise create disconnected duplicate DDLs without a visible solver
    error.
    """

    elements = list(getattr(model, "elements", []))
    families = {str(getattr(element, "type", "")).upper() for element in elements}
    solid_families = families.intersection(MIXED_LINEAR_STATIC_FAMILIES)
    if len(solid_families) < 2:
        return []

    scope_name = f"Mixed {analysis_type}"
    errors: list[str] = []
    unsupported = sorted(families - MIXED_LINEAR_STATIC_FAMILIES)
    if unsupported:
        errors.append(
            f"{scope_name} scope supports only TET4/WEDGE6/HEX8 solid families; "
            f"received {', '.join(sorted(families))}."
        )
    if getattr(model, "multipoint_constraints", []) or getattr(model, "rbe2", []) or getattr(model, "rbe3", []):
        errors.append(
            f"{scope_name} scope rejects MPC/RBE coupling; hanging-node and nonconforming interface "
            "contracts are not supported."
        )

    faces = _face_records(elements)
    by_nodes: dict[frozenset[int], list[MixedSolidFace]] = defaultdict(list)
    by_geometry: dict[tuple[tuple[int, int, int], ...], list[MixedSolidFace]] = defaultdict(list)
    nodes = np.asarray(getattr(model, "nodes", np.empty((0, 3))), dtype=float)
    for face in faces:
        by_nodes[frozenset(face.nodes)].append(face)
        if all(0 <= node < len(nodes) for node in face.nodes):
            by_geometry[_geometry_key(nodes[list(face.nodes)])].append(face)

    for node_set, entries in by_nodes.items():
        if len(entries) > 2:
            errors.append(
                f"{scope_name} interface is non-manifold: face nodes "
                f"{sorted(node_set)} belong to {len(entries)} elements."
            )

    cross_family_interfaces = [
        entries
        for entries in by_nodes.values()
        if len(entries) == 2 and len({face.element_type for face in entries}) == 2
    ]
    for entries in by_geometry.values():
        element_ids = {face.element_index for face in entries}
        node_sets = {frozenset(face.nodes) for face in entries}
        families_at_geometry = {face.element_type for face in entries}
        if len(element_ids) > 1 and len(node_sets) > 1 and len(families_at_geometry) > 1:
            errors.append(
                f"{scope_name} nonconforming interface rejected: coincident faces from different "
                "families do not share the same node identities."
            )

    if not cross_family_interfaces:
        errors.append(
            f"{scope_name} model has no conforming shared-face interface between its solid families."
        )
    return errors


def mixed_solid_faces(model: Any) -> tuple[MixedSolidFace, ...]:
    """Return valid WP07 face records for interface and load audits."""

    return tuple(_face_records(list(getattr(model, "elements", []))))


def _face_records(elements: list[Any]) -> list[MixedSolidFace]:
    records: list[MixedSolidFace] = []
    for element_index, element in enumerate(elements):
        element_type = str(getattr(element, "type", "")).upper()
        faces = _FACE_MAP.get(element_type)
        nodes = tuple(int(node) for node in getattr(element, "nodes", ()))
        if faces is None or len(nodes) != _NODE_COUNTS[element_type]:
            continue
        for local_face, local_nodes in enumerate(faces):
            records.append(
                MixedSolidFace(
                    element_index=element_index,
                    element_type=element_type,
                    local_face=local_face,
                    nodes=tuple(nodes[index] for index in local_nodes),
                )
            )
    return records


def _geometry_key(coords: np.ndarray) -> tuple[tuple[int, int, int], ...]:
    values = np.asarray(coords, dtype=float)
    span = max(float(np.ptp(values, axis=0).max(initial=0.0)), 1.0)
    quantum = max(span * 1.0e-10, 1.0e-12)
    quantized = np.rint(values / quantum).astype(np.int64)
    return tuple(sorted(tuple(int(value) for value in row) for row in quantized))


__all__ = [
    "MIXED_LINEAR_STATIC_FAMILIES",
    "MixedSolidFace",
    "mixed_linear_static_scope_errors",
    "mixed_modal_scope_errors",
    "mixed_solid_faces",
]
