"""Load-control continuation for the nonlinear solver."""

from __future__ import annotations

from dataclasses import replace
from time import perf_counter

import numpy as np
from scipy.sparse import csr_matrix

from solveur.core.dofs import DofManager
from solveur.core.errors import NumericalConvergenceError
from solveur.core.material_state import MaterialStateSession, MaterialStateTable, commit_material_states
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear_contracts import NonlinearFailureReason
from solveur.core.nonlinear_controls import (
    AdaptiveLoadControls,
    NonlinearStep,
    incremental_work_diagnostics,
    maximum_equivalent_plastic_strain,
    maximum_plastic_dissipation,
)
from solveur.core.nonlinear_iteration import line_search_factor
from solveur.core.nonlinear_support import _failure_reason_value



class NonlinearLoadControlMixin:
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
