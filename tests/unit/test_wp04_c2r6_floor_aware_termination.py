"""Prospective WP04-C2R6 floor-aware termination controls."""

from __future__ import annotations

import numpy as np
from scipy.sparse import diags

from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.driver import ContributionResponse, UnifiedNewtonEngine
from solveur.core.nonlinear.robustness import (
    NonlinearRobustnessOptions,
    UnifiedNonlinearRobustnessController,
)
from solveur.core.nonlinear.state import NonlinearState


def _controller() -> UnifiedNonlinearRobustnessController:
    return UnifiedNonlinearRobustnessController(floor_aware_termination=True)


def _positive_inputs() -> dict[str, object]:
    # The deliberately scaled synthetic system makes the state-resolution
    # estimate observable without encoding a residual multiplier.  The
    # acceptance decision still requires every independent evidence item.
    return {
        "residual_history": [1.01e-10, 1.0100001e-10, 1.0099999e-10, 1.01e-10],
        "relative_residual": 1.01e-10,
        "convergence_tolerance": 1.0e-10,
        "correction": np.full(4, 1.0e-10),
        "displacement": np.full(4, 1.0e6),
        "tangent": diags(np.full(4, 1.0e6), format="csr"),
        "residual_scale": 1.0,
        "linear_backward_error": 1.0e-12,
        "line_search_improvement_available": False,
        "force_equilibrium": 1.0e-12,
        "moment_equilibrium": 1.0e-12,
        "state_valid": True,
    }


def _decision(**updates: object):
    values = _positive_inputs()
    values.update(updates)
    return _controller().floor_aware_decision(**values)


def test_c2r6_option_is_opt_in_and_serializable() -> None:
    assert UnifiedNonlinearRobustnessController().floor_aware_termination is False
    options = NonlinearRobustnessOptions.from_parameters(
        {"experimental_floor_aware_termination": True}
    )
    assert options is not None
    assert options.floor_aware_termination is True
    assert options.to_dict()["floor_aware_termination"] is True


def test_c2r6_positive_stationary_equilibrium_is_accepted() -> None:
    result = _decision()
    assert result.decision == "FLOOR_CONVERGED"
    assert result.reason == "NUMERICALLY_STATIONARY_EQUILIBRIUM"


def test_c2r6_primary_convergence_precedes_secondary_path() -> None:
    result = _decision(relative_residual=1.0e-11)
    assert result.decision == "PRIMARY_CONVERGED"
    assert result.reason == "PRIMARY_RESIDUAL_CRITERION"


def test_c2r6_disabled_policy_fails_closed() -> None:
    values = _positive_inputs()
    result = UnifiedNonlinearRobustnessController().floor_aware_decision(**values)
    assert result.decision == "REJECT"
    assert result.reason == "DISABLED"


def test_c2r6_early_large_residual_is_rejected() -> None:
    result = _decision(
        residual_history=[1.0e-1] * 4,
        relative_residual=1.0e-1,
    )
    assert result.decision == "REJECT"
    assert result.reason == "RESIDUAL_ABOVE_STATE_RESOLUTION"


def test_c2r6_poor_force_equilibrium_is_rejected() -> None:
    result = _decision(force_equilibrium=1.0e-3)
    assert result.decision == "REJECT"
    assert result.reason == "FORCE_EQUILIBRIUM_UNBOUNDED"


def test_c2r6_available_merit_improvement_is_rejected() -> None:
    result = _decision(line_search_improvement_available=True)
    assert result.decision == "REJECT"
    assert result.reason == "LINE_SEARCH_IMPROVEMENT_UNKNOWN_OR_AVAILABLE"


def test_c2r6_nonstationary_plateau_is_rejected() -> None:
    result = _decision(
        residual_history=[1.01e-10, 1.01e-10, 1.01e-10, 1.0e-3],
        relative_residual=1.01e-10,
    )
    assert result.decision == "REJECT"
    assert result.reason == "RESIDUAL_NOT_STATIONARY"


def test_c2r6_correction_above_resolution_is_rejected() -> None:
    result = _decision(correction=np.full(4, 1.0e3))
    assert result.decision == "REJECT"
    assert result.reason == "CORRECTION_ABOVE_MACHINE_RESOLUTION"


def test_c2r6_invalid_linear_correction_is_rejected() -> None:
    result = _decision(linear_backward_error=1.0e-5)
    assert result.decision == "REJECT"
    assert result.reason == "LINEAR_CORRECTION_NOT_VALID"


def test_c2r6_invalid_state_is_rejected() -> None:
    result = _decision(state_valid=False)
    assert result.decision == "REJECT"
    assert result.reason == "INVALID_STATE_EVIDENCE"


