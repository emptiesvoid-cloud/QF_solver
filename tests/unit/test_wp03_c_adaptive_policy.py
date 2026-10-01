"""Focused WP03-C tests for the common adaptive increment policy."""

from __future__ import annotations

import inspect

import numpy as np
import pytest
from scipy.sparse import eye

from solveur.api import solve_model
from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.controls import AdaptiveLoadControls
from solveur.core.nonlinear.driver import RetryClassification, UnifiedContinuationController
from solveur.core.nonlinear.iteration import solve_adaptive_full_newton
from solveur.core.nonlinear.robustness import (
    UnifiedAdaptiveStepPolicy,
    UnifiedNonlinearRobustnessController,
)
from solveur.core.nonlinear.state import NonlinearState, deterministic_state_digest
from solveur.verification.robustness_mesh import run_adversarial_rollback_benchmark
from tests.unit.test_analysis_features import elastoplastic_tet4_model


def _controls(**overrides: object) -> AdaptiveLoadControls:
    parameters: dict[str, object] = {
        "initial_load_increment": 1.0,
        "min_load_increment": 0.1,
        "max_load_increment": 1.0,
        "cutback_factor": 0.5,
        "growth_factor": 1.5,
        "grow_below_iterations": 3,
        "shrink_above_iterations": 8,
        "max_cutbacks": 3,
    }
    parameters.update(overrides)
    return AdaptiveLoadControls.from_parameters(parameters, load_steps=1, max_iterations=20)


class _IdentityAssembly:
    ndof = 2

    def __init__(self, failures: int = 0) -> None:
        self.failures = failures

    def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
        if self.failures:
            self.failures -= 1
            raise NumericalConvergenceError(
                "controlled adaptive failure",
                reason=NonlinearFailureReason.MAX_ITERATIONS,
            )
        return np.array([displacement[0], 0.0]), eye(2, format="csr")


def _run_stateless(*, failures: int = 0, initial_state: NonlinearState | None = None, **control_overrides: object):
    return solve_adaptive_full_newton(
        _IdentityAssembly(failures),
        np.array([1.0, 0.0]),
        np.array([1]),
        increments=1,
        tolerance=1.0e-8,
        max_iterations=5,
        controls=_controls(**control_overrides),
        initial_state=initial_state,
    )


def _decision(policy: UnifiedAdaptiveStepPolicy, iterations: int):
    return policy.on_accept(
        base_load_factor=0.0,
        policy_increment=0.4,
        proposed_increment=0.4,
        iterations=iterations,
        cutback_count=0,
    )


def test_t03c_01_common_adaptive_policy_default_controls() -> None:
    policy = UnifiedAdaptiveStepPolicy(_controls())
    assert policy.controls.cutback_factor == pytest.approx(0.5)
    assert policy.controls.growth_factor == pytest.approx(1.5)
    assert policy.controls.maximum_cutbacks == 3
    assert policy.configuration_diagnostics()["policy_id"] == "qf-solver-unified-adaptive-step"


def test_t03c_02_easy_convergence_uses_keep_decision() -> None:
    assert _decision(UnifiedAdaptiveStepPolicy(_controls()), 4).decision == "ACCEPT_KEEP"


def test_t03c_03_easy_convergence_grows_inclusively() -> None:
    decision = _decision(UnifiedAdaptiveStepPolicy(_controls()), 3)
    assert decision.decision == "ACCEPT_GROW"
    assert decision.next_increment == pytest.approx(0.6)


def test_t03c_04_expensive_convergence_shrinks_inclusively() -> None:
    decision = _decision(UnifiedAdaptiveStepPolicy(_controls()), 8)
    assert decision.decision == "ACCEPT_SHRINK"
    assert decision.next_increment == pytest.approx(0.2)


def test_t03c_05_growth_is_capped_at_maximum() -> None:
    decision = _decision(
        UnifiedAdaptiveStepPolicy(_controls(initial_load_increment=0.5, max_load_increment=0.5)),
        1,
    )
    assert decision.next_increment == pytest.approx(0.5)


def test_t03c_06_shrink_is_floored_at_minimum() -> None:
    decision = _decision(UnifiedAdaptiveStepPolicy(_controls(min_load_increment=0.3)), 20)
    assert decision.next_increment == pytest.approx(0.3)


def test_t03c_07_retryable_failure_requests_cutback() -> None:
    decision = UnifiedAdaptiveStepPolicy(_controls()).on_failure(
        base_load_factor=0.0,
        proposed_increment=0.8,
        failure_reason=NonlinearFailureReason.MAX_ITERATIONS,
        retry_classification=RetryClassification.RETRYABLE,
        rejected_count=1,
    )
    assert decision.decision == "RETRY_CUTBACK"
    assert decision.retry_increment == pytest.approx(0.4)


