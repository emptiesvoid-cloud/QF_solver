"""Meshed MITC4 shell obstacle-course benchmarks."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.benchmarks.support import BenchmarkContext, free_residual, run_status, upper_check
from solveur.benchmarks.types import BenchmarkRun


def run_cook(context: BenchmarkContext) -> BenchmarkRun:
    """Run Cook's skew membrane with a physical edge traction."""
    nx = ny = 16
    scale = 0.01
    corners = scale * np.asarray([[0.0, 0.0, 0.0], [48.0, 44.0, 0.0], [48.0, 60.0, 0.0], [0.0, 44.0, 0.0]])
    nodes, quads, node = _bilinear_quad_mesh(corners, nx, ny)
    left = [(node(0, j), node(0, j + 1)) for j in range(ny)]
    right = [(node(nx, j), node(nx, j + 1)) for j in range(ny)]
    mesh = BenchmarkMeshFactory().discrete_mitc4(
        context.root / "cook_mitc4.msh",
        nodes=nodes,
        quads=quads,
        line_groups={"fixed": left, "loaded_edge": right},
    )
    young, thickness, total_force = 1.0e6, 0.01, 100.0
    edge_length = float(np.linalg.norm(corners[2] - corners[1]))
    setup = _shell_setup(young, 1.0 / 3.0, thickness, context.profile)
    setup["groups"].extend(
        [
            _fixed("fixed", 1, ["UX", "UY", "UZ", "RX", "RY", "RZ"]),
            {
                "name": "loaded_edge",
                "dimension": 1,
                "actions": [{"type": "edge_traction", "value": [0.0, total_force / edge_length, 0.0]}],
            },
        ]
    )
    model, result, files = context.import_and_solve(mesh, setup)
    tip_node = int(np.argmax(model.nodes[:, 0] + 1.0e-3 * model.nodes[:, 1]))
    tip = float(result.displacements[result.dofs.index(tip_node, "UY")])
    reference = 23.96 * total_force / (young * thickness)
    error = abs((tip - reference) / reference)
    residual = free_residual(result)
    criteria = context.descriptor.criteria
    checks = [
        upper_check("normalized-tip", error, criteria["normalized_tip_error_max"]),
        upper_check("free-residual", residual, criteria["free_residual_max"]),
    ]
    return context.finalize(
        BenchmarkRun(
            context.descriptor,
            run_status(checks),
            {
                "mesh": [nx, ny],
                "tip_uy": tip,
                "reference_tip_uy": reference,
                "normalized_tip_error": error,
                "free_relative_residual": residual,
            },
            checks,
            files,
        )
    )