def test_c2r6_nonfinite_state_is_rejected() -> None:
    result = _decision(displacement=np.full(4, np.nan))
    assert result.decision == "REJECT"
    assert result.reason == "STATE_RESOLUTION_UNAVAILABLE"


def test_c2r6_nonfinite_history_is_rejected() -> None:
    result = _decision(residual_history=[1.0e-10, np.nan, 1.0e-10, 1.0e-10])
    assert result.decision == "REJECT"
    assert result.reason == "NONFINITE_RESIDUAL_HISTORY"


def test_c2r6_insufficient_history_is_rejected() -> None:
    result = _decision(residual_history=[1.01e-10] * 3)
    assert result.decision == "REJECT"
    assert result.reason == "PLATEAU_HISTORY_INSUFFICIENT"


def test_c2r6_missing_equilibrium_evidence_is_rejected() -> None:
    result = _decision(moment_equilibrium=None)
    assert result.decision == "REJECT"
    assert result.reason == "MOMENT_EQUILIBRIUM_UNAVAILABLE"


def test_c2r6_matrix_resolution_gate_rejects_residual_above_floor() -> None:
    result = _decision(
        tangent=diags(np.ones(4), format="csr"),
        displacement=np.ones(4),
        residual_scale=1.0,
        relative_residual=1.0e-8,
        residual_history=[1.0e-8] * 4,
    )
    assert result.decision == "REJECT"
    assert result.reason == "RESIDUAL_ABOVE_STATE_RESOLUTION"


def test_c2r6_diagnostics_are_deterministic_and_complete() -> None:
    first = _decision().to_dict()
    second = _decision().to_dict()
    assert first == second
    for key in (
        "relative_residual",
        "convergence_tolerance",
        "relative_correction_norm",
        "machine_epsilon",
        "correction_resolution_threshold",
        "plateau_window",
        "plateau_spread",
        "state_resolution_residual_estimate",
        "component_ulp_residual_estimate",
        "linear_backward_error",
        "line_search_improvement_available",
        "force_equilibrium",
        "moment_equilibrium",
        "decision",
        "reason",
    ):
        assert key in first


def test_c2r6_engine_accepts_floor_before_line_search_failure() -> None:
    class PlateauContribution:
        def __init__(self) -> None:
            self.calls = 0

        def evaluate(self, state):
            del state
            self.calls += 1
            residual = [1.10e-10, 1.08e-10, 1.06e-10, 1.041e-10][min(self.calls - 1, 3)]
            target = np.full(2, 0.1)
            return ContributionResponse(
                "synthetic",
                target - residual,
                diags(np.full(2, 1.0e6), format="csr"),
            )

    contribution = PlateauContribution()
    line_calls = 0

    def line_search(state, free, correction, target, residual_norm):
        del free, correction, target, residual_norm
        nonlocal line_calls
        line_calls += 1
        if line_calls < 4:
            return state.displacement.copy(), 0, {"factor": 1.0, "accepted": True}
        raise NumericalConvergenceError(
            "controlled floor test line-search failure",
            reason=NonlinearFailureReason.LINE_SEARCH_FAILURE,
            diagnostics={
                "initial_merit": 1.041e-10,
                "merit_history": [2.0e-10, 1.5e-10],
                "reductions": 1,
            },
        )

    accepted: list[str] = []
    options = NonlinearRobustnessOptions(
        line_search="existing",
        floor_aware_termination=True,
    )
    controller = UnifiedNonlinearRobustnessController.from_options(options)
    result = UnifiedNewtonEngine().solve(
        initial_state=NonlinearState(np.full(2, 1.0e6)),
        external_force=np.full(2, 0.1),
        fixed=np.asarray([], dtype=int),
        target_load_factors=[1.0],
        tolerance=1.0e-10,
        max_iterations=5,
        contributions=(contribution,),
        linear_solve=lambda matrix, rhs: (np.zeros(rhs.size), {"backward_error_eta_inf": 1.0e-12}),
        line_search=line_search,
        robustness_controller=controller,
        accepted_state_callback=lambda _step, state: accepted.append(state.digest),
        floor_aware_evidence=lambda *_args: {
            "state_valid": True,
            "force_equilibrium": 1.0e-12,
            "moment_equilibrium": 1.0e-12,
        },
    )
    assert result.diagnostics["increments"][0]["termination_classification"] == "CONVERGED_NUMERICAL_FLOOR"
    assert result.diagnostics["increments"][0]["floor_aware"]["decision"] == "FLOOR_CONVERGED"
    assert len(accepted) == 1