def test_t03c_08_non_retryable_failure_is_terminal() -> None:
    decision = UnifiedAdaptiveStepPolicy(_controls()).on_failure(
        base_load_factor=0.0,
        proposed_increment=0.8,
        failure_reason=NonlinearFailureReason.MATERIAL_UPDATE_FAILURE,
        retry_classification=RetryClassification.NON_RETRYABLE,
        rejected_count=1,
    )
    assert decision.decision == "TERMINAL_NON_RETRYABLE"


def test_t03c_09_owner_policy_failure_follows_explicit_policy() -> None:
    error = dict(
        base_load_factor=0.0,
        proposed_increment=0.8,
        failure_reason=NonlinearFailureReason.SINGULAR_TANGENT,
        retry_classification=RetryClassification.OWNER_POLICY_DEPENDENT,
        rejected_count=1,
    )
    assert UnifiedAdaptiveStepPolicy(_controls(), allow_owner_policy=True).on_failure(**error).decision == "RETRY_CUTBACK"
    assert UnifiedAdaptiveStepPolicy(_controls(), allow_owner_policy=False).on_failure(**error).decision == "TERMINAL_NON_RETRYABLE"


def test_t03c_10_checkpoint_failure_never_cutbacks() -> None:
    decision = UnifiedAdaptiveStepPolicy(_controls()).on_failure(
        base_load_factor=0.0,
        proposed_increment=0.8,
        failure_reason=NonlinearFailureReason.CHECKPOINT_FAILURE,
        retry_classification=RetryClassification.NON_RETRYABLE,
        rejected_count=1,
    )
    assert decision.decision == "TERMINAL_NON_RETRYABLE"
    assert decision.retry_increment == pytest.approx(0.4)


def test_t03c_11_rollback_digest_is_exact_before_retry() -> None:
    controller = UnifiedContinuationController(
        NonlinearState(np.zeros(2), material_state={"ip": {"plastic": 0.0}})
    )
    before = controller.accepted_digest
    trial = controller.begin_trial()
    trial.displacement[0] = 7.0
    trial.material_state["ip"]["plastic"] = 4.0
    controller.rollback(
        NumericalConvergenceError("retry", reason=NonlinearFailureReason.MAX_ITERATIONS),
        path="wp03-c",
    )
    assert controller.accepted_digest == before


def test_t03c_12_repeated_retries_start_from_accepted_digest() -> None:
    controller = UnifiedContinuationController(NonlinearState(np.zeros(1)))
    before = controller.accepted_digest
    for _ in range(2):
        trial = controller.begin_trial()
        trial.displacement[0] = 10.0
        controller.rollback(
            NumericalConvergenceError("retry", reason=NonlinearFailureReason.MAX_ITERATIONS),
            path="wp03-c",
        )
        assert controller.accepted_digest == before
        assert controller.rejection_log[-1]["accepted_digest_before"] == before
        assert controller.rejection_log[-1]["accepted_digest_after"] == before


def test_t03c_13_minimum_boundary_just_above_is_retryable() -> None:
    decision = UnifiedAdaptiveStepPolicy(_controls(min_load_increment=0.1)).on_failure(
        base_load_factor=0.0,
        proposed_increment=0.21,
        failure_reason=NonlinearFailureReason.MAX_ITERATIONS,
        retry_classification=RetryClassification.RETRYABLE,
        rejected_count=1,
    )
    assert decision.decision == "RETRY_CUTBACK"
    assert decision.retry_increment == pytest.approx(0.105)


def test_t03c_14_minimum_boundary_equal_is_permitted() -> None:
    decision = UnifiedAdaptiveStepPolicy(_controls(min_load_increment=0.1)).on_failure(
        base_load_factor=0.0,
        proposed_increment=0.2,
        failure_reason=NonlinearFailureReason.MAX_ITERATIONS,
        retry_classification=RetryClassification.RETRYABLE,
        rejected_count=1,
    )
    assert decision.decision == "RETRY_CUTBACK"
    assert decision.retry_increment == pytest.approx(0.1)


def test_t03c_15_minimum_boundary_below_is_terminal() -> None:
    decision = UnifiedAdaptiveStepPolicy(_controls(min_load_increment=0.1)).on_failure(
        base_load_factor=0.0,
        proposed_increment=0.19,
        failure_reason=NonlinearFailureReason.MAX_ITERATIONS,
        retry_classification=RetryClassification.RETRYABLE,
        rejected_count=1,
    )
    assert decision.decision == "TERMINAL_MIN_INCREMENT"


