"""Deterministic triangular shell models used by the MITC3+ V&V campaign."""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np

from solveur.core.model import FiniteElementModel

NodeIndexer = Callable[[int, int], int]

# Single source of truth for the laminate used by the MITC3 correlation decks.
LAMINATE_MATERIAL: dict[str, float] = {
    "E1": 130.0e9,
    "E2": 9.0e9,
    "nu12": 0.28,
    "G12": 5.0e9,
    "G13": 4.0e9,
    "G23": 3.5e9,
    "density": 1550.0,
}


def rectangular_tri_mesh(
    length: float,
    width: float,
    nx: int,
    ny: int,
    *,
    distortion: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, NodeIndexer]:
    """Return a consistently oriented two-triangle-per-cell rectangular mesh."""
    nodes = np.array(
        [[length * i / nx, width * j / ny, 0.0] for i in range(nx + 1) for j in range(ny + 1)],
        dtype=float,
    )

    def node(i: int, j: int) -> int:
        return i * (ny + 1) + j

    if distortion:
        for i in range(1, nx):
            for j in range(1, ny):
                phase = -1.0 if (i + j) % 2 else 1.0
                nodes[node(i, j), 0] += phase * distortion * length / nx
                nodes[node(i, j), 1] -= phase * distortion * width / ny
    triangles = []
    for i in range(nx):
        for j in range(ny):
            a, b = node(i, j), node(i + 1, j)
            c, d = node(i + 1, j + 1), node(i, j + 1)
            triangles.extend(((a, b, c), (a, c, d)))
    return nodes, np.asarray(triangles, dtype=int), node


def cantilever_model(
    nx: int,
    ny: int,
    *,
    thickness: float = 0.01,
    analysis: str | dict[str, object] = "linear_static",
    distortion: float = 0.0,
    laminate: bool = False,
    transverse_force: float = -1.0,
) -> FiniteElementModel:
    """Build a 1 x 0.2 clamped strip with a resultant end force."""
    nodes, triangles, node = rectangular_tri_mesh(1.0, 0.2, nx, ny, distortion=distortion)
    material = _laminate(thickness) if laminate else _isotropic(thickness)
    edge_nodes = [node(nx, j) for j in range(ny + 1)]
    weights = np.ones(ny + 1)
    weights[[0, -1]] = 0.5
    weights /= weights.sum()
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=_elements(triangles),
        materials={"skin": material},
        fixed_dofs=[{"node": node(0, j), "dofs": _shell_dofs()} for j in range(ny + 1)],
        loads=[
            {"node": current, "dof": "UZ", "value": transverse_force * float(weight)}
            for current, weight in zip(edge_nodes, weights, strict=True)
        ],
        analysis=analysis,
        verification_profile="quick",
    )


def cook_model(level: int) -> tuple[FiniteElementModel, int]:
    """Build Cook's skew membrane using MITC3+ triangles."""
    nx = ny = level
    scale = 0.01
    corners = scale * np.asarray(
        [[0.0, 0.0, 0.0], [48.0, 44.0, 0.0], [48.0, 60.0, 0.0], [0.0, 44.0, 0.0]]
    )
    nodes, quads, node = bilinear_quad_mesh(corners, nx, ny)
    triangles = split_quads(quads)
    total_force = 100.0
    edge_nodes = [node(nx, j) for j in range(ny + 1)]
    weights = np.ones(ny + 1)
    weights[[0, -1]] = 0.5
    weights /= weights.sum()
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=_elements(triangles),
        materials={"skin": _isotropic(0.01, young=1.0e6, poisson=1.0 / 3.0)},
        fixed_dofs=[{"node": node(0, j), "dofs": _shell_dofs()} for j in range(ny + 1)],
        loads=[
            {"node": current, "dof": "UY", "value": total_force * float(weight)}
            for current, weight in zip(edge_nodes, weights, strict=True)
        ],
        verification_profile="quick",
    )
    return model, node(nx, ny)


