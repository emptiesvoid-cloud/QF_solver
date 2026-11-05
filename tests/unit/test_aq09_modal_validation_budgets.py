"""Algebraic budget-refusal tests; these construct no FE model or assembly."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.sparse import diags, eye

from solveur.core.analyses.modal_basis import ModalBasis
from solveur.core.errors import ModalResidualValidationError


def test_synthetic_sparse_operators_above_term_budget_return_inconclusive_candidate() -> None:
    size = 120
    offsets = [-2, -1, 0, 1, 2]
    stiffness_values = {-2: 0.05, -1: 0.1, 0: 4.0, 1: 0.1, 2: 0.05}
    mass_values = {-2: 0.005, -1: 0.01, 0: 1.0, 1: 0.01, 2: 0.005}
    stiffness = diags(
        [np.full(size - abs(offset), stiffness_values[offset]) for offset in offsets],
        offsets,
        shape=(size, size),
        format="csr",
    )
    mass = diags(
        [np.full(size - abs(offset), mass_values[offset]) for offset in offsets],
        offsets,
        shape=(size, size),
        format="csr",
    )
    combined_terms = int(stiffness.nnz + mass.nnz)
    assert combined_terms == 1_188

    with pytest.raises(ModalResidualValidationError) as caught:
        ModalBasis._from_operators(
            stiffness,
            mass,
            operator_identity="synthetic-sparse-band-term-budget-v1",
            dof_signature=(),
            requested_modes=6,
            method="eigsh",
            dense_limit=64,
        )

    error = caught.value
    assert error.validation_status == "INCONCLUSIVE"
    assert error.diagnostics["reason"] == "aggregate_work_budget"
    candidate = error.computed_result
    assert isinstance(candidate, dict)
    assert candidate["validation"]["status"] == "INCONCLUSIVE"
    assert candidate["validation"]["reason"] == "aggregate_work_budget"
    assert candidate["eigenvalues_rad2_s2"].shape == (7,)
    assert candidate["modes"].shape == (size, 7)


def test_synthetic_sparse_operators_above_dimension_budget_return_inconclusive_candidate() -> None:
    size = 132
    stiffness = diags(np.arange(1.0, size + 1.0), format="csr")
    mass = eye(size, format="csr")

    with pytest.raises(ModalResidualValidationError) as caught:
        ModalBasis._from_operators(
            stiffness,
            mass,
            operator_identity="synthetic-sparse-dimension-budget-v1",
            dof_signature=(),
            requested_modes=6,
            method="eigsh",
            dense_limit=64,
        )

    error = caught.value
    assert error.validation_status == "INCONCLUSIVE"
    assert error.diagnostics["reason"] == "dimension_budget"
    candidate = error.computed_result
    assert isinstance(candidate, dict)
    assert candidate["validation"]["status"] == "INCONCLUSIVE"
    assert candidate["validation"]["reason"] == "dimension_budget"
    assert candidate["eigenvalues_rad2_s2"].shape == (7,)
    assert candidate["modes"].shape == (size, 7)
