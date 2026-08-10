"""Shared deterministic signatures for restart checkpoints."""

from __future__ import annotations

import json

from solveur.core.errors import InputValidationError
from solveur.io.manifest import content_digest


def checkpoint_signature(payload: dict[str, object], *, label: str) -> str:
    """Hash a JSON-compatible physical model description."""
    try:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{label} checkpoint signature payload is not JSON serializable.") from exc
    return content_digest(encoded)
