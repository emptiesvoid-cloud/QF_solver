"""Preparation-only harness for the WP05-C/D structural benchmark.

The module freezes the benchmark and supplies deterministic mesh, load,
observable, and evidence helpers.  It deliberately does not invoke a solver;
the future nonlinear termination policy is injected separately through
``StructuralQualificationRunner``.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from solveur.elements.solid.hex20 import Hex20Element
from solveur.elements.solid.tet10 import Tet10Element


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_JSON = ROOT / "qualification" / "0_2_9" / "wp05_cd_structural_contract.json"


@dataclass(frozen=True)
class MeshLevel:
    """Structured base-cell resolution frozen by the structural contract."""

    name: str
    nx: int
    ny: int
    nz: int


MESH_LEVELS: tuple[MeshLevel, ...] = (
    MeshLevel("H1", 4, 2, 2),
    MeshLevel("H2", 8, 4, 4),
    MeshLevel("H3", 16, 8, 8),
)


@dataclass(frozen=True)
class StructuralBenchmarkContract:
    """Immutable benchmark quantities and prospective qualification policies."""

    length: float = 4.0
    height: float = 0.5
    depth: float = 0.5
    young_modulus: float = 1.0e6
    poisson_ratio: float = 0.30
    total_load: tuple[float, float, float] = (0.0, -50.0, 0.0)
    sample_region: tuple[tuple[float, float], ...] = (
        (0.40, 0.60),
        (0.70, 0.95),
        (0.20, 0.80),
    )
    deformation_envelope: tuple[float, tuple[float, float], float] = (
        0.20,
        (0.75, 1.30),
        0.30,
    )
    mesh_thresholds: tuple[tuple[str, float], ...] = (
        ("mean_end_displacement", 0.02),
        ("reaction_resultant", 0.02),
        ("reaction_moment", 0.02),
        ("strain_energy", 0.02),
        ("representative_sigma_xx", 0.08),
    )
    equilibrium_thresholds: tuple[tuple[str, float], ...] = (
        ("force_relative_error", 1.0e-8),
        ("moment_relative_error", 1.0e-8),
    )
    replay_relative_tolerance: float = 1.0e-12
    replay_absolute_floor: float = 1.0e-14

    @property
    def volume(self) -> float:
        return self.length * self.height * self.depth

    def as_dict(self) -> dict[str, Any]:
        return {
            "geometry": {"L": self.length, "H": self.height, "D": self.depth},
            "material": {"E": self.young_modulus, "nu": self.poisson_ratio},
            "load": {
                "total_nodal_dead_load": list(self.total_load),
                "distribution": "CONSISTENT_EQUIVALENT_NODAL_TRACTION from uniform x=L traction",
                "surface_quadrature": {
                    "TET10": "quadratic T6 three-point degree-2 triangle rule",
                    "HEX20": "quadratic Q8 tensor 2x2 Gauss rule",
                },
                "expected_external_moment_about_global_origin": [12.5, 0.0, -200.0],
                "resultant_absolute_tolerance": 1.0e-12,
                "moment_scale_aware_relative_tolerance": 1.0e-12,
            },
            "boundary": "all displacement DOFs fixed on x=0 face",
            "sampling_region_normalized": {
                "x_over_L": list(self.sample_region[0]),
                "y_over_H": list(self.sample_region[1]),
                "z_over_D": list(self.sample_region[2]),
            },
            "deformation_envelope": {
                "minimum_det_F": self.deformation_envelope[0],
                "principal_stretches": list(self.deformation_envelope[1]),
                "maximum_green_lagrange_frobenius_norm": self.deformation_envelope[2],
            },
            "mesh_thresholds_h2_to_h3": dict(self.mesh_thresholds),
            "equilibrium_thresholds": dict(self.equilibrium_thresholds),
            "replay": {
                "relative_tolerance": self.replay_relative_tolerance,
                "absolute_floor": self.replay_absolute_floor,
                "binary_state_hash_required": False,
                "discrete_newton_iteration_count_exact": True,
                "accepted_load_factor_history_elementwise": True,
            },
        }


@dataclass(frozen=True)
class TerminationPolicy:
    """A replaceable nonlinear policy kept separate from benchmark physics."""

    name: str
    source: str
    agent_a_policy: bool = False


DEFAULT_TERMINATION_POLICY = TerminationPolicy(
    name="CURRENT_CANONICAL_GEOMETRIC_STATIC",
    source="Agent B baseline; supplied at future qualification execution",
)


@dataclass(frozen=True)
class MeshData:
    family: str
    level: MeshLevel
    coordinates: np.ndarray
    connectivity: tuple[tuple[int, ...], ...]
    end_face_nodes: tuple[int, ...]
    reference_volume: float

    @property
    def nodes(self) -> int:
        return int(self.coordinates.shape[0])

    @property
    def elements(self) -> int:
        return len(self.connectivity)

    @property
    def dofs(self) -> int:
        return 3 * self.nodes


@dataclass(frozen=True)
class SurfaceFace:
    """One ordered quadratic boundary face and its corner-node key."""

    node_ids: tuple[int, ...]
    corner_ids: tuple[int, ...]


TET10_FACE_LOCAL: tuple[tuple[int, ...], ...] = (
    (0, 1, 2, 4, 5, 6),
    (0, 1, 3, 4, 8, 7),
    (0, 2, 3, 6, 9, 7),
    (1, 2, 3, 5, 9, 8),
)

HEX20_FACE_LOCAL: tuple[tuple[int, ...], ...] = (
    (0, 1, 2, 3, 8, 11, 13, 9),
    (4, 5, 6, 7, 16, 18, 19, 17),
    (0, 1, 5, 4, 8, 12, 16, 10),
    (1, 2, 6, 5, 11, 14, 18, 12),
    (2, 3, 7, 6, 13, 15, 19, 14),
    (3, 0, 4, 7, 9, 10, 17, 15),
)

TRIANGLE_FACE_QUADRATURE: tuple[tuple[tuple[float, float, float], float], ...] = (
    ((2.0 / 3.0, 1.0 / 6.0, 1.0 / 6.0), 1.0 / 6.0),
    ((1.0 / 6.0, 2.0 / 3.0, 1.0 / 6.0), 1.0 / 6.0),
    ((1.0 / 6.0, 1.0 / 6.0, 2.0 / 3.0), 1.0 / 6.0),
)

GAUSS_ABSCISSA = 1.0 / np.sqrt(3.0)
QUAD_FACE_QUADRATURE: tuple[tuple[float, float, float], ...] = tuple(
    (xi, eta, 1.0)
    for xi in (-GAUSS_ABSCISSA, GAUSS_ABSCISSA)
    for eta in (-GAUSS_ABSCISSA, GAUSS_ABSCISSA)
)


def _node_id(i: int, j: int, k: int, level: MeshLevel) -> int:
    return i + (level.nx + 1) * (j + (level.ny + 1) * k)


def _grid_coordinates(level: MeshLevel, contract: StructuralBenchmarkContract) -> list[tuple[float, float, float]]:
    coordinates: list[tuple[float, float, float]] = []
    for k in range(level.nz + 1):
        z = contract.depth * k / level.nz
        for j in range(level.ny + 1):
            y = contract.height * j / level.ny
            for i in range(level.nx + 1):
                x = contract.length * i / level.nx
                coordinates.append((x, y, z))
    return coordinates


def _cell_corners(i: int, j: int, k: int, level: MeshLevel) -> tuple[int, ...]:
    return (
        _node_id(i, j, k, level),
        _node_id(i + 1, j, k, level),
        _node_id(i + 1, j + 1, k, level),
        _node_id(i, j + 1, k, level),
        _node_id(i, j, k + 1, level),
        _node_id(i + 1, j, k + 1, level),
        _node_id(i + 1, j + 1, k + 1, level),
        _node_id(i, j + 1, k + 1, level),
    )


HEX20_EDGES: tuple[tuple[int, int], ...] = (
    (0, 1),
    (0, 3),
    (0, 4),
    (1, 2),
    (1, 5),
    (2, 3),
    (2, 6),
    (3, 7),
    (4, 5),
    (4, 7),
    (5, 6),
    (6, 7),
)

TET10_EDGES: tuple[tuple[int, int], ...] = (
    (0, 1),
    (1, 2),
    (2, 0),
    (0, 3),
    (1, 3),
    (2, 3),
)

TET_SUBDIVISION: tuple[tuple[int, int, int, int], ...] = (
    (0, 1, 2, 6),
    (0, 2, 3, 6),
    (0, 3, 7, 6),
    (0, 7, 4, 6),
    (0, 4, 5, 6),
    (0, 5, 1, 6),
)


def _append_edge_midpoint(
    edge_nodes: dict[tuple[int, int], int],
    coordinates: list[tuple[float, float, float]],
    first: int,
    second: int,
) -> int:
    key = (min(first, second), max(first, second))
    if key not in edge_nodes:
        first_point = coordinates[first]
        second_point = coordinates[second]
        point: tuple[float, float, float] = (
            (first_point[0] + second_point[0]) / 2.0,
            (first_point[1] + second_point[1]) / 2.0,
            (first_point[2] + second_point[2]) / 2.0,
        )
        edge_nodes[key] = len(coordinates)
        coordinates.append(point)
    return edge_nodes[key]


def _face_nodes(coordinates: Sequence[Sequence[float]], contract: StructuralBenchmarkContract) -> tuple[int, ...]:
    return tuple(
        index
        for index, point in enumerate(coordinates)
        if np.isclose(point[0], contract.length, rtol=0.0, atol=1.0e-13)
    )


def _reference_volume(mesh: MeshData) -> float:
    if mesh.family == "TET10":
        return float(
            sum(
                Tet10Element.corner_signed_volume(mesh.coordinates[np.asarray(element[:4])])
                for element in mesh.connectivity
            )
        )
    if mesh.family == "HEX20":
        return float(
            sum(
                Hex20Element.jacobian_determinant(mesh.coordinates[np.asarray(element)], (0.0, 0.0, 0.0))
                * sum(Hex20Element.integration_weights)
                for element in mesh.connectivity
            )
        )
    raise ValueError(f"Unsupported family {mesh.family!r}.")


def _build_hex20(level: MeshLevel, contract: StructuralBenchmarkContract) -> MeshData:
    coordinates = _grid_coordinates(level, contract)
    edge_nodes: dict[tuple[int, int], int] = {}
    connectivity: list[tuple[int, ...]] = []
    for k in range(level.nz):
        for j in range(level.ny):
            for i in range(level.nx):
                corners = _cell_corners(i, j, k, level)
                mids = tuple(
                    _append_edge_midpoint(edge_nodes, coordinates, corners[first], corners[second])
                    for first, second in HEX20_EDGES
                )
                connectivity.append(corners + mids)
    mesh = MeshData(
        "HEX20",
        level,
        np.asarray(coordinates, dtype=float),
        tuple(connectivity),
        _face_nodes(coordinates, contract),
        0.0,
    )
    return MeshData(mesh.family, mesh.level, mesh.coordinates, mesh.connectivity, mesh.end_face_nodes, _reference_volume(mesh))


def _tet10_connectivity(
    corners: tuple[int, int, int, int],
    edge_nodes: dict[tuple[int, int], int],
    coordinates: list[tuple[float, float, float]],
) -> tuple[int, ...]:
    signed = Tet10Element.corner_signed_volume(np.asarray([coordinates[index] for index in corners], dtype=float))
    if signed <= 0.0:
        corners = (corners[0], corners[1], corners[3], corners[2])
        signed = Tet10Element.corner_signed_volume(np.asarray([coordinates[index] for index in corners], dtype=float))
    if not np.isfinite(signed) or signed <= 0.0:
        raise ValueError(f"TET10 orientation repair failed: signed volume={signed!r}.")
    mids = tuple(
        _append_edge_midpoint(edge_nodes, coordinates, corners[first], corners[second])
        for first, second in TET10_EDGES
    )
    return corners + mids


def _build_tet10(level: MeshLevel, contract: StructuralBenchmarkContract) -> MeshData:
    coordinates = _grid_coordinates(level, contract)
    edge_nodes: dict[tuple[int, int], int] = {}
    connectivity: list[tuple[int, ...]] = []
    for k in range(level.nz):
        for j in range(level.ny):
            for i in range(level.nx):
                cell = _cell_corners(i, j, k, level)
                for pattern in TET_SUBDIVISION:
                    tet_corners = (
                        cell[pattern[0]],
                        cell[pattern[1]],
                        cell[pattern[2]],
                        cell[pattern[3]],
                    )
                    connectivity.append(_tet10_connectivity(tet_corners, edge_nodes, coordinates))
    mesh = MeshData(
        "TET10",
        level,
        np.asarray(coordinates, dtype=float),
        tuple(connectivity),
        _face_nodes(coordinates, contract),
        0.0,
    )
    return MeshData(mesh.family, mesh.level, mesh.coordinates, mesh.connectivity, mesh.end_face_nodes, _reference_volume(mesh))


def build_mesh(
    family: str,
    level: MeshLevel | str,
    contract: StructuralBenchmarkContract | None = None,
) -> MeshData:
    """Build one deterministic straight-sided mesh without invoking a solver."""
    contract = contract or StructuralBenchmarkContract()
    selected = next((item for item in MESH_LEVELS if item.name == level), level) if isinstance(level, str) else level
    if not isinstance(selected, MeshLevel) or selected not in MESH_LEVELS:
        raise ValueError(f"Unsupported mesh level {level!r}.")
    normalized = family.upper()
    if normalized == "HEX20":
        return _build_hex20(selected, contract)
    if normalized == "TET10":
        return _build_tet10(selected, contract)
    raise ValueError(f"WP05-C/D harness supports TET10 and HEX20 only, not {family!r}.")


def boundary_surface_faces(mesh: MeshData) -> tuple[SurfaceFace, ...]:
    """Return unique quadratic boundary faces in deterministic order."""
    local_faces = TET10_FACE_LOCAL if mesh.family == "TET10" else HEX20_FACE_LOCAL
    candidates = []
    for element in mesh.connectivity:
        for local_face in local_faces:
            node_ids = tuple(element[index] for index in local_face)
            corner_count = 3 if mesh.family == "TET10" else 4
            candidates.append(SurfaceFace(node_ids, node_ids[:corner_count]))
    counts: dict[tuple[int, ...], int] = {}
    for face in candidates:
        key = tuple(sorted(face.corner_ids))
        counts[key] = counts.get(key, 0) + 1
    boundary = [face for face in candidates if counts[tuple(sorted(face.corner_ids))] == 1]
    return tuple(sorted(boundary, key=lambda face: tuple(sorted(face.corner_ids))))


def _end_surface_faces(mesh: MeshData, contract: StructuralBenchmarkContract) -> tuple[SurfaceFace, ...]:
    return tuple(
        face
        for face in boundary_surface_faces(mesh)
        if all(
            np.isclose(mesh.coordinates[index][0], contract.length, rtol=0.0, atol=1.0e-13)
            for index in face.corner_ids
        )
    )


def _t6_shape_functions(
    barycentric: tuple[float, float, float],
) -> tuple[np.ndarray, np.ndarray]:
    """Return T6 values and derivatives with respect to (l2, l3)."""
    l1, l2, l3 = barycentric
    values: np.ndarray = np.asarray(
        [
            l1 * (2.0 * l1 - 1.0),
            l2 * (2.0 * l2 - 1.0),
            l3 * (2.0 * l3 - 1.0),
            4.0 * l1 * l2,
            4.0 * l2 * l3,
            4.0 * l3 * l1,
        ],
        dtype=float,
    )
    derivatives: np.ndarray = np.asarray(
        [
            (-(4.0 * l1 - 1.0), -(4.0 * l1 - 1.0)),
            (4.0 * l2 - 1.0, 0.0),
            (0.0, 4.0 * l3 - 1.0),
            (4.0 * (l1 - l2), -4.0 * l2),
            (4.0 * l3, 4.0 * l2),
            (-4.0 * l3, 4.0 * (l1 - l3)),
        ],
        dtype=float,
    )
    return values, derivatives


def _q8_shape_functions(
    xi: float,
    eta: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return Q8 serendipity values and derivatives on [-1,1]^2."""
    corners = ((-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0))
    values = []
    derivatives = []
    for corner_xi, corner_eta in corners:
        term = corner_xi * xi + corner_eta * eta - 1.0
        values.append(0.25 * (1.0 + corner_xi * xi) * (1.0 + corner_eta * eta) * term)
        derivatives.append(
            (
                0.25 * corner_xi * (1.0 + corner_eta * eta) * (term + 1.0 + corner_xi * xi),
                0.25 * corner_eta * (1.0 + corner_xi * xi) * (term + 1.0 + corner_eta * eta),
            )
        )
    values.extend(
        (
            0.5 * (1.0 - xi * xi) * (1.0 - eta),
            0.5 * (1.0 + xi) * (1.0 - eta * eta),
            0.5 * (1.0 - xi * xi) * (1.0 + eta),
            0.5 * (1.0 - xi) * (1.0 - eta * eta),
        )
    )
    derivatives.extend(
        (
            (-xi * (1.0 - eta), -0.5 * (1.0 - xi * xi)),
            (0.5 * (1.0 - eta * eta), -(1.0 + xi) * eta),
            (-xi * (1.0 + eta), 0.5 * (1.0 - xi * xi)),
            (-0.5 * (1.0 - eta * eta), -(1.0 - xi) * eta),
        )
    )
    return np.asarray(values, dtype=float), np.asarray(derivatives, dtype=float)


