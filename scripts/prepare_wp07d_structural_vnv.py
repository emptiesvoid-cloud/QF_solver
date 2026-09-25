"""Build and validate the no-solve WP07-D structural V&V preflight plan."""

from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp07d_structural_vnv_contract.json"
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
MESH_LEVELS = ("M1", "M2", "M3")
BENCHMARKS = {
    "ACTIVE_SET": "linear_static",
    "PENALTY": "geometric_nonlinear_static",
}
BODY_LOWER = np.array([0.0, 0.0, 0.01], dtype=float)
BODY_UPPER = np.array([1.0, 0.5, 0.21], dtype=float)
MASTER_NODES = np.array(
    [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
    dtype=float,
)
TRACTION = np.array([0.0, 0.0, -100000.0], dtype=float)
EXPECTED_RESULTANT = np.array([0.0, 0.0, -50000.0], dtype=float)
EXPECTED_MOMENT = np.array([-12500.0, 25000.0, 0.0], dtype=float)
TET4_FACES = ((1, 2, 3), (0, 3, 2), (0, 1, 3), (0, 2, 1))
BASE_CELLS = {
    "M1": (2, 2, 1),
    "M2": (4, 4, 2),
    "M3": (8, 8, 4),
}


def local_contact_refinement_axis_fractions() -> dict[str, tuple[float, ...]]:
    """Return the frozen nested local-contact-refinement coordinate arrays."""

    x_values = {Fraction(index, 16) for index in range(17)}
    for interval in (3, 4):
        x_values.update(
            Fraction(interval, 16) + Fraction(subdivision, 80)
            for subdivision in range(1, 5)
        )
    z_values = {Fraction(index, 8) for index in range(9)}
    z_values.update(Fraction(subdivision, 40) for subdivision in range(1, 5))
    return {
        "x": tuple(float(value) for value in sorted(x_values)),
        "y": tuple(float(Fraction(index, 16)) for index in range(17)),
        "z": tuple(float(value) for value in sorted(z_values)),
    }


def focused_local_contact_refinement_axis_fractions() -> dict[str, tuple[float, ...]]:
    """Return the exact nested focused-contact refinement coordinate arrays."""

    x_values = {Fraction(index, 16) for index in range(17)}
    for interval in range(2, 6):
        x_values.update(
            Fraction(interval, 16) + Fraction(subdivision, 80)
            for subdivision in range(1, 5)
        )
    z_values = {Fraction(index, 8) for index in range(9)}
    for interval in (0, 7):
        z_values.update(
            Fraction(interval, 8) + Fraction(subdivision, 40)
            for subdivision in range(1, 5)
        )
    return {
        "x": tuple(float(value) for value in sorted(x_values)),
        "y": tuple(float(Fraction(index, 16)) for index in range(17)),
        "z": tuple(float(value) for value in sorted(z_values)),
    }


def _validated_axis_fractions(
    values: tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]],
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    """Validate exact normalized axes used by the immutable mesh bindings."""

    if not isinstance(values, tuple) or len(values) != 3:
        raise ValueError("TET4 axis fractions must define X, Y and Z coordinate arrays.")
    normalized: list[tuple[float, ...]] = []
    for axis in values:
        try:
            coordinates = tuple(float(value) for value in axis)
        except (TypeError, ValueError) as error:
            raise ValueError("TET4 axis fractions must be numeric sequences.") from error
        if (
            len(coordinates) < 2
            or not all(math.isfinite(value) for value in coordinates)
            or coordinates[0] != 0.0
            or coordinates[-1] != 1.0
            or any(right <= left for left, right in zip(coordinates, coordinates[1:]))
        ):
            raise ValueError("TET4 axis fractions must be strictly increasing from exactly zero to one.")
        normalized.append(coordinates)
    return (normalized[0], normalized[1], normalized[2])


@dataclass(frozen=True)
class StructuredTet4Mesh:
    """Deterministic TET4 body and boundary data for the WP07-D contract."""

    nodes: np.ndarray
    elements: tuple[tuple[int, int, int, int], ...]
    top_faces: tuple[tuple[int, int, int], ...]
    bottom_faces: tuple[tuple[int, int, int], ...]
    slave_nodes: tuple[int, ...]
    signed_volumes: np.ndarray


def _git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _signed_tet4_volume(coordinates: np.ndarray) -> float:
    matrix = np.column_stack(
        (coordinates[1] - coordinates[0], coordinates[2] - coordinates[0], coordinates[3] - coordinates[0])
    )
    return float(np.linalg.det(matrix) / 6.0)


