"""Opt-in numerical robustness controls for nonlinear R&D experiments."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
from math import isfinite
from typing import Any, cast
import warnings

import numpy as np
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import MatrixRankWarning, splu, spsolve

from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.controls import AdaptiveLoadControls, ArcLengthControls


_PARAMETER_KEYS = {
    "experimental_linear_solver",
    "experimental_linear_preconditioner",
    "experimental_linear_assume_spd",
    "experimental_linear_rtol",
    "experimental_linear_atol",
    "experimental_linear_maxiter",
    "experimental_linear_residual_tolerance",
    "experimental_linear_backward_error_tolerance",
    "experimental_linear_absolute_floor",
    "experimental_linear_symmetry_tolerance",
    "experimental_linear_direct_fallback",
    "experimental_jacobi_diagonal_floor",
    "experimental_ilu_drop_tol",
    "experimental_ilu_fill_factor",
    "experimental_gmres_restart",
    "experimental_linear_permutation",
    "experimental_system_scaling",
    "experimental_residual_scaling",
    "experimental_line_search",
    "experimental_line_search_min_alpha",
    "experimental_line_search_max_reductions",
    "experimental_line_search_c",
    "experimental_floor_aware_termination",
}
_PERMUTATIONS = {"NATURAL", "MMD_ATA", "MMD_AT_PLUS_A", "COLAMD"}

ROBUSTNESS_POLICY_ID = "qf-solver-unified-robustness"
ROBUSTNESS_POLICY_VERSION = 1
ADAPTIVE_POLICY_ID = "qf-solver-unified-adaptive-step"
ADAPTIVE_POLICY_VERSION = 1
FLOOR_AWARE_POLICY_ID = "qf-solver-floor-aware-termination"
FLOOR_AWARE_POLICY_VERSION = 1
FLOOR_AWARE_PLATEAU_WINDOW = 4
FLOOR_AWARE_CORRECTION_EPS_MULTIPLIER = 8.0
FLOOR_AWARE_COMPONENT_ULP_MULTIPLIER = 4.0
FLOOR_AWARE_EQUILIBRIUM_TOLERANCE = 1.0e-8
FLOOR_AWARE_LINEAR_BACKWARD_ERROR_TOLERANCE = 1.0e-10


class RobustnessPolicySource(str, Enum):
    """Origin of a robustness policy recorded in nonlinear diagnostics."""

    PUBLIC_DEFAULT = "PUBLIC_DEFAULT"
    EXPERIMENTAL_OVERRIDE = "EXPERIMENTAL_OVERRIDE"
    COMPATIBILITY_ADAPTER = "COMPATIBILITY_ADAPTER"


@dataclass(frozen=True)
class StagnationDecision:
    """Deterministic result of one residual-history stagnation decision."""

    decision: str
    reason: NonlinearFailureReason | None
    residual_window: tuple[float, ...]
    window_size: int
    plateau_threshold: float
    initial_window_residual: float | None
    final_window_residual: float | None
    relative_change: float | None
    convergence_tolerance: float | None
    policy_id: str = ROBUSTNESS_POLICY_ID
    policy_version: int = ROBUSTNESS_POLICY_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return stable, JSON-compatible stagnation diagnostics."""
        return {
            "decision": self.decision,
            "reason": self.reason.value if self.reason is not None else None,
            "window": list(self.residual_window),
            "residual_window": list(self.residual_window),
            "window_size": self.window_size,
            "plateau_threshold": self.plateau_threshold,
            "initial_window_residual": self.initial_window_residual,
            "final_window_residual": self.final_window_residual,
            "relative_change": self.relative_change,
            "convergence_tolerance": self.convergence_tolerance,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
        }


@dataclass(frozen=True)
class FloorAwareTerminationDecision:
    """Scale-aware secondary convergence decision.

    This decision is deliberately evidence-heavy.  It is not a relaxed
    residual tolerance: acceptance requires a finite residual inside a
    matrix/state-resolution estimate, a four-sample stationary window, a
    machine-scale correction, a valid linear solve, an unsuccessful merit
    search and bounded physical equilibrium evidence.
    """

    decision: str
    reason: str
    relative_residual: float | None
    convergence_tolerance: float
    correction_norm: float | None
    relative_correction_norm: float | None
    machine_epsilon: float
    correction_resolution_threshold: float
    plateau_window: tuple[float, ...]
    plateau_spread: float | None
    plateau_spread_threshold: float | None
    state_resolution_residual_estimate: float | None
    component_ulp_residual_estimate: float | None
    linear_backward_error: float | None
    linear_backward_error_tolerance: float
    line_search_improvement_available: bool | None
    force_equilibrium: float | None
    moment_equilibrium: float | None
    equilibrium_tolerance: float
    state_valid: bool
    policy_id: str = FLOOR_AWARE_POLICY_ID
    policy_version: int = FLOOR_AWARE_POLICY_VERSION

    @property
    def accepted(self) -> bool:
        """Return whether the secondary convergence path accepted the state."""
        return self.decision == "FLOOR_CONVERGED"

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic, JSON-compatible floor diagnostics."""
        return {
            "decision": self.decision,
            "reason": self.reason,
            "relative_residual": self.relative_residual,
            "convergence_tolerance": self.convergence_tolerance,
            "correction_norm": self.correction_norm,
            "relative_correction_norm": self.relative_correction_norm,
            "machine_epsilon": self.machine_epsilon,
            "correction_resolution_threshold": self.correction_resolution_threshold,
            "plateau_window": list(self.plateau_window),
            "plateau_spread": self.plateau_spread,
            "plateau_spread_threshold": self.plateau_spread_threshold,
            "state_resolution_residual_estimate": self.state_resolution_residual_estimate,
            "component_ulp_residual_estimate": self.component_ulp_residual_estimate,
            "linear_backward_error": self.linear_backward_error,
            "linear_backward_error_tolerance": self.linear_backward_error_tolerance,
            "line_search_improvement_available": self.line_search_improvement_available,
            "force_equilibrium": self.force_equilibrium,
            "moment_equilibrium": self.moment_equilibrium,
            "equilibrium_tolerance": self.equilibrium_tolerance,
            "state_valid": self.state_valid,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
        }


@dataclass(frozen=True)
class LineSearchEvaluation:
    """One detached line-search merit evaluation supplied by an adapter."""

    merit: float
    payload: object | None = None
    diagnostics: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LineSearchResult:
    """Deterministic result of the single common line-search policy loop."""

    accepted: bool
    factor: float | None
    reductions: int
    merit_history: tuple[float, ...]
    accepted_factors: tuple[float, ...]
    initial_merit: float
    min_alpha: float
    max_reductions: int
    armijo_c: float | None
    policy_source: str
    failure_reason: NonlinearFailureReason | None = None
    payload: object | None = None
    trial_diagnostics: tuple[Mapping[str, Any], ...] = ()
    supplemental_trials: int = 0
    policy_id: str = ROBUSTNESS_POLICY_ID
    policy_version: int = ROBUSTNESS_POLICY_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return stable line-search diagnostics without serializing payloads."""
        return {
            "accepted": self.accepted,
            "factor": self.factor,
            "accepted_factor": self.factor,
            "reductions": self.reductions,
            "total_reductions": self.reductions,
            "merit_history": list(self.merit_history),
            "accepted_factors": list(self.accepted_factors),
            "initial_merit": self.initial_merit,
            "min_alpha": self.min_alpha,
            "max_reductions": self.max_reductions,
            "armijo_c": self.armijo_c,
            "policy_source": self.policy_source,
            "failure_reason": self.failure_reason.value if self.failure_reason is not None else None,
            "trial_diagnostics": [dict(item) for item in self.trial_diagnostics],
            "supplemental_trials": self.supplemental_trials,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
        }


