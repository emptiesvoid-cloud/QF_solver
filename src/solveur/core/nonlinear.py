"""Nonlinear static solver."""

from __future__ import annotations

from dataclasses import replace
from time import perf_counter

import numpy as np
from scipy.sparse import csr_matrix

from solveur.core.assembler import GlobalAssembler
from solveur.core.audit import SolverAudit, static_equilibrium_summary
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError, MeshValidationError, NumericalConvergenceError
from solveur.core.linear_methods import LinearSystemSolver
from solveur.core.material_state import MaterialStateSession, MaterialStateTable, commit_material_states
from solveur.core.material_state import copy_material_states
from solveur.core.material_state import initial_material_states
from solveur.core.nonlinear_contracts import NonlinearFailureReason
from solveur.core.nonlinear_assembly import (
    NonlinearAssemblyPlan,
    assemble_internal_tangent,
    build_nonlinear_assembly_plan,
)
from solveur.core.nonlinear_iteration import line_search_factor, solve_arc_length_correction
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear_controls import (
    AdaptiveLoadControls,
    ArcLengthControls,
    NonlinearStep,
    NonlinearSolverOptions,
    incremental_work_diagnostics,
    maximum_equivalent_plastic_strain,
    maximum_plastic_dissipation,
    validated_load_path,
)
from solveur.core.nonlinear_checkpoint import NonlinearCheckpointSession, NonlinearCheckpointStore
from solveur.core.results import SolveResult
from solveur.mesh.validation import MeshValidator
from solveur.post.audit import PostProcessingAuditor
from solveur.post.stress import StressPostProcessor


