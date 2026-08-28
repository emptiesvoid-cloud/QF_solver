# ruff: noqa: F401, F403, F405

"""Implementation group for the nonlinear robustness campaign: robustness_arc_length."""

from __future__ import annotations

from tempfile import TemporaryDirectory

from scipy.sparse import csr_matrix

from solveur.core.dofs import DofManager
from solveur.core.errors import NumericalConvergenceError
from solveur.core.material_state import MaterialStateTable, copy_material_states
from solveur.core.nonlinear import NonlinearStaticSolver
from solveur.core.nonlinear_contracts import NonlinearFailureReason
from solveur.verification.robustness_support import *  # noqa: F401,F403
from solveur.verification.robustness_mesh import _multi_element_model
from solveur.verification.robustness_arc_length_extended import (
    _common_fem_snap_through_model,
    run_common_fem_snap_through_benchmark,
    run_common_fem_snap_through_failure_rollback_benchmark,
    run_common_fem_snap_through_restart_benchmark,
)



def run_arc_length_benchmark() -> dict[str, Any]:
    """Exercise the sparse arc-length continuation path and compare endpoint data."""

    def model_for(method: str) -> FiniteElementModel:
        return FiniteElementModel.from_raw(
            nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
            elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "rubber"}],
            materials={"rubber": {"type": "nonlinear_isotropic_3d", "E": 1000.0, "nu": 0.25, "hardening": 1.0e6}},
            fixed_dofs=[
                {"node": 0, "dofs": ["UX", "UY", "UZ"]},
                {"node": 2, "dofs": ["UX", "UY", "UZ"]},
                {"node": 3, "dofs": ["UX", "UY", "UZ"]},
            ],
            loads=[{"node": 1, "dof": "UX", "value": 10.0}],
            analysis={
                "type": "nonlinear_static",
                "method": method,
                "load_steps": 5,
                "max_iterations": 50,
                "tolerance": 1.0e-9,
                "max_arc_steps": 12,
                "target_load_factor": 1.0,
            },
        )

    arc_model = model_for("arc_length")
    arc_result = solve_model(arc_model, enforce_policy=False)

    reference = solve_model(model_for("newton_raphson"), enforce_policy=False)
    arc_data = arc_result.to_dict()
    steps = arc_data["solver"]["steps"]
    factors = [float(step["load_factor"]) for step in steps]
    residuals = [float(step["relative_residual"]) for step in steps]
    displacement_error = float(
        np.linalg.norm(arc_result.displacements - reference.displacements)
        / max(np.linalg.norm(reference.displacements), 1.0e-15)
    )
    monotone = all(next_factor >= factor - 1.0e-12 for factor, next_factor in zip(factors, factors[1:]))
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if arc_result.status == "PASS" and factors and monotone and np.all(np.isfinite(residuals))
        else "FAIL",
        "method": arc_result.method,
        "load_factors": factors,
        "target_load_factor": 1.0,
        "reached_target": bool(factors and abs(factors[-1] - 1.0) <= 1.0e-3),
        "monotone_load_factor": monotone,
        "step_count": len(steps),
        "maximum_relative_residual": max(residuals, default=float("inf")),
        "residual_histories": [list(map(float, step.get("residual_history", []))) for step in steps],
        "endpoint_displacement_relative_error": displacement_error,
        "owner_acceptance_band_required": True,
        "limitations": [
            "The model is a proportional small-strain nonlinear material path without a snap-through limit point.",
            "This is continuation-path evidence, not a post-buckling or external-validation claim.",
        ],
    }


