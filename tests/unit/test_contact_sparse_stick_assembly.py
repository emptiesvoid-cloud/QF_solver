"""Regression tests for sparse, support-local stick stiffness assembly."""

from __future__ import annotations

import numpy as np

from solveur.contact.support import _sparse_rank_one


def test_sparse_rank_one_matches_dense_rank_one_on_small_support() -> None:
    vector = np.zeros(31, dtype=float)
    vector[[1, 4, 11, 30]] = [0.5, -1.25, 2.0, 0.75]
    factor = 2.6667e6

    actual = _sparse_rank_one(vector, factor)
    expected = factor * np.outer(vector, vector)

    np.testing.assert_allclose(actual.toarray(), expected, rtol=0.0, atol=0.0)
    assert actual.format == "csr"
    assert actual.nnz == 16


def test_sparse_rank_one_for_refined_mesh_scales_with_contact_support() -> None:
    vector = np.zeros(4131, dtype=float)
    support = np.array([0, 3, 4, 5, 1200, 1201, 1202, 4100, 4101, 4102, 4129, 4130])
    vector[support] = np.linspace(-1.0, 1.0, len(support))

    actual = _sparse_rank_one(vector, 2.6667e6)

    assert actual.shape == (4131, 4131)
    assert actual.format == "csr"
    assert actual.nnz == len(support) ** 2
    assert actual.nnz < 200
