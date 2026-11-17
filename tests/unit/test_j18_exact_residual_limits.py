"""Exact residual resource limits for the sparse research verifier."""

from __future__ import annotations

import numpy as np
from scipy.sparse import csr_matrix

from research.j17.exact_residual import evaluate_exact_residual


def test_exact_csr_residual_returns_inconclusive_on_fraction_bit_budget() -> None:
    matrix = csr_matrix(np.array([[1.0 + 0.0j]], dtype=np.complex128))
    result = evaluate_exact_residual(
        matrix,
        np.array([1.0 + 0.0j], dtype=np.complex128),
        np.array([1.0 + 0.0j], dtype=np.complex128),
        max_fraction_bits=8,
    )

    assert result.status == "INCONCLUSIVE"
    assert "bit-length limit" in result.reason


def test_exact_residual_rejects_scalar_conversion_overflow() -> None:
    matrix = np.array([[1.0]])
    vector = np.array([1.0])
    for parameter in ("tolerance", "max_elapsed_seconds"):
        result = evaluate_exact_residual(matrix, vector, vector, **{parameter: 10**400})
        assert result.status == "INCONCLUSIVE"
        assert "scalar" in result.reason
