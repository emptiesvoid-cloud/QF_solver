"""Targeted WP15-B phase-1 console and route instrumentation tests."""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.core.router import AnalysisRouter
from solveur.core.telemetry import (
    ConsoleSink,
    EventStatus,
    EventType,
    JsonlSink,
    LegacyWP04Adapter,
    MemorySink,
    TelemetryEmitter,
    TelemetryEvent,
)


def _event(
    sequence_number: int,
    event_type: EventType,
    *,
    analysis_id: str = "console-test",
    status: EventStatus = EventStatus.RUNNING,
    metrics: dict[str, object] | None = None,
) -> TelemetryEvent:
    return TelemetryEvent(
        schema_version=1,
        event_type=event_type,
        analysis_id=analysis_id,
        analysis_type="linear_static",
        route="linear_static",
        sequence_number=sequence_number,
        elapsed_time_s=0.1 * sequence_number,
        status=status,
        metrics=metrics or {"residual": 1.0},
        metadata={"source": "wp15b-test"},
    )


def _tet4_model(analysis: str | dict[str, object]) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.25, "density": 10.0}},
        fixed_dofs=[
            {"node": node, "dofs": ["UX", "UY", "UZ"]}
            for node in (0, 2, 3)
        ],
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
        analysis=analysis,
    )


def test_console_rendering_has_stable_linear_columns_and_missing_values() -> None:
    stream = io.StringIO()
    sink = ConsoleSink(stream=stream, profile="linear_static")
    event = _event(
        0,
        EventType.LINEAR_SOLVE_END,
        status=EventStatus.COMPLETED,
        metrics={
            "dofs": 12,
            "elements": 1,
            "matrix_nnz": 42,
            "assembly_time_s": 0.02,
            "backend": "scipy",
            "iterations": 1,
            "relative_residual_norm": 1.0e-12,
            "solve_time_s": 0.01,
        },
    )
    sink.emit(event)
    line = stream.getvalue()
    assert "analysis=console-test" in line
    assert "event=LINEAR_SOLVE_END" in line
    assert "dofs=12" in line
    assert "nnz=42" in line
    assert "backend=scipy" in line
    assert "private=-" in line


def test_console_lifecycle_events_bypass_display_rate_limiting() -> None:
    stream = io.StringIO()
    sink = ConsoleSink(stream=stream, profile="nonlinear", every_n=10)
    events = [
        _event(0, EventType.ANALYSIS_START, status=EventStatus.STARTED),
        _event(1, EventType.NONLINEAR_ITERATION),
        _event(2, EventType.NONLINEAR_ITERATION),
        _event(3, EventType.STEP_ACCEPTED, status=EventStatus.ACCEPTED),
        _event(4, EventType.ANALYSIS_END, status=EventStatus.COMPLETED),
    ]
    for event in events:
        sink.emit(event)
    output = stream.getvalue()
    assert "event=ANALYSIS_START" in output
    assert "event=STEP_ACCEPTED" in output
    assert "event=ANALYSIS_END" in output
    assert "event=NONLINEAR_ITERATION" not in output
    assert sink.displayed_event_count == 3


