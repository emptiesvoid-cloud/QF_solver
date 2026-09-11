"""Independent adversarial closure checks for the WP03 robustness boundary."""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear import arc_length, iteration, load_control, robustness
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.controls import AdaptiveLoadControls, ArcLengthControls
from solveur.core.nonlinear.driver import (
    RetryClassification,
    UnifiedContinuationController,
    continuation_retry_classification,
)
from solveur.core.nonlinear.robustness import (
    LineSearchEvaluation,
    UnifiedAdaptiveStepPolicy,
    UnifiedArcLengthRadiusPolicy,
    UnifiedNonlinearRobustnessController,
)
from solveur.core.nonlinear.state import NonlinearState, deterministic_state_digest


def _adaptive_controls(**overrides: object) -> AdaptiveLoadControls:
    parameters: dict[str, object] = {
        "initial_load_increment": 0.4,
        "min_load_increment": 0.1,
        "max_load_increment": 0.8,
        "cutback_factor": 0.5,
        "growth_factor": 1.5,
        "grow_below_iterations": 3,
        "shrink_above_iterations": 8,
        "max_cutbacks": 2,
    }
    parameters.update(overrides)
    return AdaptiveLoadControls.from_parameters(parameters, load_steps=1, max_iterations=20)


def _arc_controls(**overrides: object) -> ArcLengthControls:
    parameters: dict[str, object] = {
        "adaptive_arc_length": True,
        "min_arc_length_radius": 1.0e-8,
        "arc_length_growth_factor": 1.5,
        "arc_length_shrink_factor": 0.5,
        "arc_length_grow_below_iterations": 3,
        "arc_length_shrink_above_iterations": 8,
    }
    parameters.update(overrides)
    return ArcLengthControls.from_parameters(parameters, max_iterations=20)


def test_wp03e_01_single_authorities_and_no_policy_state_commit() -> None:
    robustness_source = inspect.getsource(robustness)
    arc_source = inspect.getsource(arc_length.NonlinearArcLengthMixin._solve_arc_length)
    iteration_source = inspect.getsource(iteration)
    load_source = inspect.getsource(load_control)

    assert robustness_source.count("class UnifiedNonlinearRobustnessController") == 1
    assert robustness_source.count("class UnifiedAdaptiveStepPolicy") == 1
    assert robustness_source.count("class UnifiedArcLengthRadiusPolicy") == 1
    assert arc_source.count("UnifiedArcLengthRadiusPolicy(") == 1
    assert arc_source.count("radius_policy.on_failure(") == 1
    assert iteration_source.count("adaptive_policy = UnifiedAdaptiveStepPolicy(") == 1
    assert load_source.count("adaptive_policy = UnifiedAdaptiveStepPolicy(") == 1
    # Both legacy helpers are thin adapters to the sole robustness policy;
    # neither contains an independent alpha-reduction loop.
    assert inspect.getsource(iteration._line_search_assembly_with_result).count("policy.line_search(") == 1
    assert inspect.getsource(iteration._line_search_factor_with_result).count("policy.line_search(") == 1

    for policy in (
        UnifiedNonlinearRobustnessController,
        UnifiedAdaptiveStepPolicy,
        UnifiedArcLengthRadiusPolicy,
    ):
        source = inspect.getsource(policy)
        assert ".commit(" not in source
        assert ".rollback(" not in source
        assert "NonlinearStateTransaction" not in source


def test_wp03e_02_failure_taxonomy_is_deterministic_and_complete() -> None:
    expected = {
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
    }
    for reason, classification in expected.items():
        first = continuation_retry_classification(NumericalConvergenceError("audit", reason=reason))
        second = continuation_retry_classification(NumericalConvergenceError("audit", reason=reason))
        assert first is classification
        assert second is classification
    assert continuation_retry_classification(RuntimeError("unknown")) is RetryClassification.OWNER_POLICY_DEPENDENT


def test_wp03e_03_stagnation_boundaries_and_nonfinite_precedence() -> None:
    controller = UnifiedNonlinearRobustnessController()
    threshold = controller.plateau_threshold
    assert controller.stagnation_decision([1.0] * 3).decision == "INSUFFICIENT_HISTORY"
    assert controller.stagnation_decision([1.0, 1.0, 1.0, 1.0 - threshold]).reason is NonlinearFailureReason.CONVERGENCE_STAGNATION
    assert controller.stagnation_decision([1.0, 1.0, 1.0, 1.0 - 1.1 * threshold]).decision == "CONTINUE"
    assert controller.stagnation_decision([1.0, 0.5, 1.1, 0.9]).decision == "CONTINUE"
    assert controller.stagnation_decision([1.0e300, 1.0e300, 1.0e300, 1.0e300]).reason is NonlinearFailureReason.CONVERGENCE_STAGNATION
    assert controller.stagnation_decision([1.0e-300] * 4).reason is NonlinearFailureReason.CONVERGENCE_STAGNATION
    assert controller.stagnation_decision([1.0, np.nan, 1.0, 1.0], converged=True).reason is NonlinearFailureReason.NAN_DETECTED
    assert controller.stagnation_decision([1.0, np.inf, 1.0, 1.0], converged=True).reason is NonlinearFailureReason.INF_DETECTED
    assert controller.stagnation_decision([1.0] * 4, converged=True).decision == "CONVERGED"


