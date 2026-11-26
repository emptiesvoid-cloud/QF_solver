"""Exact squared residual comparison for finite binary64 CSR inputs (research only)."""
from fractions import Fraction

import numpy as np


def exact_check(data, indices, indptr, shape, rhs, candidate, threshold, *, max_nnz=100000):
    """Compare exact dyadic sums; reject noncanonical CSR and undefined normalization."""
    data, indices, indptr = np.asarray(data), np.asarray(indices), np.asarray(indptr)
    rhs, candidate = np.asarray(rhs), np.asarray(candidate)
    if len(shape) != 2 or shape[0] != shape[1] or shape[0] < 1:
        raise ValueError("invalid matrix shape")
    n = shape[0]
    if data.dtype != np.float64 or rhs.dtype != np.float64 or candidate.dtype != np.float64:
        raise ValueError("binary64 required")
    if indices.dtype.kind not in "iu" or indptr.dtype.kind not in "iu":
        raise ValueError("integer CSR indices required")
    if data.ndim != 1 or indices.shape != data.shape or indptr.shape != (n + 1,) or rhs.shape != (n,) or candidate.shape != (n,):
        raise ValueError("incompatible dimensions")
    if data.size > max_nnz or max_nnz < 0:
        raise ValueError("resource budget exceeded")
    if not all(np.all(np.isfinite(a)) for a in (data, rhs, candidate)) or not isinstance(threshold, float) or not np.isfinite(threshold) or threshold <= 0:
        raise ValueError("finite data and positive binary64 threshold required")
    if indptr[0] != 0 or indptr[-1] != data.size or np.any(indptr[1:] < indptr[:-1]):
        raise ValueError("invalid CSR pointers")
    if np.any(indices < 0) or np.any(indices >= n):
        raise ValueError("invalid CSR index")
    for i in range(n):
        row = indices[indptr[i]:indptr[i+1]]
        if np.any(row[1:] <= row[:-1]):
            raise ValueError("CSR rows must be sorted and duplicate-free")
    f = lambda v: Fraction.from_float(float(v))  # noqa: E731
    xx = [f(v) for v in candidate]
    bb = [f(v) for v in rhs]
    ax = [sum((f(data[k]) * xx[int(indices[k])] for k in range(int(indptr[i]), int(indptr[i+1]))), Fraction()) for i in range(n)]
    residual_squared = sum(((ax[i]-bb[i])**2 for i in range(n)), Fraction())
    denominator_squared = max(sum((v*v for v in ax), Fraction()), sum((v*v for v in bb), Fraction()))
    if denominator_squared == 0:
        raise ValueError("zero normalization denominator")
    return {
        "decision": "PASS" if residual_squared <= f(threshold)**2 * denominator_squared else "FAIL",
        "residual_squared": residual_squared,
        "denominator_squared": denominator_squared,
    }
