"""WP03-B focused tests for the common stagnation and line-search authority."""

from __future__ import annotations

import inspect

import numpy as np
import pytest
from scipy.sparse import diags

from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.driver import ContributionResponse, UnifiedNewtonEngine
from solveur.core.nonlinear.iteration import (
    _line_search_assembly_with_diagnostics,
    _line_search_factor_with_result,
    line_search_factor,
    solve_full_newton,
)
from solveur.core.nonlinear.robustness import (
    LineSearchEvaluation,
    NonlinearRobustnessOptions,
    RobustnessPolicySource,
    UnifiedNonlinearRobustnessController,
)
from solveur.core.nonlinear.state import NonlinearState


def _controller(**kwargs: object) -> UnifiedNonlinearRobustnessController:
    return UnifiedNonlinearRobustnessController(**kwargs)


def test_t03b_01_common_controller_has_one_frozen_policy_identity() -> None:
    controller = _controller()
    diagnostics = controller.configuration_diagnostics()
    assert diagnostics["policy_id"] == "qf-solver-unified-robustness"
    assert diagnostics["policy_version"] == 1


def test_t03b_02_stagnation_window_below_four_is_not_a_failure() -> None:
    decision = _controller().stagnation_decision([1.0, 1.0, 1.0])
    assert decision.reason is None
    assert decision.decision == "INSUFFICIENT_HISTORY"


def test_t03b_03_exactly_four_strictly_decreasing_samples_continue() -> None:
    decision = _controller().stagnation_decision([4.0, 3.0, 2.0, 1.0])
    assert decision.reason is None
    assert decision.decision == "CONTINUE"


def test_t03b_04_stagnation_threshold_boundary_is_inclusive() -> None:
    controller = _controller()
    final = 1.0 * (1.0 - controller.plateau_threshold)
    decision = controller.stagnation_decision([1.0, 1.0, 1.0, final])
    assert decision.reason is NonlinearFailureReason.CONVERGENCE_STAGNATION
    assert decision.decision == "STAGNATION"


def test_t03b_05_decrease_beyond_threshold_is_not_stagnation() -> None:
    controller = _controller()
    final = 1.0 - 1.1 * controller.plateau_threshold
    decision = controller.stagnation_decision([1.0, 1.0, 1.0, final])
    assert decision.reason is None
    assert decision.decision == "CONTINUE"


def test_t03b_06_decrease_inside_threshold_is_stagnation() -> None:
    controller = _controller()
    final = 1.0 - 0.9 * controller.plateau_threshold
    decision = controller.stagnation_decision([1.0, 1.0, 1.0, final])
    assert decision.reason is NonlinearFailureReason.CONVERGENCE_STAGNATION


def test_t03b_07_oscillatory_history_uses_the_frozen_window_rule() -> None:
    decision = _controller().stagnation_decision([1.0, 0.5, 1.1, 0.9])
    assert decision.reason is None
    assert decision.decision == "CONTINUE"
    assert decision.relative_change == pytest.approx(0.1)


def test_t03b_08_convergence_precedes_stagnation() -> None:
    decision = _controller().stagnation_decision(
        [1.0, 1.0, 1.0, 1.0], converged=True, convergence_tolerance=1.0e-8
    )
    assert decision.decision == "CONVERGED"
    assert decision.reason is None


def test_t03b_09_nan_has_explicit_nonfinite_reason() -> None:
    decision = _controller().stagnation_decision([1.0, np.nan, 1.0, 1.0])
    assert decision.reason is NonlinearFailureReason.NAN_DETECTED
    assert decision.decision == "NONFINITE"


def test_t03b_10_inf_has_explicit_nonfinite_reason() -> None:
    decision = _controller().stagnation_decision([1.0, np.inf, 1.0, 1.0])
    assert decision.reason is NonlinearFailureReason.INF_DETECTED
    assert decision.decision == "NONFINITE"


def test_t03b_11_disabled_stagnation_is_observable_without_failure() -> None:
    decision = _controller(stagnation_enabled=False).stagnation_decision([1.0] * 4)
    assert decision.decision == "DISABLED"
    assert decision.reason is None


def test_t03b_12_stagnation_diagnostics_are_complete_and_deterministic() -> None:
    controller = _controller()
    first = controller.stagnation_decision([4.0, 3.0, 2.0, 1.0], convergence_tolerance=1.0e-8).to_dict()
    second = controller.stagnation_decision([4.0, 3.0, 2.0, 1.0], convergence_tolerance=1.0e-8).to_dict()
    assert first == second
    assert {
        "window",
        "window_size",
        "plateau_threshold",
        "initial_window_residual",
        "final_window_residual",
        "relative_change",
        "convergence_tolerance",
        "decision",
        "policy_id",
        "policy_version",
    }.issubset(first)


