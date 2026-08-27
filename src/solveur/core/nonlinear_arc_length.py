"""Arc-length continuation for the nonlinear solver."""

from __future__ import annotations

from time import perf_counter

import numpy as np

from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.material_state import (
    MaterialStateSession,
    MaterialStateTable,
    commit_material_states,
)
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear_checkpoint import NonlinearCheckpointSession
from solveur.core.nonlinear_contracts import NonlinearFailureReason
from solveur.core.nonlinear_controls import ArcLengthControls, NonlinearStep
from solveur.core.nonlinear_iteration import solve_arc_length_correction
from solveur.core.nonlinear_support import _failure_reason_value



class NonlinearArcLengthMixin:
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
        control_dof_value = params.get("arc_length_control_dof")
        control_dof: int | None = None
        if control_dof_value is not None:
            if isinstance(control_dof_value, bool) or not isinstance(control_dof_value, int):
                raise InputValidationError("arc_length_control_dof must be an integer global DDL index.")
            if control_dof_value < 0 or control_dof_value >= dofs.ndof or control_dof_value not in set(free.tolist()):
                raise InputValidationError("arc_length_control_dof must identify a free global DDL.")
            control_dof = control_dof_value
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
            previous_dlambda = float(continuation_state.get("previous_dlambda", 0.0))
            if previous_du.shape != (free.size,) or not np.all(np.isfinite(previous_du)):
                raise InputValidationError("Arc-length checkpoint previous displacement increment is invalid.")
            if not np.isfinite(previous_dlambda):
                raise InputValidationError("Arc-length checkpoint previous load increment is invalid.")
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
            previous_dlambda = 0.0
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
                    previous_dlambda,
                    max_iterations,
                    tolerance,
                    reference,
                    linear_method,
                    allow_load_factor_turning=allow_turning,
                    load_factor_limit=load_factor_limit,
                    target_direction=target_direction,
                    control_dof=control_dof,
                )
                previous_dlambda = info.load_increment
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
                        reason=NonlinearFailureReason.ARC_LENGTH_FAILURE,
                        diagnostics={
                            "failure_stage": "minimum_radius",
                            "minimum_radius": controls.minimum_radius,
                            "last_radius": radius,
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
                        reason=NonlinearFailureReason.ARC_LENGTH_FAILURE,
                        diagnostics={
                            "failure_stage": "minimum_radius",
                            "minimum_radius": controls.minimum_radius,
                            "last_radius": radius,
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
                        "previous_dlambda": previous_dlambda,
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
        previous_dlambda: float,
        max_iterations: int,
        tolerance: float,
        reference: float,
        linear_method: str,
        *,
        allow_load_factor_turning: bool = False,
        load_factor_limit: float | None = None,
        target_direction: float = 1.0,
        control_dof: int | None = None,
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
        has_previous_direction = bool(
            previous_du.size == predictor.size
            and (float(np.linalg.norm(previous_du)) > 1.0e-14 or abs(previous_dlambda) > 1.0e-14)
        )
        displacement_orientation = float(previous_du @ predictor)
        tangent_orientation = float(displacement_orientation + load_scale**2 * previous_dlambda)
        if has_previous_direction:
            # Preserve the physical displacement branch first.  The load
            # factor is allowed to reverse at a limit point, so it must not
            # override the displacement orientation.  The augmented term is
            # only a tie-breaker when the displacement projection vanishes.
            displacement_scale = max(
                float(np.linalg.norm(previous_du)) * float(np.linalg.norm(predictor)),
                1.0e-30,
            )
            if abs(displacement_orientation) > 1.0e-12 * displacement_scale:
                direction = 1.0 if displacement_orientation > 0.0 else -1.0
            elif tangent_orientation < 0.0:
                direction = -1.0
        delta_factor = direction * radius / np.sqrt(float(predictor @ predictor) + load_scale**2)
        predictor_sign = int(np.sign(delta_factor))
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
                alignment = float(
                    delta_u_step @ previous_du + load_scale**2 * delta_lambda * previous_dlambda
                )
                # A negative augmented-space dot product is not sufficient to
                # reject a point: at a legitimate load-factor turning point,
                # the displacement branch can remain continuous while the
                # signed load increment changes direction.  The predictor
                # selects the continuation branch; retain the alignment as a
                # diagnostic for the evidence layer instead of treating every
                # lambda reversal as a branch jump.
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
                        arc_length_control_displacement=(
                            float(displacement[control_dof]) if control_dof is not None else None
                        ),
                        arc_length_predictor_sign=predictor_sign,
                        arc_length_branch_direction=(
                            int(np.sign(alignment)) if has_previous_direction else predictor_sign
                        ),
                        arc_length_direction_alignment=alignment if has_previous_direction else None,
                        arc_length_constraint_residual=constraint,
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