def _quality_base(mesh: MeshData) -> dict[str, Any]:
    coordinates = mesh.coordinates
    valid_indices = all(0 <= index < mesh.nodes for element in mesh.connectivity for index in element)
    unique_local = all(len(set(element)) == len(element) for element in mesh.connectivity)
    return {
        "finite_coordinates": bool(np.isfinite(coordinates).all()),
        "connectivity_in_range": valid_indices,
        "unique_local_connectivity": unique_local,
        "end_face_nodes_sorted": mesh.end_face_nodes == tuple(sorted(mesh.end_face_nodes)),
        "end_face_node_count": len(mesh.end_face_nodes),
    }


def validate_tet10_mesh(mesh: MeshData) -> dict[str, Any]:
    """Validate ordering, orientation, Hammer-4 Jacobians, and edge sharing."""
    if mesh.family != "TET10":
        raise ValueError("TET10 quality validation received another family.")
    result = _quality_base(mesh)
    signed_volumes = []
    hammer_determinants = []
    edge_midpoint_errors = []
    for element in mesh.connectivity:
        corners = np.asarray([mesh.coordinates[index] for index in element[:4]], dtype=float)
        signed_volumes.append(Tet10Element.corner_signed_volume(corners))
        element_coordinates = mesh.coordinates[np.asarray(element)]
        hammer_determinants.extend(Tet10Element.jacobian_determinants(element_coordinates, Tet10Element.integration_points))
        for first, second, middle in Tet10Element.edge_nodes:
            expected = 0.5 * (element_coordinates[first] + element_coordinates[second])
            edge_midpoint_errors.append(float(np.linalg.norm(element_coordinates[middle] - expected)))
    signed = np.asarray(signed_volumes, dtype=float)
    determinants = np.asarray(hammer_determinants, dtype=float)
    result.update(
        {
            "element_count": mesh.elements,
            "expected_nodes_per_element": 10,
            "positive_reference_orientation": bool(np.all(signed > 0.0)),
            "minimum_signed_volume": float(np.min(signed)),
            "finite_positive_hammer4_jacobians": bool(np.isfinite(determinants).all() and np.all(determinants > 0.0)),
            "minimum_hammer4_jacobian": float(np.min(determinants)),
            "unique_midside_nodes": len({index for element in mesh.connectivity for index in element[4:]})
            == mesh.nodes - len({index for element in mesh.connectivity for index in element[:4]}),
            "maximum_midpoint_error": float(max(edge_midpoint_errors, default=0.0)),
            "straight_sided": float(max(edge_midpoint_errors, default=0.0)) <= Tet10Element.straight_sided_tolerance,
            "subdivision": "Freudenthal six-tet pattern; swap local corners 2/3 only when signed volume is non-positive",
            "quadrature": "Hammer-4",
        }
    )
    return result


