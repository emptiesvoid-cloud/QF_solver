import numpy as np
import pytest
from scipy.sparse import eye

from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear_controls import AdaptiveLoadControls
from solveur.core.nonlinear_contracts import NonlinearFailureReason
from solveur.core.nonlinear_iteration import solve_adaptive_full_newton, solve_full_newton


def _controls(**overrides: object) -> AdaptiveLoadControls:
    parameters: dict[str, object] = {
        "initial_load_increment": 1.0,
        "min_load_increment": 0.1,
        "max_load_increment": 1.0,
        "cutback_factor": 0.5,
        "growth_factor": 1.0,
        "grow_below_iterations": 2,
        "shrink_above_iterations": 10,
        "max_cutbacks": 4,
    }
    parameters.update(overrides)
    return AdaptiveLoadControls.from_parameters(parameters, load_steps=1, max_iterations=5)


class _RejectOnceAssembly:
    ndof = 2

    def __init__(self) -> None:
        self.calls = 0

    def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
        self.calls += 1
        if self.calls == 1:
            raise NumericalConvergenceError(
                "controlled failed increment",
                reason=NonlinearFailureReason.MAX_ITERATIONS,
            )
        return np.array([displacement[0], 0.0]), eye(2, format="csr")


class _AlwaysFailAssembly:
    ndof = 2

    def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
        raise NumericalConvergenceError(
            "controlled failed increment",
            reason=NonlinearFailureReason.MAX_ITERATIONS,
        )


def test_adaptive_full_newton_rolls_back_and_retries_from_committed_state() -> None:
    assembly = _RejectOnceAssembly()

    displacement, diagnostics = solve_adaptive_full_newton(
        assembly,
        np.array([1.0, 0.0]),
        np.array([1]),
        increments=1,
        tolerance=1.0e-8,
        max_iterations=5,
        controls=_controls(),
    )

    np.testing.assert_array_equal(displacement, np.array([1.0, 0.0]))
    assert diagnostics["rejected_increments"] == 1
    assert diagnostics["increments"][0]["load_factor"] == pytest.approx(0.5)
    assert diagnostics["increments"][0]["load_step_cutbacks"] == 1
    assert diagnostics["rejection_log"][0]["rollback_before_retry"] is True
    assert diagnostics["rejection_log"][0]["failure_reason"] == "MAX_ITERATIONS"


def test_adaptive_full_newton_fails_closed_at_max_cutbacks() -> None:
    with pytest.raises(NumericalConvergenceError) as raised:
        solve_adaptive_full_newton(
            _AlwaysFailAssembly(),
            np.array([1.0, 0.0]),
            np.array([1]),
            increments=1,
            tolerance=1.0e-8,
            max_iterations=5,
            controls=_controls(max_cutbacks=2),
        )

    assert raised.value.reason is NonlinearFailureReason.MAX_ITERATIONS
    assert raised.value.diagnostics["rejected_increments"] == 2
    assert all(item["rollback_before_retry"] for item in raised.value.diagnostics["rejection_log"])


def test_adaptive_full_newton_fails_closed_at_minimum_increment() -> None:
    with pytest.raises(NumericalConvergenceError) as raised:
        solve_adaptive_full_newton(
            _AlwaysFailAssembly(),
            np.array([1.0, 0.0]),
            np.array([1]),
            increments=1,
            tolerance=1.0e-8,
            max_iterations=5,
            controls=_controls(min_load_increment=0.75, max_cutbacks=4),
        )

    assert raised.value.reason is NonlinearFailureReason.MIN_INCREMENT_REACHED
    assert raised.value.diagnostics["minimum_increment"] == pytest.approx(0.75)


def test_adaptive_full_newton_retry_schedule_is_deterministic() -> None:
    runs = []
    for _ in range(2):
        _, diagnostics = solve_adaptive_full_newton(
            _RejectOnceAssembly(),
            np.array([1.0, 0.0]),
            np.array([1]),
            increments=1,
            tolerance=1.0e-8,
            max_iterations=5,
            controls=_controls(),
        )
        runs.append(
            (
                [
                    (step["load_factor"], step["load_increment"], step["load_step_cutbacks"])
                    for step in diagnostics["increments"]
                ],
                [
                    (item["base_load_factor"], item["rejected_increment"], item["retry_increment"])
                    for item in diagnostics["rejection_log"]
                ],
            )
        )

    assert runs[0] == runs[1]


def test_fixed_full_newton_keeps_historical_no_retry_behavior() -> None:
    with pytest.raises(NumericalConvergenceError) as raised:
        solve_full_newton(
            _AlwaysFailAssembly(),
            np.array([1.0, 0.0]),
            np.array([1]),
            increments=1,
            tolerance=1.0e-8,
            max_iterations=5,
        )

    assert raised.value.reason is NonlinearFailureReason.MAX_ITERATIONS
    assert "rejection_log" not in raised.value.diagnostics
