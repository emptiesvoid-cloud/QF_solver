"""Nonlinear static solver."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix

from solveur.core.assembler import GlobalAssembler
from solveur.core.audit import SolverAudit, static_equilibrium_summary
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError, MeshValidationError, NumericalConvergenceError
from solveur.core.linear_methods import LinearSystemSolver
from solveur.core.material_state import MaterialStateTable, commit_material_states
from solveur.core.material_state import copy_material_states
from solveur.core.material_state import initial_material_states
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear_controls import (
    AdaptiveLoadControls,
    NonlinearStep,
    incremental_work_diagnostics,
    maximum_equivalent_plastic_strain,
    validated_load_path,
)
from solveur.core.nonlinear_checkpoint import NonlinearCheckpointSession, NonlinearCheckpointStore
from solveur.core.results import SolveResult
from solveur.elements.registry import ElementRegistry
from solveur.materials.factory import MaterialFactory
from solveur.mesh.validation import MeshValidator
from solveur.post.audit import PostProcessingAuditor
from solveur.post.stress import StressPostProcessor


class NonlinearStaticSolver:
    """Load-control Newton solver for small-strain nonlinear TET4 models."""

    supported_methods = ("newton_raphson", "modified_newton", "newton_line_search", "arc_length")

    def __init__(self, checkpoint_store: NonlinearCheckpointStore | None = None) -> None:
        self.validator = MeshValidator()
        self.assembler = GlobalAssembler()
        self.linear_solver = LinearSystemSolver()
        self.post = StressPostProcessor()
        self.post_auditor = PostProcessingAuditor()
        self.checkpoint_store = checkpoint_store

    def solve(self, model: FiniteElementModel) -> SolveResult:
        if model.analysis.method not in self.supported_methods:
            raise InputValidationError(f"Unsupported nonlinear method {model.analysis.method!r}.")

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
        load_steps = max(1, int(params.get("load_steps", 1)))
        max_iterations = max(1, int(params.get("max_iterations", 25)))
        tolerance = float(params.get("tolerance", 1.0e-8))
        linear_method = str(params.get("linear_method", "direct")).lower()
        min_alpha = float(params.get("line_search_min_alpha", 1.0e-4))
        max_reductions = max(0, int(params.get("line_search_max_reductions", 12)))
        armijo = float(params.get("line_search_c", 1.0e-4))
        adaptive = bool(params.get("adaptive_load_steps", False))
        load_path = validated_load_path(params, load_steps)
        if load_path is not None and adaptive:
            raise InputValidationError("analysis.load_path is not yet compatible with adaptive_load_steps.")
        if load_path is not None and model.analysis.method == "arc_length":
            raise InputValidationError("analysis.load_path is not compatible with arc_length.")
        checkpoint_requested = any(key in params for key in ("checkpoint_path", "restart_from"))
        if checkpoint_requested and (adaptive or model.analysis.method == "arc_length"):
            raise InputValidationError("Nonlinear checkpoint/restart currently requires fixed load-control steps.")
        self._rejected_increments = 0
        self._rejection_log: list[dict[str, float]] = []
        reference_force_norm = max(float(np.linalg.norm(loads[free])), 1.0)

        displacement = np.zeros(dofs.ndof, dtype=float)
        material_states = initial_material_states(model)
        checkpoint_session: NonlinearCheckpointSession | None = None
        completed_factors: list[float] = []
        if model.analysis.method == "arc_length":
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
                "adaptive_load_steps": adaptive,
                "arc_length": model.analysis.method == "arc_length",
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
    ) -> list[NonlinearStep]:
        params = model.analysis.parameters
        target_factor = float(params.get("target_load_factor", 1.0))
        max_steps = max(1, int(params.get("max_arc_steps", max(load_steps * 4, load_steps + 1))))
        min_radius = float(params.get("min_arc_length_radius", 1.0e-10))
        current_factor = 0.0
        history: list[NonlinearStep] = []
        reference = max(float(np.linalg.norm(loads[free])), 1.0)
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
        radius = float(params.get("arc_length_radius", radius))
        load_scale = float(params.get("arc_length_load_scale", load_scale))
        previous_du = np.zeros(free.size, dtype=float)
        step = 0
        while current_factor < target_factor - 1.0e-12:
            step += 1
            if step > max_steps:
                raise NumericalConvergenceError(
                    "Arc-length continuation reached max_arc_steps before the target load factor."
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
            step_radius = max(step_radius, min_radius)
            trial = displacement.copy()
            trial_states = copy_material_states(material_states)
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
                )
            except RuntimeError:
                radius *= 0.5
                if radius < min_radius:
                    raise NumericalConvergenceError("Arc-length continuation reached the minimum radius.")
                step -= 1
                continue
            displacement[:] = trial
            commit_material_states(material_states, trial_states)
            history.append(info)
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
            raise NumericalConvergenceError("Arc-length predictor solve did not converge.")
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
        if remaining <= 0.0:
            return radius
        _, tangent, _ = self._assemble_internal_tangent(model, dofs, displacement, material_states)
        predictor, info = self.linear_solver.solve(tangent[free, :][:, free], loads[free], method=linear_method)
        if not info.converged:
            raise NumericalConvergenceError("Arc-length target-radius solve did not converge.")
        exact_radius = remaining * np.sqrt(float(predictor @ predictor) + load_scale**2)
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
    ) -> tuple[NonlinearStep, float, np.ndarray]:
        base_u = displacement.copy()
        _, tangent, _ = self._assemble_internal_tangent(model, dofs, displacement, material_states)
        predictor, info = self.linear_solver.solve(tangent[free, :][:, free], loads[free], method=linear_method)
        if not info.converged:
            raise NumericalConvergenceError("Arc-length predictor solve did not converge.")
        direction = 1.0
        if previous_du.size == predictor.size and float(previous_du @ predictor) < 0.0:
            direction = -1.0
        delta_factor = direction * radius / np.sqrt(float(predictor @ predictor) + load_scale**2)
        if base_factor + delta_factor > target_factor:
            delta_factor = target_factor - base_factor
        displacement[free] += delta_factor * predictor
        load_factor = base_factor + delta_factor
        residual_norm = float("inf")
        relative = float("inf")
        for iteration in range(1, max_iterations + 1):
            internal, tangent, updated_states = self._assemble_internal_tangent(model, dofs, displacement, material_states)
            residual = load_factor * loads - internal
            residual_norm = float(np.linalg.norm(residual[free]))
            delta_u_step = displacement[free] - base_u[free]
            delta_lambda = load_factor - base_factor
            constraint = float(delta_u_step @ delta_u_step + (load_scale * delta_lambda) ** 2 - radius**2)
            relative = max(residual_norm / reference, abs(constraint) / max(radius**2, 1.0e-30))
            if relative <= tolerance:
                commit_material_states(material_states, updated_states)
                return (
                    NonlinearStep(step, load_factor, iteration - 1, residual_norm, relative, 0, 1.0, delta_lambda),
                    load_factor,
                    delta_u_step.copy(),
                )
            correction_u, correction_lambda = self._solve_arc_length_correction(
                tangent[free, :][:, free],
                loads[free],
                residual[free],
                delta_u_step,
                delta_lambda,
                constraint,
                load_scale,
            )
            displacement[free] += correction_u
            load_factor += correction_lambda
        raise NumericalConvergenceError(
            f"Arc-length step {step} did not converge in {max_iterations} iterations; "
            f"relative residual={relative:.6e}."
        )

    @staticmethod
    def _solve_arc_length_correction(
        tangent: csr_matrix,
        reference_load: np.ndarray,
        residual: np.ndarray,
        delta_u_step: np.ndarray,
        delta_lambda: float,
        constraint: float,
        load_scale: float,
    ) -> tuple[np.ndarray, float]:
        size = residual.size
        matrix = np.zeros((size + 1, size + 1), dtype=float)
        matrix[:size, :size] = tangent.toarray()
        matrix[:size, size] = -reference_load
        matrix[size, :size] = 2.0 * delta_u_step
        matrix[size, size] = 2.0 * load_scale**2 * delta_lambda
        rhs = np.zeros(size + 1, dtype=float)
        rhs[:size] = residual
        rhs[size] = -constraint
        try:
            solution = np.linalg.solve(matrix, rhs)
        except np.linalg.LinAlgError as exc:
            raise NumericalConvergenceError("Arc-length augmented system is singular.") from exc
        if not np.all(np.isfinite(solution)):
            raise NumericalConvergenceError("Arc-length correction produced non-finite values.")
        return solution[:size], float(solution[size])

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
            trial_states = copy_material_states(material_states)
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
            except RuntimeError:
                self._rejected_increments += 1
                pending_cutbacks += 1
                rejected = proposed
                proposed *= controls.cutback_factor
                self._rejection_log.append(
                    {
                        "base_load_factor": current_factor,
                        "rejected_increment": rejected,
                        "retry_increment": proposed,
                    }
                )
                if self._rejected_increments > controls.maximum_cutbacks:
                    raise NumericalConvergenceError(
                        f"Adaptive nonlinear load stepping exceeded max_cutbacks={controls.maximum_cutbacks}."
                    )
                if proposed < controls.minimum_increment:
                    raise NumericalConvergenceError(
                        "Adaptive nonlinear load stepping reached the minimum load increment."
                    )
                increment = proposed
                continue
            info = replace(info, load_step_cutbacks=pending_cutbacks)
            pending_cutbacks = 0
            displacement[:] = trial
            commit_material_states(material_states, trial_states)
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
        total_reductions = 0
        min_factor = 1.0
        last_correction_norm = 0.0
        cumulative_correction_norm = 0.0
        for iteration in range(1, max_iterations + 1):
            internal, tangent, updated_states = self._assemble_internal_tangent(model, dofs, displacement, material_states)
            if base_internal is None:
                base_internal = internal.copy()
            residual = target_load - internal
            residual_norm = float(np.linalg.norm(residual[free]))
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
                )
            if model.analysis.method == "modified_newton":
                if cached_tangent is None:
                    cached_tangent = tangent[free, :][:, free]
                active_tangent = cached_tangent
            else:
                active_tangent = tangent[free, :][:, free]
            increment, info = self.linear_solver.solve(active_tangent, residual[free], method=linear_method)
            if not info.converged:
                raise NumericalConvergenceError(
                    f"Nonlinear linearization failed with {linear_method}; residual={info.residual_norm:.6e}."
                )
            if model.analysis.method == "newton_line_search":
                factor, reductions = self._line_search_factor(
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
            f"relative residual={relative:.6e}."
        )

    def _line_search_factor(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        displacement: np.ndarray,
        free: np.ndarray,
        target_load: np.ndarray,
        material_states: MaterialStateTable,
        increment: np.ndarray,
        residual_norm: float,
        min_alpha: float,
        max_reductions: int,
        armijo: float,
    ) -> tuple[float, int]:
        alpha = 1.0
        for reductions in range(max_reductions + 1):
            trial = displacement.copy()
            trial[free] += alpha * increment
            trial_internal, _, _ = self._assemble_internal_tangent(model, dofs, trial, material_states)
            trial_norm = float(np.linalg.norm((target_load - trial_internal)[free]))
            if trial_norm <= (1.0 - armijo * alpha) * residual_norm:
                return alpha, reductions
            alpha *= 0.5
            if alpha < min_alpha:
                break
        raise NumericalConvergenceError("Newton line-search failed to reduce the residual.")

    @staticmethod
    def _assemble_internal_tangent(
        model: FiniteElementModel,
        dofs: DofManager,
        displacement: np.ndarray,
        material_states: MaterialStateTable | None = None,
    ) -> tuple[np.ndarray, csr_matrix, MaterialStateTable]:
        rows: list[int] = []
        cols: list[int] = []
        vals: list[float] = []
        internal = np.zeros(dofs.ndof, dtype=float)
        updated_states: MaterialStateTable = {}
        for element_index, definition in enumerate(model.elements):
            spec = ElementRegistry.get(definition.type)
            material = MaterialFactory.create(model.materials[definition.material])
            element = spec.factory(material)
            if not hasattr(element, "internal_force_and_tangent"):
                raise InputValidationError(f"Element {definition.type} does not support nonlinear static analysis.")
            coords = model.nodes[list(definition.nodes)]
            edofs = []
            for node in definition.nodes:
                edofs.extend(dofs.node_indices(node, spec.dofs))
            local_u = displacement[edofs]
            states = (material_states or {}).get(element_index)
            if hasattr(element, "internal_force_tangent_state"):
                local_internal, local_tangent, element_states = element.internal_force_tangent_state(coords, local_u, states)
                if element_states:
                    updated_states[element_index] = element_states
            else:
                local_internal, local_tangent = element.internal_force_and_tangent(coords, local_u)
            if not np.all(np.isfinite(local_internal)) or not np.all(np.isfinite(local_tangent)):
                raise NumericalConvergenceError(
                    f"Element {element_index} produced a non-finite nonlinear force or tangent."
                )
            internal[edofs] += local_internal
            rr, cc = np.meshgrid(edofs, edofs, indexing="ij")
            rows.extend(rr.ravel().tolist())
            cols.extend(cc.ravel().tolist())
            vals.extend(local_tangent.ravel().tolist())
        tangent = coo_matrix((vals, (rows, cols)), shape=(dofs.ndof, dofs.ndof)).tocsr()
        return internal, tangent, updated_states