def run_fem_arc_length_benchmark() -> dict[str, Any]:
    """Record the existing sparse FEM arc-length path as bounded evidence."""

    length = 2.0
    nodes, elements = _structured_tet4_mesh(4, 1, 1, length, 0.5, 0.5)
    nodes[:, 2] += 0.005 * (1.0 - np.cos(0.5 * np.pi * nodes[:, 0] / length))
    assembly = TotalLagrangianTet4Assembly(
        nodes,
        elements,
        SolidMaterial(E=1.0e6, nu=0.3),
    )
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    tip_nodes = np.flatnonzero(np.isclose(nodes[:, 0], length))
    fixed = (3 * fixed_nodes[:, None] + np.arange(3)).reshape(-1)
    reference_load = np.zeros(assembly.ndof, dtype=float)
    reference_load[3 * tip_nodes] = -100.0 / tip_nodes.size
    displacement, history = trace_sparse_arc_length(
        assembly,
        reference_load,
        fixed,
        tip_nodes,
        steps=24,
        initial_load_increment=0.02,
        tolerance=1.0e-8,
    )
    factors = [float(point.load_factor) for point in history]
    residuals = [float(point.relative_residual) for point in history]
    minimum_det_f = min((float(point.minimum_det_f) for point in history), default=float("nan"))
    factor_differences = np.diff(factors)
    turn_count = int(np.count_nonzero((factor_differences[:-1] > 0.0) & (factor_differences[1:] < 0.0)))
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if len(history) == 24
        and factors
        and np.all(np.isfinite(displacement))
        and np.all(np.isfinite(residuals))
        and max(residuals) < 1.0e-7
        and minimum_det_f > 0.99
        else "FAIL",
        "method": "trace_sparse_arc_length",
        "node_count": int(nodes.shape[0]),
        "element_count": int(len(elements)),
        "dof_count": int(assembly.ndof),
        "step_count": len(history),
        "load_factor_range": [min(factors), max(factors)] if factors else [],
        "load_factor_turn_count": turn_count,
        "maximum_relative_residual": max(residuals, default=float("inf")),
        "minimum_det_f": minimum_det_f,
        "final_tip_axial_displacement": float(history[-1].tip_axial_displacement) if history else None,
        "final_tip_lateral_displacement": float(history[-1].tip_lateral_displacement) if history else None,
        "residual_history": residuals,
        "owner_acceptance_band_required": True,
        "limitations": [
            "Existing TET4 total-Lagrangian FEM path, separate from the common nonlinear driver.",
            "This case remains monotone over the bounded window and does not demonstrate a snap-through limit point.",
            "No material plasticity, contact, external correlation or production qualification is claimed.",
        ],
    }