def test_t03b_13_line_search_accepts_full_step_on_strict_decrease() -> None:
    result = _controller().line_search(2.0, lambda alpha: LineSearchEvaluation(1.0, payload=alpha))
    assert result.accepted is True
    assert result.factor == 1.0
    assert result.reductions == 0


def test_t03b_14_line_search_halves_after_rejected_full_step() -> None:
    result = _controller().line_search(1.0, lambda alpha: LineSearchEvaluation(alpha))
    assert result.factor == 0.5
    assert result.reductions == 1
    assert result.merit_history == (1.0, 0.5)


def test_t03b_15_line_search_records_multiple_reductions() -> None:
    result = _controller().line_search(
        1.0,
        lambda alpha: LineSearchEvaluation(1.0 if alpha >= 0.5 else 0.5),
    )
    assert result.factor == 0.25
    assert result.reductions == 2
    assert result.accepted_factors == (0.25,)


def test_t03b_16_line_search_floor_failure_is_canonical() -> None:
    controller = _controller(min_alpha=0.5, max_reductions=12)
    with pytest.raises(NumericalConvergenceError) as error:
        controller.line_search(1.0, lambda _alpha: LineSearchEvaluation(1.0))
    assert error.value.reason is NonlinearFailureReason.LINE_SEARCH_FAILURE
    assert error.value.diagnostics["min_alpha"] == 0.5


def test_t03b_17_line_search_reduction_budget_is_bounded() -> None:
    controller = _controller(min_alpha=0.0, max_reductions=2)
    with pytest.raises(NumericalConvergenceError) as error:
        controller.line_search(1.0, lambda _alpha: LineSearchEvaluation(1.0))
    assert len(error.value.diagnostics["merit_history"]) == 3
    assert error.value.diagnostics["reductions"] == 2


def test_t03b_18_explicit_armijo_accepts_the_contract_boundary() -> None:
    controller = _controller(armijo_c=0.1)
    result = controller.line_search(1.0, lambda alpha: LineSearchEvaluation(1.0 - 0.1 * alpha))
    assert result.accepted is True
    assert result.factor == 1.0
    assert result.armijo_c == 0.1


def test_t03b_19_default_strict_policy_rejects_equal_merit() -> None:
    controller = _controller(max_reductions=0)
    with pytest.raises(NumericalConvergenceError) as error:
        controller.line_search(1.0, lambda _alpha: LineSearchEvaluation(1.0))
    assert error.value.reason is NonlinearFailureReason.LINE_SEARCH_FAILURE


def test_t03b_20_line_search_callback_receives_deterministic_alpha_sequence() -> None:
    seen: list[float] = []

    def evaluate(alpha: float) -> LineSearchEvaluation:
        seen.append(alpha)
        return LineSearchEvaluation(1.0)

    with pytest.raises(NumericalConvergenceError):
        _controller(min_alpha=0.25, max_reductions=5).line_search(1.0, evaluate)
    assert seen == [1.0, 0.5, 0.25]


def test_t03b_21_line_search_does_not_mutate_callback_owned_trial_state() -> None:
    state = np.zeros(2)
    before = state.copy()

    def evaluate(alpha: float) -> LineSearchEvaluation:
        candidate = state.copy()
        candidate[0] += alpha
        return LineSearchEvaluation(float(np.linalg.norm(candidate)), payload=candidate)

    result = _controller().line_search(1.0, evaluate)
    assert state.tolist() == before.tolist()
    assert result.payload is not None


def test_t03b_22_empty_options_select_public_default_policy() -> None:
    controller = UnifiedNonlinearRobustnessController.from_options(None)
    assert controller.policy_source == RobustnessPolicySource.PUBLIC_DEFAULT.value
    assert controller.min_alpha == 1.0e-4
    assert controller.max_reductions == 12
    assert controller.armijo_c is None


def test_t03b_23_existing_option_is_explicit_compatibility_override() -> None:
    controller = UnifiedNonlinearRobustnessController.from_options(NonlinearRobustnessOptions())
    assert controller.policy_source == RobustnessPolicySource.EXPERIMENTAL_OVERRIDE.value
    assert controller.min_alpha == 0.0
    assert controller.max_reductions == 14
    assert controller.armijo_c is None


def test_t03b_24_armijo_option_is_explicit_experimental_override() -> None:
    options = NonlinearRobustnessOptions(line_search="armijo", line_search_c=2.0e-4)
    controller = UnifiedNonlinearRobustnessController.from_options(options)
    assert controller.policy_source == RobustnessPolicySource.EXPERIMENTAL_OVERRIDE.value
    assert controller.armijo_c == 2.0e-4
    assert controller.min_alpha == options.line_search_min_alpha


