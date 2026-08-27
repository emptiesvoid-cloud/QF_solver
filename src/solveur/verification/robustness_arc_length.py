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


def _common_fem_snap_through_model(
    *,
    radius: float = 0.02,
    max_arc_steps: int = 80,
    checkpoint_path: str | None = None,
    restart_from: str | None = None,
    checkpoint_keep_steps: bool = False,
) -> FiniteElementModel:
    """Build the small 3D TET4 snap-through model used by the common driver.

    The two tetrahedra share the crown face and form a minimal volumetric
    shallow arch.  The model is intentionally small enough for unit-level
    branch and restart checks, while still exercising global sparse assembly,
    finite kinematics and the production nonlinear driver.
    """

    nodes = np.asarray(
        [
            [-1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, -0.05, 0.20],
            [0.0, 0.05, 0.20],
            [0.0, 0.00, 0.25],
        ],
        dtype=float,
    )
    elements = [[0, 2, 3, 4], [1, 3, 2, 4]]
    fixed_dofs = [
        {"node": 0, "dofs": ["UX", "UY", "UZ"]},
        {"node": 1, "dofs": ["UX", "UY", "UZ"]},
        *[{"node": node, "dofs": ["UY"]} for node in (2, 3, 4)],
    ]
    loads = [{"node": node, "dof": "UZ", "value": 1.0 / 3.0} for node in (2, 3, 4)]
    parameters: dict[str, object] = {
        "type": "nonlinear_static",
        "method": "arc_length",
        "kinematics": "total_lagrangian",
        "target_load_factor": -1.0,
        "max_iterations": 80,
        "tolerance": 1.0e-8,
        "max_arc_steps": max_arc_steps,
        "arc_length_stop_mode": "max_steps",
        "arc_length_allow_load_factor_turning": True,
        "arc_length_load_factor_limit": 5.0,
        "arc_length_radius": radius,
        "max_arc_length_radius": radius,
        "min_arc_length_radius": radius * 1.0e-4,
        "adaptive_arc_length": False,
        "arc_length_load_scale": 1.0,
        "arc_length_control_dof": 14,
    }
    if checkpoint_path is not None:
        parameters.update(
            {
                "checkpoint_path": checkpoint_path,
                "checkpoint_interval": 1,
                "checkpoint_keep_steps": checkpoint_keep_steps,
            }
        )
    if restart_from is not None:
        parameters["restart_from"] = restart_from
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "TET4", "nodes": item, "material": "solid"} for item in elements],
        materials={"solid": {"type": "isotropic_3d", "E": 100.0, "nu": 0.3}},
        fixed_dofs=fixed_dofs,
        loads=loads,
        analysis=parameters,
    )


def run_common_fem_snap_through_benchmark(
    *,
    radius: float = 0.02,
    max_arc_steps: int = 80,
) -> dict[str, Any]:
    """Exercise a true FEM snap-through branch through the common driver.

    This is controlled internal evidence for G04 implementation work.  It
    records the signed load-factor path, displacement control quantity,
    predictor/branch diagnostics and residual histories, but does not claim
    external correlation or close the release gate.
    """

    model = _common_fem_snap_through_model(radius=radius, max_arc_steps=max_arc_steps)
    result = solve_model(model, enforce_policy=False)
    solver = result.to_dict()["solver"]
    steps = list(solver["steps"])
    factors = np.asarray([float(step["load_factor"]) for step in steps], dtype=float)
    control_displacements = np.asarray(
        [float(step["arc_length_control_displacement"]) for step in steps],
        dtype=float,
    )
    factor_increments = np.diff(factors)
    direction_changes = np.flatnonzero(
        (factor_increments[:-1] * factor_increments[1:]) < -1.0e-14
    )
    finite_residuals = all(
        np.all(np.isfinite(np.asarray(step.get("residual_history", []), dtype=float))) for step in steps
    )
    minimum_det_f = min(
        (
            float(point["det_f"])
            for row in result.element_results
            for point in row.get("integration_points", [])
            if point.get("det_f") is not None
        ),
        default=float("nan"),
    )
    maximum_relative_residual = max(
        (float(step["relative_residual"]) for step in steps),
        default=float("inf"),
    )
    turning_index = int(direction_changes[0] + 1) if direction_changes.size else None
    status = (
        "PASS_INTERNAL_RESEARCH"
        if result.status == "PASS"
        and len(steps) == max_arc_steps
        and direction_changes.size > 0
        and np.all(np.isfinite(factors))
        and np.all(np.isfinite(control_displacements))
        and finite_residuals
        and maximum_relative_residual < 1.0e-7
        and np.isfinite(minimum_det_f)
        and minimum_det_f > 0.0
        else "FAIL"
    )
    return {
        "status": status,
        "method": "arc_length",
        "kinematics": "total_lagrangian",
        "common_driver": True,
        "element_family": "TET4",
        "node_count": int(model.node_count),
        "element_count": int(len(model.elements)),
        "dof_count": int(result.displacements.size),
        "step_count": len(steps),
        "load_factors": factors.tolist(),
        "load_factor_increments": factor_increments.tolist(),
        "control_dof": 14,
        "control_displacements": control_displacements.tolist(),
        "predictor_signs": [step.get("arc_length_predictor_sign") for step in steps],
        "branch_directions": [step.get("arc_length_branch_direction") for step in steps],
        "direction_alignments": [step.get("arc_length_direction_alignment") for step in steps],
        "radius_history": [float(step["arc_length_radius"]) for step in steps],
        "residual_histories": [list(map(float, step.get("residual_history", []))) for step in steps],
        "newton_iterations": [int(step["iterations"]) for step in steps],
        "load_factor_range": [float(factors.min()), float(factors.max())] if factors.size else [],
        "control_displacement_range": (
            [float(control_displacements.min()), float(control_displacements.max())]
            if control_displacements.size
            else []
        ),
        "branch_turn_count": int(direction_changes.size),
        "turning_point_step": turning_index,
        "turning_point_load_factor": float(factors[turning_index]) if turning_index is not None else None,
        "maximum_relative_residual": maximum_relative_residual,
        "minimum_det_f": minimum_det_f,
        "rejected_increments": int(solver.get("rejected_increments", 0)),
        "rejection_log": solver.get("rejection_log", []),
        "owner_acceptance_band_required": True,
        "limitations": [
            "Minimal two-element TET4 volumetric snap-through model for internal branch verification.",
            "Internal common-driver evidence only; no Code_Aster, CalculiX or physical validation claim.",
            "The benchmark does not close 025-G04 until mesh and external evidence are attached.",
        ],
    }


