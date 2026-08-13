"""Additional TET4 membrane and Saint-Venant torsion benchmarks."""

from __future__ import annotations

from typing import Any

import numpy as np

from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.benchmarks.solid import observed_convergence_order
from solveur.benchmarks.support import BenchmarkContext, free_residual, lower_check, run_status, upper_check
from solveur.benchmarks.types import BenchmarkRun
from solveur.core.model import NodalLoad
from solveur.elements.solid.quadrature import triangle_duffy_rule, triangle_shape_functions
from solveur.mesh.topology import TET10_FACES, TET4_FACES


def run_tet4_membrane(context: BenchmarkContext) -> BenchmarkRun:
    """Exercise a thin 3D TET4 panel under an exact in-plane uniaxial field."""
    factory = BenchmarkMeshFactory()
    length, width, thickness = 2.0, 1.0, 0.2
    young, poisson, sigma = 70.0e9, 0.3, 10.0e6
    reference_ux = sigma * length / young
    traction_rows: list[dict[str, Any]] = []
    compression_rows: list[dict[str, Any]] = []
    files: dict[str, str] = {}
    for level, mesh_size in enumerate((0.34, 0.24, 0.17, 0.13, 0.10), start=1):
        mesh = factory.box_tetra(
            context.root / f"h{level}.msh",
            length=length,
            width=width,
            height=thickness,
            mesh_size=mesh_size,
            anchors=True,
        )
        for label, sign, rows in (
            ("traction", 1.0, traction_rows),
            ("compression", -1.0, compression_rows),
        ):
            model, result, level_files = context.import_and_solve(
                mesh,
                _membrane_setup(young, poisson, sign * sigma, context.profile),
                prefix=f"{label}_h{level}",
            )
            tip = _mean_end_displacement(model, result, "UX")
            stresses = np.asarray([item["stress"] for item in result.to_dict()["element_results"]], dtype=float)
            target = np.zeros_like(stresses)
            target[:, 0] = sign * sigma
            expected = sign * reference_ux
            displacement_error = abs((tip - expected) / expected)
            stress_error = float(np.linalg.norm(stresses - target) / max(np.linalg.norm(target), 1.0e-30))
            rows.append(
                {
                    "level": level,
                    "mesh_size": mesh_size,
                    "node_count": model.node_count,
                    "element_count": len(model.elements),
                    "mean_end_ux": tip,
                    "reference_end_ux": expected,
                    "relative_displacement_error": displacement_error,
                    "relative_stress_error": stress_error,
                    "free_relative_residual": free_residual(result),
                }
            )
            files.update(level_files)
    criteria = context.descriptor.criteria
    checks = [
        upper_check(
            "membrane-displacement",
            max(float(row["relative_displacement_error"]) for row in traction_rows),
            criteria["relative_displacement_error_max"],
        ),
        upper_check(
            "membrane-constant-stress",
            max(float(row["relative_stress_error"]) for row in traction_rows),
            criteria["relative_stress_error_max"],
        ),
        upper_check(
            "membrane-free-residual",
            max(float(row["free_relative_residual"]) for row in traction_rows),
            criteria["free_residual_max"],
        ),
        upper_check(
            "compression-displacement",
            max(float(row["relative_displacement_error"]) for row in compression_rows),
            criteria["relative_displacement_error_max"],
        ),
        upper_check(
            "compression-constant-stress",
            max(float(row["relative_stress_error"]) for row in compression_rows),
            criteria["relative_stress_error_max"],
        ),
        upper_check(
            "compression-free-residual",
            max(float(row["free_relative_residual"]) for row in compression_rows),
            criteria["free_residual_max"],
        ),
    ]
    return context.finalize(
        BenchmarkRun(
            context.descriptor,
            run_status(checks),
            {
                "reference_end_ux": reference_ux,
                "membrane_resultant_nx": sigma * thickness,
                "membrane_h_convergence": traction_rows,
                "compression_h_convergence": compression_rows,
                "max_relative_displacement_error": max(
                    float(row["relative_displacement_error"]) for row in traction_rows + compression_rows
                ),
                "max_relative_stress_error": max(
                    float(row["relative_stress_error"]) for row in traction_rows + compression_rows
                ),
            },
            checks,
            files,
            "These are 3D thin-solid axial patches, not plane-stress or shell elements.",
        )
    )


