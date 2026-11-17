"""Pure numerical tests for J16 archived residual re-evaluation."""

from __future__ import annotations

import math

import mpmath as mp
import numpy as np

from research.j16.guard_exact_residual import high_precision_residual_metrics


def test_high_precision_residual_metrics_match_complex_diagonal_case() -> None:
    matrix_real = np.array([[2.0, 0.0], [0.0, 4.0]])
    matrix_imag = np.array([[1.0, 0.0], [0.0, 0.0]])
    rhs_real = np.array([1.0, 2.0])
    rhs_imag = np.zeros(2)
    solution_real = np.array([0.5, 0.5])
    solution_imag = np.zeros(2)

    result = high_precision_residual_metrics(
        matrix_real,
        matrix_imag,
        rhs_real,
        rhs_imag,
        solution_real,
        solution_imag,
        decimal_digits=80,
    )

    expected_relative = mp.mpf("0.5") / mp.sqrt(mp.mpf("5.25"))
    assert mp.almosteq(result["relative_residual_l2"], expected_relative)
    assert math.isclose(float(result["backward_error_eta_inf"]), 0.125, rel_tol=1e-15)


def test_high_precision_residual_rejects_shape_mismatch() -> None:
    with np.testing.assert_raises_regex(ValueError, "match the matrix dimension"):
        high_precision_residual_metrics(
            np.eye(2),
            np.zeros((2, 2)),
            np.ones(2),
            np.zeros(2),
            np.ones(1),
            np.zeros(1),
            decimal_digits=50,
        )