@dataclass(frozen=True)
class AdaptivePolicyDecision:
    """One deterministic adaptive increment-policy decision."""

    decision: str
    base_load_factor: float
    policy_increment: float
    proposed_increment: float
    accepted: bool
    rejected: bool
    failure_reason: str | None
    retry_classification: str | None
    cutback_factor: float
    growth_factor: float
    minimum_increment: float
    maximum_increment: float
    cutback_count: int
    maximum_cutbacks: int
    iterations: int | None
    grow_below_iterations: int
    shrink_above_iterations: int
    next_increment: float | None
    retry_increment: float | None
    clipped_to_target: bool = False
    policy_id: str = ADAPTIVE_POLICY_ID
    policy_version: int = ADAPTIVE_POLICY_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic, JSON-compatible policy diagnostics."""
        return {
            "decision": self.decision,
            "base_load_factor": self.base_load_factor,
            "policy_increment": self.policy_increment,
            "proposed_increment": self.proposed_increment,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "failure_reason": self.failure_reason,
            "retry_classification": self.retry_classification,
            "cutback_factor": self.cutback_factor,
            "growth_factor": self.growth_factor,
            "minimum_increment": self.minimum_increment,
            "maximum_increment": self.maximum_increment,
            "cutback_count": self.cutback_count,
            "maximum_cutbacks": self.maximum_cutbacks,
            "iterations": self.iterations,
            "grow_below_iterations": self.grow_below_iterations,
            "shrink_above_iterations": self.shrink_above_iterations,
            "next_increment": self.next_increment,
            "retry_increment": self.retry_increment,
            "clipped_to_target": self.clipped_to_target,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
        }


class UnifiedAdaptiveStepPolicy:
    """Single formulation-neutral authority for adaptive step decisions.

    This class owns only deterministic increment policy.  It does not own
    model assembly, material/contact state or accepted-state publication;
    callers must rollback through ``UnifiedContinuationController`` before
    asking it to classify a failed trial.
    """

    def __init__(
        self,
        controls: AdaptiveLoadControls,
        *,
        policy_source: str | RobustnessPolicySource = RobustnessPolicySource.PUBLIC_DEFAULT,
        allow_owner_policy: bool = True,
    ) -> None:
        source = policy_source.value if isinstance(policy_source, RobustnessPolicySource) else str(policy_source)
        if source not in {item.value for item in RobustnessPolicySource}:
            raise ValueError(f"Unknown adaptive policy source {source!r}.")
        self.controls = controls
        self.policy_source = source
        self.allow_owner_policy = bool(allow_owner_policy)
        self._decisions: list[AdaptivePolicyDecision] = []

    @property
    def decisions(self) -> tuple[AdaptivePolicyDecision, ...]:
        """Return the immutable view of decisions emitted so far."""
        return tuple(self._decisions)

    def configuration_diagnostics(self) -> dict[str, Any]:
        """Return controls and deterministic policy history."""
        controls = self.controls
        return {
            "policy_id": ADAPTIVE_POLICY_ID,
            "policy_version": ADAPTIVE_POLICY_VERSION,
            "policy_source": self.policy_source,
            "allow_owner_policy": self.allow_owner_policy,
            "controls": {
                "initial_increment": controls.initial_increment,
                "minimum_increment": controls.minimum_increment,
                "maximum_increment": controls.maximum_increment,
                "cutback_factor": controls.cutback_factor,
                "growth_factor": controls.growth_factor,
                "grow_below_iterations": controls.grow_below_iterations,
                "shrink_above_iterations": controls.shrink_above_iterations,
                "maximum_cutbacks": controls.maximum_cutbacks,
            },
            "minimum_increment_equality": "PERMITTED",
            "maximum_cutbacks_semantics": "terminal after the Nth rejected attempt; no N+1 attempt",
            "decisions": [decision.to_dict() for decision in self._decisions],
        }

    def initial_increment(self, stored_increment: float | None = None) -> float:
        """Return a validated initial/continued policy increment."""
        if stored_increment is None or not np.isfinite(float(stored_increment)) or float(stored_increment) <= 0.0:
            return self.controls.initial_increment
        return min(
            self.controls.maximum_increment,
            max(self.controls.minimum_increment, float(stored_increment)),
        )

    def propose_increment(self, accepted_load_factor: float, policy_increment: float) -> float:
        """Clip one policy increment to the final target without mutating policy state."""
        base = float(accepted_load_factor)
        increment = float(policy_increment)
        if not np.isfinite(base) or not np.isfinite(increment) or increment <= 0.0:
            raise ValueError("Adaptive policy inputs must be finite and positive where required.")
        remaining = 1.0 - base
        if remaining <= 0.0:
            return 0.0
        proposed = min(increment, remaining)
        if proposed <= 0.0 or not np.isfinite(proposed):
            raise ValueError("Adaptive policy produced an invalid proposed increment.")
        return proposed

    def on_accept(
        self,
        *,
        base_load_factor: float,
        policy_increment: float,
        proposed_increment: float,
        iterations: int,
        cutback_count: int,
    ) -> AdaptivePolicyDecision:
        """Choose keep/grow/shrink after a globally accepted increment."""
        controls = self.controls
        policy_value = float(policy_increment)
        proposed_value = float(proposed_increment)
        if not np.isfinite(policy_value) or not np.isfinite(proposed_value) or policy_value <= 0.0 or proposed_value <= 0.0:
            raise ValueError("Accepted adaptive increments must be finite and positive.")
        if int(iterations) <= controls.grow_below_iterations:
            decision_name = "ACCEPT_GROW"
            next_increment = min(controls.maximum_increment, policy_value * controls.growth_factor)
        elif int(iterations) >= controls.shrink_above_iterations:
            decision_name = "ACCEPT_SHRINK"
            next_increment = max(controls.minimum_increment, policy_value * controls.cutback_factor)
        else:
            decision_name = "ACCEPT_KEEP"
            next_increment = policy_value
        decision = AdaptivePolicyDecision(
            decision=decision_name,
            base_load_factor=float(base_load_factor),
            policy_increment=policy_value,
            proposed_increment=proposed_value,
            accepted=True,
            rejected=False,
            failure_reason=None,
            retry_classification=None,
            cutback_factor=controls.cutback_factor,
            growth_factor=controls.growth_factor,
            minimum_increment=controls.minimum_increment,
            maximum_increment=controls.maximum_increment,
            cutback_count=int(cutback_count),
            maximum_cutbacks=controls.maximum_cutbacks,
            iterations=int(iterations),
            grow_below_iterations=controls.grow_below_iterations,
            shrink_above_iterations=controls.shrink_above_iterations,
            next_increment=float(next_increment),
            retry_increment=None,
            clipped_to_target=proposed_value < policy_value,
        )
        self._decisions.append(decision)
        return decision

    def on_failure(
        self,
        *,
        base_load_factor: float,
        proposed_increment: float,
        failure_reason: NonlinearFailureReason | str | None,
        retry_classification: object,
        rejected_count: int,
        iterations: int | None = None,
    ) -> AdaptivePolicyDecision:
        """Classify a post-rollback failure and choose retry or terminal outcome."""
        controls = self.controls
        proposed_value = float(proposed_increment)
        if not np.isfinite(proposed_value) or proposed_value <= 0.0:
            raise ValueError("Failed adaptive increments must be finite and positive.")
        reason_value = self._enum_value(failure_reason)
        classification_value = self._enum_value(retry_classification)
        retry_allowed = classification_value == "RETRYABLE" or (
            self.allow_owner_policy and classification_value == "OWNER_POLICY_DEPENDENT"
        )
        retry_value = proposed_value * controls.cutback_factor
        if not retry_allowed:
            decision_name = "TERMINAL_NON_RETRYABLE"
            next_increment = None
        elif int(rejected_count) >= controls.maximum_cutbacks:
            decision_name = "TERMINAL_MAX_CUTBACKS"
            next_increment = None
        elif retry_value < controls.minimum_increment:
            decision_name = "TERMINAL_MIN_INCREMENT"
            next_increment = None
        else:
            decision_name = "RETRY_CUTBACK"
            next_increment = retry_value
        decision = AdaptivePolicyDecision(
            decision=decision_name,
            base_load_factor=float(base_load_factor),
            policy_increment=proposed_value,
            proposed_increment=proposed_value,
            accepted=False,
            rejected=True,
            failure_reason=None if reason_value is None else str(reason_value),
            retry_classification=None if classification_value is None else str(classification_value),
            cutback_factor=controls.cutback_factor,
            growth_factor=controls.growth_factor,
            minimum_increment=controls.minimum_increment,
            maximum_increment=controls.maximum_increment,
            cutback_count=int(rejected_count),
            maximum_cutbacks=controls.maximum_cutbacks,
            iterations=None if iterations is None else int(iterations),
            grow_below_iterations=controls.grow_below_iterations,
            shrink_above_iterations=controls.shrink_above_iterations,
            next_increment=None if next_increment is None else float(next_increment),
            retry_increment=float(retry_value),
        )
        self._decisions.append(decision)
        return decision

    @staticmethod
    def _enum_value(value: object) -> object:
        return getattr(value, "value", value)


ARC_RADIUS_POLICY_ID = "qf-solver-unified-arc-length-radius"
ARC_RADIUS_POLICY_VERSION = 1


@dataclass(frozen=True)
class ArcRadiusPolicyDecision:
    """One deterministic accepted-step or retry radius decision."""

    decision: str
    accepted_step: int
    base_load_factor: float
    policy_radius: float
    effective_attempt_radius: float
    adaptive_radius_enabled: bool
    iterations: int | None
    grow_below_iterations: int
    shrink_above_iterations: int
    growth_factor: float
    shrink_factor: float
    minimum_radius: float
    maximum_radius: float
    failure_reason: str | None
    retry_classification: str | None
    rejected_count: int
    retry_radius: float | None
    effective_retry_radius: float | None
    accepted_next_radius: float | None
    target_clipped: bool
    rollback_verified: bool
    accepted_state_digest: str | None
    failure_stage: str | None = None
    policy_id: str = ARC_RADIUS_POLICY_ID
    policy_version: int = ARC_RADIUS_POLICY_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic, JSON-compatible radius diagnostics."""
        return {
            "decision": self.decision,
            "accepted_step": self.accepted_step,
            "base_load_factor": self.base_load_factor,
            "policy_radius": self.policy_radius,
            "effective_attempt_radius": self.effective_attempt_radius,
            "adaptive_radius_enabled": self.adaptive_radius_enabled,
            "iterations": self.iterations,
            "grow_below_iterations": self.grow_below_iterations,
            "shrink_above_iterations": self.shrink_above_iterations,
            "growth_factor": self.growth_factor,
            "shrink_factor": self.shrink_factor,
            "minimum_radius": self.minimum_radius,
            "maximum_radius": self.maximum_radius,
            "failure_reason": self.failure_reason,
            "retry_classification": self.retry_classification,
            "rejected_count": self.rejected_count,
            "retry_radius": self.retry_radius,
            "effective_retry_radius": self.effective_retry_radius,
            "accepted_next_radius": self.accepted_next_radius,
            "target_clipped": self.target_clipped,
            "rollback_verified": self.rollback_verified,
            "accepted_state_digest": self.accepted_state_digest,
            "failure_stage": self.failure_stage,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
        }


