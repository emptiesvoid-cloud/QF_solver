"""Opt-in, failure-isolated telemetry for unified nonlinear solves."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


NonlinearTelemetryObserver = Callable[[Mapping[str, object]], None]


class JsonlNonlinearTelemetry:
    """Write compact solver events without retaining matrices or state arrays."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._stream = self.path.open("a", encoding="utf-8")

    def __call__(self, event: Mapping[str, object]) -> None:
        self._stream.write(json.dumps(dict(event), sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
        self._stream.flush()

    def close(self) -> None:
        self._stream.close()

    def __enter__(self) -> "JsonlNonlinearTelemetry":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def emit_telemetry(observer: NonlinearTelemetryObserver | None, event: Mapping[str, object]) -> None:
    """Emit a detached event; observer failures must never change a solve."""

    if observer is None:
        return
    try:
        observer(dict(event))
    except Exception:
        # Telemetry is diagnostic-only and is forbidden from affecting state,
        # convergence, retries, or failure classification.
        return


def process_memory_bytes() -> tuple[int | None, int | None]:
    """Return RSS and USS/private bytes when psutil is available."""

    try:
        import psutil

        process = psutil.Process()
        rss = int(process.memory_info().rss)
        full = process.memory_full_info()
        private = getattr(full, "uss", getattr(full, "private", None))
        return rss, None if private is None else int(private)
    except Exception:
        return None, None


def telemetry_event(event: str, **values: Any) -> dict[str, object]:
    """Construct a JSON-safe telemetry event with a stable event discriminator."""

    return {"event": event, **values}
