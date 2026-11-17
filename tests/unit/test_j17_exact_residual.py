"""Controlled tests for the offline exact represented-residual verifier."""

from __future__ import annotations

from fractions import Fraction

import numpy as np

from research.j17.exact_residual import evaluate_exact_residual


def test_exact_residual_pass_fail_and_threshold_neighborhood() -> None:
    matrix = np.eye(2, dtype=np.float64)
    rhs = np.array([1.0, 0.0], dtype=np.float64)

    below = evaluate_exact_residual(matrix, rhs, np.array([1.0, 0.99e-7]))
    above = evaluate_exact_residual(matrix, rhs, np.array([1.0, 1.01e-7]))
    comfortably_above = evaluate_exact_residual(matrix, rhs, np.array([1.0, 2.0e-7]))

    assert below.status == "PASS"
    assert above.status == "FAIL"
    assert comfortably_above.status == "FAIL"
    assert below.relative_residual_squared is not None
    assert below.relative_residual_squared < below.threshold_binary64**2
    assert above.relative_residual_squared is not None
    assert above.relative_residual_squared > above.threshold_binary64**2


def test_exact_residual_uses_complex_binary_values_without_float_norms() -> None:
    matrix = np.array([[2.0 + 1.0j, 0.0], [0.0, 4.0]], dtype=np.complex128)
    rhs = np.array([1.0 + 1.0j, 2.0], dtype=np.complex128)
    solution = np.array([0.5 + 0.0j, 0.5], dtype=np.complex128)

    result = evaluate_exact_residual(matrix, rhs, solution)

    # First component residual is -0.5 - 0.5j; ||b||^2 = 6.
    assert result.status == "FAIL"
    assert result.residual_squared == Fraction(1, 4)
    assert result.reference_squared == Fraction(6, 1)


def test_exact_residual_handles_ill_conditioning_and_tiny_norms() -> None:
    matrix = np.diag(np.array([1.0, 1.0e-300], dtype=np.float64))
    rhs = np.array([1.0, 0.0], dtype=np.float64)
    solution = np.array([1.0, 1.0], dtype=np.float64)

    result = evaluate_exact_residual(matrix, rhs, solution)

    assert result.status == "PASS"
    assert result.residual_squared == Fraction.from_float(1.0e-300) ** 2
    assert result.relative_residual_display is not None
    assert result.relative_residual_display.startswith("1.000")
    assert result.relative_residual_display.endswith("E-300")


def test_exact_residual_defines_zero_reference_and_small_scale_cases() -> None:
    zero = evaluate_exact_residual(np.zeros((1, 1)), np.zeros(1), np.zeros(1))
    nonzero_small = evaluate_exact_residual(
        np.array([[1.0e-300]]), np.array([0.0]), np.array([1.0])
    )

    assert zero.status == "PASS"
    assert zero.relative_residual_squared == Fraction(0)
    assert nonzero_small.status == "FAIL"
    assert nonzero_small.relative_residual_squared == Fraction(1)


def test_invalid_nonfinite_and_over_budget_inputs_are_inconclusive() -> None:
    nonfinite = evaluate_exact_residual(
        np.array([[np.inf]]), np.array([1.0]), np.array([1.0])
    )
    oversized = evaluate_exact_residual(
        np.eye(2), np.ones(2), np.zeros(2), max_dimension=1
    )
    wrong_shape = evaluate_exact_residual(np.eye(2), np.ones(1), np.ones(2))
    unsupported = evaluate_exact_residual(
        np.array([[1]], dtype=np.int64), np.ones(1), np.ones(1)
    )

    assert nonfinite.status == "INCONCLUSIVE"
    assert "finite" in nonfinite.reason
    assert oversized.status == "INCONCLUSIVE"
    assert "dimension" in oversized.reason
    assert wrong_shape.status == "INCONCLUSIVE"
    assert "match the matrix" in wrong_shape.reason
    assert unsupported.status == "INCONCLUSIVE"
    assert "float32/float64" in unsupported.reason
