"""Bounded algebraic checks for the interval-first AQ09 prototype."""
from __future__ import annotations

import numpy as np
import pytest
from scipy.sparse import csc_matrix, csr_matrix

from experiments.aq09_hybrid_experimental import check_modal_residual_hybrid


def _underflow_counterexample(matrix_type):
    stiffness = np.array([[1.0e-16, 1.0e-17], [1.0e-17, 2.0e-18]])
    mass = np.diag([1.0e-16, 1.0e-18])
    if matrix_type is csr_matrix:
        stiffness, mass = csr_matrix(stiffness), csr_matrix(mass)
    elif matrix_type is csc_matrix:
        stiffness, mass = csc_matrix(stiffness), csc_matrix(mass)
    return stiffness, mass, 1.0, np.array([1.0e-307, 0.0]), 1.0e-7


@pytest.mark.parametrize("matrix_type", [np.ndarray, csr_matrix, csc_matrix])
def test_interval_or_exact_fallback_rejects_partial_underflow_false_pass(matrix_type):
    stiffness, mass, eigenvalue, vector, tolerance = _underflow_counterexample(matrix_type)
    result = check_modal_residual_hybrid(stiffness, mass, eigenvalue, vector, tolerance)
    assert result.status == "FAIL"
    assert result.path == "exact_fallback"


def test_interval_fast_path_accepts_exact_scaled_identity_case():
    stiffness = np.diag(np.array([2.0, 4.0], dtype=np.float64))
    mass = np.diag(np.array([1.0, 2.0], dtype=np.float64))
    vector = np.array([1.0, -3.0], dtype=np.float64)
    result = check_modal_residual_hybrid(stiffness, mass, 2.0, vector, 1.0e-7)
    assert result.status == "PASS_CONDITIONAL"
    assert result.path == "outward_interval"
    assert result.residual_l1_upper is not None
    assert result.reference_linf_lower is not None


def test_fast_path_handles_sparse_duplicate_coordinates_conservatively():
    # Two stored values at (0, 0) represent their exact sum in the sparse matrix.
    stiffness = csr_matrix(
        (np.array([1.0, 1.0], dtype=np.float64),
         np.array([0, 0], dtype=np.int32),
         np.array([0, 2], dtype=np.int32)),
        shape=(1, 1),
    )
    mass = csr_matrix(np.array([[1.0]], dtype=np.float64))
    result = check_modal_residual_hybrid(
        stiffness, mass, 2.0, np.array([1.0], dtype=np.float64), 1.0e-7
    )
    assert result.status == "PASS_CONDITIONAL"
    assert result.terms == 3


def test_unsupported_float32_uses_exact_fallback_without_lossy_promotion():
    stiffness = np.eye(1, dtype=np.float32)
    mass = np.eye(1, dtype=np.float32)
    result = check_modal_residual_hybrid(
        stiffness, mass, np.float32(1.0), np.array([1.0], dtype=np.float32), 1.0e-7
    )
    assert result.status == "PASS_CERTIFIED"
    assert result.path == "exact_fallback"


def test_nonfinite_input_is_inconclusive_not_pass():
    stiffness = np.array([[np.nan]], dtype=np.float64)
    mass = np.eye(1, dtype=np.float64)
    result = check_modal_residual_hybrid(
        stiffness, mass, 1.0, np.array([1.0], dtype=np.float64), 1.0e-7
    )
    assert result.status == "INCONCLUSIVE"
    assert result.path == "exact_fallback"


def test_malformed_sparse_array_dimensions_are_inconclusive():
    stiffness = csr_matrix(np.eye(1, dtype=np.float64))
    stiffness.indices = stiffness.indices.reshape((1, 1))
    mass = csr_matrix(np.eye(1, dtype=np.float64))
    result = check_modal_residual_hybrid(
        stiffness, mass, 1.0, np.ones(1, dtype=np.float64), 1.0e-7
    )
    assert result.status == "INCONCLUSIVE"
    assert result.path == "exact_fallback"


