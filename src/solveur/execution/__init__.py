"""Execution-state, diagnostic and recovery contracts for solver routes."""

from solveur.execution.contract import (
    ExecutionContractError,
    ExecutionSession,
    ExecutionState,
)
from solveur.execution.diagnostics import (
    Diagnostic,
    DiagnosticCategory,
    DiagnosticCode,
    ExecutionRecoveryError,
    ResourceLimitationError,
    diagnostic_from_exception,
)

__all__ = [
    "Diagnostic",
    "DiagnosticCategory",
    "DiagnosticCode",
    "ExecutionContractError",
    "ExecutionRecoveryError",
    "ResourceLimitationError",
    "ExecutionSession",
    "ExecutionState",
    "diagnostic_from_exception",
]
