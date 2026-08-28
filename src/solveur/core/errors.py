"""Stable solver error categories and process exit codes."""

from __future__ import annotations

from enum import IntEnum
from typing import Any

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
