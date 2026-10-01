"""Deterministic bounded linear-elastic models for prospective WP12 R3.

This module generates identical meshes and nodal loads for QF Solver and
Code_Aster.  It is experiment tooling only; it does not change solver
mechanics or the WP12 R2 evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

import numpy as np

from solveur.core.model import FiniteElementModel
from solveur.elements.solid.hex20 import Hex20Element
from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.tet10 import Tet10Element
from solveur.large.multifamily import LinearSystem, MATERIAL, assemble_linear_system


FAMILIES = ("TET4", "HEX8", "TET10", "HEX20")
GEOMETRIES: dict[str, tuple[float, float, float]] = {
    "slender_beam": (2.0, 0.5, 0.5),
    "rectangular_beam": (2.0, 1.0, 0.5),
    "short_block": (1.0, 0.75, 0.75),
}
MESHES: dict[str, tuple[int, int, int]] = {
    "H1": (1, 1, 1),
    "H2": (2, 1, 1),
    "H3": (2, 2, 1),
}
LOADS: dict[str, tuple[float, float, float]] = {
    "axial_x": (1000.0, 0.0, 0.0),
    "transverse_y": (0.0, 1000.0, 0.0),
    "transverse_z": (0.0, 0.0, -1000.0),
    "combined_xyz": (577.3502691896258, 577.3502691896258, -577.3502691896258),
}
HEX8_ASTER_ORDER = tuple(range(8))
TET4_ASTER_ORDER = tuple(range(4))
TET10_ASTER_ORDER = tuple(range(10))
HEX20_ASTER_ORDER = (0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 13, 9, 10, 12, 14, 15, 16, 18, 19, 17)
ASTER_TYPES = {"TET4": "TETRA4", "HEX8": "HEXA8", "TET10": "TETRA10", "HEX20": "HEXA20"}
HEX_SIGNS = tuple(tuple(int(value) for value in row) for row in Hex8Element.node_signs)
TET_SPLIT = ((0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6), (0, 7, 4, 6), (0, 4, 5, 6), (0, 5, 1, 6))
SURFACE_GAUSS = (
    (-np.sqrt(3.0 / 5.0), 5.0 / 9.0),
    (0.0, 8.0 / 9.0),
    (np.sqrt(3.0 / 5.0), 5.0 / 9.0),
)
LOAD_RESULTANT_N = 1000.0


@dataclass(frozen=True)
class ExpandedCase:
    case_id: str
    family: str
    geometry: str
    dimensions: tuple[float, float, float]
    mesh: str
    divisions: tuple[int, int, int]
    load_case: str
    resultant: tuple[float, float, float]
    model: FiniteElementModel
    system: LinearSystem
    connectivity: np.ndarray
    fingerprint: str
    load_area: float
    load_moment: tuple[float, float, float]


def _grid_node(i: int, j: int, k: int, divisions: tuple[int, int, int]) -> int:
    nx, ny, nz = divisions
    return i * (ny + 1) * (nz + 1) + j * (nz + 1) + k


def _grid_coordinates(dimensions: tuple[float, float, float], divisions: tuple[int, int, int]) -> list[list[float]]:
    length, height, width = dimensions
    nx, ny, nz = divisions
    return [
        [length * i / nx, height * j / ny, width * k / nz]
        for i in range(nx + 1)
        for j in range(ny + 1)
        for k in range(nz + 1)
    ]


def _hex_corner_connectivity(i: int, j: int, k: int, divisions: tuple[int, int, int]) -> list[int]:
    return [
        _grid_node(i + (sx + 1) // 2, j + (sy + 1) // 2, k + (sz + 1) // 2, divisions)
        for sx, sy, sz in HEX_SIGNS
    ]


def _hex20_edge_corner_pairs() -> tuple[tuple[int, int], ...]:
    pairs: list[tuple[int, int]] = []
    for free_axis, fixed_axes, fixed_signs in Hex20Element.edge_data:
        first = [0, 0, 0]
        second = [0, 0, 0]
        for axis, sign in zip(fixed_axes, fixed_signs, strict=True):
            first[axis] = second[axis] = int(sign)
        first[free_axis] = -1
        second[free_axis] = 1
        pairs.append((HEX_SIGNS.index(tuple(first)), HEX_SIGNS.index(tuple(second))))
    return tuple(pairs)


def _hex_connectivity(
    family: str,
    dimensions: tuple[float, float, float],
    divisions: tuple[int, int, int],
) -> tuple[np.ndarray, np.ndarray]:
    coordinates = _grid_coordinates(dimensions, divisions)
    elements: list[list[int]] = []
    edge_node: dict[tuple[int, int], int] = {}
    edge_pairs = _hex20_edge_corner_pairs()
    nx, ny, nz = divisions
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                corners = _hex_corner_connectivity(i, j, k, divisions)
                if family == "HEX8":
                    elements.append(corners)
                    continue
                mids: list[int] = []
                for first_local, second_local in edge_pairs:
                    first_global, second_global = corners[first_local], corners[second_local]
                    key = (min(first_global, second_global), max(first_global, second_global))
                    if key not in edge_node:
                        edge_node[key] = len(coordinates)
                        coordinates.append(
                            (0.5 * (np.asarray(coordinates[first_global]) + np.asarray(coordinates[second_global]))).tolist()
                        )
                    mids.append(edge_node[key])
                elements.append(corners + mids)
    return np.asarray(coordinates, dtype=np.float64), np.asarray(elements, dtype=np.int64)


def _tet_connectivity(
    family: str,
    dimensions: tuple[float, float, float],
    divisions: tuple[int, int, int],
) -> tuple[np.ndarray, np.ndarray]:
    coordinates = _grid_coordinates(dimensions, divisions)
    elements: list[list[int]] = []
    edge_node: dict[tuple[int, int], int] = {}
    nx, ny, nz = divisions
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                cube_corners = _hex_corner_connectivity(i, j, k, divisions)
                for local_tet in TET_SPLIT:
                    corners = [cube_corners[index] for index in local_tet]
                    xyz = np.asarray([coordinates[node] for node in corners], dtype=np.float64)
                    determinant = float(np.linalg.det(np.column_stack((xyz[1] - xyz[0], xyz[2] - xyz[0], xyz[3] - xyz[0]))))
                    if abs(determinant) <= 1.0e-15:
                        raise ValueError("Structured tetrahedral split produced a degenerate element.")
                    if determinant < 0.0:
                        corners[1], corners[2] = corners[2], corners[1]
                    if family == "TET4":
                        elements.append(corners)
                        continue
                    mids: list[int] = []
                    for first_local, second_local, _ in Tet10Element.edge_nodes:
                        first_global, second_global = corners[first_local], corners[second_local]
                        key = (min(first_global, second_global), max(first_global, second_global))
                        if key not in edge_node:
                            edge_node[key] = len(coordinates)
                            coordinates.append(
                                (0.5 * (np.asarray(coordinates[first_global]) + np.asarray(coordinates[second_global]))).tolist()
                            )
                        mids.append(edge_node[key])
                    elements.append(corners + mids)
    return np.asarray(coordinates, dtype=np.float64), np.asarray(elements, dtype=np.int64)


def mesh_for_case(
    family: str,
    geometry: str,
    mesh: str,
) -> tuple[np.ndarray, np.ndarray, tuple[float, float, float], tuple[int, int, int]]:
    family = family.upper()
    if family not in FAMILIES or geometry not in GEOMETRIES or mesh not in MESHES:
        raise ValueError("Unknown family, geometry, or mesh in expanded WP12 case.")
    dimensions = GEOMETRIES[geometry]
    divisions = MESHES[mesh]
    if family in {"HEX8", "HEX20"}:
        coordinates, connectivity = _hex_connectivity(family, dimensions, divisions)
    else:
        coordinates, connectivity = _tet_connectivity(family, dimensions, divisions)
    return coordinates, connectivity, dimensions, divisions


def _triangle_area(points: np.ndarray) -> float:
    return 0.5 * float(np.linalg.norm(np.cross(points[1] - points[0], points[2] - points[0])))


def _hex_face_loads(
    family: str,
    coordinates: np.ndarray,
    connectivity: np.ndarray,
    length: float,
) -> tuple[np.ndarray, float]:
    load_weights: np.ndarray = np.zeros(len(coordinates), dtype=np.float64)
    face_elements: list[np.ndarray] = []
    for element_nodes in connectivity:
        local_x = coordinates[element_nodes, 0]
        face_count = 4 if family == "HEX8" else 8
        if int(np.count_nonzero(np.isclose(local_x, length, rtol=0.0, atol=1.0e-12))) == face_count:
            face_elements.append(element_nodes)
    if not face_elements:
        raise ValueError(f"{family}: distal traction face is empty.")

    total_area = 0.0
    quadrature_records: list[tuple[np.ndarray, np.ndarray, float]] = []
    for element_nodes in face_elements:
        local_coordinates = coordinates[element_nodes]
        for eta, weight_eta in SURFACE_GAUSS:
            for zeta, weight_zeta in SURFACE_GAUSS:
                point = (1.0, eta, zeta)
                if family == "HEX8":
                    shape = Hex8Element.shape_functions(point)
                    derivative = Hex8Element.shape_derivatives_reference(point)
                else:
                    shape = Hex20Element.shape_functions(point)
                    derivative = Hex20Element.shape_derivatives_reference(point)
                tangent_eta = derivative[:, 1] @ local_coordinates
                tangent_zeta = derivative[:, 2] @ local_coordinates
                surface_jacobian = float(np.linalg.norm(np.cross(tangent_eta, tangent_zeta)))
                weighted_jacobian = surface_jacobian * weight_eta * weight_zeta
                total_area += weighted_jacobian
                quadrature_records.append((element_nodes, shape, weighted_jacobian))
    if not np.isfinite(total_area) or total_area <= 0.0:
        raise ValueError(f"{family}: invalid distal face area {total_area}.")
    for element_nodes, shape, weighted_jacobian in quadrature_records:
        load_weights[element_nodes] += shape * weighted_jacobian / total_area
    return load_weights, total_area


def _tet_face_loads(
    family: str,
    coordinates: np.ndarray,
    connectivity: np.ndarray,
    length: float,
) -> tuple[np.ndarray, float]:
    load_weights: np.ndarray = np.zeros(len(coordinates), dtype=np.float64)
    face_records: list[tuple[np.ndarray, float]] = []
    edge_local_index = {(min(a, b), max(a, b)): middle for a, b, middle in Tet10Element.edge_nodes}
    for element_nodes in connectivity:
        corner_x = coordinates[element_nodes[:4], 0]
        face_corners = [index for index, value in enumerate(corner_x) if np.isclose(value, length, rtol=0.0, atol=1.0e-12)]
        if len(face_corners) != 3:
            continue
        global_face_corners = np.asarray([element_nodes[index] for index in face_corners], dtype=np.int64)
        area = _triangle_area(coordinates[global_face_corners])
        if area <= 0.0:
            raise ValueError(f"{family}: invalid distal triangular face area {area}.")
        if family == "TET4":
            face_records.append((global_face_corners, area))
        else:
            mid_nodes = [
                int(element_nodes[edge_local_index[(min(first, second), max(first, second))]])
                for position, first in enumerate(face_corners)
                for second in face_corners[position + 1 :]
            ]
            face_records.append((np.asarray(mid_nodes, dtype=np.int64), area))
    if not face_records:
        raise ValueError(f"{family}: distal traction face is empty.")
    total_area = sum(area for _, area in face_records)
    for nodes, area in face_records:
        # Consistent integration of constant traction: T3 gets A/3 at each
        # corner; T6 gets A/3 at each edge midpoint and zero at corners.
        load_weights[nodes] += area / 3.0 / total_area
    return load_weights, total_area


def _equivalent_nodal_loads(
    family: str,
    coordinates: np.ndarray,
    connectivity: np.ndarray,
    dimensions: tuple[float, float, float],
    resultant: tuple[float, float, float],
) -> tuple[np.ndarray, float, tuple[float, float, float]]:
    if family.startswith("HEX"):
        scalar_loads, area = _hex_face_loads(family, coordinates, connectivity, dimensions[0])
    else:
        scalar_loads, area = _tet_face_loads(family, coordinates, connectivity, dimensions[0])
    loads = scalar_loads[:, None] * np.asarray(resultant, dtype=np.float64)[None, :]
    moment = np.sum(np.cross(coordinates, loads), axis=0)
    return loads, area, (float(moment[0]), float(moment[1]), float(moment[2]))


def model_fingerprint(
    family: str,
    coordinates: np.ndarray,
    connectivity: np.ndarray,
    fixed: np.ndarray,
    loads: np.ndarray,
    material: dict[str, Any],
) -> str:
    digest = hashlib.sha256()
    digest.update(family.encode("ascii"))
    for values, dtype in (
        (coordinates, np.float64),
        (connectivity, np.int64),
        (fixed, np.int64),
        (loads, np.float64),
    ):
        array = np.asarray(values, dtype=dtype)
        digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
        digest.update(array.tobytes(order="C"))
    digest.update(json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return digest.hexdigest()


def build_case(family: str, geometry: str, mesh: str, load_case: str) -> ExpandedCase:
    family = family.upper()
    if load_case not in LOADS:
        raise ValueError(f"Unknown load case {load_case!r}.")
    coordinates, connectivity, dimensions, divisions = mesh_for_case(family, geometry, mesh)
    resultant = LOADS[load_case]
    nodal_loads, load_area, load_moment = _equivalent_nodal_loads(
        family, coordinates, connectivity, dimensions, resultant
    )
    fixed_nodes = np.flatnonzero(np.isclose(coordinates[:, 0], 0.0, rtol=0.0, atol=1.0e-12))
    elements = [{"type": family, "nodes": row.tolist(), "material": "solid"} for row in connectivity]
    loads = [
        {"node": int(node), "dof": dof, "value": float(nodal_loads[node, axis])}
        for node in range(len(coordinates))
        for axis, dof in enumerate(("UX", "UY", "UZ"))
        if nodal_loads[node, axis] != 0.0
    ]
    model = FiniteElementModel.from_raw(
        nodes=coordinates.tolist(),
        elements=elements,
        materials={"solid": dict(MATERIAL)},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=loads,
        analysis={"type": "linear_static", "method": "direct"},
        units={"system": "SI"},
        verification_profile="wp12_expanded_linear_static_correlation_r3",
    )
    system = assemble_linear_system(model)
    fingerprint = model_fingerprint(family, coordinates, connectivity, system.fixed, system.loads, MATERIAL)
    case_id = f"{family.lower()}_{geometry.lower()}_{mesh.lower()}_{load_case.lower()}"
    return ExpandedCase(
        case_id=case_id,
        family=family,
        geometry=geometry,
        dimensions=dimensions,
        mesh=mesh,
        divisions=divisions,
        load_case=load_case,
        resultant=resultant,
        model=model,
        system=system,
        connectivity=connectivity,
        fingerprint=fingerprint,
        load_area=load_area,
        load_moment=load_moment,
    )


def case_catalog() -> list[ExpandedCase]:
    return [
        build_case(family, geometry, mesh, load_case)
        for family in FAMILIES
        for geometry in GEOMETRIES
        for mesh in MESHES
        for load_case in LOADS
    ]
