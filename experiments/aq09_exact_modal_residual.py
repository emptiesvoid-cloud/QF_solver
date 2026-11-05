"""Bounded experimental residual check for represented real numbers; not a solver.

The comparison uses exact rational arithmetic, not a floating-point error bound.
It is intentionally not imported by the production modal route.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from numbers import Integral

import numpy as np
from scipy.sparse import isspmatrix_csc, isspmatrix_csr

MAX_DIMENSION = 512
MAX_TERMS = 2048
MAX_BITS = 8192


class _Refuse(Exception):
    pass


@dataclass(frozen=True)
class CheckResult:
    status: str
    reason: str
    coefficients: int
    max_integer_bits: int


def check_modal_residual(stiffness: object, mass: object, eigenvalue: object,
                         vector: object, tolerance: object, *, max_terms: int = MAX_TERMS,
                         max_bits: int = MAX_BITS) -> CheckResult:
    """Compare squared exact residual and reference, or return INCONCLUSIVE.

    Integers and IEEE binary16/32/64 inputs are exact. Real dense numpy arrays
    and SciPy CSR/CSC matrices only. Sparse duplicate entries are summed as
    rationals. A zero reference and any unsupported input are inconclusive.
    Budgets bound input dimensions, stored terms and rational integer sizes.
    """
    seen_bits = 0
    terms = 0

    def check(q: Fraction) -> Fraction:
        nonlocal seen_bits
        bits = max(q.numerator.bit_length(), q.denominator.bit_length())
        seen_bits = max(seen_bits, bits)
        if bits > max_bits:
            raise _Refuse("integer_bit_budget")
        return q

    def scalar(v: object) -> Fraction:
        if isinstance(v, (bool, np.bool_)):
            raise _Refuse("unsupported_scalar")
        if isinstance(v, Integral):
            return check(Fraction(int(v)))
        if isinstance(v, (float, np.floating)):
            if isinstance(v, np.floating) and v.dtype.itemsize > 8:
                raise _Refuse("unsupported_scalar_precision")
            f = float(v)
            if not np.isfinite(f):
                raise _Refuse("nonfinite_input")
            return check(Fraction.from_float(f))
        raise _Refuse("unsupported_scalar")

    def dtype_ok(a: np.ndarray) -> None:
        if a.dtype.kind not in "fiu" or a.dtype.itemsize > 8:
            raise _Refuse("unsupported_dtype")
        if a.dtype.kind == "f" and not np.all(np.isfinite(a)):
            raise _Refuse("nonfinite_input")

    def matrix_entries(mat: object, n: int) -> tuple[int, object]:
        if isinstance(mat, np.ndarray):
            if mat.ndim != 2 or mat.shape != (n, n):
                raise _Refuse("matrix_shape")
            if mat.size > max_terms:
                raise _Refuse("coefficient_budget")
            dtype_ok(mat)
            return mat.size, ((i, j, mat[i, j]) for i in range(n) for j in range(n))
        if isspmatrix_csr(mat) or isspmatrix_csc(mat):
            if mat.shape != (n, n):
                raise _Refuse("matrix_shape")
            if len(mat.data) > max_terms:
                raise _Refuse("coefficient_budget")
            dtype_ok(mat.data)
            indptr, indices, data = mat.indptr, mat.indices, mat.data
            if (not isinstance(indptr, np.ndarray) or not isinstance(indices, np.ndarray) or
                indptr.ndim != 1 or indices.ndim != 1 or
                indptr.dtype.kind not in "iu" or indices.dtype.kind not in "iu"):
                raise _Refuse("invalid_sparse_index_dtype")
            if (len(indptr) != n + 1 or int(indptr[0]) != 0 or
                int(indptr[-1]) != len(data) or len(indices) != len(data) or
                np.any(indptr[1:] < indptr[:-1]) or np.any(indices < 0) or np.any(indices >= n)):
                raise _Refuse("invalid_sparse_structure")
            def entries():
                for outer in range(n):
                    for pos in range(int(indptr[outer]), int(indptr[outer + 1])):
                        inner = int(indices[pos])
                        yield (outer, inner, data[pos]) if isspmatrix_csr(mat) else (inner, outer, data[pos])
            return len(data), entries()
        raise _Refuse("unsupported_matrix")

    try:
        if (type(max_terms) is not int or not 0 <= max_terms <= MAX_TERMS or
            type(max_bits) is not int or not 1 <= max_bits <= MAX_BITS):
            raise _Refuse("invalid_budget")
        if not isinstance(vector, np.ndarray):
            raise _Refuse("unsupported_vector")
        v = vector
        if v.ndim != 1 or not 0 < v.size <= MAX_DIMENSION:
            raise _Refuse("vector_shape_or_budget")
        dtype_ok(v)
        n = v.size
        eig, tol = scalar(eigenvalue), scalar(tolerance)
        if tol <= 0:
            raise _Refuse("invalid_tolerance")
        vv = [scalar(x) for x in v]
        if not any(vv):
            raise _Refuse("zero_vector")
        count_k, entries_k = matrix_entries(stiffness, n)
        count_m, entries_m = matrix_entries(mass, n)
        terms = count_k + count_m
        if terms > max_terms:
            raise _Refuse("coefficient_budget")
        a = [Fraction(0) for _ in range(n)]
        b = [Fraction(0) for _ in range(n)]
        for target, entries in ((a, entries_k), (b, entries_m)):
            for i, j, val in entries:
                target[i] = check(target[i] + check(scalar(val) * vv[j]))
        b = [check(eig * x) for x in b]
        q = da = db = Fraction(0)
        for x, y in zip(a, b):
            delta = check(x - y)
            q = check(q + check(delta * delta))
            da = check(da + check(x * x))
            db = check(db + check(y * y))
        reference = max(da, db)
        if reference == 0:
            raise _Refuse("zero_reference")
        limit = check(check(tol * tol) * reference)
        return CheckResult("PASS_CERTIFIED" if q <= limit else "FAIL", "exact_comparison", terms, seen_bits)
    except (_Refuse, ArithmeticError, TypeError, ValueError, IndexError, AttributeError, MemoryError) as exc:
        return CheckResult("INCONCLUSIVE", str(exc) or type(exc).__name__, terms, seen_bits)