class UnifiedArcLengthRadiusPolicy:
    """Single formulation-neutral policy authority for arc-length radii.

    The policy owns only radius decisions.  It does not know the augmented
    arc-length equations and it never publishes accepted nonlinear state.
    ``effective_attempt_radius`` is the radius actually passed to the
    correction kernel after target clipping; it is used to prevent a retry
    from silently repeating an identical clipped attempt.
    """

    _TERMINAL_ARC_FAILURE_STAGES = frozenset(
        {
            "minimum_radius",
            "max_steps",
            "load_factor_limit",
            "target_load_factor_limit",
            "terminal_policy",
        }
    )

    def __init__(
        self,
        controls: ArcLengthControls,
        *,
        policy_source: str | RobustnessPolicySource = RobustnessPolicySource.PUBLIC_DEFAULT,
        allow_owner_policy: bool = True,
    ) -> None:
        source = policy_source.value if isinstance(policy_source, RobustnessPolicySource) else str(policy_source)
        if source not in {item.value for item in RobustnessPolicySource}:
            raise ValueError(f"Unknown arc-length policy source {source!r}.")
        self.controls = controls
        self.policy_source = source
        self.allow_owner_policy = bool(allow_owner_policy)
        self._decisions: list[ArcRadiusPolicyDecision] = []

    @property
    def decisions(self) -> tuple[ArcRadiusPolicyDecision, ...]:
        """Return an immutable view of all radius decisions."""
        return tuple(self._decisions)

    def configuration_diagnostics(self) -> dict[str, Any]:
        """Return controls and the deterministic decision history."""
        controls = self.controls
        return {
            "policy_id": ARC_RADIUS_POLICY_ID,
            "policy_version": ARC_RADIUS_POLICY_VERSION,
            "policy_source": self.policy_source,
            "allow_owner_policy": self.allow_owner_policy,
            "controls": {
                "adaptive_radius": controls.adaptive_radius,
                "minimum_radius": controls.minimum_radius,
                "growth_factor": controls.growth_factor,
                "shrink_factor": controls.shrink_factor,
                "grow_below_iterations": controls.grow_below_iterations,
                "shrink_above_iterations": controls.shrink_above_iterations,
            },
            "minimum_radius_equality": "PERMITTED",
            "radius_roles": {
                "policy_radius": "radius carried between accepted/rejected decisions",
                "effective_attempt_radius": "radius passed to the augmented correction after target clipping",
            },
            "decisions": [decision.to_dict() for decision in self._decisions],
        }

    def on_accept(
        self,
        *,
        accepted_step: int,
        base_load_factor: float,
        policy_radius: float,
        effective_attempt_radius: float,
        maximum_radius: float,
        iterations: int,
        target_clipped: bool | None = None,
        accepted_state_digest: str | None = None,
    ) -> ArcRadiusPolicyDecision:
        """Choose keep/grow/shrink after a globally accepted arc step."""
        controls = self.controls
        policy_value = float(policy_radius)
        effective_value = float(effective_attempt_radius)
        maximum_value = float(maximum_radius)
        if (
            not np.isfinite(policy_value)
            or policy_value <= 0.0
            or not np.isfinite(effective_value)
            or effective_value <= 0.0
            or not np.isfinite(maximum_value)
            or maximum_value < policy_value
        ):
            raise ValueError("Accepted arc-length radii must be finite and ordered.")
        if int(iterations) <= controls.grow_below_iterations and controls.adaptive_radius:
            decision_name = "ACCEPT_GROW"
            next_radius = min(maximum_value, policy_value * controls.growth_factor)
        elif int(iterations) >= controls.shrink_above_iterations and controls.adaptive_radius:
            decision_name = "ACCEPT_SHRINK"
            next_radius = max(controls.minimum_radius, policy_value * controls.shrink_factor)
        else:
            decision_name = "ACCEPT_KEEP"
            next_radius = policy_value
        decision = ArcRadiusPolicyDecision(
            decision=decision_name,
            accepted_step=int(accepted_step),
            base_load_factor=float(base_load_factor),
            policy_radius=policy_value,
            effective_attempt_radius=effective_value,
            adaptive_radius_enabled=controls.adaptive_radius,
            iterations=int(iterations),
            grow_below_iterations=controls.grow_below_iterations,
            shrink_above_iterations=controls.shrink_above_iterations,
            growth_factor=controls.growth_factor,
            shrink_factor=controls.shrink_factor,
            minimum_radius=controls.minimum_radius,
            maximum_radius=maximum_value,
            failure_reason=None,
            retry_classification=None,
            rejected_count=0,
            retry_radius=None,
            effective_retry_radius=None,
            accepted_next_radius=float(next_radius),
            target_clipped=(effective_value < policy_value) if target_clipped is None else bool(target_clipped),
            rollback_verified=False,
            accepted_state_digest=accepted_state_digest,
        )
        self._decisions.append(decision)
        return decision

    def on_failure(
        self,
        *,
        accepted_step: int,
        base_load_factor: float,
        policy_radius: float,
        effective_attempt_radius: float,
        maximum_radius: float,
        failure_reason: object,
        retry_classification: object,
        rejected_count: int,
        failure_diagnostics: Mapping[str, Any] | None = None,
        rollback_verified: bool = True,
        accepted_state_digest: str | None = None,
    ) -> ArcRadiusPolicyDecision:
        """Classify a post-rollback failure and choose the next radius."""
        controls = self.controls
        policy_value = float(policy_radius)
        effective_value = float(effective_attempt_radius)
        maximum_value = float(maximum_radius)
        if (
            not np.isfinite(policy_value)
            or policy_value <= 0.0
            or not np.isfinite(effective_value)
            or effective_value <= 0.0
            or not np.isfinite(maximum_value)
            or maximum_value < policy_value
        ):
            raise ValueError("Failed arc-length radii must be finite and ordered.")
        diagnostics = dict(failure_diagnostics or {})
        reason_value = self._enum_value(failure_reason)
        classification_value = self._enum_value(retry_classification)
        reason_name = None if reason_value is None else str(reason_value)
        classification_name = None if classification_value is None else str(classification_value)
        failure_stage = diagnostics.get("failure_stage")
        failure_stage_name = None if failure_stage is None else str(failure_stage).lower()
        terminal_arc_boundary = self._is_terminal_arc_failure(
            reason_name,
            diagnostics,
            failure_stage_name,
        )
        retry_allowed = classification_name == "RETRYABLE" or (
            self.allow_owner_policy and classification_name == "OWNER_POLICY_DEPENDENT"
        )
        if terminal_arc_boundary:
            retry_allowed = False

        # A target-clipped attempt can otherwise retry the same effective
        # radius even after the policy radius is reduced.  Advance the policy
        # radius through the first value strictly below the failed effective
        # radius.  This preserves the legacy geometric cutback sequence while
        # guaranteeing that the next correction genuinely steps down.
        policy_retry_value = policy_value * controls.shrink_factor
        while effective_value < policy_value and policy_retry_value >= effective_value:
            policy_retry_value *= controls.shrink_factor
        effective_retry_value = policy_retry_value
        if (
            not np.isfinite(policy_retry_value)
            or policy_retry_value <= 0.0
            or not np.isfinite(effective_retry_value)
            or effective_retry_value <= 0.0
        ):
            raise ValueError("Arc-length radius policy produced an invalid retry radius.")
        if not rollback_verified:
            decision_name = "TERMINAL_NON_RETRYABLE"
        elif not retry_allowed:
            decision_name = "TERMINAL_NON_RETRYABLE"
        elif effective_retry_value < controls.minimum_radius:
            decision_name = "TERMINAL_MIN_RADIUS"
        else:
            decision_name = "RETRY_SHRINK"
        decision = ArcRadiusPolicyDecision(
            decision=decision_name,
            accepted_step=int(accepted_step),
            base_load_factor=float(base_load_factor),
            policy_radius=policy_value,
            effective_attempt_radius=effective_value,
            adaptive_radius_enabled=controls.adaptive_radius,
            iterations=None,
            grow_below_iterations=controls.grow_below_iterations,
            shrink_above_iterations=controls.shrink_above_iterations,
            growth_factor=controls.growth_factor,
            shrink_factor=controls.shrink_factor,
            minimum_radius=controls.minimum_radius,
            maximum_radius=maximum_value,
            failure_reason=reason_name,
            retry_classification=classification_name,
            rejected_count=int(rejected_count),
            retry_radius=float(policy_retry_value),
            effective_retry_radius=float(effective_retry_value),
            accepted_next_radius=None,
            target_clipped=effective_value < policy_value,
            rollback_verified=bool(rollback_verified),
            accepted_state_digest=accepted_state_digest,
            failure_stage=failure_stage_name,
        )
        self._decisions.append(decision)
        return decision

    def record_accepted_state_digest(self, digest: str) -> ArcRadiusPolicyDecision:
        """Attach the digest published by the completed accepted increment."""
        if not self._decisions or not self._decisions[-1].decision.startswith("ACCEPT_"):
            raise RuntimeError("An accepted radius decision is required before recording its state digest.")
        if not isinstance(digest, str) or not digest:
            raise ValueError("Accepted arc-length state digest must be a non-empty string.")
        decision = replace(self._decisions[-1], accepted_state_digest=digest)
        self._decisions[-1] = decision
        return decision

    @classmethod
    def _is_terminal_arc_failure(
        cls,
        reason_name: str | None,
        diagnostics: Mapping[str, Any],
        failure_stage: str | None,
    ) -> bool:
        if reason_name != NonlinearFailureReason.ARC_LENGTH_FAILURE.value:
            return False
        if failure_stage in cls._TERMINAL_ARC_FAILURE_STAGES:
            return True
        # A predictor/correction envelope violation is a retryable numerical
        # correction failure.  The route emits an explicit failure stage for
        # terminal policy boundaries, so a bare load-factor diagnostic must
        # not bypass radius cutback and retry.
        return "max_arc_steps" in diagnostics

    @staticmethod
    def _enum_value(value: object) -> object:
        return getattr(value, "value", value)