def test_t03c_16_max_cutbacks_boundary_before_budget_is_retryable() -> None:
    decision = UnifiedAdaptiveStepPolicy(_controls(max_cutbacks=2)).on_failure(
        base_load_factor=0.0,
        proposed_increment=0.8,
        failure_reason=NonlinearFailureReason.MAX_ITERATIONS,
        retry_classification=RetryClassification.RETRYABLE,
        rejected_count=1,
    )
    assert decision.decision == "RETRY_CUTBACK"


def test_t03c_17_max_cutbacks_boundary_at_budget_is_terminal() -> None:
    decision = UnifiedAdaptiveStepPolicy(_controls(max_cutbacks=2)).on_failure(
        base_load_factor=0.0,
        proposed_increment=0.8,
        failure_reason=NonlinearFailureReason.MAX_ITERATIONS,
        retry_classification=RetryClassification.RETRYABLE,
        rejected_count=2,
    )
    assert decision.decision == "TERMINAL_MAX_CUTBACKS"


def test_t03c_18_max_cutbacks_boundary_has_no_extra_attempt() -> None:
    policy = UnifiedAdaptiveStepPolicy(_controls(max_cutbacks=2))
    decision = policy.on_failure(
        base_load_factor=0.0,
        proposed_increment=0.8,
        failure_reason=NonlinearFailureReason.MAX_ITERATIONS,
        retry_classification=RetryClassification.RETRYABLE,
        rejected_count=3,
    )
    assert decision.decision == "TERMINAL_MAX_CUTBACKS"
    assert decision.next_increment is None


def test_t03c_19_stateless_route_delegates_to_common_policy() -> None:
    _, diagnostics = _run_stateless(growth_factor=1.0)
    policy = diagnostics["adaptive_policy"]
    assert policy["policy_id"] == "qf-solver-unified-adaptive-step"
    assert len(policy["decisions"]) == 1


def test_t03c_20_stateful_route_delegates_to_common_policy() -> None:
    model = elastoplastic_tet4_model()
    model.analysis.parameters.update(
        {
            "adaptive_load_steps": True,
            "initial_load_increment": 1.0,
            "min_load_increment": 0.1,
            "max_load_increment": 1.0,
            "growth_factor": 1.0,
        }
    )
    data = solve_model(model).to_dict()["solver"]["adaptive_policy"]
    assert data["policy_id"] == "qf-solver-unified-adaptive-step"
    assert data["decisions"]


def test_t03c_21_no_duplicate_adaptive_decision_loop_remains() -> None:
    from solveur.core.nonlinear import iteration, load_control, robustness

    stateless_source = inspect.getsource(iteration.solve_adaptive_full_newton)
    stateful_source = inspect.getsource(load_control.NonlinearLoadControlMixin._solve_adaptive_load_steps)
    assert stateless_source.count("UnifiedAdaptiveStepPolicy") == 1
    assert stateful_source.count("UnifiedAdaptiveStepPolicy") == 1
    assert inspect.getsource(robustness).count("class UnifiedAdaptiveStepPolicy") == 1
    for source in (stateless_source, stateful_source):
        assert "if next_iterations <= controls.grow_below_iterations" not in source
        assert "proposed *= controls.cutback_factor" not in source
        assert "rejected_increments > controls.maximum_cutbacks" not in source


def test_t03c_22_b08_easy_adaptive_preservation() -> None:
    _, diagnostics = _run_stateless(growth_factor=1.0)
    assert diagnostics["rejected_increments"] == 0
    assert diagnostics["increments"][0]["load_factor"] == pytest.approx(1.0)


def test_t03c_23_b09_forced_cutback() -> None:
    _, diagnostics = _run_stateless(failures=1, growth_factor=1.0)
    assert diagnostics["rejected_increments"] == 1
    assert diagnostics["rejection_log"][0]["retry_increment"] == pytest.approx(0.5)


def test_t03c_24_b10_multiple_cutbacks() -> None:
    _, diagnostics = _run_stateless(failures=3, max_cutbacks=4, growth_factor=1.0)
    assert diagnostics["rejected_increments"] == 3
    assert [item["retry_increment"] for item in diagnostics["rejection_log"]] == pytest.approx(
        [0.5, 0.25, 0.125]
    )


def test_t03c_25_b11_minimum_increment_failure() -> None:
    with pytest.raises(NumericalConvergenceError) as raised:
        _run_stateless(failures=1, min_load_increment=0.75, growth_factor=1.0)
    assert raised.value.reason is NonlinearFailureReason.MIN_INCREMENT_REACHED


def test_t03c_26_max_cutback_terminal_campaign() -> None:
    with pytest.raises(NumericalConvergenceError) as raised:
        _run_stateless(failures=5, max_cutbacks=2, min_load_increment=0.01, growth_factor=1.0)
    assert raised.value.reason is NonlinearFailureReason.MAX_ITERATIONS
    assert raised.value.diagnostics["rejected_increments"] == 2


