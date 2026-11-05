"""Experimental interval-first modal residual check, never used by production.

The fast path performs scalar Python binary64 operations, encloses each result
outwardly, and falls back to the bounded exact rational oracle when it cannot
establish the tolerance.  It does not call BLAS/SciPy matvecs.  The proof is
conditional on the IEEE environment remaining stable during an invocation.
"""
from __future__ import annotations

import math
import sys
import time
from dataclasses import dataclass
from fractions import Fraction

import numpy as np
from scipy.sparse import isspmatrix_csc, isspmatrix_csr

from experiments.aq09_exact_modal_residual import check_modal_residual

FAST_MAX_DIMENSION = 10_000
FAST_MAX_TERMS = 100_000
FAST_MAX_OPERATIONS = 3_000_000
FAST_MAX_ESTIMATED_MEMORY_BYTES = 32_000_000


@dataclass(frozen=True)
class HybridResult:
    status: str
    path: str
    reason: str
    terms: int
    residual_l1_upper: float | None = None
    reference_linf_lower: float | None = None
    operations_estimate: int = 0


def _environment_supported() -> bool:
    """Probe the current thread's binary64 rounding and gradual-underflow mode.

    ``sys.float_info.rounds`` alone is a startup-time report on some runtimes;
    tie probes check the mode at the point this function is called.
    """
    smallest = math.nextafter(0.0, math.inf)
    smallest_normal = sys.float_info.min
    half_normal = math.ldexp(1.0, -1023)
    half_ulp = math.ldexp(1.0, -53)
    return (
        sys.float_info.radix == 2
        and sys.float_info.mant_dig == 53
        and sys.float_info.rounds == 1
        and 1.0 + half_ulp == 1.0
        and -1.0 - half_ulp == -1.0
        and smallest > 0.0
        and smallest * 1.0 == smallest
        and smallest + 0.0 == smallest
        and math.nextafter(0.0, math.inf) == smallest
        # A gradual-underflow probe: FTZ/DAZ environments normally fail here.
        and half_normal > 0.0
        and half_normal < smallest_normal
        and half_normal * 2.0 == smallest_normal
    )


def _require_normal_or_zero(value: float) -> float:
    if not math.isfinite(value):
        raise ArithmeticError("nonfinite_interval_endpoint")
    if value != 0.0 and abs(value) < sys.float_info.min:
        raise ArithmeticError("subnormal_interval_endpoint")
    return value


def _down(value: float) -> float:
    if not math.isfinite(value):
        raise ArithmeticError("nonfinite_interval_endpoint")
    return _require_normal_or_zero(math.nextafter(value, -math.inf))


def _up(value: float) -> float:
    if not math.isfinite(value):
        raise ArithmeticError("nonfinite_interval_endpoint")
    return _require_normal_or_zero(math.nextafter(value, math.inf))


def _add_scalar(a: float, b: float) -> tuple[float, bool]:
    """Add finite normal-or-zero binary64 values; return result and exactness.

    Exact zero and addition by zero are recognized without widening.  A result
    that could have been flushed to zero, or that is subnormal, refuses the
    fast path and is delegated to the exact fallback.
    """
    if not math.isfinite(a) or not math.isfinite(b):
        raise ArithmeticError("nonfinite_addend")
    if ((a != 0.0 and abs(a) < sys.float_info.min) or
            (b != 0.0 and abs(b) < sys.float_info.min)):
        raise ArithmeticError("subnormal_addend")
    if a == 0.0:
        return b, True
    if b == 0.0:
        return a, True
    if a == -b:
        return 0.0, True
    value = a + b
    if not math.isfinite(value):
        raise ArithmeticError("nonfinite_interval_sum")
    if value == 0.0:
        raise ArithmeticError("possible_flushed_addition")
    if abs(value) < sys.float_info.min:
        raise ArithmeticError("subnormal_sum")
    return value, False


def _mul_scalar(a: float, b: float) -> tuple[float, bool]:
    """Multiply finite normal-or-zero binary64 values with fail-closed underflow."""
    if not math.isfinite(a) or not math.isfinite(b):
        raise ArithmeticError("nonfinite_factor")
    if ((a != 0.0 and abs(a) < sys.float_info.min) or
            (b != 0.0 and abs(b) < sys.float_info.min)):
        raise ArithmeticError("subnormal_factor")
    if a == 0.0 or b == 0.0:
        return 0.0, True
    value = a * b
    if not math.isfinite(value):
        raise ArithmeticError("nonfinite_interval_product")
    if value == 0.0:
        raise ArithmeticError("possible_flushed_product")
    if abs(value) < sys.float_info.min:
        raise ArithmeticError("subnormal_product")
    return value, False


