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
from time import monotonic
from typing import Literal

import numpy as np
from scipy.sparse import issparse


Decision = Literal["PASS", "FAIL", "INCONCLUSIVE"]


@dataclass(frozen=True)
class ExactResidualResult:
    """Result for one represented matrix problem.

    Squared norms and the threshold comparison are exact rational values.
    Decimal norm strings are display approximations and are not used to decide.
    For CSR inputs, nonzero_entries counts nonzero stored terms before
    duplicate columns are mathematically coalesced; stored_entries also counts
    explicit zeros.
    """

    status: Decision
    reason: str
    dimension: int | None = None
    nonzero_entries: int | None = None
    stored_entries: int | None = None
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
    # Binary16/32 values are exactly representable in binary64; conversion
    # preserves their value. Wider floats are rejected before this helper.
    return Fraction.from_float(float(value))


def _complex_fraction(value: np.generic | complex | float) -> tuple[Fraction, Fraction]:
    if isinstance(value, (complex, np.complexfloating)):
        return _fraction_from_real(value.real), _fraction_from_real(value.imag)
    return _fraction_from_real(value), Fraction(0)


def _supported_float_array(array: np.ndarray) -> bool:
    if array.dtype.kind == "f":
        return array.dtype.itemsize in {2, 4, 8}
    if array.dtype.kind == "c":
        return array.dtype.itemsize in {8, 16}
    return False


def _decimal_sqrt(value: Fraction, digits: int = 50) -> str:
    with localcontext() as context:
        context.prec = digits
        decimal_value = Decimal(value.numerator) / Decimal(value.denominator)
        return str(decimal_value.sqrt())


def _within_fraction_bit_limit(value: Fraction, maximum_bits: int) -> bool:
    return value.numerator.bit_length() <= maximum_bits and value.denominator.bit_length() <= maximum_bits


