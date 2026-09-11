"""Load-control continuation for the nonlinear solver."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
from scipy.sparse import csr_matrix

from solveur.core.dofs import DofManager
from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.material_state import (
    MaterialStateTable,
    commit_material_states,
    copy_material_states,
)
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.controls import (
    AdaptiveLoadControls,
    NonlinearStep,
    incremental_work_diagnostics,
    maximum_equivalent_plastic_strain,
    maximum_plastic_dissipation,
)
from solveur.core.nonlinear.driver import (
    CompositeContributionResponse,
    ContributionResponse,
    UnifiedContinuationController,
    UnifiedNewtonEngine,
    continuation_retry_permitted,
)
from solveur.core.nonlinear.checkpoint import NonlinearCheckpointSession
from solveur.core.nonlinear.iteration import line_search_factor
from solveur.core.nonlinear.state import NonlinearState
from solveur.core.nonlinear.support import _failure_reason_value

class _MaterialLoadControlContribution:
    """Adapt the existing material/geometric/contact assembly to the common driver."""

    name = "material"

    def __init__(
        self,
        owner: "NonlinearLoadControlMixin",
        model: FiniteElementModel,
        dofs: DofManager,
        contact_diagnostics: dict[str, object],
        timing: dict[str, float | int],
        material_states: MaterialStateTable,
    ) -> None:
        self.owner = owner
        self.model = model
        self.dofs = dofs
        self.contact_diagnostics = contact_diagnostics
        self.timing = timing
        self.committed_material_states = copy_material_states(material_states)
        self.first_internal: np.ndarray | None = None
        self.last_internal: np.ndarray | None = None
        self.last_updated_states: MaterialStateTable | None = None

    def evaluate(self, state: NonlinearState) -> ContributionResponse:
        internal, tangent, updated_states = self.owner._assemble_internal_tangent(
            self.model,
            self.dofs,
            state.displacement,
            self.committed_material_states,
            contact_diagnostics=self.contact_diagnostics,
            timing=self.timing,
        )
        values = np.asarray(internal, dtype=float)
        if self.first_internal is None:
            self.first_internal = values.copy()
        self.last_internal = values.copy()
        self.last_updated_states = copy_material_states(updated_states)
        return ContributionResponse(
            name=self.name,
            internal_force=values,
            tangent=tangent,
            trial_state=updated_states,
            diagnostics={
                "contact": dict(self.contact_diagnostics),
                "tangent_nnz": int(tangent.nnz),
            },
        )


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
        *,
        checkpoint_session: NonlinearCheckpointSession | None = None,
        initial_state: NonlinearState | None = None,
    ) -> list[NonlinearStep]:
        params = model.analysis.parameters
        controls = AdaptiveLoadControls.from_parameters(
            params,
            load_steps=load_steps,
            max_iterations=max_iterations,
        )
        starting_state = (
            initial_state.detached_copy()
            if initial_state is not None
            else NonlinearState(
                displacement=displacement,
                load_factor=0.0,
                material_state=copy_material_states(material_states),
                continuation_state={"accepted_step": 0},
            )
        )
        controller = UnifiedContinuationController(starting_state)
        self._continuation_rejection_log: list[dict[str, object]] = []
        self._continuation_commit_count = 0
        current_factor = float(controller.accepted_state.load_factor)
        step = (
            int(checkpoint_session.restart_step)
            if checkpoint_session is not None and checkpoint_session.restart_step > 0
            else int(controller.accepted_state.continuation_state.get("accepted_step", 0))
        )
        stored_increment = controller.accepted_state.continuation_state.get("next_increment")
        if isinstance(stored_increment, (int, float)) and np.isfinite(float(stored_increment)) and float(stored_increment) > 0.0:
            increment = min(controls.maximum_increment, max(controls.minimum_increment, float(stored_increment)))
        else:
            increment = controls.initial_increment
        history: list[NonlinearStep] = []
        pending_cutbacks = 0
        metadata = controller.accepted_state.accepted_increment_metadata
        self._rejected_increments = int(metadata.get("rejected_increments", 0)) if isinstance(metadata, dict) else 0
        while current_factor < 1.0 - 1.0e-12:
            proposed = min(increment, 1.0 - current_factor)
            target_factor = current_factor + proposed
            trial_state = controller.begin_trial()
            try:
                info = self._solve_load_step(
                    model,
                    dofs,
                    trial_state.displacement,
                    free,
                    target_factor * loads,
                    trial_state.material_state,
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
                    commit_to_inputs=False,
                )
            except RuntimeError as error:
                controller.rollback(
                    error,
                    path="adaptive_load_control",
                    metadata={
                        "base_load_factor": current_factor,
                        "rejected_increment": proposed,
                        "retry_increment": proposed * controls.cutback_factor,
                    },
                )
                self._continuation_rejection_log = list(controller.rejection_log)
                self._rejected_increments = controller.rejected_increments
                if not continuation_retry_permitted(error, allow_owner_policy=True):
                    raise
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
                            "continuation_commit_count": controller.transaction.commit_count,
                            "accepted_state_digest": controller.accepted_digest,
                        },
                    )
                if proposed < controls.minimum_increment:
                    raise NumericalConvergenceError(
                        "Adaptive nonlinear load stepping reached the minimum load increment.",
                        reason=NonlinearFailureReason.MIN_INCREMENT_REACHED,
                        diagnostics={
                            "minimum_increment": controls.minimum_increment,
                            "continuation_commit_count": controller.transaction.commit_count,
                            "accepted_state_digest": controller.accepted_digest,
                        },
                    )
                increment = proposed
                continue
            accepted_cutbacks = pending_cutbacks
            info = replace(info, load_step_cutbacks=accepted_cutbacks)
            pending_cutbacks = 0
            final_state = self._last_load_step_state
            if final_state is None:
                raise NumericalConvergenceError(
                    "Adaptive load-control did not expose the unified accepted trial state.",
                    reason=NonlinearFailureReason.STATE_CORRUPTION,
                )
            trial_state.displacement = final_state.displacement.copy()
            trial_state.material_state = copy_material_states(final_state.material_state)
            trial_state.load_factor = target_factor
            if info.iterations <= controls.grow_below_iterations:
                next_increment = min(controls.maximum_increment, proposed * controls.growth_factor)
            elif info.iterations >= controls.shrink_above_iterations:
                next_increment = max(controls.minimum_increment, proposed * controls.cutback_factor)
            else:
                next_increment = proposed
            trial_state.continuation_state = {
                "accepted_step": step + 1,
                "current_factor": target_factor,
                "next_increment": next_increment,
                "controller_policy": "adaptive_load_control_v1",
            }
            trial_state.accepted_increment_metadata = {
                "step": step + 1,
                "load_increment": proposed,
                "load_step_cutbacks": accepted_cutbacks,
                "rejected_increments": controller.rejected_increments,
            }
            controller.commit()
            self._continuation_commit_count = controller.transaction.commit_count
            accepted = controller.accepted_state
            displacement[:] = accepted.displacement
            commit_material_states(material_states, accepted.material_state)
            self._rejected_increments = controller.rejected_increments
            history.append(info)
            step += 1
            current_factor = target_factor
            increment = next_increment
            if checkpoint_session is not None:
                checkpoint_session.save_state(
                    step,
                    controller.accepted_state,
                    final=current_factor >= 1.0 - 1.0e-12,
                    migration_metadata={"continuation_kind": "adaptive_load_control"},
                )
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
        *,
        commit_to_inputs: bool = True,
    ) -> NonlinearStep:
        """Run standard fixed load control through :class:`UnifiedNewtonEngine`.

        ``modified_newton`` reuses the same lifecycle with its historical
        cached tangent policy; no separate global Newton loop remains.
        """

        previous_load = np.zeros_like(target_load) if previous_load is None else previous_load
        base_displacement = displacement.copy()
        force_scale = max(float(np.linalg.norm(target_load[free])), float(reference_force_norm or 0.0), 1.0)
        contact_diagnostics: dict[str, object] = {}
        phase_timing: dict[str, float | int] = {}
        contribution = _MaterialLoadControlContribution(
            self, model, dofs, contact_diagnostics, phase_timing, material_states
        )

        def finalize_trial_state(trial: NonlinearState, composite: CompositeContributionResponse) -> None:
            updated = contribution.last_updated_states
            if updated is None:
                raise NumericalConvergenceError(
                    "Unified Newton material contribution did not provide a final trial state.",
                    reason=NonlinearFailureReason.MATERIAL_UPDATE_FAILURE,
                )
            trial.material_state = copy_material_states(updated)

        active_tangent = cached_tangent

        def linear_solve(matrix: csr_matrix, rhs: np.ndarray):
            nonlocal active_tangent
            solve_matrix = matrix
            if model.analysis.method == "modified_newton":
                if active_tangent is None:
                    active_tangent = matrix.copy()
                solve_matrix = active_tangent
            try:
                increment, info = self.linear_solver.solve(solve_matrix, rhs, method=linear_method)
            except NumericalConvergenceError as exc:
                raise NumericalConvergenceError(
                    str(exc),
                    reason=NonlinearFailureReason.LINEAR_SOLVER_FAILURE,
                    diagnostics={"linear_method": linear_method},
                ) from exc
            if not info.converged:
                raise NumericalConvergenceError(
                    f"Nonlinear linearization failed with {linear_method}; residual={info.residual_norm:.6e}.",
                    reason=NonlinearFailureReason.LINEAR_SOLVER_FAILURE,
                    diagnostics={"linear_method": linear_method, "residual": info.residual_norm},
                )
            return increment, info.to_dict()

        def line_search(
            trial: NonlinearState,
            free_dofs: np.ndarray,
            correction: np.ndarray,
            target: np.ndarray,
            residual_norm: float,
        ):
            factor, reductions = line_search_factor(
                self._assemble_internal_tangent,
                model,
                dofs,
                trial.displacement,
                free_dofs,
                target,
                contribution.committed_material_states,
                correction,
                residual_norm,
                min_alpha,
                max_reductions,
                armijo,
            )
            updated = trial.displacement.copy()
            updated[free_dofs] += factor * correction
            return updated, reductions, {"factor": factor}

        result = UnifiedNewtonEngine().solve(
            initial_state=NonlinearState(
                displacement=displacement,
                load_factor=load_factor - load_increment,
                material_state=copy_material_states(material_states),
            ),
            external_force=target_load / load_factor if abs(load_factor) > 1.0e-15 else target_load,
            fixed=np.setdiff1d(np.arange(dofs.ndof, dtype=int), free),
            target_load_factors=(load_factor,),
            tolerance=tolerance,
            max_iterations=max_iterations,
            contributions=(contribution,),
            linear_solve=linear_solve,
            line_search=line_search if model.analysis.method == "newton_line_search" else None,
            finalize_trial_state=finalize_trial_state,
            force_scale=force_scale,
            solver_name="nonlinear_static_unified_newton",
            stagnation_check=False,
        )
        final_state = result.state
        self._last_load_step_state = final_state.detached_copy()
        final_displacement = final_state.displacement
        if commit_to_inputs:
            displacement[:] = final_displacement
            commit_material_states(material_states, final_state.material_state)  # type: ignore[arg-type]
        raw = result.diagnostics["increments"][0]
        assert isinstance(raw, dict)
        final_internal = contribution.last_internal
        base_internal = contribution.first_internal
        if final_internal is None or base_internal is None:
            raise NumericalConvergenceError(
                "Unified Newton did not retain final assembly diagnostics.",
                reason=NonlinearFailureReason.INVALID_ELEMENT,
            )
        internal_work, external_work, work_imbalance = incremental_work_diagnostics(
            base_displacement,
            final_displacement,
            base_internal,
            final_internal,
            previous_load,
            target_load,
        )
        factors = tuple(float(value) for value in raw.get("line_search_factors", ()))
        return NonlinearStep(
            step=step,
            load_factor=load_factor,
            iterations=max(int(raw["iterations"]) - 1, 0),
            residual_norm=float(raw["residual_final"]),
            relative_residual=float(raw["relative_residual"]),
            line_search_reductions=int(raw["line_search_iterations"]),
            min_line_search_factor=min(factors) if factors else 1.0,
            load_increment=load_increment,
            equivalent_plastic_strain_max=maximum_equivalent_plastic_strain(final_state.material_state),  # type: ignore[arg-type]
            state_committed=True,
            last_correction_norm=float(raw["last_correction_norm"]),
            cumulative_correction_norm=float(raw["cumulative_correction_norm"]),
            incremental_internal_work=internal_work,
            incremental_external_work=external_work,
            relative_work_imbalance=work_imbalance,
            load_step_cutbacks=0,
            work_diagnostics_available=True,
            residual_initial=float(raw["residual_initial"]),
            residual_history=tuple(float(value) for value in raw["residual_history"]),
            plastic_dissipation_max=maximum_plastic_dissipation(final_state.material_state),  # type: ignore[arg-type]
            assembly_seconds=float(raw["assembly_seconds"]),
            linear_solve_seconds=float(raw["linear_solve_seconds"]),
            line_search_seconds=float(raw["line_search_seconds"]),
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
            sparse_peak_chunk_bytes_estimate=int(phase_timing.get("sparse_peak_chunk_bytes_estimate", 0)),
            sparse_accumulator_levels=int(phase_timing.get("sparse_accumulator_levels", 0)),
            tangent_nnz=int(phase_timing.get("tangent_nnz", 0)),
            contact_active_contacts=tuple(int(index) for index in contact_diagnostics.get("active_contacts", [])),
            contact_gaps=tuple(float(gap) for gap in contact_diagnostics.get("gaps", [])),
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
