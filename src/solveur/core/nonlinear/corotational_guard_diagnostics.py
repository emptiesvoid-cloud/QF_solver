"""Opt-in, non-invasive records for corrected corotational domain refusals."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
from typing import Any, Iterator, Mapping


_LOGGER = logging.getLogger("solveur.nonlinear.corotational_guard")
_CURRENT_CONTEXT: ContextVar[dict[str, Any] | None] = ContextVar(
    "qf_corotational_guard_context", default=None
)


@contextmanager
def bind_newton_trial_guard_context(
    context: Mapping[str, Any], *, enabled: bool
) -> Iterator[None]:
    """Bind Newton coordinates only when the caller explicitly enables logging."""

    if not enabled:
        yield
        return
    token = _CURRENT_CONTEXT.set(dict(context))
    try:
        yield
    finally:
        _CURRENT_CONTEXT.reset(token)


def emit_corotational_guard_event(event: Mapping[str, Any]) -> None:
    """Emit one structured refusal record without affecting solver decisions."""

    context = _CURRENT_CONTEXT.get()
    if context is None:
        return
    payload = {
        "schema": "qfsolver-corotational-guard-event-v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        **context,
        **dict(event),
    }
    try:
        _LOGGER.warning("QF_COROTATIONAL_GUARD %s", json.dumps(payload, sort_keys=True))
    except Exception:
        # Diagnostic plumbing must never change Newton acceptance or rejection.
        return
