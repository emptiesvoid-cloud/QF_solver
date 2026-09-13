"""Explicit health accounting for non-critical telemetry sinks."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import cast

from solveur.core.telemetry.events import EventType, TelemetryEvent


class HealthState(str, Enum):
    """Operational state of a telemetry sink or sink group."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"


@dataclass(frozen=True, slots=True)
class SinkFailure:
    """One recorded sink failure with the event context available at failure."""

    sink_identifier: str
    failure_type: str
    failure_message: str
    sequence_number: int | None = None
    event_type: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "sink_identifier": self.sink_identifier,
            "failure_type": self.failure_type,
            "failure_message": self.failure_message,
            "sequence_number": self.sequence_number,
            "event_type": self.event_type,
        }


class TelemetryHealth:
    """Thread-safe health ledger which never raises while recording a failure."""

    def __init__(self, sink_identifier: str = "telemetry") -> None:
        if not isinstance(sink_identifier, str) or not sink_identifier.strip():
            raise ValueError("sink_identifier must be a non-empty string.")
        self.sink_identifier = sink_identifier
        self._failures: list[SinkFailure] = []
        self._lock = RLock()

    @property
    def state(self) -> HealthState:
        with self._lock:
            return HealthState.DEGRADED if self._failures else HealthState.HEALTHY

    @property
    def status(self) -> str:
        return self.state.value

    @property
    def degraded(self) -> bool:
        return self.state is HealthState.DEGRADED

    @property
    def failures(self) -> tuple[SinkFailure, ...]:
        with self._lock:
            return tuple(self._failures)

    def record_failure(
        self,
        error: BaseException | str,
        *,
        sink_identifier: str | None = None,
        event: TelemetryEvent | Mapping[str, object] | None = None,
    ) -> None:
        """Record a failure without allowing bookkeeping to mask the solve."""

        if isinstance(error, BaseException):
            failure_type = type(error).__name__
            failure_message = str(error) or failure_type
        else:
            failure_type = "TelemetryError"
            failure_message = str(error)
        if not failure_message:
            failure_message = failure_type
        sequence_number: int | None = None
        event_type: str | None = None
        if isinstance(event, TelemetryEvent):
            sequence_number = event.sequence_number
            event_type = cast(EventType, event.event_type).value
        elif isinstance(event, Mapping):
            sequence = event.get("sequence_number")
            sequence_number = sequence if isinstance(sequence, int) and not isinstance(sequence, bool) else None
            event_value = event.get("event_type")
            event_type = event_value if isinstance(event_value, str) else None
        failure = SinkFailure(
            sink_identifier=sink_identifier or self.sink_identifier,
            failure_type=failure_type,
            failure_message=failure_message,
            sequence_number=sequence_number,
            event_type=event_type,
        )
        with self._lock:
            self._failures.append(failure)

    def to_dict(self) -> dict[str, object]:
        with self._lock:
            return {
                "sink_identifier": self.sink_identifier,
                "state": HealthState.DEGRADED.value if self._failures else HealthState.HEALTHY.value,
                "failures": [failure.to_dict() for failure in self._failures],
            }
