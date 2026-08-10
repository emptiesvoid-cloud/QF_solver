"""Meshed solid benchmarks for TET4 and TET10."""

from __future__ import annotations

import copy
from typing import Any

import numpy as np

from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.benchmarks.support import BenchmarkContext, free_residual, lower_check, run_status, upper_check
from solveur.benchmarks.types import BenchmarkRun
from solveur.core.analysis import AnalysisSettings
from solveur.core.qualification import enforce_qualification_policy
from solveur.core.router import AnalysisRouter
from solveur.io.json_writer import JsonResultWriter


def run_tet4_patch(context: BenchmarkContext) -> BenchmarkRun:
    """Run an exact constant-stress patch on an unstructured tetrahedral cube."""
    mesh = BenchmarkMeshFactory().box_tetra(
        context.root / "patch_tet4.msh",
        length=1.0,
        width=1.0,
        height=1.0,
        mesh_size=0.42,
        anchors=True,
    )
    sigma = 12.5e6
    setup = _solid_setup("TET4", young=210.0e9, poisson=0.3)
    setup["groups"].extend(
        [
            _fixed("anchor_origin", 0, ["UX", "UY", "UZ"]),
            _fixed("anchor_x", 0, ["UY", "UZ"]),
            _fixed("anchor_xy", 0, ["UZ"]),
            _surface("x_min", "surface_traction", [-sigma, 0.0, 0.0]),
            _surface("x_max", "surface_traction", [sigma, 0.0, 0.0]),
        ]
    )
    _, result, files = context.import_and_solve(mesh, setup)
    stresses = np.asarray([row["stress"] for row in result.to_dict()["element_results"]], dtype=float)
    target = np.asarray([sigma, 0.0, 0.0, 0.0, 0.0, 0.0])
    stress_error = float(np.linalg.norm(stresses - target) / max(np.linalg.norm(np.tile(target, (len(stresses), 1))), 1.0))
    residual = free_residual(result)
    criteria = context.descriptor.criteria
    checks = [
        upper_check("constant-stress", stress_error, criteria["relative_stress_error_max"]),
        upper_check("free-residual", residual, criteria["free_residual_max"]),
    ]
    return context.finalize(
        BenchmarkRun(
            context.descriptor,
            run_status(checks),
            {
                "element_count": len(stresses),
                "target_sigma_xx": sigma,
                "mean_stress": np.mean(stresses, axis=0).tolist(),
                "relative_stress_error": stress_error,
                "free_relative_residual": residual,
            },
            checks,
            files,
        )
    )


