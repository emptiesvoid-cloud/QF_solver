"""Backend-neutral text console sink for generic telemetry events."""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Callable, Mapping
from threading import RLock
from time import monotonic
from typing import TextIO, cast

from solveur.core.telemetry.events import EventStatus, EventType, TelemetryEvent
from solveur.core.telemetry.health import TelemetryHealth


LIFECYCLE_EVENTS = frozenset(
    {
        EventType.ANALYSIS_START.value,
        EventType.ANALYSIS_END.value,
        EventType.ANALYSIS_FAILED.value,
        EventType.STEP_ACCEPTED.value,
        EventType.STEP_REJECTED.value,
        EventType.CHECKPOINT.value,
    }
)

_LINEAR_COLUMNS = (
    ("dofs", "dofs"),
    ("elements", "elements"),
    ("nnz", "matrix_nnz", "nnz"),
    ("assembly_s", "assembly_time_s", "assembly_seconds"),
    ("backend", "backend", "solver_backend"),
    ("iterations", "iterations"),
    ("residual", "relative_residual_norm", "residual_norm", "raw_residual_norm"),
    ("solve_s", "linear_solve_time_s", "solve_time_s", "linear_solve_seconds"),
    ("rss", "peak_rss_process", "telemetry_sample_peak_rss"),
    ("private", "peak_private_or_uss_process", "telemetry_sample_peak_private"),
)

_MODAL_COLUMNS = (
    ("dofs", "dofs"),
    ("requested_modes", "requested_modes", "mode_count_requested"),
    ("mode", "mode_index", "index"),
    ("eigenvalue", "eigenvalue"),
    ("frequency_hz", "frequency_hz", "frequency"),
    ("eigen_residual", "eigen_residual", "relative_residual_norm"),
    ("iterations", "iterations"),
    ("backend", "backend", "solver_backend"),
    ("elapsed", "elapsed_time_s"),
)

_NONLINEAR_COLUMNS = (
    ("step", "step"),
    ("iteration", "iteration"),
    ("load_factor", "load_factor"),
    ("residual", "relative_residual", "relative_residual_norm", "residual_norm"),
    ("correction", "correction_norm", "correction"),
    ("alpha", "line_search_alpha", "alpha"),
    ("backend", "backend", "solver_backend"),
    ("krylov", "krylov_iterations", "linear_iterations"),
    ("eta", "backward_error_eta_inf", "eta"),
    ("solve_s", "linear_solve_time_s", "solve_time_s"),
    ("rss", "peak_rss_process", "telemetry_sample_peak_rss"),
    ("elapsed", "elapsed_time_s"),
)


class ConsoleSink:
    """Render validated telemetry as concise deterministic text.

    Rate limiting applies only to display. The sink never alters the event
    delivered to sibling sinks or the canonical JSONL stream.
    """

    def __init__(
        self,
        *,
        stream: TextIO | None = None,
        profile: str = "generic",
        every_n: int = 1,
        min_interval_s: float | None = None,
        clock: Callable[[], float] = monotonic,
        sink_identifier: str = "console",
        health: TelemetryHealth | None = None,
    ) -> None:
        if not isinstance(every_n, int) or isinstance(every_n, bool) or every_n <= 0:
            raise ValueError("every_n must be a positive integer.")
        if min_interval_s is not None:
            if isinstance(min_interval_s, bool):
                raise ValueError("min_interval_s must be finite and non-negative.")
            min_interval_s = float(min_interval_s)
            if not math.isfinite(min_interval_s) or min_interval_s < 0.0:
                raise ValueError("min_interval_s must be finite and non-negative.")
        self.stream = stream if stream is not None else sys.stdout
        self.profile = str(profile).strip().lower()
        self.every_n = every_n
        self.min_interval_s = min_interval_s
        self._clock = clock
        self.sink_identifier = sink_identifier
        self.health = health or TelemetryHealth(sink_identifier)
        self._event_count = 0
        self._displayed_event_count = 0
        self._last_display_time: float | None = None
        self._closed = False
        self._lock = RLock()

    @property
    def status(self) -> str:
        return self.health.status

    @property
    def displayed_event_count(self) -> int:
        with self._lock:
            return self._displayed_event_count

    def emit(self, event: TelemetryEvent) -> None:
        with self._lock:
            if self._closed:
                return
            try:
                if not isinstance(event, TelemetryEvent):
                    event = TelemetryEvent.from_mapping(event)
                self._event_count += 1
                event_name = cast(EventType, event.event_type).value
                if not self._should_display(event_name):
                    return
                line = self.render(event)
                self.stream.write(line + "\n")
                self.stream.flush()
                self._displayed_event_count += 1
            except Exception as error:
                self.health.record_failure(error, event=event if isinstance(event, TelemetryEvent) else None)

    def _should_display(self, event_name: str) -> bool:
        if event_name in LIFECYCLE_EVENTS:
            return True
        if (self._event_count - 1) % self.every_n != 0:
            return False
        if self.min_interval_s is None:
            return True
        now = self._clock()
        if self._last_display_time is not None and now - self._last_display_time < self.min_interval_s:
            return False
        self._last_display_time = now
        return True

    def render(self, event: TelemetryEvent) -> str:
        """Return one stable, single-line representation without I/O."""

        event_name = cast(EventType, event.event_type).value
        status = cast(EventStatus, event.status).value
        columns = self._columns_for_profile()
        fields = [
            f"analysis={event.analysis_id}",
            f"event={event_name}",
            f"route={event.route}",
            f"status={status}",
        ]
        metrics = event.metrics
        for label, *keys in columns:
            value = _first_present(metrics, event, keys)
            fields.append(f"{label}={_display_value(value)}")
        if event.message:
            fields.append(f"message={event.message}")
        return " ".join(fields)

    def _columns_for_profile(self) -> tuple[tuple[str, ...], ...]:
        if self.profile == "linear_static":
            return _LINEAR_COLUMNS
        if self.profile == "modal":
            return _MODAL_COLUMNS
        if self.profile in {"nonlinear", "nonlinear_static", "geometric_nonlinear_static"}:
            return _NONLINEAR_COLUMNS
        return (("elapsed", "elapsed_time_s"),)

    def flush(self) -> None:
        with self._lock:
            if self._closed:
                return
            try:
                self.stream.flush()
            except Exception as error:
                self.health.record_failure(error)

    def close(self) -> None:
        with self._lock:
            self._closed = True


def _first_present(metrics: Mapping[str, object], event: TelemetryEvent, keys: list[str]) -> object:
    for key in keys:
        if key in metrics:
            return metrics[key]
        if key == "solver_backend" and event.solver_backend is not None:
            return event.solver_backend
        if key == "elapsed_time_s":
            return event.elapsed_time_s
        if key == "step" and event.step is not None:
            return event.step
        if key == "iteration" and event.iteration is not None:
            return event.iteration
        if key == "load_factor" and event.load_factor is not None:
            return event.load_factor
    return None


def _display_value(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, Mapping) and "value" in value:
        if value.get("value") is None:
            return f"NA({value.get('reason', 'MISSING')})"
        return _display_value(value.get("value"))
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (int, str)):
        return str(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
