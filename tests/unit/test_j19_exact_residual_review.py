from __future__ import annotations

import json
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from research.j17.exact_residual import evaluate_exact_residual
from research.j19.checkpoint import write_atomic_json
from solveur.core.solvers.linear import _sparse_matvec_roundoff_bound


def _decimal_complex(value: complex | np.complexfloating) -> tuple[Decimal, Decimal]:
    scalar = complex(value)
    return Decimal.from_float(scalar.real), Decimal.from_float(scalar.imag)


def _decimal_oracle_status(matrix: object, rhs: np.ndarray, solution: np.ndarray, tolerance: float) -> str:
    """Independent high-precision Decimal oracle for tiny controlled systems."""
    with localcontext() as context:
        context.prec = 2600
        product: list[tuple[Decimal, Decimal]] = []
        for row in range(matrix.shape[0]):
            row_real = Decimal(0)
            row_imag = Decimal(0)
            if hasattr(matrix, "indptr"):
                positions = range(int(matrix.indptr[row]), int(matrix.indptr[row + 1]))
                entries = ((int(matrix.indices[pos]), matrix.data[pos]) for pos in positions)
            else:
                entries = ((column, matrix[row, column]) for column in range(matrix.shape[1]))
            for column, coefficient in entries:
                a_real, a_imag = _decimal_complex(coefficient)
                x_real, x_imag = _decimal_complex(solution[column])
                row_real += a_real * x_real - a_imag * x_imag
                row_imag += a_real * x_imag + a_imag * x_real
            product.append((row_real, row_imag))

        residual_squared = Decimal(0)
        rhs_squared = Decimal(0)
        product_squared = Decimal(0)
        for (p_real, p_imag), b_value in zip(product, rhs, strict=True):
            b_real, b_imag = _decimal_complex(b_value)
            r_real, r_imag = p_real - b_real, p_imag - b_imag
            residual_squared += r_real * r_real + r_imag * r_imag
            rhs_squared += b_real * b_real + b_imag * b_imag
            product_squared += p_real * p_real + p_imag * p_imag
        reference_squared = max(rhs_squared, product_squared)
        if reference_squared == 0:
            return "PASS" if residual_squared == 0 else "FAIL"
        threshold = Decimal.from_float(float(tolerance))
        return "PASS" if residual_squared <= threshold * threshold * reference_squared else "FAIL"


def test_j19_exact_result_matches_decimal_oracle_at_zero_tiny_and_threshold_scales() -> None:
    tolerance = 1.0e-7
    threshold_neighbor = 1.0 - tolerance
    b_pass = np.nextafter(threshold_neighbor, 1.0)
    b_fail = np.nextafter(threshold_neighbor, 0.0)
    smallest = np.nextafter(0.0, 1.0)

    exact_matrix = np.array([[1.25 + 0.5j]], dtype=np.complex128)
    exact_solution = np.array([0.75 - 0.25j], dtype=np.complex128)
    exact_rhs = np.array([1.0625 + 0.0625j], dtype=np.complex128)
    threshold_matrix = np.array([[1.0 + 0j]], dtype=np.complex128)
    threshold_solution = np.array([1.0 + 0j], dtype=np.complex128)
    tiny_matrix = np.array([[4.0 * smallest + 0j]], dtype=np.complex128)
    tiny_rhs = np.array([3.0 * smallest + 0j], dtype=np.complex128)

    duplicate_matrix = csr_matrix(
        (
            np.array([1.0 + 2.0j, -1.0 - 2.0j, 0.5 - 0.25j, 0j], dtype=np.complex128),
            np.array([0, 0, 0, 0], dtype=np.int32),
            np.array([0, 4], dtype=np.int32),
        ),
        shape=(1, 1),
    )
    duplicate_solution = np.array([1.0 + 0.5j], dtype=np.complex128)
    duplicate_rhs = np.array([0.625 + 0j], dtype=np.complex128)
    zero_matrix = np.zeros((1, 1), dtype=np.complex128)
    zero_vector = np.zeros(1, dtype=np.complex128)

    cases = [
        ("exact", exact_matrix, exact_rhs, exact_solution, "PASS"),
        ("just_below_threshold", threshold_matrix, np.array([b_pass + 0j]), threshold_solution, "PASS"),
        ("just_above_threshold", threshold_matrix, np.array([b_fail + 0j]), threshold_solution, "FAIL"),
        ("small_nonzero_denominator", tiny_matrix, tiny_rhs, np.array([1.0 + 0j]), "FAIL"),
        ("duplicate_cancelled_csr", duplicate_matrix, duplicate_rhs, duplicate_solution, "PASS"),
        ("zero_over_zero_convention", zero_matrix, zero_vector, zero_vector, "PASS"),
    ]
    for label, matrix, rhs, solution, expected in cases:
        oracle = _decimal_oracle_status(matrix, rhs, solution, tolerance)
        evaluated = evaluate_exact_residual(matrix, rhs, solution, tolerance=tolerance)
        assert oracle == expected, label
        assert evaluated.status == oracle, (label, evaluated.reason)

    duplicate = evaluate_exact_residual(
        duplicate_matrix, duplicate_rhs, duplicate_solution, tolerance=tolerance
    )
    assert duplicate.stored_entries == 4
    assert duplicate.nonzero_entries == 3  # Raw nonzero stored terms; duplicate cancellation is not coalesced in metadata.