def test_t03c_27_adaptive_restart_next_increment_is_preserved() -> None:
    state = NonlinearState(np.zeros(2), continuation_state={"next_increment": 0.25})
    _, diagnostics = _run_stateless(initial_state=state, growth_factor=1.0)
    assert diagnostics["increments"][0]["load_increment"] == pytest.approx(0.25)


def test_t03c_28_adaptive_restart_rejection_path_is_preserved() -> None:
    state = NonlinearState(np.zeros(2), continuation_state={"next_increment": 0.5})
    _, diagnostics = _run_stateless(initial_state=state, failures=1, growth_factor=1.0)
    assert diagnostics["rejection_log"][0]["rejected_increment"] == pytest.approx(0.5)
    assert diagnostics["rejection_log"][0]["retry_increment"] == pytest.approx(0.25)


def test_t03c_29_final_target_clipping_does_not_corrupt_policy_increment() -> None:
    policy = UnifiedAdaptiveStepPolicy(_controls(max_load_increment=1.0))
    proposed = policy.propose_increment(0.75, 0.75)
    decision = policy.on_accept(
        base_load_factor=0.75,
        policy_increment=0.75,
        proposed_increment=proposed,
        iterations=1,
        cutback_count=0,
    )
    assert proposed == pytest.approx(0.25)
    assert decision.clipped_to_target is True
    assert decision.next_increment == pytest.approx(1.0)


def test_t03c_30_path_dependent_material_rollback_integrity() -> None:
    state = NonlinearState(
        np.zeros(1),
        material_state={"element": {"ip": [{"plastic": 0.25}]}},
        contact_state={"pair": {"active": False}},
    )
    controller = UnifiedContinuationController(state)
    before = controller.accepted_component_digests
    trial = controller.begin_trial()
    trial.material_state["element"]["ip"][0]["plastic"] = 9.0
    trial.contact_state["pair"]["active"] = True
    controller.rollback(
        NumericalConvergenceError("retry", reason=NonlinearFailureReason.MAX_ITERATIONS),
        path="wp03-c",
    )
    assert controller.accepted_component_digests == before


def test_t03c_31_caller_material_changes_only_on_commit() -> None:
    controller = UnifiedContinuationController(
        NonlinearState(np.zeros(1), material_state={"ip": {"plastic": 0.0}})
    )
    trial = controller.begin_trial()
    trial.material_state["ip"]["plastic"] = 1.0
    assert controller.accepted_state.material_state["ip"]["plastic"] == pytest.approx(0.0)
    controller.commit()
    assert controller.accepted_state.material_state["ip"]["plastic"] == pytest.approx(1.0)
    assert controller.transaction.commit_count == 1


def test_t03c_32_signature_mismatch_debt_is_resolved_as_fixture_stale() -> None:
    result = run_adversarial_rollback_benchmark()
    assert result["status"] == "PASS_INTERNAL_ROLLBACK"
    source = inspect.getsource(run_adversarial_rollback_benchmark)
    assert "commit_to_inputs" in source


def test_t03c_33_failure_diagnostics_are_deterministic() -> None:
    def run() -> str:
        policy = UnifiedAdaptiveStepPolicy(_controls())
        decisions = [
            policy.on_failure(
                base_load_factor=0.0,
                proposed_increment=value,
                failure_reason=NonlinearFailureReason.MAX_ITERATIONS,
                retry_classification=RetryClassification.RETRYABLE,
                rejected_count=index,
            ).to_dict()
            for index, value in enumerate((0.8, 0.4), start=1)
        ]
        return deterministic_state_digest(decisions)

    assert run() == run()


def test_t03c_34_policy_diagnostics_are_mapping_order_independent() -> None:
    first = {"b": {"2": [1, 2]}, "a": (3, 4)}
    second = {"a": (3, 4), "b": {"2": [1, 2]}}
    assert deterministic_state_digest(first) == deterministic_state_digest(second)
    assert deterministic_state_digest({1: "value"}) != deterministic_state_digest({"1": "value"})


def test_t03c_35_wp03b_stagnation_and_line_search_remain_available() -> None:
    controller = UnifiedNonlinearRobustnessController(
        stagnation_window=3,
        plateau_threshold=1.0e-3,
        line_search_enabled=True,
        min_alpha=0.1,
        max_reductions=3,
    )
    stagnation = controller.stagnation_decision([1.0, 0.9999, 0.9998])
    line_search = controller.line_search(
        1.0,
        lambda alpha: 2.0 if alpha == 1.0 else 0.5,
        raise_on_failure=False,
    )
    assert stagnation.reason is NonlinearFailureReason.CONVERGENCE_STAGNATION
    assert line_search.accepted is True
    assert line_search.factor == pytest.approx(0.5)