def scordelis_model(nx: int, ny: int) -> tuple[FiniteElementModel, tuple[int, int]]:
    """Build a triangulated faceted Scordelis-Lo roof."""
    nodes, quads, node = cylindrical_panel_mesh(50.0, 25.0, math.radians(80.0), nx, ny)
    triangles = split_quads(quads)
    fixed = [
        {"node": node(i, j), "dofs": ["UY", "UZ"]}
        for i in (0, nx)
        for j in range(ny + 1)
    ]
    fixed.append({"node": node(0, 0), "dofs": ["UX", "RZ"]})
    return (
        FiniteElementModel.from_raw(
            nodes=nodes.tolist(),
            elements=_elements(triangles),
            materials={"skin": _isotropic(0.25, young=4.32e8, poisson=0.0)},
            fixed_dofs=fixed,
            distributed_loads=[
                {
                    "type": "surface_traction",
                    "element": index,
                    "value": [0.0, 0.0, -90.0],
                    "coordinate_system": "global",
                }
                for index in range(len(triangles))
            ],
            verification_profile="quick",
        ),
        (node(nx // 2, 0), node(nx // 2, ny)),
    )


def pinched_cylinder_model(
    nx: int,
    ntheta: int,
) -> tuple[FiniteElementModel, int]:
    """Build the full triangulated pinched-cylinder benchmark."""
    nodes = np.asarray(
        [
            [
                -300.0 + 600.0 * i / nx,
                300.0 * math.cos(2.0 * math.pi * j / ntheta),
                300.0 * math.sin(2.0 * math.pi * j / ntheta),
            ]
            for i in range(nx + 1)
            for j in range(ntheta)
        ],
        dtype=float,
    )

    def node(i: int, j: int) -> int:
        return i * ntheta + (j % ntheta)

    quads = np.asarray(
        [
            [node(i, j), node(i + 1, j), node(i + 1, j + 1), node(i, j + 1)]
            for i in range(nx)
            for j in range(ntheta)
        ],
        dtype=int,
    )
    load_a = node(nx // 2, 0)
    load_b = node(nx // 2, ntheta // 2)
    fixed = [
        {"node": node(i, j), "dofs": ["UY", "UZ", "RX"]}
        for i in (0, nx)
        for j in range(ntheta)
    ]
    fixed.append({"node": node(0, 0), "dofs": ["UX", "RZ"]})
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=_elements(split_quads(quads)),
        materials={"skin": _isotropic(3.0, young=3.0e6, poisson=0.3)},
        fixed_dofs=fixed,
        loads=[
            {"node": load_a, "dof": "UY", "value": -1.0},
            {"node": load_b, "dof": "UY", "value": 1.0},
        ],
        units={"system": "consistent_benchmark"},
        verification_profile="quick",
    )
    return model, load_a


def pinched_hemisphere_model(
    n_meridian: int,
    n_azimuth: int | None = None,
    *,
    load: float = 1.0,
) -> tuple[FiniteElementModel, np.ndarray, dict[str, int]]:
    """Build one symmetric quarter of the classical pinched hemisphere.

    The midsurface has radius 10 and an 18 degree polar cut-out.  The two
    equatorial end nodes receive half loads because they lie on symmetry
    planes. Mirroring the quarter creates two balanced pairs of magnitude 2.
    """
    if n_meridian < 2:
        raise ValueError("Pinched hemisphere requires at least two meridian divisions.")
    n_azimuth = n_meridian if n_azimuth is None else int(n_azimuth)
    if n_azimuth < 2:
        raise ValueError("Pinched hemisphere requires at least two azimuth divisions.")
    radius = 10.0
    alpha_0 = math.radians(18.0)
    nodes = np.asarray(
        [
            [
                radius * math.sin(alpha) * math.cos(phi),
                radius * math.sin(alpha) * math.sin(phi),
                radius * math.cos(alpha),
            ]
            for i in range(n_meridian + 1)
            for alpha in [alpha_0 + (0.5 * math.pi - alpha_0) * i / n_meridian]
            for j in range(n_azimuth + 1)
            for phi in [0.5 * math.pi * j / n_azimuth]
        ],
        dtype=float,
    )

    def node(i: int, j: int) -> int:
        return i * (n_azimuth + 1) + j

    quads = np.asarray(
        [
            [node(i, j), node(i + 1, j), node(i + 1, j + 1), node(i, j + 1)]
            for i in range(n_meridian)
            for j in range(n_azimuth)
        ],
        dtype=int,
    )
    triangles = split_quads(quads)
    point_x = node(n_meridian, 0)
    point_y = node(n_meridian, n_azimuth)
    fixed = [
        {"node": node(i, 0), "dofs": ["UY", "RX", "RZ"]}
        for i in range(n_meridian + 1)
    ]
    fixed.extend(
        {"node": node(i, n_azimuth), "dofs": ["UX", "RY", "RZ"]}
        for i in range(n_meridian + 1)
    )
    fixed.append({"node": point_x, "dofs": ["UZ"]})
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=_elements(triangles),
        materials={"skin": _isotropic(0.04, young=6.825e7, poisson=0.3)},
        fixed_dofs=fixed,
        loads=[
            {"node": point_x, "dof": "UX", "value": -float(load)},
            {"node": point_y, "dof": "UY", "value": float(load)},
        ],
        units={"system": "consistent_benchmark"},
        verification_profile="quick",
    )
    return model, triangles, {"point_x": point_x, "point_y": point_y}


def bilinear_quad_mesh(
    corners: np.ndarray,
    nx: int,
    ny: int,
) -> tuple[np.ndarray, np.ndarray, NodeIndexer]:
    nodes = []
    for i in range(nx + 1):
        xi = i / nx
        for j in range(ny + 1):
            eta = j / ny
            nodes.append(
                (1.0 - xi) * (1.0 - eta) * corners[0]
                + xi * (1.0 - eta) * corners[1]
                + xi * eta * corners[2]
                + (1.0 - xi) * eta * corners[3]
            )

    def node(i: int, j: int) -> int:
        return i * (ny + 1) + j

    quads = [
        [node(i, j), node(i + 1, j), node(i + 1, j + 1), node(i, j + 1)]
        for i in range(nx)
        for j in range(ny)
    ]
    return np.asarray(nodes), np.asarray(quads, dtype=int), node


def cylindrical_panel_mesh(
    length: float,
    radius: float,
    angle: float,
    nx: int,
    ny: int,
) -> tuple[np.ndarray, np.ndarray, NodeIndexer]:
    nodes = []
    for i in range(nx + 1):
        x = length * i / nx
        for j in range(ny + 1):
            theta = -0.5 * angle + angle * j / ny
            nodes.append([x, radius * math.sin(theta), radius * math.cos(theta)])

    def node(i: int, j: int) -> int:
        return i * (ny + 1) + j

    quads = [
        [node(i, j), node(i + 1, j), node(i + 1, j + 1), node(i, j + 1)]
        for i in range(nx)
        for j in range(ny)
    ]
    return np.asarray(nodes), np.asarray(quads, dtype=int), node


def split_quads(quads: np.ndarray) -> np.ndarray:
    return np.asarray(
        [(quad[0], quad[1], quad[2]) for quad in quads]
        + [(quad[0], quad[2], quad[3]) for quad in quads],
        dtype=int,
    )


def _elements(triangles: np.ndarray) -> list[dict[str, object]]:
    return [
        {"type": "MITC3", "nodes": triangle.tolist(), "material": "skin"}
        for triangle in triangles
    ]


def _shell_dofs() -> list[str]:
    return ["UX", "UY", "UZ", "RX", "RY", "RZ"]


def _isotropic(
    thickness: float,
    *,
    young: float = 70.0e9,
    poisson: float = 0.3,
) -> dict[str, object]:
    return {
        "type": "shell_isotropic",
        "E": young,
        "nu": poisson,
        "t": thickness,
        "density": 2700.0,
        "drilling_scale": 1.0e-4,
    }


def _laminate(thickness: float) -> dict[str, object]:
    ply_t = thickness / 4.0
    return {
        "type": "shell_laminate",
        "reference_direction": [1.0, 0.0, 0.0],
        "plies": [
            {
                "name": f"ply-{index + 1}",
                "thickness": ply_t,
                "angle_deg": angle,
                **LAMINATE_MATERIAL,
            }
            for index, angle in enumerate((0.0, 90.0, 90.0, 0.0))
        ],
    }