def run_scordelis(context: BenchmarkContext) -> BenchmarkRun:
    """Run the curved Scordelis-Lo roof through the public model path."""
    nx = ny = 20
    length, radius = 50.0, 25.0
    nodes, quads, node = _cylindrical_panel_mesh(length, radius, math.radians(80.0), nx, ny)
    ends = [(node(0, j), node(0, j + 1)) for j in range(ny)]
    ends.extend((node(nx, j), node(nx, j + 1)) for j in range(ny))
    mesh = BenchmarkMeshFactory().discrete_mitc4(
        context.root / "scordelis_mitc4.msh",
        nodes=nodes,
        quads=quads,
        line_groups={"diaphragms": ends},
        point_groups={"anchor": [node(0, 0)]},
    )
    setup = _shell_setup(4.32e8, 0.0, 0.25, context.profile)
    setup["groups"][0]["actions"].append(
        {"type": "surface_traction", "value": [0.0, 0.0, -90.0], "coordinate_system": "global"}
    )
    setup["groups"].extend(
        [
            _fixed("diaphragms", 1, ["UY", "UZ"]),
            _fixed("anchor", 0, ["UX", "RZ"]),
        ]
    )
    model, result, files = context.import_and_solve(mesh, setup)
    edge_a = node(nx // 2, 0)
    edge_b = node(nx // 2, ny)
    value_a = float(result.displacements[result.dofs.index(edge_a, "UZ")])
    value_b = float(result.displacements[result.dofs.index(edge_b, "UZ")])
    reference = -0.3024
    error = abs((0.5 * (value_a + value_b) - reference) / reference)
    symmetry = abs(value_a - value_b) / abs(reference)
    criteria = context.descriptor.criteria
    checks = [
        upper_check("edge-displacement", error, criteria["edge_displacement_error_max"]),
        upper_check("symmetry", symmetry, criteria["symmetry_error_max"]),
        upper_check("free-residual", free_residual(result), 1.0e-8),
    ]
    return context.finalize(
        BenchmarkRun(
            context.descriptor,
            run_status(checks),
            {
                "mesh": [nx, ny],
                "edge_uz_a": value_a,
                "edge_uz_b": value_b,
                "reference_edge_uz": reference,
                "edge_displacement_error": error,
                "symmetry_error": symmetry,
                "reference_caveat": "Historical converged value; provenance limitations are documented on the site.",
            },
            checks,
            files,
        )
    )


def run_pinched_cylinder(context: BenchmarkContext) -> BenchmarkRun:
    """Run a full pinched cylinder with opposite point loads and end diaphragms."""
    nx, ntheta = 32, 64
    length, radius = 600.0, 300.0
    nodes, quads, node = _periodic_cylinder_mesh(length, radius, nx, ntheta)
    ends = [(node(0, j), node(0, (j + 1) % ntheta)) for j in range(ntheta)]
    ends.extend((node(nx, j), node(nx, (j + 1) % ntheta)) for j in range(ntheta))
    load_a = node(nx // 2, 0)
    load_b = node(nx // 2, ntheta // 2)
    mesh = BenchmarkMeshFactory().discrete_mitc4(
        context.root / "pinched_cylinder_mitc4.msh",
        nodes=nodes,
        quads=quads,
        line_groups={"diaphragms": ends},
        point_groups={"anchor": [node(0, 0)], "load_a": [load_a], "load_b": [load_b]},
    )
    setup = _shell_setup(3.0e6, 0.3, 3.0, context.profile, units="consistent_benchmark")
    setup["groups"].extend(
        [
            _fixed("diaphragms", 1, ["UY", "UZ", "RX"]),
            _fixed("anchor", 0, ["UX", "RZ"]),
            _nodal("load_a", "UY", -1.0),
            _nodal("load_b", "UY", 1.0),
        ]
    )
    _, result, files = context.import_and_solve(mesh, setup)
    displacement = abs(float(result.displacements[result.dofs.index(load_a, "UY")]))
    reference = 1.8248e-5
    error = abs((displacement - reference) / reference)
    residual = free_residual(result)
    criteria = context.descriptor.criteria
    checks = [
        upper_check("pinched-displacement", error, criteria["normalized_displacement_error_max"]),
        upper_check("free-residual", residual, criteria["free_residual_max"]),
    ]
    return context.finalize(
        BenchmarkRun(
            context.descriptor,
            run_status(checks),
            {
                "mesh": [nx, ntheta],
                "loaded_point_displacement": displacement,
                "reference_displacement": reference,
                "normalized_displacement_error": error,
                "free_relative_residual": residual,
            },
            checks,
            files,
        )
    )


def _shell_setup(
    young: float,
    poisson: float,
    thickness: float,
    profile: str,
    *,
    units: str = "SI",
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": units},
        "verification_profile": profile,
        "analysis": {"type": "linear_static", "method": "direct"},
        "materials": {"shell": {"type": "shell_isotropic", "E": young, "nu": poisson, "t": thickness, "density": 1.0}},
        "groups": [
            {
                "name": "shell",
                "dimension": 2,
                "actions": [{"type": "elements", "element_type": "MITC4", "material": "shell"}],
            }
        ],
    }


def _fixed(name: str, dimension: int, dofs: list[str]) -> dict[str, Any]:
    return {"name": name, "dimension": dimension, "actions": [{"type": "fixed_dofs", "dofs": dofs}]}


def _nodal(name: str, dof: str, value: float) -> dict[str, Any]:
    return {"name": name, "dimension": 0, "actions": [{"type": "nodal_load", "dof": dof, "value": value}]}


def _bilinear_quad_mesh(
    corners: np.ndarray,
    nx: int,
    ny: int,
) -> tuple[np.ndarray, np.ndarray, Any]:
    nodes = []
    for i in range(nx + 1):
        xi = i / nx
        for j in range(ny + 1):
            eta = j / ny
            point = (
                (1.0 - xi) * (1.0 - eta) * corners[0]
                + xi * (1.0 - eta) * corners[1]
                + xi * eta * corners[2]
                + (1.0 - xi) * eta * corners[3]
            )
            nodes.append(point)

    def node(i: int, j: int) -> int:
        return i * (ny + 1) + j

    quads = [
        [node(i, j), node(i + 1, j), node(i + 1, j + 1), node(i, j + 1)]
        for i in range(nx)
        for j in range(ny)
    ]
    return np.asarray(nodes), np.asarray(quads, dtype=int), node


def _cylindrical_panel_mesh(
    length: float,
    radius: float,
    angle: float,
    nx: int,
    ny: int,
) -> tuple[np.ndarray, np.ndarray, Any]:
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


def _periodic_cylinder_mesh(
    length: float,
    radius: float,
    nx: int,
    ntheta: int,
) -> tuple[np.ndarray, np.ndarray, Any]:
    nodes = []
    for i in range(nx + 1):
        x = -0.5 * length + length * i / nx
        for j in range(ntheta):
            theta = 2.0 * math.pi * j / ntheta
            nodes.append([x, radius * math.cos(theta), radius * math.sin(theta)])

    def node(i: int, j: int) -> int:
        return i * ntheta + (j % ntheta)

    quads = [
        [node(i, j), node(i + 1, j), node(i + 1, j + 1), node(i, j + 1)]
        for i in range(nx)
        for j in range(ntheta)
    ]
    return np.asarray(nodes), np.asarray(quads, dtype=int), node
