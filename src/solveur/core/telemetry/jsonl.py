"""Failure-isolated JSONL sink for the generic telemetry envelope."""

from __future__ import annotations

import os
from pathlib import Path
from threading import RLock
from typing import TextIO, cast

from solveur.core.telemetry.events import EventType, TelemetryEvent
from solveur.core.telemetry.health import TelemetryHealth


DURABILITY_EVENT_TYPES = frozenset(
    {
        EventType.CHECKPOINT.value,
        EventType.ANALYSIS_END.value,
        EventType.ANALYSIS_FAILED.value,
    }
)


class JsonlSink:
    """Append validated events and isolate ordinary file failures.

    A single JsonlSink instance is intended for one writer and one logical
    analysis stream. The emitter provides per-analysis sequence assignment;
    this sink does not claim cross-process or distributed ordering.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        fsync: bool = False,
        sink_identifier: str = "jsonl",
        health: TelemetryHealth | None = None,
    ) -> None:
        self.path = Path(path)
        self.fsync = fsync
        self.sink_identifier = sink_identifier
        self.health = health or TelemetryHealth(sink_identifier)
        self._stream: TextIO | None = None
        self._closed = False
        self._lock = RLock()
        try:
            self._stream = self.path.open("a", encoding="utf-8", newline="")
        except Exception as error:
            self._record_failure(error)

    @property
    def status(self) -> str:
        return self.health.status

    @property
    def is_open(self) -> bool:
        with self._lock:
            return self._stream is not None and not self._closed

    def _record_failure(self, error: BaseException, event: TelemetryEvent | None = None) -> None:
        self.health.record_failure(error, event=event)
        stream = self._stream
        self._stream = None
        if stream is not None:
            try:
                stream.close()
            except Exception:
                pass

    def emit(self, event: TelemetryEvent) -> None:
        with self._lock:
            if not isinstance(event, TelemetryEvent):
                try:
                    event = TelemetryEvent.from_mapping(event)
                except Exception as error:
                    self._record_failure(error)
                    return
            if self._closed or self._stream is None:
                return
            try:
                self._stream.write(event.to_json() + "\n")
                self._stream.flush()
                event_type = cast(EventType, event.event_type)
                if self.fsync and event_type.value in DURABILITY_EVENT_TYPES:
                    os.fsync(self._stream.fileno())
            except Exception as error:
                self._record_failure(error, event)

    def flush(self) -> None:
        with self._lock:
            if self._stream is None or self._closed:
                return
            try:
                self._stream.flush()
            except Exception as error:
                self._record_failure(error)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            stream = self._stream
            self._stream = None
            if stream is None:
                return
            try:
                stream.close()
            except Exception as error:
                self.health.record_failure(error)

    def __enter__(self) -> "JsonlSink":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