def run_tet4_torsion(context: BenchmarkContext) -> BenchmarkRun:
    """Compare a circular TET4 shaft to the exact Saint-Venant torsion field."""
    factory = BenchmarkMeshFactory()
    length, radius = 3.0, 0.5
    young, poisson, torque = 80.0e9, 0.3, 1000.0
    shear = young / (2.0 * (1.0 + poisson))
    polar_moment = 0.5 * np.pi * radius**4
    reference_twist = torque * length / (shear * polar_moment)
    rows: list[dict[str, Any]] = []
    files: dict[str, str] = {}
    # The h9 stress probe remains the fine V&V campaign. These eight levels
    # are the reproducible engineering/documentation sweep for a workstation.
    for level, mesh_size in enumerate((0.48, 0.40, 0.34, 0.29, 0.25, 0.21, 0.18, 0.15), start=1):
        prefix = f"h{level}"
        mesh = factory.cylinder_tetra(
            context.root / f"{prefix}.msh",
            length=length,
            radius=radius,
            mesh_size=mesh_size,
        )
        load_diagnostics: dict[str, float] = {}

        def prepare(model: object) -> None:
            load_diagnostics.update(apply_consistent_circular_torsion(model, torque))

        model, result, level_files = context.import_and_solve(
            mesh,
            _torsion_setup(young, poisson, context.profile),
            prefix=prefix,
            prepare_model=prepare,
        )
        twist = _end_twist(model, result)
        twist_error = abs((twist - reference_twist) / reference_twist)
        stress_error = _torsion_stress_error(model, result, torque, polar_moment)
        rows.append(
            {
                "level": level,
                "mesh_size": mesh_size,
                "node_count": model.node_count,
                "element_count": len(model.elements),
                "twist_angle": twist,
                "reference_twist_angle": reference_twist,
                "relative_twist_error": twist_error,
                "relative_stress_l2_error": stress_error,
                "applied_torque": load_diagnostics["resultant_torque_x"],
                "resultant_force_norm": load_diagnostics["resultant_force_norm"],
                "free_relative_residual": free_residual(result),
            }
        )
        files.update(level_files)
    errors = np.asarray([row["relative_twist_error"] for row in rows], dtype=float)
    # Only the final refinements are expected to be in the asymptotic regime
    # for independently generated unstructured tetrahedral meshes.
    asymptotic_rows = rows[-3:]
    asymptotic_errors = np.asarray(
        [row["relative_twist_error"] for row in asymptotic_rows], dtype=float
    )
    order = observed_convergence_order(
        [row["mesh_size"] for row in asymptotic_rows], asymptotic_errors
    )
    monotonicity = float(max(np.max(np.diff(asymptotic_errors)), 0.0))
    criteria = context.descriptor.criteria
    checks = [
        upper_check("torsion-finest-twist", float(errors[-1]), criteria["finest_twist_error_max"]),
        lower_check("torsion-observed-order", order, criteria["observed_order_min"]),
        upper_check("torsion-monotonicity", monotonicity, criteria["monotonicity_tolerance"]),
        upper_check(
            "torsion-load-resultant",
            max(abs(float(row["applied_torque"]) - torque) / torque for row in rows),
            criteria["torque_error_max"],
        ),
        upper_check(
            "torsion-force-resultant",
            max(float(row["resultant_force_norm"]) / torque for row in rows),
            criteria["force_resultant_ratio_max"],
        ),
        upper_check(
            "torsion-free-residual",
            max(float(row["free_relative_residual"]) for row in rows),
            criteria["free_residual_max"],
        ),
    ]
    return context.finalize(
        BenchmarkRun(
            context.descriptor,
            run_status(checks),
            {
                "reference_twist_angle": reference_twist,
                "shear_modulus": shear,
                "polar_moment": polar_moment,
                "torsion_h_convergence": rows,
                "asymptotic_levels": [int(row["level"]) for row in asymptotic_rows],
                "observed_order": order,
                "finest_relative_twist_error": float(errors[-1]),
                "monotonicity_violation": monotonicity,
            },
            checks,
            files,
        )
    )


def apply_consistent_circular_torsion(model: object, torque: float) -> dict[str, float]:
    """Apply the consistent nodal form of t=(0,-alpha*z,alpha*y) on x=max."""
    nodes = np.asarray(model.nodes, dtype=float)
    maximum = float(np.max(nodes[:, 0]))
    tolerance = 1.0e-9 * max(float(np.ptp(nodes[:, 0])), 1.0)
    nodal = np.zeros_like(nodes)
    face_count = 0
    terminal_nodes: set[int] = set()
    for element in model.elements:
        family = str(element.type).upper()
        if family not in {"TET4", "TET10"}:
            raise ValueError("Circular torsion benchmark only supports TET4 and TET10 elements.")
        faces = TET4_FACES if family == "TET4" else TET10_FACES
        connectivity = tuple(int(node) for node in element.nodes)
        for local_face in faces:
            face = np.asarray([connectivity[index] for index in local_face], dtype=int)
            coordinates = nodes[face]
            if not np.all(np.abs(coordinates[:, 0] - maximum) <= tolerance):
                continue
            local_force = _integrate_torsion_face(coordinates)
            for local_node, node in enumerate(face):
                nodal[node] += local_force[local_node]
                terminal_nodes.add(int(node))
            face_count += 1
    if face_count == 0:
        raise ValueError("Circular torsion benchmark found no terminal tetrahedral faces.")
    terminal = np.asarray(sorted(terminal_nodes), dtype=int)
    raw_resultant = np.sum(nodal, axis=0)
    nodal[terminal] -= raw_resultant / len(terminal)
    correction_norm = float(np.linalg.norm(raw_resultant))
    raw_torque = float(np.sum(nodes[:, 1] * nodal[:, 2] - nodes[:, 2] * nodal[:, 1]))
    if not np.isfinite(raw_torque) or abs(raw_torque) <= 1.0e-30:
        raise ValueError("Circular torsion benchmark produced a null discrete torque.")
    nodal *= float(torque) / raw_torque
    model.loads.extend(
        NodalLoad(node=node, dof=dof, value=float(nodal[node, component]))
        for node in range(nodes.shape[0])
        for component, dof in ((1, "UY"), (2, "UZ"))
        if abs(nodal[node, component]) > 1.0e-18
    )
    resultant = np.sum(nodal, axis=0)
    applied = float(np.sum(nodes[:, 1] * nodal[:, 2] - nodes[:, 2] * nodal[:, 1]))
    return {
        "face_count": float(face_count),
        "resultant_torque_x": applied,
        "resultant_force_norm": float(np.linalg.norm(resultant)),
        "equilibrium_correction_norm": correction_norm,
    }


