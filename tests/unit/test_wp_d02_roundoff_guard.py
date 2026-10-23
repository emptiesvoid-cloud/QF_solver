"""Pure arithmetic checks for cancellation-aware stress accumulation."""

from __future__ import annotations

import numpy as np

from solveur.post.dynamic_stress import _decimal_matvec, _matvec_roundoff_limited


def test_roundoff_guard_recovers_cancelled_dot_product_without_bias() -> None:
    matrix = np.asarray([[1.0e16, 1.0, -1.0e16], [0.0, 0.0, 0.0]])
    vector = np.ones(3)
    ordinary = matrix @ vector

    assert ordinary[0] == 0.0
    assert _matvec_roundoff_limited(matrix, vector, ordinary)
    assert _decimal_matvec(matrix, vector).tolist() == [1.0, 0.0]


def test_roundoff_guard_leaves_well_conditioned_dot_product_alone() -> None:
    matrix = np.asarray([[2.0, -3.0, 4.0]])
    vector = np.asarray([5.0, 7.0, 11.0])
    result = matrix @ vector

    assert result.tolist() == [33.0]
    assert not _matvec_roundoff_limited(matrix, vector, result)


def test_decimal_matvec_preserves_complex_real_and_imaginary_parts() -> None:
    matrix = np.asarray([[1.0, 2.0]])
    vector = np.asarray([1.0 + 1.0j, 3.0 - 2.0j])

    assert _decimal_matvec(matrix, vector).tolist() == [(7.0 - 3.0j)]


def test_roundoff_guard_detects_cancellation_in_complex_components() -> None:
    matrix = np.asarray([[1.0e16, 1.0, -1.0e16]])
    vector = np.ones(3, dtype=np.complex128) * (1.0 + 1.0j)
    ordinary = matrix @ vector

    assert ordinary.tolist() == [0.0 + 0.0j]
    assert _matvec_roundoff_limited(matrix, vector, ordinary)
    assert _decimal_matvec(matrix, vector).tolist() == [1.0 + 1.0j]


def test_roundoff_guard_detects_strain_accumulation_error() -> None:
    b_row = np.asarray([[1.0e16, 1.0, -1.0e16]])
    relative_displacement = np.ones(3)
    ordinary_strain = b_row @ relative_displacement

    assert ordinary_strain.tolist() == [0.0]
    assert _matvec_roundoff_limited(b_row, relative_displacement, ordinary_strain)
    assert _decimal_matvec(b_row, relative_displacement).tolist() == [1.0]
