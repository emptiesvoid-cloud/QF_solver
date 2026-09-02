"""Stable diagnostic taxonomy for execution and recovery boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from solveur.core.errors import (
    InfrastructureError,
    InputValidationError,
    MeshValidationError,
    NumericalConvergenceError,
)


class DiagnosticCategory(str, Enum):
    """Stable categories used by execution reports."""

    MODEL_INPUT = "MODEL_INPUT"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    SOLVER_NON_CONVERGENCE = "SOLVER_NON_CONVERGENCE"
    RESOURCE_LIMITATION = "RESOURCE_LIMITATION"
    NUMERICAL_INVALIDITY = "NUMERICAL_INVALIDITY"
    CHECKPOINT_CORRUPTION = "CHECKPOINT_CORRUPTION"
    RECOVERY_FAILURE = "RECOVERY_FAILURE"
    EXECUTION_FAILURE = "EXECUTION_FAILURE"


class DiagnosticCode(str, Enum):
    """Stable machine-readable identifiers for the diagnostic categories."""

    INVALID_MODEL_INPUT = "QF-EXEC-INPUT-001"
    UNSUPPORTED_CAPABILITY = "QF-EXEC-CAPABILITY-001"
    BACKEND_UNAVAILABLE = "QF-EXEC-BACKEND-001"
    SOLVER_NON_CONVERGENCE = "QF-EXEC-SOLVE-001"
    RESOURCE_LIMITATION = "QF-EXEC-RESOURCE-001"
    NUMERICAL_INVALIDITY = "QF-EXEC-NUMERICAL-001"
    CHECKPOINT_CORRUPTION = "QF-EXEC-CHECKPOINT-001"
    RECOVERY_FAILURE = "QF-EXEC-RECOVERY-001"
    EXECUTION_FAILURE = "QF-EXEC-FAILURE-001"


@dataclass(frozen=True)
class Diagnostic:
    """A deterministic failure description suitable for evidence records."""

    code: DiagnosticCode | str
    category: DiagnosticCategory | str
    message: str
    context: Mapping[str, Any] = field(default_factory=dict)
    recoverable: bool = False

    def __post_init__(self) -> None:
        if not str(self.code).strip() or not str(self.category).strip():
            raise ValueError("Diagnostic code and category are required.")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("Diagnostic message must be non-empty.")
        if not isinstance(self.recoverable, bool):
            raise ValueError("Diagnostic recoverable flag must be boolean.")
        if not isinstance(self.context, Mapping):
            raise ValueError("Diagnostic context must be a mapping.")

    def to_dict(self) -> dict[str, Any]:
        """Return stable enum values and sorted context keys."""
        code = self.code.value if isinstance(self.code, DiagnosticCode) else str(self.code)
        category = self.category.value if isinstance(self.category, DiagnosticCategory) else str(self.category)
        return {
            "category": category,
            "code": code,
            "context": {str(key): self.context[key] for key in sorted(self.context, key=str)},
            "message": self.message,
            "recoverable": self.recoverable,
        }


class ExecutionRecoveryError(RuntimeError):
    """Raised after a recovery attempt is classified and the session fails."""

    def __init__(self, diagnostic: Diagnostic) -> None:
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


class ResourceLimitationError(RuntimeError):
    """Raised when a run cannot continue within its declared resource budget."""


def diagnostic_from_exception(
    error: BaseException,
    *,
    context: Mapping[str, Any] | None = None,
) -> Diagnostic:
    """Map existing solver exceptions to stable execution diagnostics."""
    message = str(error) or error.__class__.__name__
    lowered = message.lower()
    details = {"exception_type": error.__class__.__name__, **dict(context or {})}
    if "checkpoint" in lowered:
        if any(token in lowered for token in ("corrupt", "invalid npz", "cannot read", "malformed")):
            return Diagnostic(
                DiagnosticCode.CHECKPOINT_CORRUPTION,
                DiagnosticCategory.CHECKPOINT_CORRUPTION,
                message,
                details,
                recoverable=False,
            )
        if any(token in lowered for token in ("match", "inconsistent", "beyond", "topology", "envelope")):
            return Diagnostic(
                DiagnosticCode.RECOVERY_FAILURE,
                DiagnosticCategory.RECOVERY_FAILURE,
                message,
                details,
                recoverable=True,
            )
    if isinstance(error, ResourceLimitationError) or any(
        token in lowered for token in ("resource-limited", "out of memory", "timed out", "timeout")
    ):
        return Diagnostic(
            DiagnosticCode.RESOURCE_LIMITATION,
            DiagnosticCategory.RESOURCE_LIMITATION,
            message,
            details,
            recoverable=True,
        )
    if isinstance(error, InfrastructureError):
        return Diagnostic(
            DiagnosticCode.BACKEND_UNAVAILABLE,
            DiagnosticCategory.BACKEND_UNAVAILABLE,
            message,
            details,
            recoverable=True,
        )
    if isinstance(error, NumericalConvergenceError):
        if any(token in lowered for token in ("non-finite", "nan", "inf")):
            return Diagnostic(
                DiagnosticCode.NUMERICAL_INVALIDITY,
                DiagnosticCategory.NUMERICAL_INVALIDITY,
                message,
                details,
                recoverable=False,
            )
        return Diagnostic(
            DiagnosticCode.SOLVER_NON_CONVERGENCE,
            DiagnosticCategory.SOLVER_NON_CONVERGENCE,
            message,
            details,
            recoverable=True,
        )
    if isinstance(error, (InputValidationError, MeshValidationError)):
        if "unsupported" in lowered:
            return Diagnostic(
                DiagnosticCode.UNSUPPORTED_CAPABILITY,
                DiagnosticCategory.UNSUPPORTED_CAPABILITY,
                message,
                details,
                recoverable=False,
            )
        return Diagnostic(
            DiagnosticCode.INVALID_MODEL_INPUT,
            DiagnosticCategory.MODEL_INPUT,
            message,
            details,
            recoverable=False,
        )
    return Diagnostic(
        DiagnosticCode.EXECUTION_FAILURE,
        DiagnosticCategory.EXECUTION_FAILURE,
        message,
        details,
        recoverable=False,
    )
