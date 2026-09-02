"""Fail-closed execution lifecycle and recovery coordination."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, TypeVar

from solveur.execution.diagnostics import (
    Diagnostic,
    ExecutionRecoveryError,
    diagnostic_from_exception,
)


class ExecutionState(str, Enum):
    """States allowed by the minimal execution contract."""

    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    RUNNING = "RUNNING"
    CONVERGED = "CONVERGED"
    FAILED = "FAILED"
    CHECKPOINTED = "CHECKPOINTED"
    RECOVERED = "RECOVERED"


class ExecutionContractError(RuntimeError):
    """Raised when a lifecycle transition would violate the contract."""


_ALLOWED_TRANSITIONS = {
    ExecutionState.CREATED: {ExecutionState.VALIDATED, ExecutionState.FAILED},
    ExecutionState.VALIDATED: {ExecutionState.RUNNING, ExecutionState.FAILED},
    ExecutionState.RUNNING: {ExecutionState.CONVERGED, ExecutionState.FAILED},
    ExecutionState.CONVERGED: {ExecutionState.CHECKPOINTED, ExecutionState.FAILED},
    ExecutionState.CHECKPOINTED: {ExecutionState.RECOVERED, ExecutionState.FAILED},
    ExecutionState.RECOVERED: {ExecutionState.RUNNING, ExecutionState.FAILED},
    ExecutionState.FAILED: set(),
}
T = TypeVar("T")


@dataclass
class ExecutionSession:
    """Track one route without changing how the underlying solver executes."""

    case_id: str
    source_sha: str
    route: str
    backend: str
    provenance: dict[str, Any] = field(default_factory=dict)
    state: ExecutionState = ExecutionState.CREATED
    solver_status: str = "NOT_STARTED"
    evidence_link: str | None = None
    diagnostic: Diagnostic | None = None
    state_history: list[ExecutionState] = field(default_factory=list)

    def __post_init__(self) -> None:
        for name in ("case_id", "source_sha", "route", "backend"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")
        if not self.state_history:
            self.state_history.append(self.state)

    def transition(
        self,
        target: ExecutionState | str,
        *,
        solver_status: str | None = None,
        evidence_link: str | None = None,
        provenance: Mapping[str, Any] | None = None,
        diagnostic: Diagnostic | None = None,
    ) -> None:
        """Apply one legal transition; invalid transitions fail closed."""
        try:
            next_state = target if isinstance(target, ExecutionState) else ExecutionState(str(target).upper())
        except ValueError as exc:
            raise ExecutionContractError(f"Unknown execution state {target!r}.") from exc
        if next_state not in _ALLOWED_TRANSITIONS[self.state]:
            raise ExecutionContractError(f"Invalid execution transition {self.state.value} -> {next_state.value}.")
        if next_state == ExecutionState.FAILED and diagnostic is None:
            raise ExecutionContractError("FAILED transition requires a structured diagnostic.")
        self.state = next_state
        self.state_history.append(next_state)
        self.solver_status = solver_status or next_state.value
        if evidence_link is not None:
            self.evidence_link = evidence_link
        if provenance:
            self.provenance.update(provenance)
        if diagnostic is not None:
            self.diagnostic = diagnostic

    def validate(self, *, provenance: Mapping[str, Any] | None = None) -> None:
        self.transition(ExecutionState.VALIDATED, provenance=provenance)

    def execute(self, operation: Callable[[], T]) -> T:
        """Run an already validated operation and classify failures explicitly."""
        if self.state is not ExecutionState.VALIDATED:
            raise ExecutionContractError("Execution requires the VALIDATED state.")
        self.transition(ExecutionState.RUNNING)
        try:
            result = operation()
        except Exception as exc:
            diagnostic = diagnostic_from_exception(exc, context={"case_id": self.case_id, "route": self.route})
            self.fail(diagnostic)
            raise
        self.transition(ExecutionState.CONVERGED, solver_status="CONVERGED")
        return result

    def checkpoint(self, *, evidence_link: str, provenance: Mapping[str, Any] | None = None) -> None:
        if not evidence_link.strip():
            raise ValueError("evidence_link must be non-empty.")
        self.transition(ExecutionState.CHECKPOINTED, evidence_link=evidence_link, provenance=provenance)

    def recover(self, loader: Callable[[], T]) -> T:
        """Load a checkpoint and mark recovery failure instead of hiding corruption."""
        if self.state is not ExecutionState.CHECKPOINTED:
            raise ExecutionContractError("Recovery requires the CHECKPOINTED state.")
        try:
            value = loader()
        except Exception as exc:
            diagnostic = diagnostic_from_exception(exc, context={"case_id": self.case_id, "route": self.route})
            self.fail(diagnostic)
            raise ExecutionRecoveryError(diagnostic) from exc
        self.transition(ExecutionState.RECOVERED, solver_status="RECOVERED")
        return value

    def fail(self, diagnostic: Diagnostic) -> None:
        self.transition(ExecutionState.FAILED, solver_status="FAILED", diagnostic=diagnostic)

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "case_id": self.case_id,
            "diagnostic": self.diagnostic.to_dict() if self.diagnostic else None,
            "evidence_link": self.evidence_link,
            "provenance": {str(key): self.provenance[key] for key in sorted(self.provenance, key=str)},
            "route": self.route,
            "solver_status": self.solver_status,
            "source_sha": self.source_sha,
            "state": self.state.value,
            "state_history": [item.value for item in self.state_history],
        }
