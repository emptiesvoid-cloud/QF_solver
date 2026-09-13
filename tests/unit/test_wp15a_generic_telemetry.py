"""Targeted WP15-A tests for the generic telemetry core."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from solveur.core.telemetry import (
    CHILD_SINK_REPORTED_FAILURE,
    DURABILITY_EVENT_TYPES,
    DIRECT_COMPOSITE_FAILURE,
    LINEAR_BACKENDS,
    MEMORY_FIELD_NAMES,
    TIMING_FIELD_NAMES,
    CompositeSink,
    EventStatus,
    EventType,
    JsonlSink,
    LegacyWP04Adapter,
    MemorySink,
    MissingValueReason,
    SequenceError,
    SequenceGenerator,
    SequenceValidator,
    TelemetryEmitter,
    TelemetryEvent,
    TelemetryHealth,
    TelemetryValidationError,
    missing_value,
    preserve_solver_exception,
    validate_linear_solver_metrics,
    validate_memory_metrics,
    validate_timing_metrics,
)


def make_event(
    *,
    sequence_number: int = 0,
    analysis_id: str = "analysis-a",
    event_type: EventType = EventType.ANALYSIS_START,
    status: EventStatus = EventStatus.STARTED,
    metrics: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
) -> TelemetryEvent:
    return TelemetryEvent(
        schema_version=1,
        event_type=event_type,
        analysis_id=analysis_id,
        analysis_type="linear_static",
        route="linear_static",
        sequence_number=sequence_number,
        elapsed_time_s=0.25,
        status=status,
        metrics={"residual": 1.0} if metrics is None else metrics,
        metadata={"source": "unit-test"} if metadata is None else metadata,
    )


def test_controlled_event_types_and_statuses_are_finite_contract_vocabulary() -> None:
    expected = {
        "ANALYSIS_START",
        "ANALYSIS_END",
        "ANALYSIS_FAILED",
        "MESH_READY",
        "ASSEMBLY_START",
        "ASSEMBLY_END",
        "LINEAR_SOLVE_START",
        "LINEAR_SOLVE_ITERATION",
        "LINEAR_SOLVE_END",
        "STEP_START",
        "STEP_ACCEPTED",
        "STEP_REJECTED",
        "NONLINEAR_ITERATION",
        "LINE_SEARCH_TRIAL",
        "LINE_SEARCH_ACCEPTED",
        "LINE_SEARCH_REJECTED",
        "CHECKPOINT",
        "CONTACT_STATE",
        "TIME_STEP_START",
        "TIME_STEP_ACCEPTED",
        "TIME_STEP_REJECTED",
        "MODAL_MODE_FOUND",
    }
    assert {event.value for event in EventType} == expected
    assert EventStatus.FAILED.value == "FAILED"
    assert EventStatus.COMPLETED.value == "COMPLETED"


def test_event_requires_all_mandatory_fields_and_rejects_unknown_fields() -> None:
    record = make_event().to_dict()
    del record["metadata"]
    with pytest.raises(TelemetryValidationError, match="metadata"):
        TelemetryEvent.from_mapping(record)

    record = make_event().to_dict()
    record["unexpected"] = True
    with pytest.raises(TelemetryValidationError, match="Unknown event fields"):
        TelemetryEvent.from_mapping(record)


@pytest.mark.parametrize("nonfinite", [math.nan, math.inf, -math.inf])
def test_nested_nonfinite_values_are_rejected(nonfinite: float) -> None:
    with pytest.raises(TelemetryValidationError, match="finite"):
        make_event(metrics={"nested": {"values": [1.0, nonfinite]}})
    with pytest.raises(TelemetryValidationError, match="finite"):
        make_event(metadata={"nested": {"values": [nonfinite]}})


def test_missing_measurement_is_explicit_and_bare_null_is_rejected() -> None:
    event = make_event(metrics={"residual": missing_value(MissingValueReason.NOT_COMPUTABLE)})
    payload = json.loads(event.to_json())
    assert payload["metrics"]["residual"] == {"reason": "NOT_COMPUTABLE", "value": None}

    with pytest.raises(TelemetryValidationError, match="null"):
        make_event(metrics={"residual": None})
    with pytest.raises(TelemetryValidationError, match="Unknown missing-value"):
        missing_value("UNCONTROLLED")


def test_event_json_is_deterministic_when_clock_fields_are_declared() -> None:
    first = make_event(metadata={"b": 2, "a": 1})
    second = make_event(metadata={"a": 1, "b": 2})
    assert first.to_json() == second.to_json()
    assert json.loads(first.to_json())["schema_version"] == 1


def test_sequence_generator_has_independent_streams_and_rejects_wrong_numbers() -> None:
    generator = SequenceGenerator()
    assert generator.next("A") == 0
    assert generator.next("B") == 0
    assert generator.next("A") == 1
    generator.observe("B", 1)
    with pytest.raises(SequenceError, match="Expected sequence 2"):
        generator.observe("B", 1)

    validator = SequenceValidator()
    validator.validate(make_event(sequence_number=0))
    validator.validate(make_event(sequence_number=1))
    with pytest.raises(SequenceError):
        validator.validate(make_event(sequence_number=1))
    with pytest.raises(SequenceError):
        validator.validate(make_event(sequence_number=3))


def test_emitter_assigns_per_analysis_sequence_and_preserves_order() -> None:
    sink = MemorySink()
    emitter = TelemetryEmitter("run-a", "linear_static", "linear_static", sink)
    emitter.emit(EventType.ANALYSIS_START, status=EventStatus.STARTED, elapsed_time_s=0.0)
    emitter.emit(EventType.ANALYSIS_END, status=EventStatus.COMPLETED, elapsed_time_s=1.0)
    assert [event.sequence_number for event in sink.events] == [0, 1]
    assert [event.event_type.value for event in sink.events] == ["ANALYSIS_START", "ANALYSIS_END"]


def test_disabled_emitter_does_not_call_sinks_or_lazy_metric_suppliers() -> None:
    class CountingSink:
        def __init__(self) -> None:
            self.calls = 0

        def emit(self, _event: TelemetryEvent) -> None:
            self.calls += 1

    sink = CountingSink()
    emitter = TelemetryEmitter("disabled", "linear_static", "linear_static", sink, enabled=False)
    called = False

    def supplier() -> dict[str, object]:
        nonlocal called
        called = True
        raise AssertionError("lazy metrics were evaluated on disabled path")

    assert emitter.emit(EventType.ANALYSIS_START, status=EventStatus.STARTED, metrics=supplier) is None
    assert sink.calls == 0
    assert called is False


def test_jsonl_round_trip_flushes_immediately(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    sink = JsonlSink(path)
    sink.emit(make_event())
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["event_type"] == "ANALYSIS_START"
    sink.close()


@pytest.mark.parametrize(
    ("name", "sequence_numbers", "written_lines"),
    [
        ("duplicate", [0, 1, 1], 2),
        ("skipped", [0, 2], 1),
        ("backwards", [0, 1, 0], 2),
    ],
)
def test_jsonl_rejects_invalid_per_analysis_sequences(
    tmp_path: Path,
    name: str,
    sequence_numbers: list[int],
    written_lines: int,
) -> None:
    path = tmp_path / f"{name}.jsonl"
    sink = JsonlSink(path)
    for sequence_number in sequence_numbers:
        sink.emit(make_event(sequence_number=sequence_number))
    assert sink.health.status == "DEGRADED"
    assert sink.health.failures[-1].failure_type == "SequenceError"
    assert len(path.read_text(encoding="utf-8").splitlines()) == written_lines
    sink.close()


def test_jsonl_accepts_independent_analysis_streams(tmp_path: Path) -> None:
    path = tmp_path / "independent.jsonl"
    sink = JsonlSink(path)
    for analysis_id, sequence_number in [("A", 0), ("B", 0), ("A", 1), ("B", 1)]:
        sink.emit(make_event(analysis_id=analysis_id, sequence_number=sequence_number))
    assert sink.health.status == "HEALTHY"
    assert len(path.read_text(encoding="utf-8").splitlines()) == 4
    sink.close()


def test_jsonl_durability_is_limited_to_owner_boundaries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "durable.jsonl"
    calls: list[int] = []
    monkeypatch.setattr("solveur.core.telemetry.jsonl.os.fsync", lambda descriptor: calls.append(descriptor))
    sink = JsonlSink(path, fsync=True)
    sink.emit(make_event(event_type=EventType.ANALYSIS_START))
    sink.emit(make_event(event_type=EventType.CHECKPOINT, sequence_number=1, status=EventStatus.CHECKPOINTED))
    sink.emit(make_event(event_type=EventType.ANALYSIS_END, sequence_number=2, status=EventStatus.COMPLETED))
    sink.close()
    assert DURABILITY_EVENT_TYPES == {"CHECKPOINT", "ANALYSIS_END", "ANALYSIS_FAILED"}
    assert len(calls) == 2


def test_composite_sink_continues_after_partial_failure_and_records_health() -> None:
    class FailingSink:
        sink_identifier = "broken"

        def emit(self, _event: TelemetryEvent) -> None:
            raise OSError("destination unavailable")

    good = MemorySink(sink_identifier="good")
    composite = CompositeSink({"broken": FailingSink(), "good": good})
    composite.emit(make_event())
    assert len(good.events) == 1
    assert composite.health.status == "DEGRADED"
    assert composite.health.failures[0].sink_identifier == "broken"
    assert composite.health.failures[0].failure_type == "OSError"
    assert composite.health.failures[0].sequence_number == 0
    assert composite.health.failures[0].provenance == DIRECT_COMPOSITE_FAILURE


def test_child_open_failure_degrades_composite_and_emitter_without_duplicate_ledger(
    tmp_path: Path,
) -> None:
    broken = JsonlSink(tmp_path / "missing-parent" / "events.jsonl")
    good = MemorySink(sink_identifier="good")
    emitter = TelemetryEmitter("open-failure", "linear_static", "linear_static", [broken, good])

    assert broken.health.status == "DEGRADED"
    assert emitter.sink.health.status == "DEGRADED"
    assert emitter.health.status == "DEGRADED"
    emitter.emit(EventType.ANALYSIS_START, status=EventStatus.STARTED, elapsed_time_s=0.0)
    emitter.emit(EventType.ANALYSIS_END, status=EventStatus.COMPLETED, elapsed_time_s=1.0)
    assert len(good.events) == 2
    child_failures = [
        failure
        for failure in emitter.health.failures
        if failure.provenance == CHILD_SINK_REPORTED_FAILURE
    ]
    assert len(child_failures) == 1
    assert child_failures[0].sink_identifier == "jsonl"


def test_child_write_failure_degrades_emitter_and_sibling_continues(tmp_path: Path) -> None:
    class FailingStream:
        def write(self, _value: str) -> int:
            raise OSError("write unavailable")

        def flush(self) -> None:
            raise OSError("flush unavailable")

        def close(self) -> None:
            return None

    path = tmp_path / "write-failure.jsonl"
    broken = JsonlSink(path)
    stream = broken._stream
    assert stream is not None
    stream.close()
    broken._stream = FailingStream()  # type: ignore[assignment]
    good = MemorySink(sink_identifier="good")
    emitter = TelemetryEmitter("write-failure", "linear_static", "linear_static", [broken, good])

    emitter.emit(EventType.ANALYSIS_START, status=EventStatus.STARTED, elapsed_time_s=0.0)
    assert broken.health.status == "DEGRADED"
    assert emitter.health.status == "DEGRADED"
    assert len(good.events) == 1
    assert path.read_text(encoding="utf-8") == ""


def test_child_memory_capacity_failure_degrades_composite_and_emitter() -> None:
    child = MemorySink(max_events=1)
    emitter = TelemetryEmitter("memory-capacity", "linear_static", "linear_static", child)
    emitter.emit(EventType.ANALYSIS_START, status=EventStatus.STARTED, elapsed_time_s=0.0)
    emitter.emit(EventType.ANALYSIS_END, status=EventStatus.COMPLETED, elapsed_time_s=1.0)
    assert child.health.status == "DEGRADED"
    assert emitter.sink.health.status == "DEGRADED"
    assert emitter.health.status == "DEGRADED"
    assert emitter.health.failures[-1].provenance == CHILD_SINK_REPORTED_FAILURE
    assert len(child.events) == 1


def test_healthy_children_keep_composite_and_emitter_healthy() -> None:
    emitter = TelemetryEmitter("healthy", "linear_static", "linear_static", [MemorySink(), MemorySink()])
    assert emitter.health.status == "HEALTHY"
    emitter.emit(EventType.ANALYSIS_START, status=EventStatus.STARTED, elapsed_time_s=0.0)
    assert emitter.health.status == "HEALTHY"


@pytest.mark.parametrize("operation", ["flush", "close"])
def test_composite_refreshes_child_health_after_lifecycle_operations(operation: str) -> None:
    class LifecycleSink:
        sink_identifier = "lifecycle"

        def __init__(self) -> None:
            self.health = TelemetryHealth(self.sink_identifier)

        def emit(self, _event: TelemetryEvent) -> None:
            return None

        def flush(self) -> None:
            self.health.record_failure(OSError("flush unavailable"))

        def close(self) -> None:
            self.health.record_failure(OSError("close unavailable"))

    child = LifecycleSink()
    composite = CompositeSink((child,))
    getattr(composite, operation)()
    assert child.health.status == "DEGRADED"
    assert composite.health.status == "DEGRADED"
    assert composite.health.failures[-1].provenance == CHILD_SINK_REPORTED_FAILURE


def test_jsonl_open_failure_is_degraded_without_raising(tmp_path: Path) -> None:
    sink = JsonlSink(tmp_path / "missing-parent" / "events.jsonl")
    assert sink.status == "DEGRADED"
    sink.emit(make_event())
    sink.close()


def test_original_solver_exception_is_preserved_when_failure_sink_breaks() -> None:
    class FailingSink:
        def emit(self, _event: TelemetryEvent) -> None:
            raise OSError("telemetry is unavailable")

    emitter = TelemetryEmitter("failure", "linear_static", "linear_static", FailingSink())
    with pytest.raises(RuntimeError, match="sentinel"):
        with preserve_solver_exception(emitter):
            raise RuntimeError("sentinel")


def test_keyboard_interrupt_semantics_are_preserved() -> None:
    emitter = TelemetryEmitter("interrupt", "linear_static", "linear_static")
    with pytest.raises(KeyboardInterrupt):
        with preserve_solver_exception(emitter):
            raise KeyboardInterrupt()


def test_legacy_wp04_adapter_preserves_payload_and_maps_lifecycle() -> None:
    sink = MemorySink()
    adapter = LegacyWP04Adapter(sink, analysis_id="legacy-run")
    payloads = [
        {"event": "ITERATION", "load_step": 0, "iteration": 1, "residual_norm": 2.0},
        {"event": "STEP_ACCEPTED", "load_step": 0},
        {"event": "STEP_FAILED", "load_step": 1, "reason": "retry"},
        {"event": "SOLVE_FAILED", "reason": "non-convergence"},
        {"event": "SOLVE_COMPLETED", "iterations": 3},
    ]
    events = [adapter.emit(payload) for payload in payloads]
    assert [event.sequence_number for event in events] == [0, 1, 2, 3, 4]
    assert [event.event_type.value for event in events] == [
        "NONLINEAR_ITERATION",
        "STEP_ACCEPTED",
        "STEP_REJECTED",
        "ANALYSIS_FAILED",
        "ANALYSIS_END",
    ]
    assert events[0].metadata["legacy_payload"] == payloads[0]
    assert events[0].metrics["residual_norm"] == 2.0


def test_linear_schema_supports_all_declared_backends_and_terminal_fields() -> None:
    start = {
        "backend": "DIRECT",
        "preconditioner": "none",
        "matrix_rows": 10,
        "matrix_columns": 10,
        "matrix_nnz": 30,
        "method": "direct",
        "rtol": 1.0e-8,
        "atol": 1.0e-12,
        "max_iterations": 100,
    }
    for backend in LINEAR_BACKENDS:
        candidate = dict(start, backend=backend)
        assert validate_linear_solver_metrics(candidate, phase="start")["backend"] == backend
    end = {
        "converged": True,
        "status": "COMPLETED",
        "iterations": 4,
        "raw_residual_norm": 1.0e-12,
        "relative_residual_norm": 1.0e-10,
        "backward_error_eta_inf": 1.0e-12,
        "fallback_used": False,
        "solve_time_s": 0.2,
    }
    assert validate_linear_solver_metrics(end, phase="end")["iterations"] == 4
    with pytest.raises(TelemetryValidationError, match="Unsupported linear backend"):
        validate_linear_solver_metrics(dict(start, backend="UNKNOWN"), phase="start")
    with pytest.raises(TelemetryValidationError, match="Missing linear end fields"):
        validate_linear_solver_metrics({"converged": True}, phase="end")


def test_memory_and_timing_names_are_explicit_and_fail_closed() -> None:
    memory = {name: 100 for name in MEMORY_FIELD_NAMES}
    timing = {name: 0.5 for name in TIMING_FIELD_NAMES}
    assert set(validate_memory_metrics(memory)) == MEMORY_FIELD_NAMES
    assert set(validate_timing_metrics(timing)) == TIMING_FIELD_NAMES
    with pytest.raises(TelemetryValidationError, match="non-negative"):
        validate_memory_metrics({"peak_rss_process": -1})
    with pytest.raises(TelemetryValidationError, match="finite"):
        validate_timing_metrics({"assembly_time_s": math.inf})


def test_bounded_memory_sink_records_order_and_health_on_capacity() -> None:
    sink = MemorySink(max_events=1)
    sink.emit(make_event(sequence_number=0))
    sink.emit(make_event(sequence_number=1))
    assert len(sink.events) == 1
    assert sink.health.status == "DEGRADED"
    assert sink.health.failures[0].failure_type == "MemoryError"
