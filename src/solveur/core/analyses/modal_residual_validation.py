"""Conservative, bounded validation of represented modal eigenpair residuals.

This module performs exact rational arithmetic on the binary values supplied
to it. It is not a bound on eigensolver error, eigenvector error, or continuum
model error. Inputs outside the small, explicit domain return INCONCLUSIVE.
"""
from __future__ import annotations

import math
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from numbers import Integral
from typing import Iterator, cast

import numpy as np
from scipy.sparse import csc_matrix, csr_matrix, isspmatrix_csc, isspmatrix_csr

MAX_DIMENSION = 128
MAX_EIGENPAIRS = 128
MAX_STORED_TERMS = 1_024
MAX_OPERATIONS = 65_536
MAX_INTEGER_BITS = 8_192
MAX_ESTIMATED_MEMORY_BYTES = 2_000_000
BUDGET_INCONCLUSIVE_REASONS = frozenset(
    {
        "dimension_budget",
        "eigenpair_count_budget",
        "aggregate_work_budget",
        "combined_stored_term_budget",
        "estimated_memory_budget",
    }
)


@dataclass(frozen=True)
class ModalResidualCheck:
    status: str
    reason: str
    dimension: int
    coefficients: int
    operation_count: int
    max_integer_bits: int
    residual_ratio_squared: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "reason": self.reason,
            "dimension": self.dimension,
            "coefficients": self.coefficients,
            "operation_count": self.operation_count,
            "max_integer_bits": self.max_integer_bits,
            "residual_ratio_squared": self.residual_ratio_squared,
            "criterion": "||K phi - lambda M phi||_2^2 <= tolerance^2 * max(||K phi||_2^2, ||lambda M phi||_2^2)",
            "arithmetic": "exact rational arithmetic on represented inputs",
        }


@dataclass(frozen=True)
class ModalEigenpairValidation:
    status: str
    reason: str
    checks: tuple[ModalResidualCheck, ...]
    operation_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "reason": self.reason,
            "operation_count": self.operation_count,
            "max_dimension": MAX_DIMENSION,
            "max_eigenpairs": MAX_EIGENPAIRS,
            "max_stored_terms": MAX_STORED_TERMS,
            "max_operations": MAX_OPERATIONS,
            "max_integer_bits": MAX_INTEGER_BITS,
            "max_estimated_memory_bytes": MAX_ESTIMATED_MEMORY_BYTES,
            "exact_fallback": False,
            "checks": [check.to_dict() for check in self.checks],
        }


def is_budget_limited_inconclusive(validation: ModalEigenpairValidation) -> bool:
    """True only when exact certification was withheld by a declared work cap."""
    if validation.status != "INCONCLUSIVE":
        return False
    if validation.reason in BUDGET_INCONCLUSIVE_REASONS:
        return True
    return (
        validation.reason == "one_or_more_residuals_not_certified"
        and bool(validation.checks)
        and all(
            check.status == "INCONCLUSIVE" and check.reason in BUDGET_INCONCLUSIVE_REASONS
            for check in validation.checks
        )
    )


def modal_response_status(validation_status: str) -> str:
    """Map validation state to a result state without promoting uncertainty."""
    if validation_status == "PASS_CERTIFIED":
        return "PASS"
    if validation_status in {"INCONCLUSIVE", "FAIL"}:
        return validation_status
    raise ValueError(f"Unsupported modal validation status {validation_status!r}.")


class _Refuse(Exception):
    pass


def _has_supported_binary64() -> bool:
    info = sys.float_info
    return (
        info.radix == 2
        and info.mant_dig == 53
        and info.min_exp == -1_021
        and info.max_exp == 1_024
        and np.dtype(np.float64).itemsize == 8
        and np.finfo(np.float64).nmant == 52
    )