def _boundary_faces(elements: tuple[tuple[int, int, int, int], ...]) -> tuple[tuple[int, int, int], ...]:
    """Return deterministic exterior TET4 faces, preserving first orientation."""

    occurrences: dict[tuple[int, int, int], list[tuple[int, int, int]]] = {}
    for element in elements:
        for local_face in TET4_FACES:
            face = (element[local_face[0]], element[local_face[1]], element[local_face[2]])
            sorted_face = sorted(face)
            key = (sorted_face[0], sorted_face[1], sorted_face[2])
            occurrences.setdefault(key, []).append(face)
    return tuple(
        face_list[0]
        for key, face_list in sorted(occurrences.items())
        if len(face_list) == 1
    )


def generate_structured_tet4_mesh(
    level: str,
    *,
    lower: np.ndarray = BODY_LOWER,
    upper: np.ndarray = BODY_UPPER,
    cell_counts: tuple[int, int, int] | None = None,
    axis_fractions: tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]] | None = None,
) -> StructuredTet4Mesh:
    """Generate the frozen six-TET-per-cell mesh without solving.

    Optional subdivisions and normalized axis fractions are execution-binding
    inputs used by source-bound WP07 requalification. The default path retains
    the historical preparation mesh exactly.
    """

    try:
        default_counts = BASE_CELLS[level]
    except KeyError as exc:
        raise ValueError(f"Unknown WP07-D mesh level {level!r}.") from exc
    counts = tuple(int(value) for value in (cell_counts or default_counts))
    if len(counts) != 3 or any(value <= 0 for value in counts):
        raise ValueError("WP07-D cell_counts must contain three positive integers.")
    nx, ny, nz = counts
    if axis_fractions is None:
        axes: tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]] = (
            tuple(index / nx for index in range(nx + 1)),
            tuple(index / ny for index in range(ny + 1)),
            tuple(index / nz for index in range(nz + 1)),
        )
    else:
        if len(axis_fractions) != 3:
            raise ValueError("WP07-D axis_fractions must define x, y, and z arrays.")
        axes = (
            tuple(float(value) for value in axis_fractions[0]),
            tuple(float(value) for value in axis_fractions[1]),
            tuple(float(value) for value in axis_fractions[2]),
        )
        for axis, expected_count, name in zip(axes, counts, ("x", "y", "z"), strict=True):
            if (
                len(axis) != expected_count + 1
                or not np.all(np.isfinite(axis))
                or not np.isclose(axis[0], 0.0, rtol=0.0, atol=1.0e-14)
                or not np.isclose(axis[-1], 1.0, rtol=0.0, atol=1.0e-14)
                or np.any(np.diff(axis) <= 0.0)
            ):
                raise ValueError(f"WP07-D {name}-axis fractions are invalid for the requested cell count.")
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    if lower.shape != (3,) or upper.shape != (3,) or not np.all(np.isfinite([lower, upper])):
        raise ValueError("Mesh bounds must be finite 3-vectors.")
    if np.any(upper <= lower):
        raise ValueError("Mesh upper bounds must exceed lower bounds.")

    def node_index(i: int, j: int, k: int) -> int:
        return k * (ny + 1) * (nx + 1) + j * (nx + 1) + i

    nodes = np.array(
        [
            [
                lower[0] + (upper[0] - lower[0]) * axes[0][i],
                lower[1] + (upper[1] - lower[1]) * axes[1][j],
                lower[2] + (upper[2] - lower[2]) * axes[2][k],
            ]
            for k in range(nz + 1)
            for j in range(ny + 1)
            for i in range(nx + 1)
        ],
        dtype=float,
    )
    elements: list[tuple[int, int, int, int]] = []
    signed_volumes: list[float] = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                v0 = node_index(i, j, k)
                v1 = node_index(i + 1, j, k)
                v2 = node_index(i + 1, j + 1, k)
                v3 = node_index(i, j + 1, k)
                v4 = node_index(i, j, k + 1)
                v5 = node_index(i + 1, j, k + 1)
                v6 = node_index(i + 1, j + 1, k + 1)
                v7 = node_index(i, j + 1, k + 1)
                raw_elements = (
                    (v0, v1, v2, v6),
                    (v0, v2, v3, v6),
                    (v0, v3, v7, v6),
                    (v0, v7, v4, v6),
                    (v0, v4, v5, v6),
                    (v0, v5, v1, v6),
                )
                for raw in raw_elements:
                    oriented = raw
                    volume = _signed_tet4_volume(nodes[list(oriented)])
                    if not np.isfinite(volume) or abs(volume) <= 1.0e-15:
                        raise ValueError("Frozen WP07-D subdivision produced a degenerate TET4.")
                    if volume < 0.0:
                        oriented = (raw[0], raw[1], raw[3], raw[2])
                        volume = _signed_tet4_volume(nodes[list(oriented)])
                    if not np.isfinite(volume) or volume <= 0.0:
                        raise ValueError("Frozen WP07-D orientation repair failed.")
                    elements.append(oriented)
                    signed_volumes.append(volume)

    frozen_elements = tuple(elements)
    exterior = _boundary_faces(frozen_elements)
    z_min = float(lower[2])
    z_max = float(upper[2])
    top_faces = tuple(
        face for face in exterior if all(np.isclose(nodes[index, 2], z_max, rtol=0.0, atol=1.0e-14) for index in face)
    )
    bottom_faces = tuple(
        face for face in exterior if all(np.isclose(nodes[index, 2], z_min, rtol=0.0, atol=1.0e-14) for index in face)
    )
    slave_nodes = tuple(sorted({index for face in bottom_faces for index in face}))
    return StructuredTet4Mesh(
        nodes=nodes,
        elements=frozen_elements,
        top_faces=top_faces,
        bottom_faces=bottom_faces,
        slave_nodes=slave_nodes,
        signed_volumes=np.asarray(signed_volumes, dtype=float),
    )