def run_cantilever(context: BenchmarkContext) -> BenchmarkRun:
    """Compare TET4/TET10 bending and all published linear solvers."""
    factory = BenchmarkMeshFactory()
    length, width, height = 8.0, 1.0, 1.0
    young, poisson, total_force = 70.0e9, 0.3, -1000.0
    setup4 = _cantilever_setup("TET4", young, poisson, total_force, context.profile)
    setup10 = _cantilever_setup("TET10", young, poisson, total_force, context.profile)
    mesh4 = factory.box_tetra(
        context.root / "cantilever_tet4.msh",
        length=length,
        width=width,
        height=height,
        mesh_size=0.72,
    )
    mesh10 = factory.box_tetra(
        context.root / "cantilever_tet10.msh",
        length=length,
        width=width,
        height=height,
        mesh_size=0.72,
        order=2,
    )
    model4, result4, files4 = context.import_and_solve(mesh4, setup4, prefix="tet4")
    model10, result10, files10 = context.import_and_solve(mesh10, setup10, prefix="tet10")
    tip4 = _mean_tip(model4, result4, "UZ")
    tip10 = _mean_tip(model10, result10, "UZ")
    shear_modulus = young / (2.0 * (1.0 + poisson))
    inertia = width * height**3 / 12.0
    reference = total_force * length**3 / (3.0 * young * inertia) + total_force * length / (
        (5.0 / 6.0) * shear_modulus * width * height
    )
    tet10_error = abs((tip10 - reference) / reference)
    convergence, convergence_files = _tet4_h_convergence(
        context,
        factory,
        length=length,
        width=width,
        height=height,
        young=young,
        poisson=poisson,
        total_force=total_force,
        reference=reference,
    )
    method_rows, method_files = _linear_method_comparison(context, model4, result4)
    solver_difference = max(row["relative_displacement_difference"] for row in method_rows)
    criteria = context.descriptor.criteria
    checks = [
        upper_check("tet10-tip-reference", tet10_error, criteria["tet10_tip_error_max"]),
        upper_check("linear-method-agreement", solver_difference, criteria["solver_difference_max"]),
        lower_check(
            "tet4-h-observed-order",
            convergence["observed_order"],
            criteria["tet4_h_observed_order_min"],
        ),
        upper_check(
            "tet4-h-finest-error",
            convergence["finest_relative_error"],
            criteria["tet4_h_finest_error_max"],
        ),
        upper_check(
            "tet4-h-monotonicity",
            convergence["monotonicity_violation"],
            criteria["tet4_h_monotonicity_tolerance"],
        ),
        upper_check(
            "tet4-h-max-residual",
            convergence["max_free_relative_residual"],
            criteria["tet4_h_residual_max"],
        ),
        upper_check("tet4-free-residual", free_residual(result4), 1.0e-8),
        upper_check("tet10-free-residual", free_residual(result10), 1.0e-8),
    ]
    return context.finalize(
        BenchmarkRun(
            context.descriptor,
            run_status(checks),
            {
                "reference_tip_uz": reference,
                "tet4_tip_uz": tip4,
                "tet10_tip_uz": tip10,
                "tet10_relative_error": tet10_error,
                **convergence,
                "linear_methods": method_rows,
            },
            checks,
            {**files4, **files10, **convergence_files, **method_files},
        )
    )


def observed_convergence_order(mesh_sizes: object, errors: object) -> float:
    """Return the least-squares slope of log(error) versus log(mesh size)."""
    sizes = np.asarray(mesh_sizes, dtype=float)
    values = np.asarray(errors, dtype=float)
    if sizes.ndim != 1 or values.shape != sizes.shape or sizes.size < 2:
        raise ValueError("Convergence order requires matching one-dimensional arrays with at least two values.")
    if np.any(~np.isfinite(sizes)) or np.any(~np.isfinite(values)) or np.any(sizes <= 0.0) or np.any(values <= 0.0):
        raise ValueError("Mesh sizes and errors must be finite and strictly positive.")
    if np.unique(sizes).size != sizes.size:
        raise ValueError("Mesh sizes must be distinct.")
    return float(np.polyfit(np.log(sizes), np.log(values), 1)[0])


