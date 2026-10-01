"""Run the owner-frozen WP04-C2R6 floor-aware M2/M3 campaign.

M3 is launched in a fresh child process only after M2 reaches the final load
without an unrelated numerical failure.  The runner records accepted states
and compact telemetry; it never stores matrices or trial vectors in Git.
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
OUTPUT = ROOT / "qualification" / "0_2_9" / "c2r6"
CONTROLS = OUTPUT / "floor_aware_policy.json"
FORENSICS_ROOT = Path(tempfile.gettempdir()) / "qf_solver_029_c2r6_forensics"
CASES = {"C2-M2": (48, 24, 24), "C2-M3": (64, 32, 32)}
INCREMENTS = 12
NEWTON_TOLERANCE = 1.0e-10
MAX_NEWTON_ITERATIONS = 40
MINRES_RTOL = 1.0e-11
MINRES_ATOL = 1.0e-14
MINRES_MAXITER = 10_000
LINEAR_BACKWARD_ERROR_TOLERANCE = 1.0e-10


def _jsonable(value: Any) -> Any:
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
                self.peak_rss = max(self.peak_rss or 0, int(rss))
            if private is not None:
                self.peak_private = max(self.peak_private or 0, int(private))
            self.stop.wait(0.10)

    def __enter__(self) -> "_PeakMemorySampler":
        self.thread = threading.Thread(target=self._sample, name="c2r6-memory", daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop.set()
        if self.thread is not None:
            self.thread.join(timeout=2.0)


class _RecordingAssembly:
    """Retain only the latest assembly for failure forensics."""

    def __init__(self, assembly: Any) -> None:
        self._assembly = assembly
        self.ndof = int(assembly.ndof)

    def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True) -> tuple[Any, Any]:
        return self._assembly.assemble(displacement, tangent_required=tangent_required)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._assembly, name)


class _FailureSystemCapture:
    """Persist one failed reduced system outside the repository."""

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
            "size_bytes": int(target.stat().st_size),
            "sha256": _sha256(target),
            "shape": [int(item) for item in matrix.shape],
            "nnz": int(matrix.nnz),
            "linear_method": diagnostics.get("linear_method"),
            "linear_backend": diagnostics.get("linear_backend"),
        }
        self.pending = None
        return self.written


def _aggregate(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    iterations = [event for event in events if event.get("event") == "ITERATION"]
    solves = [
        event
        for event in iterations
        if event.get("linear_method") is not None or event.get("status") == "LINEAR_FAILED"
    ]
    krylov = [
        int(event["krylov_iterations"])
        for event in solves
        if isinstance(event.get("krylov_iterations"), (int, float))
    ]
    solve_times = [
        float(event["linear_solve_time_s"])
        for event in solves
        if isinstance(event.get("linear_solve_time_s"), (int, float))
    ]
    etas = [
        float(event["linear_backward_error_eta_inf"])
        for event in solves
        if isinstance(event.get("linear_backward_error_eta_inf"), (int, float))
        and np.isfinite(float(event["linear_backward_error_eta_inf"]))
    ]
    raw = [
        float(event["linear_relative_residual"])
        for event in solves
        if isinstance(event.get("linear_relative_residual"), (int, float))
        and np.isfinite(float(event["linear_relative_residual"]))
    ]
    accepted = [event for event in events if event.get("event") == "STEP_ACCEPTED"]
    floor = [event for event in iterations if event.get("status") == "FLOOR_CONVERGED"]
    primary = [event for event in iterations if event.get("termination_classification") == "CONVERGED_RESIDUAL"]
    return {
        "accepted_step_count": len(accepted),
        "accepted_load_factors": [event.get("target_load_factor") for event in accepted],
        "total_newton_iterations": len(iterations),
        "total_linear_solves": len(solves),
        "termination_counts": {"CONVERGED_RESIDUAL": len(primary), "CONVERGED_NUMERICAL_FLOOR": len(floor)},
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
        "max_raw_linear_relative_residual": max(raw) if raw else None,
        "fallback_count": sum(1 for event in solves if bool(event.get("fallback_used"))),
        "line_search_alphas": [event.get("line_search_alpha") for event in iterations],
    }


def _floor_evidence(case: Mapping[str, Any], state: Any, response: Any, external: np.ndarray, free: np.ndarray, load_factor: float) -> Mapping[str, Any]:
    """Supply case-observable equilibrium and envelope evidence to the generic policy."""

    internal = np.asarray(response.internal_force, dtype=float)
    fixed = np.setdiff1d(np.arange(internal.size, dtype=int), np.asarray(free, dtype=int))
    target = float(load_factor) * np.asarray(external, dtype=float)
    reactions = np.zeros_like(internal)
    reactions[fixed] = internal[fixed] - target[fixed]
    physical = np.asarray(case["nodes"], dtype=float) + np.asarray(state.displacement).reshape(-1, 3)
    target_vectors = target.reshape(-1, 3)
    reaction_vectors = reactions.reshape(-1, 3)
    force = np.sum(target_vectors, axis=0) + np.sum(reaction_vectors, axis=0)
    moment = np.sum(np.cross(physical, target_vectors), axis=0) + np.sum(
        np.cross(physical, reaction_vectors), axis=0
    )
    force_scale = max(float(np.linalg.norm(np.sum(target_vectors, axis=0))), float(np.linalg.norm(np.sum(reaction_vectors, axis=0))), 1.0)
    moment_scale = max(float(np.linalg.norm(np.sum(np.cross(physical, target_vectors), axis=0))), float(np.linalg.norm(np.sum(np.cross(physical, reaction_vectors), axis=0))), 1.0)
    geometric = case["assembly"].element_states(np.asarray(state.displacement, dtype=float))
    deformation = np.asarray(geometric["deformation_gradient"], dtype=float)
    stretches = np.linalg.svd(deformation, compute_uv=False)
    green = np.asarray(geometric["green_lagrange_strain"], dtype=float)
    finite = bool(
        np.all(np.isfinite(deformation))
        and np.all(np.isfinite(stretches))
        and np.all(np.isfinite(green))
        and np.all(np.isfinite(geometric["det_f"]))
    )
    valid = finite and bool(
        np.min(geometric["det_f"]) >= 0.20
        and np.min(stretches) >= 0.75
        and np.max(stretches) <= 1.30
        and np.max(np.linalg.norm(green, axis=(1, 2))) <= 0.30
    )
    return {
        "state_valid": valid,
        "force_equilibrium": float(np.linalg.norm(force) / force_scale),
        "moment_equilibrium": float(np.linalg.norm(moment) / moment_scale),
        "minimum_det_f": float(np.min(geometric["det_f"])),
        "minimum_principal_stretch": float(np.min(stretches)),
        "maximum_principal_stretch": float(np.max(stretches)),
        "maximum_green_lagrange_norm": float(np.max(np.linalg.norm(green, axis=(1, 2)))),
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
    from tests.verification.test_wp04_c2_tet4_requalification import _case, _equilibrium, _mesh_metrics, _observe

    case_name = str(args.case)
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    slug = case_name.split("-")[-1].lower()
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
    failure_capture = _FailureSystemCapture(case_name)
    original_solve = NonlinearLinearSolverAdapter.solve

    def wrapped_solve(self: Any, matrix: Any, rhs: np.ndarray, **kwargs: Any) -> Any:
        try:
            return original_solve(self, matrix, rhs, **kwargs)
        except NumericalConvergenceError as exc:
            failure_capture.hold(matrix, rhs, exc.diagnostics)
            raise

    NonlinearLinearSolverAdapter.solve = wrapped_solve
    failure: dict[str, Any] | None = None
    outcome = "COMPLETED"
    observed: dict[str, Any] | None = None
    peak_rss: int | None = None
    peak_private: int | None = None
    try:
        case = _case(case_name)
        recording = _RecordingAssembly(case["assembly"])
        options = NonlinearRobustnessOptions(
            linear_solver="minres",
            linear_preconditioner="jacobi",
            linear_rtol=MINRES_RTOL,
            linear_atol=MINRES_ATOL,
            linear_maxiter=MINRES_MAXITER,
            linear_residual_tolerance=LINEAR_BACKWARD_ERROR_TOLERANCE,
            linear_backward_error_tolerance=LINEAR_BACKWARD_ERROR_TOLERANCE,
            linear_direct_fallback=False,
            line_search="existing",
            floor_aware_termination=True,
        )
        options.validate()

        def accepted(step: int, state: NonlinearState) -> None:
            accepted_records.append(
                {
                    "step": int(step),
                    "load_factor": float(state.load_factor),
                    "digest": state.digest,
                    "component_digests": state.component_digests,
                }
            )

        def observe(event: Mapping[str, object]) -> None:
            enriched = {**dict(event), "case": case_name, "mesh": list(CASES[case_name]), "phase": "C2R6"}
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
                failure_capture.flush(enriched)
            _write_json(status_path, status)

        with _PeakMemorySampler() as sampler:
            with JsonlNonlinearTelemetry(telemetry_path) as telemetry:
                displacement, diagnostics = _newton_dead_load(
                    recording,
                    case["external"],
                    case["fixed"],
                    increments=INCREMENTS,
                    tolerance=NEWTON_TOLERANCE,
                    max_iterations=MAX_NEWTON_ITERATIONS,
                    robustness_options=options,
                    initial_state=NonlinearState(
                        np.zeros(recording.ndof), load_factor=0.0, continuation_state={"accepted_step": 0}
                    ),
                    target_load_factors=[step / INCREMENTS for step in range(1, INCREMENTS + 1)],
                    accepted_state_callback=accepted,
                    telemetry_observer=observe,
                    floor_aware_evidence=lambda state, response, external, free, factor: _floor_evidence(
                        case, state, response, external, free, factor
                    ),
                )
            peak_rss = sampler.peak_rss
            peak_private = sampler.peak_private
        internal, _ = case["assembly"].assemble(displacement, tangent_required=False)
        observed, _ = _observe(case, displacement)
        observed["mesh"] = _mesh_metrics(case)
        observed["equilibrium"] = _equilibrium(case, displacement, internal)
        observed["accepted_load_factors"] = [record["load_factor"] for record in accepted_records]
        observed["accepted_state_digests"] = [record["digest"] for record in accepted_records]
        observed["newton_iterations"] = int(sum(int(row["iterations"]) for row in diagnostics["increments"]))
        observed["deformation_envelope"] = {
            "minimum_det_f": observed["minimum_det_f"],
            "minimum_principal_stretch": observed["minimum_principal_stretch"],
            "maximum_principal_stretch": observed["maximum_principal_stretch"],
            "maximum_green_lagrange_norm": observed["maximum_green_lagrange_norm"],
        }
    except NumericalConvergenceError as exc:
        outcome = "NUMERICAL_FAILURE"
        failure = {
            "reason": exc.reason.value if hasattr(exc.reason, "value") else exc.reason,
            "message": str(exc),
            "diagnostics": _jsonable(exc.diagnostics),
        }
        failure_capture.flush(exc.diagnostics)
    except MemoryError as exc:
        outcome = "FAILED_MEMORY"
        failure = {"reason": "MemoryError", "message": str(exc)}
    except OSError as exc:
        outcome = "HOST_FAILURE"
        failure = {"reason": type(exc).__name__, "message": str(exc)}
    except Exception as exc:  # pragma: no cover - protects unattended execution
        outcome = "RUNNER_ERROR"
        failure = {"reason": type(exc).__name__, "message": str(exc)}
    finally:
        NonlinearLinearSolverAdapter.solve = original_solve

    rss, private = process_memory_bytes()
    peak_rss = max(peak_rss or 0, rss or 0) or None
    peak_private = max(peak_private or 0, private or 0) or None
    status.update(
        {
            "status": outcome,
            "elapsed_wall_time": perf_counter() - started_wall,
            "last_update_timestamp": datetime.now(timezone.utc).isoformat(),
            "terminal_reason": failure.get("reason") if failure else None,
        }
    )
    _write_json(status_path, status)
    summary = {
        "schema_version": 1,
        "record_id": f"QF-SOLVER-0.2.9-WP04-C2R6-{slug.upper()}",
        "case": case_name,
        "mesh_cells": list(CASES[case_name]),
        "status": outcome,
        "process_end_reason": outcome,
        "route": {
            "linear_solver": "MINRES",
            "preconditioner": "Jacobi",
            "rtol": MINRES_RTOL,
            "atol": MINRES_ATOL,
            "maxiter": MINRES_MAXITER,
            "direct_fallback": False,
            "line_search": "existing/enabled",
            "floor_aware_termination": True,
            "newton_tolerance": NEWTON_TOLERANCE,
            "increments": INCREMENTS,
        },
        "start_sha": "2c52bf8196a7d47d14ce1784290580160de26590",
        "started_timestamp": started_timestamp,
        "ended_timestamp": datetime.now(timezone.utc).isoformat(),
        "wall_time_s": perf_counter() - started_wall,
        "cpu_time_s": process_time() - started_cpu,
        "failure": failure,
        "telemetry_path": str(telemetry_path),
        "status_path": str(status_path),
        "telemetry_event_count": len(events),
        "accepted_records": accepted_records,
        "performance": {**_aggregate(events), "peak_rss_bytes": peak_rss, "peak_private_or_uss_bytes": peak_private},
        "observables": observed,
        "failing_system_capture": failure_capture.written,
        "full_test_suite_run": False,
        "production_source_changed": True,
        "mechanics_formulation_changed": False,
        "element_formulation_changed": False,
        "material_model_changed": False,
        "maturity_changed": False,
    }
    _write_json(result_path, summary)
    return 0


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
    if not CONTROLS.exists():
        raise FileNotFoundError(f"Frozen C2R6 controls are missing: {CONTROLS}")
    controls = json.loads(CONTROLS.read_text(encoding="utf-8"))
    if controls.get("status") != "FROZEN_BEFORE_M2" or controls.get("controls_status") != "PASS_ALL_POSITIVE_AND_NEGATIVE_CONTROLS":
        raise RuntimeError("C2R6 controls are not frozen and passing; campaign is not authorized.")
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve()
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join([str(SRC), str(ROOT), environment.get("PYTHONPATH", "")])
    campaign_started = datetime.now(timezone.utc).isoformat()
    child_results: dict[str, Any] = {}
    m2_completed = False
    print(f"[{campaign_started}] launching C2-M2 with frozen C2R6 policy", flush=True)
    completed = subprocess.run(
        [sys.executable, str(script), "--child", "--case", "C2-M2", "--output-dir", str(output)],
        cwd=ROOT,
        env=environment,
        check=False,
    )
    m2_path = output / "m2_result.json"
    if m2_path.exists():
        child_results["C2-M2"] = json.loads(m2_path.read_text(encoding="utf-8"))
        m2_completed = child_results["C2-M2"].get("status") == "COMPLETED"
    else:
        status_path = output / "m2_status.json"
        status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
        status.update({"status": "EXTERNALLY_INTERRUPTED" if completed.returncode < 0 else "PROCESS_EXIT_NONZERO", "process_returncode": completed.returncode})
        _write_json(status_path, status)
        child_results["C2-M2"] = status

    if m2_completed:
        safe, reason = _host_safe_for_m3()
        if safe:
            print(f"[{datetime.now(timezone.utc).isoformat()}] C2-M2 completed; launching C2-M3 ({reason})", flush=True)
            subprocess.run(
                [sys.executable, str(script), "--child", "--case", "C2-M3", "--output-dir", str(output)],
                cwd=ROOT,
                env=environment,
                check=False,
            )
            m3_path = output / "m3_result.json"
            if m3_path.exists():
                child_results["C2-M3"] = json.loads(m3_path.read_text(encoding="utf-8"))
            else:
                status_path = output / "m3_status.json"
                status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
                status["status"] = "EXTERNALLY_INTERRUPTED"
                _write_json(status_path, status)
                child_results["C2-M3"] = status
        else:
            child_results["C2-M3"] = {
                "case": "C2-M3",
                "status": "SKIPPED_HOST_UNSAFE",
                "process_end_reason": "SKIPPED_HOST_UNSAFE",
                "host_safety_reason": reason,
            }
            _write_json(output / "m3_status.json", child_results["C2-M3"])
    else:
        child_results["C2-M3"] = {
            "case": "C2-M3",
            "status": "NOT_AUTHORIZED_AFTER_M2_FAILURE",
            "process_end_reason": "NOT_AUTHORIZED_AFTER_M2_FAILURE",
        }
        _write_json(output / "m3_status.json", child_results["C2-M3"])

    campaign = {
        "schema_version": 1,
        "record_id": "QF-SOLVER-0.2.9-WP04-C2R6-FLOOR-AWARE-CAMPAIGN",
        "start_sha": "2c52bf8196a7d47d14ce1784290580160de26590",
        "start_timestamp": campaign_started,
        "route": {
            "linear_solver": "MINRES",
            "preconditioner": "Jacobi",
            "rtol": MINRES_RTOL,
            "atol": MINRES_ATOL,
            "maxiter": MINRES_MAXITER,
            "direct_fallback": False,
            "line_search": "existing/enabled",
            "floor_aware_termination": True,
            "newton_tolerance": NEWTON_TOLERANCE,
            "increments": INCREMENTS,
        },
        "cases": child_results,
        "m2_completed": m2_completed,
        "m3_run": "C2-M3" in child_results and child_results["C2-M3"].get("status") != "NOT_AUTHORIZED_AFTER_M2_FAILURE",
        "m4_run": False,
        "petsc_work": False,
        "full_test_suite_run": False,
        "wp04_status": "HOLD",
        "G04-10": "UNRESOLVED",
        "wp04_points": "0/12",
        "validated_total": 29,
    }
    _write_json(output / "campaign_result.json", campaign)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--case", choices=tuple(CASES))
    parser.add_argument("--output-dir", default=str(OUTPUT))
    args = parser.parse_args()
    return _child(args) if args.child else _parent(args)


if __name__ == "__main__":
    raise SystemExit(main())