def test_j19_malformed_csr_index_dtypes_and_unsigned_pointer_overflow_are_inconclusive() -> None:
    for field, malformed in (
        ("indices", np.array([0.75], dtype=np.float64)),
        ("indices", np.array([0.0 + 0.0j], dtype=np.complex128)),
        ("indptr", np.array([0.0, 1.0], dtype=np.float64)),
    ):
        matrix = csr_matrix(([1.0 + 0j], ([0], [0])), shape=(1, 1), dtype=np.complex128)
        setattr(matrix, field, malformed)
        result = evaluate_exact_residual(matrix, np.ones(1, dtype=np.complex128), np.ones(1, dtype=np.complex128))
        assert result.status == "INCONCLUSIVE"
        assert "integer" in result.reason

    matrix = csr_matrix(
        (np.ones(2, dtype=np.complex128), np.array([0, 1], dtype=np.int64), np.array([0, 1, 2])),
        shape=(2, 2),
    )
    matrix.indptr = np.array([0, np.iinfo(np.uint64).max, 2], dtype=np.uint64)
    result = evaluate_exact_residual(matrix, np.ones(2, dtype=np.complex128), np.ones(2, dtype=np.complex128))
    assert result.status == "INCONCLUSIVE"
    assert "malformed" in result.reason


def _fraction_complex(value: complex | np.complexfloating) -> tuple[Fraction, Fraction]:
    scalar = complex(value)
    return Fraction.from_float(scalar.real), Fraction.from_float(scalar.imag)


def test_j19_complex_csr_row_bound_covers_deterministic_exact_oracle_cases() -> None:
    rng = np.random.default_rng(190719)
    dimension = 32
    exponent_choices = np.array([-600, -500, -53, 0, 450, 500], dtype=int)

    def signed_power(exponent: int) -> float:
        return float(np.ldexp(float(rng.choice([-1.0, 1.0])), int(exponent)))

    solution = np.array(
        [complex(signed_power(int(rng.choice(exponent_choices))), signed_power(int(rng.choice(exponent_choices))))
         for _ in range(dimension)],
        dtype=np.complex128,
    )
    data: list[complex] = []
    indices: list[int] = []
    indptr = [0]
    for row in range(dimension):
        count = 1 + (row % 8)
        for _ in range(count):
            exponent = int(rng.choice(exponent_choices))
            real = signed_power(exponent)
            imag = signed_power(exponent)
            data.append(complex(real, imag))
            # Repeated and unsorted columns deliberately exercise raw CSR terms.
            indices.append(int(rng.integers(0, dimension)))
        indptr.append(len(data))
    matrix = csr_matrix(
        (np.asarray(data, dtype=np.complex128), np.asarray(indices, dtype=np.int32), np.asarray(indptr, dtype=np.int32)),
        shape=(dimension, dimension),
    )
    rhs = np.array(
        [complex(signed_power(int(rng.choice(exponent_choices))), signed_power(int(rng.choice(exponent_choices))))
         for _ in range(dimension)],
        dtype=np.complex128,
    )
    product = matrix @ solution
    rounded_residual = product - rhs
    bounds = _sparse_matvec_roundoff_bound(matrix, rhs, solution, product)
    assert np.all(np.isfinite(product))
    assert np.all(np.isfinite(rounded_residual))
    assert np.all(np.isfinite(bounds))

    for row in range(dimension):
        exact_product_real = Fraction(0)
        exact_product_imag = Fraction(0)
        for position in range(int(matrix.indptr[row]), int(matrix.indptr[row + 1])):
            coefficient_real, coefficient_imag = _fraction_complex(matrix.data[position])
            solution_real, solution_imag = _fraction_complex(solution[int(matrix.indices[position])])
            exact_product_real += coefficient_real * solution_real - coefficient_imag * solution_imag
            exact_product_imag += coefficient_real * solution_imag + coefficient_imag * solution_real
        rhs_real, rhs_imag = _fraction_complex(rhs[row])
        exact_residual_real = exact_product_real - rhs_real
        exact_residual_imag = exact_product_imag - rhs_imag
        rounded_real, rounded_imag = _fraction_complex(rounded_residual[row])
        error_real = rounded_real - exact_residual_real
        error_imag = rounded_imag - exact_residual_imag
        bound_fraction = Fraction.from_float(float(bounds[row]))
        assert error_real * error_real + error_imag * error_imag <= bound_fraction * bound_fraction, row


def test_j19_zero_time_budget_returns_inconclusive_before_exact_work() -> None:
    result = evaluate_exact_residual(
        np.eye(1, dtype=np.complex128),
        np.ones(1, dtype=np.complex128),
        np.ones(1, dtype=np.complex128),
        max_elapsed_seconds=0.0,
    )
    assert result.status == "INCONCLUSIVE"
    assert "time budget" in result.reason


def test_j19_ragged_rhs_or_solution_is_reported_inconclusive() -> None:
    matrix = np.eye(2, dtype=np.complex128)
    result = evaluate_exact_residual(
        matrix,
        rhs=[[1.0], [1.0, 2.0]],
        solution=np.ones(2, dtype=np.complex128),
    )
    assert result.status == "INCONCLUSIVE"
    assert "rectangular numeric arrays" in result.reason


def test_j19_atomic_checkpoint_keeps_previous_results_if_replacement_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    checkpoint = tmp_path / "replay.json"
    previous = {"results": [{"frequency_hz": 2.3, "state": "COMPLETE"}]}
    write_atomic_json(checkpoint, previous)

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError("simulated interrupted atomic replace")

    monkeypatch.setattr("research.j19.checkpoint.os.replace", fail_replace)
    with pytest.raises(OSError, match="simulated interrupted"):
        write_atomic_json(checkpoint, {"results": [*previous["results"], {"frequency_hz": 2.4}]})

    assert json.loads(checkpoint.read_text(encoding="utf-8")) == previous
    assert list(tmp_path.glob("*.tmp")) == []