def _integrate_torsion_face(coords: np.ndarray) -> np.ndarray:
    """Integrate the unit-amplitude linear torsion traction on a T3 or T6 face."""
    node_count = int(coords.shape[0])
    if node_count not in {3, 6}:
        raise ValueError("Torsion face integration expects three or six nodes.")
    local = np.zeros((node_count, 3), dtype=float)
    for barycentric, weight in triangle_duffy_rule(5):
        shape, derivatives = triangle_shape_functions(node_count, barycentric)
        tangent_u = derivatives[:, 0] @ coords
        tangent_v = derivatives[:, 1] @ coords
        measure = float(np.linalg.norm(np.cross(tangent_u, tangent_v)))
        point = shape @ coords
        traction = np.array([0.0, -point[2], point[1]])
        local += np.outer(shape, traction) * weight * measure
    return local


def _membrane_setup(young: float, poisson: float, sigma: float, profile: str) -> dict[str, Any]:
    setup = _solid_setup(young, poisson, profile)
    setup["groups"].extend(
        [
            _fixed("x_min", 2, ["UX"]),
            _fixed("anchor_origin", 0, ["UY", "UZ"]),
            _fixed("anchor_xy", 0, ["UZ"]),
            {"name": "x_max", "dimension": 2, "actions": [{"type": "surface_traction", "value": [sigma, 0.0, 0.0]}]},
        ]
    )
    return setup


def _torsion_setup(young: float, poisson: float, profile: str) -> dict[str, Any]:
    setup = _solid_setup(young, poisson, profile)
    setup["groups"].append(_fixed("x_min", 2, ["UX", "UY", "UZ"]))
    return setup


def _solid_setup(young: float, poisson: float, profile: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": "SI"},
        "verification_profile": profile,
        "analysis": {"type": "linear_static", "method": "direct"},
        "materials": {"solid": {"type": "isotropic_3d", "E": young, "nu": poisson, "density": 7800.0}},
        "groups": [
            {
                "name": "domain",
                "dimension": 3,
                "actions": [{"type": "elements", "element_type": "TET4", "material": "solid"}],
            }
        ],
    }


def _fixed(name: str, dimension: int, dofs: list[str]) -> dict[str, Any]:
    return {"name": name, "dimension": dimension, "actions": [{"type": "fixed_dofs", "dofs": dofs}]}


def _mean_end_displacement(model: object, result: object, dof: str) -> float:
    maximum = float(np.max(model.nodes[:, 0]))
    selected = np.where(np.isclose(model.nodes[:, 0], maximum))[0]
    return float(np.mean([result.displacements[result.dofs.index(int(node), dof)] for node in selected]))


def _end_twist(model: object, result: object) -> float:
    nodes = np.asarray(model.nodes, dtype=float)
    maximum = float(np.max(nodes[:, 0]))
    selected = np.where(np.isclose(nodes[:, 0], maximum))[0]
    y = nodes[selected, 1]
    z = nodes[selected, 2]
    uy = np.asarray([result.displacements[result.dofs.index(int(node), "UY")] for node in selected])
    uz = np.asarray([result.displacements[result.dofs.index(int(node), "UZ")] for node in selected])
    return float(np.sum(y * uz - z * uy) / np.sum(y * y + z * z))


def _torsion_stress_error(model: object, result: object, torque: float, polar_moment: float) -> float:
    stresses = np.asarray([item["stress"] for item in result.to_dict()["element_results"]], dtype=float)
    centroids = np.asarray(
        [np.mean(model.nodes[np.asarray(element.nodes[:4], dtype=int)], axis=0) for element in model.elements],
        dtype=float,
    )
    reference = np.zeros_like(stresses)
    reference[:, 3] = -torque * centroids[:, 2] / polar_moment
    reference[:, 5] = torque * centroids[:, 1] / polar_moment
    return float(np.linalg.norm(stresses - reference) / max(np.linalg.norm(reference), 1.0e-30))