def validate_hex20_mesh(mesh: MeshData) -> dict[str, Any]:
    """Validate conformity and positive Jacobians at all 27 Gauss points."""
    if mesh.family != "HEX20":
        raise ValueError("HEX20 quality validation received another family.")
    result = _quality_base(mesh)
    determinants: list[float] = []
    edge_midpoint_errors = []
    for element in mesh.connectivity:
        element_coordinates = mesh.coordinates[np.asarray(element)]
        determinants.extend(
            Hex20Element.jacobian_determinant(element_coordinates, point)
            for point in Hex20Element.integration_points
        )
        for first, second in HEX20_EDGES:
            middle = 8 + HEX20_EDGES.index((first, second))
            expected = 0.5 * (element_coordinates[first] + element_coordinates[second])
            edge_midpoint_errors.append(float(np.linalg.norm(element_coordinates[middle] - expected)))
    values: np.ndarray = np.asarray(determinants, dtype=float)
    result.update(
        {
            "element_count": mesh.elements,
            "expected_nodes_per_element": 20,
            "positive_jacobians_all_27_gauss_points": bool(np.isfinite(values).all() and np.all(values > 0.0)),
            "minimum_27_point_jacobian": float(np.min(values)),
            "gauss_points_per_element": len(Hex20Element.integration_points),
            "unique_midside_nodes": len({index for element in mesh.connectivity for index in element[8:]})
            == mesh.nodes - len({index for element in mesh.connectivity for index in element[:8]}),
            "conforming_midpoint_error": float(max(edge_midpoint_errors, default=0.0)),
            "full_integration": True,
            "reduced_integration_or_hourglass_claim": False,
        }
    )
    return result


