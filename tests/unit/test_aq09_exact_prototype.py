"""Bounded algebraic prototype checks; no assembly or FEM solve."""
import numpy as np
import pytest
from scipy.sparse import csc_matrix, csr_matrix
from fractions import Fraction

from experiments.aq09_exact_modal_residual import check_modal_residual


@pytest.mark.parametrize("factory", [np.asarray, csr_matrix, csc_matrix])
def test_spd_partial_underflow_is_fail(factory: object) -> None:
    k = np.array([[1e-16, 1e-17], [1e-17, 2e-18]])
    m = np.diag([1e-16, 1e-18])
    result = check_modal_residual(factory(k), factory(m), 1.0, np.array([1e-307, 0.0]), 1e-7)
    assert result.status == "FAIL"


@pytest.mark.parametrize("factory", [csr_matrix, csc_matrix])
def test_sparse_cancellation_is_fail(factory: object) -> None:
    k = np.zeros((4, 4))
    m = np.zeros((4, 4))
    k[0] = [1e16, 1.0, -1e16, 1.0]
    m[0, 3] = 1.0
    result = check_modal_residual(factory(k), factory(m), 1.0, np.ones(4), 1e-7)
    assert result.status == "FAIL"


@pytest.mark.parametrize("scale", [1e-300, 1e-12, 1.0, 1e300])
def test_scale_and_ordinary_pass(scale: float) -> None:
    matrix = np.diag([scale, scale])
    assert check_modal_residual(matrix, matrix, 1.0, np.array([1.0, 0.0]), 1e-7).status == "PASS_CERTIFIED"
    assert check_modal_residual(matrix, 2 * matrix, 1.0, np.array([1.0, 0.0]), 1e-7).status == "FAIL"


@pytest.mark.parametrize("factory", [csr_matrix, csc_matrix])
def test_sparse_duplicate_entries_are_exact(factory: object) -> None:
    k = factory((np.array([1e16, 1.0, -1e16]), np.array([0, 0, 0]), np.array([0, 3])), shape=(1, 1))
    m = factory(np.ones((1, 1)))
    assert check_modal_residual(k, m, 1.0, np.ones(1), 1e-7).status == "PASS_CERTIFIED"


def test_inconclusive_guards_and_integer_exactness() -> None:
    k = np.zeros((1, 1))
    v = np.ones(1)
    assert check_modal_residual(k, k, 1.0, v, 1e-7).reason == "zero_reference"
    assert check_modal_residual(np.array([[np.nan]]), k, 1.0, v, 1e-7).status == "INCONCLUSIVE"
    assert check_modal_residual(np.array([[np.inf]]), k, 1.0, v, 1e-7).status == "INCONCLUSIVE"
    assert check_modal_residual(np.ones((1, 1)), np.ones((1, 1)), 1.0, v, 1e-7, max_terms=1).reason == "coefficient_budget"
    assert check_modal_residual(np.ones((1, 1)), np.ones((1, 1)), 1.0, v, True).status == "INCONCLUSIVE"
    a = np.array([[2**53 + 1]], dtype=np.int64)
    b = np.array([[2**53]], dtype=np.int64)
    assert check_modal_residual(a, b, 1, v, 1e-20).status == "FAIL"


def test_review_counterexamples_invalid_scalar_and_sparse_indices() -> None:
    matrix = np.eye(2)
    vector = np.array([1.0, 0.0])
    result = check_modal_residual(matrix, matrix, Fraction(10**17 + 1, 10**17), vector, Fraction(1, 10**20))
    assert result.status == "INCONCLUSIVE"
    bad = csr_matrix(matrix)
    bad.indices = bad.indices.astype(float)
    bad.indices[0] = 0.9
    result = check_modal_residual(bad, csr_matrix(matrix), 1.0, vector, 1e-7)
    assert result.reason == "invalid_sparse_index_dtype"
    bad = csr_matrix(matrix)
    bad.indptr = bad.indptr.astype(float)
    bad.indptr[1] = 0.9
    result = check_modal_residual(bad, csr_matrix(matrix), 1.0, vector, 1e-7)
    assert result.reason == "invalid_sparse_index_dtype"


@pytest.mark.parametrize("dtype", [np.float16, np.float32, np.float64])
def test_represented_float_boundary_and_limits(dtype: object) -> None:
    k = np.array([[2.0]], dtype=dtype)
    m = np.array([[1.0]], dtype=dtype)
    v = np.array([1.0], dtype=dtype)
    assert check_modal_residual(k, m, dtype(1.0), v, dtype(0.5)).status == "PASS_CERTIFIED"
    assert check_modal_residual(k, m, dtype(1.0), v, dtype(0.25)).status == "FAIL"
    assert check_modal_residual(k, m, dtype(1.0), v, dtype(0.5), max_bits=1).status == "INCONCLUSIVE"


@pytest.mark.parametrize("factory", [np.asarray, csr_matrix, csc_matrix])
def test_spd_cancellation_against_exact_fraction_reference(factory: object) -> None:
    a, d = 1e16, 0.5
    k = np.zeros((4, 4))
    k[0, 0] = 1.0
    k[1:, 1:] = [[a, d, -a], [d, a, -a], [-a, -a, 2 * a]]
    m = np.diag([1.0, 1e-9, 1e-9, 1e-9])
    vector = np.ones(4)
    exact_k = [sum(Fraction.from_float(float(x)) for x in row) for row in k]
    exact_m = [sum(Fraction.from_float(float(x)) for x in row) for row in m]
    q = sum((x - y) ** 2 for x, y in zip(exact_k, exact_m))
    reference = max(sum(x * x for x in exact_k), sum(y * y for y in exact_m))
    assert q > Fraction.from_float(1e-7) ** 2 * reference
    assert check_modal_residual(factory(k), factory(m), 1.0, vector, 1e-7).status == "FAIL"


def test_singular_and_small_eigenvalue() -> None:
    k = np.diag([0.0, 1e-300])
    m = np.eye(2)
    assert check_modal_residual(k, m, 1e-300, np.array([0.0, 1.0]), 1e-7).status == "PASS_CERTIFIED"
    assert check_modal_residual(np.zeros((2, 2)), m, 0.0, np.array([1.0, 0.0]), 1e-7).reason == "zero_reference"


def test_total_underflow_remains_exactly_detectable() -> None:
    k = np.array([[1e-300]])
    m = np.array([[2e-300]])
    assert check_modal_residual(k, m, 1.0, np.array([1e-100]), 1e-7).status == "FAIL"