def _tet4_h_convergence(
    context: BenchmarkContext,
    factory: BenchmarkMeshFactory,
    *,
    length: float,
    width: float,
    height: float,
    young: float,
    poisson: float,
    total_force: float,
    reference: float,
) -> tuple[dict[str, Any], dict[str, str]]:
    # Keep six h-levels, but bound the engineering campaign to a mesh that can
    # be assembled on a normal workstation without a direct-factorization spike.
    sizes = (0.82, 0.68, 0.56, 0.46, 0.36, 0.26)
    rows: list[dict[str, float | int]] = []
    files: dict[str, str] = {}
    for level, mesh_size in enumerate(sizes, start=1):
        prefix = f"tet4_h{level}"
        mesh = factory.box_tetra(
            context.root / f"{prefix}.msh",
            length=length,
            width=width,
            height=height,
            mesh_size=mesh_size,
        )
        model, result, level_files = context.import_and_solve(
            mesh,
            _cantilever_setup(
                "TET4", young, poisson, total_force, context.profile, method="cg"
            ),
            prefix=prefix,
        )
        tip = _mean_tip(model, result, "UZ")
        rows.append(
            {
                "level": level,
                "mesh_size": mesh_size,
                "node_count": model.node_count,
                "element_count": len(model.elements),
                "tip_uz": tip,
                "relative_error": abs((tip - reference) / reference),
                "free_relative_residual": free_residual(result),
            }
        )
        files.update(level_files)
    errors = np.asarray([row["relative_error"] for row in rows], dtype=float)
    # Unstructured coarse meshes can oscillate before entering the asymptotic
    # regime. Acceptance therefore uses the final three refinements only.
    asymptotic_rows = rows[-3:]
    asymptotic_sizes = [float(row["mesh_size"]) for row in asymptotic_rows]
    asymptotic_errors = np.asarray(
        [row["relative_error"] for row in asymptotic_rows], dtype=float
    )
    order = observed_convergence_order(asymptotic_sizes, asymptotic_errors)
    pair_orders = np.log(errors[:-1] / errors[1:]) / np.log(np.asarray(sizes[:-1]) / np.asarray(sizes[1:]))
    return (
        {
            "tet4_h_convergence": rows,
            "tet4_h_observed_order": order,
            "tet4_h_pair_orders": pair_orders.tolist(),
            "tet4_h_finest_relative_error": float(errors[-1]),
            "observed_order": order,
            "finest_relative_error": float(errors[-1]),
            "asymptotic_levels": [int(row["level"]) for row in asymptotic_rows],
            "monotonicity_violation": float(max(np.max(np.diff(asymptotic_errors)), 0.0)),
            "max_free_relative_residual": float(max(row["free_relative_residual"] for row in rows)),
        },
        files,
    )


def run_lame(context: BenchmarkContext) -> BenchmarkRun:
    """Compare a curved TET10 quarter-cylinder against the plane-strain Lame field."""
    inner, outer, height = 4.0, 10.0, 1.0
    young, poisson, pressure = 1000.0, 0.3, 15.0
    mesh = BenchmarkMeshFactory().quarter_cylinder_tet10(
        context.root / "lame_tet10.msh",
        inner_radius=inner,
        outer_radius=outer,
        height=height,
        mesh_size=1.65,
    )
    setup = _solid_setup("TET10", young=young, poisson=poisson)
    setup["groups"].extend(
        [
            _fixed("symmetry_x", 2, ["UX"]),
            _fixed("symmetry_y", 2, ["UY"]),
            _fixed("plane_strain_z", 2, ["UZ"]),
            _surface("inner_pressure", "pressure", pressure),
        ]
    )
    model, result, files = context.import_and_solve(mesh, setup)
    translations = _translations(model, result)
    radius = np.linalg.norm(model.nodes[:, :2], axis=1)
    radial = np.sum(translations[:, :2] * model.nodes[:, :2], axis=1) / np.maximum(radius, 1.0e-30)
    exact = pressure * inner**2 * (1.0 + poisson) * (outer**2 + radius**2 * (1.0 - 2.0 * poisson)) / (
        radius * young * (outer**2 - inner**2)
    )
    displacement_error = float(np.linalg.norm(radial - exact) / np.linalg.norm(exact))
    residual = free_residual(result)
    criteria = context.descriptor.criteria
    checks = [
        upper_check("radial-displacement", displacement_error, criteria["radial_displacement_error_max"]),
        upper_check("free-residual", residual, criteria["free_residual_max"]),
    ]
    return context.finalize(
        BenchmarkRun(
            context.descriptor,
            run_status(checks, expected_warning=True),
            {
                "radial_displacement_relative_l2_error": displacement_error,
                "radial_displacement_min": float(np.min(radial)),
                "radial_displacement_max": float(np.max(radial)),
                "analytical_min": float(np.min(exact)),
                "analytical_max": float(np.max(exact)),
                "free_relative_residual": residual,
            },
            checks,
            files,
            "TET10 curved geometry is accepted only within the reviewed quality limits.",
        )
    )