def _add_interval(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    low, low_exact = _add_scalar(a[0], b[0])
    high, high_exact = _add_scalar(a[1], b[1])
    return (low if low_exact else _down(low), high if high_exact else _up(high))


def _mul_interval(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    candidates: list[tuple[float, float]] = []
    for left in (a[0], a[1]):
        for right in (b[0], b[1]):
            value, exact = _mul_scalar(left, right)
            candidates.append((value, value) if exact else (_down(value), _up(value)))
    return min(item[0] for item in candidates), max(item[1] for item in candidates)


def _matrix_kind_and_count(matrix: object, n: int, budget: int) -> tuple[str, int]:
    if isinstance(matrix, np.ndarray):
        if matrix.dtype != np.dtype(np.float64) or matrix.ndim != 2 or matrix.shape != (n, n):
            raise ValueError("fast_path_requires_dense_float64_square")
        if matrix.size > budget:
            raise OverflowError("fast_coefficient_budget")
        if not np.all(np.isfinite(matrix)):
            raise ValueError("nonfinite_matrix")
        if any(_is_subnormal(float(x)) for x in matrix.flat):
            raise ValueError("subnormal_matrix_entry")
        return "dense", int(matrix.size)

    if not (isspmatrix_csr(matrix) or isspmatrix_csc(matrix)):
        raise ValueError("fast_path_supports_dense_csr_csc_only")
    if matrix.dtype != np.dtype(np.float64) or matrix.shape != (n, n):
        raise ValueError("fast_path_requires_sparse_float64_square")
    if matrix.data.ndim != 1 or matrix.indices.ndim != 1 or matrix.indptr.ndim != 1:
        raise ValueError("invalid_sparse_array_dimensions")
    if matrix.data.size > budget:
        raise OverflowError("fast_coefficient_budget")
    if not np.all(np.isfinite(matrix.data)):
        raise ValueError("nonfinite_matrix")
    if any(_is_subnormal(float(x)) for x in matrix.data):
        raise ValueError("subnormal_matrix_entry")
    ptr, indices = matrix.indptr, matrix.indices
    if (ptr.dtype.kind not in "iu" or indices.dtype.kind not in "iu" or
        len(ptr) != n + 1 or int(ptr[0]) != 0 or int(ptr[-1]) != len(matrix.data) or
        len(indices) != len(matrix.data) or np.any(ptr[1:] < ptr[:-1]) or
        np.any(indices < 0) or np.any(indices >= n)):
        raise ValueError("invalid_sparse_structure")
    return ("csr" if isspmatrix_csr(matrix) else "csc"), len(matrix.data)


def _is_subnormal(value: float) -> bool:
    return value != 0.0 and abs(value) < sys.float_info.min


def _matvec_enclosures(
    matrix: object,
    kind: str,
    vector: np.ndarray,
    n: int,
    deadline: float,
) -> list[tuple[float, float]]:
    """Stream matrix slots into row intervals; extra storage is O(n), not O(nnz)."""
    result = [(0.0, 0.0) for _ in range(n)]
    if kind == "dense":
        for i in range(n):
            _check_deadline(deadline)
            total = (0.0, 0.0)
            for j in range(n):
                product = _mul_interval(
                    (float(matrix[i, j]), float(matrix[i, j])),
                    (float(vector[j]), float(vector[j])),
                )
                total = _add_interval(total, product)
            result[i] = total
        return result
    ptr, indices, data = matrix.indptr, matrix.indices, matrix.data
    if kind == "csr":
        for i in range(n):
            _check_deadline(deadline)
            total = (0.0, 0.0)
            for pos in range(int(ptr[i]), int(ptr[i + 1])):
                if (pos & 255) == 0:
                    _check_deadline(deadline)
                j = int(indices[pos])
                product = _mul_interval(
                    (float(data[pos]), float(data[pos])),
                    (float(vector[j]), float(vector[j])),
                )
                total = _add_interval(total, product)
            result[i] = total
        return result
    # CSC is traversed column-wise and accumulates into each output row. Exact
    # matrix semantics are independent of this order; intervals enclose it.
    for j in range(n):
        _check_deadline(deadline)
        x = (float(vector[j]), float(vector[j]))
        for pos in range(int(ptr[j]), int(ptr[j + 1])):
            if (pos & 255) == 0:
                _check_deadline(deadline)
            i = int(indices[pos])
            product = _mul_interval((float(data[pos]), float(data[pos])), x)
            result[i] = _add_interval(result[i], product)
    return result


def _upper_add(a: float, b: float) -> float:
    result, exact = _add_scalar(a, b)
    return result if exact else _up(result)


def _check_deadline(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise TimeoutError("time_budget")


def check_modal_residual_hybrid(
    stiffness: object, mass: object, eigenvalue: object, vector: object,
    tolerance: object, *, max_dimension: int = FAST_MAX_DIMENSION,
    max_terms: int = FAST_MAX_TERMS,
    max_operations: int = FAST_MAX_OPERATIONS,
    max_estimated_memory_bytes: int = FAST_MAX_ESTIMATED_MEMORY_BYTES,
    max_seconds: float = 2.0,
    exact_fallback: bool = True,
) -> HybridResult:
    """Return conditional interval PASS, exact FAIL/PASS, or INCONCLUSIVE.

    Only an interval upper bound that proves the tolerance returns on the fast
    path. Ambiguous or unsupported arithmetic may fall back to the exact
    prototype within the caller's budget; budget overruns are INCONCLUSIVE.
    """
    terms = 0
    try:
        if (type(exact_fallback) is not bool or
            type(max_dimension) is not int or not 1 <= max_dimension <= FAST_MAX_DIMENSION or
            type(max_terms) is not int or not 1 <= max_terms <= FAST_MAX_TERMS or
            type(max_operations) is not int or not 1 <= max_operations <= FAST_MAX_OPERATIONS or
            type(max_estimated_memory_bytes) is not int or
            not 1 <= max_estimated_memory_bytes <= FAST_MAX_ESTIMATED_MEMORY_BYTES or
            isinstance(max_seconds, bool) or not isinstance(max_seconds, (int, float)) or
            not math.isfinite(float(max_seconds)) or not 0.0 < float(max_seconds) <= 60.0):
            return HybridResult("INCONCLUSIVE", "none", "invalid_or_exceeded_prototype_budget", 0)
        started = time.monotonic()
        deadline = started + float(max_seconds)
        # Enforce caller budgets before any unsupported dtype/representation can
        # trigger the exact fallback. The fallback has its own caps, but must
        # never bypass a tighter caller-supplied envelope.
        if isinstance(vector, np.ndarray) and vector.ndim == 1:
            n_preflight = int(vector.size)
            if n_preflight > max_dimension:
                return HybridResult("INCONCLUSIVE", "none", "dimension_budget", 0)
            preflight_terms = 0
            for matrix in (stiffness, mass):
                if isinstance(matrix, np.ndarray):
                    preflight_terms += int(matrix.size)
                elif isspmatrix_csr(matrix) or isspmatrix_csc(matrix):
                    data = getattr(matrix, "data", None)
                    if isinstance(data, np.ndarray):
                        preflight_terms += int(data.size)
            if preflight_terms > max_terms:
                return HybridResult("INCONCLUSIVE", "none", "combined_coefficient_budget", preflight_terms)
            estimated_ops = 24 * preflight_terms + 32 * n_preflight
            if estimated_ops > max_operations:
                return HybridResult("INCONCLUSIVE", "none", "operation_budget", preflight_terms,
                                    operations_estimate=estimated_ops)
            fast_memory_estimate = 1_024 + 512 * n_preflight
            if fast_memory_estimate > max_estimated_memory_bytes:
                return HybridResult("INCONCLUSIVE", "none", "estimated_memory_budget", preflight_terms,
                                    operations_estimate=estimated_ops)
            if time.monotonic() >= deadline:
                return HybridResult("INCONCLUSIVE", "none", "time_budget_before_preflight", preflight_terms,
                                    operations_estimate=estimated_ops)
        if not _environment_supported():
            raise ValueError("unsupported_ieee_environment")
        if not isinstance(vector, np.ndarray) or vector.dtype != np.dtype(np.float64):
            raise ValueError("fast_path_requires_float64_vector")
        if vector.ndim != 1 or vector.size == 0 or not np.all(np.isfinite(vector)):
            raise ValueError("invalid_vector")
        if vector.size > max_dimension:
            return HybridResult("INCONCLUSIVE", "none", "dimension_budget", 0)
        n = vector.size
        if isinstance(eigenvalue, (bool, np.bool_)) or not isinstance(eigenvalue, (float, np.float64)):
            raise ValueError("fast_path_requires_binary64_eigenvalue")
        if isinstance(tolerance, (bool, np.bool_)) or not isinstance(tolerance, (float, np.float64)):
            raise ValueError("fast_path_requires_binary64_tolerance")
        lam, tau = float(eigenvalue), float(tolerance)
        if not math.isfinite(lam) or not math.isfinite(tau) or tau <= 0.0:
            raise ValueError("invalid_eigenvalue_or_tolerance")
        kkind, knnz = _matrix_kind_and_count(stiffness, n, max_terms)
        mkind, mnnz = _matrix_kind_and_count(mass, n, max_terms)
        terms = knnz + mnnz
        if terms > max_terms:
            return HybridResult("INCONCLUSIVE", "none", "combined_coefficient_budget", terms)
        operations_estimate = 24 * terms + 32 * n
        if operations_estimate > max_operations:
            return HybridResult("INCONCLUSIVE", "none", "operation_budget", terms,
                                operations_estimate=operations_estimate)
        if not _environment_supported():
            raise ValueError("unsupported_ieee_environment_before_products")
        if any(_is_subnormal(float(x)) for x in vector):
            raise ValueError("subnormal_vector_entry")
        kphi = _matvec_enclosures(stiffness, kkind, vector, n, deadline)
        mphi = _matvec_enclosures(mass, mkind, vector, n, deadline)
        lmass = [_mul_interval((lam, lam), x) for x in mphi]
        residual = []
        for k, b in zip(kphi, lmass):
            low, low_exact = _add_scalar(k[0], -b[1])
            high, high_exact = _add_scalar(k[1], -b[0])
            residual.append((low if low_exact else _down(low), high if high_exact else _up(high)))
        residual_l1_upper = 0.0
        reference_linf_lower = 0.0
        for r, k, b in zip(residual, kphi, lmass):
            residual_l1_upper = _upper_add(residual_l1_upper, max(abs(r[0]), abs(r[1])))
            for interval in (k, b):
                lower_abs = 0.0 if interval[0] <= 0.0 <= interval[1] else min(abs(interval[0]), abs(interval[1]))
                reference_linf_lower = max(reference_linf_lower, lower_abs)
        if not _environment_supported():
            raise ValueError("unsupported_ieee_environment_after_products")
        if time.monotonic() >= deadline:
            raise TimeoutError("time_budget_after_interval")
        if reference_linf_lower > 0.0:
            # Fraction compares the exact binary endpoints; avoids a rounded quotient.
            if Fraction.from_float(residual_l1_upper) <= Fraction.from_float(tau) * Fraction.from_float(reference_linf_lower):
                return HybridResult(
                    "PASS_CONDITIONAL", "outward_interval",
                    "l1_upper_over_linf_lower; assumes IEEE-754 binary64 RNE and gradual underflow",
                    terms, residual_l1_upper, reference_linf_lower, operations_estimate,
                )
    except OverflowError as exc:
        # A caller-supplied resource envelope cannot be bypassed via the exact fallback.
        if "budget" in str(exc):
            return HybridResult("INCONCLUSIVE", "none", str(exc), terms)
        fast_reason = str(exc) or type(exc).__name__
    except TimeoutError as exc:
        return HybridResult("INCONCLUSIVE", "none", str(exc), terms,
                            operations_estimate=24 * terms + 32 * int(getattr(vector, "size", 0)))
    except (ArithmeticError, TypeError, ValueError, IndexError, AttributeError, MemoryError) as exc:
        fast_reason = str(exc) or type(exc).__name__
    else:
        fast_reason = "interval_did_not_prove_pass"

    if not exact_fallback:
        return HybridResult(
            "INCONCLUSIVE", "interval_only", fast_reason, terms,
            operations_estimate=24 * terms + 32 * int(getattr(vector, "size", 0)),
        )

    vector_size = int(getattr(vector, "size", 0))
    exact_memory_estimate = 1_024 + 4_096 * vector_size
    if exact_memory_estimate > max_estimated_memory_bytes:
        return HybridResult("INCONCLUSIVE", "none", "estimated_exact_memory_budget", terms,
                            operations_estimate=24 * terms + 32 * vector_size)
    if time.monotonic() >= deadline:
        return HybridResult("INCONCLUSIVE", "none", "time_budget_before_exact_fallback", terms,
                            operations_estimate=24 * terms + 32 * vector_size)
    exact = check_modal_residual(
        stiffness, mass, eigenvalue, vector, tolerance,
        max_terms=min(max_terms, 2048),
    )
    if time.monotonic() - started > float(max_seconds):
        return HybridResult("INCONCLUSIVE", "none", "time_budget_after_exact_fallback", exact.coefficients,
                            operations_estimate=24 * exact.coefficients +
                            32 * vector_size)
    status = {"PASS_CERTIFIED": "PASS_CERTIFIED", "FAIL": "FAIL"}.get(exact.status, "INCONCLUSIVE")
    return HybridResult(status, "exact_fallback", f"{fast_reason}; {exact.reason}", exact.coefficients,
                        operations_estimate=24 * exact.coefficients + 32 * int(getattr(vector, "size", 0)))


def check_modal_residual_conservative(
    stiffness: object,
    mass: object,
    eigenvalue: object,
    vector: object,
    tolerance: object,
    **budgets: int,
) -> HybridResult:
    """Use only the conditional interval path; ambiguous cases are INCONCLUSIVE."""
    result = check_modal_residual_hybrid(
        stiffness, mass, eigenvalue, vector, tolerance, exact_fallback=False, **budgets
    )
    return result
