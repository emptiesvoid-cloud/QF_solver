"""Validation helpers for the bounded 0.2.8 mixed-solid static route."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np

from solveur.core.errors import InputValidationError
from solveur.core.rbe import rbe2_constraints
from solveur.mesh.topology import HEX8_FACES, PYRAMID5_FACES, TET4_FACES, WEDGE6_FACES


MIXED_LINEAR_STATIC_FAMILIES = frozenset({"TET4", "WEDGE6", "HEX8"})
PYRAMID5_FEASIBILITY_FAMILIES = frozenset({"TET4", "PYRAMID5", "HEX8"})
_FACE_MAP = {
    "TET4": TET4_FACES,
    "WEDGE6": WEDGE6_FACES,
    "HEX8": HEX8_FACES,
    "PYRAMID5": PYRAMID5_FACES,
}
_NODE_COUNTS = {"TET4": 4, "WEDGE6": 6, "HEX8": 8, "PYRAMID5": 5}


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


def declared_mixed_dynamic_scope_errors(model: Any) -> list[str]:
    """Validate an explicitly declared dynamic mixed-family/interface scope.

    Pure-family dynamic models remain family-generic.  A dynamic input opts
    into this preflight only when it declares the families and interfaces that
    the campaign requires; this makes a missing family an explicit input/model
    error instead of silently reducing the problem to a different topology.
    """

    parameters = getattr(getattr(model, "analysis", None), "parameters", {})
    required_raw = parameters.get("required_mixed_families")
    interfaces_raw = parameters.get("required_mixed_interfaces")
    if required_raw is None and interfaces_raw is None:
        return []

    errors: list[str] = []
    required: list[str] = []
    if not isinstance(required_raw, list) or not required_raw or any(
        not isinstance(item, str) or not item.strip() for item in required_raw
    ):
        errors.append("required_mixed_families must be a non-empty list of family names.")
    else:
        required = [item.strip().upper() for item in required_raw]
        if len(set(required)) != len(required):
            errors.append("required_mixed_families must not contain duplicate family names.")

    elements = list(getattr(model, "elements", []))
    actual = {str(getattr(element, "type", "")).upper() for element in elements}
    missing = sorted(set(required).difference(actual))
    if missing:
        errors.append(
            "Declared mixed dynamic scope is missing required element family/families: "
            + ", ".join(missing)
            + "."
        )

    declared_interfaces: list[tuple[str, str]] = []
    if interfaces_raw is not None:
        if not isinstance(interfaces_raw, list):
            errors.append("required_mixed_interfaces must be a list of two-family pairs.")
        else:
            for index, raw_pair in enumerate(interfaces_raw):
                if (
                    not isinstance(raw_pair, list)
                    or len(raw_pair) != 2
                    or any(not isinstance(item, str) or not item.strip() for item in raw_pair)
                ):
                    errors.append(
                        f"required_mixed_interfaces[{index}] must contain exactly two family names."
                    )
                    continue
                declared_interfaces.append((raw_pair[0].strip().upper(), raw_pair[1].strip().upper()))

    if declared_interfaces:
        faces = _face_records(elements)
        by_nodes: dict[frozenset[int], list[MixedSolidFace]] = defaultdict(list)
        for face in faces:
            by_nodes[frozenset(face.nodes)].append(face)
        present_pairs = {
            frozenset(face.element_type for face in entries)
            for entries in by_nodes.values()
            if len(entries) == 2
        }
        for left, right in declared_interfaces:
            pair = frozenset((left, right))
            if left not in required or right not in required:
                errors.append(
                    f"Declared mixed interface {left}/{right} is not included in required_mixed_families."
                )
            if left not in actual or right not in actual or pair not in present_pairs:
                errors.append(
                    f"Declared mixed interface {left}/{right} is missing or not conformingly connected."
                )
    return errors


def _mixed_scope_errors(model: Any, analysis_type: str) -> list[str]:
    """Return explicit errors for an out-of-contract mixed solid model.

    The general solver remains family-generic.  When a supported analysis model
    uses more than one solid family, the qualified WP07 contract requires the
    three WP07 families, shared-node conforming interfaces and no hidden
    MPC/RBE coupling.  The separate PYRAMID5 feasibility path is limited to
    bounded internal linear-static verification and does not extend WP07.
    Exact coincident faces with different node identities are rejected because
    they otherwise create disconnected duplicate DDLs without a visible solver
    error.
    """

    elements = list(getattr(model, "elements", []))
    families = {str(getattr(element, "type", "")).upper() for element in elements}
    allowed_scopes = (
        (MIXED_LINEAR_STATIC_FAMILIES, PYRAMID5_FEASIBILITY_FAMILIES)
        if analysis_type == "linear_static"
        else (MIXED_LINEAR_STATIC_FAMILIES,)
    )
    solid_families = families.intersection(frozenset().union(*allowed_scopes))
    if len(solid_families) < 2:
        return []

    scope_name = f"Mixed {analysis_type}"
    errors: list[str] = []
    if not any(families.issubset(scope) for scope in allowed_scopes):
        errors.append(
            f"{scope_name} scope supports only its declared conforming solid families; "
            f"received {', '.join(sorted(families))}."
        )
    if analysis_type != "linear_static":
        if getattr(model, "multipoint_constraints", []) or getattr(model, "rbe2", []) or getattr(model, "rbe3", []):
            errors.append(
                f"{scope_name} scope rejects MPC/RBE coupling; only the bounded linear_static "
                "translation-only route is enabled."
            )
    else:
        errors.extend(_mixed_linear_static_constraint_errors(model))

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


def _mixed_linear_static_constraint_errors(model: Any) -> list[str]:
    """Keep mixed static MPC/RBE2 enabling narrow and fail closed."""

    errors: list[str] = []
    rotational = {"RX", "RY", "RZ"}
    for index, constraint in enumerate(getattr(model, "multipoint_constraints", [])):
        if any(str(term.dof).upper() in rotational for term in constraint.terms):
            errors.append(
                f"Mixed linear_static MPC {index} contains rotational DOFs; "
                "the bounded mixed route is translation-only."
            )
    if getattr(model, "rbe3", []):
        errors.append("Mixed linear_static RBE3 coupling is outside the bounded MPC/RBE2 route.")
    for index, definition in enumerate(getattr(model, "rbe2", [])):
        if definition.tie_rotations:
            errors.append(
                f"Mixed linear_static RBE2 {index} requests rotational tying; "
                "RBE2 rotational coupling is outside the bounded route."
            )
            continue
        try:
            generated = rbe2_constraints(np.asarray(model.nodes, dtype=float), definition)
        except (InputValidationError, ValueError) as exc:
            errors.append(f"Mixed linear_static RBE2 {index} is invalid: {exc}")
            continue
        if any(str(term.dof).upper() in rotational for row in generated for term in row.terms):
            errors.append(
                f"Mixed linear_static RBE2 {index} generates rotational master terms from a nonzero offset; "
                "rotational RBE2 support is not available in the mixed solid route."
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
    "PYRAMID5_FEASIBILITY_FAMILIES",
    "MixedSolidFace",
    "mixed_linear_static_scope_errors",
    "mixed_modal_scope_errors",
    "declared_mixed_dynamic_scope_errors",
    "mixed_solid_faces",
]
