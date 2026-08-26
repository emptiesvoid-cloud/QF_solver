"""Small shared helpers for the nonlinear solver modules."""

from __future__ import annotations

from solveur.core.nonlinear_contracts import NonlinearFailureReason


def _failure_reason_value(error: BaseException) -> str:
    """Return a stable failure code for adaptive-step telemetry."""
    reason = getattr(error, "reason", None)
    if isinstance(reason, NonlinearFailureReason):
        return reason.value
    if reason is not None:
        return str(reason)
    return type(error).__name__
