"""Five-level structural convergence studies for the MITC4 element."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np

from mitc4.benchmarks import ScordelisLoBenchmark
from mitc4.constants import DOF_PER_NODE, RX, RZ, UX, UY, UZ
from mitc4.material import ShellMaterial
from mitc4.model import ShellModel


@dataclass(frozen=True)
class ConvergencePoint:
    mesh: tuple[int, int]
    element_count: int
    value: float
    reference: float
    relative_error: float
    solver_method: str = "direct"
    solver_iterations: int | None = None
    solver_relative_residual: float | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class StructuralConvergence:
    identifier: str
    points: tuple[ConvergencePoint, ...]
    error_limit: float
    status: str
    final_increment: float
    minimum_reference_error: float
    review_status: str
    recommendation: str

    def to_dict(self) -> dict[str, object]:
        return {
            "study_id": self.identifier,
            "status": self.status,
            "error_limit": self.error_limit,
            "points": [point.to_dict() for point in self.points],
            "final_increment": self.final_increment,
            "minimum_reference_error": self.minimum_reference_error,
            "review_status": self.review_status,
            "recommendation": self.recommendation,
        }


class Mitc4StructuralConvergence:
    """Run Cook, Scordelis-Lo and pinched-cylinder h studies."""

    def run(self, *, quick: bool = False) -> dict[str, StructuralConvergence]:
        if quick:
            return {}
        return {
            "cook": self._study(
                "VNV-MITC4-COOK-001",
                ((4, 4), (8, 8), (16, 16), (24, 24), (32, 32), (64, 64)),
                0.05,
                _cook_point,
            ),
            "scordelis": self._study(
                "VNV-MITC4-SCORDELIS-001",
                ((8, 8), (12, 12), (16, 16), (24, 24), (32, 32)),
                0.02,
                _scordelis_point,
            ),
            "pinched": self._study(
                "VNV-MITC4-PINCHED-001",
                ((8, 16), (12, 24), (16, 32), (24, 48), (32, 64)),
                0.10,
                _pinched_point,
            ),
        }

    @staticmethod
    def drilling_sensitivity(
        scales: tuple[float, ...] = (1.0e-6, 1.0e-5, 1.0e-4, 1.0e-3, 1.0e-2),
    ) -> dict[str, object]:
        points = [
            {"drilling_scale": scale, "tip_displacement": _cook_point(16, 16, scale).value}
            for scale in scales
        ]
        baseline = next(point["tip_displacement"] for point in points if point["drilling_scale"] == 1.0e-4)
        for point in points:
            point["relative_change"] = abs(point["tip_displacement"] - baseline) / max(abs(baseline), 1.0e-30)
        plateau = max(
            point["relative_change"]
            for point in points
            if 1.0e-5 <= point["drilling_scale"] <= 1.0e-3
        )
        return {
            "study_id": "VNV-MITC4-DRILLING-001",
            "status": "PASS" if plateau <= 0.01 else "FAIL",
            "plateau_relative_change": plateau,
            "plateau_limit": 0.01,
            "selected_scale": 1.0e-4,
            "points": points,
        }

    @staticmethod
    def _study(
        identifier: str,
        meshes: tuple[tuple[int, int], ...],
        limit: float,
        runner: object,
    ) -> StructuralConvergence:
        points = tuple(runner(*mesh) for mesh in meshes)
        final_error = points[-1].relative_error
        minimum_error = min(point.relative_error for point in points)
        final_increment = abs(points[-1].value - points[-2].value) / max(abs(points[-1].value), 1.0e-30)
        status = "PASS" if final_error <= limit and final_increment <= limit else "FAIL"
        review_status = "WARNING" if final_error > minimum_error + 0.01 else "PASS"
        recommendation = (
            "The reference error rises after an earlier minimum; audit the Cook reference and boundary conditions "
            "before claiming full static acceptance."
            if review_status == "WARNING"
            else "Reference-error trend is compatible with the current acceptance criterion."
        )
        return StructuralConvergence(
            identifier,
            points,
            limit,
            status,
            final_increment,
            minimum_error,
            review_status,
            recommendation,
        )


def cook_large_point(nx: int = 200, ny: int = 200) -> ConvergencePoint:
    """Run an opt-in, memory-bounded Cook refinement point."""
    return _cook_point(nx, ny, iterative=True)


def _cook_point(
    nx: int,
    ny: int,
    drilling_scale: float = 1.0e-4,
    *,
    iterative: bool = False,
) -> ConvergencePoint:
    scale = 0.01
    corners = scale * np.asarray(
        [[0.0, 0.0, 0.0], [48.0, 44.0, 0.0], [48.0, 60.0, 0.0], [0.0, 44.0, 0.0]]
    )
    nodes, quads, node = _bilinear_mesh(corners, nx, ny)
    young, thickness, total_force = 1.0e6, 0.01, 100.0
    model = ShellModel(
        nodes,
        quads,
        ShellMaterial(E=young, nu=1.0 / 3.0, t=thickness, drilling_scale=drilling_scale),
    )
    edge_length = float(np.linalg.norm(corners[2] - corners[1]))
    traction = total_force / edge_length
    for j in range(ny):
        first, second = node(nx, j), node(nx, j + 1)
        segment = float(np.linalg.norm(nodes[second] - nodes[first]))
        model.add_nodal_load(first, UY, 0.5 * traction * segment)
        model.add_nodal_load(second, UY, 0.5 * traction * segment)
    for j in range(ny + 1):
        model.fix_node(node(0, j))
    diagnostics: dict[str, float | int | str] = {}
    if iterative:
        displacement, diagnostics = model.solve_iterative()
    else:
        displacement = model.solve()
    tip = node(nx, ny)
    value = float(displacement[tip * DOF_PER_NODE + UY])
    reference = 23.96 * total_force / (young * thickness)
    return _point(
        nx,
        ny,
        value,
        reference,
        solver_method=str(diagnostics.get("method", "direct")),
        solver_iterations=int(diagnostics["iterations"]) if "iterations" in diagnostics else None,
        solver_relative_residual=(
            float(diagnostics["relative_residual"]) if "relative_residual" in diagnostics else None
        ),
    )


def _scordelis_point(nx: int, ny: int) -> ConvergencePoint:
    result = ScordelisLoBenchmark(nx, ny).run().values
    value = 0.5 * (result["w_edge_center"] + result["w_opposite_edge_center"])
    return _point(nx, ny, value, result["reference"])


def _pinched_point(nx: int, ntheta: int) -> ConvergencePoint:
    length, radius = 600.0, 300.0
    nodes, quads, node = _periodic_cylinder(length, radius, nx, ntheta)
    model = ShellModel(nodes, quads, ShellMaterial(E=3.0e6, nu=0.3, t=3.0))
    for j in range(ntheta):
        for i in (0, nx):
            model.add_fixed_dof(node(i, j), UY)
            model.add_fixed_dof(node(i, j), UZ)
            model.add_fixed_dof(node(i, j), RX)
    model.add_fixed_dof(node(0, 0), UX)
    model.add_fixed_dof(node(0, 0), RZ)
    load_a = node(nx // 2, 0)
    load_b = node(nx // 2, ntheta // 2)
    model.add_nodal_load(load_a, UY, -1.0)
    model.add_nodal_load(load_b, UY, 1.0)
    displacement = model.solve()
    value = abs(float(displacement[load_a * DOF_PER_NODE + UY]))
    return _point(nx, ntheta, value, 1.8248e-5)


def _point(
    nx: int,
    ny: int,
    value: float,
    reference: float,
    *,
    solver_method: str = "direct",
    solver_iterations: int | None = None,
    solver_relative_residual: float | None = None,
) -> ConvergencePoint:
    return ConvergencePoint(
        mesh=(nx, ny),
        element_count=nx * ny,
        value=value,
        reference=reference,
        relative_error=abs((value - reference) / reference),
        solver_method=solver_method,
        solver_iterations=solver_iterations,
        solver_relative_residual=solver_relative_residual,
    )


def _bilinear_mesh(
    corners: np.ndarray, nx: int, ny: int
) -> tuple[np.ndarray, np.ndarray, object]:
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


def _periodic_cylinder(
    length: float, radius: float, nx: int, ntheta: int
) -> tuple[np.ndarray, np.ndarray, object]:
    nodes = [
        [-0.5 * length + length * i / nx, radius * math.cos(2.0 * math.pi * j / ntheta), radius * math.sin(2.0 * math.pi * j / ntheta)]
        for i in range(nx + 1)
        for j in range(ntheta)
    ]

    def node(i: int, j: int) -> int:
        return i * ntheta + (j % ntheta)

    quads = [
        [node(i, j), node(i + 1, j), node(i + 1, j + 1), node(i, j + 1)]
        for i in range(nx)
        for j in range(ntheta)
    ]
    return np.asarray(nodes), np.asarray(quads, dtype=int), node