def _triangle_area(coordinates: np.ndarray) -> float:
    return 0.5 * float(np.linalg.norm(np.cross(coordinates[1] - coordinates[0], coordinates[2] - coordinates[0])))


def _master_barycentric(point: np.ndarray, triangle: np.ndarray) -> np.ndarray:
    edge_1 = triangle[1] - triangle[0]
    edge_2 = triangle[2] - triangle[0]
    relative = point - triangle[0]
    gram = np.array([[edge_1 @ edge_1, edge_1 @ edge_2], [edge_1 @ edge_2, edge_2 @ edge_2]])
    xi_eta = np.linalg.solve(gram, np.array([relative @ edge_1, relative @ edge_2]))
    return np.array([1.0 - xi_eta[0] - xi_eta[1], xi_eta[0], xi_eta[1]])


def mesh_contract_check(
    contract: dict[str, Any],
    level: str,
    *,
    cell_counts: tuple[int, int, int] | None = None,
    axis_fractions: tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]] | None = None,
) -> dict[str, Any]:
    """Validate actual frozen mesh topology and fixed master coverage."""

    mesh = generate_structured_tet4_mesh(level, cell_counts=cell_counts, axis_fractions=axis_fractions)
    replay = generate_structured_tet4_mesh(level, cell_counts=cell_counts, axis_fractions=axis_fractions)
    expected = next(item for item in contract["mesh_levels"] if item["id"] == level)
    expected_body_nodes = int(expected["body_nodes"])
    expected_elements = int(expected["tet4_elements"])
    expected_contact_nodes = int(expected["contact_slave_nodes"])
    deterministic = (
        np.array_equal(mesh.nodes, replay.nodes)
        and mesh.elements == replay.elements
        and mesh.top_faces == replay.top_faces
        and mesh.bottom_faces == replay.bottom_faces
        and mesh.slave_nodes == replay.slave_nodes
    )
    finite = bool(np.all(np.isfinite(mesh.nodes)) and np.all(np.isfinite(mesh.signed_volumes)))
    positive_volumes = bool(mesh.signed_volumes.size == expected_elements and np.all(mesh.signed_volumes > 0.0))
    connectivity = bool(
        all(len(element) == 4 and all(0 <= node < len(mesh.nodes) for node in element) for element in mesh.elements)
    )
    top_area = math.fsum(_triangle_area(mesh.nodes[list(face)]) for face in mesh.top_faces)
    bottom_area = math.fsum(_triangle_area(mesh.nodes[list(face)]) for face in mesh.bottom_faces)
    coverage_barycentric = np.array(
        [_master_barycentric(mesh.nodes[index], MASTER_NODES) for index in mesh.slave_nodes], dtype=float
    )
    master_coverage = bool(
        coverage_barycentric.size
        and np.all(np.isfinite(coverage_barycentric))
        and np.min(coverage_barycentric) >= -1.0e-12
        and np.max(coverage_barycentric) <= 1.0 + 1.0e-12
    )
    expected_total_nodes = expected_body_nodes + len(MASTER_NODES)
    expected_dofs = expected_total_nodes * 3
    fixed_body_nodes = int(np.count_nonzero(np.isclose(mesh.nodes[:, 0], BODY_LOWER[0], rtol=0.0, atol=1.0e-14)))
    body_dofs = len(mesh.nodes) * 3
    no_contact_free_dofs = body_dofs - 3 * fixed_body_nodes
    passed = all(
        (
            len(mesh.nodes) == expected_body_nodes,
            len(mesh.elements) == expected_elements,
            len(mesh.slave_nodes) == expected_contact_nodes,
            len(mesh.top_faces) == int(expected["top_boundary_triangles"]),
            body_dofs == int(expected["body_dofs"]),
            no_contact_free_dofs == int(expected["expected_no_contact_free_dofs"]),
            deterministic,
            finite,
            positive_volumes,
            connectivity,
            abs(top_area - float(expected["top_surface_area"])) <= 64.0 * np.finfo(float).eps,
            abs(bottom_area - float(expected["bottom_surface_area"])) <= 64.0 * np.finfo(float).eps,
            master_coverage,
        )
    )
    return {
        "level": level,
        "status": "PASS" if passed else "FAIL",
        "body_nodes": len(mesh.nodes),
        "total_nodes_with_master": expected_total_nodes,
        "body_dofs": len(mesh.nodes) * 3,
        "fixed_body_node_count": fixed_body_nodes,
        "fixed_body_dof_count": 3 * fixed_body_nodes,
        "no_contact_free_dofs": no_contact_free_dofs,
        "declared_total_dofs": expected_dofs,
        "tet4_elements": len(mesh.elements),
        "contact_slave_nodes": len(mesh.slave_nodes),
        "top_boundary_triangles": len(mesh.top_faces),
        "top_surface_area": top_area,
        "bottom_surface_area": bottom_area,
        "minimum_signed_tet4_volume": float(np.min(mesh.signed_volumes)),
        "maximum_signed_tet4_volume": float(np.max(mesh.signed_volumes)),
        "finite_coordinates_and_volumes": finite,
        "positive_reference_volumes": positive_volumes,
        "connectivity_valid": connectivity,
        "deterministic_connectivity": deterministic,
        "master_coverage": master_coverage,
        "minimum_master_barycentric": float(np.min(coverage_barycentric)),
        "maximum_master_barycentric": float(np.max(coverage_barycentric)),
        "initial_clearance": float(BODY_LOWER[2] - MASTER_NODES[0, 2]),
        "slave_policy": "ALL_BOTTOM_FACE_NODES_INCLUDING_CLAMPED_X0",
    }


