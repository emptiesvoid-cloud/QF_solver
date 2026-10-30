"""Synthetic checks for diagnostic tracing; no FEM model or solver is run."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.wp12_vv3d_adaptive import case_harness, performance_trace


def _events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_trace_records_monotonic_stages_and_sampled_peak(tmp_path, monkeypatch) -> None:
    path = tmp_path / "trace.jsonl"
    trace = performance_trace.PerformanceTrace(path, case_id="VV3D-TET4-L3", attempt_id="synthetic-attempt")
    samples = iter([100, 250, 150, 125])
    monkeypatch.setattr(trace, "_memory", lambda: next(samples))
    with trace:
        with performance_trace.stage("body_load_order_8"):
            assert performance_trace.current() is trace
    events = _events(path)
    assert [(event["stage"], event["state"]) for event in events] == [
        ("trace", "START"), ("body_load_order_8", "START"),
        ("body_load_order_8", "END"), ("trace", "END"),
    ]
    assert [event["monotonic_seconds"] for event in events] == sorted(event["monotonic_seconds"] for event in events)
    assert events[-1]["peak_rss_bytes_sampled"] == 250
    assert events[2]["duration_seconds"] >= 0
    assert performance_trace.current() is None
    with pytest.raises(FileExistsError):
        with performance_trace.PerformanceTrace(path, case_id="VV3D-TET4-L3", attempt_id="other"):
            pass


def test_interrupted_process_retains_started_stage_and_heartbeat(tmp_path) -> None:
    trace_path = tmp_path / "interrupted.jsonl"
    code = (
        "import sys,time; from pathlib import Path; "
        "from experiments.wp12_vv3d_adaptive.performance_trace import PerformanceTrace; "
        "t=PerformanceTrace(Path(sys.argv[1]),case_id='VV3D-TET4-L3',attempt_id='synthetic',sample_seconds=.05); "
        "t.__enter__(); s=t.stage('body_load_order_12'); s.__enter__(); "
        "print('READY',flush=True); time.sleep(60)"
    )
    process = subprocess.Popen([sys.executable, "-B", "-c", code, str(trace_path)],
                               cwd=Path(__file__).resolve().parents[2],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert process.stdout is not None and process.stdout.readline().strip() == "READY"
        import time

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not any(e["stage"] == "heartbeat" for e in _events(trace_path)):
            time.sleep(0.02)
        process.terminate()
        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
    events = _events(trace_path)
    assert any(e["stage"] == "body_load_order_12" and e["state"] == "START" for e in events)
    assert any(e["stage"] == "heartbeat" and e["active_stages"] == ["body_load_order_12"] for e in events)
    assert not any(e["stage"] == "body_load_order_12" and e["state"] == "END" for e in events)


def test_sampling_failure_is_reported(tmp_path, monkeypatch) -> None:
    import time

    trace = performance_trace.PerformanceTrace(tmp_path / "failure.jsonl", case_id="VV3D-TET4-L3",
                                               attempt_id="synthetic", sample_seconds=0.01)
    original = trace.event

    def fail_heartbeat(stage, state, **fields):
        if stage == "heartbeat":
            raise OSError("synthetic failure")
        return original(stage, state, **fields)

    monkeypatch.setattr(trace, "event", fail_heartbeat)
    with pytest.raises(RuntimeError, match="sampling failed"):
        with trace:
            deadline = time.monotonic() + 5
            while trace._sampler_error is None and time.monotonic() < deadline:
                time.sleep(0.01)
    assert trace._sampler_error is not None


def test_solver_hooks_observe_fake_matrices_and_restore_methods(tmp_path, monkeypatch) -> None:
    from solveur.core.assembly.assembler import GlobalAssembler
    from solveur.core.constraints import ConstraintReduction
    from solveur.core.solvers.linear import LinearSystemSolver

    matrix = SimpleNamespace(shape=(7, 7), nnz=19, dtype="float64")
    reduced = SimpleNamespace(matrix=matrix, transform=matrix)
    info = SimpleNamespace(method="direct", backend="scipy")
    monkeypatch.setattr(GlobalAssembler, "assemble_stiffness", lambda *args, **kwargs: matrix)
    monkeypatch.setattr(ConstraintReduction, "from_system", classmethod(lambda cls, *args, **kwargs: reduced))
    monkeypatch.setattr(LinearSystemSolver, "solve", lambda *args, **kwargs: ("unchanged", info))
    originals = [GlobalAssembler.__dict__["assemble_stiffness"], ConstraintReduction.__dict__["from_system"],
                 LinearSystemSolver.__dict__["solve"]]
    path = tmp_path / "trace.jsonl"
    with performance_trace.PerformanceTrace(path, case_id="VV3D-TET4-L3", attempt_id="synthetic") as trace:
        with performance_trace.instrument_static_solver(trace):
            assert GlobalAssembler().assemble_stiffness(None, None) is matrix
            assert ConstraintReduction.from_system(None, None, None, None, None) is reduced
            assert LinearSystemSolver().solve(matrix, None, method="direct") == ("unchanged", info)
    assert [GlobalAssembler.__dict__["assemble_stiffness"], ConstraintReduction.__dict__["from_system"],
            LinearSystemSolver.__dict__["solve"]] == originals
    events = _events(path)
    matrices = [e["matrix"] for e in events if e["state"] == "MATRIX"]
    assert len(matrices) == 2 and all(m["shape"] == [7, 7] and m["nnz"] == 19 for m in matrices)
    assert any(e["state"] == "SOLVER" and e["method"] == "direct" and e["backend"] == "scipy" for e in events)


def test_registered_case_tracing_is_opt_in_and_preserves_result(tmp_path, monkeypatch) -> None:
    context = {"attempt_id": "synthetic-attempt", "evidence_root": str(tmp_path),
               "scientific_fingerprint": "a" * 64, "controller_fingerprint": "b" * 64,
               "manifest_sha256": "c" * 64}
    result = {"payload": {"synthetic": True}}
    monkeypatch.setattr(case_harness, "require_authorized_execution", lambda case: context)
    monkeypatch.setattr(case_harness, "run_prospective_case", lambda *args, **kwargs: result)
    monkeypatch.setattr(case_harness, "assert_prospective_acceptance", lambda payload: None)
    monkeypatch.delenv("QF_VV3D_PERFORMANCE_TRACE", raising=False)
    assert case_harness.run_registered_case("VV3D-TET4-L3") is result
    assert not list(tmp_path.iterdir())
    monkeypatch.setenv("QF_VV3D_PERFORMANCE_TRACE", "1")
    assert case_harness.run_registered_case("VV3D-TET4-L3") is result
    trace = tmp_path / "diagnostic-timings/VV3D-TET4-L3/synthetic-attempt/stages.jsonl"
    assert any(e["stage"] == "acceptance" and e["state"] == "END" for e in _events(trace))
    with pytest.raises(PermissionError):
        case_harness.run_registered_case("VV3D-TET4-L2")


def test_instrumented_worker_emits_stages_with_fake_fem_hooks(tmp_path, monkeypatch) -> None:
    """Reuse the existing fully mocked worker fixture; no scientific computation occurs."""
    import importlib.util

    source = Path(__file__).with_name("test_wp12_vv3d_adaptive_prepared.py")
    spec = importlib.util.spec_from_file_location("vv3d_synthetic_worker_test", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    trace_path = tmp_path / "worker-trace.jsonl"
    with performance_trace.PerformanceTrace(trace_path, case_id="VV3D-TET4-L3", attempt_id="synthetic"):
        module.test_synthetic_adaptive_worker_persists_sidecar_with_faked_solver_and_load_hooks(tmp_path, monkeypatch)
    ended = {event["stage"] for event in _events(trace_path) if event["state"] == "END"}
    assert {"imports", "model_preparation", "body_load_order_8", "body_load_order_12",
            "finite_element_model", "solve_model", "stress_recovery", "extract_displacements",
            "independent_errors_order_8", "independent_errors_order_12", "postprocess_metrics",
            "criteria_evaluation", "serialize_and_archive"}.issubset(ended)
