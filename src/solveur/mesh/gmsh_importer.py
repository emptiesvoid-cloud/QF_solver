"""Strict translation of named Gmsh physical groups into QF_solver models."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from solveur.core.errors import InputValidationError, MeshValidationError
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import sha256
from solveur.mesh.gmsh_reader import GmshNativeReader
from solveur.mesh.gmsh_types import GmshImportReport, GmshImportResult, GmshMeshData, GmshPhysicalGroup
from solveur.mesh.topology import MITC3_EDGES, MITC4_EDGES, TET10_FACES, TET4_FACES
from solveur.mesh.validation import MeshValidator
from solveur.version import DISPLAY_NAME, __version__


SUPPORTED_FAMILIES = {"TET4", "TET10", "MITC3", "MITC4"}
SUPPORTED_ACTIONS = {
    "elements",
    "fixed_dofs",
    "nodal_load",
    "pressure",
    "surface_traction",
    "edge_traction",
    "gravity",
    "body_force",
}

# Gmsh orders the final TET10 edge nodes as (corner 2, corner 3) then
# (corner 3, corner 1). QF_solver uses (corner 1, corner 3) then
# (corner 2, corner 3), matching Tet10Element.edge_nodes.
GMSH_TET10_TO_INTERNAL = (0, 1, 2, 3, 4, 5, 6, 7, 9, 8)


class GmshModelImporter:
    """Build one finite-element model from a MSH mesh and companion JSON setup."""

    def import_model(
        self,
        mesh_path: str | Path,
        setup_path: str | Path,
        *,
        repair_tetra_orientation: bool = False,
    ) -> GmshImportResult:
        setup_source = Path(setup_path).resolve()
        setup = _read_setup(setup_source)
        mesh = GmshNativeReader().read(mesh_path)
        return self.from_data(
            mesh,
            setup,
            setup_path=setup_source,
            setup_sha256=sha256(setup_source),
            source_sha256=sha256(mesh.path),
            repair_tetra_orientation=repair_tetra_orientation,
        )

    def from_data(
        self,
        mesh: GmshMeshData,
        setup: dict[str, Any],
        *,
        setup_path: str | Path = "<memory>",
        setup_sha256: str = "memory",
        source_sha256: str = "memory",
        repair_tetra_orientation: bool = False,
    ) -> GmshImportResult:
        normalized, warnings = _validate_setup(setup)
        assignments, families, family, referenced_groups = _element_assignments(mesh, normalized)
        native_connectivity, repair_count = _oriented_connectivities(
            mesh,
            assignments,
            families,
            repair_tetra_orientation,
        )
        if set(families.values()).issubset({"MITC3", "MITC4"}):
            _validate_shell_orientation(native_connectivity, families)
        used_tags = sorted({node for connectivity in native_connectivity.values() for node in connectivity})
        missing_nodes = [tag for tag in used_tags if tag not in mesh.nodes]
        if missing_nodes:
            raise MeshValidationError(f"Gmsh connectivities reference missing node tags: {missing_nodes[:8]}")
        scale = float(normalized["mesh_scale_to_m"])
        node_index = {tag: index for index, tag in enumerate(used_tags)}
        nodes = [[scale * value for value in mesh.nodes[tag]] for tag in used_tags]
        ordered_tags = sorted(assignments)
        element_index = {tag: index for index, tag in enumerate(ordered_tags)}
        elements = [
            {
                "type": families[tag],
                "nodes": [node_index[node] for node in native_connectivity[tag]],
                "material": assignments[tag],
            }
            for tag in ordered_tags
        ]
        fixed, nodal, distributed, action_counts = _boundary_and_load_actions(
            mesh,
            normalized,
            families,
            native_connectivity,
            node_index,
            element_index,
            referenced_groups,
        )
        for key, group in mesh.groups.items():
            if key not in referenced_groups:
                warnings.append(f"Physical group {group.name!r} (dimension {group.dimension}) is unused.")
        model = FiniteElementModel.from_raw(
            nodes=nodes,
            elements=elements,
            materials=normalized["materials"],
            fixed_dofs=fixed,
            loads=nodal,
            distributed_loads=distributed,
            analysis=normalized.get("analysis", "linear_static"),
            schema_version=int(normalized.get("schema_version", 1)),
            units=normalized.get("units", {"system": "SI"}),
            verification_profile=str(normalized.get("verification_profile", "engineering")),
        )
        mesh_report = MeshValidator().validate(model)
        if mesh_report.status == "FAIL":
            raise MeshValidationError("Imported Gmsh model is invalid: " + "; ".join(mesh_report.errors))
        warnings.extend(mesh_report.warnings)
        report = GmshImportReport(
            status="WARNING" if warnings else "PASS",
            solver_name=DISPLAY_NAME,
            solver_version=__version__,
            source_path=_portable_input_path(mesh.path),
            source_sha256=source_sha256,
            setup_path=_portable_input_path(setup_path),
            setup_sha256=setup_sha256,
            gmsh_version=mesh.gmsh_version,
            msh_version=mesh.format_version,
            binary=mesh.binary,
            element_family=family,
            node_count=model.node_count,
            element_count=len(model.elements),
            group_count=len(mesh.groups),
            physical_groups=[
                {
                    "name": group.name,
                    "dimension": group.dimension,
                    "tag": group.tag,
                    "cell_count": len(group.cell_tags),
                    "node_count": len(group.node_tags),
                }
                for _, group in sorted(mesh.groups.items())
            ],
            action_counts=dict(sorted(action_counts.items())),
            orientation_repairs=repair_count,
            mesh_status=mesh_report.status,
            warnings=warnings,
        )
        return GmshImportResult(model=model, report=report)


def _portable_input_path(path: str | Path) -> str:
    """Return a publishable input identifier without a workstation path."""
    raw = str(path)
    if raw == "<memory>":
        return raw
    candidate = Path(raw)
    return candidate.name if candidate.is_absolute() else candidate.as_posix()


def _read_setup(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise InputValidationError(f"Gmsh companion setup does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"Invalid Gmsh companion JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise InputValidationError("Gmsh companion setup root must be an object.")
    return payload


def _validate_setup(setup: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    allowed = {
        "schema_version",
        "mesh_scale_to_m",
        "units",
        "verification_profile",
        "analysis",
        "materials",
        "groups",
    }
    unknown = sorted(set(setup) - allowed)
    if unknown:
        raise InputValidationError(f"Unknown Gmsh companion fields: {unknown}")
    if int(setup.get("schema_version", 1)) != 1:
        raise InputValidationError("Gmsh companion schema_version must be 1.")
    if "mesh_scale_to_m" not in setup:
        raise InputValidationError("Gmsh companion requires an explicit mesh_scale_to_m.")
    scale = _positive_float(setup["mesh_scale_to_m"], "mesh_scale_to_m")
    materials = setup.get("materials")
    if not isinstance(materials, dict) or not materials:
        raise InputValidationError("Gmsh companion materials must be a non-empty object.")
    groups = setup.get("groups")
    if not isinstance(groups, list) or not groups:
        raise InputValidationError("Gmsh companion groups must be a non-empty list.")
    normalized = dict(setup)
    normalized["mesh_scale_to_m"] = scale
    seen: set[tuple[int, str]] = set()
    for index, item in enumerate(groups):
        if not isinstance(item, dict):
            raise InputValidationError(f"Gmsh companion group {index} must be an object.")
        unknown_group = sorted(set(item) - {"name", "dimension", "actions"})
        if unknown_group:
            raise InputValidationError(f"Unknown fields in Gmsh companion group {index}: {unknown_group}")
        name = str(item.get("name", "")).strip()
        dimension = _dimension(item.get("dimension"), f"groups[{index}].dimension")
        if not name:
            raise InputValidationError(f"Gmsh companion group {index} requires a name.")
        key = (dimension, name)
        if key in seen:
            raise InputValidationError(f"Duplicate Gmsh companion group {name!r} in dimension {dimension}.")
        seen.add(key)
        actions = item.get("actions")
        if not isinstance(actions, list) or not actions:
            raise InputValidationError(f"Gmsh companion group {name!r} requires actions.")
        for action_index, action in enumerate(actions):
            if not isinstance(action, dict):
                raise InputValidationError(f"Action {action_index} for group {name!r} must be an object.")
            action_type = str(action.get("type", "")).lower()
            if action_type not in SUPPORTED_ACTIONS:
                raise InputValidationError(f"Unsupported Gmsh group action {action_type!r} for group {name!r}.")
    return normalized, []


def _element_assignments(
    mesh: GmshMeshData,
    setup: dict[str, Any],
) -> tuple[dict[int, str], dict[int, str], str, set[tuple[int, str]]]:
    assignments: dict[int, str] = {}
    families: dict[int, str] = {}
    selected_families: set[str] = set()
    referenced: set[tuple[int, str]] = set()
    for group_spec in setup["groups"]:
        group = _physical_group(mesh, group_spec)
        referenced.add((group.dimension, group.name))
        for action in group_spec["actions"]:
            if str(action["type"]).lower() != "elements":
                continue
            family = str(action.get("element_type", "")).upper()
            material = str(action.get("material", ""))
            if family not in SUPPORTED_FAMILIES:
                raise InputValidationError(f"Unsupported imported element_type {family!r}.")
            if material not in setup["materials"]:
                raise InputValidationError(f"Element group {group.name!r} references unknown material {material!r}.")
            selected_families.add(family)
            if len(selected_families) > 1 and not selected_families.issubset({"MITC3", "MITC4"}):
                raise MeshValidationError(
                    "Mixed imported families are supported only for MITC3/MITC4 shells: "
                    + ", ".join(sorted(selected_families))
                )
            matching = [tag for tag in group.cell_tags if _cell_family(mesh.cells[tag]) == family]
            if not matching:
                raise MeshValidationError(f"Physical group {group.name!r} contains no {family} cells.")
            for tag in matching:
                previous = assignments.get(tag)
                if previous is not None and previous != material:
                    raise MeshValidationError(f"Gmsh element {tag} has conflicting materials {previous!r}/{material!r}.")
                assignments[tag] = material
                families[tag] = family
    if not selected_families:
        raise InputValidationError("Gmsh companion has no elements action.")
    candidates = {
        tag for tag, cell in mesh.cells.items() if _cell_family(cell) in selected_families
    }
    missing = sorted(candidates - assignments.keys())
    if missing:
        raise MeshValidationError(
            "Structural cells are not assigned to a material: "
            f"{missing[:8]} (families={sorted(selected_families)})"
        )
    if all(family.startswith("TET") for family in selected_families):
        unsupported = [cell.tag for cell in mesh.cells.values() if cell.dimension == 3 and cell.tag not in candidates]
    else:
        unsupported = [cell.tag for cell in mesh.cells.values() if cell.dimension == 2 and cell.tag not in candidates]
    if unsupported:
        raise MeshValidationError(f"Unsupported structural cells are present in the Gmsh mesh: {unsupported[:8]}")
    family_label = "+".join(sorted(selected_families))
    return assignments, families, family_label, referenced


def _oriented_connectivities(
    mesh: GmshMeshData,
    assignments: dict[int, str],
    families: dict[int, str],
    repair: bool,
) -> tuple[dict[int, tuple[int, ...]], int]:
    connectivities: dict[int, tuple[int, ...]] = {}
    repairs = 0
    for tag in sorted(assignments):
        family = families[tag]
        connectivity = mesh.cells[tag].nodes
        if family == "TET10":
            connectivity = tuple(connectivity[index] for index in GMSH_TET10_TO_INTERNAL)
        if family.startswith("TET"):
            corners = np.asarray([mesh.nodes[node] for node in connectivity[:4]], dtype=float)
            determinant = float(np.linalg.det((corners[1:] - corners[0]).T))
            span = max(float(np.max(np.ptp(corners, axis=0))), 1.0)
            tolerance = 1.0e-14 * span**3
            if abs(determinant) <= tolerance:
                raise MeshValidationError(f"Gmsh tetrahedron {tag} is degenerate.")
            if determinant < 0.0:
                if not repair:
                    raise MeshValidationError(
                        f"Gmsh tetrahedron {tag} is inverted; use repair_tetra_orientation explicitly to repair it."
                    )
                permutation = (0, 2, 1, 3) if family == "TET4" else (0, 2, 1, 3, 6, 5, 4, 7, 9, 8)
                connectivity = tuple(connectivity[index] for index in permutation)
                repairs += 1
        connectivities[tag] = tuple(connectivity)
    return connectivities, repairs


def _validate_shell_orientation(
    connectivities: dict[int, tuple[int, ...]],
    families: dict[int, str],
) -> None:
    edges: dict[tuple[int, int], list[tuple[int, int, int]]] = defaultdict(list)
    for tag, connectivity in connectivities.items():
        family = families[tag]
        local_edges = MITC3_EDGES if family == "MITC3" else MITC4_EDGES
        for first, second in local_edges:
            a, b = connectivity[first], connectivity[second]
            edges[tuple(sorted((a, b)))].append((tag, a, b))
    for key, uses in edges.items():
        if len(uses) > 2:
            raise MeshValidationError(f"Non-manifold shell edge {key} belongs to {len(uses)} elements.")
        if len(uses) == 2 and uses[0][1:] == uses[1][1:]:
            raise MeshValidationError(
                f"Inconsistent shell orientation across edge {key}; shell orientation is never repaired automatically."
            )


def _boundary_and_load_actions(
    mesh: GmshMeshData,
    setup: dict[str, Any],
    families: dict[int, str],
    connectivities: dict[int, tuple[int, ...]],
    node_index: dict[int, int],
    element_index: dict[int, int],
    referenced: set[tuple[int, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    fixed: dict[int, set[str]] = defaultdict(set)
    nodal_values: dict[tuple[int, str], float] = defaultdict(float)
    distributed: list[dict[str, Any]] = []
    counts: dict[str, int] = defaultdict(int)
    family_set = set(families.values())
    solid_faces = _solid_face_map(families, connectivities, element_index)
    shell_edges = (
        _shell_edge_map(families, connectivities, element_index)
        if family_set.issubset({"MITC3", "MITC4"})
        else {}
    )
    for group_spec in setup["groups"]:
        group = _physical_group(mesh, group_spec)
        referenced.add((group.dimension, group.name))
        model_nodes = [node_index[tag] for tag in group.node_tags if tag in node_index]
        for action in group_spec["actions"]:
            action_type = str(action["type"]).lower()
            if action_type == "elements":
                counts[action_type] += sum(tag in element_index for tag in group.cell_tags)
            elif action_type == "fixed_dofs":
                if not model_nodes:
                    raise MeshValidationError(f"Fixed group {group.name!r} has no structural nodes.")
                dofs = action.get("dofs")
                if not isinstance(dofs, list) or not dofs:
                    raise InputValidationError(f"fixed_dofs action for {group.name!r} requires a dofs list.")
                for node in model_nodes:
                    fixed[node].update(str(dof).upper() for dof in dofs)
                counts[action_type] += len(model_nodes)
            elif action_type == "nodal_load":
                if not model_nodes:
                    raise MeshValidationError(f"Nodal-load group {group.name!r} has no structural nodes.")
                dof = str(action.get("dof", "")).upper()
                value = _finite_float(action.get("value"), f"nodal_load[{group.name}].value")
                for node in model_nodes:
                    nodal_values[(node, dof)] += value
                counts[action_type] += len(model_nodes)
            elif action_type in {"gravity", "body_force"}:
                targets = sorted(element_index[tag] for tag in group.cell_tags if tag in element_index)
                if not targets:
                    raise MeshValidationError(f"Volume-load group {group.name!r} has no structural elements.")
                if action_type == "gravity":
                    distributed.append({"type": action_type, "acceleration": _vector(action.get("acceleration")), "elements": targets})
                else:
                    distributed.append(
                        {
                            "type": action_type,
                            "value": _vector(action.get("value")),
                            "elements": targets,
                            "coordinate_system": str(action.get("coordinate_system", "global")),
                        }
                    )
                counts[action_type] += len(targets)
            elif action_type in {"pressure", "surface_traction"}:
                targets = _surface_targets(mesh, group, families, solid_faces, element_index)
                value: float | tuple[float, float, float]
                value = _finite_float(action.get("value"), f"pressure[{group.name}].value") if action_type == "pressure" else _vector(action.get("value"))
                for element, face in targets:
                    item: dict[str, Any] = {"type": action_type, "element": element, "value": value}
                    if face is not None:
                        item["face"] = face
                    if action_type == "surface_traction":
                        item["coordinate_system"] = str(action.get("coordinate_system", "global"))
                    distributed.append(item)
                counts[action_type] += len(targets)
            elif action_type == "edge_traction":
                if not family_set.issubset({"MITC3", "MITC4"}):
                    raise MeshValidationError("edge_traction is only supported for shell imports.")
                targets = _edge_targets(mesh, group, shell_edges)
                for element, edge in targets:
                    distributed.append(
                        {
                            "type": action_type,
                            "element": element,
                            "edge": edge,
                            "value": _vector(action.get("value")),
                            "coordinate_system": str(action.get("coordinate_system", "global")),
                        }
                    )
                counts[action_type] += len(targets)
    fixed_rows = [{"node": node, "dofs": sorted(dofs)} for node, dofs in sorted(fixed.items())]
    nodal_rows = [
        {"node": node, "dof": dof, "value": value}
        for (node, dof), value in sorted(nodal_values.items())
    ]
    return fixed_rows, nodal_rows, distributed, counts


def _solid_face_map(
    families: dict[int, str],
    connectivities: dict[int, tuple[int, ...]],
    element_index: dict[int, int],
) -> dict[frozenset[int], list[tuple[int, int]]]:
    family_set = set(families.values())
    if len(family_set) != 1 or not family_set.issubset({"TET4", "TET10"}):
        return {}
    family = next(iter(family_set))
    faces = TET4_FACES if family == "TET4" else TET10_FACES
    mapping: dict[frozenset[int], list[tuple[int, int]]] = defaultdict(list)
    for tag, connectivity in connectivities.items():
        for face, local_nodes in enumerate(faces):
            mapping[frozenset(connectivity[index] for index in local_nodes)].append((element_index[tag], face))
    return mapping


def _shell_edge_map(
    families: dict[int, str],
    connectivities: dict[int, tuple[int, ...]],
    element_index: dict[int, int],
) -> dict[frozenset[int], list[tuple[int, int]]]:
    mapping: dict[frozenset[int], list[tuple[int, int]]] = defaultdict(list)
    for tag, connectivity in connectivities.items():
        edges = MITC3_EDGES if families[tag] == "MITC3" else MITC4_EDGES
        for edge, local_nodes in enumerate(edges):
            mapping[frozenset(connectivity[index] for index in local_nodes)].append((element_index[tag], edge))
    return mapping


def _surface_targets(
    mesh: GmshMeshData,
    group: GmshPhysicalGroup,
    families: dict[int, str],
    solid_faces: dict[frozenset[int], list[tuple[int, int]]],
    element_index: dict[int, int],
) -> list[tuple[int, int | None]]:
    family_set = set(families.values())
    if family_set.issubset({"MITC3", "MITC4"}):
        targets = [(element_index[tag], None) for tag in group.cell_tags if tag in element_index]
        if not targets:
            raise MeshValidationError(f"Shell surface group {group.name!r} has no shell elements.")
        return sorted(targets)
    family = next(iter(family_set))
    expected_nodes = 3 if family == "TET4" else 6
    targets: list[tuple[int, int | None]] = []
    for tag in group.cell_tags:
        cell = mesh.cells[tag]
        if cell.dimension != 2:
            continue
        if len(cell.nodes) != expected_nodes:
            raise MeshValidationError(
                f"Solid surface group {group.name!r} has incompatible cell {tag} with {len(cell.nodes)} nodes."
            )
        parents = solid_faces.get(frozenset(cell.nodes), [])
        if len(parents) != 1:
            raise MeshValidationError(
                f"Boundary cell {tag} in group {group.name!r} has {len(parents)} parent solid faces; expected one."
            )
        targets.append(parents[0])
    if not targets:
        raise MeshValidationError(f"Solid surface group {group.name!r} has no boundary faces.")
    return sorted(set(targets))


def _edge_targets(
    mesh: GmshMeshData,
    group: GmshPhysicalGroup,
    edge_map: dict[frozenset[int], list[tuple[int, int]]],
) -> list[tuple[int, int]]:
    targets: list[tuple[int, int]] = []
    for tag in group.cell_tags:
        cell = mesh.cells[tag]
        if cell.dimension != 1:
            continue
        if len(cell.nodes) != 2:
            raise MeshValidationError(f"Shell edge group {group.name!r} requires two-node line cells.")
        parents = edge_map.get(frozenset(cell.nodes), [])
        if len(parents) != 1:
            raise MeshValidationError(
                f"Boundary line {tag} in group {group.name!r} has {len(parents)} parent shell edges; expected one."
            )
        targets.append(parents[0])
    if not targets:
        raise MeshValidationError(f"Shell edge group {group.name!r} has no boundary edges.")
    return sorted(set(targets))


def _physical_group(mesh: GmshMeshData, spec: dict[str, Any]) -> GmshPhysicalGroup:
    key = (_dimension(spec.get("dimension"), "group.dimension"), str(spec.get("name", "")))
    try:
        return mesh.groups[key]
    except KeyError as exc:
        raise MeshValidationError(f"Gmsh physical group {key[1]!r} in dimension {key[0]} does not exist.") from exc


def _cell_family(cell: Any) -> str | None:
    name = cell.name.lower()
    if cell.dimension == 3 and "tetra" in name and cell.order == 1 and len(cell.nodes) == 4:
        return "TET4"
    if cell.dimension == 3 and "tetra" in name and cell.order == 2 and len(cell.nodes) == 10:
        return "TET10"
    if cell.dimension == 2 and ("quad" in name) and cell.order == 1 and len(cell.nodes) == 4:
        return "MITC4"
    if cell.dimension == 2 and ("triangle" in name or "tri" in name) and cell.order == 1 and len(cell.nodes) == 3:
        return "MITC3"
    return None


def _dimension(value: object, name: str) -> int:
    try:
        dimension = int(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{name} must be an integer from 0 to 3.") from exc
    if dimension not in {0, 1, 2, 3}:
        raise InputValidationError(f"{name} must be an integer from 0 to 3.")
    return dimension


def _finite_float(value: object, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{name} must be finite.") from exc
    if not math.isfinite(result):
        raise InputValidationError(f"{name} must be finite.")
    return result


def _positive_float(value: object, name: str) -> float:
    result = _finite_float(value, name)
    if result <= 0.0:
        raise InputValidationError(f"{name} must be strictly positive.")
    return result


def _vector(value: object) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise InputValidationError("Gmsh vector load values must contain three components.")
    return tuple(_finite_float(component, "vector component") for component in value)  # type: ignore[return-value]
