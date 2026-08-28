# ruff: noqa: F401, F403, F405

"""Extended FEM arc-length robustness evidence helpers."""

from __future__ import annotations

from tempfile import TemporaryDirectory

from scipy.sparse import csr_matrix

from solveur.core.dofs import DofManager
from solveur.core.errors import NumericalConvergenceError
from solveur.core.material_state import MaterialStateTable, copy_material_states
from solveur.core.nonlinear import NonlinearStaticSolver
from solveur.core.nonlinear_contracts import NonlinearFailureReason
from solveur.verification.robustness_support import *  # noqa: F401,F403


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

__all__ = [
    "run_common_fem_snap_through_benchmark",
    "run_common_fem_snap_through_restart_benchmark",
    "run_common_fem_snap_through_failure_rollback_benchmark",
]
