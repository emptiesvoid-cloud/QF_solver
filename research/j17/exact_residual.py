"""Exact residual checks for finite binary floating-point linear systems.

This research utility evaluates the mathematical residual of the values that
were actually stored in floating-point arrays. It is deliberately separate
from QF Solver's route guard: a PASS here says nothing about assembly accuracy,
the physical model, or the solution's forward error.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Literal

import numpy as np


Decision = Literal["PASS", "FAIL", "INCONCLUSIVE"]


@dataclass(frozen=True)
class ExactResidualResult:
    """Result for one represented matrix problem.

    Squared norms and the threshold comparison are exact rational values.
    Decimal norm strings are display approximations and are not used to decide.
    """

    status: Decision
    reason: str
    dimension: int | None = None
    nonzero_entries: int | None = None
    residual_squared: Fraction | None = None
    reference_squared: Fraction | None = None
    relative_residual_squared: Fraction | None = None
    threshold_binary64: Fraction | None = None
    residual_l2_display: str | None = None
    relative_residual_display: str | None = None


def exact_fraction(value: Fraction) -> dict[str, str]:
    """Serialize an exact rational without losing numerator or denominator."""
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _fraction_from_real(value: np.generic | float) -> Fraction:
    # float32 values are exactly representable in binary64; the conversion
    # preserves their value. Wider floats are rejected before this helper.
    return Fraction.from_float(float(value))


def _complex_fraction(value: np.generic | complex | float) -> tuple[Fraction, Fraction]:
    if isinstance(value, (complex, np.complexfloating)):
        return _fraction_from_real(value.real), _fraction_from_real(value.imag)
    return _fraction_from_real(value), Fraction(0)


def _supported_float_array(array: np.ndarray) -> bool:
    if array.dtype.kind == "f":
        return array.dtype.itemsize <= 8
    if array.dtype.kind == "c":
        return array.dtype.itemsize <= 16
    return False


def _decimal_sqrt(value: Fraction, digits: int = 50) -> str:
    with localcontext() as context:
        context.prec = digits
        decimal_value = Decimal(value.numerator) / Decimal(value.denominator)
        return str(decimal_value.sqrt())


def _within_fraction_bit_limit(value: Fraction, maximum_bits: int) -> bool:
    return value.numerator.bit_length() <= maximum_bits and value.denominator.bit_length() <= maximum_bits


def evaluate_exact_residual(
    matrix: np.ndarray,
    rhs: np.ndarray,
    solution: np.ndarray,
    *,
    tolerance: float = 1.0e-7,
    max_dimension: int = 256,
    max_nonzero_entries: int = 100_000,
    max_fraction_bits: int = 65_536,
) -> ExactResidualResult:
    """Compare an exact represented-system residual with a binary64 limit.

    The formula is ``||A*x-b||2 / max(||b||2, ||A*x||2)``.  Instead of
    computing square roots, the method compares the exact rational squared
    numerator and denominator with the exact square of ``float(tolerance)``.
    Thus PASS/FAIL is exact for the supplied IEEE float32/float64 values,
    while input quantization and physical/model error remain outside scope.

    Unsupported, malformed, non-finite, or over-budget inputs return
    INCONCLUSIVE. The limits prevent this research path from being mistaken
    for an unbounded production solver routine.
    """
    if (
        isinstance(tolerance, (bool, np.bool_))
        or not isinstance(tolerance, (int, float, np.integer, np.floating))
        or not np.isfinite(float(tolerance))
        or float(tolerance) <= 0.0
    ):
        return ExactResidualResult("INCONCLUSIVE", "tolerance must be a finite positive scalar")
    if min(max_dimension, max_nonzero_entries, max_fraction_bits) <= 0:
        return ExactResidualResult("INCONCLUSIVE", "resource limits must be positive")

    arrays = tuple(np.asarray(values) for values in (matrix, rhs, solution))
    matrix_array, rhs_array, solution_array = arrays
    if any(not _supported_float_array(array) for array in arrays):
        return ExactResidualResult("INCONCLUSIVE", "only float32/float64 and complex64/complex128 arrays are supported")
    if matrix_array.ndim != 2 or matrix_array.shape[0] != matrix_array.shape[1]:
        return ExactResidualResult("INCONCLUSIVE", "matrix must be square")
    dimension = int(matrix_array.shape[0])
    if rhs_array.shape != (dimension,) or solution_array.shape != (dimension,):
        return ExactResidualResult("INCONCLUSIVE", "right-hand side and solution must be one-dimensional and match the matrix")
    if dimension > max_dimension:
        return ExactResidualResult("INCONCLUSIVE", "matrix dimension exceeds the exact-evaluation limit", dimension=dimension)
    if not all(np.all(np.isfinite(array)) for array in arrays):
        return ExactResidualResult("INCONCLUSIVE", "matrix, right-hand side, and solution must be finite", dimension=dimension)

    nonzero_entries = int(np.count_nonzero(matrix_array))
    if nonzero_entries > max_nonzero_entries:
        return ExactResidualResult(
            "INCONCLUSIVE",
            "matrix nonzero count exceeds the exact-evaluation limit",
            dimension=dimension,
            nonzero_entries=nonzero_entries,
        )

    try:
        exact_solution = [_complex_fraction(solution_array[column]) for column in range(dimension)]
        exact_rhs = [_complex_fraction(rhs_array[row]) for row in range(dimension)]
        exact_product: list[tuple[Fraction, Fraction]] = []
        for row in range(dimension):
            product_real = Fraction(0)
            product_imag = Fraction(0)
            for column in range(dimension):
                coefficient = matrix_array[row, column]
                if coefficient == 0:
                    continue
                a_real, a_imag = _complex_fraction(coefficient)
                x_real, x_imag = exact_solution[column]
                product_real += a_real * x_real - a_imag * x_imag
                product_imag += a_real * x_imag + a_imag * x_real
            if not _within_fraction_bit_limit(product_real, max_fraction_bits) or not _within_fraction_bit_limit(
                product_imag, max_fraction_bits
            ):
                return ExactResidualResult(
                    "INCONCLUSIVE",
                    "exact product exceeds the rational bit-length limit",
                    dimension=dimension,
                    nonzero_entries=nonzero_entries,
                )
            exact_product.append((product_real, product_imag))

        residual_squared = Fraction(0)
        rhs_squared = Fraction(0)
        product_squared = Fraction(0)
        for (product_real, product_imag), (rhs_real, rhs_imag) in zip(exact_product, exact_rhs, strict=True):
            residual_real = product_real - rhs_real
            residual_imag = product_imag - rhs_imag
            residual_squared += residual_real * residual_real + residual_imag * residual_imag
            rhs_squared += rhs_real * rhs_real + rhs_imag * rhs_imag
            product_squared += product_real * product_real + product_imag * product_imag

        reference_squared = max(rhs_squared, product_squared)
        threshold = Fraction.from_float(float(tolerance))
        threshold_squared = threshold * threshold
        if reference_squared == 0:
            relative_squared = Fraction(0) if residual_squared == 0 else None
        else:
            relative_squared = residual_squared / reference_squared

        exact_values = (residual_squared, rhs_squared, product_squared, threshold_squared)
        if any(not _within_fraction_bit_limit(value, max_fraction_bits) for value in exact_values):
            return ExactResidualResult(
                "INCONCLUSIVE",
                "exact norm accumulation exceeds the rational bit-length limit",
                dimension=dimension,
                nonzero_entries=nonzero_entries,
            )
        if relative_squared is not None and not _within_fraction_bit_limit(relative_squared, max_fraction_bits):
            return ExactResidualResult(
                "INCONCLUSIVE",
                "exact residual ratio exceeds the rational bit-length limit",
                dimension=dimension,
                nonzero_entries=nonzero_entries,
            )

        passed = residual_squared == 0 if reference_squared == 0 else relative_squared <= threshold_squared
        status: Decision = "PASS" if passed else "FAIL"
        reason = (
            "exact represented-system residual is at or below the binary64 tolerance"
            if passed
            else "exact represented-system residual is above the binary64 tolerance"
        )
        return ExactResidualResult(
            status=status,
            reason=reason,
            dimension=dimension,
            nonzero_entries=nonzero_entries,
            residual_squared=residual_squared,
            reference_squared=reference_squared,
            relative_residual_squared=relative_squared,
            threshold_binary64=threshold,
            residual_l2_display=_decimal_sqrt(residual_squared),
            relative_residual_display=_decimal_sqrt(relative_squared) if relative_squared is not None else None,
        )
    except (ArithmeticError, OverflowError, ValueError) as exc:
        return ExactResidualResult(
            "INCONCLUSIVE",
            f"exact evaluation could not be completed: {type(exc).__name__}: {exc}",
            dimension=dimension,
            nonzero_entries=nonzero_entries,
        )
