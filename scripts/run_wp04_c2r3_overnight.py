"""Run the owner-frozen WP04-C2R3 MINRES/Jacobi M2 then M3 campaign.

This is qualification orchestration, not a production solver path.  Each
mesh is executed in a fresh child process so that the M2 allocation is
released before M3 starts.  Numerical failures are recorded and do not stop
the authorized M3 attempt.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
from time import perf_counter, process_time
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_9" / "c2r3"
FORENSICS_ROOT = Path(tempfile.gettempdir()) / "qf_solver_029_c2r3_forensics"
CASES = {"C2-M2": (48, 24, 24), "C2-M3": (64, 32, 32)}
INCREMENTS = 12
NEWTON_TOLERANCE = 1.0e-10
MAX_NEWTON_ITERATIONS = 40
MINRES_RTOL = 1.0e-11
MINRES_ATOL = 1.0e-14
MINRES_MAXITER = 10_000
LINEAR_BACKWARD_ERROR_TOLERANCE = 1.0e-10


def _jsonable(value: Any) -> Any:
    """Convert small diagnostics to strict JSON without serializing arrays."""

    if value is None or isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and not np.isfinite(value):
            return None
        return value
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _percentile(values: Sequence[int | float], percentile: float) -> float | None:
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=float), percentile, method="linear"))


class _PeakMemorySampler:
    def __init__(self) -> None:
        self.stop = threading.Event()
        self.thread: threading.Thread | None = None
        self.peak_rss: int | None = None
        self.peak_private: int | None = None

    def _sample(self) -> None:
        from solveur.core.nonlinear.telemetry import process_memory_bytes

        while not self.stop.is_set():
            rss, private = process_memory_bytes()
            if rss is not None:
                self.peak_rss = max(self.peak_rss or 0, rss)
            if private is not None:
                self.peak_private = max(self.peak_private or 0, private)
            self.stop.wait(0.10)

    def __enter__(self) -> "_PeakMemorySampler":
        self.thread = threading.Thread(target=self._sample, name="c2r3-memory", daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop.set()
        if self.thread is not None:
            self.thread.join(timeout=2.0)


class _FailureSystemCapture:
    """Hold one failed sparse system until the engine emits its step context."""

    def __init__(self, case: str) -> None:
        self.case = case
        self.pending: tuple[Any, np.ndarray, dict[str, Any]] | None = None
        self.written: dict[str, Any] | None = None

    def hold(self, matrix: Any, rhs: np.ndarray, diagnostics: Mapping[str, Any]) -> None:
        if self.pending is None and self.written is None:
            self.pending = (matrix.copy(), np.array(rhs, dtype=float, copy=True), dict(diagnostics))

    def flush(self, context: Mapping[str, Any]) -> dict[str, Any] | None:
        if self.pending is None or self.written is not None:
            return self.written
        matrix, rhs, diagnostics = self.pending
        FORENSICS_ROOT.mkdir(parents=True, exist_ok=True)
        stem = self.case.lower().replace("-", "_")
        step = context.get("load_step", diagnostics.get("step", "unknown"))
        iteration = context.get("newton_iteration", diagnostics.get("iterations", "unknown"))
        target = FORENSICS_ROOT / f"{stem}_failing_system_step{step}_iter{iteration}.npz"
        np.savez_compressed(
            target,
            data=np.asarray(matrix.data),
            indices=np.asarray(matrix.indices),
            indptr=np.asarray(matrix.indptr),
            shape=np.asarray(matrix.shape, dtype=np.int64),
            rhs=rhs,
        )
        self.written = {
            "case": self.case,
            "load_step": step,
            "newton_iteration": iteration,
            "path": str(target),
            "size_bytes": target.stat().st_size,
            "sha256": _sha256(target),
            "shape": [int(item) for item in matrix.shape],
            "nnz": int(matrix.nnz),
            "linear_method": diagnostics.get("linear_method", "minres"),
            "linear_backend": diagnostics.get("linear_backend"),
            "failure_diagnostics": dict(diagnostics),
        }
        self.pending = None
        return self.written


def _aggregate_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    iteration_events = [event for event in events if event.get("event") == "ITERATION"]
    linear_events = [
        event
        for event in iteration_events
        if event.get("linear_method") is not None
        or event.get("status") == "LINEAR_FAILED"
    ]
    krylov = [
        int(event["krylov_iterations"])
        for event in linear_events
        if isinstance(event.get("krylov_iterations"), (int, float))
    ]
    solve_times = [
        float(event["linear_solve_time_s"])
        for event in linear_events
        if isinstance(event.get("linear_solve_time_s"), (int, float))
    ]
    etas = [
        float(event["linear_backward_error_eta_inf"])
        for event in linear_events
        if isinstance(event.get("linear_backward_error_eta_inf"), (int, float))
        and np.isfinite(float(event["linear_backward_error_eta_inf"]))
    ]
    raw_residuals = [
        float(event["linear_relative_residual"])
        for event in linear_events
        if isinstance(event.get("linear_relative_residual"), (int, float))
        and np.isfinite(float(event["linear_relative_residual"]))
    ]
    accepted = [event for event in events if event.get("event") == "STEP_ACCEPTED"]
    return {
        "accepted_step_count": len(accepted),
        "accepted_steps": [event.get("load_step") for event in accepted],
        "accepted_load_factors": [event.get("target_load_factor") for event in accepted],
        "total_newton_iterations": len(iteration_events),
        "total_linear_solves": len(linear_events),
        "krylov_iterations": {
            "min": min(krylov) if krylov else None,
            "median": float(np.median(krylov)) if krylov else None,
            "p95": _percentile(krylov, 95.0),
            "max": max(krylov) if krylov else None,
            "total": int(sum(krylov)),
        },
        "linear_solve_time_s": {
            "total": float(sum(solve_times)),
            "median": float(np.median(solve_times)) if solve_times else None,
            "p95": _percentile(solve_times, 95.0),
            "max": max(solve_times) if solve_times else None,
        },
        "max_eta_inf": max(etas) if etas else None,
        "max_raw_linear_relative_residual": max(raw_residuals) if raw_residuals else None,
        "fallback_count": sum(1 for event in linear_events if bool(event.get("fallback_used"))),
        "line_search_alpha": [event.get("line_search_alpha") for event in iteration_events],
        "linear_methods": sorted({str(event.get("linear_method")) for event in linear_events}),
    }


def _child(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(SRC))
    sys.path.insert(0, str(ROOT))

    from solveur.core.analyses.geometric_nonlinear import _newton_dead_load
    from solveur.core.errors import NumericalConvergenceError
    from solveur.core.nonlinear.linear_solver import NonlinearLinearSolverAdapter
    from solveur.core.nonlinear.robustness import NonlinearRobustnessOptions
    from solveur.core.nonlinear.state import NonlinearState
    from solveur.core.nonlinear.telemetry import JsonlNonlinearTelemetry, process_memory_bytes
    from tests.verification.test_wp04_c2_tet4_requalification import _case, _equilibrium, _observe, _mesh_metrics

    case_name = str(args.case)
    slug = case_name.split("-")[-1].lower()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    status_path = output / f"{slug}_status.json"
    result_path = output / f"{slug}_result.json"
    telemetry_path = output / f"{slug}_telemetry.jsonl"
    started_wall = perf_counter()
    started_cpu = process_time()
    started_timestamp = datetime.now(timezone.utc).isoformat()
    status: dict[str, Any] = {
        "case": case_name,
        "mesh": list(CASES[case_name]),
        "status": "RUNNING",
        "pid": os.getpid(),
        "load_step": 0,
        "Newton_iteration": 0,
        "latest_eta_inf": None,
        "latest_Krylov_iterations": None,
        "latest_linear_solve_time": None,
        "latest_line_search_alpha": None,
        "RSS": None,
        "private_memory": None,
        "elapsed_wall_time": 0.0,
        "last_update_timestamp": started_timestamp,
        "started_timestamp": started_timestamp,
    }
    _write_json(status_path, status)

    events: list[dict[str, Any]] = []
    accepted_records: list[dict[str, Any]] = []
    latest_state: NonlinearState | None = None
    capture = _FailureSystemCapture(case_name)
    original_solve = NonlinearLinearSolverAdapter.solve

    def wrapped_solve(self: Any, matrix: Any, rhs: np.ndarray, **kwargs: Any) -> Any:
        try:
            return original_solve(self, matrix, rhs, **kwargs)
        except NumericalConvergenceError as exc:
            capture.hold(matrix, rhs, exc.diagnostics)
            raise

    NonlinearLinearSolverAdapter.solve = wrapped_solve

    def observe(event: Mapping[str, object]) -> None:
        enriched = dict(event)
        enriched.update({"case": case_name, "mesh": list(CASES[case_name])})
        events.append(_jsonable(enriched))
        telemetry(enriched)
        rss, private = process_memory_bytes()
        status.update(
            {
                "load_step": enriched.get("load_step", status["load_step"]),
                "Newton_iteration": enriched.get("newton_iteration", status["Newton_iteration"]),
                "latest_eta_inf": enriched.get("linear_backward_error_eta_inf", status["latest_eta_inf"]),
                "latest_Krylov_iterations": enriched.get("krylov_iterations", status["latest_Krylov_iterations"]),
                "latest_linear_solve_time": enriched.get("linear_solve_time_s", status["latest_linear_solve_time"]),
                "latest_line_search_alpha": enriched.get("line_search_alpha", status["latest_line_search_alpha"]),
                "RSS": rss,
                "private_memory": private,
                "elapsed_wall_time": perf_counter() - started_wall,
                "last_update_timestamp": datetime.now(timezone.utc).isoformat(),
                "last_event_status": enriched.get("status"),
            }
        )
        if enriched.get("status") == "LINEAR_FAILED":
            capture.flush(enriched)
        _write_json(status_path, status)

    failure: dict[str, Any] | None = None
    outcome = "COMPLETED"
    peak_rss: int | None = None
    peak_private: int | None = None
    try:
        options = NonlinearRobustnessOptions(
            linear_solver="minres",
            linear_preconditioner="jacobi",
            linear_rtol=MINRES_RTOL,
            linear_atol=MINRES_ATOL,
            linear_maxiter=MINRES_MAXITER,
            linear_residual_tolerance=LINEAR_BACKWARD_ERROR_TOLERANCE,
            linear_backward_error_tolerance=LINEAR_BACKWARD_ERROR_TOLERANCE,
            linear_direct_fallback=False,
            line_search="off",
        )
        options.validate()
        case = _case(case_name)

        def accepted(_step: int, state: NonlinearState) -> None:
            nonlocal latest_state
            latest_state = state
            accepted_records.append(
                {
                    "step": int(_step),
                    "load_factor": float(state.load_factor),
                    "digest": state.digest,
                    "component_digests": state.component_digests,
                }
            )

        with _PeakMemorySampler() as sampler:
            with JsonlNonlinearTelemetry(telemetry_path) as telemetry:
                displacement, diagnostics = _newton_dead_load(
                    case["assembly"],
                    case["external"],
                    case["fixed"],
                    increments=INCREMENTS,
                    tolerance=NEWTON_TOLERANCE,
                    max_iterations=MAX_NEWTON_ITERATIONS,
                    robustness_options=options,
                    initial_state=NonlinearState(
                        np.zeros(case["assembly"].ndof),
                        load_factor=0.0,
                        continuation_state={"accepted_step": 0},
                    ),
                    target_load_factors=[step / INCREMENTS for step in range(1, INCREMENTS + 1)],
                    accepted_state_callback=accepted,
                    telemetry_observer=observe,
                )
            peak_rss = sampler.peak_rss
            peak_private = sampler.peak_private
        internal, _ = case["assembly"].assemble(displacement, tangent_required=False)
        observed, _ = _observe(case, displacement)
        observed["mesh"] = _mesh_metrics(case)
        observed["equilibrium"] = _equilibrium(case, displacement, internal)
        observed["final_displacement_norm"] = float(np.linalg.norm(displacement))
        observed["final_state_digest"] = latest_state.digest if latest_state is not None else None
    except NumericalConvergenceError as exc:
        outcome = "NUMERICAL_FAILURE"
        failure = {
            "reason": exc.reason.value if hasattr(exc.reason, "value") else exc.reason,
            "message": str(exc),
            "diagnostics": _jsonable(exc.diagnostics),
        }
        capture.flush(exc.diagnostics)
    except MemoryError as exc:
        outcome = "FAILED_MEMORY"
        failure = {"reason": "MemoryError", "message": str(exc)}
    except OSError as exc:
        outcome = "HOST_FAILURE"
        failure = {"reason": type(exc).__name__, "message": str(exc)}
    except Exception as exc:  # pragma: no cover - protects an unattended run
        outcome = "RUNNER_ERROR"
        failure = {"reason": type(exc).__name__, "message": str(exc)}
    finally:
        NonlinearLinearSolverAdapter.solve = original_solve

    rss, private = process_memory_bytes()
    peak_rss = max(peak_rss or 0, rss or 0) or None
    peak_private = max(peak_private or 0, private or 0) or None
    if outcome == "COMPLETED":
        terminal_status = "COMPLETED"
    else:
        terminal_status = outcome
    status.update(
        {
            "status": terminal_status,
            "elapsed_wall_time": perf_counter() - started_wall,
            "last_update_timestamp": datetime.now(timezone.utc).isoformat(),
            "terminal_reason": failure.get("reason") if failure else None,
        }
    )
    _write_json(status_path, status)
    summary: dict[str, Any] = {
        "schema_version": 1,
        "record_id": f"QF-SOLVER-0.2.9-WP04-C2R3-{slug.upper()}",
        "case": case_name,
        "mesh_cells": list(CASES[case_name]),
        "expected_route": {
            "linear_solver": "minres",
            "preconditioner": "jacobi",
            "rtol": MINRES_RTOL,
            "atol": MINRES_ATOL,
            "maxiter": MINRES_MAXITER,
            "direct_fallback": False,
            "line_search": "off",
            "increments": INCREMENTS,
            "newton_tolerance": NEWTON_TOLERANCE,
            "max_newton_iterations": MAX_NEWTON_ITERATIONS,
        },
        "started_timestamp": started_timestamp,
        "ended_timestamp": datetime.now(timezone.utc).isoformat(),
        "wall_time_s": perf_counter() - started_wall,
        "cpu_time_s": process_time() - started_cpu,
        "process_end_reason": outcome,
        "status": outcome,
        "failure": failure,
        "telemetry_path": str(telemetry_path),
        "status_path": str(status_path),
        "telemetry_event_count": len(events),
        "accepted_records": accepted_records,
        "performance": {
            **_aggregate_events(events),
            "peak_rss_bytes": peak_rss,
            "peak_private_or_uss_bytes": peak_private,
        },
        "observables": locals().get("observed"),
        "failing_system_capture": capture.written,
        "full_test_suite_run": False,
        "production_source_changed": False,
        "mechanics_formulation_changed": False,
        "maturity_changed": False,
    }
    _write_json(result_path, summary)
    return 0 if outcome in {"COMPLETED", "NUMERICAL_FAILURE", "FAILED_MEMORY", "HOST_FAILURE"} else 1


def _host_safe_for_m3() -> tuple[bool, str]:
    free = shutil.disk_usage(ROOT).free
    if free < 1_000_000_000:
        return False, f"free disk is only {free} bytes"
    try:
        import psutil

        available = int(psutil.virtual_memory().available)
        if available < 512 * 1024 * 1024:
            return False, f"available memory is only {available} bytes"
    except Exception:
        pass
    return True, "disk and available-memory checks are within bounded thresholds"


def _parent(args: argparse.Namespace) -> int:
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve()
    child_results: dict[str, Any] = {}
    campaign_started = datetime.now(timezone.utc).isoformat()
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join([str(SRC), str(ROOT), environment.get("PYTHONPATH", "")])

    for case_name in ("C2-M2", "C2-M3"):
        print(f"[{datetime.now(timezone.utc).isoformat()}] launching {case_name} in a fresh process", flush=True)
        completed = subprocess.run(
            [sys.executable, str(script), "--child", "--case", case_name, "--output-dir", str(output)],
            cwd=ROOT,
            env=environment,
            check=False,
        )
        slug = case_name.split("-")[-1].lower()
        result_path = output / f"{slug}_result.json"
        status_path = output / f"{slug}_status.json"
        if result_path.exists():
            child_results[case_name] = json.loads(result_path.read_text(encoding="utf-8"))
        else:
            status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
            status.update(
                {
                    "status": "EXTERNALLY_INTERRUPTED" if completed.returncode < 0 else "PROCESS_EXIT_NONZERO",
                    "process_returncode": completed.returncode,
                    "last_update_timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            _write_json(status_path, status)
            child_results[case_name] = {
                "case": case_name,
                "status": status["status"],
                "process_end_reason": status["status"],
                "process_returncode": completed.returncode,
            }
        if case_name == "C2-M2":
            safe, reason = _host_safe_for_m3()
            if not safe:
                skip = {
                    "case": "C2-M3",
                    "status": "SKIPPED_HOST_UNSAFE",
                    "process_end_reason": "SKIPPED_HOST_UNSAFE",
                    "host_safety_reason": reason,
                }
                child_results["C2-M3"] = skip
                _write_json(output / "m3_status.json", skip)
                break
            print(f"[{datetime.now(timezone.utc).isoformat()}] {case_name} returned; starting C2-M3 ({reason})", flush=True)

    parent = {
        "schema_version": 1,
        "record_id": "QF-SOLVER-0.2.9-WP04-C2R3-OVERNIGHT",
        "start_timestamp": campaign_started,
        "cases": child_results,
        "m3_started": "C2-M3" in child_results and child_results["C2-M3"].get("status") != "SKIPPED_HOST_UNSAFE",
        "m4_run": False,
        "full_test_suite_run": False,
    }
    _write_json(output / "overnight_campaign_result.json", parent)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--case", choices=tuple(CASES))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    if args.child:
        if args.case is None:
            parser.error("--child requires --case")
        return _child(args)
    return _parent(args)


if __name__ == "__main__":
    raise SystemExit(main())