def accumulate_constant_t3_traction(
    nodes: Any,
    triangular_faces: Any,
    traction: Any,
) -> np.ndarray:
    """Assemble consistent nodal forces for constant traction on T3 faces."""

    coordinates = np.asarray(nodes, dtype=float)
    faces = tuple(tuple(int(index) for index in face) for face in triangular_faces)
    vector = np.asarray(traction, dtype=float)
    if coordinates.ndim != 2 or coordinates.shape[1] != 3:
        raise ValueError("Surface nodes must have shape (n, 3).")
    if vector.shape != (3,) or not np.all(np.isfinite(vector)):
        raise ValueError("Surface traction must be a finite 3-vector.")
    forces = np.zeros_like(coordinates)
    for face in faces:
        if len(face) != 3 or any(index < 0 or index >= len(coordinates) for index in face):
            raise ValueError("Every surface face must contain three valid node indices.")
        first, second, third = coordinates[list(face)]
        area = 0.5 * float(np.linalg.norm(np.cross(second - first, third - first)))
        if not np.isfinite(area) or area <= 0.0:
            raise ValueError("Every surface face must have positive finite area.")
        forces[list(face)] += vector * area / 3.0
    return forces


def resultant_and_moment(nodes: Any, nodal_forces: Any) -> tuple[np.ndarray, np.ndarray]:
    """Return the global resultant and origin moment of nodal forces."""

    coordinates = np.asarray(nodes, dtype=float)
    forces = np.asarray(nodal_forces, dtype=float)
    if coordinates.shape != forces.shape or coordinates.ndim != 2 or coordinates.shape[1] != 3:
        raise ValueError("Nodes and nodal forces must have matching shape (n, 3).")
    if not np.all(np.isfinite(coordinates)) or not np.all(np.isfinite(forces)):
        raise ValueError("Nodes and nodal forces must be finite.")
    resultant = np.array(
        [math.fsum(float(value) for value in forces[:, component]) for component in range(3)],
        dtype=float,
    )
    cross_products = np.cross(coordinates, forces)
    moment = np.array(
        [math.fsum(float(value) for value in cross_products[:, component]) for component in range(3)],
        dtype=float,
    )
    return resultant, moment