def run_common_fem_snap_through_restart_benchmark(
    *,
    radius: float = 0.02,
    max_arc_steps: int = 80,
    restart_position: str = "before_turn",
) -> dict[str, Any]:
    """Verify restart and continuation-state fidelity across the limit point."""

    if restart_position not in {"before_turn", "after_turn"}:
        raise ValueError("restart_position must be 'before_turn' or 'after_turn'.")

    with TemporaryDirectory(prefix="qf_solver_arc_length_") as temporary_directory:
        root = Path(temporary_directory)
        continuous_model = _common_fem_snap_through_model(
            radius=radius,
            max_arc_steps=max_arc_steps,
            checkpoint_path=str(root / "continuous.npz"),
            checkpoint_keep_steps=True,
        )
        continuous = solve_model(continuous_model, enforce_policy=False)
        continuous_steps = list(continuous.to_dict()["solver"]["steps"])
        continuous_factors = np.asarray(
            [float(step["load_factor"]) for step in continuous_steps],
            dtype=float,
        )
        increments = np.diff(continuous_factors)
        changes = np.flatnonzero((increments[:-1] * increments[1:]) < -1.0e-14)
        checkpoint_offset = 1 if restart_position == "before_turn" else 2
        checkpoint_step = int(changes[0] + checkpoint_offset) if changes.size else 0
        checkpoint = root / f"continuous.step{checkpoint_step:08d}.npz"
        if checkpoint_step <= 0 or not checkpoint.is_file():
            return {
                "status": "FAIL",
                "reason": "No checkpoint was available immediately before the observed turning point.",
                "checkpoint_step": checkpoint_step,
            }
        restarted_model = _common_fem_snap_through_model(
            radius=radius,
            max_arc_steps=max_arc_steps,
            checkpoint_path=str(root / "restarted.npz"),
            restart_from=str(checkpoint),
        )
        resumed = solve_model(restarted_model, enforce_policy=False)
        resumed_steps = list(resumed.to_dict()["solver"]["steps"])
        resumed_factors = np.asarray(
            [float(step["load_factor"]) for step in resumed_steps],
            dtype=float,
        )
        expected_suffix = continuous_factors[checkpoint_step:]
        factor_error = float(
            np.max(np.abs(resumed_factors - expected_suffix))
            if resumed_factors.size and resumed_factors.shape == expected_suffix.shape
            else float("inf")
        )
        displacement_error = float(
            np.linalg.norm(resumed.displacements - continuous.displacements)
            / max(float(np.linalg.norm(continuous.displacements)), 1.0e-15)
        )
        material_state_match = resumed.material_states == continuous.material_states
        passed = (
            continuous.status == "PASS"
            and resumed.status == "PASS"
            and resumed.solver["restart_step"] == checkpoint_step
            and resumed.solver["history_is_partial"] is True
            and factor_error <= 1.0e-14
            and displacement_error <= 1.0e-14
            and material_state_match
        )
        return {
            "status": "PASS_INTERNAL_RESEARCH" if passed else "FAIL",
            "method": "arc_length",
            "common_driver": True,
            "restart_position": restart_position,
            "checkpoint_step": checkpoint_step,
            "turning_point_crossed_after_restart": bool(changes.size),
            "continuous_step_count": len(continuous_steps),
            "resumed_step_count": len(resumed_steps),
            "resumed_restart_step": int(resumed.solver["restart_step"]),
            "suffix_load_factor_max_error": factor_error,
            "final_displacement_relative_error": displacement_error,
            "material_state_match": material_state_match,
            "rollback_contract": "checkpoint restores committed state before continuation retry",
            "limitations": [
                "Restart evidence uses the same controlled minimal TET4 snap-through model.",
                "This is internal restart/branch evidence and does not close 025-G04.",
            ],
        }