class _IdentityContribution:
    name = "identity"

    def evaluate(self, state: NonlinearState) -> ContributionResponse:
        return ContributionResponse(
            self.name,
            state.displacement.copy(),
            diags([1.0, 1.0], format="csr"),
        )


def _run_identity_engine(*, max_iterations: int = 4, stagnation_check: bool = True):
    return UnifiedNewtonEngine().solve(
        initial_state=NonlinearState(np.zeros(2)),
        external_force=np.asarray([1.0, 0.0]),
        fixed=np.asarray([1]),
        target_load_factors=(1.0,),
        tolerance=1.0e-12,
        max_iterations=max_iterations,
        contributions=(_IdentityContribution(),),
        linear_solve=lambda _matrix, rhs: (np.asarray(rhs, dtype=float), None),
        stagnation_check=stagnation_check,
    )


def test_t03b_25_engine_success_contains_common_robustness_diagnostics() -> None:
    result = _run_identity_engine()
    increment = result.diagnostics["increments"][0]
    assert increment["robustness"]["policy_id"] == "qf-solver-unified-robustness"
    assert increment["robustness"]["stagnation"]["decision"] == "CONVERGED"


def test_t03b_26_engine_stagnation_uses_common_failure_reason_and_payload() -> None:
    class FlatContribution:
        name = "flat"

        def evaluate(self, state: NonlinearState) -> ContributionResponse:
            return ContributionResponse(
                self.name,
                np.zeros(2),
                diags([1.0, 1.0], format="csr"),
            )

    with pytest.raises(NumericalConvergenceError) as error:
        UnifiedNewtonEngine().solve(
            initial_state=NonlinearState(np.zeros(2)),
            external_force=np.asarray([1.0, 0.0]),
            fixed=np.asarray([1]),
            target_load_factors=(1.0,),
            tolerance=1.0e-12,
            max_iterations=5,
            contributions=(FlatContribution(),),
            linear_solve=lambda _matrix, _rhs: (np.asarray([0.0]), None),
        )
    assert error.value.reason is NonlinearFailureReason.CONVERGENCE_STAGNATION
    assert error.value.diagnostics["robustness"]["stagnation"]["window_size"] == 4


def test_t03b_27_full_newton_adapter_publishes_common_policy_diagnostics() -> None:
    class IdentityAssembly:
        ndof = 2

        def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
            return np.asarray(displacement, dtype=float), diags([1.0, 1.0], format="csr")

    _, diagnostics = solve_full_newton(
        IdentityAssembly(),
        np.asarray([1.0, 0.0]),
        np.asarray([1]),
        increments=1,
        tolerance=1.0e-12,
        max_iterations=4,
    )
    policy = diagnostics["increments"][0]["diagnostics"]["robustness"]
    assert policy["policy_source"] == "PUBLIC_DEFAULT"
    assert policy["line_search"]["events"][0]["factor"] == 1.0


def test_t03b_28_assembly_compatibility_wrapper_delegates_to_common_policy() -> None:
    class IdentityAssembly:
        ndof = 2

        def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
            return np.asarray(displacement, dtype=float), diags([1.0, 1.0], format="csr")

    trial, reductions = _line_search_assembly_with_diagnostics(
        IdentityAssembly(),
        np.zeros(2),
        np.asarray([0]),
        np.asarray([1.0]),
        np.asarray([1.0, 0.0]),
        1.0,
    )
    assert trial[0] == 1.0
    assert reductions == 0


def test_t03b_29_stateful_factor_wrapper_and_result_share_common_policy() -> None:
    def assemble(model, dofs, displacement, material_states):
        del model, dofs, material_states
        return np.asarray(displacement, dtype=float), None, {}

    result = _line_search_factor_with_result(
        assemble,
        object(),
        object(),
        np.zeros(1),
        np.asarray([0]),
        np.asarray([1.0]),
        {},
        np.asarray([1.0]),
        1.0,
        1.0e-4,
        12,
        1.0e-4,
    )
    assert result.factor == 1.0
    assert line_search_factor(
        assemble,
        object(),
        object(),
        np.zeros(1),
        np.asarray([0]),
        np.asarray([1.0]),
        {},
        np.asarray([1.0]),
        1.0,
        1.0e-4,
        12,
        1.0e-4,
    ) == (1.0, 0)


def test_t03b_30_compatibility_helpers_have_no_second_policy_loop() -> None:
    helper_sources = [
        inspect.getsource(_line_search_assembly_with_diagnostics),
        inspect.getsource(line_search_factor),
        inspect.getsource(_line_search_factor_with_result),
    ]
    assert all("for reductions" not in source for source in helper_sources)
    controller_source = inspect.getsource(UnifiedNonlinearRobustnessController.line_search)
    assert controller_source.count("for reductions in") == 1
