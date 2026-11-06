"""Behavioral tests for safe serialization of solver errors and candidates."""

from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

from solveur.core.errors import ModalResidualValidationError, QualificationGateError
from solveur.core.nonlinear.contracts import NonlinearFailureReason


class _ItemBackedScalar:
    """Exercise adapters that expose a scalar through the NumPy item protocol."""

    @staticmethod
    def item() -> np.float64:
        return np.float64(2.5)


class _ScalarConversionFailure:
    """A dtype-bearing extension scalar whose Python conversion can fail."""

    def __init__(self, dtype: str) -> None:
        self.dtype = np.dtype(dtype)
        self.shape: tuple[()] = ()

    def __float__(self) -> float:
        raise OverflowError("scalar is outside the Python float range")

    def __complex__(self) -> complex:
        raise ValueError("scalar cannot be converted to Python complex")

    def __int__(self) -> int:
        raise TypeError("scalar cannot be converted to Python int")


class _LargeArrayWithoutBuffer:
    """Array metadata without a buffer must produce an omission record safely."""

    dtype = np.dtype("float64")
    shape = (5_000,)
    size = 5_000
    nbytes = 5_000 * 8
    flags = SimpleNamespace(c_contiguous=True)

    @staticmethod
    def tolist() -> list[float]:
        raise AssertionError("large diagnostics arrays must not materialize as Python lists")


def test_modal_validation_error_rejects_nonfailure_validation_status() -> None:
    with pytest.raises(ValueError, match="require FAIL or INCONCLUSIVE"):
        ModalResidualValidationError(
            "cannot certify candidate",
            validation_status="PASS_CERTIFIED",
            diagnostics={},
        )


def test_qualification_gate_error_retains_rejected_result_and_summary() -> None:
    result = object()
    summary = {"status": "FAIL", "reason": "required evidence missing"}

    error = QualificationGateError("qualification gate rejected the run", result=result, summary=summary)

    assert error.result is result
    assert error.summary == summary
    assert error.summary is not summary


def test_error_payload_serializes_enums_complex_and_numpy_scalars_as_json() -> None:
    candidate = {
        "float": np.float64(1.25),
        "complex": np.complex128(2.0 - 3.5j),
        "integer": np.int64(-7),
        "unsigned": np.uint64(9),
        "boolean": np.bool_(True),
        "timestamp": np.datetime64("2026-11-06", "D"),
        "item_scalar": _ItemBackedScalar(),
        "unsupported": object(),
    }
    error = ModalResidualValidationError(
        "modal validation remains inconclusive",
        validation_status="INCONCLUSIVE",
        diagnostics={
            "reason": NonlinearFailureReason.MAX_ITERATIONS,
            "complex_diagnostic": complex(1.5, -2.25),
            "complex_nonfinite": complex(0.0, float("inf")),
        },
        computed_result=candidate,
    )

    serialized = error.to_dict()
    json.dumps(serialized, allow_nan=False)

    assert error.computed_result is candidate
    assert serialized["diagnostics"]["reason"] == NonlinearFailureReason.MAX_ITERATIONS.value
    assert serialized["modal_validation_status"] == "INCONCLUSIVE"
    assert serialized["diagnostics"]["complex_diagnostic"] == {"real": 1.5, "imag": -2.25}
    assert serialized["diagnostics"]["complex_nonfinite"] == {
        "real": 0.0,
        "imag": {"nonfinite": "+Infinity"},
    }
    assert serialized["computed_result"] == {
        "float": 1.25,
        "complex": {"real": 2.0, "imag": -3.5},
        "integer": -7,
        "unsigned": 9,
        "boolean": True,
        "timestamp": {"unsupported_type": "date"},
        "item_scalar": 2.5,
        "unsupported": {"unsupported_type": "object"},
    }


def test_error_serialization_survives_scalar_conversion_failures() -> None:
    error = ModalResidualValidationError(
        "modal residual validation failed",
        validation_status="FAIL",
        diagnostics={
            "float": _ScalarConversionFailure("float64"),
            "complex": _ScalarConversionFailure("complex128"),
            "integer": _ScalarConversionFailure("int64"),
        },
    )

    serialized = error.to_dict()
    json.dumps(serialized, allow_nan=False)

    assert serialized["diagnostics"] == {
        "float": {"nonfinite": "out-of-range-floating-value"},
        "complex": {"nonfinite": "out-of-range-complex-value"},
        "integer": {"unsupported_scalar": "int64"},
    }


def test_error_serialization_omits_large_array_when_buffer_is_unavailable() -> None:
    error = ModalResidualValidationError(
        "modal residual validation is outside the supported domain",
        validation_status="INCONCLUSIVE",
        diagnostics={},
        computed_result={"modes": _LargeArrayWithoutBuffer()},
    )

    serialized = error.to_dict()

    assert serialized["computed_result"]["modes"] == {
        "values_omitted": "array exceeds bounded error serialization size",
        "shape": [5_000],
        "dtype": "float64",
        "sha256": None,
        "hash_omitted_reason": "non-contiguous or unsupported buffer layout",
        "full_values_available_on_exception": True,
    }
