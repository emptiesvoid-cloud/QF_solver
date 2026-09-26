"""Preparation-only mesh and load preflight for a WP08 area-contact coupon.

This module generates geometry and checks reference measures only.  It never
builds a solver model or executes a structural/contact solve.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any

import numpy as np


LENGTH_M = 2.0
WIDTH_M = 1.0
HEIGHT_M = 0.5
INITIAL_GAP_M = 5.0e-4
YOUNG_MODULUS_PA = 1.0e6
POISSON_RATIO = 0.3
FRICTION_COEFFICIENT = 0.3
TANGENTIAL_STIFFNESS_DENSITY_N_PER_M3 = 2_666_700.0
NORMAL_RESULTANT_N = 1_000.0
STICK_TANGENTIAL_RESULTANT_N = 150.0
SLIP_TANGENTIAL_RESULTANT_N = 450.0


@dataclass(frozen=True)
class MeshLevel:
    name: str
    nx: int
    ny: int
    nz: int


MESH_LEVELS = (
    MeshLevel("M1", 2, 1, 1),
    MeshLevel("M2", 4, 2, 2),
    MeshLevel("M3", 8, 4, 4),
)


def _node_id(i: int, j: int, k: int, level: MeshLevel) -> int:
    return (k * (level.ny + 1) + j) * (level.nx + 1) + i


def _signed_tet_volume(coordinates: np.ndarray) -> float:
    edges = np.column_stack(
        (coordinates[1] - coordinates[0], coordinates[2] - coordinates[0], coordinates[3] - coordinates[0])
    )
    return float(np.linalg.det(edges) / 6.0)


def _oriented_tet(tet: tuple[int, int, int, int], nodes: np.ndarray) -> tuple[int, int, int, int]:
    volume = _signed_tet_volume(nodes[list(tet)])
    if volume < 0.0:
        tet = (tet[0], tet[1], tet[3], tet[2])
        volume = _signed_tet_volume(nodes[list(tet)])
    if not np.isfinite(volume) or volume <= 0.0:
        raise ValueError(f"Invalid TET4 orientation or volume: {volume!r}")
    return tet


def _boundary_faces(elements: tuple[tuple[int, int, int, int], ...]) -> tuple[tuple[int, int, int], ...]:
    faces: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    counts: dict[tuple[int, int, int], int] = {}
    for a, b, c, d in elements:
        for face in ((a, b, c), (a, b, d), (a, c, d), (b, c, d)):
            ordered = sorted(face)
            key = (ordered[0], ordered[1], ordered[2])
            counts[key] = counts.get(key, 0) + 1
            faces[key] = face
    if any(count not in (1, 2) for count in counts.values()):
        raise ValueError("TET4 topology contains a non-manifold face.")
    return tuple(faces[key] for key, count in counts.items() if count == 1)


def _triangle_area(nodes: np.ndarray, face: tuple[int, int, int]) -> float:
    a, b, c = nodes[list(face)]
    return 0.5 * float(np.linalg.norm(np.cross(b - a, c - a)))


def _surface_geometry(
    level: MeshLevel,
) -> tuple[np.ndarray, tuple[tuple[int, int, int, int], ...], tuple[tuple[int, int, int], ...], tuple[int, ...], tuple[int, ...]]:
    body = np.asarray(
        [
            [LENGTH_M * i / level.nx, WIDTH_M * j / level.ny, HEIGHT_M * k / level.nz]
            for k in range(level.nz + 1)
            for j in range(level.ny + 1)
            for i in range(level.nx + 1)
        ],
        dtype=float,
    )
    elements: list[tuple[int, int, int, int]] = []
    for k in range(level.nz):
        for j in range(level.ny):
            for i in range(level.nx):
                v000 = _node_id(i, j, k, level)
                v100 = _node_id(i + 1, j, k, level)
                v110 = _node_id(i + 1, j + 1, k, level)
                v010 = _node_id(i, j + 1, k, level)
                v001 = _node_id(i, j, k + 1, level)
                v101 = _node_id(i + 1, j, k + 1, level)
                v111 = _node_id(i + 1, j + 1, k + 1, level)
                v011 = _node_id(i, j + 1, k + 1, level)
                raw = (
                    (v000, v100, v110, v111),
                    (v000, v110, v010, v111),
                    (v000, v010, v011, v111),
                    (v000, v011, v001, v111),
                    (v000, v001, v101, v111),
                    (v000, v101, v100, v111),
                )
                elements.extend(_oriented_tet(tet, body) for tet in raw)
    tets = tuple(elements)
    boundary = _boundary_faces(tets)
    slave_faces = tuple(
        face for face in boundary if np.allclose(body[list(face), 0], LENGTH_M, rtol=0.0, atol=1.0e-14)
    )
    slave_nodes = tuple(
        _node_id(level.nx, j, k, level)
        for k in range(level.nz + 1)
        for j in range(level.ny + 1)
    )
    fixed_nodes = tuple(
        _node_id(0, j, k, level)
        for k in range(level.nz + 1)
        for j in range(level.ny + 1)
    )
    if not slave_faces or not slave_nodes:
        raise ValueError("The candidate contact face must be nonempty.")
    if set(slave_nodes).intersection(fixed_nodes):
        raise ValueError("The contact interface overlaps the fixed face.")
    return body, tets, slave_faces, slave_nodes, fixed_nodes


def generate_preflight(level: MeshLevel) -> dict[str, Any]:
    """Generate one candidate coupon and report geometry without solving it."""
    body, tets, slave_faces, slave_nodes, fixed_nodes = _surface_geometry(level)
    body_count = len(body)

    area_by_node = {node: 0.0 for node in slave_nodes}
    total_area = 0.0
    for face in slave_faces:
        area = _triangle_area(body, face)
        if area <= 0.0 or not np.isfinite(area):
            raise ValueError("The contact patch contains a degenerate triangle.")
        total_area += area
        for node in face:
            area_by_node[node] += area / 3.0
    if set(area_by_node) != set(slave_nodes) or any(value <= 0.0 for value in area_by_node.values()):
        raise ValueError("Every slave node must receive positive reference area.")

    contact_coordinates = body[list(slave_nodes)]
    centered = contact_coordinates - np.mean(contact_coordinates, axis=0)
    support_rank = int(np.linalg.matrix_rank(centered))
    projection_covered = bool(
        np.all((contact_coordinates[:, 1] >= 0.0) & (contact_coordinates[:, 1] <= WIDTH_M))
        and np.all((contact_coordinates[:, 2] >= 0.0) & (contact_coordinates[:, 2] <= HEIGHT_M))
    )
    master = np.asarray(
        [
            [LENGTH_M + INITIAL_GAP_M, 0.0, 0.0],
            [LENGTH_M + INITIAL_GAP_M, 0.0, HEIGHT_M],
            [LENGTH_M + INITIAL_GAP_M, WIDTH_M, HEIGHT_M],
            [LENGTH_M + INITIAL_GAP_M, WIDTH_M, 0.0],
        ],
        dtype=float,
    )
    master_normals = []
    for face in ((0, 1, 2), (0, 2, 3)):
        triangle = master[list(face)]
        normal = np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
        master_normals.append((normal / np.linalg.norm(normal)).tolist())

    integrated_stiffness = TANGENTIAL_STIFFNESS_DENSITY_N_PER_M3 * total_area
    free_axial_displacement = NORMAL_RESULTANT_N * LENGTH_M / (YOUNG_MODULUS_PA * WIDTH_M * HEIGHT_M)
    first_step_free_displacement = 0.25 * free_axial_displacement

    def load_case(name: str, tangent: float) -> dict[str, Any]:
        force = np.asarray([NORMAL_RESULTANT_N, tangent, 0.0])
        nodal_loads = []
        integrated_force = np.zeros(3)
        integrated_moment = np.zeros(3)
        for node, nodal_area in area_by_node.items():
            nodal_force = force * (nodal_area / total_area)
            integrated_force += nodal_force
            integrated_moment += np.cross(body[node], nodal_force)
            nodal_loads.append({"node": node, "force_N": nodal_force.tolist()})
        return {
            "case": name,
            "resultant_N": force.tolist(),
            "moment_about_origin_Nm": integrated_moment.tolist(),
            "integrated_nodal_resultant_N": integrated_force.tolist(),
            "integrated_nodal_moment_about_origin_Nm": integrated_moment.tolist(),
            "nodal_loads": nodal_loads,
            "tangential_to_friction_capacity_ratio": tangent
            / (FRICTION_COEFFICIENT * NORMAL_RESULTANT_N),
        }

    volumes = np.asarray([_signed_tet_volume(body[list(tet)]) for tet in tets])
    return {
        "mesh": asdict(level),
        "node_count": body_count + len(master),
        "body_node_count": body_count,
        "element_count": len(tets),
        "body_dofs": 3 * body_count,
        "total_dofs_including_rigid_master_metadata": 3 * (body_count + len(master)),
        "contact_slave_node_count": len(slave_nodes),
        "contact_face_count": len(slave_faces),
        "contact_support_affine_rank": support_rank,
        "all_slave_nodes_project_inside_master_patch": projection_covered,
        "contact_patch_area_m2": total_area,
        "expected_contact_patch_area_m2": WIDTH_M * HEIGHT_M,
        "all_slave_nodes_have_positive_area": all(value > 0.0 for value in area_by_node.values()),
        "fixed_contact_node_intersection_count": len(set(slave_nodes).intersection(fixed_nodes)),
        "minimum_tributary_area_m2": min(area_by_node.values()),
        "maximum_tributary_area_m2": max(area_by_node.values()),
        "slave_tributary_areas_m2": {str(node): area for node, area in area_by_node.items()},
        "integrated_tangential_stiffness_N_per_m": integrated_stiffness,
        "minimum_tet_volume_m3": float(np.min(volumes)),
        "total_volume_m3": float(np.sum(volumes)),
        "master_normals": master_normals,
        "initial_gap_m": INITIAL_GAP_M,
        "one_dimensional_free_axial_displacement_estimate_m": free_axial_displacement,
        "first_normal_step_free_displacement_estimate_m": first_step_free_displacement,
        "first_step_estimate_exceeds_gap": first_step_free_displacement > INITIAL_GAP_M,
        "load_cases": [
            load_case("stick_target", STICK_TANGENTIAL_RESULTANT_N),
            load_case("slip_target", SLIP_TANGENTIAL_RESULTANT_N),
        ],
    }


def preflight_record() -> dict[str, Any]:
    levels = [generate_preflight(level) for level in MESH_LEVELS]
    area = WIDTH_M * HEIGHT_M
    expected_k = TANGENTIAL_STIFFNESS_DENSITY_N_PER_M3 * area
    return {
        "schema": "qf.wp08.area_supported_benchmark_preflight.v1",
        "status": "PREPARATION_ONLY_OWNER_REVIEW_REQUIRED",
        "structural_solves_authorized": False,
        "production_mechanics_changed": False,
        "thresholds_changed": False,
        "definition": {
            "element": "TET4",
            "geometry_m": {"length_x": LENGTH_M, "width_y": WIDTH_M, "height_z": HEIGHT_M},
            "fixed_face": "x=0, all body nodes, UX/UY/UZ fixed",
            "contact_face": "x=length_x, all boundary nodes/faces; disjoint from fixed face",
            "rigid_master_plane": "x=length_x + initial_gap, normal points toward -x",
            "normal_contact": "existing bounded fixed-search node-to-triangle route",
            "tangential_law": "existing surface-lumped T3 reference-area law; no redistribution",
            "kappa_N_per_m3": TANGENTIAL_STIFFNESS_DENSITY_N_PER_M3,
            "friction_coefficient": FRICTION_COEFFICIENT,
            "young_modulus_Pa": YOUNG_MODULUS_PA,
            "poisson_ratio": POISSON_RATIO,
            "normal_resultant_N": [NORMAL_RESULTANT_N, 0.0, 0.0],
            "tangential_cases_N": {
                "stick_target": STICK_TANGENTIAL_RESULTANT_N,
                "slip_target": SLIP_TANGENTIAL_RESULTANT_N,
            },
            "mesh_levels": [asdict(level) for level in MESH_LEVELS],
        },
        "constant_target_integrated_stiffness_N_per_m": expected_k,
        "levels": levels,
        "gates_before_any_formal_run": [
            "Owner freezes geometry, gap, BCs, load cases, load path, and thresholds prospectively.",
            "M1 diagnostic must show a two-dimensional active support; otherwise stop before M2/M3.",
            "Active-support area and integrated tangential stiffness are reported separately.",
            "No full-area renormalization and no change to kappa after observing results.",
            "Independent reference scope and replay requirements are frozen before execution.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(preflight_record(), indent=2, sort_keys=True))