def mesh_quality(mesh: MeshData) -> dict[str, Any]:
    """Dispatch family-specific quality checks."""
    if mesh.family == "TET10":
        return validate_tet10_mesh(mesh)
    if mesh.family == "HEX20":
        return validate_hex20_mesh(mesh)
    raise ValueError(f"Unsupported family {mesh.family!r}.")


def _integrated_face_shape_weights(mesh: MeshData, face: SurfaceFace) -> tuple[float, np.ndarray]:
    """Integrate quadratic face shape functions against physical surface measure."""
    face_coordinates = mesh.coordinates[np.asarray(face.node_ids)]
    nodal_integrals: np.ndarray = np.zeros(len(face.node_ids), dtype=float)
    area = 0.0
    if mesh.family == "TET10":
        quadrature = ((point, weight) for point, weight in TRIANGLE_FACE_QUADRATURE)
        for point, weight in quadrature:
            shape, derivatives = _t6_shape_functions(point)
            tangents = derivatives.T @ face_coordinates
            surface_jacobian = float(np.linalg.norm(np.cross(tangents[0], tangents[1])))
            area += weight * surface_jacobian
            nodal_integrals += weight * surface_jacobian * shape
    elif mesh.family == "HEX20":
        for xi, eta, weight in QUAD_FACE_QUADRATURE:
            shape, derivatives = _q8_shape_functions(xi, eta)
            tangents = derivatives.T @ face_coordinates
            surface_jacobian = float(np.linalg.norm(np.cross(tangents[0], tangents[1])))
            area += weight * surface_jacobian
            nodal_integrals += weight * surface_jacobian * shape
    else:
        raise ValueError(f"Unsupported family {mesh.family!r} for quadratic face integration.")
    if not np.isfinite(area) or area <= 0.0 or not np.isfinite(nodal_integrals).all():
        raise ValueError("Quadratic boundary-face integration produced an invalid surface measure.")
    return area, nodal_integrals


def _end_surface_integration(
    mesh: MeshData,
    contract: StructuralBenchmarkContract,
) -> tuple[float, dict[SurfaceFace, tuple[float, np.ndarray]]]:
    faces = _end_surface_faces(mesh, contract)
    if not faces:
        raise ValueError("Cannot distribute load: x=L has no boundary faces.")
    integrated: dict[SurfaceFace, tuple[float, np.ndarray]] = {
        face: _integrated_face_shape_weights(mesh, face) for face in faces
    }
    return sum(value[0] for value in integrated.values()), integrated


def nodal_load_vector(mesh: MeshData, contract: StructuralBenchmarkContract | None = None) -> np.ndarray:
    """Assemble consistent equivalent nodal forces for uniform x=L traction."""
    contract = contract or StructuralBenchmarkContract()
    area, face_integrals = _end_surface_integration(mesh, contract)
    traction = np.asarray(contract.total_load, dtype=float) / area
    loads: np.ndarray = np.zeros((mesh.nodes, 3), dtype=float)
    for face, (_, nodal_integrals) in face_integrals.items():
        loads[np.asarray(face.node_ids)] += nodal_integrals[:, None] * traction[None, :]
    if not np.isfinite(loads).all():
        raise ValueError("Consistent equivalent nodal traction produced non-finite loads.")
    return loads


def load_resultant(loads: np.ndarray) -> np.ndarray:
    """Return the global resultant of nodal 3-D loads."""
    values = np.asarray(loads, dtype=float)
    if values.ndim != 2 or values.shape[1] != 3:
        raise ValueError("Nodal loads must have shape (nodes, 3).")
    if not np.isfinite(values).all():
        raise ValueError("Nodal loads must be finite.")
    return np.sum(values, axis=0)