def test_malformed_sparse_data_is_rejected_before_finiteness_scan():
    stiffness = csr_matrix(np.eye(1, dtype=np.float64))
    stiffness.data = stiffness.data.reshape((1, 1))
    mass = csr_matrix(np.eye(1, dtype=np.float64))
    result = check_modal_residual_hybrid(
        stiffness, mass, 1.0, np.ones(1, dtype=np.float64), 1.0e-7
    )
    assert result.status == "INCONCLUSIVE"
    assert result.path == "exact_fallback"


def test_budget_overrun_is_inconclusive_and_never_bypasses_caller_budget():
    stiffness = np.eye(2, dtype=np.float64)
    mass = np.eye(2, dtype=np.float64)
    result = check_modal_residual_hybrid(
        stiffness, mass, 1.0, np.ones(2, dtype=np.float64), 1.0e-7, max_terms=1
    )
    assert result.path == "none"
    assert result.status == "INCONCLUSIVE"
    assert "budget" in result.reason


def test_unsupported_dtype_cannot_bypass_sparse_term_budget():
    stiffness = csr_matrix(np.eye(1, dtype=np.float32))
    mass = csr_matrix(np.eye(1, dtype=np.float32))
    result = check_modal_residual_hybrid(
        stiffness, mass, np.float32(1.0), np.ones(1, dtype=np.float32),
        1.0e-7, max_terms=1,
    )
    assert result.status == "INCONCLUSIVE"
    assert result.reason == "combined_coefficient_budget"


def test_unsupported_dtype_cannot_bypass_caller_dimension_budget():
    stiffness = np.eye(2, dtype=np.float32)
    mass = np.eye(2, dtype=np.float32)
    result = check_modal_residual_hybrid(
        stiffness, mass, np.float32(1.0), np.ones(2, dtype=np.float32),
        1.0e-7, max_dimension=1,
    )
    assert result.status == "INCONCLUSIVE"
    assert result.reason == "dimension_budget"


def test_unsupported_environment_cannot_bypass_caller_term_budget(monkeypatch):
    import experiments.aq09_hybrid_experimental as module

    monkeypatch.setattr(module, "_environment_supported", lambda: False)
    result = module.check_modal_residual_hybrid(
        np.eye(1, dtype=np.float64), np.eye(1, dtype=np.float64), 1.0,
        np.ones(1, dtype=np.float64), 1.0e-7, max_terms=1,
    )
    assert result.status == "INCONCLUSIVE"
    assert result.reason == "combined_coefficient_budget"


def test_environment_change_during_interval_path_uses_exact_fallback(monkeypatch):
    import experiments.aq09_hybrid_experimental as module

    probes = iter((True, True, False))
    monkeypatch.setattr(module, "_environment_supported", lambda: next(probes))
    stiffness = np.diag(np.array([2.0, 4.0], dtype=np.float64))
    mass = np.diag(np.array([1.0, 2.0], dtype=np.float64))
    result = module.check_modal_residual_hybrid(
        stiffness, mass, 2.0, np.array([1.0, -3.0]), 1.0e-7,
    )
    assert result.status == "PASS_CERTIFIED"
    assert result.path == "exact_fallback"


def test_exact_fallback_over_deadline_is_downgraded_to_inconclusive(monkeypatch):
    import time
    import experiments.aq09_hybrid_experimental as module

    exact_check = module.check_modal_residual

    def slow_exact_check(*args, **kwargs):
        time.sleep(0.12)
        return exact_check(*args, **kwargs)

    monkeypatch.setattr(module, "check_modal_residual", slow_exact_check)
    stiffness = np.array([[1.0e-16, 1.0e-17], [1.0e-17, 2.0e-18]], dtype=np.float64)
    mass = np.diag([1.0e-16, 1.0e-18])
    vector = np.array([np.nextafter(0.0, 1.0), 0.0], dtype=np.float64)
    result = module.check_modal_residual_hybrid(
        stiffness, mass, 1.0, vector, 1.0e-7, max_seconds=0.1,
    )
    assert result.status == "INCONCLUSIVE"
    assert result.reason == "time_budget_after_exact_fallback"


def test_zero_reference_is_inconclusive():
    zero = np.zeros((1, 1), dtype=np.float64)
    result = check_modal_residual_hybrid(
        zero, zero.copy(), 1.0, np.ones(1, dtype=np.float64), 1.0e-7
    )
    assert result.status == "INCONCLUSIVE"
    assert result.path == "exact_fallback"
