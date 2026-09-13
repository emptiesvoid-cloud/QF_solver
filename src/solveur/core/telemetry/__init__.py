"""Generic, route-neutral telemetry infrastructure for WP15-A."""

from solveur.core.telemetry.events import (
    SCHEMA_VERSION,
    EventStatus,
    EventType,
    MissingValueReason,
    SequenceError,
    TelemetryEvent,
    TelemetryValidationError,
    missing_value,
    validate_json_value,
)
from solveur.core.telemetry.health import HealthState, SinkFailure, TelemetryHealth
from solveur.core.telemetry.jsonl import DURABILITY_EVENT_TYPES, JsonlSink
from solveur.core.telemetry.legacy import LegacyWP04Adapter
from solveur.core.telemetry.observer import (
    CompositeSink,
    MemorySink,
    SequenceGenerator,
    SequenceValidator,
    TelemetryEmitter,
    TelemetrySink,
    emit_analysis_failed_best_effort,
    preserve_solver_exception,
)
from solveur.core.telemetry.schemas import (
    LINEAR_BACKENDS,
    LINEAR_SOLVER_FIELDS,
    MEMORY_FIELD_NAMES,
    TIMING_FIELD_NAMES,
    validate_linear_solve_metrics,
    validate_linear_solver_metrics,
    validate_memory_metrics,
    validate_timing_metrics,
)

__all__ = [
    "SCHEMA_VERSION",
    "DURABILITY_EVENT_TYPES",
    "EventStatus",
    "EventType",
    "MissingValueReason",
    "SequenceError",
    "TelemetryEvent",
    "TelemetryValidationError",
    "missing_value",
    "validate_json_value",
    "HealthState",
    "SinkFailure",
    "TelemetryHealth",
    "JsonlSink",
    "LegacyWP04Adapter",
    "CompositeSink",
    "MemorySink",
    "SequenceGenerator",
    "SequenceValidator",
    "TelemetryEmitter",
    "TelemetrySink",
    "emit_analysis_failed_best_effort",
    "preserve_solver_exception",
    "LINEAR_BACKENDS",
    "LINEAR_SOLVER_FIELDS",
    "MEMORY_FIELD_NAMES",
    "TIMING_FIELD_NAMES",
    "validate_linear_solve_metrics",
    "validate_linear_solver_metrics",
    "validate_memory_metrics",
    "validate_timing_metrics",
]
