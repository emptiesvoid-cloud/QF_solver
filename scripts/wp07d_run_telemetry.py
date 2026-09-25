"""WP15-compatible live telemetry and heartbeat snapshots for WP07-D runs."""

from __future__ import annotations

import json
import math
import os
import threading
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from solveur.core.nonlinear.telemetry import process_memory_bytes
from solveur.core.telemetry.events import (
    EventStatus,
    EventType,
    MissingValueReason,
    TelemetryEvent,
    missing_value,
)
from solveur.core.telemetry.health import TelemetryHealth
from solveur.core.telemetry.jsonl import JsonlSink
from solveur.core.telemetry.observer import TelemetryEmitter


def _json_safe(value: Any) -> object:
    """Keep telemetry finite and serializable without affecting solver state."""

    if value is None:
        return missing_value(MissingValueReason.NOT_AVAILABLE)
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else missing_value(MissingValueReason.NOT_AVAILABLE)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _json_safe(item())
        except Exception:
            pass
    return str(value)


class _ProgressSink:
    """Persist canonical WP15 events and a separately refreshed live snapshot."""

    sink_identifier = "wp07d-wp15-jsonl"

    def __init__(
        self,
        output: Path,
        *,
        route: str,
        mesh: str,
        heartbeat_interval: float,
    ) -> None:
        if not math.isfinite(heartbeat_interval) or heartbeat_interval <= 0.0:
            raise ValueError("WP07-D heartbeat interval must be finite and positive.")
        self.output = output
        self.events_path = output / "telemetry.jsonl"
        self.progress_path = output / "progress.json"
        self.health = TelemetryHealth(self.sink_identifier)
        output.mkdir(parents=True, exist_ok=True)
        existing = [
            path.name
            for path in (
                self.events_path,
                self.progress_path,
                output / "result.json",
                output / "run.json",
                output / "failure.json",
            )
            if path.exists()
        ]
        if existing:
            raise FileExistsError(f"Refusing to overwrite existing WP07-D run evidence: {existing}")

        self._events = JsonlSink(self.events_path, fsync=True, sink_identifier=self.sink_identifier)
        self.health = self._events.health
        self._started = time.monotonic()
        self._last_event_monotonic = self._started
        self._heartbeat_interval = float(heartbeat_interval)
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._closed = False
        self._state: dict[str, Any] = {
            "schema_version": 1,
            "status": "RUNNING",
            "route": route,
            "mesh": mesh,
            "phase": "INITIALIZING",
            "process_id": os.getpid(),
            "current_step": None,
            "total_steps": None,
            "current_newton_iteration": None,
            "linear_solver": None,
            "latest_residual": None,
            "current_accepted": None,
            "current_rejected": None,
            "telemetry_status": "HEALTHY",
        }
        self._write_progress_locked()
        self._thread = threading.Thread(
            target=self._heartbeat_loop,
            name=f"wp07d-wp15-heartbeat-{route.lower()}-{mesh.lower()}",
            daemon=True,
        )
        self._thread.start()

    def _sample_resources(self) -> dict[str, object]:
        rss_bytes, private_bytes = process_memory_bytes()
        cpu_seconds: float | None = None
        try:
            import psutil

            cpu = psutil.Process(os.getpid()).cpu_times()
            cpu_seconds = float(cpu.user + cpu.system)
        except Exception:
            pass
        return {
            "rss_bytes": rss_bytes,
            "private_memory_bytes": private_bytes,
            "cpu_time_seconds": cpu_seconds,
        }

    def _write_progress_locked(self) -> None:
        self._state["elapsed_seconds"] = time.monotonic() - self._started
        self._state["last_event_age_seconds"] = time.monotonic() - self._last_event_monotonic
        self._state["heartbeat_utc"] = datetime.now(timezone.utc).isoformat()
        self._state.update(self._sample_resources())
        self._state["telemetry_status"] = self._events.status
        temporary = self.progress_path.with_name(f".progress.{os.getpid()}.tmp")
        try:
            serialized = json.dumps(self._state, indent=2, sort_keys=True, allow_nan=False) + "\n"
            with temporary.open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(serialized)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.progress_path)
        except Exception as error:
            self.health.record_failure(error, sink_identifier="wp07d-progress")
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def _heartbeat_loop(self) -> None:
        while not self._stop.wait(self._heartbeat_interval):
            with self._lock:
                if not self._closed:
                    self._write_progress_locked()

    @property
    def last_event(self) -> str | None:
        with self._lock:
            value = self._state.get("last_event")
            return value if isinstance(value, str) else None

    def emit(self, event: TelemetryEvent) -> None:
        """Consume a standard WP15 event and refresh its live progress view."""

        self._events.emit(event)
        with self._lock:
            metrics = dict(event.metrics)
            event_name = event.event_type.value
            self._state.update(
                {
                    "phase": event_name,
                    "last_event": event_name,
                    "last_event_status": event.status.value,
                    "last_event_utc": event.timestamp or datetime.now(timezone.utc).isoformat(),
                }
            )
            step = event.step if event.step is not None else metrics.get("load_step")
            if isinstance(step, int) and not isinstance(step, bool):
                self._state["current_step"] = step
            iteration = event.iteration
            if iteration is None:
                candidate_iteration = metrics.get("newton_iteration", metrics.get("iteration"))
                iteration = candidate_iteration if isinstance(candidate_iteration, int) else None
            if iteration is not None:
                self._state["current_newton_iteration"] = iteration
            residual = next(
                (
                    metrics[key]
                    for key in (
                        "relative_residual",
                        "linear_relative_residual",
                        "relative_residual_norm",
                        "residual_norm",
                    )
                    if key in metrics
                ),
                None,
            )
            if residual is not None:
                self._state["latest_residual"] = _json_safe(residual)
            solver = event.solver_backend or next(
                (
                    metrics[key]
                    for key in ("linear_method", "method", "linear_backend", "backend")
                    if isinstance(metrics.get(key), str)
                ),
                None,
            )
            if solver is not None:
                self._state["linear_solver"] = solver
            if event.status is EventStatus.ACCEPTED:
                self._state["current_accepted"] = True
                self._state["current_rejected"] = False
            elif event.status in {EventStatus.REJECTED, EventStatus.FAILED}:
                self._state["current_accepted"] = False
                self._state["current_rejected"] = True
            elif event.event_type is EventType.STEP_START:
                self._state["current_accepted"] = False
                self._state["current_rejected"] = False
            total_steps = metrics.get("total_steps", metrics.get("load_increments"))
            if isinstance(total_steps, int) and not isinstance(total_steps, bool):
                self._state["total_steps"] = total_steps
            self._last_event_monotonic = time.monotonic()
            self._write_progress_locked()

    def set_progress(self, **values: Any) -> None:
        with self._lock:
            self._state.update({key: _json_safe(value) for key, value in values.items()})
            self._write_progress_locked()

    def flush(self) -> None:
        self._events.flush()

    def close(self) -> None:
        self._stop.set()
        thread = getattr(self, "_thread", None)
        if thread is not None and thread is not threading.current_thread():
            thread.join()
        with self._lock:
            if self._closed:
                return
            self._write_progress_locked()
            self._closed = True
        self._events.close()


