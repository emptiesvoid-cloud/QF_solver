"""Preparation-only WP08-D frictional structural/reference contract helpers.

This module generates deterministic TET4 mesh metadata and load-integration
checks.  It deliberately does not call a contact or structural solver.  The
only numerical precheck is the permitted M1 no-contact stiffness assembly.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import numpy as np

from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel


SOURCE_SHA = "604d3a4a6d533c3b12642c0d00b0fa75e9cd033f"
HISTORICAL_SOURCE_SHA = "502dd1f7b1f19f37e1929ae9a6107ee1a4f9e514"
CONTROLLED_BRANCH = "0.2.9-wp08-controlled-integration"
GOVERNING_BASE_SHA = "7b93e71bab06a0e58108bd2479cd46808d533b67"
GOVERNING_POLICY_DIGEST = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
LENGTH = 2.0
WIDTH = 1.0
HEIGHT = 0.5
INITIAL_CLEARANCE = 0.02
TOP_Z = INITIAL_CLEARANCE + HEIGHT
YOUNG_MODULUS = 1.0e6
POISSON_RATIO = 0.3
FRICTION_COEFFICIENT = 0.3
TANGENTIAL_STIFFNESS = 1.0e6
GAP_TOLERANCE = 1.0e-10
FRICTION_TOLERANCE = 1.0e-9
NORMAL_RESULTANT = np.array([0.0, 0.0, -1000.0], dtype=float)
TANGENTIAL_RESULTANT = np.array([300.0, 0.0, 0.0], dtype=float)
LOAD_RELATIVE_TOLERANCE = 1.0e-12
MACHINE_SCALE_MULTIPLIER = 64.0


@dataclass(frozen=True)
class MeshLevel:
    """One frozen structured subdivision of the deformable block."""

    name: str
    nx: int
    ny: int
    nz: int

    @property
    def cell_count(self) -> int:
        return self.nx * self.ny * self.nz

    @property
    def tet_count(self) -> int:
        return 6 * self.cell_count

    @property
    def body_node_count(self) -> int:
        return (self.nx + 1) * (self.ny + 1) * (self.nz + 1)


@dataclass(frozen=True)
class StructuralMesh:
    """Generated body plus the rigid master surface node metadata."""

    level: MeshLevel
    nodes: np.ndarray
    elements: tuple[tuple[int, int, int, int], ...]
    top_faces: tuple[tuple[int, int, int], ...]
    bottom_faces: tuple[tuple[int, int, int], ...]
    master_nodes: tuple[int, int, int, int]
    master_faces: tuple[tuple[int, int, int], ...]
    slave_nodes: tuple[int, ...]
    slave_face_map: tuple[tuple[int, int], ...]
    fixed_body_nodes: tuple[int, ...]

    @property
    def body_nodes(self) -> np.ndarray:
        return self.nodes[: self.level.body_node_count]


MESH_LEVELS = (
    MeshLevel("M1", nx=2, ny=1, nz=1),
    MeshLevel("M2", nx=4, ny=2, nz=2),
    MeshLevel("M3", nx=8, ny=4, nz=4),
)


def _node_index(i: int, j: int, k: int, level: MeshLevel) -> int:
    return (k * (level.ny + 1) + j) * (level.nx + 1) + i


def _signed_tet_volume(coords: np.ndarray) -> float:
    matrix = np.column_stack((coords[1] - coords[0], coords[2] - coords[0], coords[3] - coords[0]))
    return float(np.linalg.det(matrix) / 6.0)


def _oriented_tet(tet: tuple[int, int, int, int], nodes: np.ndarray) -> tuple[int, int, int, int]:
    signed = _signed_tet_volume(nodes[list(tet)])
    if signed < 0.0:
        tet = (tet[0], tet[1], tet[3], tet[2])
        signed = _signed_tet_volume(nodes[list(tet)])
    if signed <= 0.0 or not np.isfinite(signed):
        raise ValueError(f"Invalid generated TET4 orientation/volume: {signed!r}.")
    return tet


def _tet_boundary_faces(elements: tuple[tuple[int, int, int, int], ...]) -> tuple[tuple[int, int, int], ...]:
    counts: dict[tuple[int, int, int], int] = {}
    for a, b, c, d in elements:
        for face in ((a, b, c), (a, b, d), (a, c, d), (b, c, d)):
            ordered = sorted(face)
            key: tuple[int, int, int] = (ordered[0], ordered[1], ordered[2])
            counts[key] = counts.get(key, 0) + 1
    return tuple(sorted(face for face, count in counts.items() if count == 1))


def _barycentric(point: np.ndarray, triangle: np.ndarray) -> np.ndarray:
    edge_1 = triangle[1] - triangle[0]
    edge_2 = triangle[2] - triangle[0]
    relative = point - triangle[0]
    gram = np.array(
        [
            [edge_1 @ edge_1, edge_1 @ edge_2],
            [edge_1 @ edge_2, edge_2 @ edge_2],
        ],
        dtype=float,
    )
    rhs = np.array([relative @ edge_1, relative @ edge_2], dtype=float)
    xi_eta = np.linalg.solve(gram, rhs)
    return np.array([1.0 - xi_eta[0] - xi_eta[1], xi_eta[0], xi_eta[1]], dtype=float)


def _master_face_for(point: np.ndarray) -> int:
    """Select the lower/upper master triangle deterministically on the diagonal."""
    normalized_x = float(point[0]) / LENGTH
    normalized_y = float(point[1]) / WIDTH
    return 0 if normalized_y <= normalized_x + 1.0e-12 else 1


def generate_mesh(level: MeshLevel) -> StructuralMesh:
    """Generate the frozen structured TET4 body and two-facet master plane."""
    body_coordinates = [
        [LENGTH * i / level.nx, WIDTH * j / level.ny, INITIAL_CLEARANCE + HEIGHT * k / level.nz]
        for k in range(level.nz + 1)
        for j in range(level.ny + 1)
        for i in range(level.nx + 1)
    ]
    body_nodes = np.asarray(body_coordinates, dtype=float)
    master_coordinates = np.array(
        [[0.0, 0.0, 0.0], [LENGTH, 0.0, 0.0], [LENGTH, WIDTH, 0.0], [0.0, WIDTH, 0.0]],
        dtype=float,
    )
    nodes = np.vstack((body_nodes, master_coordinates))
    body_count = level.body_node_count
    master_nodes: tuple[int, int, int, int] = (body_count, body_count + 1, body_count + 2, body_count + 3)
    master_faces = (
        (master_nodes[0], master_nodes[1], master_nodes[2]),
        (master_nodes[0], master_nodes[2], master_nodes[3]),
    )

    elements: list[tuple[int, int, int, int]] = []
    for k in range(level.nz):
        for j in range(level.ny):
            for i in range(level.nx):
                v000 = _node_index(i, j, k, level)
                v100 = _node_index(i + 1, j, k, level)
                v110 = _node_index(i + 1, j + 1, k, level)
                v010 = _node_index(i, j + 1, k, level)
                v001 = _node_index(i, j, k + 1, level)
                v101 = _node_index(i + 1, j, k + 1, level)
                v111 = _node_index(i + 1, j + 1, k + 1, level)
                v011 = _node_index(i, j + 1, k + 1, level)
                raw = (
                    (v000, v100, v110, v111),
                    (v000, v110, v010, v111),
                    (v000, v010, v011, v111),
                    (v000, v011, v001, v111),
                    (v000, v001, v101, v111),
                    (v000, v101, v100, v111),
                )
                elements.extend(_oriented_tet(tet, nodes) for tet in raw)

    connectivity = tuple(elements)
    boundary = _tet_boundary_faces(connectivity)
    top_faces = tuple(
        face for face in boundary if np.allclose(nodes[list(face), 2], TOP_Z, rtol=0.0, atol=1.0e-14)
    )
    bottom_faces = tuple(
        face for face in boundary if np.allclose(nodes[list(face), 2], INITIAL_CLEARANCE, rtol=0.0, atol=1.0e-14)
    )
    slave_nodes = tuple(
        _node_index(i, j, 0, level)
        for j in range(level.ny + 1)
        for i in range(1, level.nx + 1)
    )
    slave_face_map = tuple((node, _master_face_for(nodes[node])) for node in slave_nodes)
    fixed_body_nodes = tuple(
        _node_index(0, j, k, level)
        for k in range(level.nz + 1)
        for j in range(level.ny + 1)
    )
    return StructuralMesh(
        level=level,
        nodes=nodes,
        elements=connectivity,
        top_faces=top_faces,
        bottom_faces=bottom_faces,
        master_nodes=master_nodes,
        master_faces=master_faces,
        slave_nodes=slave_nodes,
        slave_face_map=slave_face_map,
        fixed_body_nodes=fixed_body_nodes,
    )


def _surface_area(nodes: np.ndarray, faces: tuple[tuple[int, int, int], ...]) -> float:
    return float(
        sum(
            0.5 * np.linalg.norm(np.cross(nodes[face[1]] - nodes[face[0]], nodes[face[2]] - nodes[face[0]]))
            for face in faces
        )
    )


def consistent_surface_traction(
    mesh: StructuralMesh,
    faces: tuple[tuple[int, int, int], ...],
    resultant: np.ndarray,
) -> dict[str, Any]:
    """Integrate a constant traction on T3 faces with area/3 nodal weights."""
    area = _surface_area(mesh.nodes, faces)
    if area <= 0.0 or not np.isfinite(area):
        raise ValueError("Surface area must be finite and positive.")
    traction = np.asarray(resultant, dtype=float) / area
    nodal_forces = np.zeros((mesh.nodes.shape[0], 3), dtype=float)
    for face in faces:
        coordinates = mesh.nodes[list(face)]
        face_area = 0.5 * np.linalg.norm(np.cross(coordinates[1] - coordinates[0], coordinates[2] - coordinates[0]))
        contribution = traction * face_area / 3.0
        for node in face:
            nodal_forces[node] += contribution
    observed_resultant = np.sum(nodal_forces, axis=0)
    observed_moment = np.sum(np.cross(mesh.nodes, nodal_forces), axis=0)
    return {
        "area": area,
        "traction": traction,
        "nodal_forces": nodal_forces,
        "resultant": observed_resultant,
        "moment_about_origin": observed_moment,
    }


def _vector_error(observed: np.ndarray, expected: np.ndarray) -> dict[str, Any]:
    observed = np.asarray(observed, dtype=float)
    expected = np.asarray(expected, dtype=float)
    absolute_error = float(np.linalg.norm(observed - expected))
    scale = max(float(np.linalg.norm(expected)), 1.0)
    absolute_floor = float(MACHINE_SCALE_MULTIPLIER * np.finfo(float).eps * scale)
    allowed = float(max(LOAD_RELATIVE_TOLERANCE * scale, absolute_floor))
    return {
        "observed": observed,
        "expected": expected,
        "absolute_error": absolute_error,
        "relative_error": absolute_error / scale,
        "absolute_floor": absolute_floor,
        "allowed": allowed,
        "status": "PASS" if absolute_error <= allowed else "FAIL",
    }


def load_contract(mesh: StructuralMesh) -> dict[str, Any]:
    """Return normal/tangential load checks and analytical origin moments."""
    centroid = np.array([LENGTH / 2.0, WIDTH / 2.0, TOP_Z], dtype=float)
    expected = {
        "normal": (NORMAL_RESULTANT, np.cross(centroid, NORMAL_RESULTANT)),
        "tangential": (TANGENTIAL_RESULTANT, np.cross(centroid, TANGENTIAL_RESULTANT)),
    }
    result: dict[str, Any] = {"top_area": _surface_area(mesh.nodes, mesh.top_faces), "centroid": centroid}
    for name, (resultant, moment) in expected.items():
        observed = consistent_surface_traction(mesh, mesh.top_faces, resultant)
        result[name] = {
            "traction": observed["traction"],
            "resultant": _vector_error(observed["resultant"], resultant),
            "moment": _vector_error(observed["moment_about_origin"], moment),
        }
    return result


def mesh_contract(mesh: StructuralMesh) -> dict[str, Any]:
    """Return no-solve geometry, orientation and contact coverage checks."""
    volumes = np.asarray([_signed_tet_volume(mesh.nodes[list(tet)]) for tet in mesh.elements], dtype=float)
    coverage_values = [
        _barycentric(mesh.nodes[node], mesh.nodes[list(mesh.master_faces[face_index])])
        for node, face_index in mesh.slave_face_map
    ]
    coverage = bool(coverage_values) and all(float(np.min(value)) >= -1.0e-12 for value in coverage_values)
    total_node_count = int(mesh.nodes.shape[0])
    return {
        "level": mesh.level.name,
        "subdivision": {"nx": mesh.level.nx, "ny": mesh.level.ny, "nz": mesh.level.nz},
        "nodes": total_node_count,
        "body_nodes": mesh.level.body_node_count,
        "elements": len(mesh.elements),
        "dofs": 3 * total_node_count,
        "body_dofs": 3 * mesh.level.body_node_count,
        "contact_slave_count": len(mesh.slave_nodes),
        "master_facet_count": len(mesh.master_faces),
        "top_face_count": len(mesh.top_faces),
        "bottom_face_count": len(mesh.bottom_faces),
        "volume": float(np.sum(volumes)),
        "minimum_signed_tet_volume": float(np.min(volumes)),
        "finite_coordinates": bool(np.isfinite(mesh.nodes).all()),
        "positive_reference_volumes": bool(np.all(volumes > 0.0)),
        "master_projection_coverage": coverage,
        "slave_face_map": [list(item) for item in mesh.slave_face_map],
        "fixed_body_nodes": list(mesh.fixed_body_nodes),
        "master_nodes": list(mesh.master_nodes),
        "master_faces": [list(face) for face in mesh.master_faces],
    }


def _no_contact_model(mesh: StructuralMesh) -> FiniteElementModel:
    elements = [{"type": "TET4", "nodes": list(tet), "material": "elastic"} for tet in mesh.elements]
    fixed_dofs = [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in mesh.fixed_body_nodes]
    return FiniteElementModel.from_raw(
        nodes=mesh.nodes.tolist(),
        elements=elements,
        materials={"elastic": {"type": "isotropic_3d", "E": YOUNG_MODULUS, "nu": POISSON_RATIO}},
        fixed_dofs=fixed_dofs,
        loads=[],
        analysis={"type": "linear_static", "method": "direct"},
    )


def no_contact_well_posedness(mesh: StructuralMesh) -> dict[str, Any]:
    """Assemble and inspect the permitted M1 no-contact reduced stiffness only."""
    if mesh.level.name != "M1":
        raise ValueError("The Phase-0 well-posedness precheck is frozen to M1.")
    model = _no_contact_model(mesh)
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    stiffness = assembler.assemble_stiffness(model, dofs)
    fixed = assembler.fixed_indices(model, dofs)
    free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
    reduced = np.asarray(stiffness[free, :][:, free].toarray(), dtype=float)
    symmetric = 0.5 * (reduced + reduced.T)
    eigenvalues = np.linalg.eigvalsh(symmetric)
    scale = max(float(np.linalg.norm(symmetric, ord=2)), 1.0)
    numerical_zero = MACHINE_SCALE_MULTIPLIER * np.finfo(float).eps * scale
    minimum_eigenvalue = float(np.min(eigenvalues))
    maximum_eigenvalue = float(np.max(eigenvalues))
    passed = bool(np.isfinite(reduced).all() and eigenvalues.size > 0 and minimum_eigenvalue > numerical_zero)
    return {
        "status": "PASS" if passed else "FAIL",
        "reduced_dof": int(free.size),
        "matrix_shape": [int(value) for value in reduced.shape],
        "matrix_nnz": int(stiffness[free, :][:, free].nnz),
        "minimum_eigenvalue": minimum_eigenvalue,
        "maximum_eigenvalue": maximum_eigenvalue,
        "numerical_zero_threshold": numerical_zero,
        "finite_matrix": bool(np.isfinite(reduced).all()),
        "contact_terms_included": False,
        "solve_performed": False,
    }


def phase0_execution_guard(
    *,
    structural_solves_enabled: bool = False,
    external_solver_enabled: bool = False,
    owner_phase1_authorized: bool = False,
) -> None:
    """Fail closed when preparation code is asked to execute without Owner authorization."""
    if (structural_solves_enabled or external_solver_enabled) and not owner_phase1_authorized:
        raise RuntimeError("WP08-D Phase-0 preparation cannot execute solves without explicit Phase-1 authorization.")


def _jsonable(value: object) -> object:
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def phase0_report() -> dict[str, Any]:
    """Build a no-solve preparation report for manual Owner inspection."""
    meshes = [generate_mesh(level) for level in MESH_LEVELS]
    return {
        "artifact_id": "QF-SOLVER-0.2.9-WP08D-001",
        "source_sha": SOURCE_SHA,
        "historical_source_sha": HISTORICAL_SOURCE_SHA,
        "branch": CONTROLLED_BRANCH,
        "governing_base_sha": GOVERNING_BASE_SHA,
        "governing_policy_digest": GOVERNING_POLICY_DIGEST,
        "status": "PREPARATION_ONLY",
        "structural_solves_enabled": False,
        "external_solver_enabled": False,
        "levels": [
            {"mesh": mesh_contract(mesh), "loads": load_contract(mesh)}
            for mesh in meshes
        ],
        "no_contact_well_posedness": no_contact_well_posedness(meshes[0]),
    }


if __name__ == "__main__":
    print(json.dumps(_jsonable(phase0_report()), indent=2, sort_keys=True))