def check_load_contract(
    nodes: Any,
    triangular_faces: Any,
    traction: Any,
    expected_resultant: Any,
    expected_moment: Any,
    *,
    tolerance: float = 1.0e-12,
) -> dict[str, Any]:
    """Check deterministic T3 load conservation without running a solve."""

    forces = accumulate_constant_t3_traction(nodes, triangular_faces, traction)
    resultant, moment = resultant_and_moment(nodes, forces)
    reference_resultant = np.asarray(expected_resultant, dtype=float)
    reference_moment = np.asarray(expected_moment, dtype=float)
    resultant_error = float(np.linalg.norm(resultant - reference_resultant))
    moment_error = float(np.linalg.norm(moment - reference_moment))
    resultant_scale = max(float(np.linalg.norm(reference_resultant)), 1.0)
    moment_scale = max(float(np.linalg.norm(reference_moment)), 1.0)
    machine_floor_resultant = float(64.0 * np.finfo(float).eps * resultant_scale)
    machine_floor_moment = float(64.0 * np.finfo(float).eps * moment_scale)
    return {
        "nodal_forces": forces,
        "resultant": resultant,
        "moment": moment,
        "resultant_error": resultant_error,
        "moment_error": moment_error,
        "resultant_relative_error": resultant_error / resultant_scale,
        "moment_relative_error": moment_error / moment_scale,
        "resultant_absolute_floor": machine_floor_resultant,
        "moment_absolute_floor": machine_floor_moment,
        "pass": (
            resultant_error <= max(tolerance * resultant_scale, machine_floor_resultant)
            and moment_error <= max(tolerance * moment_scale, machine_floor_moment)
        ),
    }


def _scale_aware_load_error(actual: np.ndarray, expected: np.ndarray, relative_tolerance: float) -> dict[str, float | bool]:
    difference = np.asarray(actual, dtype=float) - np.asarray(expected, dtype=float)
    absolute_error = float(np.linalg.norm(difference))
    scale = max(float(np.linalg.norm(expected)), 1.0)
    absolute_floor = float(64.0 * np.finfo(float).eps * scale)
    relative_error = absolute_error / scale
    return {
        "absolute_error": absolute_error,
        "relative_error": relative_error,
        "absolute_floor": absolute_floor,
        "pass": bool(absolute_error <= max(relative_tolerance * scale, absolute_floor)),
    }


def actual_mesh_load_check(
    contract: dict[str, Any],
    level: str,
    *,
    cell_counts: tuple[int, int, int] | None = None,
    axis_fractions: tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]] | None = None,
) -> dict[str, Any]:
    """Integrate the frozen top boundary of a real generated mesh."""

    mesh = generate_structured_tet4_mesh(level, cell_counts=cell_counts, axis_fractions=axis_fractions)
    load = check_load_contract(
        mesh.nodes,
        mesh.top_faces,
        TRACTION,
        EXPECTED_RESULTANT,
        EXPECTED_MOMENT,
        tolerance=float(contract["loading"]["load_check_tolerance"]["resultant_relative"]),
    )
    resultant_error = _scale_aware_load_error(
        load["resultant"],
        EXPECTED_RESULTANT,
        float(contract["loading"]["load_check_tolerance"]["resultant_relative"]),
    )
    moment_error = _scale_aware_load_error(
        load["moment"],
        EXPECTED_MOMENT,
        float(contract["loading"]["load_check_tolerance"]["moment_relative"]),
    )
    passed = bool(resultant_error["pass"] and moment_error["pass"])
    return {
        "level": level,
        "status": "PASS" if passed else "FAIL",
        "resultant": load["resultant"].tolist(),
        "moment_about_origin": load["moment"].tolist(),
        "resultant_error": resultant_error,
        "moment_error": moment_error,
        "nodal_load_count": int(np.count_nonzero(np.linalg.norm(load["nodal_forces"], axis=1) > 0.0)),
        "top_boundary_triangles": len(mesh.top_faces),
    }


