"""Formulation-neutral contributions, transactions and nonlinear drivers."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from time import perf_counter
from typing import Any, Protocol

import numpy as np
from scipy.sparse import csr_matrix

from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.robustness import UnifiedNonlinearRobustnessController
from solveur.core.nonlinear.state import NonlinearState, NonlinearStateTransaction
from solveur.core.nonlinear.telemetry import (
    NonlinearTelemetryObserver,
    emit_telemetry,
    process_memory_bytes,
    telemetry_event,
)
from solveur.core.nonlinear.support import _failure_reason_value


class RetryClassification(str, Enum):
    """Frozen WP01 retry classification; legacy retry behaviour is unchanged."""

    RETRYABLE = "RETRYABLE"
    NON_RETRYABLE = "NON_RETRYABLE"
    OWNER_POLICY_DEPENDENT = "OWNER_POLICY_DEPENDENT"


_RETRY_CLASSIFICATION: dict[NonlinearFailureReason, RetryClassification] = {
    NonlinearFailureReason.MAX_ITERATIONS: RetryClassification.RETRYABLE,
    NonlinearFailureReason.CONVERGENCE_STAGNATION: RetryClassification.RETRYABLE,
    NonlinearFailureReason.LINE_SEARCH_FAILURE: RetryClassification.RETRYABLE,
    NonlinearFailureReason.CONTACT_UPDATE_FAILURE: RetryClassification.RETRYABLE,
    NonlinearFailureReason.CONTACT_PENETRATION_EXCESSIVE: RetryClassification.RETRYABLE,
    NonlinearFailureReason.ARC_LENGTH_FAILURE: RetryClassification.RETRYABLE,
    NonlinearFailureReason.SINGULAR_TANGENT: RetryClassification.OWNER_POLICY_DEPENDENT,
    NonlinearFailureReason.LINEAR_SOLVER_FAILURE: RetryClassification.OWNER_POLICY_DEPENDENT,
    NonlinearFailureReason.MATERIAL_UPDATE_FAILURE: RetryClassification.NON_RETRYABLE,
    NonlinearFailureReason.STATE_CORRUPTION: RetryClassification.NON_RETRYABLE,
    NonlinearFailureReason.NAN_DETECTED: RetryClassification.NON_RETRYABLE,
    NonlinearFailureReason.INF_DETECTED: RetryClassification.NON_RETRYABLE,
    NonlinearFailureReason.INVALID_ELEMENT: RetryClassification.NON_RETRYABLE,
    NonlinearFailureReason.MIN_INCREMENT_REACHED: RetryClassification.NON_RETRYABLE,
    NonlinearFailureReason.CHECKPOINT_FAILURE: RetryClassification.NON_RETRYABLE,
    NonlinearFailureReason.BUCKLING_FAILURE: RetryClassification.NON_RETRYABLE,
}


def retry_classification(reason: NonlinearFailureReason) -> RetryClassification:
    """Return the frozen policy classification for one canonical reason."""
    return _RETRY_CLASSIFICATION[reason]


def continuation_retry_classification(error: BaseException) -> RetryClassification:
    """Classify a continuation failure without weakening the frozen policy."""

    reason = getattr(error, "reason", None)
    if isinstance(reason, NonlinearFailureReason):
        return retry_classification(reason)
    return RetryClassification.OWNER_POLICY_DEPENDENT


def continuation_retry_permitted(
    error: BaseException,
    *,
    allow_owner_policy: bool = False,
) -> bool:
    """Return whether a continuation controller may retry one failed trial."""

    classification = continuation_retry_classification(error)
    return classification is RetryClassification.RETRYABLE or (
        allow_owner_policy and classification is RetryClassification.OWNER_POLICY_DEPENDENT
    )


class UnifiedContinuationController:
    """Own accepted-state publication and retry diagnostics for continuations.

    Standard Newton and arc-length use different correction kernels, but both
    pass their accepted state through this controller.  A retry policy may
    adjust a *next-trial controller variable* (load increment or radius), but
    it cannot mutate the accepted composite state after rollback.
    """

    def __init__(self, initial_state: NonlinearState) -> None:
        self.transaction = NonlinearStateTransaction(initial_state)
        self.rejected_increments = 0
        self.rejection_log: list[dict[str, Any]] = []

    @property
    def accepted_state(self) -> NonlinearState:
        return self.transaction.accepted_state

    @property
    def accepted_digest(self) -> str:
        return self.transaction.accepted_digest

    @property
    def accepted_component_digests(self) -> dict[str, str]:
        return self.transaction.accepted_component_digests

    @property
    def trial_state(self) -> NonlinearState | None:
        return self.transaction.trial_state

    def begin_trial(self) -> NonlinearState:
        """Start a detached trial from the complete accepted composite state."""

        return self.transaction.begin_trial()

    def commit(self, *, accepted_increment_metadata: Mapping[str | int, Any] | None = None) -> NonlinearState:
        """Atomically publish a trial and optional accepted-step metadata."""

        trial = self.transaction.trial_state
        if trial is None:
            raise RuntimeError("A continuation commit requires an open trial.")
        if accepted_increment_metadata is not None:
            trial.accepted_increment_metadata = deepcopy(dict(accepted_increment_metadata))
        return self.transaction.commit()

    def rollback(
        self,
        error: BaseException,
        *,
        path: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> RetryClassification:
        """Rollback and prove the accepted composite digest did not change."""

        before = self.accepted_digest
        before_components = self.accepted_component_digests
        before_load_factor = self.accepted_state.load_factor
        before_continuation = deepcopy(dict(self.accepted_state.continuation_state))
        classification = continuation_retry_classification(error)
        self.transaction.rollback()
        after = self.accepted_digest
        after_components = self.accepted_component_digests
        if before != after:
            raise NumericalConvergenceError(
                "Continuation rollback changed the accepted composite state.",
                reason=NonlinearFailureReason.STATE_CORRUPTION,
                diagnostics={
                    "path": path,
                    "accepted_digest_before": before,
                    "accepted_digest_after": after,
                },
            ) from error
        self.rejected_increments += 1
        entry: dict[str, Any] = dict(metadata or {})
        entry.update(
            {
                "path": path,
                "failure_reason": _failure_reason_value(error),
                "retry_classification": classification.value,
                "accepted_digest_before": before,
                "accepted_digest_after": after,
                "accepted_component_digests_before": before_components,
                "accepted_component_digests_after": after_components,
                "accepted_load_factor_before": before_load_factor,
                "accepted_load_factor_after": self.accepted_state.load_factor,
                "accepted_continuation_before": before_continuation,
                "accepted_continuation_after": deepcopy(dict(self.accepted_state.continuation_state)),
                "rollback_before_retry": True,
            }
        )
        diagnostics = getattr(error, "diagnostics", None)
        if isinstance(diagnostics, Mapping):
            entry["failure_diagnostics"] = deepcopy(dict(diagnostics))
        self.rejection_log.append(entry)
        return classification


@dataclass(frozen=True)
class ContributionResponse:
    """Immutable response from one formulation-neutral nonlinear contribution."""

    name: str
    internal_force: np.ndarray
    tangent: csr_matrix
    trial_state: Mapping[str | int, Any] | None = None
    diagnostics: Mapping[str, Any] = field(default_factory=dict)
    admissible: bool = True
    failure_reason: NonlinearFailureReason | None = None

    def __post_init__(self) -> None:
        values = np.array(self.internal_force, dtype=float, copy=True)
        matrix = csr_matrix(self.tangent, dtype=float, copy=True)
        if values.ndim != 1 or not np.all(np.isfinite(values)):
            raise ValueError("ContributionResponse internal_force must be a finite vector.")
        if matrix.shape != (values.size, values.size) or not np.all(np.isfinite(matrix.data)):
            raise ValueError("ContributionResponse tangent must be finite and square for internal_force.")
        if not self.name:
            raise ValueError("ContributionResponse name must be non-empty.")
        if self.failure_reason is not None and not isinstance(self.failure_reason, NonlinearFailureReason):
            raise TypeError("ContributionResponse failure_reason must use NonlinearFailureReason.")
        object.__setattr__(self, "internal_force", values)
        object.__setattr__(self, "tangent", matrix)
        object.__setattr__(self, "trial_state", None if self.trial_state is None else deepcopy(dict(self.trial_state)))
        object.__setattr__(self, "diagnostics", deepcopy(dict(self.diagnostics)))


class NonlinearContribution(Protocol):
    """Physics-agnostic contribution evaluated against a detached trial state."""

    def evaluate(self, state: NonlinearState) -> ContributionResponse:
        """Return force/tangent/state/diagnostics without committing global state."""


@dataclass(frozen=True)
class CompositeContributionResponse:
    """Accumulated force/tangent with namespaced diagnostics and trial updates."""

    internal_force: np.ndarray
    tangent: csr_matrix
    trial_state_updates: Mapping[str, Mapping[str | int, Any]]
    diagnostics: Mapping[str, Mapping[str, Any]]
    admissible: bool
    failure_reason: NonlinearFailureReason | None


def compose_contribution_responses(responses: Sequence[ContributionResponse]) -> CompositeContributionResponse:
    """Compose contribution responses without interpreting their physics."""
    if not responses:
        raise ValueError("At least one nonlinear contribution response is required.")
    size = responses[0].internal_force.size
    names = [response.name for response in responses]
    if len(set(names)) != len(names):
        raise ValueError("Nonlinear contribution response names must be unique.")
    internal: np.ndarray = np.zeros(size, dtype=float)
    tangent = csr_matrix((size, size), dtype=float)
    updates: dict[str, Mapping[str | int, Any]] = {}
    diagnostics: dict[str, Mapping[str, Any]] = {}
    admissible = True
    failure_reason: NonlinearFailureReason | None = None
    for response in responses:
        if response.internal_force.size != size or response.tangent.shape != (size, size):
            raise ValueError("Nonlinear contribution responses must share vector and tangent dimensions.")
        internal += response.internal_force
        tangent = tangent + response.tangent
        if response.trial_state is not None:
            updates[response.name] = deepcopy(dict(response.trial_state))
        diagnostics[response.name] = deepcopy(dict(response.diagnostics))
        admissible = admissible and response.admissible
        if failure_reason is None and response.failure_reason is not None:
            failure_reason = response.failure_reason
    return CompositeContributionResponse(
        internal_force=internal,
        tangent=tangent.tocsr(),
        trial_state_updates=updates,
        diagnostics=diagnostics,
        admissible=admissible,
        failure_reason=failure_reason,
    )


def canonical_residual(
    external_force: np.ndarray, load_factor: float, response: CompositeContributionResponse
) -> np.ndarray:
    """Return the frozen WP01 diagnostic residual on all degrees of freedom."""
    external = np.asarray(external_force, dtype=float)
    if external.shape != response.internal_force.shape or not np.all(np.isfinite(external)):
        raise ValueError("External force must be finite and match the composite contribution dimensions.")
    if not np.isfinite(load_factor):
        raise ValueError("Load factor must be finite.")
    return float(load_factor) * external - response.internal_force


@dataclass(frozen=True)
class DriverDecision:
    """Formulation-neutral decision supplied after correction/trial update."""

    accepted: bool
    reason: NonlinearFailureReason | None = None
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.accepted and self.reason is not None:
            raise ValueError("An accepted nonlinear driver decision cannot carry a failure reason.")


@dataclass(frozen=True)
class DriverLifecycleResult:
    """Deterministic result of one authoritative increment lifecycle."""

    accepted: bool
    reason: NonlinearFailureReason | None
    retry_class: RetryClassification | None
    response: CompositeContributionResponse
    diagnostics: Mapping[str, Any]
    lifecycle: tuple[str, ...]
    commit_count: int


TrialUpdate = Callable[[NonlinearState, CompositeContributionResponse], None]
ConvergenceDecision = Callable[[NonlinearState, CompositeContributionResponse], DriverDecision]


class UnifiedNonlinearDriverFoundation:
    """Own the non-physics increment lifecycle for future nonlinear migration.

    It intentionally performs no Newton linear solve or formulation evaluation.
    A later driver migration supplies correction/convergence callbacks while
    this class retains ownership of trial isolation, acceptance and rollback.
    """

    def execute_increment(
        self,
        transaction: NonlinearStateTransaction,
        contributions: Sequence[NonlinearContribution],
        *,
        correction: TrialUpdate | None = None,
        trial_update: TrialUpdate | None = None,
        convergence: ConvergenceDecision,
    ) -> DriverLifecycleResult:
        """Execute one trial/evaluate/update/decision/commit-or-rollback lifecycle."""
        lifecycle = ["begin_trial"]
        trial = transaction.begin_trial()
        responses = tuple(contribution.evaluate(trial) for contribution in contributions)
        composite = compose_contribution_responses(responses)
        lifecycle.append("evaluate")

        if composite.failure_reason is not None:
            return self._reject(transaction, composite, composite.failure_reason, lifecycle, "contribution_failure")
        if not composite.admissible:
            return self._reject(
                transaction,
                composite,
                NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                lifecycle,
                "contribution_inadmissible",
            )

        if correction is not None:
            correction(trial, composite)
        lifecycle.append("correction")
        if trial_update is not None:
            trial_update(trial, composite)
        lifecycle.append("trial_update")
        decision = convergence(trial, composite)
        lifecycle.append("convergence")
        if not decision.accepted:
            reason = decision.reason or NonlinearFailureReason.MAX_ITERATIONS
            return self._reject(transaction, composite, reason, lifecycle, dict(decision.diagnostics))

        transaction.commit()
        lifecycle.append("commit")
        return DriverLifecycleResult(
            accepted=True,
            reason=None,
            retry_class=None,
            response=composite,
            diagnostics={"decision": dict(decision.diagnostics)},
            lifecycle=tuple(lifecycle),
            commit_count=transaction.commit_count,
        )

    @staticmethod
    def _reject(
        transaction: NonlinearStateTransaction,
        response: CompositeContributionResponse,
        reason: NonlinearFailureReason,
        lifecycle: list[str],
        diagnostics: Mapping[str, Any] | str,
    ) -> DriverLifecycleResult:
        transaction.rollback()
        lifecycle.append("rollback")
        details: dict[str, Any] = (
            {"decision": diagnostics} if isinstance(diagnostics, str) else {"decision": dict(diagnostics)}
        )
        return DriverLifecycleResult(
            accepted=False,
            reason=reason,
            retry_class=retry_classification(reason),
            response=response,
            diagnostics=details,
            lifecycle=tuple(lifecycle),
            commit_count=transaction.commit_count,
        )


@dataclass(frozen=True)
class UnifiedNewtonResult:
    """Result of the formulation-neutral fixed load-control Newton engine."""

    state: NonlinearState
    diagnostics: Mapping[str, Any]


LinearSolve = Callable[[csr_matrix, np.ndarray], tuple[np.ndarray, Mapping[str, Any] | None]]
LineSearch = Callable[
    [NonlinearState, np.ndarray, np.ndarray, np.ndarray, float], tuple[np.ndarray, int, Mapping[str, Any] | None]
]
TrialStateApplier = Callable[[NonlinearState, CompositeContributionResponse], None]
FinalTrialStateApplier = Callable[[NonlinearState, CompositeContributionResponse], None]
FailureDiagnostics = Callable[
    [int, int, list[float], float, float, int], dict[str, Any]
]
AssemblyFailureReason = Callable[[str], NonlinearFailureReason]
NonFiniteFailureReason = Callable[[np.ndarray], NonlinearFailureReason]


class UnifiedNewtonEngine:
    """Authoritative formulation-neutral Newton lifecycle for fixed load control.

    The engine owns one global increment/iteration lifecycle.  Contributions
    only evaluate force, tangent and detached trial responses; they never
    publish accepted state.  Legacy routes provide adapters for their existing
    linear backend and line-search implementation, which keeps this class free
    of constitutive, geometric and contact mathematics.
    """

    def solve(
        self,
        *,
        initial_state: NonlinearState,
        external_force: np.ndarray,
        fixed: np.ndarray,
        target_load_factors: Sequence[float],
        tolerance: float,
        max_iterations: int,
        contributions: Sequence[NonlinearContribution],
        linear_solve: LinearSolve,
        line_search: LineSearch | None = None,
        apply_trial_state: TrialStateApplier | None = None,
        finalize_trial_state: FinalTrialStateApplier | None = None,
        force_scale: float | None = None,
        solver_name: str = "unified_newton",
        failure_diagnostics: FailureDiagnostics | None = None,
        assembly_failure_reason: AssemblyFailureReason | None = None,
        nonfinite_failure_reason: NonFiniteFailureReason | None = None,
        stagnation_check: bool = True,
        robustness_controller: UnifiedNonlinearRobustnessController | None = None,
        accepted_state_callback: Callable[[int, NonlinearState], None] | None = None,
        telemetry_observer: NonlinearTelemetryObserver | None = None,
    ) -> UnifiedNewtonResult:
        """Solve the requested fixed load factors through one transaction lifecycle."""

        if tolerance <= 0.0 or not np.isfinite(tolerance):
            raise ValueError("Unified Newton tolerance must be finite and positive.")
        if max_iterations < 1:
            raise ValueError("Unified Newton requires max_iterations >= 1.")
        if not contributions:
            raise ValueError("Unified Newton requires at least one contribution.")
        external = np.asarray(external_force, dtype=float)
        fixed_values = np.asarray(fixed, dtype=int)
        if external.ndim != 1 or not np.all(np.isfinite(external)):
            raise ValueError("Unified Newton external force must be a finite one-dimensional vector.")
        if initial_state.displacement.shape != external.shape:
            raise ValueError("Unified Newton state and external force dimensions must match.")
        free = np.setdiff1d(np.arange(external.size, dtype=int), fixed_values)
        if free.size == 0:
            raise ValueError("Unified Newton requires at least one free degree of freedom.")
        factors = tuple(float(value) for value in target_load_factors)
        if not factors or any(not np.isfinite(value) for value in factors):
            raise ValueError("Unified Newton target load factors must be finite and non-empty.")

        policy = robustness_controller or UnifiedNonlinearRobustnessController(
            stagnation_enabled=stagnation_check,
            line_search_enabled=line_search is not None,
        )

        transaction = NonlinearStateTransaction(initial_state)
        history: list[dict[str, Any]] = []
        total_iterations = 0
        for step, load_factor in enumerate(factors, start=1):
            try:
                transaction.begin_trial()
                step_result, step_iterations = self._solve_increment(
                    transaction=transaction,
                    external=external,
                    free=free,
                    load_factor=load_factor,
                    step=step,
                    tolerance=tolerance,
                    max_iterations=max_iterations,
                    contributions=contributions,
                    linear_solve=linear_solve,
                    line_search=line_search,
                    apply_trial_state=apply_trial_state,
                    finalize_trial_state=finalize_trial_state,
                    force_scale=force_scale,
                    solver_name=solver_name,
                    failure_diagnostics=failure_diagnostics,
                    assembly_failure_reason=assembly_failure_reason,
                    nonfinite_failure_reason=nonfinite_failure_reason,
                    robustness_controller=policy,
                    telemetry_observer=telemetry_observer,
                )
                if accepted_state_callback is not None:
                    accepted_state_callback(step, transaction.accepted_state.detached_copy())
                emit_telemetry(
                    telemetry_observer,
                    telemetry_event(
                        "STEP_ACCEPTED",
                        load_step=step,
                        target_load_factor=load_factor,
                        current_load_factor=transaction.accepted_state.load_factor,
                        iterations=step_result["iterations"],
                        step_wall_time_s=step_result["assembly_seconds"]
                        + step_result["linear_solve_seconds"]
                        + step_result["line_search_seconds"],
                        matrix_nnz=(step_result["linear_system_diagnostics"][-1].get("matrix_nnz")
                                    if step_result["linear_system_diagnostics"] else None),
                        status="ACCEPTED",
                    ),
                )
                history.append(step_result)
                total_iterations += step_iterations
            except NumericalConvergenceError as exc:
                if transaction.trial_state is not None:
                    transaction.rollback()
                emit_telemetry(
                    telemetry_observer,
                    telemetry_event(
                        "STEP_FAILED",
                        load_step=step,
                        target_load_factor=load_factor,
                        current_load_factor=transaction.accepted_state.load_factor,
                        reason=exc.reason.value if exc.reason is not None else None,
                        residual=exc.diagnostics.get("final_relative_residual"),
                        iteration=exc.diagnostics.get("iteration"),
                        line_search_state=exc.diagnostics.get("line_search"),
                        status="FAILED",
                    ),
                )
                emit_telemetry(
                    telemetry_observer,
                    telemetry_event("SOLVE_FAILED", load_step=step, reason=exc.reason.value if exc.reason else None, status="FAILED"),
                )
                raise
            except (TypeError, ValueError, FloatingPointError) as exc:
                if transaction.trial_state is not None:
                    transaction.rollback()
                raise NumericalConvergenceError(
                    f"Unified Newton increment {step} failed: {exc}",
                    reason=NonlinearFailureReason.INVALID_ELEMENT,
                    diagnostics={"step": step, "solver": solver_name},
                ) from exc

        accepted = transaction.accepted_state.detached_copy()
        emit_telemetry(
            telemetry_observer,
            telemetry_event(
                "SOLVE_COMPLETED",
                load_step=len(factors),
                current_load_factor=accepted.load_factor,
                newton_iterations=total_iterations,
                status="COMPLETED",
            ),
        )
        return UnifiedNewtonResult(
            state=accepted,
            diagnostics={
                "converged": True,
                "newton_iterations": total_iterations,
                "final_relative_residual": history[-1]["relative_residual"],
                "increments": history,
                "solver": solver_name,
                "state_digest": accepted.digest,
                "commit_count": transaction.commit_count,
                "robustness_policy": policy.configuration_diagnostics(),
            },
        )

    def _solve_increment(
        self,
        *,
        transaction: NonlinearStateTransaction,
        external: np.ndarray,
        free: np.ndarray,
        load_factor: float,
        step: int,
        tolerance: float,
        max_iterations: int,
        contributions: Sequence[NonlinearContribution],
        linear_solve: LinearSolve,
        line_search: LineSearch | None,
        apply_trial_state: TrialStateApplier | None,
        finalize_trial_state: FinalTrialStateApplier | None,
        force_scale: float | None,
        solver_name: str,
        failure_diagnostics: FailureDiagnostics | None,
        assembly_failure_reason: AssemblyFailureReason | None,
        nonfinite_failure_reason: NonFiniteFailureReason | None,
        robustness_controller: UnifiedNonlinearRobustnessController,
        telemetry_observer: NonlinearTelemetryObserver | None,
    ) -> tuple[dict[str, Any], int]:
        trial = transaction.trial_state
        if trial is None:
            raise RuntimeError("Unified Newton increment requires an open transaction trial.")
        target = load_factor * external
        scale = max(
            float(np.linalg.norm(target[free])),
            float(force_scale or 0.0),
            1.0,
        )
        residual_history: list[float] = []
        line_search_iterations = 0
        assembly_seconds = 0.0
        linear_solve_seconds = 0.0
        line_search_seconds = 0.0
        linear_diagnostics: list[dict[str, Any]] = []
        line_search_factors: list[float] = []
        line_search_events: list[dict[str, Any]] = []
        correction_norms: list[float] = []
        contribution_diagnostics: Mapping[str, Mapping[str, Any]] = {}
        stagnation_diagnostics: dict[str, Any] | None = None

        def add_robustness_diagnostics(details: dict[str, Any]) -> dict[str, Any]:
            details["robustness"] = robustness_controller.configuration_diagnostics(
                stagnation=stagnation_diagnostics,
                line_search=line_search_events,
            )
            return details

        for iteration in range(1, max_iterations + 1):
            iteration_started = perf_counter()
            assembly_started = perf_counter()
            try:
                responses = tuple(contribution.evaluate(trial) for contribution in contributions)
                composite = compose_contribution_responses(responses)
                contribution_diagnostics = composite.diagnostics
                if apply_trial_state is not None:
                    apply_trial_state(trial, composite)
            except NumericalConvergenceError:
                raise
            except (TypeError, ValueError, FloatingPointError) as exc:
                diagnostics = self._failure_diagnostics(
                    failure_diagnostics, step, iteration, residual_history, float("inf"), tolerance, line_search_iterations
                )
                add_robustness_diagnostics(diagnostics)
                diagnostics["assembly_error"] = str(exc)
                reason = (
                    assembly_failure_reason(str(exc))
                    if assembly_failure_reason is not None
                    else NonlinearFailureReason.INVALID_ELEMENT
                )
                raise NumericalConvergenceError(
                    f"Unified Newton assembly failed at increment {step}: {exc}",
                    reason=reason,
                    diagnostics=diagnostics,
                ) from exc
            finally:
                assembly_elapsed = perf_counter() - assembly_started
                assembly_seconds += assembly_elapsed

            if composite.failure_reason is not None:
                diagnostics = self._failure_diagnostics(
                    failure_diagnostics, step, iteration, residual_history, float("inf"), tolerance, line_search_iterations
                )
                add_robustness_diagnostics(diagnostics)
                diagnostics["contribution_diagnostics"] = dict(contribution_diagnostics)
                raise NumericalConvergenceError(
                    f"Unified Newton contribution failed at increment {step}.",
                    reason=composite.failure_reason,
                    diagnostics=diagnostics,
                )
            if not composite.admissible:
                diagnostics = self._failure_diagnostics(
                    failure_diagnostics, step, iteration, residual_history, float("inf"), tolerance, line_search_iterations
                )
                add_robustness_diagnostics(diagnostics)
                diagnostics["contribution_diagnostics"] = dict(contribution_diagnostics)
                raise NumericalConvergenceError(
                    f"Unified Newton contribution was inadmissible at increment {step}.",
                    reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                    diagnostics=diagnostics,
                )

            residual = load_factor * external - composite.internal_force
            if not np.all(np.isfinite(residual)):
                reason = (
                    nonfinite_failure_reason(residual)
                    if nonfinite_failure_reason is not None
                    else NonlinearFailureReason.NAN_DETECTED
                )
                diagnostics = self._failure_diagnostics(
                    failure_diagnostics, step, iteration, residual_history, float("inf"), tolerance, line_search_iterations
                )
                add_robustness_diagnostics(diagnostics)
                raise NumericalConvergenceError(
                    f"Unified Newton residual is non-finite at increment {step}.",
                    reason=reason,
                    diagnostics=diagnostics,
                )
            residual_norm = float(np.linalg.norm(residual[free]))
            relative = residual_norm / scale
            residual_history.append(residual_norm)
            stagnation_decision = robustness_controller.stagnation_decision(
                residual_history,
                converged=relative <= tolerance,
                convergence_tolerance=tolerance,
            )
            stagnation_diagnostics = stagnation_decision.to_dict()
            if relative <= tolerance:
                if finalize_trial_state is not None:
                    finalize_trial_state(trial, composite)
                trial.load_factor = load_factor
                transaction.commit()
                rss_bytes, private_bytes = process_memory_bytes()
                emit_telemetry(
                    telemetry_observer,
                    telemetry_event(
                        "ITERATION",
                        load_step=step,
                        target_load_factor=load_factor,
                        current_load_factor=load_factor,
                        newton_iteration=iteration,
                        residual_norm=residual_norm,
                        relative_residual=relative,
                        correction_norm=0.0,
                        line_search_alpha=1.0,
                        line_search_iterations=0,
                        assembly_time_s=assembly_elapsed,
                        linear_solve_time_s=0.0,
                        iteration_wall_time_s=perf_counter() - iteration_started,
                        matrix_shape=None,
                        matrix_nnz=None,
                        linear_backend=None,
                        linear_method=None,
                        krylov_iterations=0,
                        linear_relative_residual=None,
                        fallback_used=False,
                        RSS_bytes=rss_bytes,
                        private_or_USS_bytes=private_bytes,
                        status="CONVERGED",
                    ),
                )
                return (
                    {
                        "increment": step,
                        "load_factor": load_factor,
                        "iterations": iteration,
                        "relative_residual": relative,
                        "residual_initial": residual_history[0],
                        "residual_final": residual_history[-1],
                        "residual_history": tuple(residual_history),
                        "line_search_iterations": line_search_iterations,
                        "line_search_factors": tuple(line_search_factors),
                        "last_correction_norm": correction_norms[-1] if correction_norms else 0.0,
                        "cumulative_correction_norm": float(sum(correction_norms)),
                        "assembly_seconds": assembly_seconds,
                        "linear_solve_seconds": linear_solve_seconds,
                        "line_search_seconds": line_search_seconds,
                        "linear_system_diagnostics": linear_diagnostics,
                        "contribution_diagnostics": dict(contribution_diagnostics),
                        "robustness": robustness_controller.configuration_diagnostics(
                            stagnation=stagnation_diagnostics,
                            line_search=line_search_events,
                        ),
                        "state_committed": True,
                    },
                    max(iteration - 1, 0),
                )
            if stagnation_decision.reason is NonlinearFailureReason.CONVERGENCE_STAGNATION:
                diagnostics = self._failure_diagnostics(
                    failure_diagnostics, step, iteration, residual_history, relative, tolerance, line_search_iterations
                )
                add_robustness_diagnostics(diagnostics)
                raise NumericalConvergenceError(
                    f"Unified Newton stagnated at increment {step}; relative residual={relative:.6e}.",
                    reason=NonlinearFailureReason.CONVERGENCE_STAGNATION,
                    diagnostics=diagnostics,
                )

            reduced_tangent = composite.tangent[free, :][:, free]
            linear_started = perf_counter()
            try:
                correction, solve_diagnostics = linear_solve(reduced_tangent, residual[free])
            except NumericalConvergenceError as exc:
                diagnostics = self._failure_diagnostics(
                    failure_diagnostics,
                    step,
                    iteration,
                    residual_history,
                    relative,
                    tolerance,
                    line_search_iterations,
                )
                diagnostics.update(exc.diagnostics)
                add_robustness_diagnostics(diagnostics)
                rss_bytes, private_bytes = process_memory_bytes()
                emit_telemetry(
                    telemetry_observer,
                    telemetry_event(
                        "ITERATION",
                        load_step=step,
                        target_load_factor=load_factor,
                        current_load_factor=transaction.accepted_state.load_factor,
                        newton_iteration=iteration,
                        residual_norm=residual_norm,
                        relative_residual=relative,
                        correction_norm=None,
                        line_search_alpha=None,
                        line_search_iterations=line_search_iterations,
                        assembly_time_s=assembly_elapsed,
                        linear_solve_time_s=perf_counter() - linear_started,
                        iteration_wall_time_s=perf_counter() - iteration_started,
                        matrix_shape=list(reduced_tangent.shape),
                        matrix_nnz=int(reduced_tangent.nnz),
                        linear_backend=exc.diagnostics.get("linear_backend"),
                        linear_method=exc.diagnostics.get("linear_method"),
                        krylov_iterations=exc.diagnostics.get("krylov_iterations"),
                        linear_relative_residual=exc.diagnostics.get("linear_relative_residual"),
                        fallback_used=exc.diagnostics.get("fallback_used", False),
                        RSS_bytes=rss_bytes,
                        private_or_USS_bytes=private_bytes,
                        status="LINEAR_FAILED",
                    ),
                )
                raise NumericalConvergenceError(
                    str(exc), reason=exc.reason, diagnostics=diagnostics
                ) from exc
            finally:
                linear_elapsed = perf_counter() - linear_started
                linear_solve_seconds += linear_elapsed
            if solve_diagnostics is not None:
                linear_diagnostics.append(dict(solve_diagnostics))
            correction = np.asarray(correction, dtype=float)
            if correction.shape != free.shape or not np.all(np.isfinite(correction)):
                reason = (
                    nonfinite_failure_reason(correction)
                    if nonfinite_failure_reason is not None
                    else NonlinearFailureReason.NAN_DETECTED
                )
                diagnostics = self._failure_diagnostics(
                    failure_diagnostics, step, iteration, residual_history, relative, tolerance, line_search_iterations
                )
                add_robustness_diagnostics(diagnostics)
                raise NumericalConvergenceError(
                    f"Unified Newton correction is non-finite at increment {step}.",
                    reason=reason,
                    diagnostics=diagnostics,
                )

            before_displacement = trial.displacement[free].copy()
            line_diagnostics: Mapping[str, Any] | None = None
            if line_search is None:
                trial.displacement[free] += correction
                reductions = 0
            else:
                line_started = perf_counter()
                try:
                    updated, reductions, line_diagnostics = line_search(
                        trial, free, correction, target, residual_norm
                    )
                except NumericalConvergenceError as exc:
                    diagnostics = self._failure_diagnostics(
                        failure_diagnostics,
                        step,
                        iteration,
                        residual_history,
                        relative,
                        tolerance,
                        line_search_iterations,
                    )
                    diagnostics.update(exc.diagnostics)
                    if isinstance(exc.diagnostics, Mapping) and exc.reason is NonlinearFailureReason.LINE_SEARCH_FAILURE:
                        line_search_events.append(dict(exc.diagnostics))
                    add_robustness_diagnostics(diagnostics)
                    raise NumericalConvergenceError(
                        str(exc), reason=exc.reason, diagnostics=diagnostics
                    ) from exc
                line_search_seconds += perf_counter() - line_started
                trial.displacement = np.array(updated, dtype=float, copy=True)
                if line_diagnostics is not None:
                    line_search_events.append(dict(line_diagnostics))
                    contribution_diagnostics = {
                        **dict(contribution_diagnostics),
                        "line_search": dict(line_diagnostics),
                    }
                    factor = line_diagnostics.get("factor")
                    if factor is not None:
                        line_search_factors.append(float(factor))
            correction_norms.append(float(np.linalg.norm(trial.displacement[free] - before_displacement)))
            line_search_iterations += int(reductions)
            rss_bytes, private_bytes = process_memory_bytes()
            effective_alpha = 1.0
            if line_diagnostics is not None:
                effective_alpha = float(line_diagnostics.get("factor", 1.0))
            diagnostics_values = dict(solve_diagnostics or {})
            emit_telemetry(
                telemetry_observer,
                telemetry_event(
                    "ITERATION",
                    load_step=step,
                    target_load_factor=load_factor,
                    current_load_factor=transaction.accepted_state.load_factor,
                    newton_iteration=iteration,
                    residual_norm=residual_norm,
                    relative_residual=relative,
                    correction_norm=correction_norms[-1],
                    line_search_alpha=effective_alpha,
                    line_search_iterations=reductions,
                    assembly_time_s=assembly_elapsed,
                    linear_solve_time_s=linear_elapsed,
                    iteration_wall_time_s=perf_counter() - iteration_started,
                    matrix_shape=diagnostics_values.get("matrix_shape", list(reduced_tangent.shape)),
                    matrix_nnz=diagnostics_values.get("matrix_nnz", int(reduced_tangent.nnz)),
                    linear_backend=diagnostics_values.get("linear_backend"),
                    linear_method=diagnostics_values.get("linear_method"),
                    krylov_iterations=diagnostics_values.get("krylov_iterations"),
                    linear_relative_residual=diagnostics_values.get("linear_relative_residual"),
                    fallback_used=diagnostics_values.get("fallback_used", False),
                    RSS_bytes=rss_bytes,
                    private_or_USS_bytes=private_bytes,
                    status="ITERATION",
                ),
            )

        diagnostics = self._failure_diagnostics(
            failure_diagnostics,
            step,
            max_iterations,
            residual_history,
            relative,
            tolerance,
            line_search_iterations,
        )
        add_robustness_diagnostics(diagnostics)
        diagnostics.update(
            {
                "assembly_seconds": assembly_seconds,
                "linear_solve_seconds": linear_solve_seconds,
                "line_search_seconds": line_search_seconds,
                "linear_system_diagnostics": linear_diagnostics,
                "contribution_diagnostics": dict(contribution_diagnostics),
            }
        )
        raise NumericalConvergenceError(
            f"Unified Newton did not converge at increment {step}; relative residual={relative:.6e}.",
            reason=NonlinearFailureReason.MAX_ITERATIONS,
            diagnostics=diagnostics,
        )

    @staticmethod
    def _failure_diagnostics(
        factory: FailureDiagnostics | None,
        step: int,
        iterations: int,
        residual_history: list[float],
        relative: float,
        tolerance: float,
        line_search_iterations: int,
    ) -> dict[str, Any]:
        if factory is not None:
            return factory(step, iterations, residual_history, relative, tolerance, line_search_iterations)
        finite = bool(np.isfinite(relative))
        return {
            "step": step,
            "iterations": iterations,
            "residual_initial": residual_history[0] if residual_history else None,
            "residual_final": residual_history[-1] if residual_history else None,
            "relative_residual": relative if finite else None,
            "relative_residual_status": "COMPUTED" if finite else "NOT_COMPUTABLE",
            "tolerance": tolerance,
            "solver": "unified_newton",
            "residual_history": tuple(residual_history),
            "line_search_iterations": line_search_iterations,
        }
