"""WP06-C lightweight predictor, corrector and constraint identity tests."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.controls import ArcLengthControls
from solveur.core.nonlinear.iteration import solve_arc_length_correction
from solveur.core.solvers.linear import LinearSystemSolver
from solveur.verification.robustness_arc_length import run_shallow_arch_arc_length_benchmark


def test_wp06c_predictor_linear_identity() -> None:
    tangent = csr_matrix([[2.0, 0.0], [0.0, 3.0]])
    reference_load = np.array([1.0, -2.0])
    predictor, info = LinearSystemSolver().solve(tangent, reference_load, method="direct")
    relative_residual = float(
        np.linalg.norm(tangent @ predictor - reference_load)
        / max(float(np.linalg.norm(reference_load)), 1.0)
    )
    assert info.converged
    assert relative_residual <= 1.0e-11


@pytest.mark.parametrize(
    ("radius", "load_scale"),
    [
        (1.0e-3, 0.5),
        (5.0e-2, 1.0),
        (4.0e-1, 2.0),
    ],
)
def test_wp06c_spherical_constraint_identity(radius: float, load_scale: float) -> None:
    delta_u = np.array([0.6 * radius, -0.2 * radius])
    remaining = radius**2 - float(delta_u @ delta_u)
    delta_lambda = np.sqrt(remaining) / load_scale
    constraint = float(delta_u @ delta_u + (load_scale * delta_lambda) ** 2 - radius**2)
    assert abs(constraint) / max(radius**2, 1.0) <= 1.0e-12


def test_wp06c_production_constraint_row_is_analytical(monkeypatch: pytest.MonkeyPatch) -> None:
    import solveur.core.nonlinear.iteration as iteration

    captured: dict[str, np.ndarray] = {}

    def capture_spsolve(matrix: object, rhs: np.ndarray) -> np.ndarray:
        captured["matrix"] = matrix.toarray()  # type: ignore[union-attr]
        del rhs
        return np.zeros(3)

    monkeypatch.setattr(iteration, "spsolve", capture_spsolve)
    solve_arc_length_correction(
        csr_matrix([[3.0, 0.2], [0.2, 4.0]]),
        np.array([1.0, -2.0]),
        np.zeros(2),
        np.array([0.2, -0.3]),
        0.4,
        0.0,
        0.7,
    )
    expected = np.array(
        [
            [3.0, 0.2, -1.0],
            [0.2, 4.0, 2.0],
            [0.4, -0.6, 2.0 * 0.7**2 * 0.4],
        ]
    )
    np.testing.assert_allclose(captured["matrix"], expected, rtol=0.0, atol=0.0)


def test_wp06c_augmented_jacobian_matches_three_step_central_fd() -> None:
    base_u = 0.1
    base_lambda = 0.02
    trial = np.array([0.2, 0.08])
    radius = 0.1
    load_scale = 1.2

    def system(point: np.ndarray) -> np.ndarray:
        u, load_factor = point
        residual = load_factor - (u - u**3)
        delta_u = u - base_u
        delta_lambda = load_factor - base_lambda
        constraint = delta_u**2 + (load_scale * delta_lambda) ** 2 - radius**2
        return np.array([residual, constraint])

    u, load_factor = trial
    tangent = 1.0 - 3.0 * u**2
    production = np.array(
        [
            [tangent, -1.0],
            [2.0 * (u - base_u), 2.0 * load_scale**2 * (load_factor - base_lambda)],
        ]
    )
    h_values = (1.0e-4, 1.0e-5, 1.0e-6)
    for h in h_values:
        finite_difference = np.column_stack(
            [
                (system(trial + np.eye(2)[column] * h) - system(trial - np.eye(2)[column] * h)) / (2.0 * h)
                for column in range(2)
            ]
        )
        signed_production = production.copy()
        signed_production[0, :] *= -1.0
        difference = finite_difference - signed_production
        frobenius = float(np.linalg.norm(difference) / max(np.linalg.norm(finite_difference), 1.0))
        max_column = float(
            max(
                np.linalg.norm(difference[:, column])
                / max(np.linalg.norm(finite_difference[:, column]), 1.0)
                for column in range(2)
            )
        )
        assert frobenius <= 1.0e-6
        assert max_column <= 5.0e-6


def test_wp06c_toy_limit_point_crossing_is_deterministic_research_evidence() -> None:
    first = run_shallow_arch_arc_length_benchmark(steps=80, radius=0.05, max_iterations=40)
    second = run_shallow_arch_arc_length_benchmark(steps=80, radius=0.05, max_iterations=40)
    assert first["status"] == "PASS_INTERNAL_RESEARCH"
    assert first["limit_point_observed"] is True
    assert first["maximum_equilibrium_error"] < 1.0e-8
    assert first["steps"] == second["steps"]


def test_wp06c_nonfinite_and_invalid_radius_controls_fail_closed() -> None:
    with pytest.raises(InputValidationError):
        ArcLengthControls.from_parameters({"min_arc_length_radius": np.nan}, max_iterations=10)

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