def run_finite_kinematic_arc_length_benchmark(
    element_types: tuple[str, ...] = ELEMENT_TYPES,
) -> dict[str, Any]:
    """Exercise adaptive arc-length on homogeneous J2 solid families."""

    rows: list[dict[str, Any]] = []
    for family in element_types:
        if family not in ELEMENT_TYPES:
            raise ValueError("Finite-kinematic arc-length supports TET4, TET10, HEX8 and HEX20.")
        model = _multi_element_model(family)
        parameters = dict(model.analysis.parameters)
        parameters.pop("load_path", None)
        parameters.update(
            {
                "kinematics": "total_lagrangian_j2",
                "target_load_factor": 0.5,
                "max_arc_steps": 256,
                "arc_length_stop_mode": "target_load",
                "adaptive_arc_length": True,
                "arc_length_growth_factor": 1.5,
                "arc_length_shrink_factor": 0.5,
                "max_arc_length_radius": 0.1,
                "max_iterations": 60,
                "tolerance": 1.0e-7,
            }
        )
        model.analysis = replace(model.analysis, method="arc_length", parameters=parameters)
        result = solve_model(model, enforce_policy=False)
        solver = result.to_dict()["solver"]
        steps = solver["steps"]
        final_factor = float(steps[-1]["load_factor"])
        maximum_relative_residual = float(max(step["relative_residual"] for step in steps))
        final_peeq = float(steps[-1]["equivalent_plastic_strain_max"])
        load_factors = [float(step["load_factor"]) for step in steps]
        radius_history = [
            float(step["arc_length_radius"])
            for step in steps
            if step.get("arc_length_radius") is not None
        ]
        rows.append(
            {
                "element": family,
                "status": (
                    "PASS"
                    if result.status == "PASS"
                    and final_factor >= 0.5 - 1.0e-6
                    and maximum_relative_residual < 1.0e-7
                    and np.isfinite(final_peeq)
                    else "FAIL"
                ),
                "solver_status": result.status,
                "load_factor": load_factors,
                "load_factor_range": [min(load_factors), max(load_factors)],
                "radius_history": radius_history,
                "radius_range": [min(radius_history), max(radius_history)] if radius_history else [],
                "step_count": len(steps),
                "final_load_factor": final_factor,
                "maximum_relative_residual": maximum_relative_residual,
                "final_peeq": final_peeq,
                "adaptive_arc_length": bool(solver["adaptive_arc_length"]),
                "maximum_radius": float(parameters["max_arc_length_radius"]),
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL",
        "method": "arc_length",
        "kinematics": "total_lagrangian_j2",
        "elements": [row["element"] for row in rows],
        "target_load_factor": 0.5,
        "load_factor": rows[0]["load_factor"] if len(rows) == 1 else [],
        "load_factor_ranges": {row["element"]: row["load_factor_range"] for row in rows},
        "radius_ranges": {row["element"]: row["radius_range"] for row in rows},
        "step_count": max((row["step_count"] for row in rows), default=0),
        "final_load_factor": min((row["final_load_factor"] for row in rows), default=float("nan")),
        "maximum_relative_residual": max(
            (row["maximum_relative_residual"] for row in rows), default=float("inf")
        ),
        "final_peeq": max((row["final_peeq"] for row in rows), default=float("nan")),
        "rows": rows,
        "owner_acceptance_band_required": True,
        "limitations": [
            "Bounded monotone adaptive paths for TET4, TET10, HEX8 and HEX20 to load factor 0.5.",
            "This is an internal research proof; no snap-through, snap-back, post-buckling or external correlation is claimed.",
            "The load path is a plastic J2 path, but it is not a physical validation or release qualification.",
        ],
    }


def run_shallow_arch_arc_length_benchmark(
    *,
    steps: int = 80,
    radius: float = 0.05,
    max_iterations: int = 40,
) -> dict[str, Any]:
    """Verify branch following on a reduced shallow-arch equilibrium path.

    The reduced equilibrium equation is ``lambda = u - u**3``.  It has an
    analytically known limit point, so it is useful for testing the
    continuation algebra independently of a particular finite-element
    formulation.  This is algorithmic verification only: it is not a claim
    about a shell or solid shallow-arch discretisation.
    """

    if steps < 4 or max_iterations < 1 or radius <= 0.0:
        raise ValueError("The shallow-arch benchmark requires positive steps, radius and iterations.")
    stiffness = 1.0
    softening = 1.0
    reference_load = 1.0
    load_scale = 1.0
    u = 0.0
    load_factor = 0.0
    previous_du = 0.0
    previous_dlambda = 0.0
    rows: list[dict[str, Any]] = []

    def internal(value: float) -> float:
        return stiffness * value - softening * value**3

    def tangent(value: float) -> float:
        return stiffness - 3.0 * softening * value**2

    for step in range(1, steps + 1):
        base_u = u
        base_lambda = load_factor
        base_tangent = tangent(base_u)
        if abs(base_tangent) > 1.0e-8:
            du_per_lambda = reference_load / base_tangent
        else:
            du_per_lambda = previous_du / previous_dlambda if abs(previous_dlambda) > 1.0e-12 else 0.0
        direction = 1.0
        if previous_dlambda or previous_du:
            direction = 1.0 if du_per_lambda * previous_du + load_scale**2 * previous_dlambda >= 0.0 else -1.0
        delta_lambda = direction * radius / np.sqrt(du_per_lambda**2 + load_scale**2)
        trial_u = base_u + delta_lambda * du_per_lambda
        trial_lambda = base_lambda + delta_lambda
        residual_history: list[float] = []
        converged = False
        relative = float("inf")
        for iteration in range(1, max_iterations + 1):
            residual = reference_load * trial_lambda - internal(trial_u)
            delta_u = trial_u - base_u
            delta_load = trial_lambda - base_lambda
            constraint = delta_u**2 + (load_scale * delta_load) ** 2 - radius**2
            relative = max(abs(residual) / max(abs(reference_load), 1.0), abs(constraint) / radius**2)
            residual_history.append(abs(residual))
            if relative <= 1.0e-10:
                converged = True
                break
            matrix = np.asarray(
                [
                    [tangent(trial_u), -reference_load],
                    [2.0 * delta_u, 2.0 * load_scale**2 * delta_load],
                ],
                dtype=float,
            )
            try:
                correction_u, correction_lambda = np.linalg.solve(
                    matrix, np.asarray([residual, -constraint], dtype=float)
                )
            except np.linalg.LinAlgError as exc:
                raise NumericalConvergenceError(
                    "Reduced shallow-arch arc-length system is singular.",
                    reason="ARC_LENGTH_FAILURE",
                    diagnostics={"step": step, "iteration": iteration},
                ) from exc
            if not np.isfinite(correction_u) or not np.isfinite(correction_lambda):
                raise NumericalConvergenceError(
                    "Reduced shallow-arch arc-length correction is non-finite.",
                    reason="ARC_LENGTH_FAILURE",
                )
            trial_u += float(correction_u)
            trial_lambda += float(correction_lambda)
        if not converged:
            raise NumericalConvergenceError(
                f"Reduced shallow-arch step {step} did not converge.",
                reason="ARC_LENGTH_FAILURE",
                diagnostics={"step": step, "residual_history": residual_history},
            )
        u = float(trial_u)
        load_factor = float(trial_lambda)
        previous_du = u - base_u
        previous_dlambda = load_factor - base_lambda
        rows.append(
            {
                "step": step,
                "displacement": u,
                "load_factor": load_factor,
                "exact_load_factor": internal(u),
                "equilibrium_error": abs(load_factor - internal(u)),
                "iterations": iteration,
                "relative_residual": relative,
                "residual_history": residual_history,
                "tangent": tangent(u),
            }
        )

    factors = [float(row["load_factor"]) for row in rows]
    differences = np.diff(factors)
    limit_point_u = float(np.sqrt(stiffness / (3.0 * softening)))
    limit_point_lambda = float(internal(limit_point_u))
    turn_indices = np.flatnonzero((differences[:-1] > 0.0) & (differences[1:] < 0.0))
    max_equilibrium_error = max(float(row["equilibrium_error"]) for row in rows)
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if rows and turn_indices.size and max_equilibrium_error < 1.0e-8
        else "FAIL",
        "method": "sparse_arc_length_algebra_reduced_order",
        "steps": rows,
        "step_count": len(rows),
        "radius": radius,
        "max_iterations": max_iterations,
        "limit_point_reference": {
            "displacement": limit_point_u,
            "load_factor": limit_point_lambda,
        },
        "limit_point_observed": bool(turn_indices.size),
        "limit_point_step": int(turn_indices[0] + 2) if turn_indices.size else None,
        "maximum_equilibrium_error": max_equilibrium_error,
        "load_factor_range": [min(factors), max(factors)] if factors else [],
        "branch_turn_count": int(turn_indices.size),
        "owner_acceptance_band_required": True,
        "limitations": [
            "Reduced scalar equilibrium equation; no FEM shallow-arch claim.",
            "Internal algorithmic verification only; no external solver correlation.",
            "The result does not qualify snap-through of a production element formulation.",
        ],
    }


__all__ = [name for name in globals() if not name.startswith("__")]
