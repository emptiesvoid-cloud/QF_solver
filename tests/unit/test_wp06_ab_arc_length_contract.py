"""WP06-A/B lightweight contract tests for arc-length state and failure guards."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.arc_length import NonlinearArcLengthMixin
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.driver import UnifiedContinuationController
from solveur.core.nonlinear.iteration import solve_arc_length_correction
from solveur.core.nonlinear.linear_solver import NonlinearLinearSolverAdapter
from solveur.core.nonlinear.state import NonlinearState


class _PredictorAdapter:
    def __init__(self, predictor: np.ndarray) -> None:
        self.predictor = np.asarray(predictor, dtype=float)

    def solve(self, matrix: csr_matrix, rhs: np.ndarray, *, method: str) -> tuple[np.ndarray, object]:
        del matrix, rhs, method
        return self.predictor.copy(), SimpleNamespace(converged=True)


class _ArcLengthRadiusProbe(NonlinearArcLengthMixin):
    def __init__(self, predictor: np.ndarray) -> None:
        self.linear_solver = _PredictorAdapter(predictor)

    def _assemble_internal_tangent(self, *args: object) -> tuple[np.ndarray, csr_matrix, dict[str, object]]:
        del args
        return np.zeros(1), csr_matrix([[2.0]]), {}


def _continuation_state() -> NonlinearState:
    return NonlinearState(
        np.zeros(2),
        load_factor=0.0,
        material_state={"element": {"plastic": 0.0}},
        contact_state={"pair": {"active": False}},
        continuation_state={
            "accepted_step": 0,
            "load_factor": 0.0,
            "radius": 0.1,
            "maximum_radius": 0.2,
            "load_scale": 1.0,
            "previous_du": [0.0, 0.0],
            "previous_dlambda": 0.0,
        },
    )


@pytest.mark.parametrize(
    ("predictor", "expected_scale"),
    [
        (np.array([0.0]), 1.0e-12),
        (np.array([1.0e-15]), 1.0e-12),
        (np.array([2.0]), 2.0),
        (np.array([-2.0]), 2.0),
    ],
)
def test_wp06a_initial_radius_is_finite_for_zero_and_oriented_predictors(
    predictor: np.ndarray,
    expected_scale: float,
) -> None:
    probe = _ArcLengthRadiusProbe(predictor)
    radius, scale = probe._initial_arc_length_radius(
        None,
        None,
        np.zeros(1),
        np.array([0]),
        np.ones(1),
        {},
        2,
        "direct",
    )
    assert np.isfinite(radius)
    assert scale == pytest.approx(expected_scale)


def test_wp06a_nonfinite_linear_input_is_typed_and_fail_closed() -> None:
    with pytest.raises(NumericalConvergenceError) as raised:
        NonlinearLinearSolverAdapter().solve(csr_matrix([[1.0]]), np.array([np.nan]))
    assert raised.value.reason is NonlinearFailureReason.NAN_DETECTED


def test_wp06a_augmented_correction_success_and_singular_failure_are_typed() -> None:
    correction, load_increment = solve_arc_length_correction(
        csr_matrix([[2.0]]),
        np.array([1.0]),
        np.array([0.5]),
        np.array([0.2]),
        0.1,
        0.05,
        1.0,
    )
    assert np.all(np.isfinite(correction))
    assert np.isfinite(load_increment)

    with pytest.raises(NumericalConvergenceError) as raised:
        solve_arc_length_correction(
            csr_matrix([[0.0]]),
            np.array([0.0]),
            np.array([0.0]),
            np.array([0.0]),
            0.0,
            0.0,
            1.0,
        )
    assert raised.value.reason is NonlinearFailureReason.ARC_LENGTH_FAILURE


def test_wp06a_nonfinite_augmented_correction_is_rejected() -> None:
    with pytest.raises(NumericalConvergenceError) as raised:
        solve_arc_length_correction(
            csr_matrix([[1.0]]),
            np.array([1.0]),
            np.array([np.inf]),
            np.array([0.0]),
            0.0,
            0.0,
            1.0,
        )
    assert raised.value.reason is NonlinearFailureReason.ARC_LENGTH_FAILURE


def test_wp06b_rejected_trials_preserve_two_accepted_composite_digests() -> None:
    controller = UnifiedContinuationController(_continuation_state())
    accepted_s0 = controller.accepted_digest

    trial = controller.begin_trial()
    trial.displacement[:] = 3.0
    trial.load_factor = 0.4
    trial.material_state["element"]["plastic"] = 1.0
    trial.contact_state["pair"]["active"] = True
    trial.continuation_state["radius"] = 0.05
    controller.rollback(
        NumericalConvergenceError("trial rejected", reason=NonlinearFailureReason.MAX_ITERATIONS),
        path="arc_length",
    )
    assert controller.accepted_digest == accepted_s0

    trial = controller.begin_trial()
    trial.displacement[:] = 0.2
    trial.load_factor = 0.1
    trial.continuation_state["accepted_step"] = 1
    controller.commit()
    accepted_s1 = controller.accepted_digest
    assert accepted_s1 != accepted_s0

    trial = controller.begin_trial()
    trial.displacement[:] = -4.0
    trial.load_factor = 0.8
    trial.continuation_state["radius"] = 0.01
    controller.rollback(
        NumericalConvergenceError("second trial rejected", reason=NonlinearFailureReason.MAX_ITERATIONS),
        path="arc_length",
    )
    assert controller.accepted_digest == accepted_s1
    rejection = controller.rejection_log[-1]
    assert rejection["accepted_digest_before"] == accepted_s1
    assert rejection["accepted_digest_after"] == accepted_s1


@pytest.mark.parametrize(
    "state",
    [
        pytest.param(
            {"load_factor": np.nan},
            id="nan-load-factor",
        ),
        pytest.param(
            {"continuation_state": {"radius": np.inf}},
            id="inf-radius",
        ),
    ],
)
def test_wp06b_nonfinite_state_fields_fail_closed(state: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        NonlinearState(np.zeros(2), **state)