def evaluate_exact_residual(
    matrix: object,
    rhs: np.ndarray,
    solution: np.ndarray,
    *,
    tolerance: float = 1.0e-7,
    max_dimension: int = 256,
    max_nonzero_entries: int = 100_000,
    max_fraction_bits: int = 65_536,
    max_elapsed_seconds: float | None = None,
) -> ExactResidualResult:
    """Compare an exact represented-system residual with a binary64 limit.

    The formula is ``||A*x-b||2 / max(||b||2, ||A*x||2)``.  Instead of
    computing square roots, the method compares the exact rational squared
    numerator and denominator with the exact square of ``float(tolerance)``.
    Thus PASS/FAIL is exact for the supplied IEEE binary16/32/64 values,
    while input quantization and physical/model error remain outside scope.

    Dense float arrays and CSR sparse matrices are accepted. CSR entries are
    interpreted as exact stored terms: duplicate column indices are summed
    exactly, without calling SciPy's floating-point sum_duplicates or
    converting the matrix format. stored_entries therefore includes duplicate
    entries and explicit zeros. This checks the exact linear system represented
    by the stored binary values; it does not reproduce the CSR kernel's rounded
    operation sequence.

    Binary16/32/64 real values and complex64/128 values are accepted and
    widened to exact binary64 rational values. Unsupported, malformed,
    non-finite, or over-budget inputs return
    INCONCLUSIVE. The limits prevent this research path from being mistaken
    for an unbounded production solver routine.

    ``max_elapsed_seconds`` is a cooperative CPU-time budget checked during
    row and stored-term traversal. It is not an operating-system timeout; an
    external monitored runner is still required for hard process limits.
    """
    if (
        isinstance(tolerance, (bool, np.bool_))
        or not isinstance(tolerance, (int, float, np.integer, np.floating))
        or not np.isfinite(float(tolerance))
        or float(tolerance) <= 0.0
    ):
        return ExactResidualResult("INCONCLUSIVE", "tolerance must be a finite positive scalar")
    limits = (max_dimension, max_nonzero_entries, max_fraction_bits)
    if any(isinstance(value, bool) or not isinstance(value, (int, np.integer)) or int(value) <= 0 for value in limits):
        return ExactResidualResult("INCONCLUSIVE", "resource limits must be positive")
    if max_elapsed_seconds is not None and (
        isinstance(max_elapsed_seconds, (bool, np.bool_))
        or not isinstance(max_elapsed_seconds, (int, float, np.integer, np.floating))
        or not np.isfinite(float(max_elapsed_seconds))
        or float(max_elapsed_seconds) < 0.0
    ):
        return ExactResidualResult("INCONCLUSIVE", "time limit must be a finite nonnegative scalar")
    deadline = None if max_elapsed_seconds is None else monotonic() + float(max_elapsed_seconds)

    def time_budget_exceeded() -> bool:
        return deadline is not None and monotonic() >= deadline

    if time_budget_exceeded():
        return ExactResidualResult("INCONCLUSIVE", "exact evaluation exceeded its time budget")

    sparse_matrix = matrix if issparse(matrix) else None
    if sparse_matrix is not None:
        if getattr(sparse_matrix, "format", None) != "csr":
            return ExactResidualResult(
                "INCONCLUSIVE", "sparse matrix must use CSR; implicit format conversion is not performed"
            )
        matrix_shape = tuple(sparse_matrix.shape)
        matrix_dtype = sparse_matrix.dtype
        matrix_values = np.asarray(sparse_matrix.data)
        indices = np.asarray(sparse_matrix.indices)
        indptr = np.asarray(sparse_matrix.indptr)
        if len(matrix_shape) != 2:
            return ExactResidualResult("INCONCLUSIVE", "sparse matrix shape must be two-dimensional")
        if matrix_shape[0] != matrix_shape[1]:
            return ExactResidualResult("INCONCLUSIVE", "matrix must be square")
        dimension = int(matrix_shape[0])
        if dimension > max_dimension:
            return ExactResidualResult(
                "INCONCLUSIVE", "matrix dimension exceeds the exact-evaluation limit",
                dimension=dimension, stored_entries=int(matrix_values.size),
            )
        if matrix_values.size > max_nonzero_entries:
            return ExactResidualResult(
                "INCONCLUSIVE", "matrix entry count exceeds the exact-evaluation limit",
                dimension=dimension, stored_entries=int(matrix_values.size),
            )
        if not _supported_float_array(np.empty(0, dtype=matrix_dtype)):
            return ExactResidualResult("INCONCLUSIVE", "only float16/float32/float64 and complex64/complex128 arrays are supported")
        if indices.dtype.kind not in "iu" or indptr.dtype.kind not in "iu":
            return ExactResidualResult("INCONCLUSIVE", "CSR indices and indptr must have integer dtypes")
        if (
            matrix_values.ndim != 1
            or indices.ndim != 1
            or indptr.ndim != 1
            or indices.size != matrix_values.size
            or indptr.shape != (matrix_shape[0] + 1,)
            or indptr.size == 0
            or int(indptr[0]) != 0
            or int(indptr[-1]) != matrix_values.size
            or np.any(indptr < 0)
            or np.any(indptr > matrix_values.size)
            or np.any(indptr[1:] < indptr[:-1])
            or (indices.size and (np.min(indices) < 0 or np.max(indices) >= matrix_shape[1]))
        ):
            return ExactResidualResult("INCONCLUSIVE", "CSR storage arrays are malformed")
        matrix_array = None
        stored_entries = int(matrix_values.size)
        budget_entries = stored_entries
        try:
            nonzero_entries = int(np.count_nonzero(matrix_values))
            matrix_finite = bool(np.all(np.isfinite(matrix_values)))
        except MemoryError:
            return ExactResidualResult(
                "INCONCLUSIVE", "matrix validation exceeded available memory",
                dimension=dimension, stored_entries=stored_entries,
            )
    else:
        try:
            matrix_array = np.asarray(matrix)
        except (TypeError, ValueError):
            return ExactResidualResult("INCONCLUSIVE", "matrix must be a dense array or CSR sparse matrix")
        matrix_shape = tuple(matrix_array.shape)
        matrix_dtype = matrix_array.dtype
        if not _supported_float_array(matrix_array):
            return ExactResidualResult("INCONCLUSIVE", "only float16/float32/float64 and complex64/complex128 arrays are supported")
        if len(matrix_shape) != 2 or matrix_shape[0] != matrix_shape[1]:
            return ExactResidualResult("INCONCLUSIVE", "matrix must be square")
        dimension = int(matrix_shape[0])
        if dimension > max_dimension:
            return ExactResidualResult(
                "INCONCLUSIVE", "matrix dimension exceeds the exact-evaluation limit",
                dimension=dimension, stored_entries=int(matrix_array.size),
            )
        stored_entries = int(matrix_array.size)
        try:
            nonzero_entries = int(np.count_nonzero(matrix_array))
        except MemoryError:
            return ExactResidualResult(
                "INCONCLUSIVE", "matrix validation exceeded available memory",
                dimension=dimension, stored_entries=stored_entries,
            )
        budget_entries = nonzero_entries
        if budget_entries > max_nonzero_entries:
            return ExactResidualResult(
                "INCONCLUSIVE", "matrix entry count exceeds the exact-evaluation limit",
                dimension=dimension, nonzero_entries=nonzero_entries, stored_entries=stored_entries,
            )
        try:
            matrix_finite = bool(np.all(np.isfinite(matrix_array)))
        except MemoryError:
            return ExactResidualResult(
                "INCONCLUSIVE", "matrix validation exceeded available memory",
                dimension=dimension, nonzero_entries=nonzero_entries, stored_entries=stored_entries,
            )
        matrix_values = None
        indices = None
        indptr = None

    try:
        rhs_array = np.asarray(rhs)
        solution_array = np.asarray(solution)
    except (TypeError, ValueError, OverflowError, MemoryError):
        return ExactResidualResult("INCONCLUSIVE", "right-hand side and solution must be rectangular numeric arrays")
    if not _supported_float_array(rhs_array) or not _supported_float_array(solution_array):
        return ExactResidualResult("INCONCLUSIVE", "only float16/float32/float64 and complex64/complex128 arrays are supported")
    if len(matrix_shape) != 2 or matrix_shape[0] != matrix_shape[1]:
        return ExactResidualResult("INCONCLUSIVE", "matrix must be square")
    dimension = int(matrix_shape[0])
    if rhs_array.shape != (dimension,) or solution_array.shape != (dimension,):
        return ExactResidualResult("INCONCLUSIVE", "right-hand side and solution must be one-dimensional and match the matrix")
    if dimension > max_dimension:
        return ExactResidualResult(
            "INCONCLUSIVE", "matrix dimension exceeds the exact-evaluation limit",
            dimension=dimension, stored_entries=stored_entries,
        )
    if not matrix_finite or not np.all(np.isfinite(rhs_array)) or not np.all(np.isfinite(solution_array)):
        return ExactResidualResult(
            "INCONCLUSIVE", "matrix, right-hand side, and solution must be finite",
            dimension=dimension, nonzero_entries=nonzero_entries, stored_entries=stored_entries,
        )

    if budget_entries > max_nonzero_entries:
        return ExactResidualResult(
            "INCONCLUSIVE",
            "matrix entry count exceeds the exact-evaluation limit",
            dimension=dimension,
            nonzero_entries=nonzero_entries,
            stored_entries=stored_entries,
        )

    try:
        exact_solution = [_complex_fraction(solution_array[column]) for column in range(dimension)]
        exact_rhs = [_complex_fraction(rhs_array[row]) for row in range(dimension)]
        if any(
            not _within_fraction_bit_limit(component, max_fraction_bits)
            for pair in exact_solution + exact_rhs
            for component in pair
        ):
            return ExactResidualResult(
                "INCONCLUSIVE", "an exact input value exceeds the rational bit-length limit",
                dimension=dimension, nonzero_entries=nonzero_entries, stored_entries=stored_entries,
            )
        exact_product: list[tuple[Fraction, Fraction]] = []
        for row in range(dimension):
            if time_budget_exceeded():
                return ExactResidualResult(
                    "INCONCLUSIVE", "exact evaluation exceeded its time budget",
                    dimension=dimension, nonzero_entries=nonzero_entries, stored_entries=stored_entries,
                )
            product_real = Fraction(0)
            product_imag = Fraction(0)
            if sparse_matrix is None:
                entries = ((column, matrix_array[row, column]) for column in range(dimension))
            else:
                start, stop = int(indptr[row]), int(indptr[row + 1])
                entries = ((int(indices[position]), matrix_values[position]) for position in range(start, stop))
            for term_index, (column, coefficient) in enumerate(entries):
                if time_budget_exceeded():
                    return ExactResidualResult(
                        "INCONCLUSIVE", "exact evaluation exceeded its time budget",
                        dimension=dimension, nonzero_entries=nonzero_entries, stored_entries=stored_entries,
                    )
                if coefficient == 0:
                    continue
                a_real, a_imag = _complex_fraction(coefficient)
                if not _within_fraction_bit_limit(a_real, max_fraction_bits) or not _within_fraction_bit_limit(
                    a_imag, max_fraction_bits
                ):
                    return ExactResidualResult(
                        "INCONCLUSIVE", "an exact matrix value exceeds the rational bit-length limit",
                        dimension=dimension, nonzero_entries=nonzero_entries, stored_entries=stored_entries,
                    )
                x_real, x_imag = exact_solution[column]
                product_real += a_real * x_real - a_imag * x_imag
                product_imag += a_real * x_imag + a_imag * x_real
                if not _within_fraction_bit_limit(product_real, max_fraction_bits) or not _within_fraction_bit_limit(
                    product_imag, max_fraction_bits
                ):
                    return ExactResidualResult(
                        "INCONCLUSIVE", "exact product exceeds the rational bit-length limit",
                        dimension=dimension, nonzero_entries=nonzero_entries, stored_entries=stored_entries,
                    )
            exact_product.append((product_real, product_imag))

        residual_squared = Fraction(0)
        rhs_squared = Fraction(0)
        product_squared = Fraction(0)
        for (product_real, product_imag), (rhs_real, rhs_imag) in zip(
            exact_product, exact_rhs, strict=True
        ):
            if time_budget_exceeded():
                return ExactResidualResult(
                    "INCONCLUSIVE", "exact evaluation exceeded its time budget",
                    dimension=dimension, nonzero_entries=nonzero_entries, stored_entries=stored_entries,
                )
            residual_real = product_real - rhs_real
            residual_imag = product_imag - rhs_imag
            residual_squared += residual_real * residual_real + residual_imag * residual_imag
            rhs_squared += rhs_real * rhs_real + rhs_imag * rhs_imag
            product_squared += product_real * product_real + product_imag * product_imag
            if any(
                not _within_fraction_bit_limit(value, max_fraction_bits)
                for value in (residual_squared, rhs_squared, product_squared)
            ):
                return ExactResidualResult(
                    "INCONCLUSIVE", "exact norm accumulation exceeds the rational bit-length limit",
                    dimension=dimension, nonzero_entries=nonzero_entries, stored_entries=stored_entries,
                )

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
        if time_budget_exceeded():
            return ExactResidualResult(
                "INCONCLUSIVE", "exact evaluation exceeded its time budget",
                dimension=dimension, nonzero_entries=nonzero_entries, stored_entries=stored_entries,
            )

        passed = residual_squared == 0 if reference_squared == 0 else relative_squared <= threshold_squared
        status: Decision = "PASS" if passed else "FAIL"
        reason = (
            "exact represented-system residual is at or below the binary64 tolerance"
            if passed
            else "exact represented-system residual is above the binary64 tolerance"
        )
        residual_display = _decimal_sqrt(residual_squared)
        relative_display = _decimal_sqrt(relative_squared) if relative_squared is not None else None
        if time_budget_exceeded():
            return ExactResidualResult(
                "INCONCLUSIVE", "exact evaluation exceeded its time budget",
                dimension=dimension, nonzero_entries=nonzero_entries, stored_entries=stored_entries,
            )
        return ExactResidualResult(
            status=status,
            reason=reason,
            dimension=dimension,
            nonzero_entries=nonzero_entries,
            stored_entries=stored_entries,
            residual_squared=residual_squared,
            reference_squared=reference_squared,
            relative_residual_squared=relative_squared,
            threshold_binary64=threshold,
            residual_l2_display=residual_display,
            relative_residual_display=relative_display,
        )
    except (ArithmeticError, MemoryError, OverflowError, ValueError) as exc:
        return ExactResidualResult(
            "INCONCLUSIVE",
            f"exact evaluation could not be completed: {type(exc).__name__}: {exc}",
            dimension=dimension,
            nonzero_entries=nonzero_entries,
            stored_entries=stored_entries,
        )