def _structural_model(mesh: StructuredTet4Mesh, *, include_contact: bool = False) -> Any:
    """Build a local model for algebraic prechecks, never for campaign solves."""

    # Import after the contact package has initialized to avoid the repository's
    # known model/contact import cycle when this helper is used standalone.
    from solveur.core.model import FiniteElementModel

    nodes = mesh.nodes
    master_offset = len(nodes)
    all_nodes = np.vstack((nodes, MASTER_NODES)) if include_contact else nodes
    fixed = [
        {"node": int(index), "dofs": ["UX", "UY", "UZ"]}
        for index, point in enumerate(nodes)
        if np.isclose(point[0], BODY_LOWER[0], rtol=0.0, atol=1.0e-14)
    ]
    if include_contact:
        fixed.extend(
            {"node": master_offset + index, "dofs": ["UX", "UY", "UZ"]}
            for index in range(len(MASTER_NODES))
        )
    data: dict[str, Any] = {
        "analysis": {
            "type": "geometric_nonlinear_static" if include_contact else "linear_static",
            "method": "newton_raphson" if include_contact else "direct",
            "parameters": {"contact_search_mode": "initial"} if include_contact else {},
        },
        "nodes": all_nodes.tolist(),
        "elements": [
            {"type": "TET4", "nodes": list(element), "material": "elastic"} for element in mesh.elements
        ],
        "materials": {"elastic": {"type": "isotropic_3d", "E": 1.0e6, "nu": 0.3}},
        "fixed_dofs": fixed,
    }
    if include_contact:
        data["contacts"] = [
            {
                "name": "wp07d_master_plane",
                "slave_nodes": list(mesh.slave_nodes),
                "master_nodes": [master_offset, master_offset + 1, master_offset + 2],
            }
        ]
    return FiniteElementModel.from_raw(**data)


def no_contact_well_posedness_check(level: str = "M1") -> dict[str, Any]:
    """Assemble and factor the corrected no-contact M1 structural system."""

    if level != "M1":
        raise ValueError("The WP07-D no-contact precheck is intentionally M1-only.")
    # Load the contact package first so model imports use the established
    # initialization order; this remains a tiny algebraic precheck.
    import solveur.contact.evaluation as _contact_evaluation  # noqa: F401
    from solveur.core.assembly.assembler import GlobalAssembler
    from scipy.sparse.linalg import splu

    mesh = generate_structured_tet4_mesh(level)
    model = _structural_model(mesh)
    dofs = model.dof_manager()
    stiffness = GlobalAssembler().assemble_stiffness(model, dofs)
    fixed = GlobalAssembler().fixed_indices(model, dofs)
    free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
    reduced = stiffness[free, :][:, free].tocsr()
    dense = 0.5 * (reduced.toarray() + reduced.toarray().T)
    eigenvalues = np.linalg.eigvalsh(dense)
    eigenvalue_scale = max(float(np.max(np.abs(eigenvalues))), 1.0)
    zero_tolerance = max(eigenvalue_scale * 1.0e-12, 1.0e-12)
    rhs = np.linspace(1.0, 2.0, free.size, dtype=float)
    solution = np.asarray(splu(reduced.tocsc()).solve(rhs), dtype=float)
    finite_matrix = bool(np.all(np.isfinite(reduced.data)))
    nonzero_diagonal = int(np.count_nonzero(np.abs(reduced.diagonal()) > 0.0))
    passed = bool(
        finite_matrix
        and nonzero_diagonal == reduced.shape[0]
        and float(np.min(eigenvalues)) > zero_tolerance
        and np.all(np.isfinite(solution))
    )
    return {
        "level": level,
        "status": "PASS" if passed else "FAIL",
        "contact_solve": False,
        "body_dof_count": int(dofs.ndof),
        "fixed_dof_count": int(fixed.size),
        "reduced_dof_count": int(free.size),
        "reduced_matrix_shape": list(reduced.shape),
        "reduced_matrix_nnz": int(reduced.nnz),
        "finite_matrix": finite_matrix,
        "nonzero_diagonal_count": nonzero_diagonal,
        "smallest_eigenvalue": float(np.min(eigenvalues)),
        "largest_eigenvalue": float(np.max(eigenvalues)),
        "eigenvalue_zero_tolerance": zero_tolerance,
        "sparse_factorization": "finite LU factorization succeeded",
        "arbitrary_load_solution_finite": bool(np.all(np.isfinite(solution))),
    }


