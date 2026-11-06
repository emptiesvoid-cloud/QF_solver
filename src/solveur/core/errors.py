"""Stable solver error categories and process exit codes."""

from __future__ import annotations

import hashlib
import math
from enum import Enum, IntEnum
from typing import Any, cast

from solveur.core.nonlinear.contracts import NonlinearFailureReason


class ExitCode(IntEnum):
    """Public process exit codes used by the CLI."""

    ACCEPTED = 0
    INPUT_OR_MESH = 2
    NUMERICAL_FAILURE = 3
    QUALIFICATION_REJECTED = 4
    INFRASTRUCTURE_FAILURE = 5


class SolverError(Exception):
    """Base marker for errors with a stable CLI category."""

    exit_code = ExitCode.NUMERICAL_FAILURE


class InputValidationError(ValueError, SolverError):
    """Input file or schema validation failed."""

    exit_code = ExitCode.INPUT_OR_MESH


class MeshValidationError(ValueError, SolverError):
    """Mesh, connectivity or boundary-condition validation failed."""

    exit_code = ExitCode.INPUT_OR_MESH


class NumericalConvergenceError(RuntimeError, SolverError):
    """A numerical method failed, diverged or produced an invalid state."""

    exit_code = ExitCode.NUMERICAL_FAILURE

    def __init__(
        self,
        message: str,
        *,
        reason: NonlinearFailureReason | None = None,
        diagnostics: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.diagnostics = dict(diagnostics or {})

    def to_dict(self) -> dict[str, Any]:
        """Return a stable non-converged record for API and evidence writers."""
        reason = self.reason.value if isinstance(self.reason, NonlinearFailureReason) else self.reason
        return {
            "converged": False,
            "reason": reason,
            "message": str(self),
            "diagnostics": dict(self.diagnostics),
        }


class ModalResidualValidationError(NumericalConvergenceError):
    """Modal validation refused a computed result without discarding it."""

    def __init__(
        self,
        message: str,
        *,
        validation_status: str,
        diagnostics: dict[str, Any],
        computed_result: object | None = None,
    ) -> None:
        if validation_status not in {"FAIL", "INCONCLUSIVE"}:
            raise ValueError("Modal residual validation errors require FAIL or INCONCLUSIVE.")
        super().__init__(message, diagnostics=diagnostics)
        self.validation_status = validation_status
        self.computed_result = computed_result

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["diagnostics"] = _serialize_computed_modal_data(payload["diagnostics"])
        payload["modal_validation_status"] = self.validation_status
        if self.computed_result is not None:
            payload["computed_result"] = _serialize_computed_modal_data(self.computed_result)
        return payload


def _serialize_computed_modal_data(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _serialize_computed_modal_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_computed_modal_data(item) for item in value]
    if isinstance(value, Enum):
        return _serialize_computed_modal_data(value.value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, complex):
        return {
            "real": _serialize_computed_modal_data(float(value.real)),
            "imag": _serialize_computed_modal_data(float(value.imag)),
        }
    if isinstance(value, float):
        if math.isnan(value):
            return {"nonfinite": "NaN"}
        if math.isinf(value) and value > 0:
            return {"nonfinite": "+Infinity"}
        if math.isinf(value):
            return {"nonfinite": "-Infinity"}
        return value
    dtype = getattr(value, "dtype", None)
    if getattr(value, "shape", None) == () and dtype is not None:
        kind = getattr(dtype, "kind", None)
        if kind == "f":
            try:
                return _serialize_computed_modal_data(float(cast(Any, value)))
            except (OverflowError, TypeError, ValueError):
                return {"nonfinite": "out-of-range-floating-value"}
        if kind == "c":
            try:
                return _serialize_computed_modal_data(complex(cast(Any, value)))
            except (OverflowError, TypeError, ValueError):
                return {"nonfinite": "out-of-range-complex-value"}
        if kind in {"i", "u"}:
            try:
                return int(cast(Any, value))
            except (OverflowError, TypeError, ValueError):
                return {"unsupported_scalar": str(dtype)}
        if kind == "b":
            return bool(value)
    to_list = getattr(value, "tolist", None)
    shape = getattr(value, "shape", None)
    size = getattr(value, "size", None)
    if callable(to_list) and shape is not None and size is not None:
        if int(size) <= 4_096:
            return _serialize_computed_modal_data(to_list())
        flags = getattr(value, "flags", None)
        byte_size = int(getattr(value, "nbytes", 0))
        if (byte_size <= 8_388_608 and flags is not None and
            bool(getattr(flags, "c_contiguous", False))):
            try:
                view = memoryview(cast(Any, value)).cast("B")
            except (TypeError, ValueError):
                view = None
        else:
            view = None
        if view is not None:
            digest = hashlib.sha256()
            digest.update(view)
            return {
                "values_omitted": "array exceeds bounded error serialization size",
                "shape": [int(item) for item in shape],
                "dtype": str(getattr(value, "dtype", "unknown")),
                "sha256": digest.hexdigest(),
                "full_values_available_on_exception": True,
            }
        return {
            "values_omitted": "array exceeds bounded error serialization size",
            "shape": [int(item) for item in shape],
            "dtype": str(getattr(value, "dtype", "unknown")),
            "sha256": None,
            "hash_omitted_reason": (
                "array exceeds bounded hash byte budget"
                if byte_size > 8_388_608 else
                "non-contiguous or unsupported buffer layout"
            ),
            "full_values_available_on_exception": True,
        }
    item = getattr(value, "item", None)
    if callable(item):
        return _serialize_computed_modal_data(item())
    return {"unsupported_type": type(value).__name__}


class QualificationGateError(RuntimeError, SolverError):
    """A numerically completed run was rejected by its verification profile."""

    exit_code = ExitCode.QUALIFICATION_REJECTED

    def __init__(self, message: str, *, result: object | None = None, summary: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.result = result
        self.summary = dict(summary or {})


class InfrastructureError(ImportError, SolverError):
    """A required runtime, dependency or external backend is unavailable."""

    exit_code = ExitCode.INFRASTRUCTURE_FAILURE