class UnifiedNonlinearRobustnessController:
    """Single formulation-neutral authority for stagnation and line search.

    The controller evaluates residual histories and detached merit callbacks;
    it never owns FEM physics or mutates a nonlinear accepted/trial state.
    Adapters may supply an explicit experimental or compatibility policy, but
    the policy loop and diagnostic schema remain common.
    """

    def __init__(
        self,
        *,
        policy_source: str | RobustnessPolicySource = RobustnessPolicySource.PUBLIC_DEFAULT,
        stagnation_enabled: bool = True,
        stagnation_window: int = 4,
        plateau_threshold: float = 1.0e-10,
        line_search_enabled: bool = True,
        min_alpha: float = 1.0e-4,
        max_reductions: int = 12,
        armijo_c: float | None = None,
        floor_aware_termination: bool = False,
    ) -> None:
        source = policy_source.value if isinstance(policy_source, RobustnessPolicySource) else str(policy_source)
        if source not in {item.value for item in RobustnessPolicySource}:
            raise ValueError(f"Unknown nonlinear robustness policy source {source!r}.")
        if stagnation_window < 1:
            raise ValueError("stagnation_window must be positive.")
        if not isfinite(float(plateau_threshold)) or not 0.0 <= float(plateau_threshold) < 1.0:
            raise ValueError("plateau_threshold must be finite and in [0, 1).")
        if not isfinite(float(min_alpha)) or not 0.0 <= float(min_alpha) <= 1.0:
            raise ValueError("min_alpha must be finite and in [0, 1].")
        if int(max_reductions) < 0:
            raise ValueError("max_reductions must be non-negative.")
        if armijo_c is not None and (not isfinite(float(armijo_c)) or not 0.0 <= float(armijo_c) < 1.0):
            raise ValueError("armijo_c must be None or finite in [0, 1).")
        self.policy_source = source
        self.stagnation_enabled = bool(stagnation_enabled)
        self.stagnation_window = int(stagnation_window)
        self.plateau_threshold = float(plateau_threshold)
        self.line_search_enabled = bool(line_search_enabled)
        self.min_alpha = float(min_alpha)
        self.max_reductions = int(max_reductions)
        self.armijo_c = None if armijo_c is None else float(armijo_c)
        self.floor_aware_termination = bool(floor_aware_termination)

    @classmethod
    def from_options(
        cls,
        options: NonlinearRobustnessOptions | None,
        *,
        line_search_enabled: bool = True,
    ) -> "UnifiedNonlinearRobustnessController":
        """Build the common controller from explicit or public-default options."""
        if options is None:
            return cls(
                policy_source=RobustnessPolicySource.PUBLIC_DEFAULT,
                line_search_enabled=line_search_enabled,
            )
        if options.line_search == "off":
            return cls(
                policy_source=RobustnessPolicySource.EXPERIMENTAL_OVERRIDE,
                line_search_enabled=False,
                floor_aware_termination=options.floor_aware_termination,
            )
        if options.line_search == "existing":
            # Preserve the historical helper discrepancy as an explicit
            # compatibility configuration while using the common policy loop.
            return cls(
                policy_source=RobustnessPolicySource.EXPERIMENTAL_OVERRIDE,
                line_search_enabled=line_search_enabled,
                min_alpha=0.0,
                max_reductions=14,
                armijo_c=None,
                floor_aware_termination=options.floor_aware_termination,
            )
        return cls(
            policy_source=RobustnessPolicySource.EXPERIMENTAL_OVERRIDE,
            line_search_enabled=line_search_enabled,
            min_alpha=options.line_search_min_alpha,
            max_reductions=options.line_search_max_reductions,
            armijo_c=options.line_search_c,
            floor_aware_termination=options.floor_aware_termination,
        )

    def configuration_diagnostics(
        self,
        *,
        stagnation: Mapping[str, Any] | None = None,
        line_search: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return the policy identity and current deterministic diagnostics."""
        if line_search is None:
            line_items: list[Mapping[str, Any]] = []
        elif isinstance(line_search, Mapping):
            line_items = [line_search]
        else:
            line_items = list(line_search)
        return {
            "policy_id": ROBUSTNESS_POLICY_ID,
            "policy_version": ROBUSTNESS_POLICY_VERSION,
            "policy_source": self.policy_source,
            "stagnation": dict(stagnation or {
                "decision": "NOT_EVALUATED",
                "window_size": self.stagnation_window,
                "plateau_threshold": self.plateau_threshold,
                "policy_id": ROBUSTNESS_POLICY_ID,
                "policy_version": ROBUSTNESS_POLICY_VERSION,
            }),
            "line_search": {
                "enabled": self.line_search_enabled,
                "min_alpha": self.min_alpha,
                "max_reductions": self.max_reductions,
                "armijo_c": self.armijo_c,
                "policy_source": self.policy_source,
                "policy_id": ROBUSTNESS_POLICY_ID,
                "policy_version": ROBUSTNESS_POLICY_VERSION,
                "events": [dict(item) for item in line_items],
            },
            "floor_aware_termination": {
                "enabled": self.floor_aware_termination,
                "policy_id": FLOOR_AWARE_POLICY_ID,
                "policy_version": FLOOR_AWARE_POLICY_VERSION,
                "plateau_window": FLOOR_AWARE_PLATEAU_WINDOW,
                "correction_eps_multiplier": FLOOR_AWARE_CORRECTION_EPS_MULTIPLIER,
                "component_ulp_multiplier": FLOOR_AWARE_COMPONENT_ULP_MULTIPLIER,
                "equilibrium_tolerance": FLOOR_AWARE_EQUILIBRIUM_TOLERANCE,
                "linear_backward_error_tolerance": FLOOR_AWARE_LINEAR_BACKWARD_ERROR_TOLERANCE,
            },
        }

    def stagnation_decision(
        self,
        residual_history: Sequence[float],
        *,
        converged: bool = False,
        convergence_tolerance: float | None = None,
    ) -> StagnationDecision:
        """Evaluate the frozen four-sample residual plateau contract."""
        values = tuple(float(value) for value in residual_history)
        window = values[-self.stagnation_window:]
        if any(np.isinf(value) for value in values):
            return StagnationDecision(
                "NONFINITE",
                NonlinearFailureReason.INF_DETECTED,
                window,
                self.stagnation_window,
                self.plateau_threshold,
                window[0] if window else None,
                window[-1] if window else None,
                None,
                convergence_tolerance,
            )
        if any(np.isnan(value) for value in values):
            return StagnationDecision(
                "NONFINITE",
                NonlinearFailureReason.NAN_DETECTED,
                window,
                self.stagnation_window,
                self.plateau_threshold,
                window[0] if window else None,
                window[-1] if window else None,
                None,
                convergence_tolerance,
            )
        if converged:
            return StagnationDecision(
                "CONVERGED",
                None,
                window,
                self.stagnation_window,
                self.plateau_threshold,
                window[0] if window else None,
                window[-1] if window else None,
                None,
                convergence_tolerance,
            )
        if not self.stagnation_enabled:
            decision = "DISABLED"
        elif len(values) < self.stagnation_window:
            decision = "INSUFFICIENT_HISTORY"
        else:
            initial = window[0]
            final = window[-1]
            denominator = max(abs(initial), float(np.finfo(float).tiny))
            relative_change = (initial - final) / denominator
            if final >= initial * (1.0 - self.plateau_threshold):
                return StagnationDecision(
                    "STAGNATION",
                    NonlinearFailureReason.CONVERGENCE_STAGNATION,
                    window,
                    self.stagnation_window,
                    self.plateau_threshold,
                    initial,
                    final,
                    float(relative_change),
                    convergence_tolerance,
                )
            return StagnationDecision(
                "CONTINUE",
                None,
                window,
                self.stagnation_window,
                self.plateau_threshold,
                initial,
                final,
                float(relative_change),
                convergence_tolerance,
            )
        return StagnationDecision(
            decision,
            None,
            window,
            self.stagnation_window,
            self.plateau_threshold,
            window[0] if window else None,
            window[-1] if window else None,
            None,
            convergence_tolerance,
        )

    def floor_aware_decision(
        self,
        residual_history: Sequence[float],
        *,
        relative_residual: float,
        convergence_tolerance: float,
        correction: np.ndarray | None,
        displacement: np.ndarray | None,
        tangent: csr_matrix | None,
        residual_scale: float,
        linear_backward_error: float | None,
        line_search_improvement_available: bool | None,
        force_equilibrium: float | None,
        moment_equilibrium: float | None,
        state_valid: bool,
        displacement_scale: float | None = None,
    ) -> FloorAwareTerminationDecision:
        """Evaluate the opt-in numerical-floor convergence conjunction.

        ``residual_history`` contains normalized residuals.  The matrix and
        displacement are the current reduced Newton system and its detached
        trial displacement.  They are used only to estimate a reachable
        state-resolution floor; this method never changes either object or
        the nonlinear transaction.
        """

        epsilon = float(np.finfo(np.float64).eps)
        try:
            raw_history = tuple(float(value) for value in residual_history)
        except (TypeError, ValueError):
            raw_history = ()
        finite_history = all(np.isfinite(value) for value in raw_history)
        safe_history = tuple(value if np.isfinite(value) else 0.0 for value in raw_history)
        plateau_window = safe_history[-FLOOR_AWARE_PLATEAU_WINDOW:]
        plateau_spread = (
            float(max(plateau_window) - min(plateau_window))
            if plateau_window and finite_history
            else None
        )

        try:
            relative = float(relative_residual)
        except (TypeError, ValueError):
            relative = float("nan")
        try:
            tolerance = float(convergence_tolerance)
        except (TypeError, ValueError):
            tolerance = float("nan")
        try:
            scale = float(residual_scale)
        except (TypeError, ValueError):
            scale = float("nan")

        correction_norm: float | None = None
        relative_correction_norm: float | None = None
        correction_resolution_threshold = FLOOR_AWARE_CORRECTION_EPS_MULTIPLIER * epsilon
        relative_ulp: float | None = None
        if correction is not None:
            values = np.asarray(correction, dtype=float)
            if values.ndim == 1 and np.all(np.isfinite(values)):
                correction_norm = float(np.linalg.norm(values))

        displacement_values: np.ndarray | None = None
        if displacement is not None:
            candidate = np.asarray(displacement, dtype=float)
            if candidate.ndim == 1 and np.all(np.isfinite(candidate)):
                displacement_values = candidate
                displacement_norm = float(np.linalg.norm(candidate))
                try:
                    explicit_scale = float(displacement_scale) if displacement_scale is not None else 0.0
                except (TypeError, ValueError):
                    explicit_scale = float("nan")
                if np.isfinite(explicit_scale):
                    denominator = max(displacement_norm, explicit_scale, float(np.finfo(float).tiny))
                    if correction_norm is not None:
                        relative_correction_norm = correction_norm / denominator
                    relative_ulp = float(np.linalg.norm(np.abs(np.spacing(candidate))) / denominator)
                    correction_resolution_threshold = max(
                        correction_resolution_threshold,
                        FLOOR_AWARE_COMPONENT_ULP_MULTIPLIER * relative_ulp,
                    )

        state_resolution_residual_estimate: float | None = None
        component_ulp_residual_estimate: float | None = None
        if (
            tangent is not None
            and displacement_values is not None
            and np.isfinite(scale)
            and scale > 0.0
        ):
            matrix = csr_matrix(tangent, dtype=float)
            if matrix.shape == (displacement_values.size, displacement_values.size) and np.all(
                np.isfinite(matrix.data)
            ):
                matrix_inf = float(np.max(np.asarray(np.abs(matrix).sum(axis=1)).ravel(), initial=0.0))
                displacement_norm = float(np.linalg.norm(displacement_values))
                state_resolution_residual_estimate = matrix_inf * epsilon * displacement_norm / scale
                component_ulp = np.abs(np.spacing(displacement_values))
                component_ulp_residual_estimate = float(
                    np.linalg.norm(matrix @ component_ulp) / scale
                )

        state_resolution_threshold: float | None = None
        if state_resolution_residual_estimate is not None and component_ulp_residual_estimate is not None:
            state_resolution_threshold = max(
                state_resolution_residual_estimate,
                component_ulp_residual_estimate,
                FLOOR_AWARE_CORRECTION_EPS_MULTIPLIER * epsilon,
            )
        plateau_spread_threshold = state_resolution_threshold

        try:
            backward_error = (
                None if linear_backward_error is None else float(linear_backward_error)
            )
        except (TypeError, ValueError):
            backward_error = None

        try:
            force_value = None if force_equilibrium is None else float(force_equilibrium)
        except (TypeError, ValueError):
            force_value = None
        try:
            moment_value = None if moment_equilibrium is None else float(moment_equilibrium)
        except (TypeError, ValueError):
            moment_value = None

        def result(decision: str, reason: str) -> FloorAwareTerminationDecision:
            return FloorAwareTerminationDecision(
                decision=decision,
                reason=reason,
                relative_residual=relative if np.isfinite(relative) else None,
                convergence_tolerance=tolerance,
                correction_norm=correction_norm,
                relative_correction_norm=relative_correction_norm,
                machine_epsilon=epsilon,
                correction_resolution_threshold=correction_resolution_threshold,
                plateau_window=plateau_window,
                plateau_spread=plateau_spread,
                plateau_spread_threshold=plateau_spread_threshold,
                state_resolution_residual_estimate=state_resolution_residual_estimate,
                component_ulp_residual_estimate=component_ulp_residual_estimate,
                linear_backward_error=backward_error,
                linear_backward_error_tolerance=FLOOR_AWARE_LINEAR_BACKWARD_ERROR_TOLERANCE,
                line_search_improvement_available=line_search_improvement_available,
                force_equilibrium=force_value,
                moment_equilibrium=moment_value,
                equilibrium_tolerance=FLOOR_AWARE_EQUILIBRIUM_TOLERANCE,
                state_valid=bool(state_valid),
            )

        if not self.floor_aware_termination:
            return result("REJECT", "DISABLED")
        if not np.isfinite(relative) or not np.isfinite(tolerance) or tolerance <= 0.0:
            return result("REJECT", "NONFINITE_RESIDUAL_OR_TOLERANCE")
        if relative <= tolerance:
            return result("PRIMARY_CONVERGED", "PRIMARY_RESIDUAL_CRITERION")
        if not finite_history:
            return result("REJECT", "NONFINITE_RESIDUAL_HISTORY")
        if len(raw_history) < FLOOR_AWARE_PLATEAU_WINDOW:
            return result("REJECT", "PLATEAU_HISTORY_INSUFFICIENT")
        if state_resolution_threshold is None:
            return result("REJECT", "STATE_RESOLUTION_UNAVAILABLE")
        if relative > state_resolution_threshold:
            return result("REJECT", "RESIDUAL_ABOVE_STATE_RESOLUTION")
        if plateau_spread is None or plateau_spread > state_resolution_threshold:
            return result("REJECT", "RESIDUAL_NOT_STATIONARY")
        if correction_norm is None or relative_correction_norm is None:
            return result("REJECT", "CORRECTION_UNAVAILABLE")
        if relative_correction_norm > correction_resolution_threshold:
            return result("REJECT", "CORRECTION_ABOVE_MACHINE_RESOLUTION")
        if backward_error is None or not np.isfinite(backward_error):
            return result("REJECT", "LINEAR_BACKWARD_ERROR_UNAVAILABLE")
        if backward_error > FLOOR_AWARE_LINEAR_BACKWARD_ERROR_TOLERANCE:
            return result("REJECT", "LINEAR_CORRECTION_NOT_VALID")
        if line_search_improvement_available is not False:
            return result("REJECT", "LINE_SEARCH_IMPROVEMENT_UNKNOWN_OR_AVAILABLE")
        if not bool(state_valid):
            return result("REJECT", "INVALID_STATE_EVIDENCE")
        if force_value is None or not np.isfinite(force_value):
            return result("REJECT", "FORCE_EQUILIBRIUM_UNAVAILABLE")
        if force_value > FLOOR_AWARE_EQUILIBRIUM_TOLERANCE:
            return result("REJECT", "FORCE_EQUILIBRIUM_UNBOUNDED")
        if moment_value is None or not np.isfinite(moment_value):
            return result("REJECT", "MOMENT_EQUILIBRIUM_UNAVAILABLE")
        if moment_value > FLOOR_AWARE_EQUILIBRIUM_TOLERANCE:
            return result("REJECT", "MOMENT_EQUILIBRIUM_UNBOUNDED")
        return result("FLOOR_CONVERGED", "NUMERICALLY_STATIONARY_EQUILIBRIUM")

    # Short aliases keep the contract discoverable without introducing another
    # policy implementation.
    check_stagnation = stagnation_decision
    evaluate_stagnation = stagnation_decision

    def line_search(
        self,
        initial_merit: float,
        evaluate: Callable[[float], LineSearchEvaluation | tuple[object, ...] | float],
        *,
        raise_on_failure: bool = True,
        supplemental_alphas: Sequence[float] = (),
    ) -> LineSearchResult:
        """Run the one common alpha=1, halve-until-accepted policy loop."""
        initial = float(initial_merit)
        if not np.isfinite(initial):
            reason = NonlinearFailureReason.INF_DETECTED if np.isinf(initial) else NonlinearFailureReason.NAN_DETECTED
            raise NumericalConvergenceError(
                "Nonlinear line-search initial merit is non-finite.",
                reason=reason,
                diagnostics={
                    "policy_id": ROBUSTNESS_POLICY_ID,
                    "policy_version": ROBUSTNESS_POLICY_VERSION,
                    "policy_source": self.policy_source,
                    "initial_merit": None,
                },
            )
        if not self.line_search_enabled:
            result = LineSearchResult(
                accepted=False,
                factor=None,
                reductions=0,
                merit_history=(),
                accepted_factors=(),
                initial_merit=initial,
                min_alpha=self.min_alpha,
                max_reductions=self.max_reductions,
                armijo_c=self.armijo_c,
                policy_source=self.policy_source,
                failure_reason=NonlinearFailureReason.LINE_SEARCH_FAILURE,
                policy_id=ROBUSTNESS_POLICY_ID,
                policy_version=ROBUSTNESS_POLICY_VERSION,
            )
            if raise_on_failure:
                self._raise_line_search_failure(result)
            return result

        standard_candidates: list[tuple[float, int, str, int]] = []
        alpha = 1.0
        for reductions in range(self.max_reductions + 1):
            if alpha < self.min_alpha:
                break
            standard_candidates.append((alpha, reductions, "canonical_backtracking", 0))
            alpha *= 0.5
        standard_alpha_set = {candidate[0] for candidate in standard_candidates}
        supplemental_candidates: list[tuple[float, int, str, int]] = []
        seen_supplemental: set[float] = set()
        for alpha_value in supplemental_alphas:
            candidate_alpha = float(alpha_value)
            if (
                not np.isfinite(candidate_alpha)
                or candidate_alpha <= 0.0
                or candidate_alpha > 1.0
                or candidate_alpha < self.min_alpha
                or candidate_alpha in standard_alpha_set
                or candidate_alpha in seen_supplemental
            ):
                continue
            seen_supplemental.add(candidate_alpha)
            supplemental_candidates.append(
                (candidate_alpha, self.max_reductions, "contact_event_refinement", len(supplemental_candidates) + 1)
            )
        candidates = standard_candidates + supplemental_candidates
        merits: list[float] = []
        trial_diagnostics: list[Mapping[str, Any]] = []
        last_payload: object | None = None
        supplemental_count = 0
        for alpha, reductions, candidate_phase, supplemental_index in candidates:
            try:
                evaluation = self._coerce_evaluation(evaluate(alpha))
            except (ValueError, FloatingPointError) as exc:
                evaluation = LineSearchEvaluation(
                    merit=float("inf"),
                    diagnostics={"evaluation_error": str(exc)},
                )
            merit = float(evaluation.merit)
            merits.append(merit)
            evaluation_diagnostics = dict(evaluation.diagnostics)
            if candidate_phase != "canonical_backtracking":
                evaluation_diagnostics.update(
                    {
                        "candidate_phase": candidate_phase,
                        "supplemental_trial": supplemental_index,
                    }
                )
                supplemental_count += 1
            trial_diagnostics.append(evaluation_diagnostics)
            last_payload = evaluation.payload
            if np.isfinite(merit):
                if self.armijo_c is None:
                    accepted = merit < initial
                else:
                    accepted = merit <= (1.0 - self.armijo_c * alpha) * initial
                if accepted:
                    result = LineSearchResult(
                        accepted=True,
                        factor=alpha,
                        reductions=reductions,
                        merit_history=tuple(merits),
                        accepted_factors=(alpha,),
                        initial_merit=initial,
                        min_alpha=self.min_alpha,
                        max_reductions=self.max_reductions,
                        armijo_c=self.armijo_c,
                        policy_source=self.policy_source,
                        payload=last_payload,
                        trial_diagnostics=tuple(trial_diagnostics),
                        supplemental_trials=supplemental_count,
                    )
                    return result

        result = LineSearchResult(
            accepted=False,
            factor=None,
            reductions=max(len(standard_candidates) - 1, 0),
            merit_history=tuple(merits),
            accepted_factors=(),
            initial_merit=initial,
            min_alpha=self.min_alpha,
            max_reductions=self.max_reductions,
            armijo_c=self.armijo_c,
            policy_source=self.policy_source,
            failure_reason=NonlinearFailureReason.LINE_SEARCH_FAILURE,
            payload=None,
            trial_diagnostics=tuple(trial_diagnostics),
            supplemental_trials=supplemental_count,
        )
        if raise_on_failure:
            self._raise_line_search_failure(result)
        return result

    @staticmethod
    def _coerce_evaluation(value: LineSearchEvaluation | tuple[object, ...] | float) -> LineSearchEvaluation:
        if isinstance(value, LineSearchEvaluation):
            return value
        if isinstance(value, tuple):
            if len(value) == 2:
                return LineSearchEvaluation(float(cast(Any, value[0])), value[1])
            if len(value) == 3:
                diagnostics = value[2]
                if not isinstance(diagnostics, Mapping):
                    raise TypeError("Line-search evaluation diagnostics must be a mapping.")
                return LineSearchEvaluation(float(cast(Any, value[0])), value[1], diagnostics)
            raise TypeError("Line-search tuple evaluations must contain two or three values.")
        return LineSearchEvaluation(float(cast(Any, value)))

    @staticmethod
    def _raise_line_search_failure(result: LineSearchResult) -> None:
        raise NumericalConvergenceError(
            "Nonlinear line search failed to satisfy its merit condition.",
            reason=NonlinearFailureReason.LINE_SEARCH_FAILURE,
            diagnostics=result.to_dict(),
        )


@dataclass(frozen=True)
class NonlinearRobustnessOptions:
    """Validated, opt-in controls used only by robustness experiments."""

    linear_solver: str = "spsolve"
    linear_preconditioner: str = "none"
    linear_assume_spd: bool = False
    linear_rtol: float = 1.0e-10
    linear_atol: float = 1.0e-14
    linear_maxiter: int = 10_000
    linear_residual_tolerance: float = 1.0e-10
    linear_backward_error_tolerance: float = 1.0e-10
    linear_absolute_floor: float = 1.0e-14
    linear_symmetry_tolerance: float = 1.0e-12
    linear_direct_fallback: bool = True
    jacobi_diagonal_floor: float = 1.0e-14
    ilu_drop_tol: float = 1.0e-4
    ilu_fill_factor: float = 10.0
    gmres_restart: int = 50
    linear_permutation: str = "COLAMD"
    system_scaling: str = "none"
    residual_scaling: str = "none"
    line_search: str = "existing"
    line_search_min_alpha: float = 1.0e-4
    line_search_max_reductions: int = 14
    line_search_c: float = 1.0e-4
    floor_aware_termination: bool = False

    @classmethod
    def from_parameters(cls, parameters: dict[str, object]) -> "NonlinearRobustnessOptions | None":
        """Return controls only when an explicit experimental parameter is present."""
        if not _PARAMETER_KEYS.intersection(parameters):
            return None
        options = cls(
            linear_solver=str(parameters.get("experimental_linear_solver", "spsolve")).lower(),
            linear_preconditioner=str(parameters.get("experimental_linear_preconditioner", "none")).lower(),
            linear_assume_spd=bool(parameters.get("experimental_linear_assume_spd", False)),
            linear_rtol=float(cast(Any, parameters.get("experimental_linear_rtol", 1.0e-10))),
            linear_atol=float(cast(Any, parameters.get("experimental_linear_atol", 1.0e-14))),
            linear_maxiter=int(cast(Any, parameters.get("experimental_linear_maxiter", 10_000))),
            linear_residual_tolerance=float(
                cast(Any, parameters.get("experimental_linear_residual_tolerance", 1.0e-10))
            ),
            linear_backward_error_tolerance=float(
                cast(Any, parameters.get("experimental_linear_backward_error_tolerance", 1.0e-10))
            ),
            linear_absolute_floor=float(cast(Any, parameters.get("experimental_linear_absolute_floor", 1.0e-14))),
            linear_symmetry_tolerance=float(
                cast(Any, parameters.get("experimental_linear_symmetry_tolerance", 1.0e-12))
            ),
            linear_direct_fallback=bool(parameters.get("experimental_linear_direct_fallback", True)),
            jacobi_diagonal_floor=float(cast(Any, parameters.get("experimental_jacobi_diagonal_floor", 1.0e-14))),
            ilu_drop_tol=float(cast(Any, parameters.get("experimental_ilu_drop_tol", 1.0e-4))),
            ilu_fill_factor=float(cast(Any, parameters.get("experimental_ilu_fill_factor", 10.0))),
            gmres_restart=int(cast(Any, parameters.get("experimental_gmres_restart", 50))),
            linear_permutation=str(parameters.get("experimental_linear_permutation", "COLAMD")).upper(),
            system_scaling=str(parameters.get("experimental_system_scaling", "none")).lower(),
            residual_scaling=str(parameters.get("experimental_residual_scaling", "none")).lower(),
            line_search=str(parameters.get("experimental_line_search", "existing")).lower(),
            line_search_min_alpha=float(cast(Any, parameters.get("experimental_line_search_min_alpha", 1.0e-4))),
            line_search_max_reductions=int(cast(Any, parameters.get("experimental_line_search_max_reductions", 14))),
            line_search_c=float(cast(Any, parameters.get("experimental_line_search_c", 1.0e-4))),
            floor_aware_termination=bool(parameters.get("experimental_floor_aware_termination", False)),
        )
        options.validate()
        return options

    def validate(self) -> None:
        if self.linear_solver not in {"spsolve", "splu", "direct", "auto", "cg", "minres", "gmres"}:
            raise ValueError("experimental_linear_solver is not a supported nonlinear linear method.")
        if self.linear_preconditioner not in {"none", "jacobi", "ilu"}:
            raise ValueError("experimental_linear_preconditioner must be 'none', 'jacobi' or 'ilu'.")
        for name, value in (
            ("experimental_linear_rtol", self.linear_rtol),
            ("experimental_linear_atol", self.linear_atol),
            ("experimental_linear_residual_tolerance", self.linear_residual_tolerance),
            ("experimental_linear_backward_error_tolerance", self.linear_backward_error_tolerance),
            ("experimental_linear_absolute_floor", self.linear_absolute_floor),
            ("experimental_linear_symmetry_tolerance", self.linear_symmetry_tolerance),
            ("experimental_jacobi_diagonal_floor", self.jacobi_diagonal_floor),
            ("experimental_ilu_drop_tol", self.ilu_drop_tol),
            ("experimental_ilu_fill_factor", self.ilu_fill_factor),
        ):
            if not isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and positive.")
        if self.linear_maxiter < 1:
            raise ValueError("experimental_linear_maxiter must be positive.")
        if self.gmres_restart < 1:
            raise ValueError("experimental_gmres_restart must be positive.")
        if self.linear_permutation not in _PERMUTATIONS:
            raise ValueError("experimental_linear_permutation is not a supported SciPy permutation.")
        if self.system_scaling not in {"none", "symmetric_diagonal"}:
            raise ValueError("experimental_system_scaling must be 'none' or 'symmetric_diagonal'.")
        if self.residual_scaling not in {"none", "row_max"}:
            raise ValueError("experimental_residual_scaling must be 'none' or 'row_max'.")
        if self.system_scaling != "none" and self.residual_scaling != "none":
            raise ValueError("Use one experimental linear scaling mechanism at a time.")
        if self.line_search not in {"existing", "off", "armijo"}:
            raise ValueError("experimental_line_search must be 'existing', 'off' or 'armijo'.")
        if not isfinite(self.line_search_min_alpha) or not 0.0 < self.line_search_min_alpha <= 1.0:
            raise ValueError("experimental_line_search_min_alpha must be in (0, 1].")
        if self.line_search_max_reductions < 0:
            raise ValueError("experimental_line_search_max_reductions must be non-negative.")
        if not isfinite(self.line_search_c) or not 0.0 <= self.line_search_c < 1.0:
            raise ValueError("experimental_line_search_c must be in [0, 1).")

    def to_dict(self) -> dict[str, Any]:
        return {
            "linear_solver": self.linear_solver,
            "linear_preconditioner": self.linear_preconditioner,
            "linear_assume_spd": self.linear_assume_spd,
            "linear_rtol": self.linear_rtol,
            "linear_atol": self.linear_atol,
            "linear_maxiter": self.linear_maxiter,
            "linear_residual_tolerance": self.linear_residual_tolerance,
            "linear_backward_error_tolerance": self.linear_backward_error_tolerance,
            "linear_absolute_floor": self.linear_absolute_floor,
            "linear_symmetry_tolerance": self.linear_symmetry_tolerance,
            "linear_direct_fallback": self.linear_direct_fallback,
            "jacobi_diagonal_floor": self.jacobi_diagonal_floor,
            "ilu_drop_tol": self.ilu_drop_tol,
            "ilu_fill_factor": self.ilu_fill_factor,
            "gmres_restart": self.gmres_restart,
            "linear_permutation": self.linear_permutation,
            "system_scaling": self.system_scaling,
            "residual_scaling": self.residual_scaling,
            "line_search": self.line_search,
            "line_search_min_alpha": self.line_search_min_alpha,
            "line_search_max_reductions": self.line_search_max_reductions,
            "line_search_c": self.line_search_c,
            "floor_aware_termination": self.floor_aware_termination,
        }


def solve_scaled_system(
    matrix: csr_matrix,
    rhs: np.ndarray,
    options: NonlinearRobustnessOptions,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Solve one reduced Newton system with an explicitly selected experiment."""
    options.validate()
    values = csr_matrix(matrix)
    vector = np.asarray(rhs, dtype=float)
    if values.shape[0] != values.shape[1] or vector.shape != (values.shape[0],):
        raise ValueError("Experimental nonlinear linear system has incompatible dimensions.")
    if not np.all(np.isfinite(values.data)) or not np.all(np.isfinite(vector)):
        raise ValueError("Experimental nonlinear linear system must be finite.")

    factors = np.ones(values.shape[0], dtype=float)
    scaling = "none"
    if options.system_scaling == "symmetric_diagonal":
        diagonal = np.abs(values.diagonal())
        active = diagonal > 0.0
        factors[active] = 1.0 / np.sqrt(diagonal[active])
        effective = diags(factors) @ values @ diags(factors)
        effective_rhs = factors * vector
        scaling = options.system_scaling
    elif options.residual_scaling == "row_max":
        row_max = np.asarray(np.abs(values).sum(axis=1)).ravel()
        active = row_max > 0.0
        factors[active] = 1.0 / row_max[active]
        effective = diags(factors) @ values
        effective_rhs = factors * vector
        scaling = options.residual_scaling
    else:
        effective = values
        effective_rhs = vector

    if options.linear_solver == "splu":
        solution = splu(effective.tocsc(), permc_spec=options.linear_permutation).solve(effective_rhs)
        backend = "scipy.sparse.linalg.splu"
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("error", MatrixRankWarning)
            solution = spsolve(effective.tocsc(), effective_rhs, permc_spec=options.linear_permutation)
        backend = "scipy.sparse.linalg.spsolve"

    if options.system_scaling == "symmetric_diagonal":
        solution = factors * solution
    solution = np.asarray(solution, dtype=float)
    if not np.all(np.isfinite(solution)):
        raise ValueError("Experimental nonlinear linear solve returned a non-finite correction.")
    return solution, {
        "backend": backend,
        "permutation": options.linear_permutation,
        "scaling": scaling,
        "factor_min": float(np.min(factors)) if factors.size else 1.0,
        "factor_max": float(np.max(factors)) if factors.size else 1.0,
    }