class NonlinearStaticSolver:
    """Common load-control Newton driver for supported nonlinear solid elements."""

    supported_methods = ("newton_raphson", "modified_newton", "newton_line_search", "arc_length")

    def __init__(self, checkpoint_store: NonlinearCheckpointStore | None = None) -> None:
        self.validator = MeshValidator()
        self.assembler = GlobalAssembler()
        self.linear_solver = LinearSystemSolver()
        self.post = StressPostProcessor()
        self.post_auditor = PostProcessingAuditor()
        self.checkpoint_store = checkpoint_store
        self._assembly_plan: NonlinearAssemblyPlan | None = None

    def solve(self, model: FiniteElementModel) -> SolveResult:
        if model.analysis.method not in self.supported_methods:
            raise InputValidationError(f"Unsupported nonlinear method {model.analysis.method!r}.")

        self._assembly_plan = None
        report = self.validator.validate(model)
        if report.status == "FAIL":
            raise MeshValidationError("Mesh validation failed: " + "; ".join(report.errors))
        dofs = model.dof_manager()
        loads = self.assembler.assemble_loads(model, dofs)
        fixed = self.assembler.fixed_indices(model, dofs)
        free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
        if free.size == 0:
            raise MeshValidationError("No free degree of freedom remains after boundary conditions.")

        params = model.analysis.parameters
        self._validate_kinematics_scope(model, params)
        self._assembly_plan = build_nonlinear_assembly_plan(model, dofs)
        options = NonlinearSolverOptions.from_parameters(params)
        load_steps = options.load_steps
        max_iterations = options.max_iterations
        tolerance = options.tolerance
        linear_method = options.linear_method
        min_alpha = options.line_search_min_alpha
        max_reductions = options.line_search_max_reductions
        armijo = options.line_search_c
        adaptive = options.adaptive_load_steps
        load_path = validated_load_path(params, load_steps)
        if load_path is not None and adaptive:
            raise InputValidationError("analysis.load_path is not yet compatible with adaptive_load_steps.")
        if load_path is not None and model.analysis.method == "arc_length":
            raise InputValidationError("analysis.load_path is not compatible with arc_length.")
        checkpoint_requested = any(key in params for key in ("checkpoint_path", "restart_from"))
        if checkpoint_requested and adaptive:
            raise InputValidationError("Nonlinear checkpoint/restart currently requires fixed load-control steps.")
        self._rejected_increments = 0
        self._rejection_log: list[dict[str, object]] = []
        reference_force_norm = max(float(np.linalg.norm(loads[free])), 1.0)
        arc_length_controls = (
            ArcLengthControls.from_parameters(params, max_iterations=max_iterations)
            if model.analysis.method == "arc_length"
            else None
        )

        displacement = np.zeros(dofs.ndof, dtype=float)
        material_states = initial_material_states(model)
        checkpoint_session: NonlinearCheckpointSession | None = None
        completed_factors: list[float] = []
        if model.analysis.method == "arc_length":
            checkpoint_session = NonlinearCheckpointSession.create(
                model,
                max(1, int(params.get("max_arc_steps", max(load_steps * 4, load_steps + 1)))),
                self.checkpoint_store,
            )
            displacement, material_states, continuation_state = checkpoint_session.restore_continuation(
                displacement,
                material_states,
                float(params.get("target_load_factor", 1.0)),
                float(
                    params.get(
                        "arc_length_load_factor_limit",
                        max(abs(float(params.get("target_load_factor", 1.0))), 1.0),
                    )
                ),
            )
            history = self._solve_arc_length(
                model,
                dofs,
                displacement,
                free,
                loads,
                material_states,
                load_steps,
                max_iterations,
                tolerance,
                linear_method,
                checkpoint_session,
                continuation_state,
                arc_length_controls,
            )
        elif adaptive:
            history = self._solve_adaptive_load_steps(
                model,
                dofs,
                displacement,
                free,
                loads,
                material_states,
                load_steps,
                max_iterations,
                tolerance,
                linear_method,
                min_alpha,
                max_reductions,
                armijo,
            )
        else:
            history = []
            factors = load_path or [step / load_steps for step in range(1, load_steps + 1)]
            checkpoint_session = NonlinearCheckpointSession.create(model, len(factors), self.checkpoint_store)
            displacement, material_states = checkpoint_session.restore(displacement, material_states, factors)
            previous_factor = 0.0 if checkpoint_session.restart_step == 0 else factors[checkpoint_session.restart_step - 1]
            for step, load_factor in enumerate(
                factors[checkpoint_session.restart_step :], start=checkpoint_session.restart_step + 1
            ):
                target_load = load_factor * loads
                cached_tangent: csr_matrix | None = None
                history.append(
                    self._solve_load_step(
                        model,
                        dofs,
                        displacement,
                        free,
                        target_load,
                        material_states,
                        step,
                        load_factor,
                        load_factor - previous_factor,
                        cached_tangent,
                        max_iterations,
                        tolerance,
                        linear_method,
                        min_alpha,
                        max_reductions,
                        armijo,
                        previous_factor * loads,
                        reference_force_norm,
                    )
                )
                previous_factor = load_factor
                checkpoint_session.save(step, load_factor, displacement, material_states)
            completed_factors = list(factors)

        element_results = self.post.element_results(model, dofs, displacement, material_states)
        nodal_results = self.post.nodal_results(model, element_results)
        post_results = self.post_auditor.element_audits(model, dofs, displacement, element_results)
        internal, tangent, _ = self._assemble_internal_tangent(model, dofs, displacement, material_states)
        load_factor = completed_factors[-1] if completed_factors else (history[-1].load_factor if history else 1.0)
        external = load_factor * loads
        residual = internal - external
        reactions = np.zeros_like(residual)
        reactions[fixed] = residual[fixed]
        audit = SolverAudit.from_state(
            model=model,
            dofs=dofs,
            report=report,
            fixed=fixed,
            free=free,
            vectors={
                "reference_loads": loads,
                "final_external_load": external,
                "displacements": displacement,
                "final_internal_force": internal,
                "residual": residual,
                "reactions": reactions,
            },
            load_assembly=self.assembler.last_load_diagnostics,
            matrices={"final_tangent": tangent, "reduced_final_tangent": tangent[free, :][:, free]},
            equilibrium=static_equilibrium_summary(
                model=model,
                dofs=dofs,
                loads=loads,
                internal=internal,
                displacement=displacement,
                fixed=fixed,
                free=free,
                load_factor=load_factor,
            ),
            post_results=post_results,
            notes=["Nonlinear audit uses the tangent matrix at the converged final displacement."],
        )
        return SolveResult(
            status="PASS",
            displacements=displacement,
            dofs=dofs,
            mesh_report=report,
            node_count=model.node_count,
            element_count=len(model.elements),
            analysis="nonlinear_static",
            method=model.analysis.method,
            solver={
                "nonlinear_options": {
                    "load_steps": options.load_steps,
                    "max_iterations": options.max_iterations,
                    "tolerance": options.tolerance,
                    "linear_method": options.linear_method,
                    "line_search_min_alpha": options.line_search_min_alpha,
                    "line_search_max_reductions": options.line_search_max_reductions,
                    "line_search_c": options.line_search_c,
                    "adaptive_load_steps": options.adaptive_load_steps,
                },
                "adaptive_load_steps": adaptive,
                "arc_length": model.analysis.method == "arc_length",
                "adaptive_arc_length": bool(arc_length_controls and arc_length_controls.adaptive_radius),
                "arc_length_growth_factor": (
                    arc_length_controls.growth_factor if arc_length_controls else None
                ),
                "arc_length_shrink_factor": (
                    arc_length_controls.shrink_factor if arc_length_controls else None
                ),
                "arc_length_minimum_radius": (
                    arc_length_controls.minimum_radius if arc_length_controls else None
                ),
                "arc_length_stop_mode": str(params.get("arc_length_stop_mode", "target_load")).lower(),
                "arc_length_allow_load_factor_turning": bool(
                    params.get(
                        "arc_length_allow_load_factor_turning",
                        str(params.get("arc_length_stop_mode", "target_load")).lower() == "max_steps",
                    )
                ),
                "arc_length_load_factor_limit": float(
                    params.get(
                        "arc_length_load_factor_limit",
                        max(abs(float(params.get("target_load_factor", 1.0))), 1.0),
                    )
                ),
                "kinematics": str(params.get("kinematics", "small_strain")).lower(),
                "contact_mode": str(params.get("contact_mode", "none")).lower(),
                "contact_search_mode": str(params.get("contact_search_mode", "initial")).lower(),
                "path_dependent_material_state": bool(material_states),
                "load_path": completed_factors or [item.load_factor for item in history],
                "restart_step": checkpoint_session.restart_step if checkpoint_session else 0,
                "history_is_partial": bool(checkpoint_session and checkpoint_session.restart_step > 0),
                "checkpoint_path": checkpoint_session.settings.path if checkpoint_session else None,
                "checkpoint_files": checkpoint_session.files if checkpoint_session else [],
                "checkpoint_model_signature": checkpoint_session.signature if checkpoint_session else "",
                "rejected_increments": self._rejected_increments,
                "rejection_log": list(self._rejection_log),
                "load_assembly": dict(self.assembler.last_load_diagnostics),
                "steps": [item.to_dict() for item in history],
            },
            element_results=element_results,
            nodal_results=nodal_results,
            material_states=copy_material_states(material_states),
            audit=audit,
        )

    def _solve_arc_length(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        displacement: np.ndarray,
        free: np.ndarray,
        loads: np.ndarray,
        material_states: MaterialStateTable,
        load_steps: int,
        max_iterations: int,
        tolerance: float,
        linear_method: str,
        checkpoint_session: NonlinearCheckpointSession | None = None,
        continuation_state: dict[str, object] | None = None,
        arc_length_controls: ArcLengthControls | None = None,
    ) -> list[NonlinearStep]:
        params = model.analysis.parameters
        target_factor = float(params.get("target_load_factor", 1.0))
        if not np.isfinite(target_factor):
            raise InputValidationError("target_load_factor must be finite for arc_length.")
        max_steps = max(1, int(params.get("max_arc_steps", max(load_steps * 4, load_steps + 1))))
        controls = arc_length_controls or ArcLengthControls.from_parameters(
            params,
            max_iterations=max_iterations,
        )
        stop_mode = str(params.get("arc_length_stop_mode", "target_load")).lower()
        if stop_mode not in {"target_load", "max_steps"}:
            raise InputValidationError("arc_length_stop_mode must be 'target_load' or 'max_steps'.")
        allow_turning = bool(params.get("arc_length_allow_load_factor_turning", stop_mode == "max_steps"))
        load_factor_limit = float(
            params.get("arc_length_load_factor_limit", max(abs(target_factor), 1.0))
        )
        if not np.isfinite(load_factor_limit) or load_factor_limit <= 0.0:
            raise InputValidationError("arc_length_load_factor_limit must be finite and positive.")
        target_direction = 1.0 if target_factor >= 0.0 else -1.0
        current_factor = float((continuation_state or {}).get("load_factor", 0.0))
        history: list[NonlinearStep] = []
        reference = max(float(np.linalg.norm(loads[free])), 1.0)
        if continuation_state:
            radius = float(continuation_state["radius"])
            maximum_radius = float(
                continuation_state.get(
                    "maximum_radius",
                    params.get("max_arc_length_radius", radius),
                )
            )
            load_scale = float(continuation_state["load_scale"])
            previous_du = np.asarray(continuation_state["previous_du"], dtype=float)
            if previous_du.shape != (free.size,) or not np.all(np.isfinite(previous_du)):
                raise InputValidationError("Arc-length checkpoint previous displacement increment is invalid.")
            if not np.isfinite(radius) or radius <= 0.0 or not np.isfinite(load_scale) or load_scale <= 0.0:
                raise InputValidationError("Arc-length checkpoint radius or load scale is invalid.")
            step = checkpoint_session.restart_step if checkpoint_session is not None else 0
        else:
            radius, load_scale = self._initial_arc_length_radius(
                model,
                dofs,
                displacement,
                free,
                loads,
                material_states,
                load_steps,
                linear_method,
            )
            initial_radius = radius
            radius = float(params.get("arc_length_radius", radius))
            maximum_radius = float(
                params.get("max_arc_length_radius", max(initial_radius, radius))
            )
            load_scale = float(params.get("arc_length_load_scale", load_scale))
            previous_du = np.zeros(free.size, dtype=float)
            step = 0
        if (
            not np.isfinite(maximum_radius)
            or maximum_radius < controls.minimum_radius
            or maximum_radius < radius
        ):
            raise InputValidationError(
                "max_arc_length_radius must be finite and at least the current arc-length radius."
            )
        def target_reached() -> bool:
            return target_direction * (current_factor - target_factor) >= -1.0e-12

        while (not target_reached()) if stop_mode == "target_load" else step < max_steps:
            step += 1
            if step > max_steps:
                raise NumericalConvergenceError(
                    "Arc-length continuation reached max_arc_steps before the target load factor.",
                    reason=NonlinearFailureReason.ARC_LENGTH_FAILURE,
                    diagnostics={
                        "max_arc_steps": max_steps,
                        "current_load_factor": current_factor,
                        "target_load_factor": target_factor,
                        "last_radius": radius,
                    },
                )
            step_radius = self._radius_for_target(
                model,
                dofs,
                displacement,
                free,
                loads,
                material_states,
                current_factor,
                target_factor,
                radius,
                load_scale,
                linear_method,
            )
            step_radius = max(step_radius, controls.minimum_radius)
            trial = displacement.copy()
            state_session = MaterialStateSession(material_states)
            trial_states = state_session.begin_trial()
            try:
                info, current_factor, previous_du = self._solve_arc_length_step(
                    model,
                    dofs,
                    trial,
                    free,
                    loads,
                    trial_states,
                    step,
                    current_factor,
                    target_factor,
                    step_radius,
                    load_scale,
                    previous_du,
                    max_iterations,
                    tolerance,
                    reference,
                    linear_method,
                    allow_load_factor_turning=allow_turning,
                    load_factor_limit=load_factor_limit,
                    target_direction=target_direction,
                )
            except NumericalConvergenceError as error:
                state_session.rollback()
                if error.reason not in {
                    None,
                    NonlinearFailureReason.ARC_LENGTH_FAILURE,
                    NonlinearFailureReason.LINE_SEARCH_FAILURE,
                    NonlinearFailureReason.MAX_ITERATIONS,
                    NonlinearFailureReason.SINGULAR_TANGENT,
                }:
                    raise
                previous_radius = radius
                radius *= controls.shrink_factor
                self._rejected_increments += 1
                self._rejection_log.append(
                    {
                        "path": "arc_length",
                        "step": step,
                        "base_load_factor": current_factor,
                        "rejected_radius": step_radius,
                        "retry_radius": radius,
                        "previous_radius": previous_radius,
                        "failure_reason": _failure_reason_value(error),
                        "failure_diagnostics": dict(error.diagnostics),
                        "rollback_before_retry": True,
                    }
                )
                if radius < controls.minimum_radius:
                    raise NumericalConvergenceError(
                        "Arc-length continuation reached the minimum radius.",
                        reason=NonlinearFailureReason.MIN_INCREMENT_REACHED,
                        diagnostics={
                            "minimum_radius": controls.minimum_radius,
                            "last_failure_reason": _failure_reason_value(error),
                            "last_failure_diagnostics": dict(error.diagnostics),
                        },
                    ) from error
                step -= 1
                continue
            except RuntimeError as error:
                state_session.rollback()
                previous_radius = radius
                radius *= controls.shrink_factor
                self._rejected_increments += 1
                self._rejection_log.append(
                    {
                        "path": "arc_length",
                        "step": step,
                        "base_load_factor": current_factor,
                        "rejected_radius": step_radius,
                        "retry_radius": radius,
                        "previous_radius": previous_radius,
                        "failure_reason": type(error).__name__,
                        "failure_diagnostics": {"message": str(error)},
                        "rollback_before_retry": True,
                    }
                )
                if radius < controls.minimum_radius:
                    raise NumericalConvergenceError(
                        "Arc-length continuation reached the minimum radius.",
                        reason=NonlinearFailureReason.MIN_INCREMENT_REACHED,
                        diagnostics={
                            "minimum_radius": controls.minimum_radius,
                            "last_failure_reason": _failure_reason_value(error),
                        },
                    ) from error
                step -= 1
                continue
            displacement[:] = trial
            state_session.commit()
            history.append(info)
            if controls.adaptive_radius:
                if info.iterations <= controls.grow_below_iterations:
                    radius = min(maximum_radius, radius * controls.growth_factor)
                elif info.iterations >= controls.shrink_above_iterations:
                    radius = max(controls.minimum_radius, radius * controls.shrink_factor)
            if checkpoint_session is not None:
                checkpoint_session.save(
                    step,
                    current_factor,
                    displacement,
                    material_states,
                    continuation_state={
                        "load_factor": current_factor,
                        "radius": radius,
                        "maximum_radius": maximum_radius,
                        "load_scale": load_scale,
                        "previous_du": previous_du.tolist(),
                    },
                )
        return history

    def _initial_arc_length_radius(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        displacement: np.ndarray,
        free: np.ndarray,
        loads: np.ndarray,
        material_states: MaterialStateTable,
        load_steps: int,
        linear_method: str,
    ) -> tuple[float, float]:
        _, tangent, _ = self._assemble_internal_tangent(model, dofs, displacement, material_states)
        predictor, info = self.linear_solver.solve(tangent[free, :][:, free], loads[free], method=linear_method)
        if not info.converged:
            raise NumericalConvergenceError(
                "Arc-length predictor solve did not converge.",
                reason=NonlinearFailureReason.LINEAR_SOLVER_FAILURE,
            )
        scale = max(float(np.linalg.norm(predictor)), 1.0e-12)
        radius = np.sqrt(float(predictor @ predictor) + scale**2) / max(load_steps, 1)
        return float(radius), float(scale)

    def _radius_for_target(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        displacement: np.ndarray,
        free: np.ndarray,
        loads: np.ndarray,
        material_states: MaterialStateTable,
        current_factor: float,
        target_factor: float,
        radius: float,
        load_scale: float,
        linear_method: str,
    ) -> float:
        remaining = target_factor - current_factor
        if abs(remaining) <= 1.0e-12:
            return radius
        _, tangent, _ = self._assemble_internal_tangent(model, dofs, displacement, material_states)
        predictor, info = self.linear_solver.solve(tangent[free, :][:, free], loads[free], method=linear_method)
        if not info.converged:
            raise NumericalConvergenceError(
                "Arc-length target-radius solve did not converge.",
                reason=NonlinearFailureReason.LINEAR_SOLVER_FAILURE,
            )
        exact_radius = abs(remaining) * np.sqrt(float(predictor @ predictor) + load_scale**2)
        return min(radius, float(exact_radius))

    def _solve_arc_length_step(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        displacement: np.ndarray,
        free: np.ndarray,
        loads: np.ndarray,
        material_states: MaterialStateTable,
        step: int,
        base_factor: float,
        target_factor: float,
        radius: float,
        load_scale: float,
        previous_du: np.ndarray,
        max_iterations: int,
        tolerance: float,
        reference: float,
        linear_method: str,
        *,
        allow_load_factor_turning: bool = False,
        load_factor_limit: float | None = None,
        target_direction: float = 1.0,
    ) -> tuple[NonlinearStep, float, np.ndarray]:
        base_u = displacement.copy()
        assembly_seconds = 0.0
        linear_solve_seconds = 0.0
        phase_timing: dict[str, float | int] = {}
        phase_started = perf_counter()
        _, tangent, _ = self._assemble_internal_tangent(
            model, dofs, displacement, material_states, timing=phase_timing
        )
        assembly_seconds += perf_counter() - phase_started
        phase_started = perf_counter()
        predictor, info = self.linear_solver.solve(tangent[free, :][:, free], loads[free], method=linear_method)
        linear_solve_seconds += perf_counter() - phase_started
        if not info.converged:
            raise NumericalConvergenceError(
                "Arc-length predictor solve did not converge.",
                reason=NonlinearFailureReason.LINEAR_SOLVER_FAILURE,
            )
        direction = 1.0 if target_direction >= 0.0 else -1.0
        if previous_du.size == predictor.size and float(previous_du @ predictor) < 0.0:
            direction = -1.0
        delta_factor = direction * radius / np.sqrt(float(predictor @ predictor) + load_scale**2)
        if not allow_load_factor_turning and target_direction * (base_factor + delta_factor - target_factor) > 0.0:
            delta_factor = target_factor - base_factor
        displacement[free] += delta_factor * predictor
        load_factor = base_factor + delta_factor
        if load_factor_limit is not None and abs(load_factor) > load_factor_limit + 1.0e-12:
            raise NumericalConvergenceError(
                "Arc-length predictor exceeded the configured load-factor envelope.",
                reason=NonlinearFailureReason.ARC_LENGTH_FAILURE,
                diagnostics={"load_factor": load_factor, "load_factor_limit": load_factor_limit},
            )
        residual_norm = float("inf")
        relative = float("inf")
        residual_history: list[float] = []
        contact_diagnostics: dict[str, object] = {}
        for iteration in range(1, max_iterations + 1):
            phase_started = perf_counter()
            internal, tangent, updated_states = self._assemble_internal_tangent(
                model,
                dofs,
                displacement,
                material_states,
                contact_diagnostics=contact_diagnostics,
                timing=phase_timing,
            )
            assembly_seconds += perf_counter() - phase_started
            residual = load_factor * loads - internal
            residual_norm = float(np.linalg.norm(residual[free]))
            residual_history.append(residual_norm)
            delta_u_step = displacement[free] - base_u[free]
            delta_lambda = load_factor - base_factor
            constraint = float(delta_u_step @ delta_u_step + (load_scale * delta_lambda) ** 2 - radius**2)
            relative = max(residual_norm / reference, abs(constraint) / max(radius**2, 1.0e-30))
            if relative <= tolerance:
                commit_material_states(material_states, updated_states)
                return (
                    NonlinearStep(
                        step,
                        load_factor,
                        iteration - 1,
                        residual_norm,
                        relative,
                        0,
                        1.0,
                        delta_lambda,
                        arc_length_radius=radius,
                        residual_history=tuple(residual_history),
                        assembly_seconds=assembly_seconds,
                        linear_solve_seconds=linear_solve_seconds,
                        element_setup_seconds=float(phase_timing.get("element_setup_seconds", 0.0)),
                        element_kernel_seconds=float(phase_timing.get("element_kernel_seconds", 0.0)),
                        element_scatter_seconds=float(phase_timing.get("element_scatter_seconds", 0.0)),
                        sparse_conversion_seconds=float(phase_timing.get("sparse_conversion_seconds", 0.0)),
                        contact_assembly_seconds=float(phase_timing.get("contact_assembly_seconds", 0.0)),
                        element_kernel_calls=int(phase_timing.get("element_kernel_calls", 0)),
                        contact_assembly_calls=int(phase_timing.get("contact_assembly_calls", 0)),
                        element_cache_hits=int(phase_timing.get("element_cache_hits", 0)),
                        element_cache_misses=int(phase_timing.get("element_cache_misses", 0)),
                        reference_cache_hits=int(phase_timing.get("reference_cache_hits", 0)),
                        reference_cache_misses=int(phase_timing.get("reference_cache_misses", 0)),
                        sparse_chunk_count=int(phase_timing.get("sparse_chunk_count", 0)),
                        sparse_peak_chunk_entries=int(phase_timing.get("sparse_peak_chunk_entries", 0)),
                        sparse_peak_chunk_bytes_estimate=int(
                            phase_timing.get("sparse_peak_chunk_bytes_estimate", 0)
                        ),
                        sparse_accumulator_levels=int(phase_timing.get("sparse_accumulator_levels", 0)),
                        tangent_nnz=int(phase_timing.get("tangent_nnz", 0)),
                        contact_active_contacts=tuple(
                            int(index) for index in contact_diagnostics.get("active_contacts", [])
                        ),
                        contact_gaps=tuple(
                            float(gap) for gap in contact_diagnostics.get("gaps", [])
                        ),
                        contact_tangent_nnz=int(contact_diagnostics.get("tangent_nnz", 0)),
                        contact_master_face_indices=tuple(
                            int(index) for index in contact_diagnostics.get("master_face_indices", [])
                        ),
                        contact_search_mode=(
                            str(contact_diagnostics["search_mode"])
                            if contact_diagnostics.get("search_mode") is not None
                            else None
                        ),
                        contact_finite_sliding=bool(contact_diagnostics.get("finite_sliding", False)),
                        contact_projection_clamped=tuple(
                            bool(value) for value in contact_diagnostics.get("projection_clamped", [])
                        ),
                        contact_closest_distances=tuple(
                            float(value) for value in contact_diagnostics.get("closest_distances", [])
                        ),
                    ),
                    load_factor,
                    delta_u_step.copy(),
                )
            phase_started = perf_counter()
            correction_u, correction_lambda = solve_arc_length_correction(
                tangent[free, :][:, free],
                loads[free],
                residual[free],
                delta_u_step,
                delta_lambda,
                constraint,
                load_scale,
            )
            linear_solve_seconds += perf_counter() - phase_started
            candidate_factor = load_factor + correction_lambda
            if load_factor_limit is not None and abs(candidate_factor) > load_factor_limit + 1.0e-12:
                raise NumericalConvergenceError(
                    "Arc-length correction exceeded the configured load-factor envelope.",
                    reason=NonlinearFailureReason.ARC_LENGTH_FAILURE,
                    diagnostics={"load_factor": candidate_factor, "load_factor_limit": load_factor_limit},
                )
            displacement[free] += correction_u
            load_factor = candidate_factor
        raise NumericalConvergenceError(
            f"Arc-length step {step} did not converge in {max_iterations} iterations; "
            f"relative residual={relative:.6e}.",
            reason=NonlinearFailureReason.ARC_LENGTH_FAILURE,
            diagnostics={
                "step": step,
                "iterations": max_iterations,
                "relative_residual": relative,
                "residual_history": residual_history,
            },
        )

    def _solve_adaptive_load_steps(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        displacement: np.ndarray,
        free: np.ndarray,
        loads: np.ndarray,
        material_states: MaterialStateTable,
        load_steps: int,
        max_iterations: int,
        tolerance: float,
        linear_method: str,
        min_alpha: float,
        max_reductions: int,
        armijo: float,
    ) -> list[NonlinearStep]:
        params = model.analysis.parameters
        controls = AdaptiveLoadControls.from_parameters(
            params,
            load_steps=load_steps,
            max_iterations=max_iterations,
        )
        current_factor = 0.0
        increment = controls.initial_increment
        history: list[NonlinearStep] = []
        step = 0
        pending_cutbacks = 0
        while current_factor < 1.0 - 1.0e-12:
            proposed = min(increment, 1.0 - current_factor)
            target_factor = current_factor + proposed
            trial = displacement.copy()
            state_session = MaterialStateSession(material_states)
            trial_states = state_session.begin_trial()
            try:
                info = self._solve_load_step(
                    model,
                    dofs,
                    trial,
                    free,
                    target_factor * loads,
                    trial_states,
                    step + 1,
                    target_factor,
                    proposed,
                    None,
                    max_iterations,
                    tolerance,
                    linear_method,
                    min_alpha,
                    max_reductions,
                    armijo,
                    current_factor * loads,
                    max(float(np.linalg.norm(loads[free])), 1.0),
                )
            except RuntimeError as error:
                state_session.rollback()
                self._rejected_increments += 1
                pending_cutbacks += 1
                rejected = proposed
                proposed *= controls.cutback_factor
                self._rejection_log.append(
                    {
                        "base_load_factor": current_factor,
                        "rejected_increment": rejected,
                        "retry_increment": proposed,
                        "failure_reason": _failure_reason_value(error),
                    }
                )
                if self._rejected_increments > controls.maximum_cutbacks:
                    raise NumericalConvergenceError(
                        f"Adaptive nonlinear load stepping exceeded max_cutbacks={controls.maximum_cutbacks}.",
                        reason=NonlinearFailureReason.MAX_ITERATIONS,
                        diagnostics={
                            "max_cutbacks": controls.maximum_cutbacks,
                            "last_failure_reason": _failure_reason_value(error),
                        },
                    )
                if proposed < controls.minimum_increment:
                    raise NumericalConvergenceError(
                        "Adaptive nonlinear load stepping reached the minimum load increment.",
                        reason=NonlinearFailureReason.MIN_INCREMENT_REACHED,
                        diagnostics={"minimum_increment": controls.minimum_increment},
                    )
                increment = proposed
                continue
            info = replace(info, load_step_cutbacks=pending_cutbacks)
            pending_cutbacks = 0
            displacement[:] = trial
            state_session.commit()
            history.append(info)
            step += 1
            current_factor = target_factor
            if info.iterations <= controls.grow_below_iterations:
                increment = min(controls.maximum_increment, proposed * controls.growth_factor)
            elif info.iterations >= controls.shrink_above_iterations:
                increment = max(controls.minimum_increment, proposed * controls.cutback_factor)
            else:
                increment = proposed
        return history

    def _solve_load_step(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        displacement: np.ndarray,
        free: np.ndarray,
        target_load: np.ndarray,
        material_states: MaterialStateTable,
        step: int,
        load_factor: float,
        load_increment: float,
        cached_tangent: csr_matrix | None,
        max_iterations: int,
        tolerance: float,
        linear_method: str,
        min_alpha: float,
        max_reductions: int,
        armijo: float,
        previous_load: np.ndarray | None = None,
        reference_force_norm: float | None = None,
    ) -> NonlinearStep:
        base_displacement = displacement.copy()
        base_internal: np.ndarray | None = None
        previous_load = np.zeros_like(target_load) if previous_load is None else previous_load
        force_scale = max(float(np.linalg.norm(target_load[free])), float(reference_force_norm or 0.0), 1.0)
        residual_norm = float("inf")
        relative = float("inf")
        residual_history: list[float] = []
        contact_diagnostics: dict[str, object] = {}
        total_reductions = 0
        min_factor = 1.0
        last_correction_norm = 0.0
        cumulative_correction_norm = 0.0
        initial_residual_norm = 0.0
        assembly_seconds = 0.0
        linear_solve_seconds = 0.0
        line_search_seconds = 0.0
        phase_timing: dict[str, float | int] = {}
        for iteration in range(1, max_iterations + 1):
            phase_started = perf_counter()
            internal, tangent, updated_states = self._assemble_internal_tangent(
                model,
                dofs,
                displacement,
                material_states,
                contact_diagnostics=contact_diagnostics,
                timing=phase_timing,
            )
            assembly_seconds += perf_counter() - phase_started
            if base_internal is None:
                base_internal = internal.copy()
            residual = target_load - internal
            residual_norm = float(np.linalg.norm(residual[free]))
            residual_history.append(residual_norm)
            if iteration == 1:
                initial_residual_norm = residual_norm
            relative = residual_norm / force_scale
            if relative <= tolerance:
                internal_work, external_work, work_imbalance = incremental_work_diagnostics(
                    base_displacement, displacement, base_internal, internal, previous_load, target_load
                )
                commit_material_states(material_states, updated_states)
                return NonlinearStep(
                    step,
                    load_factor,
                    iteration - 1,
                    residual_norm,
                    relative,
                    total_reductions,
                    min_factor,
                    load_increment,
                    maximum_equivalent_plastic_strain(updated_states),
                    True,
                    last_correction_norm,
                    cumulative_correction_norm,
                    internal_work,
                    external_work,
                    work_imbalance,
                    0,
                    True,
                    initial_residual_norm,
                    residual_history=tuple(residual_history),
                    plastic_dissipation_max=maximum_plastic_dissipation(updated_states),
                    assembly_seconds=assembly_seconds,
                    linear_solve_seconds=linear_solve_seconds,
                    line_search_seconds=line_search_seconds,
                    element_setup_seconds=float(phase_timing.get("element_setup_seconds", 0.0)),
                    element_kernel_seconds=float(phase_timing.get("element_kernel_seconds", 0.0)),
                    element_scatter_seconds=float(phase_timing.get("element_scatter_seconds", 0.0)),
                    sparse_conversion_seconds=float(phase_timing.get("sparse_conversion_seconds", 0.0)),
                    contact_assembly_seconds=float(phase_timing.get("contact_assembly_seconds", 0.0)),
                    element_kernel_calls=int(phase_timing.get("element_kernel_calls", 0)),
                    contact_assembly_calls=int(phase_timing.get("contact_assembly_calls", 0)),
                    element_cache_hits=int(phase_timing.get("element_cache_hits", 0)),
                    element_cache_misses=int(phase_timing.get("element_cache_misses", 0)),
                    reference_cache_hits=int(phase_timing.get("reference_cache_hits", 0)),
                    reference_cache_misses=int(phase_timing.get("reference_cache_misses", 0)),
                    sparse_chunk_count=int(phase_timing.get("sparse_chunk_count", 0)),
                    sparse_peak_chunk_entries=int(phase_timing.get("sparse_peak_chunk_entries", 0)),
                    sparse_peak_chunk_bytes_estimate=int(
                        phase_timing.get("sparse_peak_chunk_bytes_estimate", 0)
                    ),
                    sparse_accumulator_levels=int(phase_timing.get("sparse_accumulator_levels", 0)),
                    tangent_nnz=int(phase_timing.get("tangent_nnz", 0)),
                    contact_active_contacts=tuple(
                        int(index) for index in contact_diagnostics.get("active_contacts", [])
                    ),
                    contact_gaps=tuple(
                        float(gap) for gap in contact_diagnostics.get("gaps", [])
                    ),
                    contact_tangent_nnz=int(contact_diagnostics.get("tangent_nnz", 0)),
                    contact_master_face_indices=tuple(
                        int(index) for index in contact_diagnostics.get("master_face_indices", [])
                    ),
                    contact_search_mode=(
                        str(contact_diagnostics["search_mode"])
                        if contact_diagnostics.get("search_mode") is not None
                        else None
                    ),
                    contact_finite_sliding=bool(contact_diagnostics.get("finite_sliding", False)),
                    contact_projection_clamped=tuple(
                        bool(value) for value in contact_diagnostics.get("projection_clamped", [])
                    ),
                    contact_closest_distances=tuple(
                        float(value) for value in contact_diagnostics.get("closest_distances", [])
                    ),
                    contact_projection_modes=tuple(
                        str(value) for value in contact_diagnostics.get("projection_modes", [])
                    ),
                )
            if model.analysis.method == "modified_newton":
                if cached_tangent is None:
                    cached_tangent = tangent[free, :][:, free]
                active_tangent = cached_tangent
            else:
                active_tangent = tangent[free, :][:, free]
            phase_started = perf_counter()
            increment, info = self.linear_solver.solve(active_tangent, residual[free], method=linear_method)
            linear_solve_seconds += perf_counter() - phase_started
            if not info.converged:
                raise NumericalConvergenceError(
                    f"Nonlinear linearization failed with {linear_method}; residual={info.residual_norm:.6e}.",
                    reason=NonlinearFailureReason.LINEAR_SOLVER_FAILURE,
                    diagnostics={"linear_method": linear_method, "residual": info.residual_norm},
                )
            if model.analysis.method == "newton_line_search":
                phase_started = perf_counter()
                factor, reductions = line_search_factor(
                    self._assemble_internal_tangent,
                    model,
                    dofs,
                    displacement,
                    free,
                    target_load,
                    material_states,
                    increment,
                    residual_norm,
                    min_alpha,
                    max_reductions,
                    armijo,
                )
                line_search_seconds += perf_counter() - phase_started
                total_reductions += reductions
                min_factor = min(min_factor, factor)
                applied_increment = factor * increment
                displacement[free] += applied_increment
            else:
                applied_increment = increment
                displacement[free] += applied_increment
            last_correction_norm = float(np.linalg.norm(applied_increment))
            cumulative_correction_norm += last_correction_norm
        raise NumericalConvergenceError(
            f"Nonlinear step {step} did not converge in {max_iterations} iterations; "
            f"relative residual={relative:.6e}.",
            reason=NonlinearFailureReason.MAX_ITERATIONS,
            diagnostics={
                "step": step,
                "iterations": max_iterations,
                "residual_initial": initial_residual_norm,
                "residual_final": residual_norm,
                "relative_residual": relative,
            },
        )

    @staticmethod
    def _validate_kinematics_scope(model: FiniteElementModel, params: dict[str, object]) -> None:
        """Validate the explicitly experimental finite-kinematic J2 branch."""
        if model.contacts:
            contact_mode = str(params.get("contact_mode", "")).lower()
            if contact_mode != "penalty":
                raise InputValidationError(
                    "Nonlinear contact requires explicit contact_mode='penalty'; "
                    "the historical active-set solver is not silently reused."
                )
            if any(contact.friction_coefficient > 0.0 for contact in model.contacts):
                raise InputValidationError("The common nonlinear contact path is frictionless only.")
        kinematics = str(params.get("kinematics", "small_strain")).lower()
        if kinematics == "small_strain":
            return
        if kinematics != "total_lagrangian_j2":
            raise InputValidationError(
                "nonlinear_static kinematics must be 'small_strain' or 'total_lagrangian_j2'."
            )
        if model.analysis.method == "modified_newton":
            raise InputValidationError(
                "total_lagrangian_j2 is qualified only with Full Newton; "
                "modified_newton remains outside the 0.2.5 production scope."
            )
        families = {element.type for element in model.elements}
        if not families or not families <= {"TET4", "TET10", "HEX8", "HEX20"}:
            raise InputValidationError(
                "total_lagrangian_j2 currently supports homogeneous TET4, TET10, HEX8 or HEX20 meshes."
            )
        if len(families) != 1:
            raise InputValidationError(
                "total_lagrangian_j2 currently requires one homogeneous element family."
            )
        material_types = {
            str(model.materials[element.material].get("type", "")).lower()
            for element in model.elements
        }
        if material_types != {"von_mises_elastoplastic_3d"}:
            raise InputValidationError(
                "total_lagrangian_j2 requires material type 'von_mises_elastoplastic_3d'."
            )

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
        return assemble_internal_tangent(
            model,
            dofs,
            displacement,
            material_states,
            contact_diagnostics=contact_diagnostics,
            timing=timing,
            plan=self._assembly_plan,
        )


def _failure_reason_value(error: BaseException) -> str:
    """Return a stable failure code for adaptive-step telemetry."""
    reason = getattr(error, "reason", None)
    if isinstance(reason, NonlinearFailureReason):
        return reason.value
    if reason is not None:
        return str(reason)
    return type(error).__name__
