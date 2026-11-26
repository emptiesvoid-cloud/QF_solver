"""Bounded exact residual comparison for finite real binary64 CSR data."""

from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from time import monotonic

import numpy as np


DEFAULT_TOLERANCE = 1e-7
FLOAT_QUANTUM_SHIFT = 1074
MAX_DIMENSION = 4096
MAX_TERMS = 300_000
MAX_ROW_TERMS = 512


@dataclass(frozen=True)
class Limits:
    dimension: int = MAX_DIMENSION
    terms: int = MAX_TERMS
    row_terms: int = MAX_ROW_TERMS
    seconds: float = 8.0


def _inconclusive(reason):
    return {"status": "INCONCLUSIVE", "reason": reason}


def _scaled_integer(value):
    numerator, denominator = float(value).as_integer_ratio()
    return numerator << (FLOAT_QUANTUM_SHIFT - (denominator.bit_length() - 1))


def _vector(array, dtypes):
    return type(array) is np.ndarray and array.ndim == 1 and array.dtype in dtypes


def check_residual(data, indices, indptr, b, x, *, tolerance=DEFAULT_TOLERANCE, limits=Limits()):
    """Compare squared norms exactly, without forming rounded CSR duplicates.

    A zero denominator means b and the exact product are both zero, so the
    residual is zero and the guard's zero convention applies.
    """
    started = monotonic()
    caps = ((limits.dimension, MAX_DIMENSION), (limits.terms, MAX_TERMS), (limits.row_terms, MAX_ROW_TERMS))
    if any(type(value) is not int or not 0 < value <= cap for value, cap in caps):
        return _inconclusive("INVALID_LIMITS")
    if type(limits.seconds) not in (int, float) or not 0 <= limits.seconds <= 8:
        return _inconclusive("INVALID_LIMITS")
    if type(tolerance) is not float or not np.isfinite(tolerance) or tolerance <= 0:
        return _inconclusive("INVALID_TOLERANCE")
    real = (np.dtype("float64"),)
    index = (np.dtype("int32"), np.dtype("int64"))
    if not all(_vector(a, real) for a in (data, b, x)) or not all(_vector(a, index) for a in (indices, indptr)):
        return _inconclusive("UNSUPPORTED_ARRAY_FORMAT")
    n, terms = b.size, data.size
    if n > limits.dimension or terms > limits.terms:
        return _inconclusive("DIMENSION_OR_TERMS_LIMIT")
    if n == 0 or x.size != n or indptr.size != n + 1 or indices.size != terms:
        return _inconclusive("INVALID_SHAPE")
    if (
        indptr[0] != 0
        or indptr[-1] != terms
        or np.any(indptr[1:] < indptr[:-1])
        or np.any(indices < 0)
        or np.any(indices >= n)
    ):
        return _inconclusive("INVALID_CSR")
    if np.any(np.diff(indptr) > limits.row_terms):
        return _inconclusive("ROW_TERMS_LIMIT")
    if not all(np.isfinite(a).all() for a in (data, b, x)):
        return _inconclusive("NONFINITE_INPUT")

    deadline = started + limits.seconds
    x_exact = [_scaled_integer(value) for value in x]
    residual_squared = rhs_squared = product_squared = 0
    for row, b_value in enumerate(b):
        if monotonic() >= deadline:
            return _inconclusive("COOPERATIVE_TIME_LIMIT")
        product = 0
        for k in range(int(indptr[row]), int(indptr[row + 1])):
            product += _scaled_integer(data[k]) * x_exact[int(indices[k])]
        rhs = _scaled_integer(b_value) << FLOAT_QUANTUM_SHIFT
        residual_squared += (product - rhs) ** 2
        rhs_squared += rhs**2
        product_squared += product**2

    reference = max(rhs_squared, product_squared)
    threshold_num, threshold_den = tolerance.as_integer_ratio()
    passed = residual_squared * threshold_den**2 <= reference * threshold_num**2
    squared_ratio = Fraction(residual_squared, reference) if reference else Fraction()
    with localcontext() as context:
        context.prec = 20
        ratio = (Decimal(squared_ratio.numerator) / Decimal(squared_ratio.denominator)).sqrt()
    result = {
        "status": "PASS" if passed else "FAIL",
        "reason": "ZERO_REFERENCE_EXACT_ZERO" if reference == 0 else "EXACT_SQUARED_COMPARISON",
        "relative_l2_display": str(ratio),
        "relative_squared_hex": [hex(squared_ratio.numerator), hex(squared_ratio.denominator)],
        "threshold_hex": tolerance.hex(),
        "dimension": n,
        "stored_terms": terms,
    }
    elapsed = monotonic() - started
    if elapsed >= limits.seconds:
        return _inconclusive("COOPERATIVE_TIME_LIMIT")
    return dict(result, verifier_seconds=elapsed)
