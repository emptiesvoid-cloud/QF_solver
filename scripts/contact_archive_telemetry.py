"""Decode telemetry events stored as mappings or JSON strings in run archives."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any


def decode_telemetry_event(value: object, *, index: int) -> dict[str, Any]:
    """Return one event mapping from an in-memory or serialized archive value."""
    if isinstance(value, Mapping):
        return dict(value)
    if not isinstance(value, str):
        raise ValueError(f"telemetry event {index} must be an object or JSON string")
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"telemetry event {index} contains invalid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError(f"telemetry event {index} JSON must decode to an object")
    return dict(decoded)


def decode_telemetry_events(value: object) -> list[dict[str, Any]]:
    """Normalize an event sequence without treating a JSON string as a sequence."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError("telemetry_events must be a sequence of events")
    return [decode_telemetry_event(event, index=index) for index, event in enumerate(value)]