def test_wp03e_04_line_search_boundaries_are_single_loop_and_state_safe() -> None:
    controller = UnifiedNonlinearRobustnessController(min_alpha=0.25, max_reductions=4)
    state = NonlinearState(np.zeros(2), material_state={"ip": {"p": 0.0}})
    before = state.digest

    full = controller.line_search(1.0, lambda alpha: LineSearchEvaluation(0.5, payload=alpha))
    assert full.factor == pytest.approx(1.0)
    halved = controller.line_search(1.0, lambda alpha: LineSearchEvaluation(2.0 if alpha == 1.0 else 0.5))
    assert halved.factor == pytest.approx(0.5)
    armijo = UnifiedNonlinearRobustnessController(armijo_c=0.5)
    assert armijo.line_search(1.0, lambda alpha: LineSearchEvaluation(0.5)).accepted is True
    failed = controller.line_search(1.0, lambda alpha: LineSearchEvaluation(2.0), raise_on_failure=False)
    assert failed.accepted is False
    assert failed.failure_reason is NonlinearFailureReason.LINE_SEARCH_FAILURE
    callback_failure = controller.line_search(
        1.0,
        lambda alpha: (_ for _ in ()).throw(ValueError("assembly callback failure")),
        raise_on_failure=False,
    )
    assert callback_failure.accepted is False
    assert state.digest == before
    assert inspect.getsource(UnifiedNonlinearRobustnessController.line_search).count("alpha *= 0.5") == 1


def test_wp03e_05_adaptive_terminal_boundaries_are_exact_and_repeatable() -> None:
    controls = _adaptive_controls()
    policy = UnifiedAdaptiveStepPolicy(controls)
    equal = policy.on_failure(
        base_load_factor=0.0,
        proposed_increment=0.2,
        failure_reason=NonlinearFailureReason.MAX_ITERATIONS,
        retry_classification=RetryClassification.RETRYABLE,
        rejected_count=1,
    )
    below = UnifiedAdaptiveStepPolicy(controls).on_failure(
        base_load_factor=0.0,
        proposed_increment=0.19,
        failure_reason=NonlinearFailureReason.MAX_ITERATIONS,
        retry_classification=RetryClassification.RETRYABLE,
        rejected_count=1,
    )
    at_budget = UnifiedAdaptiveStepPolicy(controls).on_failure(
        base_load_factor=0.0,
        proposed_increment=0.4,
        failure_reason=NonlinearFailureReason.MAX_ITERATIONS,
        retry_classification=RetryClassification.RETRYABLE,
        rejected_count=2,
    )
    assert equal.decision == "RETRY_CUTBACK"
    assert below.decision == "TERMINAL_MIN_INCREMENT"
    assert at_budget.decision == "TERMINAL_MAX_CUTBACKS"
    assert deterministic_state_digest(equal.to_dict()) == deterministic_state_digest(
        UnifiedAdaptiveStepPolicy(controls)
        .on_failure(
            base_load_factor=0.0,
            proposed_increment=0.2,
            failure_reason=NonlinearFailureReason.MAX_ITERATIONS,
            retry_classification=RetryClassification.RETRYABLE,
            rejected_count=1,
        )
        .to_dict()
    )


def test_wp03e_06_rollback_preserves_every_accepted_component() -> None:
    controller = UnifiedContinuationController(
        NonlinearState(
            np.zeros(2),
            load_factor=0.2,
            material_state={"ip": {"plastic": 0.0}},
            contact_state={"pair": {"active": False}},
            continuation_state={"radius": 0.1, "previous_du": [0.0, 0.0]},
            accepted_increment_metadata={"step": 2},
        )
    )
    before = controller.accepted_digest
    for reason in (NonlinearFailureReason.MAX_ITERATIONS, NonlinearFailureReason.CONVERGENCE_STAGNATION):
        trial = controller.begin_trial()
        trial.displacement[:] = 9.0
        trial.load_factor = 0.8
        trial.material_state["ip"]["plastic"] = 2.0
        trial.contact_state["pair"]["active"] = True
        trial.continuation_state["radius"] = 0.01
        trial.accepted_increment_metadata["step"] = 99
        controller.rollback(NumericalConvergenceError("retry", reason=reason), path="wp03-e")
        assert controller.accepted_digest == before
        assert controller.rejection_log[-1]["accepted_digest_before"] == before
        assert controller.rejection_log[-1]["accepted_digest_after"] == before


def test_wp03e_07_arc_policy_keeps_correction_algebra_outside_policy() -> None:
    policy = UnifiedArcLengthRadiusPolicy(_arc_controls())
    decision = policy.on_failure(
        accepted_step=0,
        base_load_factor=0.0,
        policy_radius=0.1,
        effective_attempt_radius=0.0035355339059327385,
        maximum_radius=0.2,
        failure_reason=NonlinearFailureReason.MAX_ITERATIONS,
        retry_classification=RetryClassification.RETRYABLE,
        rejected_count=1,
        rollback_verified=True,
    )
    assert decision.decision == "RETRY_SHRINK"
    assert decision.effective_retry_radius is not None
    assert decision.effective_retry_radius < decision.effective_attempt_radius
    assert "solve_arc_length_correction" not in inspect.getsource(UnifiedArcLengthRadiusPolicy)
    assert "previous_du" not in inspect.getsource(UnifiedArcLengthRadiusPolicy)
    assert "previous_dlambda" not in inspect.getsource(UnifiedArcLengthRadiusPolicy)


def test_wp03e_08_policy_mapping_diagnostics_are_order_independent() -> None:
    first = {"a": {"z": [1, 2], "y": (3, 4)}, "reason": "MAX_ITERATIONS"}
    second = {"reason": "MAX_ITERATIONS", "a": {"y": (3, 4), "z": [1, 2]}}
    assert deterministic_state_digest(first) == deterministic_state_digest(second)
    assert deterministic_state_digest({1: "value"}) != deterministic_state_digest({"1": "value"})