class WP07DRunMonitor:
    """Single-writer WP15 telemetry facade for a production or reference run."""

    _NONLINEAR_EVENT_MAP: dict[str, tuple[EventType, EventStatus]] = {
        "ITERATION": (EventType.NONLINEAR_ITERATION, EventStatus.RUNNING),
        "STEP_ACCEPTED": (EventType.STEP_ACCEPTED, EventStatus.ACCEPTED),
        "STEP_FAILED": (EventType.STEP_REJECTED, EventStatus.REJECTED),
        "SOLVE_COMPLETED": (EventType.ANALYSIS_END, EventStatus.COMPLETED),
        "SOLVE_FAILED": (EventType.ANALYSIS_FAILED, EventStatus.FAILED),
    }

    def __init__(
        self,
        output: Path,
        *,
        route: str,
        mesh: str,
        analysis_type: str,
        heartbeat_interval: float = 5.0,
    ) -> None:
        self._progress = _ProgressSink(
            Path(output), route=route, mesh=mesh, heartbeat_interval=heartbeat_interval
        )
        self.emitter = TelemetryEmitter(
            analysis_id=f"WP07D-{route}-{mesh}",
            analysis_type=analysis_type,
            route=route,
            sinks=self._progress,
            metadata={"work_package": "WP07-D", "mesh_level": mesh},
        )
        self._closed = False

    @property
    def telemetry_status(self) -> str:
        return self.emitter.health.status

    def emit(self, event_type: EventType | str, **kwargs: Any) -> None:
        self.emitter.emit(event_type, **kwargs)

    def set_progress(self, **values: Any) -> None:
        self._progress.set_progress(**values)

    def observe_nonlinear(self, event: Mapping[str, object]) -> None:
        """Adapt the solver's established nonlinear observer to the WP15 envelope."""

        raw_name = event.get("event")
        event_name = raw_name if isinstance(raw_name, str) else "ITERATION"
        event_type, status = self._NONLINEAR_EVENT_MAP.get(
            event_name, (EventType.NONLINEAR_ITERATION, EventStatus.RUNNING)
        )
        raw_metrics = {
            str(key): _json_safe(value)
            for key, value in event.items()
            if key
            not in {
                "event",
                "status",
                "load_step",
                "newton_iteration",
                "iteration",
                "target_load_factor",
                "current_load_factor",
            }
        }
        if "status" in event:
            raw_metrics["solver_event_status"] = _json_safe(event["status"])
        step_value = event.get("load_step")
        step = step_value if isinstance(step_value, int) and not isinstance(step_value, bool) else None
        iteration_value = event.get("newton_iteration", event.get("iteration"))
        iteration = (
            iteration_value
            if isinstance(iteration_value, int) and not isinstance(iteration_value, bool)
            else None
        )
        raw_factor = event.get("target_load_factor", event.get("current_load_factor"))
        load_factor = float(raw_factor) if isinstance(raw_factor, (float, int)) else None
        self.emitter.emit(
            event_type,
            status=status,
            metrics=raw_metrics,
            step=step,
            iteration=iteration,
            load_factor=load_factor,
            metadata={"source": "geometric_nonlinear_observer", "source_event": event_name},
        )

    def __enter__(self) -> WP07DRunMonitor:
        self.emit(
            EventType.ANALYSIS_START,
            status=EventStatus.STARTED,
            metrics={"route": self._progress._state["route"], "mesh": self._progress._state["mesh"]},
        )
        return self

    def finish(self, *, status: str, error: BaseException | None = None) -> None:
        if self._closed:
            return
        last_event = self._progress.last_event
        if status == "COMPLETED" and last_event != EventType.ANALYSIS_END.value:
            self.emit(
                EventType.ANALYSIS_END,
                status=EventStatus.COMPLETED,
                metrics={"status": status},
            )
            phase = "TERMINAL"
        elif status != "COMPLETED" and last_event != EventType.ANALYSIS_FAILED.value:
            self.emit(
                EventType.ANALYSIS_FAILED,
                status=EventStatus.FAILED,
                metrics={
                    "error_type": type(error).__name__ if error is not None else "UnknownError",
                    "error_message": str(error) if error is not None else "run ended fail-closed",
                },
            )
            phase = "TERMINAL"
        else:
            phase = "TERMINAL"
        self._progress.set_progress(
            status=status,
            phase=phase,
            error_type=type(error).__name__ if error is not None else None,
            error_message=str(error) if error is not None else None,
        )
        self.emitter.close()
        self._closed = True

    def __exit__(
        self, exc_type: Any, exc: BaseException | None, _traceback: Any
    ) -> Literal[False]:
        self.finish(status="COMPLETED" if exc is None else "FAIL_CLOSED", error=exc)
        return False
