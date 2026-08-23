"""Validated configuration helpers for modal analysis."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from solveur.core.errors import InputValidationError


# These are release-gate values, not claims about the maximum capability of
# PETSc/SLEPc.  The first value is the largest modal campaign currently
# archived; the second is the conservative pre-assembly protection limit.
SLEPC_MODAL_TESTED_MAX_DOFS = 107_811
SLEPC_MODAL_PROTECTION_LIMIT = 500_000


def validate_slepc_modal_scale(global_dofs: int, *, requested: bool) -> None:
    """Reject an unqualified large SLEPc modal request before assembly.

    The check intentionally uses the global model DDL count rather than the
    reduced free-DOF count.  It is therefore conservative and, importantly,
    runs before allocating global stiffness and mass matrices.  The limit is
    a protection gate for the current release, not a proof that a larger
    model cannot be solved with a different factorization or machine.
    """

    if not requested:
        return
    try:
        dofs = int(global_dofs)
    except (TypeError, ValueError) as exc:
        raise InputValidationError("The modal global DDL count must be an integer.") from exc
    if dofs < 0:
        raise InputValidationError("The modal global DDL count must be non-negative.")
    if dofs <= SLEPC_MODAL_PROTECTION_LIMIT:
        return
    raise InputValidationError(
        "SLEPc modal solve refused before sparse assembly: "
        f"requested global DDL={dofs:,}, protection limit="
        f"{SLEPC_MODAL_PROTECTION_LIMIT:,}. The currently tested SLEPc scope "
        f"ends at {SLEPC_MODAL_TESTED_MAX_DOFS:,} DDL; the protection limit is "
        "a theoretical R&D ceiling, not a validated capacity. "
        "Use the SciPy modal path or an explicitly qualified R&D backend, "
        "and do not infer 2M-DDL support from this release."
    )


def _boolean_parameter(value: object, name: str) -> bool:
    """Parse a strict boolean analysis parameter without truthiness traps."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    raise InputValidationError(f"{name} must be a boolean.")


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
