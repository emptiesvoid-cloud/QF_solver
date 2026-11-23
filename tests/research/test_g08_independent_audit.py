"""Independent exact-arithmetic checks for the G08 inertia proof inputs."""

from __future__ import annotations

from fractions import Fraction
import math
from typing import Any

import numpy as np
import pytest

from research.g08_compare.verified_inertia import (
    VerifiedInertiaInputError,
    certify_pencil_inertia,
    certify_symmetric_inertia,
    residual_enclosure,
)


def exact_binary64_inertia(matrix: Any) -> tuple[int, int, int]:
    """Compute inertia by exact rational 1x1/2x2 congruence elimination."""
    try:
        rows = [list(row) for row in matrix]
    except TypeError as exc:
        raise ValueError("matrix must be a square array") from exc
    dimension = len(rows)
    if dimension == 0 or any(len(row) != dimension for row in rows):
        raise ValueError("matrix must be a nonempty square array")

    exact = []
    for row in rows:
        exact_row = []
        for item in row:
            if isinstance(item, (complex, np.complexfloating)):
                raise ValueError("matrix must be real")
            value = float(item)
            if not math.isfinite(value):
                raise ValueError("matrix must be finite")
            exact_row.append(Fraction.from_float(value))
        exact.append(exact_row)
    if any(exact[i][j] != exact[j][i] for i in range(dimension) for j in range(dimension)):
        raise ValueError("matrix must be symmetric")

    positive = negative = zero = 0

    def swap_symmetric(index: int, target: int) -> None:
        if index == target:
            return
        exact[index], exact[target] = exact[target], exact[index]
        for row in exact:
            row[index], row[target] = row[target], row[index]

    while exact:
        size = len(exact)
        diagonal_index = next((i for i in range(size) if exact[i][i]), None)
        if diagonal_index is not None:
            swap_symmetric(diagonal_index, 0)
            pivot = exact[0][0]
            if pivot > 0:
                positive += 1
            else:
                negative += 1
            exact = [
                [exact[i][j] - exact[i][0] * exact[0][j] / pivot for j in range(1, size)]
                for i in range(1, size)
            ]
            continue

        off_diagonal = next(
            ((i, j) for i in range(size) for j in range(i + 1, size) if exact[i][j]),
            None,
        )
        if off_diagonal is None:
            zero += size
            break

        first, second = off_diagonal
        swap_symmetric(first, 0)
        swap_symmetric(second, 1)
        pivot = exact[0][1]
        positive += 1
        negative += 1
        exact = [
            [
                exact[i][j]
                - (exact[i][0] * exact[1][j] + exact[i][1] * exact[0][j]) / pivot
                for j in range(2, size)
            ]
            for i in range(2, size)
        ]

    return negative, zero, positive


def test_exact_fraction_method_on_positive_indefinite_singular_and_tiny_cases() -> None:
    cases = [
        (np.diag([1.0, 1.0, 2.0]), (0, 0, 3)),
        (np.array([[0.0, 1.0], [1.0, 0.0]]), (1, 0, 1)),
        (np.diag([2.0, 0.0, 0.0]), (0, 2, 1)),
        (
            np.diag([math.ldexp(1.0, -1074), -math.ldexp(1.0, -1022)]),
            (1, 0, 1),
        ),
    ]
    for matrix, expected in cases:
        assert exact_binary64_inertia(matrix) == expected


def test_exact_fraction_method_is_invariant_under_rational_congruence() -> None:
    transform = [
        [1, 1, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 1, 1],
        [0, 0, 0, 1],
    ]
    diagonal = [-2, 0, 3, 4]
    matrix = [
        [sum(transform[k][i] * diagonal[k] * transform[k][j] for k in range(4)) for j in range(4)]
        for i in range(4)
    ]

    assert exact_binary64_inertia(matrix) == (1, 1, 2)


def test_exact_fraction_counts_match_arb_on_synthetic_nonsingular_matrices() -> None:
    pytest.importorskip("flint")
    cases = [
        (np.diag([-3.0, 1.0, 2.0]), (1, 0, 2)),
        (np.array([[0.0, 1.0], [1.0, 0.0]]), (1, 0, 1)),
        (np.array([[1.0, 1.0], [1.0, 1.0 + 2.0**-52]]), (0, 0, 2)),
    ]
    for matrix, expected in cases:
        exact = exact_binary64_inertia(matrix)
        certified = certify_symmetric_inertia(matrix)
        assert exact == expected
        assert certified["status"] == "CERTIFIED"
        assert certified["inertia"] == {"negative": expected[0], "zero": expected[1], "positive": expected[2]}


def test_complex_and_lossy_integer_inputs_are_rejected() -> None:
    for matrix in (np.array([[1.0 + 2.0j]]), np.array([[1.0 + 2.0j]], dtype=object)):
        with pytest.raises(VerifiedInertiaInputError, match="complex input"):
            certify_symmetric_inertia(matrix)

    too_large = np.asarray([[2**53 + 1]], dtype=np.int64)
    with pytest.raises(VerifiedInertiaInputError, match="integer precision"):
        certify_symmetric_inertia(too_large)

    with pytest.raises(VerifiedInertiaInputError, match="complex input"):
        certify_pencil_inertia(np.eye(1), np.asarray([[1.0 + 1.0j]]), 0.5)
    with pytest.raises(VerifiedInertiaInputError, match="complex input"):
        residual_enclosure(np.eye(1), np.eye(1), 0.5, np.asarray([1.0 + 1.0j]), np.asarray([0]))


def test_exact_method_rejects_nonsymmetric_complex_and_nonfinite_input() -> None:
    with pytest.raises(ValueError, match="symmetric"):
        exact_binary64_inertia([[1.0, 1.0], [0.0, 1.0]])
    with pytest.raises(ValueError, match="real"):
        exact_binary64_inertia([[1.0 + 1.0j]])
    with pytest.raises(ValueError, match="finite"):
        exact_binary64_inertia([[math.inf]])