def _solid_setup(family: str, *, young: float, poisson: float) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": "SI"},
        "verification_profile": "engineering",
        "analysis": {"type": "linear_static", "method": "direct"},
        "materials": {"solid": {"type": "isotropic_3d", "E": young, "nu": poisson, "density": 2700.0}},
        "groups": [
            {
                "name": "domain",
                "dimension": 3,
                "actions": [{"type": "elements", "element_type": family, "material": "solid"}],
            }
        ],
    }


def _cantilever_setup(
    family: str,
    young: float,
    poisson: float,
    force: float,
    profile: str,
    *,
    method: str = "direct",
) -> dict[str, Any]:
    setup = _solid_setup(family, young=young, poisson=poisson)
    setup["verification_profile"] = profile
    analysis: dict[str, Any] = {
        "type": "linear_static",
        "method": method,
        "rtol": 1.0e-10,
        "maxiter": 10000,
        "preconditioner": "jacobi",
    }
    if method == "cg":
        # The benchmark has positive elastic material data and a fully fixed end, so its reduced K is SPD.
        analysis["assume_spd"] = True
    setup["analysis"] = analysis
    setup["groups"].extend(
        [
            _fixed("x_min", 2, ["UX", "UY", "UZ"]),
            _surface("x_max", "surface_traction", [0.0, 0.0, force]),
        ]
    )
    return setup


def _fixed(name: str, dimension: int, dofs: list[str]) -> dict[str, Any]:
    return {"name": name, "dimension": dimension, "actions": [{"type": "fixed_dofs", "dofs": dofs}]}


def _surface(name: str, kind: str, value: object) -> dict[str, Any]:
    return {"name": name, "dimension": 2, "actions": [{"type": kind, "value": value}]}


def _mean_tip(model: object, result: object, dof: str) -> float:
    maximum = float(np.max(model.nodes[:, 0]))
    nodes = np.where(np.isclose(model.nodes[:, 0], maximum))[0]
    return float(np.mean([result.displacements[result.dofs.index(int(node), dof)] for node in nodes]))


def _translations(model: object, result: object) -> np.ndarray:
    values = np.zeros_like(model.nodes)
    for node in range(model.node_count):
        for component, dof in enumerate(("UX", "UY", "UZ")):
            values[node, component] = result.displacements[result.dofs.index(node, dof)]
    return values


def _linear_method_comparison(
    context: BenchmarkContext,
    model: object,
    direct_result: object,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    reference = np.asarray(direct_result.displacements, dtype=float)
    rows: list[dict[str, Any]] = []
    files: dict[str, str] = {}
    for method in ("direct", "cg", "gmres", "bicgstab", "minres"):
        if method == "direct":
            result = direct_result
        else:
            candidate = copy.deepcopy(model)
            preconditioner = "ilu" if method in {"gmres", "bicgstab"} else "jacobi"
            parameters: dict[str, Any] = {
                "type": "linear_static",
                "method": method,
                "rtol": 1.0e-10,
                "maxiter": 10000,
                "preconditioner": preconditioner,
            }
            if method == "cg":
                parameters["assume_spd"] = True
            candidate.analysis = AnalysisSettings.from_raw(
                parameters
            )
            result = enforce_qualification_policy(AnalysisRouter().solve(candidate), candidate)
        difference = float(np.linalg.norm(result.displacements - reference) / max(np.linalg.norm(reference), 1.0e-30))
        info = result.to_dict()["solver"]
        rows.append(
            {
                "method": method,
                "iterations": int(info.get("iterations", 0)),
                "residual_norm": float(info.get("residual_norm", 0.0)),
                "relative_displacement_difference": difference,
            }
        )
        path = context.root / f"linear_method_{method}.json"
        JsonResultWriter().write(result, path)
        files[f"linear_method_{method}"] = path.name
    return rows, files