def run_common_fem_snap_through_failure_rollback_benchmark(
    *,
    radius: float = 0.02,
    max_arc_steps: int = 80,
    failure_step: int = 76,
) -> dict[str, Any]:
    """Exercise rollback/retry after Newton corrections near the turning point."""

    if failure_step < 2 or failure_step > max_arc_steps:
        raise ValueError("failure_step must identify an interior arc-length step.")

    class FailingArcLengthSolver(NonlinearStaticSolver):
        """Inject one post-correction failure without changing production code paths."""

        def __init__(self) -> None:
            super().__init__()
            self.active_step: int | None = None
            self.assembly_calls = 0
            self.failed = False
            self.retry_clean = False
            self.before_failure_displacement: np.ndarray | None = None
            self.before_failure_states: MaterialStateTable | None = None

        def _solve_arc_length_step(self, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
            step = int(args[6])
            displacement = np.asarray(args[2], dtype=float)
            material_states = args[5]
            if step == failure_step:
                if not self.failed:
                    self.assembly_calls = 0
                    self.before_failure_displacement = displacement.copy()
                    self.before_failure_states = copy_material_states(material_states)  # type: ignore[arg-type]
                elif not self.retry_clean:
                    self.retry_clean = bool(
                        self.before_failure_displacement is not None
                        and np.array_equal(displacement, self.before_failure_displacement)
                        and self.before_failure_states == material_states
                    )
            self.active_step = step
            try:
                return super()._solve_arc_length_step(*args, **kwargs)
            finally:
                self.active_step = None

        def _assemble_internal_tangent(
            self,
            model: FiniteElementModel,
            dofs: DofManager,
            displacement: np.ndarray,
            material_states: MaterialStateTable | None = None,
            *,
            contact_diagnostics: dict[str, object] | None = None,
            timing: dict[str, float | int] | None = None,
        ) -> tuple[np.ndarray, csr_matrix, MaterialStateTable]:
            if self.active_step == failure_step:
                self.assembly_calls += 1
                if not self.failed and self.assembly_calls == 4:
                    displacement[:] = 789.0
                    self.failed = True
                    raise NumericalConvergenceError(
                        "controlled failure after two Newton corrections near the turning point",
                        reason=NonlinearFailureReason.MAX_ITERATIONS,
                        diagnostics={
                            "failure_step": failure_step,
                            "corrections_completed": 2,
                            "near_turning_point": True,
                        },
                    )
            return super()._assemble_internal_tangent(
                model,
                dofs,
                displacement,
                material_states,
                contact_diagnostics=contact_diagnostics,
                timing=timing,
            )

    solver = FailingArcLengthSolver()
    model = _common_fem_snap_through_model(radius=radius, max_arc_steps=max_arc_steps)
    result = solver.solve(model)
    data = result.to_dict()
    solver_data = data["solver"]
    rejection_log = list(solver_data.get("rejection_log", []))
    steps = list(solver_data.get("steps", []))
    factors = np.asarray([float(step["load_factor"]) for step in steps], dtype=float)
    control_displacements = np.asarray(
        [float(step["arc_length_control_displacement"]) for step in steps],
        dtype=float,
    )
    branch_directions = [step.get("arc_length_branch_direction") for step in steps]
    rejection = rejection_log[0] if rejection_log else {}
    passed = (
        result.status == "PASS"
        and solver.failed
        and solver.retry_clean
        and len(steps) == max_arc_steps
        and len(rejection_log) == 1
        and rejection.get("step") == failure_step
        and rejection.get("rollback_before_retry") is True
        and rejection.get("failure_reason") == NonlinearFailureReason.MAX_ITERATIONS.value
        and np.all(np.isfinite(factors))
        and np.all(np.isfinite(control_displacements))
        and np.all(np.diff(control_displacements) < 0.0)
        and all(direction == 1 for direction in branch_directions[1:])
    )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if passed else "FAIL",
        "method": "arc_length",
        "common_driver": True,
        "failure_step": failure_step,
        "near_turning_point": True,
        "corrections_completed": 2,
        "retry_clean": solver.retry_clean,
        "step_count": len(steps),
        "control_displacement_range": (
            [float(control_displacements.min()), float(control_displacements.max())]
            if control_displacements.size
            else []
        ),
        "branch_directions_after_initial_step": branch_directions[1:],
        "rejected_increments": int(solver_data.get("rejected_increments", 0)),
        "rejection_log": rejection_log,
        "base_load_factor": rejection.get("base_load_factor"),
        "final_load_factor": float(factors[-1]) if factors.size else None,
        "limitations": [
            "Controlled internal failure injection on the minimal two-element TET4 model.",
            "The result verifies transaction behavior and does not close 025-G04.",
        ],
    }


__all__ = [name for name in globals() if not name.startswith("__")]