def test_console_rate_limiting_does_not_drop_jsonl_events(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "events.jsonl"
    console_output = io.StringIO()
    jsonl = JsonlSink(jsonl_path)
    console = ConsoleSink(stream=console_output, every_n=10)
    emitter = TelemetryEmitter("fanout", "linear_static", "linear_static", [jsonl, console])
    emitter.emit(EventType.ANALYSIS_START, status=EventStatus.STARTED, elapsed_time_s=0.0)
    for _ in range(4):
        emitter.emit(EventType.NONLINEAR_ITERATION, status=EventStatus.RUNNING)
    emitter.emit(EventType.ANALYSIS_END, status=EventStatus.COMPLETED, elapsed_time_s=1.0)
    jsonl.close()
    assert len(jsonl_path.read_text(encoding="utf-8").splitlines()) == 6
    assert console_output.getvalue().count("event=") == 2


def test_linear_static_instrumentation_emits_bounded_lifecycle() -> None:
    sink = MemorySink()
    emitter = TelemetryEmitter("linear-run", "linear_static", "linear_static", sink)
    result = solve_model(_tet4_model("linear_static"), telemetry=emitter)
    event_names = [event.event_type.value for event in sink.events]
    assert result.status == "PASS"
    assert event_names == [
        "ANALYSIS_START",
        "MESH_READY",
        "ASSEMBLY_START",
        "ASSEMBLY_END",
        "LINEAR_SOLVE_START",
        "LINEAR_SOLVE_END",
        "ANALYSIS_END",
    ]
    linear_end = sink.events[5]
    assert linear_end.metrics["matrix_nnz"] > 0
    assert linear_end.metrics["converged"] is True
    assert linear_end.metrics["backward_error_eta_inf"]["reason"] == "NOT_AVAILABLE"


def test_modal_instrumentation_emits_modes_without_fabricated_iterations() -> None:
    sink = MemorySink()
    emitter = TelemetryEmitter("modal-run", "modal", "modal", sink)
    result = solve_model(
        _tet4_model({"type": "modal", "method": "eigh", "modes": 2}),
        telemetry=emitter,
    )
    event_names = [event.event_type.value for event in sink.events]
    assert result.status == "PASS"
    assert event_names[:4] == ["ANALYSIS_START", "MESH_READY", "ASSEMBLY_START", "ASSEMBLY_END"]
    assert event_names.count("MODAL_MODE_FOUND") == 2
    assert event_names[-1] == "ANALYSIS_END"
    mode = next(event for event in sink.events if event.event_type is EventType.MODAL_MODE_FOUND)
    assert mode.metrics["eigenvalue"] > 0.0
    assert mode.metrics["iterations"]["reason"] == "NOT_AVAILABLE"


def test_linear_and_modal_outputs_are_invariant_with_telemetry() -> None:
    static_off = solve_model(_tet4_model("linear_static"))
    static_sink = MemorySink()
    static_on = solve_model(
        _tet4_model("linear_static"),
        telemetry=TelemetryEmitter("static-on", "linear_static", "linear_static", static_sink),
    )
    np.testing.assert_array_equal(static_off.displacements, static_on.displacements)
    assert (static_off.status, static_off.method, static_off.node_count) == (
        static_on.status,
        static_on.method,
        static_on.node_count,
    )

    modal_off = solve_model(_tet4_model({"type": "modal", "method": "eigh", "modes": 2}))
    modal_sink = MemorySink()
    modal_on = solve_model(
        _tet4_model({"type": "modal", "method": "eigh", "modes": 2}),
        telemetry=TelemetryEmitter("modal-on", "modal", "modal", modal_sink),
    )
    np.testing.assert_array_equal(modal_off.eigenvalues, modal_on.eigenvalues)
    np.testing.assert_array_equal(modal_off.frequencies_hz, modal_on.frequencies_hz)


def test_telemetry_sink_failures_do_not_change_route_result_or_sibling_delivery() -> None:
    class BrokenTextStream:
        def write(self, _value: str) -> int:
            raise OSError("console unavailable")

        def flush(self) -> None:
            raise OSError("console unavailable")

    good = MemorySink(sink_identifier="good")
    console = ConsoleSink(stream=BrokenTextStream())
    emitter = TelemetryEmitter("broken-console", "linear_static", "linear_static", [console, good])
    result = solve_model(_tet4_model("linear_static"), telemetry=emitter)
    reference = solve_model(_tet4_model("linear_static"))
    np.testing.assert_array_equal(result.displacements, reference.displacements)
    assert len(good.events) == 7
    assert emitter.health.status == "DEGRADED"


def test_jsonl_and_console_failure_isolation_keeps_memory_sibling(
    tmp_path: Path,
) -> None:
    console = ConsoleSink(stream=io.StringIO())
    jsonl = JsonlSink(tmp_path / "missing-parent" / "events.jsonl")
    good = MemorySink(sink_identifier="good")
    emitter = TelemetryEmitter("broken-jsonl", "linear_static", "linear_static", [jsonl, console, good])
    solve_model(_tet4_model("linear_static"), telemetry=emitter)
    assert len(good.events) == 7
    assert emitter.health.status == "DEGRADED"


def test_legacy_wp04_payloads_render_through_console_sink() -> None:
    stream = io.StringIO()
    adapter = LegacyWP04Adapter(ConsoleSink(stream=stream, profile="nonlinear"), analysis_id="legacy")
    adapter.emit({"event": "ITERATION", "load_step": 0, "iteration": 1, "residual_norm": 2.0})
    adapter.emit({"event": "STEP_ACCEPTED", "load_step": 0})
    adapter.emit({"event": "STEP_FAILED", "load_step": 1, "reason": "retry"})
    adapter.emit({"event": "SOLVE_FAILED", "reason": "non-convergence"})
    adapter.emit({"event": "SOLVE_COMPLETED", "iterations": 3})
    output = stream.getvalue()
    assert "event=NONLINEAR_ITERATION" in output
    assert "event=STEP_REJECTED" in output
    assert "event=ANALYSIS_FAILED" in output
    assert "event=ANALYSIS_END" in output


def test_route_failure_preserves_original_exception_and_emits_analysis_failed() -> None:
    sink = MemorySink()
    emitter = TelemetryEmitter("failed-route", "linear_static", "linear_static", sink)
    model = _tet4_model("linear_static")
    model.nodes[0, 0] = np.nan
    with pytest.raises(Exception):
        solve_model(model, telemetry=emitter)
    assert sink.events[-1].event_type is EventType.ANALYSIS_FAILED
    assert sink.events[-1].status is EventStatus.FAILED
    assert json.loads(sink.events[-1].to_json())["event_type"] == "ANALYSIS_FAILED"


@pytest.mark.parametrize(
    ("analysis", "actual_route"),
    [
        ("linear_static", "linear_static"),
        ({"type": "modal", "method": "eigh", "modes": 2}, "modal"),
    ],
)
def test_router_binds_canonical_provenance_to_actual_route(
    analysis: str | dict[str, object],
    actual_route: str,
) -> None:
    sink = MemorySink()
    caller_context = "modal" if actual_route == "linear_static" else "linear_static"
    emitter = TelemetryEmitter("provenance", caller_context, caller_context, sink)
    result = solve_model(_tet4_model(analysis), telemetry=emitter)
    assert result.status == "PASS"
    assert sink.events
    assert all(event.analysis_type == actual_route for event in sink.events)
    assert all(event.route == actual_route for event in sink.events)
    binding = sink.events[0].metadata["telemetry_route_binding"]
    assert binding["caller_context_mismatch"] is True
    assert binding["actual_route"] == actual_route


@pytest.mark.parametrize(
    "analysis",
    [
        "linear_static",
        {"type": "modal", "method": "eigh", "modes": 2},
    ],
)
def test_instrumented_preflight_failure_has_one_start_and_one_failure(
    analysis: str | dict[str, object],
) -> None:
    sink = MemorySink()
    emitter = TelemetryEmitter("preflight-failure", "wrong", "wrong", sink)
    model = _tet4_model(analysis)
    model.nodes[0, 0] = np.nan
    with pytest.raises(Exception) as caught:
        solve_model(model, telemetry=emitter)
    assert caught.value.__class__.__name__ == "MeshValidationError"
    event_names = [event.event_type.value for event in sink.events]
    assert event_names == ["ANALYSIS_START", "ANALYSIS_FAILED"]
    assert sink.events[0].status is EventStatus.STARTED
    assert sink.events[1].status is EventStatus.FAILED
    assert sink.events[1].metadata["telemetry_route_binding"]["actual_route"] in {
        "linear_static",
        "modal",
    }


@pytest.mark.parametrize("route", ["geometric_nonlinear_static", "nonlinear_static"])
def test_non_instrumented_routes_receive_no_phase1_generic_events(route: str) -> None:
    sink = MemorySink()
    emitter = TelemetryEmitter("not-instrumented", "linear_static", "linear_static", sink)
    model = _tet4_model(route)
    router = AnalysisRouter()
    with patch.object(router, "_solve", return_value=object()):
        router.solve(model, telemetry=emitter)
    assert sink.events == ()


def test_stream_context_cannot_change_after_first_event() -> None:
    emitter = TelemetryEmitter("context", "linear_static", "linear_static", MemorySink())
    emitter.emit(EventType.ANALYSIS_START, status=EventStatus.STARTED)
    bound = emitter.bind_route("modal", "modal")
    with pytest.raises(ValueError, match="context cannot change"):
        bound.emit(EventType.ANALYSIS_END, status=EventStatus.COMPLETED)
