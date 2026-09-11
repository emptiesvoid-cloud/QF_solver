"""Formulation-neutral contribution and authoritative driver foundation.

The foundation deliberately stops before a Newton implementation.  Existing
drivers continue to own legacy physics until a later migration step delegates
to this lifecycle boundary.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

import numpy as np
from scipy.sparse import csr_matrix

from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.state import NonlinearState, NonlinearStateTransaction


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