def modal_diagnostics_are_finite(value: object) -> bool:
    """Return false for non-finite or unsupported values in modal diagnostics."""
    if value is None or isinstance(value, (str, bool, int, np.bool_, np.integer)):
        return True
    if isinstance(value, (float, np.floating)):
        try:
            return math.isfinite(float(value))
        except (OverflowError, TypeError, ValueError):
            return False
    if isinstance(value, np.ndarray):
        if value.dtype.kind in "iu":
            return True
        if value.dtype.kind in "fc":
            return bool(np.all(np.isfinite(value)))
        return modal_diagnostics_are_finite(value.tolist())
    if isinstance(value, Mapping):
        return all(modal_diagnostics_are_finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(modal_diagnostics_are_finite(item) for item in value)
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return modal_diagnostics_are_finite(item())
        except (TypeError, ValueError, OverflowError):
            return False
    return False


def modal_result_components_are_finite(
    diagnostics: object, frequencies: object, expanded_modes: object
) -> bool:
    """Require all result components that would accompany a modal PASS to be finite."""
    return (
        modal_diagnostics_are_finite(diagnostics)
        and modal_diagnostics_are_finite(frequencies)
        and modal_diagnostics_are_finite(expanded_modes)
    )


def _fraction(value: object, *, seen_bits: list[int]) -> Fraction:
    if isinstance(value, (bool, np.bool_)):
        raise _Refuse("boolean_scalar")
    if isinstance(value, Integral):
        result = Fraction(int(value))
    elif isinstance(value, (float, np.floating)):
        if isinstance(value, np.floating) and value.dtype.itemsize > 8:
            raise _Refuse("unsupported_float_precision")
        as_float = float(value)
        if not math.isfinite(as_float):
            raise _Refuse("nonfinite_input")
        result = Fraction.from_float(as_float)
    else:
        raise _Refuse("unsupported_scalar_type")
    bits = max(result.numerator.bit_length(), result.denominator.bit_length())
    seen_bits[0] = max(seen_bits[0], bits)
    if bits > MAX_INTEGER_BITS:
        raise _Refuse("integer_bit_budget")
    return result


def _check_fraction(value: Fraction, *, seen_bits: list[int]) -> Fraction:
    bits = max(value.numerator.bit_length(), value.denominator.bit_length())
    seen_bits[0] = max(seen_bits[0], bits)
    if bits > MAX_INTEGER_BITS:
        raise _Refuse("integer_bit_budget")
    return value


def _matrix_entries(matrix: object, dimension: int) -> tuple[int, Iterator[tuple[int, int, object]]]:
    if isinstance(matrix, np.ndarray):
        if matrix.ndim != 2 or matrix.shape != (dimension, dimension):
            raise _Refuse("matrix_shape")
        if matrix.dtype.kind not in "fiu" or matrix.dtype.itemsize > 8:
            raise _Refuse("unsupported_matrix_dtype")
        count = int(matrix.size)
        if count > MAX_STORED_TERMS:
            raise _Refuse("stored_term_budget")
        if matrix.dtype.kind == "f" and not np.all(np.isfinite(matrix)):
            raise _Refuse("nonfinite_matrix")

        def dense_entries() -> Iterator[tuple[int, int, object]]:
            for row in range(dimension):
                for column in range(dimension):
                    yield row, column, matrix[row, column]

        return count, dense_entries()

    if not (isspmatrix_csr(matrix) or isspmatrix_csc(matrix)):
        raise _Refuse("unsupported_matrix_format")
    sparse_matrix = cast(csr_matrix | csc_matrix, matrix)
    if sparse_matrix.shape != (dimension, dimension):
        raise _Refuse("matrix_shape")
    if sparse_matrix.dtype.kind not in "fiu" or sparse_matrix.dtype.itemsize > 8:
        raise _Refuse("unsupported_matrix_dtype")
    data, indices, indptr = sparse_matrix.data, sparse_matrix.indices, sparse_matrix.indptr
    if data.size > MAX_STORED_TERMS:
        raise _Refuse("stored_term_budget")
    if sparse_matrix.dtype.kind == "f" and not np.all(np.isfinite(data)):
        raise _Refuse("nonfinite_matrix")
    if (indices.dtype.kind not in "iu" or indptr.dtype.kind not in "iu" or
        len(indptr) != dimension + 1 or int(indptr[0]) != 0 or
        int(indptr[-1]) != len(data) or len(indices) != len(data) or
        np.any(indptr[1:] < indptr[:-1]) or np.any(indices < 0) or
        np.any(indices >= dimension)):
        raise _Refuse("invalid_sparse_structure")

    is_csr = isspmatrix_csr(sparse_matrix)

    def sparse_entries() -> Iterator[tuple[int, int, object]]:
        for outer in range(dimension):
            for position in range(int(indptr[outer]), int(indptr[outer + 1])):
                inner = int(indices[position])
                if is_csr:
                    yield outer, inner, data[position]
                else:
                    yield inner, outer, data[position]

    return len(data), sparse_entries()


def _preflight_matrix(matrix: object, dimension: int, label: str) -> tuple[str | None, int]:
    if isinstance(matrix, np.ndarray):
        if matrix.ndim != 2 or matrix.shape != (dimension, dimension):
            return f"{label}_matrix_shape", 0
        if matrix.dtype.kind not in "fiu" or matrix.dtype.itemsize > 8:
            return f"unsupported_{label}_matrix_dtype", 0
        return None, int(matrix.size)
    if not (isspmatrix_csr(matrix) or isspmatrix_csc(matrix)):
        return f"unsupported_{label}_matrix_format", 0
    sparse_matrix = cast(csr_matrix | csc_matrix, matrix)
    if sparse_matrix.shape != (dimension, dimension):
        return f"{label}_matrix_shape", 0
    if sparse_matrix.dtype.kind not in "fiu" or sparse_matrix.dtype.itemsize > 8:
        return f"unsupported_{label}_matrix_dtype", 0
    return None, int(sparse_matrix.data.size)


def _modal_eigenpair_preflight(
    stiffness: object, mass: object, eigenvalues: object, eigenvectors: object
) -> tuple[str | None, int]:
    """Check shape/type/work metadata without scanning numerical values."""
    if not isinstance(eigenvalues, np.ndarray) or not isinstance(eigenvectors, np.ndarray):
        return "unsupported_eigenpair_container", 0
    values: np.ndarray = eigenvalues
    vectors: np.ndarray = eigenvectors
    if values.ndim != 1 or vectors.ndim != 2 or vectors.shape[1] != values.size:
        return "eigenpair_shape", 0
    if (values.dtype.kind not in "fiu" or values.dtype.itemsize > 8 or
        vectors.dtype.kind not in "fiu" or vectors.dtype.itemsize > 8):
        return "unsupported_eigenpair_dtype", 0
    dimension = int(vectors.shape[0])
    if values.size == 0 or dimension == 0:
        return "empty_eigenpairs", 0
    if dimension > MAX_DIMENSION:
        return "dimension_budget", 0
    if values.size > MAX_EIGENPAIRS:
        return "eigenpair_count_budget", 0

    k_reason, k_terms = _preflight_matrix(stiffness, dimension, "stiffness")
    if k_reason is not None:
        return k_reason, 0
    m_reason, m_terms = _preflight_matrix(mass, dimension, "mass")
    if m_reason is not None:
        return m_reason, 0
    total_terms = k_terms + m_terms
    total_operations = values.size * (2 * total_terms + 8 * dimension + 3)
    if total_terms > MAX_STORED_TERMS or total_operations > MAX_OPERATIONS:
        return "aggregate_work_budget", total_operations
    max_integer_decimal_chars = (MAX_INTEGER_BITS * 30_103 + 99_999) // 100_000 + 1
    result_bytes = values.size * (512 + 2 * max_integer_decimal_chars)
    scratch_bytes = 65_536 + 32 * total_terms + 3 * dimension * (MAX_INTEGER_BITS // 4 + 128)
    if result_bytes + scratch_bytes > MAX_ESTIMATED_MEMORY_BYTES:
        return "estimated_memory_budget", total_operations
    return None, total_operations


def check_modal_residual_exact(
    stiffness: object,
    mass: object,
    eigenvalue: object,
    vector: object,
    tolerance: object,
) -> ModalResidualCheck:
    """Compare the exact represented-input residual within fixed work caps.

    No floating-point matvec, interval path, or exact fallback is used. The
    only successful state is PASS_CERTIFIED; unsupported or over-budget input
    is INCONCLUSIVE. FAIL means the represented algebraic residual exceeds the
    stated relative threshold, not that the physical model is invalid.
    """
    dimension = int(vector.size) if isinstance(vector, np.ndarray) and vector.ndim == 1 else 0
    terms = 0
    operations = 0
    seen_bits = [0]

    def result(status: str, reason: str, ratio: Fraction | None = None) -> ModalResidualCheck:
        ratio_text = None if ratio is None else f"{ratio.numerator}/{ratio.denominator}"
        return ModalResidualCheck(status, reason, dimension, terms, operations, seen_bits[0], ratio_text)

    try:
        if not _has_supported_binary64():
            raise _Refuse("unsupported_python_float_format")
        if not isinstance(vector, np.ndarray) or vector.ndim != 1 or dimension == 0:
            raise _Refuse("vector_shape")
        if dimension > MAX_DIMENSION:
            raise _Refuse("dimension_budget")
        if vector.dtype.kind not in "fiu" or vector.dtype.itemsize > 8:
            raise _Refuse("unsupported_vector_dtype")
        if vector.dtype.kind == "f" and not np.all(np.isfinite(vector)):
            raise _Refuse("nonfinite_vector")

        tolerance_q = _fraction(tolerance, seen_bits=seen_bits)
        eigenvalue_q = _fraction(eigenvalue, seen_bits=seen_bits)
        if tolerance_q <= 0:
            raise _Refuse("invalid_tolerance")
        vector_q = [_fraction(value, seen_bits=seen_bits) for value in vector]
        if not any(vector_q):
            raise _Refuse("zero_vector")

        k_count, k_entries = _matrix_entries(stiffness, dimension)
        m_count, m_entries = _matrix_entries(mass, dimension)
        terms = k_count + m_count
        if terms > MAX_STORED_TERMS:
            raise _Refuse("combined_stored_term_budget")
        # Two rational operations per stored term (multiply and accumulate),
        # plus lambda scaling, residual and three squared-norm accumulations.
        operations = 2 * terms + 8 * dimension + 3
        if operations > MAX_OPERATIONS:
            raise _Refuse("operation_budget")
        estimated_memory = 65_536 + 32 * terms + 3 * dimension * (MAX_INTEGER_BITS // 4 + 128)
        if estimated_memory > MAX_ESTIMATED_MEMORY_BYTES:
            raise _Refuse("estimated_memory_budget")

        k_phi = [Fraction(0) for _ in range(dimension)]
        m_phi = [Fraction(0) for _ in range(dimension)]
        for target, entries in ((k_phi, k_entries), (m_phi, m_entries)):
            for row, column, coefficient in entries:
                product = _check_fraction(
                    _fraction(coefficient, seen_bits=seen_bits) * vector_q[column],
                    seen_bits=seen_bits,
                )
                target[row] = _check_fraction(target[row] + product, seen_bits=seen_bits)
        lambda_m_phi = [
            _check_fraction(eigenvalue_q * component, seen_bits=seen_bits)
            for component in m_phi
        ]

        residual_norm_squared = Fraction(0)
        stiffness_norm_squared = Fraction(0)
        mass_term_norm_squared = Fraction(0)
        for k_value, m_value in zip(k_phi, lambda_m_phi):
            residual = _check_fraction(k_value - m_value, seen_bits=seen_bits)
            residual_norm_squared = _check_fraction(
                residual_norm_squared + _check_fraction(residual * residual, seen_bits=seen_bits),
                seen_bits=seen_bits,
            )
            stiffness_norm_squared = _check_fraction(
                stiffness_norm_squared + _check_fraction(k_value * k_value, seen_bits=seen_bits),
                seen_bits=seen_bits,
            )
            mass_term_norm_squared = _check_fraction(
                mass_term_norm_squared + _check_fraction(m_value * m_value, seen_bits=seen_bits),
                seen_bits=seen_bits,
            )
        reference_norm_squared = max(stiffness_norm_squared, mass_term_norm_squared)
        if reference_norm_squared == 0:
            raise _Refuse("zero_reference")
        limit = _check_fraction(
            _check_fraction(tolerance_q * tolerance_q, seen_bits=seen_bits) * reference_norm_squared,
            seen_bits=seen_bits,
        )
        ratio_squared = _check_fraction(
            residual_norm_squared / reference_norm_squared,
            seen_bits=seen_bits,
        )
        if residual_norm_squared <= limit:
            return result("PASS_CERTIFIED", "exact_represented_input_comparison", ratio_squared)
        return result("FAIL", "exact_represented_input_residual_exceeds_tolerance", ratio_squared)
    except (_Refuse, ArithmeticError, TypeError, ValueError, IndexError, AttributeError, MemoryError) as exc:
        return result("INCONCLUSIVE", str(exc) or type(exc).__name__)


def validate_modal_eigenpairs(
    stiffness: object,
    mass: object,
    eigenvalues: object,
    eigenvectors: object,
    tolerance: object,
    *,
    legacy_residuals: object | None = None,
) -> ModalEigenpairValidation:
    """Validate columns with the exact checker and aggregate fail-closed."""
    # Do not coerce arbitrary sequences here: np.asarray can allocate a copy
    # proportional to caller-controlled input before the work caps are checked.
    preflight_reason, total_operations = _modal_eigenpair_preflight(
        stiffness, mass, eigenvalues, eigenvectors
    )
    if preflight_reason is not None:
        return ModalEigenpairValidation(
            "INCONCLUSIVE", preflight_reason, (), total_operations
        )
    if not isinstance(eigenvalues, np.ndarray) or not isinstance(eigenvectors, np.ndarray):
        return ModalEigenpairValidation("INCONCLUSIVE", "unsupported_eigenpair_container", ())
    values: np.ndarray = eigenvalues
    vectors: np.ndarray = eigenvectors
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(vectors)):
        return ModalEigenpairValidation(
            "INCONCLUSIVE", "nonfinite_or_empty_eigenpairs", (), total_operations
        )
    checks = tuple(
        check_modal_residual_exact(stiffness, mass, value, vectors[:, index], tolerance)
        for index, value in enumerate(values)
    )
    if legacy_residuals is not None:
        if isinstance(legacy_residuals, np.ndarray):
            if legacy_residuals.size > MAX_EIGENPAIRS or legacy_residuals.shape != values.shape:
                return ModalEigenpairValidation(
                    "INCONCLUSIVE", "invalid_legacy_diagnostic_shape", checks, total_operations
                )
            if legacy_residuals.dtype.kind not in "fiu" or legacy_residuals.dtype.itemsize > 8:
                return ModalEigenpairValidation(
                    "INCONCLUSIVE", "invalid_legacy_diagnostic_type", checks, total_operations
                )
            legacy = legacy_residuals
        elif isinstance(legacy_residuals, (list, tuple)):
            if len(legacy_residuals) != values.size or len(legacy_residuals) > MAX_EIGENPAIRS:
                return ModalEigenpairValidation(
                    "INCONCLUSIVE", "invalid_legacy_diagnostic_shape", checks, total_operations
                )
            if any(
                isinstance(item, (bool, np.bool_))
                or not isinstance(item, (int, float, np.integer, np.floating))
                for item in legacy_residuals
            ):
                return ModalEigenpairValidation(
                    "INCONCLUSIVE", "invalid_legacy_diagnostic_type", checks, total_operations
                )
            try:
                legacy = np.asarray(legacy_residuals, dtype=np.float64)
            except (TypeError, ValueError, OverflowError):
                return ModalEigenpairValidation(
                    "INCONCLUSIVE", "invalid_legacy_diagnostic", checks, total_operations
                )
        else:
            return ModalEigenpairValidation(
                "INCONCLUSIVE", "invalid_legacy_diagnostic_container", checks, total_operations
            )
        if not np.all(np.isfinite(legacy)):
            return ModalEigenpairValidation(
                "INCONCLUSIVE", "nonfinite_legacy_diagnostic", checks, total_operations
            )
    if any(check.status == "FAIL" for check in checks):
        return ModalEigenpairValidation(
            "FAIL", "one_or_more_represented_residuals_fail", checks, total_operations
        )
    if any(check.status != "PASS_CERTIFIED" for check in checks):
        return ModalEigenpairValidation(
            "INCONCLUSIVE", "one_or_more_residuals_not_certified", checks, total_operations
        )
    return ModalEigenpairValidation(
        "PASS_CERTIFIED", "all_represented_residuals_certified", checks, total_operations
    )