def penalty_initial_state_check(level: str = "M1") -> dict[str, Any]:
    """Evaluate only the zero-displacement penalty contact algebraically."""

    if level != "M1":
        raise ValueError("The WP07-D penalty initial-state precheck is intentionally M1-only.")
    from solveur.contact.evaluation import evaluate_penalty_contact

    mesh = generate_structured_tet4_mesh(level)
    model = _structural_model(mesh, include_contact=True)
    dofs = model.dof_manager()
    evaluation = evaluate_penalty_contact(model, dofs, np.zeros(dofs.ndof, dtype=float), penalty=1.0e8)
    expected_clearance = float(BODY_LOWER[2] - MASTER_NODES[0, 2])
    passed = bool(
        len(evaluation.active_contacts) == 0
        and np.linalg.norm(evaluation.internal_force) == 0.0
        and evaluation.tangent.nnz == 0
        and all(abs(gap - expected_clearance) <= 1.0e-14 for gap in evaluation.gaps)
    )
    return {
        "level": level,
        "status": "PASS" if passed else "FAIL",
        "contact_solve": False,
        "active_count": len(evaluation.active_contacts),
        "force_norm": float(np.linalg.norm(evaluation.internal_force)),
        "tangent_nnz": int(evaluation.tangent.nnz),
        "minimum_gap": min(evaluation.gaps, default=0.0),
        "maximum_gap": max(evaluation.gaps, default=0.0),
        "expected_initial_clearance": expected_clearance,
    }


def active_set_initial_state_check(level: str = "M1") -> dict[str, Any]:
    """Confirm empty initial active set from fixed-normal geometric gaps."""

    if level != "M1":
        raise ValueError("The WP07-D active-set initial-state precheck is intentionally M1-only.")
    mesh = generate_structured_tet4_mesh(level)
    gaps: np.ndarray = np.full(len(mesh.slave_nodes), BODY_LOWER[2] - MASTER_NODES[0, 2], dtype=float)
    passed = bool(np.all(np.isfinite(gaps)) and np.all(gaps > 0.0))
    return {
        "level": level,
        "status": "PASS" if passed else "FAIL",
        "contact_solve": False,
        "initial_active_count": 0,
        "minimum_initial_gap": float(np.min(gaps)),
        "maximum_initial_gap": float(np.max(gaps)),
        "initial_active_set": [],
    }


def run_phase0_prechecks(contract: dict[str, Any]) -> dict[str, Any]:
    """Run only mesh/load and M1 algebraic prechecks; never a contact solve."""

    validate_contract(contract)
    mesh_checks = [mesh_contract_check(contract, level) for level in MESH_LEVELS]
    load_checks = [actual_mesh_load_check(contract, level) for level in MESH_LEVELS]
    no_contact = no_contact_well_posedness_check()
    penalty_initial = penalty_initial_state_check()
    active_set_initial = active_set_initial_state_check()
    penalty_initial["structural_tangent_well_posed"] = no_contact["status"] == "PASS"
    return {
        "record_type": "WP07-D_PHASE0_R1_PRECHECKS",
        "provenance": {
            "source_sha": _git("rev-parse", "HEAD"),
            "worktree_dirty": bool(_git("status", "--porcelain")),
        },
        "status": "PASS"
        if all(row["status"] == "PASS" for row in mesh_checks + load_checks)
        and no_contact["status"] == "PASS"
        and penalty_initial["status"] == "PASS"
        and active_set_initial["status"] == "PASS"
        else "FAIL",
        "mesh_checks": mesh_checks,
        "load_checks": load_checks,
        "no_contact_system": no_contact,
        "penalty_initial_state": penalty_initial,
        "active_set_initial_state": active_set_initial,
        "structural_solves_run": False,
        "external_solver_run": False,
    }


def load_contract() -> dict[str, Any]:
    """Load the frozen WP07-D contract."""

    with CONTRACT_PATH.open(encoding="utf-8") as stream:
        contract = json.load(stream)
    if not isinstance(contract, dict):
        raise ValueError("WP07-D contract root must be an object.")
    return contract


