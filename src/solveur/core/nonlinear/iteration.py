"""Newton iteration helpers shared by nonlinear drivers."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Protocol
import warnings

import numpy as np

from solveur.core.dofs import DofManager
from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.material_state import MaterialStateTable
from solveur.core.nonlinear.contracts import NonlinearFailureReason, NonlinearIterationDiagnostics
from solveur.core.nonlinear.controls import AdaptiveLoadControls
from solveur.core.nonlinear.driver import (
    ContributionResponse,
    UnifiedContinuationController,
    UnifiedNewtonEngine,
    continuation_retry_permitted,
)
from solveur.core.nonlinear.robustness import (
    LineSearchEvaluation,
    LineSearchResult,
    NonlinearRobustnessOptions,
    UnifiedNonlinearRobustnessController,
    solve_scaled_system,
)
from solveur.core.nonlinear.state import NonlinearState
from solveur.core.model import FiniteElementModel
from scipy.sparse import bmat, csr_matrix, csc_matrix
from scipy.sparse.linalg import MatrixRankWarning, spsolve


class NonlinearAssemblyProtocol(Protocol):
    """Minimal assembly contract consumed by the shared Full Newton driver."""

    ndof: int

    def assemble(
        self, displacement: np.ndarray, *, tangent_required: bool = True
    ) -> tuple[np.ndarray, csr_matrix | None]:
        """Return internal force and an optional tangent."""


class CompositeNonlinearAssembly:
    """Add sparse nonlinear contributions behind one Newton assembly contract.

    Each component may represent a material, geometric or contact contribution.
    The composite owns only accumulation and consistency checks; it does not
    interpret the component physics or duplicate a Newton loop.
    """

    def __init__(self, components: Sequence[NonlinearAssemblyProtocol]):
        if not components:
            raise ValueError("Composite nonlinear assembly requires at least one component.")
        self.components = tuple(components)
        self.ndof = int(self.components[0].ndof)
        if any(int(component.ndof) != self.ndof for component in self.components):
            raise ValueError("Composite nonlinear assembly components must share ndof.")

    def assemble(
        self, displacement: np.ndarray, *, tangent_required: bool = True
    ) -> tuple[np.ndarray, csr_matrix | None]:
        values = np.asarray(displacement, dtype=float)
        if values.shape != (self.ndof,) or not np.all(np.isfinite(values)):
            raise ValueError(f"Composite nonlinear displacement must be a finite vector of size {self.ndof}.")
        internal: np.ndarray = np.zeros(self.ndof, dtype=float)
        tangent = csr_matrix((self.ndof, self.ndof)) if tangent_required else None
        for component in self.components:
            component_internal, component_tangent = component.assemble(
                values, tangent_required=tangent_required
            )
            component_internal = np.asarray(component_internal, dtype=float)
            if component_internal.shape != (self.ndof,) or not np.all(np.isfinite(component_internal)):
                raise ValueError("Composite nonlinear component returned an invalid internal force.")
            internal += component_internal
            if tangent_required:
                if component_tangent is None or component_tangent.shape != (self.ndof, self.ndof):
                    raise ValueError("Composite nonlinear component must return a sparse tangent.")
                tangent = tangent + csr_matrix(component_tangent)
        if not np.all(np.isfinite(internal)) or (tangent is not None and not np.all(np.isfinite(tangent.data))):
            raise ValueError("Composite nonlinear assembly produced non-finite values.")
        return internal, tangent


class _AssemblyContribution:
    """Compatibility adapter from the legacy force/tangent assembly contract."""

    name = "assembly"

    def __init__(self, assembly: NonlinearAssemblyProtocol) -> None:
        self.assembly = assembly

    def evaluate(self, state: NonlinearState) -> ContributionResponse:
        internal, tangent = self.assembly.assemble(state.displacement)
        if tangent is None:
            raise ValueError("Full Newton assembly returned no tangent.")
        internal_values = np.asarray(internal, dtype=float)
        tangent_values = csr_matrix(tangent, dtype=float)
        if np.any(np.isinf(internal_values)):
            raise ValueError("Full Newton assembly returned infinite internal force.")
        if np.any(np.isnan(internal_values)):
            raise ValueError("Full Newton assembly returned nan internal force.")
        if np.any(np.isinf(tangent_values.data)):
            raise ValueError("Full Newton assembly returned infinite tangent.")
        if np.any(np.isnan(tangent_values.data)):
            raise ValueError("Full Newton assembly returned nan tangent.")
        return ContributionResponse(self.name, internal_values, tangent_values)


def solve_full_newton(
    assembly: NonlinearAssemblyProtocol,
    external: np.ndarray,
    fixed: np.ndarray,
    *,
    increments: int,
    tolerance: float,
    max_iterations: int,
    robustness_options: NonlinearRobustnessOptions | None = None,
    initial_state: NonlinearState | None = None,
    target_load_factors: Sequence[float] | None = None,
    accepted_state_callback: Callable[[int, NonlinearState], None] | None = None,
) -> tuple[np.ndarray, dict[str, object]]:
    """Compatibility adapter into the authoritative unified Newton engine."""

    if increments < 1 or max_iterations < 1:
        raise ValueError("Full Newton requires positive increments and max_iterations.")
    external_values = np.asarray(external, dtype=float)
    fixed_values = np.asarray(fixed, dtype=int)
    if external_values.shape != (assembly.ndof,) or not np.all(np.isfinite(external_values)):
        raise ValueError("Full Newton external load must be a finite vector with assembly.ndof entries.")

    def linear_solve(matrix: csr_matrix, rhs: np.ndarray) -> tuple[np.ndarray, dict[str, object] | None]:
        try:
            if robustness_options is None:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", MatrixRankWarning)
                    return spsolve(matrix, rhs), None
            correction, diagnostics = solve_scaled_system(matrix, rhs, robustness_options)
            return correction, diagnostics
        except (MatrixRankWarning, ValueError) as exc:
            raise NumericalConvergenceError(
                "Full Newton tangent is singular.",
                reason=NonlinearFailureReason.SINGULAR_TANGENT,
                diagnostics={"backend_error": str(exc)},
            ) from exc
        except RuntimeError as exc:
            raise NumericalConvergenceError(
                f"Full Newton linear solver failed: {exc}",
                reason=NonlinearFailureReason.LINEAR_SOLVER_FAILURE,
                diagnostics={"backend_error": str(exc)},
            ) from exc

    use_line_search = robustness_options is None or robustness_options.line_search != "off"
    robustness_controller = UnifiedNonlinearRobustnessController.from_options(
        robustness_options,
        line_search_enabled=use_line_search,
    )

    def line_search(
        state: NonlinearState,
        free: np.ndarray,
        correction: np.ndarray,
        target: np.ndarray,
        residual_norm: float,
    ) -> tuple[np.ndarray, int, Mapping[str, object] | None]:
        try:
            result = _line_search_assembly_with_result(
                assembly,
                state.displacement,
                free,
                correction,
                target,
                residual_norm,
                controller=robustness_controller,
            )
            updated = result.payload
            if not isinstance(updated, np.ndarray):
                raise NumericalConvergenceError(
                    "Unified line search did not return a displacement trial.",
                    reason=NonlinearFailureReason.STATE_CORRUPTION,
                )
            return updated, result.reductions, result.to_dict()
        except NumericalConvergenceError as exc:
            raise NumericalConvergenceError(
                str(exc), reason=exc.reason, diagnostics=dict(exc.diagnostics)
            ) from exc

    engine = UnifiedNewtonEngine()
    state = initial_state.detached_copy() if initial_state is not None else NonlinearState(
        np.zeros(assembly.ndof, dtype=float)
    )
    factors = (
        tuple(float(value) for value in target_load_factors)
        if target_load_factors is not None
        else tuple(float(value) for value in np.linspace(1.0 / increments, 1.0, increments))
    )
    if not factors or any(not np.isfinite(value) for value in factors):
        raise ValueError("Full Newton target load factors must be finite and non-empty.")
    try:
        result = engine.solve(
            initial_state=state,
            external_force=external_values,
            fixed=fixed_values,
            target_load_factors=factors,
            tolerance=tolerance,
            max_iterations=max_iterations,
            contributions=(_AssemblyContribution(assembly),),
            linear_solve=linear_solve,
            line_search=line_search if use_line_search else None,
            solver_name="full_newton",
            failure_diagnostics=_failure_diagnostics,
            assembly_failure_reason=_assembly_failure_reason,
            nonfinite_failure_reason=_nonfinite_failure_reason,
            robustness_controller=robustness_controller,
            accepted_state_callback=accepted_state_callback,
        )
    except NumericalConvergenceError as exc:
        # Preserve the legacy diagnostic envelope while the engine owns the
        # transaction boundary and iteration lifecycle.
        if "solver" not in exc.diagnostics:
            exc.diagnostics["solver"] = "full_newton"
        if "backend" not in exc.diagnostics:
            exc.diagnostics["backend"] = (
                "scipy.sparse.linalg.splu"
                if robustness_options is not None and robustness_options.linear_solver == "splu"
                else "scipy.sparse.linalg.spsolve"
            )
        raise

    history: list[dict[str, object]] = []
    for raw in result.diagnostics["increments"]:
        assert isinstance(raw, dict)
        raw_history = list(raw["residual_history"])
        step_diagnostics = NonlinearIterationDiagnostics(
            converged=True,
            iterations=int(raw["iterations"]),
            residual_initial=float(raw["residual_initial"]),
            residual_final=float(raw["residual_final"]),
            relative_residual=float(raw["relative_residual"]),
            tolerance=tolerance,
            solver="full_newton",
            backend=(
                "scipy.sparse.linalg.splu"
                if robustness_options is not None and robustness_options.linear_solver == "splu"
                else "scipy.sparse.linalg.spsolve"
            ),
            residual_history=tuple(float(item) for item in raw_history),
            line_search_iterations=int(raw["line_search_iterations"]),
        ).to_dict()
        step_diagnostics.update(
            {
                "assembly_seconds": raw["assembly_seconds"],
                "linear_solve_seconds": raw["linear_solve_seconds"],
                "line_search_seconds": raw["line_search_seconds"],
                "linear_system_diagnostics": raw["linear_system_diagnostics"],
                "robustness": raw.get("robustness"),
                "robustness_options": (
                    robustness_options.to_dict() if robustness_options is not None else None
                ),
            }
        )
        history.append(
            {
                "increment": raw["increment"],
                "load_factor": raw["load_factor"],
                "iterations": raw["iterations"],
                "relative_residual": raw["relative_residual"],
                "residual_initial": raw["residual_initial"],
                "residual_final": raw["residual_final"],
                "residual_history": raw_history,
                "assembly_seconds": raw["assembly_seconds"],
                "linear_solve_seconds": raw["linear_solve_seconds"],
                "line_search_seconds": raw["line_search_seconds"],
                "diagnostics": step_diagnostics,
            }
        )
    return result.state.displacement.copy(), {
        "converged": True,
        "newton_iterations": result.diagnostics["newton_iterations"],
        "final_relative_residual": result.diagnostics["final_relative_residual"],
        "increments": history,
        "robustness_policy": result.diagnostics["robustness_policy"],
        "robustness_options": robustness_options.to_dict() if robustness_options is not None else None,
    }


class _OffsetNonlinearAssembly:
    """Evaluate an assembly around a committed displacement for one retry."""

    def __init__(self, assembly: NonlinearAssemblyProtocol, offset: np.ndarray) -> None:
        self.assembly = assembly
        self.offset = np.asarray(offset, dtype=float).copy()
        self.ndof = assembly.ndof

    def assemble(
        self, displacement: np.ndarray, *, tangent_required: bool = True
    ) -> tuple[np.ndarray, csr_matrix | None]:
        values = np.asarray(displacement, dtype=float)
        if values.shape != (self.ndof,) or not np.all(np.isfinite(values)):
            raise ValueError(f"Adaptive Full Newton displacement must be a finite vector of size {self.ndof}.")
        return self.assembly.assemble(
            self.offset + values,
            tangent_required=tangent_required,
        )


def solve_adaptive_full_newton(
    assembly: NonlinearAssemblyProtocol,
    external: np.ndarray,
    fixed: np.ndarray,
    *,
    increments: int,
    tolerance: float,
    max_iterations: int,
    controls: AdaptiveLoadControls,
    robustness_options: NonlinearRobustnessOptions | None = None,
    initial_state: NonlinearState | None = None,
    accepted_state_callback: Callable[[int, NonlinearState], None] | None = None,
) -> tuple[np.ndarray, dict[str, object]]:
    """Solve a dead-load path with deterministic cutback/retry continuation.

    The existing Full Newton driver is reused for every attempt through an
    offset assembly.  Each retry therefore starts from an exact copy of the
    last accepted displacement and uses the same residual, tangent, line
    search and convergence criteria as fixed-step Full Newton.  This helper is
    intended for stateless assemblies such as the total-Lagrangian elastic
    path; stateful material routes own their transactions in
    ``NonlinearLoadControlMixin``.
    """
    if increments < 1 or max_iterations < 1:
        raise ValueError("Adaptive Full Newton requires positive increments and max_iterations.")
    external_values = np.asarray(external, dtype=float)
    if external_values.shape != (assembly.ndof,) or not np.all(np.isfinite(external_values)):
        raise ValueError(f"Adaptive Full Newton external load must be a finite vector of size {assembly.ndof}.")
    fixed = np.asarray(fixed, dtype=int)
    free = np.setdiff1d(np.arange(assembly.ndof), fixed)
    if free.size == 0:
        raise ValueError("Adaptive Full Newton requires at least one free degree of freedom.")

    starting_state = (
        initial_state.detached_copy()
        if initial_state is not None
        else NonlinearState(
            displacement=np.zeros(assembly.ndof, dtype=float),
            load_factor=0.0,
            continuation_state={"accepted_step": 0},
        )
    )
    displacement: np.ndarray = starting_state.displacement.copy()
    controller = UnifiedContinuationController(
        starting_state
    )
    history: list[dict[str, object]] = []
    rejection_log: list[dict[str, object]] = []
    current_factor = float(controller.accepted_state.load_factor)
    stored_increment = controller.accepted_state.continuation_state.get("next_increment")
    if isinstance(stored_increment, (int, float)) and np.isfinite(float(stored_increment)) and float(stored_increment) > 0.0:
        increment = min(controls.maximum_increment, max(controls.minimum_increment, float(stored_increment)))
    else:
        increment = controls.initial_increment
    accepted_step = int(controller.accepted_state.continuation_state.get("accepted_step", 0))
    total_iterations = 0
    metadata = controller.accepted_state.accepted_increment_metadata
    rejected_increments = int(metadata.get("rejected_increments", 0)) if isinstance(metadata, dict) else 0
    pending_cutbacks = 0
    while current_factor < 1.0 - 1.0e-12:
        proposed = min(increment, 1.0 - current_factor)
        target_factor = current_factor + proposed
        while True:
            trial_state = controller.begin_trial()
            attempt = _OffsetNonlinearAssembly(assembly, controller.accepted_state.displacement)
            try:
                trial_delta, attempt_diagnostics = solve_full_newton(
                    attempt,
                    target_factor * external_values,
                    fixed,
                    increments=1,
                    tolerance=tolerance,
                    max_iterations=max_iterations,
                    robustness_options=robustness_options,
                )
            except NumericalConvergenceError as exc:
                controller.rollback(
                    exc,
                    path="adaptive_full_newton",
                    metadata={
                        "adaptive_load_step": accepted_step + 1,
                        "base_load_factor": current_factor,
                        "rejected_increment": proposed,
                        "retry_increment": proposed * controls.cutback_factor,
                    },
                )
                rejected_increments = controller.rejected_increments
                pending_cutbacks += 1
                failure_reason = (
                    exc.reason.value
                    if isinstance(exc.reason, NonlinearFailureReason)
                    else (str(exc.reason) if exc.reason is not None else type(exc).__name__)
                )
                retry_increment = proposed * controls.cutback_factor
                failure_diagnostics = dict(exc.diagnostics)
                failure_diagnostics.update(
                    {
                        "adaptive_load_step": accepted_step + 1,
                        "base_load_factor": current_factor,
                        "rejected_increment": proposed,
                        "retry_increment": retry_increment,
                        "rollback_verified": True,
                        "accepted_state_digest": controller.accepted_digest,
                    }
                )
                rejection_log.append(
                    {
                        "step": accepted_step + 1,
                        "base_load_factor": current_factor,
                        "rejected_increment": proposed,
                        "retry_increment": retry_increment,
                        "failure_reason": failure_reason,
                        "failure_diagnostics": failure_diagnostics,
                        "rollback_before_retry": True,
                    }
                )
                if not continuation_retry_permitted(exc, allow_owner_policy=True):
                    raise
                if rejected_increments >= controls.maximum_cutbacks:
                    raise NumericalConvergenceError(
                        "Adaptive Full Newton exceeded the configured maximum number of cutbacks.",
                        reason=NonlinearFailureReason.MAX_ITERATIONS,
                        diagnostics={
                            **failure_diagnostics,
                            "max_cutbacks": controls.maximum_cutbacks,
                            "rejected_increments": rejected_increments,
                            "rejection_log": rejection_log,
                            "continuation_rejection_log": controller.rejection_log,
                        },
                    ) from exc
                if retry_increment < controls.minimum_increment:
                    raise NumericalConvergenceError(
                        "Adaptive Full Newton reached the minimum load increment.",
                        reason=NonlinearFailureReason.MIN_INCREMENT_REACHED,
                        diagnostics={
                            **failure_diagnostics,
                            "minimum_increment": controls.minimum_increment,
                            "rejected_increments": rejected_increments,
                            "rejection_log": rejection_log,
                            "continuation_rejection_log": controller.rejection_log,
                        },
                    ) from exc
                proposed = retry_increment
                target_factor = current_factor + proposed
                increment = proposed
                continue

            attempt_steps = attempt_diagnostics.get("increments")
            attempt_total_iterations = attempt_diagnostics.get("newton_iterations")
            if (
                not isinstance(attempt_steps, list)
                or not attempt_steps
                or not isinstance(attempt_steps[0], dict)
                or not isinstance(attempt_total_iterations, int)
            ):
                controller.rollback(
                    NumericalConvergenceError(
                        "Adaptive Full Newton received an invalid attempt diagnostic payload.",
                        reason=NonlinearFailureReason.INVALID_ELEMENT,
                    ),
                    path="adaptive_full_newton",
                    metadata={"adaptive_load_step": accepted_step + 1},
                )
                raise NumericalConvergenceError(
                    "Adaptive Full Newton received an invalid attempt diagnostic payload.",
                    reason=NonlinearFailureReason.INVALID_ELEMENT,
                    diagnostics={"adaptive_load_step": accepted_step + 1},
                )
            step_diagnostics = dict(attempt_steps[0])
            trial_state.displacement = controller.accepted_state.displacement + trial_delta
            trial_state.load_factor = target_factor
            next_iterations = int(step_diagnostics["iterations"])
            if next_iterations <= controls.grow_below_iterations:
                next_increment = min(controls.maximum_increment, proposed * controls.growth_factor)
            elif next_iterations >= controls.shrink_above_iterations:
                next_increment = max(controls.minimum_increment, proposed * controls.cutback_factor)
            else:
                next_increment = proposed
            accepted_step += 1
            trial_state.continuation_state = {
                "accepted_step": accepted_step,
                "current_factor": target_factor,
                "next_increment": next_increment,
                "controller_policy": "adaptive_load_control_v1",
            }
            trial_state.accepted_increment_metadata = {
                "step": accepted_step,
                "load_increment": proposed,
                "load_step_cutbacks": pending_cutbacks,
                "rejected_increments": controller.rejected_increments,
            }
            controller.commit()
            if accepted_state_callback is not None:
                accepted_state_callback(accepted_step, controller.accepted_state.detached_copy())
            displacement[:] = controller.accepted_state.displacement
            total_iterations += attempt_total_iterations
            step_diagnostics.update(
                {
                    "increment": accepted_step,
                    "load_factor": target_factor,
                    "load_increment": proposed,
                    "load_step_cutbacks": pending_cutbacks,
                    "state_committed": True,
                }
            )
            history.append(step_diagnostics)
            current_factor = target_factor
            pending_cutbacks = 0
            increment = next_increment
            break

    return displacement, {
        "converged": True,
        "newton_iterations": total_iterations,
        "final_relative_residual": history[-1]["relative_residual"],
        "increments": history,
        "adaptive_load_steps": True,
        "rejected_increments": rejected_increments,
        "rejection_log": rejection_log,
        "continuation_commit_count": controller.transaction.commit_count,
        "continuation_rejection_log": controller.rejection_log,
        "adaptive_controls": {
            "initial_increment": controls.initial_increment,
            "minimum_increment": controls.minimum_increment,
            "maximum_increment": controls.maximum_increment,
            "cutback_factor": controls.cutback_factor,
            "growth_factor": controls.growth_factor,
            "grow_below_iterations": controls.grow_below_iterations,
            "shrink_above_iterations": controls.shrink_above_iterations,
            "max_cutbacks": controls.maximum_cutbacks,
        },
    }


def _failure_diagnostics(
    step: int,
    iterations: int,
    residual_history: list[float],
    relative_residual: float,
    tolerance: float,
    line_search_iterations: int = 0,
) -> dict[str, object]:
    """Build the common diagnostic payload for a failed Full Newton step."""
    relative_is_finite = bool(np.isfinite(relative_residual))
    return {
        "step": step,
        "iterations": iterations,
        "residual_initial": residual_history[0] if residual_history else None,
        "residual_final": residual_history[-1] if residual_history else None,
        "relative_residual": relative_residual if relative_is_finite else None,
        "relative_residual_status": "COMPUTED" if relative_is_finite else "NOT_COMPUTABLE",
        "tolerance": tolerance,
        "solver": "full_newton",
        "backend": "scipy.sparse.linalg.spsolve",
        "residual_history": tuple(residual_history),
        "line_search_iterations": line_search_iterations,
    }


def _assembly_failure_reason(message: str) -> NonlinearFailureReason:
    """Map an assembly exception to a stable nonlinear failure category."""

    lowered = message.lower()
    if "material" in lowered or "constitutive" in lowered:
        return NonlinearFailureReason.MATERIAL_UPDATE_FAILURE
    if "contact" in lowered:
        return NonlinearFailureReason.CONTACT_UPDATE_FAILURE
    if "inf" in lowered:
        return NonlinearFailureReason.INF_DETECTED
    if "nan" in lowered or "finite" in lowered:
        return NonlinearFailureReason.NAN_DETECTED
    return NonlinearFailureReason.INVALID_ELEMENT


def _nonfinite_failure_reason(values: np.ndarray) -> NonlinearFailureReason:
    """Classify a non-finite payload, giving Inf precedence for mixed arrays."""

    return (
        NonlinearFailureReason.INF_DETECTED
        if np.any(np.isinf(np.asarray(values)))
        else NonlinearFailureReason.NAN_DETECTED
    )


def _line_search_assembly(
    assembly: NonlinearAssemblyProtocol,
    displacement: np.ndarray,
    free: np.ndarray,
    correction: np.ndarray,
    target: np.ndarray,
    residual_norm: float,
) -> np.ndarray:
    """Apply a bounded residual-decreasing line search to an assembly."""
    trial, _ = _line_search_assembly_with_diagnostics(
        assembly, displacement, free, correction, target, residual_norm
    )
    return trial


def _line_search_assembly_with_diagnostics(
    assembly: NonlinearAssemblyProtocol,
    displacement: np.ndarray,
    free: np.ndarray,
    correction: np.ndarray,
    target: np.ndarray,
    residual_norm: float,
    *,
    min_alpha: float = 0.0,
    max_reductions: int = 14,
    armijo: float | None = 0.0,
    controller: UnifiedNonlinearRobustnessController | None = None,
) -> tuple[np.ndarray, int]:
    """Return an accepted trial through the common policy loop.

    The historical defaults are intentionally retained for this compatibility
    helper.  The public ``solve_full_newton`` adapter supplies the public
    default controller explicitly, so this wrapper cannot create a second
    line-search implementation.
    """
    result = _line_search_assembly_with_result(
        assembly,
        displacement,
        free,
        correction,
        target,
        residual_norm,
        min_alpha=min_alpha,
        max_reductions=max_reductions,
        armijo_c=None if armijo is None or armijo == 0.0 else armijo,
        controller=controller,
    )
    if not isinstance(result.payload, np.ndarray):
        raise NumericalConvergenceError(
            "Common line search returned no displacement trial.",
            reason=NonlinearFailureReason.STATE_CORRUPTION,
            diagnostics=result.to_dict(),
        )
    return result.payload, result.reductions


def _line_search_assembly_with_result(
    assembly: NonlinearAssemblyProtocol,
    displacement: np.ndarray,
    free: np.ndarray,
    correction: np.ndarray,
    target: np.ndarray,
    residual_norm: float,
    *,
    min_alpha: float = 1.0e-4,
    max_reductions: int = 12,
    armijo_c: float | None = None,
    controller: UnifiedNonlinearRobustnessController | None = None,
) -> LineSearchResult:
    """Evaluate assembly merit values using the one common alpha policy."""
    policy = controller or UnifiedNonlinearRobustnessController(
        policy_source="COMPATIBILITY_ADAPTER",
        min_alpha=min_alpha,
        max_reductions=max_reductions,
        armijo_c=armijo_c,
    )

    def evaluate(alpha: float) -> LineSearchEvaluation:
        trial = displacement.copy()
        trial[free] += alpha * correction
        try:
            trial_internal, _ = assembly.assemble(trial, tangent_required=False)
        except ValueError as exc:
            return LineSearchEvaluation(
                merit=float("inf"),
                payload=trial,
                diagnostics={"assembly_rejected": True, "error": str(exc)},
            )
        trial_norm = float(np.linalg.norm((target - trial_internal)[free]))
        return LineSearchEvaluation(
            merit=trial_norm,
            payload=trial,
        )

    return policy.line_search(residual_norm, evaluate)


def line_search_factor(
    assemble: Callable[..., tuple[np.ndarray, object, MaterialStateTable]],
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
    """Compatibility wrapper over the common line-search policy."""
    result = _line_search_factor_with_result(
        assemble,
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
    if result.factor is None:
        raise NumericalConvergenceError(
            "Common Newton line search returned no accepted factor.",
            reason=NonlinearFailureReason.LINE_SEARCH_FAILURE,
            diagnostics=result.to_dict(),
        )
    return result.factor, result.reductions


def _line_search_factor_with_result(
    assemble: Callable[..., tuple[np.ndarray, object, MaterialStateTable]],
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
    *,
    controller: UnifiedNonlinearRobustnessController | None = None,
) -> LineSearchResult:
    """Run the common policy against the stateful load-control assembly."""
    policy = controller or UnifiedNonlinearRobustnessController(
        policy_source="COMPATIBILITY_ADAPTER",
        min_alpha=min_alpha,
        max_reductions=max_reductions,
        armijo_c=armijo,
    )

    def evaluate(alpha: float) -> LineSearchEvaluation:
        trial = displacement.copy()
        trial[free] += alpha * increment
        trial_internal, _, _ = assemble(model, dofs, trial, material_states)
        trial_norm = float(np.linalg.norm((target_load - trial_internal)[free]))
        return LineSearchEvaluation(merit=trial_norm, payload=alpha)

    return policy.line_search(residual_norm, evaluate)


def solve_arc_length_correction(
    tangent: csr_matrix,
    reference_load: np.ndarray,
    residual: np.ndarray,
    delta_u_step: np.ndarray,
    delta_lambda: float,
    constraint: float,
    load_scale: float,
) -> tuple[np.ndarray, float]:
    """Solve the sparse augmented correction system for arc-length continuation.

    The augmented system has one extra scalar unknown, so its sparse block
    structure is retained instead of converting the global tangent to a dense
    array. This keeps the correction compatible with the sparse backend and
    makes accidental large-system densification testable.
    """
    size = residual.size
    if tangent.shape != (size, size):
        raise ValueError("Arc-length tangent shape must match the residual dimension.")
    if reference_load.shape != (size,) or delta_u_step.shape != (size,):
        raise ValueError("Arc-length vectors must have the reduced tangent dimension.")
    matrix = bmat(
        [
            [csr_matrix(tangent), csc_matrix((-reference_load).reshape(size, 1))],
            [csr_matrix((2.0 * delta_u_step).reshape(1, size)), csc_matrix([[2.0 * load_scale**2 * delta_lambda]])],
        ],
        format="csc",
    )
    rhs = np.concatenate((np.asarray(residual, dtype=float), np.asarray([-constraint], dtype=float)))
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", MatrixRankWarning)
            solution = spsolve(matrix, rhs)
    except (MatrixRankWarning, ValueError, RuntimeError) as exc:
        raise NumericalConvergenceError(
            "Arc-length augmented system is singular.",
            reason=NonlinearFailureReason.ARC_LENGTH_FAILURE,
        ) from exc
    if not np.all(np.isfinite(solution)):
        raise NumericalConvergenceError(
            "Arc-length correction produced non-finite values.",
            reason=NonlinearFailureReason.ARC_LENGTH_FAILURE,
        )
    return solution[:size], float(solution[size])
