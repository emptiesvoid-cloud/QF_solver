"""External adapter for the existing WP04 nonlinear telemetry payloads."""

from __future__ import annotations

from collections.abc import Mapping

from solveur.core.telemetry.events import EventStatus, EventType, TelemetryEvent, validate_json_value
from solveur.core.telemetry.observer import SequenceGenerator, TelemetrySink


_EVENT_MAP = {
    "ITERATION": (EventType.NONLINEAR_ITERATION, EventStatus.RUNNING),
    "STEP_ACCEPTED": (EventType.STEP_ACCEPTED, EventStatus.ACCEPTED),
    "STEP_FAILED": (EventType.STEP_REJECTED, EventStatus.REJECTED),
    "SOLVE_FAILED": (EventType.ANALYSIS_FAILED, EventStatus.FAILED),
    "SOLVE_COMPLETED": (EventType.ANALYSIS_END, EventStatus.COMPLETED),
}
_METRIC_KEYS = frozenset(
    {
        "residual_norm",
        "correction_norm",
        "line_search_alpha",
        "assembly_time_s",
        "linear_solve_time_s",
        "iteration_wall_time_s",
        "step_wall_time_s",
        "matrix_shape",
        "matrix_nnz",
        "linear_backend",
        "linear_method",
        "krylov_iterations",
        "linear_relative_residual",
        "linear_backward_error_eta_inf",
        "fallback_used",
        "fallback_reason",
        "RSS_bytes",
        "private_or_USS_bytes",
        "iterations",
        "target_load_factor",
        "current_load_factor",
        "error_type",
        "error_code",
        "reason",
        "converged",
    }
)


class LegacyWP04Adapter:
    """Adapt representative legacy events without modifying their producer."""

    def __init__(
        self,
        sink: TelemetrySink,
        *,
        analysis_id: str,
        analysis_type: str = "geometric_nonlinear_static",
        route: str = "geometric_nonlinear_static",
        sequence_generator: SequenceGenerator | None = None,
    ) -> None:
        self.sink = sink
        self.analysis_id = analysis_id
        self.analysis_type = analysis_type
        self.route = route
        self._sequence = sequence_generator or SequenceGenerator()

    def adapt(self, payload: Mapping[str, object]) -> TelemetryEvent:
        """Return a common event while preserving the complete legacy payload."""

        if not isinstance(payload, Mapping):
            raise TypeError("Legacy WP04 telemetry payload must be a mapping.")
        legacy = validate_json_value(dict(payload), allow_null=True, path="legacy_payload")
        if not isinstance(legacy, dict):
            raise TypeError("Legacy WP04 telemetry payload must remain a mapping.")
        legacy_name = legacy.get("event")
        if not isinstance(legacy_name, str) or legacy_name not in _EVENT_MAP:
            raise ValueError(f"Unsupported legacy WP04 event: {legacy_name!r}.")
        event_type, status = _EVENT_MAP[legacy_name]
        metrics = {
            key: legacy[key]
            for key in _METRIC_KEYS
            if key in legacy and legacy[key] is not None
        }
        step = self._first_integer(legacy, "load_step", "step")
        iteration = self._first_integer(legacy, "iteration", "newton_iteration")
        load_factor = self._first_number(legacy, "current_load_factor", "target_load_factor", "load_factor")
        elapsed = self._first_number(legacy, "elapsed_time_s", "iteration_wall_time_s", "step_wall_time_s")
        if elapsed is None:
            elapsed = 0.0
        backend = legacy.get("linear_backend")
        solver_backend = backend if isinstance(backend, str) else None
        message = legacy.get("message")
        return TelemetryEvent(
            schema_version=1,
            event_type=event_type,
            analysis_id=self.analysis_id,
            analysis_type=self.analysis_type,
            route=self.route,
            sequence_number=self._sequence.next(self.analysis_id),
            elapsed_time_s=elapsed,
            status=status,
            metrics=metrics,
            metadata={
                "adapter": "LegacyWP04Adapter",
                "legacy_event_name": legacy_name,
                "legacy_payload": legacy,
            },
            step=step,
            iteration=iteration,
            load_factor=load_factor,
            solver_backend=solver_backend,
            message=message if isinstance(message, str) else None,
        )

    def emit(self, payload: Mapping[str, object]) -> TelemetryEvent:
        """Adapt and deliver one legacy payload to the configured sink."""

        event = self.adapt(payload)
        self.sink.emit(event)
        return event

    @staticmethod
    def _first_integer(payload: Mapping[str, object], *keys: str) -> int | None:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                return value
        return None

    @staticmethod
    def _first_number(payload: Mapping[str, object], *keys: str) -> float | None:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
        return None