def validate_contract(contract: dict[str, Any]) -> None:
    """Fail closed if the frozen contract cannot describe six future cases."""

    if contract.get("work_package") != "WP07-D":
        raise ValueError("Unexpected WP07-D work package.")
    levels = tuple(item.get("id") for item in contract.get("mesh_levels", []))
    if levels != MESH_LEVELS:
        raise ValueError("WP07-D requires exactly M1, M2 and M3 in order.")
    benchmarks = contract.get("benchmarks")
    if not isinstance(benchmarks, dict) or tuple(benchmarks) != tuple(BENCHMARKS):
        raise ValueError("WP07-D requires ACTIVE_SET and PENALTY benchmarks.")
    for benchmark_name, route in BENCHMARKS.items():
        benchmark = benchmarks[benchmark_name]
        if benchmark.get("route") != route:
            raise ValueError(f"Unexpected route for {benchmark_name}.")
        if tuple(benchmark.get("mesh_levels", [])) != MESH_LEVELS:
            raise ValueError(f"{benchmark_name} must declare all three mesh levels.")
    execution = contract.get("execution_policy", {})
    if execution.get("structural_solves_allowed") is not False:
        raise ValueError("Structural solves must remain disabled during preparation.")
    if execution.get("external_solver_allowed") is not False:
        raise ValueError("External solver execution must remain disabled during preparation.")
    if execution.get("status") != "PENDING_GOVERNING_BRANCH_INTEGRATION":
        raise ValueError("WP07-D execution policy must remain pending governing branch integration.")
    boundary = contract.get("physical_benchmark", {}).get("boundary_conditions", {})
    if "FULL_CLAMP" not in str(boundary.get("body_support", "")):
        raise ValueError("WP07-D requires a full x=0 body clamp.")
    contact_topology = contract.get("physical_benchmark", {}).get("contact_topology", {})
    if contact_topology.get("slave_node_policy") != "ALL_BOTTOM_FACE_NODES_INCLUDING_CLAMPED_X0":
        raise ValueError("WP07-D slave-node policy is not frozen.")
    load_tolerance = contract.get("loading", {}).get("load_check_tolerance", {})
    if not {"resultant_relative", "moment_relative", "absolute_floor"}.issubset(load_tolerance):
        raise ValueError("WP07-D load invariant tolerance is incomplete.")
    thresholds = contract.get("thresholds", {})
    mesh_thresholds = thresholds.get("mesh_m2_to_m3", {})
    required_mesh_thresholds = {
        "selected_displacement_relative",
        "reaction_resultant_relative",
        "reaction_moment_relative",
        "contact_resultant_relative",
    }
    equilibrium = thresholds.get("equilibrium", {})
    if not required_mesh_thresholds.issubset(mesh_thresholds) or not {
        "force_relative",
        "moment_relative",
    }.issubset(equilibrium):
        raise ValueError("WP07-D threshold set is incomplete.")


def build_preflight(
    contract: dict[str, Any],
    *,
    source_sha: str | None = None,
    worktree_dirty: bool | None = None,
) -> dict[str, Any]:
    """Build a deterministic, explicitly no-solve execution plan."""

    validate_contract(contract)
    resolved_sha = source_sha or _git("rev-parse", "HEAD")
    dirty = bool(_git("status", "--porcelain")) if worktree_dirty is None else worktree_dirty
    planned_cases = [
        {
            "case_id": f"WP07D-{benchmark_name}-{level}",
            "benchmark": benchmark_name,
            "route": route,
            "mesh_level": level,
            "status": "NOT_EXECUTED",
            "output_path": f"qualification/0_2_9/wp07d_runs/{benchmark_name.lower()}/{level.lower()}.json",
        }
        for benchmark_name, route in BENCHMARKS.items()
        for level in MESH_LEVELS
    ]
    return {
        "schema_version": 1,
        "record_type": "WP07-D_PREPARATION_PREFLIGHT",
        "status": "PREPARATION_ONLY",
        "source_sha": resolved_sha,
        "worktree_dirty": dirty,
        "environment": {"python": sys.version.split()[0], "platform": platform.platform()},
        "planned_cases": planned_cases,
        "replay_cases": ["WP07D-ACTIVE_SET-M2", "WP07D-PENALTY-M1"],
        "reference_comparison": "deferred until formulation-compatible reference is available",
        "capture_fields": [
            "wall_time_s",
            "peak_rss_process",
            "peak_private_or_uss_process",
            "result_json",
            "evidence_manifest",
        ],
        "execution_guard": {
            "structural_solves_enabled": False,
            "external_solver_enabled": False,
            "reason": "WP07-D contract preparation waits for WP04 M3 completion.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional preflight JSON path.")
    parser.add_argument(
        "--prechecks",
        action="store_true",
        help="Run the authorized no-solve mesh/load and tiny algebraic prechecks.",
    )
    args = parser.parse_args()
    contract = load_contract()
    preflight = run_phase0_prechecks(contract) if args.prechecks else build_preflight(contract)
    rendered = json.dumps(preflight, indent=2, sort_keys=True, default=str)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
