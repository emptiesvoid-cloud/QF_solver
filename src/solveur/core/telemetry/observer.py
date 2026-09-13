"""Observer, sink and per-analysis sequencing primitives for telemetry."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from threading import RLock
from time import monotonic
from typing import Protocol, TypeAlias, runtime_checkable

from solveur.core.telemetry.events import (
    EventStatus,
    EventType,
    SequenceError,
    TelemetryEvent,
)
from solveur.core.telemetry.health import (
    CHILD_SINK_REPORTED_FAILURE,
    DIRECT_COMPOSITE_FAILURE,
    SinkFailure,
    TelemetryHealth,
)


MetricSupplier: TypeAlias = Callable[[], Mapping[str, object]]


@runtime_checkable
class TelemetrySink(Protocol):
    """Minimal output boundary known by numerical code."""

    def emit(self, event: TelemetryEvent) -> None:
        """Consume one already validated event."""


def _sink_identifier(sink: object, fallback: str) -> str:
    identifier = getattr(sink, "sink_identifier", getattr(sink, "sink_id", fallback))
    return str(identifier) if str(identifier).strip() else fallback


class SequenceGenerator:
    """Thread-safe, independent sequence counters keyed by analysis id."""

    def __init__(self) -> None:
        self._next_by_analysis: dict[str, int] = {}
        self._lock = RLock()

    @staticmethod
    def _validate_analysis_id(analysis_id: str) -> None:
        if not isinstance(analysis_id, str) or not analysis_id.strip():
            raise ValueError("analysis_id must be a non-empty string.")

    def next(self, analysis_id: str) -> int:
        """Return and reserve the next number, starting at zero."""

        self._validate_analysis_id(analysis_id)
        with self._lock:
            number = self._next_by_analysis.get(analysis_id, 0)
            self._next_by_analysis[analysis_id] = number + 1
            return number

    def rollback(self, analysis_id: str, sequence_number: int) -> bool:
        """Undo the last reservation when no other producer advanced the stream."""

        self._validate_analysis_id(analysis_id)
        with self._lock:
            if self._next_by_analysis.get(analysis_id) != sequence_number + 1:
                return False
            self._next_by_analysis[analysis_id] = sequence_number
            return True

    def observe(self, analysis_id: str, sequence_number: int) -> None:
        """Accept only the exact next number at an external producer boundary."""

        self._validate_analysis_id(analysis_id)
        if not isinstance(sequence_number, int) or isinstance(sequence_number, bool):
            raise SequenceError("sequence_number must be an integer.")
        with self._lock:
            expected = self._next_by_analysis.get(analysis_id, 0)
            if sequence_number != expected:
                raise SequenceError(
                    f"Expected sequence {expected} for analysis {analysis_id!r}, got {sequence_number}."
                )
            self._next_by_analysis[analysis_id] = sequence_number + 1


class SequenceValidator:
    """Validate contiguous per-analysis event streams without global ordering."""

    def __init__(self) -> None:
        self._generator = SequenceGenerator()

    def validate(self, event: TelemetryEvent) -> None:
        """Reject duplicate, skipped or backwards event numbers."""

        self._generator.observe(event.analysis_id, event.sequence_number)


class CompositeSink:
    """Fan out events while isolating ordinary failures in individual sinks."""

    def __init__(
        self,
        sinks: Iterable[TelemetrySink] | Mapping[str, TelemetrySink] = (),
        *,
        health: TelemetryHealth | None = None,
        sink_identifier: str = "composite",
    ) -> None:
        if isinstance(sinks, Mapping):
            items = [(str(identifier), sink) for identifier, sink in sinks.items()]
        else:
            items = [(f"sink_{index}", sink) for index, sink in enumerate(sinks)]
        self._sinks = tuple((_sink_identifier(sink, identifier), sink) for identifier, sink in items)
        self._health = health or TelemetryHealth(sink_identifier)
        self._lock = RLock()
        self._reported_child_failure_tokens: set[tuple[tuple[str, int], int, SinkFailure]] = set()
        self._reported_degraded_children: set[tuple[str, int]] = set()
        self.refresh_health()

    @property
    def health(self) -> TelemetryHealth:
        """Return effective health after incorporating all child ledgers."""

        self.refresh_health()
        return self._health

    @property
    def sinks(self) -> tuple[TelemetrySink, ...]:
        return tuple(sink for _, sink in self._sinks)

    @staticmethod
    def _child_failure(raw_failure: object, identifier: str) -> SinkFailure:
        if isinstance(raw_failure, SinkFailure):
            return raw_failure
        if isinstance(raw_failure, Mapping):
            def read(name: str, default: object = None) -> object:
                return raw_failure.get(name, default)
        else:
            def read(name: str, default: object = None) -> object:
                return getattr(raw_failure, name, default)
        failure_type = read("failure_type", "ChildHealthFailure")
        failure_message = read("failure_message", "child sink reported a failure")
        sequence_number = read("sequence_number")
        event_type = read("event_type")
        return SinkFailure(
            sink_identifier=str(read("sink_identifier", identifier) or identifier),
            failure_type=str(failure_type or "ChildHealthFailure"),
            failure_message=str(failure_message or "child sink reported a failure"),
            sequence_number=(
                sequence_number
                if isinstance(sequence_number, int) and not isinstance(sequence_number, bool)
                else None
            ),
            event_type=str(event_type) if event_type is not None else None,
        )

    @staticmethod
    def _child_is_degraded(child_health: object) -> bool:
        if bool(getattr(child_health, "degraded", False)):
            return True
        for name in ("status", "state"):
            value = getattr(child_health, name, None)
            if getattr(value, "value", value) == "DEGRADED":
                return True
        return False

    def _aggregate_child_health(self, identifier: str, sink: TelemetrySink) -> None:
        """Mirror compatible child health once while preserving child context."""

        if sink is self:
            return
        child_health = getattr(sink, "health", None)
        if child_health is None:
            return
        child_key = (identifier, id(sink))
        try:
            raw_failures = getattr(child_health, "failures", ())
            failures = tuple(raw_failures) if raw_failures is not None else ()
            for index, raw_failure in enumerate(failures):
                failure = self._child_failure(raw_failure, identifier)
                token = (child_key, index, failure)
                if token in self._reported_child_failure_tokens:
                    continue
                self._health.record_failure_details(
                    failure,
                    provenance=CHILD_SINK_REPORTED_FAILURE,
                )
                self._reported_child_failure_tokens.add(token)
            if self._child_is_degraded(child_health) and not failures:
                degraded_token = child_key
                if degraded_token not in self._reported_degraded_children:
                    self._health.record_failure(
                        f"child sink {identifier} reported DEGRADED without a failure ledger",
                        sink_identifier=identifier,
                        provenance=CHILD_SINK_REPORTED_FAILURE,
                    )
                    self._reported_degraded_children.add(degraded_token)
        except Exception as error:
            self._health.record_failure(
                error,
                sink_identifier=identifier,
                provenance=CHILD_SINK_REPORTED_FAILURE,
            )

    def refresh_health(self) -> None:
        """Refresh effective health without allowing bookkeeping to raise."""

        with self._lock:
            for identifier, sink in self._sinks:
                self._aggregate_child_health(identifier, sink)

    def emit(self, event: TelemetryEvent) -> None:
        """Deliver to every sink; one sink failure cannot stop its siblings."""

        with self._lock:
            for identifier, sink in self._sinks:
                try:
                    sink.emit(event)
                except Exception as error:
                    self._health.record_failure(
                        error,
                        sink_identifier=identifier,
                        event=event,
                        provenance=DIRECT_COMPOSITE_FAILURE,
                    )
                finally:
                    self._aggregate_child_health(identifier, sink)
            self.refresh_health()

    def flush(self) -> None:
        """Best-effort flush for all sinks."""

        with self._lock:
            for identifier, sink in self._sinks:
                flush = getattr(sink, "flush", None)
                if not callable(flush):
                    continue
                try:
                    flush()
                except Exception as error:
                    self._health.record_failure(
                        error,
                        sink_identifier=identifier,
                        provenance=DIRECT_COMPOSITE_FAILURE,
                    )
                finally:
                    self._aggregate_child_health(identifier, sink)
            self.refresh_health()

    def close(self) -> None:
        """Best-effort close for all sinks."""

        with self._lock:
            for identifier, sink in self._sinks:
                close = getattr(sink, "close", None)
                if not callable(close):
                    continue
                try:
                    close()
                except Exception as error:
                    self._health.record_failure(
                        error,
                        sink_identifier=identifier,
                        provenance=DIRECT_COMPOSITE_FAILURE,
                    )
                finally:
                    self._aggregate_child_health(identifier, sink)
            self.refresh_health()


class MemorySink:
    """Bounded in-memory sink intended for tests and focused debugging."""

    def __init__(
        self,
        *,
        max_events: int | None = 10_000,
        sink_identifier: str = "memory",
        health: TelemetryHealth | None = None,
    ) -> None:
        if max_events is not None and (not isinstance(max_events, int) or max_events <= 0):
            raise ValueError("max_events must be positive or None.")
        self.max_events = max_events
        self.sink_identifier = sink_identifier
        self.health = health or TelemetryHealth(sink_identifier)
        self._events: list[TelemetryEvent] = []
        self._sequence = SequenceValidator()
        self._closed = False
        self._lock = RLock()

    @property
    def events(self) -> tuple[TelemetryEvent, ...]:
        with self._lock:
            return tuple(self._events)

    @property
    def records(self) -> tuple[dict[str, object], ...]:
        return tuple(event.to_dict() for event in self.events)

    def emit(self, event: TelemetryEvent) -> None:
        with self._lock:
            try:
                if self._closed:
                    raise RuntimeError("memory sink is closed")
                if not isinstance(event, TelemetryEvent):
                    event = TelemetryEvent.from_mapping(event)
                if self.max_events is not None and len(self._events) >= self.max_events:
                    raise MemoryError("memory telemetry sink capacity reached")
                self._sequence.validate(event)
                self._events.append(event)
            except Exception as error:
                self.health.record_failure(error, event=event if isinstance(event, TelemetryEvent) else None)

    def flush(self) -> None:
        """Memory has no buffered I/O."""

    def close(self) -> None:
        with self._lock:
            self._closed = True


class TelemetryEmitter:
    """Create common events and deliver them to an optional sink group."""

    def __init__(
        self,
        analysis_id: str,
        analysis_type: str,
        route: str,
        sinks: TelemetrySink | Iterable[TelemetrySink] | None = None,
        *,
        enabled: bool = True,
        metadata: Mapping[str, object] | None = None,
        sequence_generator: SequenceGenerator | None = None,
    ) -> None:
        self.analysis_id = analysis_id
        self.analysis_type = analysis_type
        self.route = route
        self.enabled = enabled
        self._metadata = dict(metadata or {})
        self._sequence = sequence_generator or SequenceGenerator()
        if sinks is None:
            sink_items: Iterable[TelemetrySink] = ()
        elif isinstance(sinks, TelemetrySink):
            sink_items = (sinks,)
        else:
            sink_items = sinks
        self.sink = CompositeSink(sink_items)
        self._started = monotonic()
        self._lock = RLock()

    @property
    def health(self) -> TelemetryHealth:
        return self.sink.health

    def emit(
        self,
        event_type: EventType | str,
        *,
        status: EventStatus | str,
        metrics: Mapping[str, object] | MetricSupplier | None = None,
        metadata: Mapping[str, object] | None = None,
        elapsed_time_s: float | None = None,
        timestamp: str | None = None,
        step: int | None = None,
        iteration: int | None = None,
        load_factor: float | None = None,
        physical_time: float | None = None,
        solver_backend: str | None = None,
        message: str | None = None,
    ) -> TelemetryEvent | None:
        """Emit one event, evaluating lazy metrics only when enabled."""

        if not self.enabled:
            return None
        with self._lock:
            if callable(metrics):
                measured_metrics = metrics()
            else:
                measured_metrics = {} if metrics is None else metrics
            combined_metadata = dict(self._metadata)
            combined_metadata.update(metadata or {})
            sequence_number = self._sequence.next(self.analysis_id)
            try:
                elapsed = monotonic() - self._started if elapsed_time_s is None else elapsed_time_s
                event = TelemetryEvent(
                    schema_version=1,
                    event_type=event_type,
                    analysis_id=self.analysis_id,
                    analysis_type=self.analysis_type,
                    route=self.route,
                    sequence_number=sequence_number,
                    elapsed_time_s=elapsed,
                    status=status,
                    metrics=measured_metrics,
                    metadata=combined_metadata,
                    timestamp=timestamp,
                    step=step,
                    iteration=iteration,
                    load_factor=load_factor,
                    physical_time=physical_time,
                    solver_backend=solver_backend,
                    message=message,
                )
            except Exception:
                self._sequence.rollback(self.analysis_id, sequence_number)
                raise
            self.sink.emit(event)
            return event

    def flush(self) -> None:
        if self.enabled:
            self.sink.flush()

    def close(self) -> None:
        if self.enabled:
            self.sink.close()


def emit_route_event_best_effort(
    emitter: TelemetryEmitter | None,
    event_type: EventType | str,
    *,
    status: EventStatus | str,
    metrics: Mapping[str, object] | MetricSupplier | None = None,
    metadata: Mapping[str, object] | None = None,
    elapsed_time_s: float | None = None,
    timestamp: str | None = None,
    step: int | None = None,
    iteration: int | None = None,
    load_factor: float | None = None,
    physical_time: float | None = None,
    solver_backend: str | None = None,
    message: str | None = None,
) -> None:
    """Emit route telemetry without allowing observability to alter a solve."""

    if emitter is None or not emitter.enabled:
        return
    try:
        emitter.emit(
            event_type,
            status=status,
            metrics=metrics,
            metadata=metadata,
            elapsed_time_s=elapsed_time_s,
            timestamp=timestamp,
            step=step,
            iteration=iteration,
            load_factor=load_factor,
            physical_time=physical_time,
            solver_backend=solver_backend,
            message=message,
        )
    except Exception as error:
        try:
            emitter.health.record_failure(error, sink_identifier="emitter")
        except Exception:
            pass


def emit_analysis_failed_best_effort(
    emitter: TelemetryEmitter | None,
    error: BaseException,
    *,
    message: str = "solver exception preserved",
) -> None:
    """Attempt terminal failure telemetry without ever replacing the error."""

    if emitter is None or not emitter.enabled:
        return
    try:
        emitter.emit(
            EventType.ANALYSIS_FAILED,
            status=EventStatus.FAILED,
            metrics={
                "error_type": type(error).__name__,
                "error_message": str(error) or type(error).__name__,
            },
            message=message,
        )
    except BaseException:
        return


@contextmanager
def preserve_solver_exception(emitter: TelemetryEmitter | None) -> Iterator[None]:
    """Emit best-effort failure telemetry and re-raise the original exception."""

    try:
        yield
    except BaseException as error:
        emit_analysis_failed_best_effort(emitter, error)
        raise