def load_moment(coordinates: np.ndarray, loads: np.ndarray) -> np.ndarray:
    """Return the three-component external moment about the global origin."""
    points = np.asarray(coordinates, dtype=float)
    values = np.asarray(loads, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or values.shape != points.shape:
        raise ValueError("Coordinates and loads must both have shape (nodes, 3).")
    if not np.isfinite(points).all() or not np.isfinite(values).all():
        raise ValueError("Coordinates and loads must be finite.")
    return np.sum(np.cross(points, values), axis=0)


def analytical_end_face_moment(contract: StructuralBenchmarkContract | None = None) -> np.ndarray:
    """Return the uniform-traction resultant moment at the end-face centroid."""
    contract = contract or StructuralBenchmarkContract()
    centroid: np.ndarray = np.asarray((contract.length, contract.height / 2.0, contract.depth / 2.0), dtype=float)
    return np.cross(centroid, np.asarray(contract.total_load, dtype=float))


def _scale_aware_error(error: float, reference: np.ndarray, absolute_tolerance: float) -> dict[str, float | bool]:
    scale = max(float(np.linalg.norm(reference)), 1.0)
    relative_tolerance = 1.0e-12
    allowed = max(absolute_tolerance, relative_tolerance * scale)
    return {
        "absolute_error": error,
        "relative_tolerance": relative_tolerance,
        "allowed_error": allowed,
        "pass": bool(error <= allowed),
    }


def check_volume_conservation(mesh: MeshData, contract: StructuralBenchmarkContract | None = None) -> dict[str, Any]:
    """Compare integrated reference volume with the frozen physical volume."""
    contract = contract or StructuralBenchmarkContract()
    actual = float(mesh.reference_volume)
    error = abs(actual - contract.volume)
    tolerance = 1.0e-12
    return {
        "status": "PASS" if np.isfinite(actual) and error <= tolerance else "FAIL",
        "integrated_reference_volume": actual,
        "target_volume": contract.volume,
        "absolute_error": error,
        "absolute_tolerance": tolerance,
        "integration": "TET10 signed corner volumes; HEX20 constant straight-sided Jacobian times full-rule weight sum",
    }


def check_load_conservation(mesh: MeshData, contract: StructuralBenchmarkContract | None = None) -> dict[str, Any]:
    """Check resultant and all three external-moment components."""
    contract = contract or StructuralBenchmarkContract()
    area, _ = _end_surface_integration(mesh, contract)
    traction = np.asarray(contract.total_load, dtype=float) / area
    loads = nodal_load_vector(mesh, contract)
    resultant = load_resultant(loads)
    target: np.ndarray = np.asarray(contract.total_load, dtype=float)
    resultant_error = float(np.linalg.norm(resultant - target))
    moment = load_moment(mesh.coordinates, loads)
    target_moment = analytical_end_face_moment(contract)
    moment_error = float(np.linalg.norm(moment - target_moment))
    tolerance = 1.0e-12
    moment_policy = _scale_aware_error(moment_error, target_moment, tolerance)
    return {
        "status": "PASS" if resultant_error <= tolerance and moment_policy["pass"] else "FAIL",
        "resultant_status": "PASS" if resultant_error <= tolerance else "FAIL",
        "moment_status": "PASS" if moment_policy["pass"] else "FAIL",
        "traction": traction.tolist(),
        "surface_area": area,
        "resultant": resultant.tolist(),
        "target": target.tolist(),
        "resultant_absolute_error": resultant_error,
        "absolute_tolerance": tolerance,
        "moment": moment.tolist(),
        "target_moment": target_moment.tolist(),
        "moment_absolute_error": moment_error,
        "moment_allowed_error": moment_policy["allowed_error"],
        "moment_relative_tolerance": moment_policy["relative_tolerance"],
        "loaded_node_count": len(mesh.end_face_nodes),
        "load_rule": "CONSISTENT_EQUIVALENT_NODAL_TRACTION",
        "surface_quadrature": "T6 degree-2 three-point" if mesh.family == "TET10" else "Q8 tensor 2x2 Gauss",
        "mesh_independent_physical_traction": True,
    }


def compare_physical_loads(
    first_mesh: MeshData,
    second_mesh: MeshData,
    contract: StructuralBenchmarkContract | None = None,
) -> dict[str, Any]:
    """Compare physical resultant/moment invariants across two topologies."""
    contract = contract or StructuralBenchmarkContract()
    first_loads = nodal_load_vector(first_mesh, contract)
    second_loads = nodal_load_vector(second_mesh, contract)
    first_resultant = load_resultant(first_loads)
    second_resultant = load_resultant(second_loads)
    first_moment = load_moment(first_mesh.coordinates, first_loads)
    second_moment = load_moment(second_mesh.coordinates, second_loads)
    resultant_error = float(np.linalg.norm(first_resultant - second_resultant))
    moment_error = float(np.linalg.norm(first_moment - second_moment))
    return {
        "status": "PASS" if resultant_error <= 1.0e-12 and moment_error <= 1.0e-10 else "FAIL",
        "same_physical_uniform_traction": True,
        "resultant_difference": resultant_error,
        "moment_difference": moment_error,
        "resultant_tolerance": 1.0e-12,
        "moment_tolerance": 1.0e-10,
        "first_resultant": first_resultant.tolist(),
        "second_resultant": second_resultant.tolist(),
        "first_moment": first_moment.tolist(),
        "second_moment": second_moment.tolist(),
    }


def sample_region_weighted_sigma_xx(
    records: Iterable[Mapping[str, Any]],
    contract: StructuralBenchmarkContract | None = None,
) -> float:
    """Compute weighted sigma_xx in the frozen physical sampling region."""
    contract = contract or StructuralBenchmarkContract()
    values: list[float] = []
    weights: list[float] = []
    for record in records:
        if "reference_coordinates" not in record or "reference_volume_weight" not in record:
            raise ValueError("Stress records require reference_coordinates and reference_volume_weight.")
        if "cauchy_stress" not in record:
            raise ValueError("Stress records require cauchy_stress.")
        point = np.asarray(record["reference_coordinates"], dtype=float)
        stress = np.asarray(record["cauchy_stress"], dtype=float)
        weight = float(record["reference_volume_weight"])
        if point.shape != (3,) or not np.isfinite(point).all():
            raise ValueError("reference_coordinates must be a finite vector with shape (3,).")
        if stress.shape != (3, 3) or not np.isfinite(stress).all():
            raise ValueError("cauchy_stress must be a finite 3x3 tensor.")
        if not np.isfinite(weight) or weight <= 0.0:
            raise ValueError("reference_volume_weight must be finite and positive.")
        normalized = (point[0] / contract.length, point[1] / contract.height, point[2] / contract.depth)
        inside = all(low <= coordinate <= high for coordinate, (low, high) in zip(normalized, contract.sample_region))
        if inside:
            values.append(float(stress[0, 0]))
            weights.append(weight)
    if not weights:
        raise ValueError("No integration-point record lies in the declared sampling region.")
    return float(np.average(np.asarray(values), weights=np.asarray(weights)))


def _finite_vector(name: str, value: Any, size: int) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.shape != (size,) or not np.isfinite(array).all():
        raise ValueError(f"{name} must be a finite vector with shape ({size},).")
    return array


def _deformation_metrics(records: Iterable[Mapping[str, Any]]) -> tuple[float, float, float, float]:
    det_values: list[float] = []
    stretch_values: list[float] = []
    strain_norms: list[float] = []
    for record in records:
        if "deformation_gradient" not in record or "green_lagrange_strain" not in record:
            raise ValueError("Integration-point records require deformation_gradient and green_lagrange_strain.")
        deformation = np.asarray(record["deformation_gradient"], dtype=float)
        green = np.asarray(record["green_lagrange_strain"], dtype=float)
        if deformation.shape != (3, 3) or green.shape != (3, 3) or not np.isfinite(deformation).all() or not np.isfinite(green).all():
            raise ValueError("Integration-point deformation records must be finite 3x3 tensors.")
        det_values.append(float(np.linalg.det(deformation)))
        stretch_values.extend(float(value) for value in np.linalg.svd(deformation, compute_uv=False))
        strain_norms.append(float(np.linalg.norm(green, ord="fro")))
    if not det_values:
        raise ValueError("At least one integration-point deformation record is required.")
    return min(det_values), min(stretch_values), max(stretch_values), max(strain_norms)


def extract_structural_observables(
    mesh: MeshData,
    displacement: np.ndarray,
    reactions: np.ndarray,
    strain_energy: float,
    integration_records: Sequence[Mapping[str, Any]],
    solver_diagnostics: Mapping[str, Any],
    contract: StructuralBenchmarkContract | None = None,
) -> dict[str, Any]:
    """Extract all frozen observables and reject incomplete/non-finite data."""
    contract = contract or StructuralBenchmarkContract()
    values = np.asarray(displacement, dtype=float)
    reaction_values = np.asarray(reactions, dtype=float)
    if values.shape != (mesh.nodes, 3) or not np.isfinite(values).all():
        raise ValueError("Displacement field must have shape (nodes, 3) and be finite.")
    if reaction_values.shape != (mesh.nodes, 3) or not np.isfinite(reaction_values).all():
        raise ValueError("Reaction field must have shape (nodes, 3) and be finite.")
    if not np.isfinite(strain_energy):
        raise ValueError("Strain energy must be finite.")
    clamp_nodes = np.asarray(
        [index for index, point in enumerate(mesh.coordinates) if np.isclose(point[0], 0.0, atol=1.0e-13, rtol=0.0)]
    )
    if not len(clamp_nodes):
        raise ValueError("The benchmark clamp face has no nodes.")
    reaction_resultant = np.sum(reaction_values[clamp_nodes], axis=0)
    reaction_moment = np.sum(np.cross(mesh.coordinates[clamp_nodes], reaction_values[clamp_nodes]), axis=0)
    increments = solver_diagnostics.get("increments")
    if not isinstance(increments, Sequence) or isinstance(increments, (str, bytes)) or not increments:
        raise ValueError("Solver diagnostics must provide a non-empty increments sequence.")
    load_history: list[float] = []
    newton_iterations = 0
    for increment in increments:
        if not isinstance(increment, Mapping):
            raise ValueError("Each solver increment diagnostic must be a mapping.")
        load_factor = float(increment["load_factor"])
        iterations = int(increment["iterations"])
        if not np.isfinite(load_factor) or iterations < 0:
            raise ValueError("Solver increment diagnostics must be finite and non-negative.")
        load_history.append(load_factor)
        newton_iterations += iterations
    minimum_det_f, minimum_stretch, maximum_stretch, maximum_gl_norm = _deformation_metrics(integration_records)
    return {
        "mean_end_displacement_y": float(np.mean(values[np.asarray(mesh.end_face_nodes), 1])),
        "clamp_reaction_resultant": reaction_resultant.tolist(),
        "clamp_reaction_moment": reaction_moment.tolist(),
        "clamp_reaction_moment_z": float(reaction_moment[2]),
        "strain_energy": float(strain_energy),
        "representative_sigma_xx": sample_region_weighted_sigma_xx(integration_records, contract),
        "minimum_det_F": minimum_det_f,
        "principal_stretch_min": minimum_stretch,
        "principal_stretch_max": maximum_stretch,
        "maximum_green_lagrange_strain_norm": maximum_gl_norm,
        "accepted_load_factor_history": load_history,
        "newton_iteration_count": newton_iterations,
    }


def evaluate_equilibrium(
    clamp_coordinates: np.ndarray,
    clamp_reactions: np.ndarray,
    external_coordinates: np.ndarray,
    external_loads: np.ndarray,
    force_tolerance: float = 1.0e-8,
    moment_tolerance: float = 1.0e-8,
) -> dict[str, Any]:
    """Evaluate three-component force and origin-moment equilibrium."""
    reaction_force = load_resultant(np.asarray(clamp_reactions, dtype=float))
    external_force = load_resultant(np.asarray(external_loads, dtype=float))
    reaction_moment = load_moment(np.asarray(clamp_coordinates, dtype=float), np.asarray(clamp_reactions, dtype=float))
    external_moment = load_moment(np.asarray(external_coordinates, dtype=float), np.asarray(external_loads, dtype=float))
    force_residual = reaction_force + external_force
    moment_residual = reaction_moment + external_moment
    force_error = float(np.linalg.norm(force_residual))
    moment_error = float(np.linalg.norm(moment_residual))
    force_scale = max(float(np.linalg.norm(reaction_force)), float(np.linalg.norm(external_force)), 1.0)
    moment_scale = max(float(np.linalg.norm(reaction_moment)), float(np.linalg.norm(external_moment)), 1.0)
    force_relative_error = force_error / force_scale
    moment_relative_error = moment_error / moment_scale
    return {
        "status": "PASS" if force_relative_error <= force_tolerance and moment_relative_error <= moment_tolerance else "FAIL",
        "force": {
            "reaction": reaction_force.tolist(),
            "external": external_force.tolist(),
            "residual": force_residual.tolist(),
            "relative_error": force_relative_error,
            "tolerance": force_tolerance,
            "status": "PASS" if force_relative_error <= force_tolerance else "FAIL",
        },
        "moment_about_global_origin": {
            "reaction": reaction_moment.tolist(),
            "external": external_moment.tolist(),
            "residual": moment_residual.tolist(),
            "relative_error": moment_relative_error,
            "tolerance": moment_tolerance,
            "status": "PASS" if moment_relative_error <= moment_tolerance else "FAIL",
        },
    }


def _compare_replay_value(
    first: Any,
    second: Any,
    relative_tolerance: float,
    absolute_floor: float,
) -> dict[str, Any]:
    first_array = np.asarray(first, dtype=float)
    second_array = np.asarray(second, dtype=float)
    if first_array.shape != second_array.shape or not np.isfinite(first_array).all() or not np.isfinite(second_array).all():
        return {"status": "FAIL", "reason": "SHAPE_OR_NONFINITE", "shape_first": first_array.shape, "shape_second": second_array.shape}
    absolute = np.abs(first_array - second_array)
    scale = np.maximum(np.maximum(np.abs(first_array), np.abs(second_array)), absolute_floor)
    relative = absolute / scale
    allowed = np.maximum(absolute_floor, relative_tolerance * scale)
    return {
        "status": "PASS" if bool(np.all(absolute <= allowed)) else "FAIL",
        "absolute_difference": absolute.tolist(),
        "relative_difference": relative.tolist(),
        "allowed_absolute_difference": allowed.tolist(),
    }


def check_replay(
    first: Mapping[str, Any],
    second: Mapping[str, Any],
    contract: StructuralBenchmarkContract | None = None,
) -> dict[str, Any]:
    """Check the complete H1 replay contract, including vectors/history/count."""
    contract = contract or StructuralBenchmarkContract()
    scalar_keys = (
        "mean_end_displacement_y",
        "strain_energy",
        "representative_sigma_xx",
        "minimum_det_F",
        "principal_stretch_min",
        "principal_stretch_max",
        "maximum_green_lagrange_strain_norm",
    )
    vector_keys = ("clamp_reaction_resultant", "clamp_reaction_moment")
    required = (*scalar_keys, *vector_keys, "accepted_load_factor_history", "newton_iteration_count")
    missing = sorted({key for key in required if key not in first or key not in second})
    if missing:
        return {"status": "FAIL", "reason": "MISSING_REPLAY_OBSERVABLE", "missing": missing}
    scalar_results = {
        key: _compare_replay_value(first[key], second[key], contract.replay_relative_tolerance, contract.replay_absolute_floor)
        for key in scalar_keys
    }
    vector_results = {
        key: _compare_replay_value(first[key], second[key], contract.replay_relative_tolerance, contract.replay_absolute_floor)
        for key in vector_keys
    }
    history_first = np.asarray(first["accepted_load_factor_history"], dtype=float)
    history_second = np.asarray(second["accepted_load_factor_history"], dtype=float)
    if history_first.ndim != 1 or history_second.ndim != 1 or history_first.shape != history_second.shape:
        history_result = {"status": "FAIL", "reason": "HISTORY_LENGTH_OR_SHAPE_MISMATCH"}
    else:
        history_result = _compare_replay_value(
            history_first,
            history_second,
            contract.replay_relative_tolerance,
            contract.replay_absolute_floor,
        )
    count_equal = first["newton_iteration_count"] == second["newton_iteration_count"]
    count_result = {
        "status": "PASS" if count_equal else "FAIL",
        "first": first["newton_iteration_count"],
        "second": second["newton_iteration_count"],
        "exact_equality_required": True,
    }
    results = (*scalar_results.values(), *vector_results.values(), history_result, count_result)
    return {
        "status": "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL",
        "scalar_observables": scalar_results,
        "vector_observables": vector_results,
        "accepted_load_factor_history": history_result,
        "newton_iteration_count": count_result,
        "binary_state_hash_required": False,
    }


def evaluate_mesh_delta(
    h2: Mapping[str, Any],
    h3: Mapping[str, Any],
    contract: StructuralBenchmarkContract | None = None,
) -> dict[str, Any]:
    """Apply frozen H2-to-H3 thresholds and fail closed on missing values."""
    contract = contract or StructuralBenchmarkContract()
    value_map: tuple[tuple[str, str, str], ...] = (
        ("mean_end_displacement", "mean_end_displacement_y", "scalar"),
        ("reaction_resultant", "clamp_reaction_resultant", "vector"),
        ("reaction_moment", "clamp_reaction_moment", "vector"),
        ("strain_energy", "strain_energy", "scalar"),
        ("representative_sigma_xx", "representative_sigma_xx", "scalar"),
    )
    thresholds = dict(contract.mesh_thresholds)
    missing: list[str] = []
    results: dict[str, Any] = {}
    for metric, key, _kind in value_map:
        if key not in h2 or key not in h3:
            missing.append(metric)
            continue
        first = np.asarray(h2[key], dtype=float)
        second = np.asarray(h3[key], dtype=float)
        if first.shape != second.shape or not np.isfinite(first).all() or not np.isfinite(second).all():
            results[metric] = {"status": "FAIL", "reason": "SHAPE_OR_NONFINITE"}
            continue
        denominator = max(float(np.linalg.norm(first)), float(np.linalg.norm(second)), 1.0e-14)
        change = float(np.linalg.norm(second - first)) / denominator
        threshold = float(thresholds[metric])
        results[metric] = {
            "status": "PASS" if change <= threshold else "FAIL",
            "relative_change": change,
            "threshold": threshold,
        }
    if missing:
        return {"status": "FAIL", "reason": "MISSING_MESH_OBSERVABLE", "missing": missing, "results": results}
    return {
        "status": "PASS" if all(item["status"] == "PASS" for item in results.values()) else "FAIL",
        "results": results,
        "h2_to_h3_only": True,
    }


def check_deformation_envelope(observables: Mapping[str, Any], contract: StructuralBenchmarkContract | None = None) -> dict[str, Any]:
    """Check the frozen deformation envelope without changing any threshold."""
    contract = contract or StructuralBenchmarkContract()
    minimum_det, stretch_bounds, strain_limit = contract.deformation_envelope
    checks = {
        "minimum_det_F": float(observables["minimum_det_F"]) >= minimum_det,
        "principal_stretches": float(observables["principal_stretch_min"]) >= stretch_bounds[0]
        and float(observables["principal_stretch_max"]) <= stretch_bounds[1],
        "maximum_green_lagrange_strain_norm": float(observables["maximum_green_lagrange_strain_norm"]) <= strain_limit,
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def estimate_resources(
    family: str,
    level: MeshLevel,
    assembly_chunk_size: int = 256,
    contract: StructuralBenchmarkContract | None = None,
) -> dict[str, Any]:
    """Estimate memory from deterministic mesh counts, without assembling/solving."""
    contract = contract or StructuralBenchmarkContract()
    mesh = build_mesh(family, level, contract)
    return _estimate_resources_for_mesh(mesh, assembly_chunk_size)


def _estimate_resources_for_mesh(mesh: MeshData, assembly_chunk_size: int = 256) -> dict[str, Any]:
    """Estimate resources from a mesh already generated for the report."""
    local_nodes = 10 if mesh.family == "TET10" else 20
    local_dofs = 3 * local_nodes
    raw_tangent_entries = mesh.elements * local_dofs * local_dofs
    upper_global_nnz = min(mesh.dofs * mesh.dofs, raw_tangent_entries)
    coordinate_bytes = mesh.nodes * 3 * 8
    connectivity_bytes = mesh.elements * local_nodes * 8
    staged_entries = min(mesh.elements, assembly_chunk_size) * local_dofs * local_dofs
    staged_bytes = staged_entries * (8 + 4 + 4)
    rough_csr_bytes = upper_global_nnz * 20
    total_bytes = coordinate_bytes + connectivity_bytes + staged_bytes + rough_csr_bytes
    return {
        "family": mesh.family,
        "level": mesh.level.name,
        "nodes": mesh.nodes,
        "elements": mesh.elements,
        "dofs": mesh.dofs,
        "local_dofs": local_dofs,
        "raw_tangent_nnz_upper_bound": raw_tangent_entries,
        "rough_coordinate_bytes": coordinate_bytes,
        "rough_connectivity_bytes": connectivity_bytes,
        "rough_staged_triplet_bytes": staged_bytes,
        "rough_global_csr_bytes": rough_csr_bytes,
        "rough_total_bytes": total_bytes,
        "rough_total_mib": total_bytes / (1024.0**2),
        "mesh_resource_estimate_available": True,
        "solve_resource_readiness": "UNKNOWN_PENDING_MEASURED_H1",
        "excluded_from_estimate": [
            "Newton state vectors",
            "assembly runtime overhead",
            "Krylov workspace",
            "preconditioner storage",
            "sparse factorization fill-in",
            "Python/SciPy overhead",
            "telemetry",
            "process overhead",
        ],
        "qualification_solve_executed": False,
    }


class StructuralQualificationRunner:
    """Future runner facade; all mechanics remain outside this preparation module."""

    def __init__(
        self,
        contract: StructuralBenchmarkContract | None = None,
        termination_policy: TerminationPolicy = DEFAULT_TERMINATION_POLICY,
    ) -> None:
        self.contract = contract or StructuralBenchmarkContract()
        self.termination_policy = termination_policy

    def prepare_mesh(self, family: str, level: MeshLevel | str) -> tuple[MeshData, dict[str, Any]]:
        mesh = build_mesh(family, level, self.contract)
        return mesh, mesh_quality(mesh)

    def check_replay(self, first: Mapping[str, Any], second: Mapping[str, Any]) -> dict[str, Any]:
        return check_replay(first, second, self.contract)

    def evaluate_equilibrium(
        self,
        clamp_coordinates: np.ndarray,
        clamp_reactions: np.ndarray,
        external_coordinates: np.ndarray,
        external_loads: np.ndarray,
    ) -> dict[str, Any]:
        """Evaluate all force and moment components with the frozen policy."""
        return evaluate_equilibrium(clamp_coordinates, clamp_reactions, external_coordinates, external_loads)

    def evaluate_mesh_delta(self, h2: Mapping[str, Any], h3: Mapping[str, Any]) -> dict[str, Any]:
        """Apply the frozen family-local H2-to-H3 thresholds."""
        return evaluate_mesh_delta(h2, h3, self.contract)

    def evaluate_precomputed(self, observables: Mapping[str, Any]) -> dict[str, Any]:
        """Evaluate future solver output; this method does not call a solver."""
        finite = all(np.isfinite(float(observables[key])) for key in (
            "mean_end_displacement_y",
            "strain_energy",
            "representative_sigma_xx",
            "minimum_det_F",
            "principal_stretch_min",
            "principal_stretch_max",
            "maximum_green_lagrange_strain_norm",
        ))
        envelope = check_deformation_envelope(observables, self.contract)
        return {
            "status": "PASS" if finite and envelope["status"] == "PASS" else "FAIL",
            "termination_policy": self.termination_policy.name,
            "solver_invoked": False,
            "finite_observables": finite,
            "deformation_envelope": envelope,
        }


def build_preparation_report(contract: StructuralBenchmarkContract | None = None) -> dict[str, Any]:
    """Build machine-readable preparation metadata; no H1/H2/H3 solve occurs."""
    contract = contract or StructuralBenchmarkContract()
    meshes: dict[str, dict[str, dict[str, Any]]] = {}
    resource_estimates: dict[str, dict[str, dict[str, Any]]] = {}
    prepared_meshes: dict[str, dict[str, MeshData]] = {}
    for family in ("TET10", "HEX20"):
        meshes[family] = {}
        resource_estimates[family] = {}
        prepared_meshes[family] = {}
        for level in MESH_LEVELS:
            mesh = build_mesh(family, level, contract)
            prepared_meshes[family][level.name] = mesh
            meshes[family][level.name] = {
                "nodes": mesh.nodes,
                "elements": mesh.elements,
                "dofs": mesh.dofs,
                "end_face_nodes": len(mesh.end_face_nodes),
                "reference_volume": mesh.reference_volume,
                "quality": mesh_quality(mesh),
                "volume_conservation": check_volume_conservation(mesh, contract),
                "load_conservation": check_load_conservation(mesh, contract),
                "mesh_generation_only": True,
            }
            resource_estimates[family][level.name] = _estimate_resources_for_mesh(mesh)
    cross_family_load_checks = {
        level.name: compare_physical_loads(
            prepared_meshes["TET10"][level.name], prepared_meshes["HEX20"][level.name], contract
        )
        for level in MESH_LEVELS
    }
    return {
        "schema_version": "1.0",
        "evidence_id": "VNV029-WP05-CD-STRUCTURAL-CONTRACT-001",
        "status": "PREPARATION_ONLY_PENDING_WP04",
        "gate": "WP05-C/D",
        "formal_points": {"WP05-C": "0/1", "WP05-D": "0/1", "WP05": "0/5"},
        "validated_release_total": "29/100",
        "owner_correction_r1": {
            "initial_equal_node_rule": "equal share over every x=L node",
            "initial_rule_status": "OWNER_REJECTED_BEFORE_ANY_MECHANICAL_SOLVE",
            "final_rule": "CONSISTENT_EQUIVALENT_NODAL_TRACTION",
        },
        "benchmark": contract.as_dict(),
        "mesh_levels": [level.__dict__ for level in MESH_LEVELS],
        "families": ["TET10", "HEX20"],
        "meshes": meshes,
        "resource_estimates": resource_estimates,
        "cross_family_load_checks": cross_family_load_checks,
        "termination_policy": {
            "name": DEFAULT_TERMINATION_POLICY.name,
            "source": DEFAULT_TERMINATION_POLICY.source,
            "agent_a_experimental_policy_imported": DEFAULT_TERMINATION_POLICY.agent_a_policy,
        },
        "observables": [
            "mean_end_displacement_y",
            "clamp_reaction_resultant",
            "clamp_reaction_moment",
            "clamp_reaction_moment_z",
            "strain_energy",
            "representative_sigma_xx",
            "minimum_det_F",
            "principal_stretch_min",
            "principal_stretch_max",
            "maximum_green_lagrange_strain_norm",
            "accepted_load_factor_history",
            "newton_iteration_count",
        ],
        "evaluators": {
            "force_equilibrium": "evaluate_equilibrium, all 3 force components, relative error <= 1e-8",
            "moment_equilibrium": "evaluate_equilibrium, all 3 origin-moment components, relative error <= 1e-8",
            "h1_replay": "check_replay, complete scalar/vector/history/count contract",
            "h2_to_h3_mesh_delta": "evaluate_mesh_delta, frozen per-family thresholds, missing/nonfinite=FAIL",
        },
        "cross_family_candidate_thresholds": {
            "mean_end_displacement": 0.03,
            "reaction_resultant": 0.02,
            "reaction_moment": 0.03,
            "strain_energy": 0.03,
            "representative_sigma_xx": 0.10,
            "owner_review_required": True,
            "wp05_e_executed": False,
        },
        "execution": {
            "h1_smoke_run": False,
            "h1_smoke_status": "SKIPPED_AGENT_A_ACTIVE",
            "h1_replay_run": False,
            "h2_qualification_run": False,
            "h3_qualification_run": False,
            "solver_or_formulation_modified": False,
        },
    }


def main() -> None:
    """Print the frozen preparation report for review or artifact generation."""
    print(json.dumps(build_preparation_report(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
