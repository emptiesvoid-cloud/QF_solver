"""R2B forensic capture and isolated solver shootout for the frozen WP04 M1 case.

This is qualification infrastructure.  It deliberately captures only the
first adapter failure and writes the sparse system outside the repository by
default.  It does not change the nonlinear solver or its numerical policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigsh, norm as sparse_norm

from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.linear_solver import NonlinearLinearSolverAdapter
from solveur.core.nonlinear.robustness import NonlinearRobustnessOptions
from solveur.core.nonlinear.state import NonlinearState
from solveur.core.nonlinear.telemetry import JsonlNonlinearTelemetry, process_memory_bytes


ROOT = Path(__file__).resolve().parents[1]
START_SHA = "bee8cb606a975a8714947776be489e00af8fa623"
DEFAULT_CAPTURE = Path(r"C:\Users\fari\AppData\Local\Temp\qf_solver_029_r2b_forensics")


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    return value


class _PeakSampler:
    def __init__(self, interval_seconds: float = 0.05) -> None:
        self.interval_seconds = interval_seconds
        self.stop_event = threading.Event()
        self.peak_rss: int | None = None
        self.peak_private: int | None = None
        self.thread = threading.Thread(target=self._run, name="r2b-memory-sampler", daemon=True)

    def _run(self) -> None:
        while not self.stop_event.is_set():
            rss, private = process_memory_bytes()
            if rss is not None:
                self.peak_rss = rss if self.peak_rss is None else max(self.peak_rss, rss)
            if private is not None:
                self.peak_private = private if self.peak_private is None else max(self.peak_private, private)
            self.stop_event.wait(self.interval_seconds)

    def __enter__(self) -> "_PeakSampler":
        self.thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop_event.set()
        self.thread.join(timeout=2.0)


class _RecordingAssembly:
    def __init__(self, assembly: Any) -> None:
        self.assembly = assembly
        self.ndof = int(assembly.ndof)
        self.last_displacement: np.ndarray | None = None

    def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True) -> Any:
        self.last_displacement = np.array(displacement, dtype=float, copy=True)
        return self.assembly.assemble(displacement, tangent_required=tangent_required)


def _array_digest(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def _matrix_digest(matrix: csr_matrix, rhs: np.ndarray) -> str:
    digest = hashlib.sha256()
    for value in (
        np.asarray(matrix.data),
        np.asarray(matrix.indices),
        np.asarray(matrix.indptr),
        np.asarray(matrix.shape, dtype=np.int64),
        np.asarray(rhs),
    ):
        digest.update(np.ascontiguousarray(value).tobytes())
    return digest.hexdigest()


def _capture_failure(capture_dir: Path) -> dict[str, Any]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from solveur.core.analyses.geometric_nonlinear import _newton_dead_load
    from tests.verification.test_wp04_c2_tet4_requalification import _case

    case = _case("C2-M1")
    recording_assembly = _RecordingAssembly(case["assembly"])
    options = NonlinearRobustnessOptions(
        linear_solver="cg",
        linear_preconditioner="jacobi",
        linear_assume_spd=True,
        linear_rtol=1.0e-10,
        linear_direct_fallback=False,
    )
    accepted: list[NonlinearState] = []
    events: list[dict[str, Any]] = []
    captured: dict[str, Any] = {}
    original_solve = NonlinearLinearSolverAdapter.solve

    def capturing_solve(self: NonlinearLinearSolverAdapter, matrix: Any, rhs: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return original_solve(self, matrix, rhs, *args, **kwargs)
        except NumericalConvergenceError as exc:
            if not captured:
                captured["matrix"] = csr_matrix(matrix, dtype=float).copy()
                captured["rhs"] = np.array(rhs, dtype=float, copy=True)
                captured["error_diagnostics"] = dict(exc.diagnostics)
                captured["error"] = str(exc)
                if recording_assembly.last_displacement is not None:
                    captured["displacement"] = recording_assembly.last_displacement.copy()
            raise

    setattr(NonlinearLinearSolverAdapter, "solve", capturing_solve)
    telemetry_path = capture_dir / "r2b_cg_reproduction.jsonl"
    started = perf_counter()
    run_error: str | None = None
    run_error_diagnostics: dict[str, Any] = {}
    try:
        with JsonlNonlinearTelemetry(telemetry_path) as telemetry:
            def observe(event: dict[str, object]) -> None:
                row = dict(event)
                events.append(row)
                telemetry(row)

            try:
                _newton_dead_load(
                    recording_assembly,
                    case["external"],
                    case["fixed"],
                    increments=12,
                    tolerance=1.0e-10,
                    max_iterations=40,
                    robustness_options=options,
                    initial_state=NonlinearState(np.zeros(recording_assembly.ndof, dtype=float)),
                    target_load_factors=[step / 12 for step in range(1, 13)],
                    accepted_state_callback=lambda _step, state: accepted.append(state.detached_copy()),
                    telemetry_observer=observe,
                )
            except NumericalConvergenceError as exc:
                run_error = str(exc)
                run_error_diagnostics = dict(exc.diagnostics)
    finally:
        setattr(NonlinearLinearSolverAdapter, "solve", original_solve)
    elapsed = perf_counter() - started

    if "matrix" not in captured or "rhs" not in captured:
        raise RuntimeError("The frozen CG reproduction did not capture a failing linear system.")
    matrix = captured["matrix"]
    rhs = captured["rhs"]
    displacement = captured.get("displacement")
    capture_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = capture_dir / "wp04_m1_failing_system_step4_iter12.npz"
    arrays: dict[str, Any] = {
        "data": np.asarray(matrix.data),
        "indices": np.asarray(matrix.indices, dtype=np.int64),
        "indptr": np.asarray(matrix.indptr, dtype=np.int64),
        "shape": np.asarray(matrix.shape, dtype=np.int64),
        "rhs": np.asarray(rhs),
    }
    if isinstance(displacement, np.ndarray):
        arrays["trial_displacement"] = displacement
    np.savez_compressed(matrix_path, **arrays)
    sha256 = hashlib.sha256(matrix_path.read_bytes()).hexdigest()
    telemetry_failure = next(
        (event for event in events if event.get("event") == "STEP_FAILED"),
        {},
    )
    step = int(run_error_diagnostics.get("step", telemetry_failure.get("load_step", 4)))
    iteration = int(run_error_diagnostics.get("iterations", telemetry_failure.get("iteration", 12)))
    diag = _matrix_forensics(matrix, rhs)
    diag.update(
        {
            "capture_path": str(matrix_path),
            "capture_sha256": sha256,
            "capture_size_bytes": matrix_path.stat().st_size,
            "capture_arrays": sorted(arrays),
            "source_sha": START_SHA,
            "case": "WP04-C2-M1 nonlinear TET4",
            "load_step": step,
            "load_factor": step / 12.0,
            "newton_iteration": iteration,
            "run_error": run_error,
            "run_error_diagnostics": run_error_diagnostics,
            "captured_error": captured.get("error"),
            "captured_error_diagnostics": captured.get("error_diagnostics", {}),
            "trial_displacement_digest": _array_digest(displacement) if isinstance(displacement, np.ndarray) else None,
            "trial_displacement_norm": float(np.linalg.norm(displacement)) if isinstance(displacement, np.ndarray) else None,
            "accepted_steps_before_failure": len(accepted),
            "accepted_digest_before_failure": accepted[-1].digest if accepted else None,
            "telemetry_path": str(telemetry_path),
            "telemetry_events": len(events),
            "reproduction_seconds": elapsed,
        }
    )
    return diag


def _matrix_forensics(matrix: csr_matrix, rhs: np.ndarray) -> dict[str, Any]:
    values = np.asarray(matrix.data, dtype=float)
    diagonal = np.asarray(matrix.diagonal(), dtype=float)
    diagonal_scale = max(float(np.max(np.abs(diagonal))) if diagonal.size else 0.0, 1.0)
    near_zero_threshold = max(1.0e-12 * diagonal_scale, 1.0e-15)
    difference = matrix - matrix.T
    symmetry_defect = float(np.linalg.norm(difference.data)) / max(float(np.linalg.norm(values)), 1.0)
    return {
        "shape": list(matrix.shape),
        "nnz": int(matrix.nnz),
        "symmetry_defect": symmetry_defect,
        "diagonal_min": float(np.min(diagonal)),
        "diagonal_max": float(np.max(diagonal)),
        "negative_diagonal_count": int(np.count_nonzero(diagonal < 0.0)),
        "near_zero_diagonal_count": int(np.count_nonzero(np.abs(diagonal) <= near_zero_threshold)),
        "near_zero_diagonal_threshold": near_zero_threshold,
        "matrix_norm_1": float(sparse_norm(matrix, ord=1)),
        "matrix_norm_inf": float(sparse_norm(matrix, ord=np.inf)),
        "rhs_norm_2": float(np.linalg.norm(rhs)),
        "rhs_norm_inf": float(np.max(np.abs(rhs))),
        "jacobi_diagonal_abs_range": [float(np.min(np.abs(diagonal))), float(np.max(np.abs(diagonal)))],
        "jacobi_inverse_abs_range": [float(1.0 / np.max(np.abs(diagonal))), float(1.0 / np.min(np.abs(diagonal)))],
        "finite": bool(np.all(np.isfinite(values)) and np.all(np.isfinite(rhs))),
    }


def _residual_metrics(matrix: csr_matrix, solution: np.ndarray, rhs: np.ndarray) -> dict[str, float | bool]:
    residual = np.asarray(matrix @ solution - rhs, dtype=float)
    rhs_norm = float(np.linalg.norm(rhs))
    raw = float(np.linalg.norm(residual)) / max(rhs_norm, 1.0e-14)
    a_inf = float(sparse_norm(matrix, ord=np.inf))
    eta = float(np.max(np.abs(residual))) / max(a_inf * float(np.max(np.abs(solution))) + float(np.max(np.abs(rhs))), 1.0e-14)
    return {
        "finite": bool(np.all(np.isfinite(solution)) and np.all(np.isfinite(residual))),
        "residual_norm_2": float(np.linalg.norm(residual)),
        "raw_relative_residual": raw,
        "backward_error_eta_inf": eta,
    }


def _shootout(capture_dir: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    with np.load(Path(metadata["capture_path"]), allow_pickle=False) as data:
        matrix = csr_matrix(
            (
                np.asarray(data["data"]),
                np.asarray(data["indices"], dtype=np.int64),
                np.asarray(data["indptr"], dtype=np.int64),
            ),
            shape=tuple(np.asarray(data["shape"], dtype=np.int64).tolist()),
        )
        rhs = np.asarray(data["rhs"], dtype=float)
    direct_options = NonlinearRobustnessOptions(linear_solver="direct", linear_direct_fallback=False)
    direct = np.asarray(
        NonlinearLinearSolverAdapter(direct_options).solve(matrix, rhs, allow_unverified_krylov=True)[0],
        dtype=float,
    )
    candidates: dict[str, NonlinearRobustnessOptions] = {
        "direct": direct_options,
        "cg-1e-10": NonlinearRobustnessOptions(
            linear_solver="cg", linear_preconditioner="jacobi", linear_assume_spd=True,
            linear_rtol=1.0e-10, linear_direct_fallback=False,
        ),
        "minres-1e-11": NonlinearRobustnessOptions(
            linear_solver="minres", linear_preconditioner="jacobi", linear_rtol=1.0e-11,
            linear_direct_fallback=False,
        ),
        "minres-1e-12": NonlinearRobustnessOptions(
            linear_solver="minres", linear_preconditioner="jacobi", linear_rtol=1.0e-12,
            linear_direct_fallback=False,
        ),
    }
    results: dict[str, Any] = {}
    for name, options in candidates.items():
        before_rss, before_private = process_memory_bytes()
        started = perf_counter()
        error: str | None = None
        diagnostics: dict[str, Any] = {}
        solution: np.ndarray | None = None
        with _PeakSampler() as sampler:
            try:
                solution, diagnostics = NonlinearLinearSolverAdapter(options).solve(
                    matrix,
                    rhs,
                    reference_solution=direct,
                    allow_unverified_krylov=True,
                )
                solution = np.asarray(solution, dtype=float)
            except NumericalConvergenceError as exc:
                error = str(exc)
                diagnostics = dict(exc.diagnostics)
            elapsed = perf_counter() - started
        row: dict[str, Any] = {
            "status": "PASS" if error is None else "FAIL",
            "error": error,
            "diagnostics": diagnostics,
            "timing_seconds": elapsed,
            "memory": {
                "rss_before": before_rss,
                "private_before": before_private,
                "peak_rss": sampler.peak_rss,
                "peak_private": sampler.peak_private,
            },
        }
        if solution is not None:
            metrics = _residual_metrics(matrix, solution, rhs)
            metrics["solution_relative_difference_vs_direct"] = float(
                np.linalg.norm(solution - direct) / max(float(np.linalg.norm(direct)), 1.0e-14)
            )
            row["metrics"] = metrics
        results[name] = row
    return {"matrix": metadata, "results": results}


def _spectral_probe(capture_path: Path) -> dict[str, Any]:
    with np.load(capture_path, allow_pickle=False) as data:
        matrix = csr_matrix(
            (
                np.asarray(data["data"]),
                np.asarray(data["indices"], dtype=np.int64),
                np.asarray(data["indptr"], dtype=np.int64),
            ),
            shape=tuple(np.asarray(data["shape"], dtype=np.int64).tolist()),
        )
    result: dict[str, Any] = {"method": "scipy.sparse.linalg.eigsh", "maxiter": 2000, "tol": 1.0e-6}
    for label, which in (("lambda_min", "SA"), ("lambda_max", "LA")):
        try:
            value, _ = eigsh(matrix, k=1, which=which, maxiter=2000, tol=1.0e-6, return_eigenvectors=True)
            result[label] = float(value[0])
            result[f"{label}_converged"] = True
        except Exception as exc:  # diagnostic optional probe; retain exact failure
            result[label] = None
            result[f"{label}_converged"] = False
            result[f"{label}_error"] = f"{type(exc).__name__}: {exc}"
    result["status"] = "ESTIMATED" if result.get("lambda_min_converged") and result.get("lambda_max_converged") else "PARTIAL_OR_FAILED"
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-dir", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--shootout", action="store_true")
    parser.add_argument("--spectral", action="store_true")
    args = parser.parse_args()
    args.capture_dir.mkdir(parents=True, exist_ok=True)
    metadata = _capture_failure(args.capture_dir)
    output: dict[str, Any] = {"schema_version": 1, "record_id": "QF-SOLVER-0.2.9-R2B-FAIL-TANGENT-FORENSICS-001", "forensics": metadata}
    if args.shootout:
        output["shootout"] = _shootout(args.capture_dir, metadata)
    if args.spectral:
        output["spectral"] = _spectral_probe(Path(metadata["capture_path"]))
    output_path = args.capture_dir / "wp04_linear_solver_r2b_forensics.json"
    output_path.write_text(json.dumps(_json_safe(output), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(_json_safe(output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
