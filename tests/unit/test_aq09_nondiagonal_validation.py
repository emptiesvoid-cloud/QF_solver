"""Deterministic algebra-only AQ-09 checks; no mesh assembly or FEM solve."""
from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest
from scipy.sparse import csc_matrix, csr_matrix

from experiments.aq09_exact_modal_residual import check_modal_residual
from experiments.aq09_hybrid_experimental import (
    check_modal_residual_conservative,
    check_modal_residual_hybrid,
)


def _generalized_spd_pair(n: int = 8, *, weight: float = 2.0**-10):
    """K=lambda*M+L, with positive diagonal M and graph Laplacian L."""
    mass_diagonal = np.array([0.5, 1.0, 2.0, 4.0] * ((n + 3) // 4), dtype=np.float64)[:n]
    eigenvalue = 0.25
    stiffness = np.diag(eigenvalue * mass_diagonal)
    edges = []
    for i in range(n):
        edges.append((i, (i + 1) % n, weight))
    for i in range(0, n - 2, 3):
        edges.append((i, i + 2, weight / 2.0))
    for i, j, edge_weight in edges:
        stiffness[i, i] += edge_weight
        stiffness[j, j] += edge_weight
        stiffness[i, j] -= edge_weight
        stiffness[j, i] -= edge_weight
    mass = np.diag(mass_diagonal)
    return stiffness, mass, eigenvalue, np.ones(n, dtype=np.float64)


def _with_duplicate_csr(matrix: np.ndarray) -> csr_matrix:
    data: list[float] = []
    indices: list[int] = []
    indptr = [0]
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = float(matrix[i, j])
            if value == 0.0:
                continue
            if (i, j) == (0, 0):
                data.extend((value / 2.0, value / 2.0))
                indices.extend((j, j))
            else:
                data.append(value)
                indices.append(j)
        indptr.append(len(data))
    return csr_matrix(
        (np.asarray(data, dtype=np.float64), np.asarray(indices, dtype=np.int32),
         np.asarray(indptr, dtype=np.int32)),
        shape=matrix.shape,
    )


def _with_duplicate_csc(matrix: np.ndarray) -> csc_matrix:
    data: list[float] = []
    indices: list[int] = []
    indptr = [0]
    for j in range(matrix.shape[1]):
        for i in range(matrix.shape[0]):
            value = float(matrix[i, j])
            if value == 0.0:
                continue
            if (i, j) == (0, 0):
                data.extend((value / 2.0, value / 2.0))
                indices.extend((i, i))
            else:
                data.append(value)
                indices.append(i)
        indptr.append(len(data))
    return csc_matrix(
        (np.asarray(data, dtype=np.float64), np.asarray(indices, dtype=np.int32),
         np.asarray(indptr, dtype=np.int32)),
        shape=matrix.shape,
    )


@pytest.mark.parametrize(
    "matrix_format", ["dense", "csr", "csc", "csr_duplicates", "csc_duplicates"],
)
def test_nondiagonal_spd_generalized_eigenpair_is_accepted(matrix_format):
    stiffness, mass, eigenvalue, vector = _generalized_spd_pair(8)
    if matrix_format == "csr":
        stiffness, mass = csr_matrix(stiffness), csr_matrix(mass)
    elif matrix_format == "csc":
        stiffness, mass = csc_matrix(stiffness), csc_matrix(mass)
    elif matrix_format == "csr_duplicates":
        stiffness, mass = _with_duplicate_csr(stiffness), _with_duplicate_csr(mass)
    elif matrix_format == "csc_duplicates":
        stiffness, mass = _with_duplicate_csc(stiffness), _with_duplicate_csc(mass)

    exact = check_modal_residual(stiffness, mass, eigenvalue, vector, 1.0e-7)
    hybrid = check_modal_residual_hybrid(stiffness, mass, eigenvalue, vector, 1.0e-7)

    assert exact.status == "PASS_CERTIFIED"
    assert hybrid.status in {"PASS_CONDITIONAL", "PASS_CERTIFIED"}


@pytest.mark.parametrize("matrix_format", ["dense", "csr", "csc"])
def test_nondiagonal_perturbed_mode_is_not_accepted(matrix_format):
    stiffness, mass, eigenvalue, vector = _generalized_spd_pair(8)
    vector[0] += 2.0**-10
    if matrix_format == "csr":
        stiffness, mass = csr_matrix(stiffness), csr_matrix(mass)
    elif matrix_format == "csc":
        stiffness, mass = csc_matrix(stiffness), csc_matrix(mass)

    exact = check_modal_residual(stiffness, mass, eigenvalue, vector, 1.0e-7)
    hybrid = check_modal_residual_hybrid(stiffness, mass, eigenvalue, vector, 1.0e-7)

    assert exact.status == "FAIL"
    assert hybrid.status == "FAIL"
    assert hybrid.path == "exact_fallback"


@pytest.mark.parametrize("scale", [2.0**-500, 1.0, 2.0**500])
@pytest.mark.parametrize("matrix_format", ["dense", "csr", "csc"])
def test_nondiagonal_generalized_pair_is_scale_invariant(scale, matrix_format):
    stiffness, mass, eigenvalue, vector = _generalized_spd_pair(6, weight=2.0**-8)
    stiffness *= scale
    mass *= scale
    if matrix_format == "csr":
        stiffness, mass = csr_matrix(stiffness), csr_matrix(mass)
    elif matrix_format == "csc":
        stiffness, mass = csc_matrix(stiffness), csc_matrix(mass)

    exact = check_modal_residual(stiffness, mass, eigenvalue, vector, 1.0e-7)
    result = check_modal_residual_hybrid(stiffness, mass, eigenvalue, vector, 1.0e-7)

    assert exact.status == "PASS_CERTIFIED"
    assert result.status in {"PASS_CONDITIONAL", "PASS_CERTIFIED"}


def test_severe_cancellation_uses_exact_fallback_for_a_valid_sparse_mode():
    n = 6
    stiffness = 2.0 * np.eye(n, dtype=np.float64)
    edge_weight = 2.0**40
    for i in range(n):
        j = (i + 1) % n
        stiffness[i, i] += edge_weight
        stiffness[j, j] += edge_weight
        stiffness[i, j] -= edge_weight
        stiffness[j, i] -= edge_weight
    mass = np.eye(n, dtype=np.float64)
    vector = np.ones(n, dtype=np.float64)
    matrix = csr_matrix(stiffness)

    exact = check_modal_residual(matrix, csr_matrix(mass), 2.0, vector, 1.0e-7)
    result = check_modal_residual_hybrid(matrix, csr_matrix(mass), 2.0, vector, 1.0e-7)

    assert exact.status == "PASS_CERTIFIED"
    assert result.status == "PASS_CERTIFIED"
    assert result.path == "exact_fallback"


def test_close_modes_and_multiplicity_keep_exact_constant_mode():
    stiffness, mass, eigenvalue, vector = _generalized_spd_pair(10, weight=2.0**-35)
    exact = check_modal_residual(stiffness, mass, eigenvalue, vector, 1.0e-7)
    result = check_modal_residual_hybrid(stiffness, mass, eigenvalue, vector, 1.0e-7)
    assert exact.status == "PASS_CERTIFIED"
    assert result.status in {"PASS_CONDITIONAL", "PASS_CERTIFIED"}


@pytest.mark.parametrize("matrix_format", ["dense", "csr", "csc"])
def test_close_but_distinct_eigenvalues_are_certified(matrix_format):
    eigenvalue_low = 0.25
    coupling = 2.0**-35
    stiffness = np.array(
        [[eigenvalue_low + coupling, -coupling],
         [-coupling, eigenvalue_low + coupling]],
        dtype=np.float64,
    )
    mass = np.eye(2, dtype=np.float64)
    pairs = (
        (eigenvalue_low, np.array([1.0, 1.0], dtype=np.float64)),
        (eigenvalue_low + 2.0 * coupling, np.array([1.0, -1.0], dtype=np.float64)),
    )
    if matrix_format == "csr":
        stiffness, mass = csr_matrix(stiffness), csr_matrix(mass)
    elif matrix_format == "csc":
        stiffness, mass = csc_matrix(stiffness), csc_matrix(mass)
    for eigenvalue, vector in pairs:
        exact = check_modal_residual(stiffness, mass, eigenvalue, vector, 1.0e-7)
        result = check_modal_residual_hybrid(stiffness, mass, eigenvalue, vector, 1.0e-7)
        assert exact.status == "PASS_CERTIFIED"
        assert result.status in {"PASS_CONDITIONAL", "PASS_CERTIFIED"}


def test_singular_rigid_mode_with_zero_reference_is_inconclusive():
    stiffness = np.array([[1.0, -1.0], [-1.0, 1.0]], dtype=np.float64)
    mass = np.eye(2, dtype=np.float64)
    vector = np.ones(2, dtype=np.float64)
    exact = check_modal_residual(stiffness, mass, 0.0, vector, 1.0e-7)
    hybrid = check_modal_residual_hybrid(stiffness, mass, 0.0, vector, 1.0e-7)
    conservative = check_modal_residual_conservative(stiffness, mass, 0.0, vector, 1.0e-7)
    assert exact.status == "INCONCLUSIVE"
    assert hybrid.status == "INCONCLUSIVE"
    assert conservative.status == "INCONCLUSIVE"


def test_operation_budget_returns_inconclusive_before_any_fallback():
    stiffness, mass, eigenvalue, vector = _generalized_spd_pair(4)
    result = check_modal_residual_hybrid(
        stiffness, mass, eigenvalue, vector, 1.0e-7, max_operations=1,
    )
    assert result.status == "INCONCLUSIVE"
    assert result.path == "none"
    assert result.reason == "operation_budget"


def test_working_memory_budget_returns_inconclusive_before_interval_allocation():
    stiffness, mass, eigenvalue, vector = _generalized_spd_pair(4)
    result = check_modal_residual_hybrid(
        stiffness, mass, eigenvalue, vector, 1.0e-7, max_estimated_memory_bytes=1_000,
    )
    assert result.status == "INCONCLUSIVE"
    assert result.path == "none"
    assert result.reason == "estimated_memory_budget"


def test_exact_fallback_memory_budget_returns_inconclusive():
    stiffness = np.diag(np.array([1.0e-16, 2.0e-16], dtype=np.float64))
    mass = np.eye(2, dtype=np.float64)
    vector = np.array([np.nextafter(0.0, 1.0), 1.0], dtype=np.float64)
    result = check_modal_residual_hybrid(
        stiffness, mass, 1.0, vector, 1.0e-7, max_estimated_memory_bytes=5_000,
    )
    assert result.status == "INCONCLUSIVE"
    assert result.path == "none"
    assert result.reason == "estimated_exact_memory_budget"


def test_time_budget_returns_inconclusive_before_products():
    stiffness, mass, eigenvalue, vector = _generalized_spd_pair(4)
    result = check_modal_residual_hybrid(
        stiffness, mass, eigenvalue, vector, 1.0e-7, max_seconds=1.0e-12,
    )
    assert result.status == "INCONCLUSIVE"
    assert result.path == "none"
    assert result.reason in {"time_budget_before_preflight", "time_budget"}


def test_exact_binary_reference_for_nondiagonal_residual():
    stiffness, mass, eigenvalue, vector = _generalized_spd_pair(4)
    vector[0] += 2.0**-10
    exact_binary = [Fraction.from_float(float(x)) for x in vector]
    row_zero = sum(
        Fraction.from_float(float(stiffness[0, j])) * exact_binary[j]
        for j in range(vector.size)
    )
    assert row_zero != Fraction.from_float(float(eigenvalue)) * exact_binary[0]
