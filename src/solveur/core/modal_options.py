"""Validated configuration helpers for modal analysis."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from solveur.core.errors import InputValidationError


@dataclass(frozen=True)
class ModalSolverOptions:
    """Validated sparse eigensolver controls and physical shift metadata."""

    shift_eigenvalue: float = 0.0
    shift_hz: float | None = None
    which: str = "LM"
    tolerance: float = 0.0
    maxiter: int | None = None
    ncv: int | None = None

    @classmethod
    def from_parameters(
        cls,
        parameters: dict[str, Any],
        *,
        method: str,
        mode_count: int,
        system_size: int,
    ) -> "ModalSolverOptions":
        if "modal_shift_hz" in parameters and "modal_shift_eigenvalue" in parameters:
            raise InputValidationError("Define only one of modal_shift_hz and modal_shift_eigenvalue.")
        shift_hz = _optional_nonnegative_float(parameters.get("modal_shift_hz"), "modal_shift_hz")
        if shift_hz is not None:
            shift = (2.0 * math.pi * shift_hz) ** 2
        else:
            shift = _optional_nonnegative_float(
                parameters.get("modal_shift_eigenvalue"), "modal_shift_eigenvalue"
            ) or 0.0
        which = str(parameters.get("arpack_which", "SM")).upper()
        if which not in {"LM", "SM", "LA", "SA", "BE"}:
            raise InputValidationError("arpack_which must be one of LM, SM, LA, SA or BE.")
        tolerance = _optional_nonnegative_float(parameters.get("arpack_tolerance"), "arpack_tolerance") or 0.0
        maxiter = _optional_positive_int(parameters.get("arpack_maxiter"), "arpack_maxiter")
        ncv = _optional_positive_int(parameters.get("arpack_ncv"), "arpack_ncv")
        if ncv is not None and not mode_count < ncv <= system_size:
            raise InputValidationError(
                f"arpack_ncv must satisfy modes < arpack_ncv <= free dofs; "
                f"got modes={mode_count}, arpack_ncv={ncv}, free dofs={system_size}."
            )
        if shift != 0.0 and method not in {"eigsh", "lanczos"}:
            raise InputValidationError("A modal shift requires method='eigsh' or method='lanczos'.")
        return cls(shift, shift_hz, which, tolerance, maxiter, ncv)

    def to_dict(self) -> dict[str, object]:
        return {
            "shift_eigenvalue": self.shift_eigenvalue,
            "shift_hz": self.shift_hz,
            "which": self.which,
            "tolerance": self.tolerance,
            "maxiter": self.maxiter,
            "ncv": self.ncv,
        }


def _optional_nonnegative_float(value: object, name: str) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{name} must be a finite non-negative number.") from exc
    if not np.isfinite(result) or result < 0.0:
        raise InputValidationError(f"{name} must be a finite non-negative number.")
    return result


def _optional_positive_int(value: object, name: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise InputValidationError(f"{name} must be a positive integer.")
    return int(value)


def _positive_parameter(value: object, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{name} must be a finite positive number.") from exc
    if not np.isfinite(result) or result <= 0.0:
        raise InputValidationError(f"{name} must be a finite positive number.")
    return result


def _positive_int_parameter(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise InputValidationError(f"{name} must be a positive integer.")
    return int(value)


def _nonnegative_int_parameter(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InputValidationError(f"{name} must be a non-negative integer.")
    return int(value)
