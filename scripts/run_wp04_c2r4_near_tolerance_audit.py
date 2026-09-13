"""C2R4 M2-only near-tolerance diagnosis for the frozen WP04 benchmark.

This script deliberately keeps the C2R3 numerical controls immutable.  It
records one final step-three state outside Git, compares isolated linear
corrections at that state, and then performs the one Owner-authorized
line-search protocol comparison when the historical route audit finds drift.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from time import perf_counter, process_time
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUTPUT = ROOT / "qualification" / "0_2_9" / "c2r4"
FORENSICS_ROOT = Path(tempfile.gettempdir()) / "qf_solver_029_c2r4_forensics"
INCREMENTS = 12
NEWTON_TOLERANCE = 1.0e-10
MAX_NEWTON_ITERATIONS = 40
MINRES_RTOL = 1.0e-11
MINRES_ATOL = 1.0e-14
MINRES_MAXITER = 10_000
LINEAR_BACKWARD_ERROR_TOLERANCE = 1.0e-10


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int, float)):
        return None if isinstance(value, float) and not np.isfinite(value) else value
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(_jsonable(value), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class _PeakProcessMemory:
    """Sample process RSS/USS independently of sparse-solve telemetry."""

    def __init__(self, memory_reader: Any) -> None:
        self._memory_reader = memory_reader
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.peak_rss: int | None = None
        self.peak_private: int | None = None

    def _sample(self) -> None:
        while not self._stop.is_set():
            rss, private = self._memory_reader()
            if rss is not None:
                self.peak_rss = max(self.peak_rss or 0, int(rss))
            if private is not None:
                self.peak_private = max(self.peak_private or 0, int(private))
            self._stop.wait(0.05)

    def __enter__(self) -> "_PeakProcessMemory":
        self._thread = threading.Thread(target=self._sample, name="c2r4-memory", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)


class _RecordingAssembly:
    """Qualification-only observer retaining the latest assembled trial."""

    def __init__(self, assembly: Any) -> None:
        self._assembly = assembly
        self.ndof = int(assembly.ndof)
        self.last: dict[str, Any] | None = None

    def assemble(
        self, displacement: np.ndarray, *, tangent_required: bool = True
    ) -> tuple[np.ndarray, csr_matrix | None]:
        internal, tangent = self._assembly.assemble(displacement, tangent_required=tangent_required)
        if tangent_required and tangent is not None:
            self.last = {
                "displacement": np.array(displacement, dtype=float, copy=True),
                "internal": np.array(internal, dtype=float, copy=True),
                "tangent": csr_matrix(tangent, dtype=float).copy(),
            }
        return internal, tangent

    def __getattr__(self, name: str) -> Any:
        return getattr(self._assembly, name)


def _options(line_search: str):
    from solveur.core.nonlinear.robustness import NonlinearRobustnessOptions

    result = NonlinearRobustnessOptions(
        linear_solver="minres",
        linear_preconditioner="jacobi",
        linear_rtol=MINRES_RTOL,
        linear_atol=MINRES_ATOL,
        linear_maxiter=MINRES_MAXITER,
        linear_residual_tolerance=LINEAR_BACKWARD_ERROR_TOLERANCE,
        linear_backward_error_tolerance=LINEAR_BACKWARD_ERROR_TOLERANCE,
        linear_direct_fallback=False,
        line_search=line_search,
    )
    result.validate()
    return result


def _capture(
    *,
    case_name: str,
    accepted: Any,
    trial: Mapping[str, Any],
    free: np.ndarray,
    external: np.ndarray,
    fixed: np.ndarray,
    load_factor: float,
) -> dict[str, Any]:
    tangent = csr_matrix(trial["tangent"])[free, :][:, free].tocsr()
    rhs = np.asarray(load_factor * external - np.asarray(trial["internal"]), dtype=float)[free]
    FORENSICS_ROOT.mkdir(parents=True, exist_ok=True)
    target = FORENSICS_ROOT / f"{case_name.lower().replace('-', '_')}_stagnation_step3.npz"
    np.savez_compressed(
        target,
        data=np.asarray(tangent.data),
        indices=np.asarray(tangent.indices),
        indptr=np.asarray(tangent.indptr),
        shape=np.asarray(tangent.shape, dtype=np.int64),
        rhs=rhs,
        trial_displacement=np.asarray(trial["displacement"]),
        trial_internal_force=np.asarray(trial["internal"]),
        accepted_displacement=np.asarray(accepted.displacement),
        external=np.asarray(external),
        fixed=np.asarray(fixed, dtype=np.int64),
        free=np.asarray(free, dtype=np.int64),
        load_factor=np.asarray([load_factor], dtype=float),
    )
    return {
        "path": str(target),
        "sha256": _sha256(target),
        "size_bytes": int(target.stat().st_size),
        "shape": [int(item) for item in tangent.shape],
        "nnz": int(tangent.nnz),
        "accepted_state_before_step": {
            "load_factor": float(accepted.load_factor),
            "digest": accepted.digest,
            "component_digests": accepted.component_digests,
        },
        "trial_state": {
            "load_factor": load_factor,
            "displacement_norm": float(np.linalg.norm(trial["displacement"])),
        },
    }


def _linear_result(adapter: Any, matrix: csr_matrix, rhs: np.ndarray, reference: np.ndarray | None) -> tuple[np.ndarray, dict[str, Any]]:
    correction, diagnostics = adapter.solve(matrix, rhs, reference_solution=reference)
    return np.asarray(correction, dtype=float), dict(diagnostics)


def _run_primary() -> dict[str, Any]:
    sys.path.insert(0, str(SRC))
    sys.path.insert(0, str(ROOT))
    from solveur.core.analyses.geometric_nonlinear import _newton_dead_load
    from solveur.core.errors import NumericalConvergenceError
    from solveur.core.nonlinear.linear_solver import NonlinearLinearSolverAdapter
    from solveur.core.nonlinear.state import NonlinearState
    from solveur.core.nonlinear.telemetry import JsonlNonlinearTelemetry, process_memory_bytes
    from tests.verification.test_wp04_c2_tet4_requalification import _case, _equilibrium

    started = perf_counter()
    started_cpu = process_time()
    options = _options("off")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    telemetry_path = OUTPUT / "m2_reproduction_telemetry.jsonl"
    events: list[dict[str, Any]] = []
    accepted: list[tuple[int, NonlinearState]] = []
    case = _case("C2-M2")
    recording = _RecordingAssembly(case["assembly"])

    def observe(event: Mapping[str, object]) -> None:
        row = {**dict(event), "case": "C2-M2", "phase": "C2R4_REPRODUCTION"}
        events.append(_jsonable(row))
        telemetry(row)

    def accepted_callback(step: int, state: NonlinearState) -> None:
        accepted.append((int(step), state.detached_copy()))

    failure: dict[str, Any] | None = None
    with _PeakProcessMemory(process_memory_bytes) as memory:
        with JsonlNonlinearTelemetry(telemetry_path) as telemetry:
            try:
                _newton_dead_load(
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
                    accepted_state_callback=accepted_callback,
                    telemetry_observer=observe,
                )
            except NumericalConvergenceError as exc:
                failure = {
                    "reason": exc.reason.value if exc.reason is not None else None,
                    "message": str(exc),
                    "diagnostics": _jsonable(exc.diagnostics),
                }
            else:
                raise RuntimeError("C2R4 expected the frozen C2R3 M2 stagnation, but the run converged.")

    if failure is None or failure["reason"] != "CONVERGENCE_STAGNATION":
        raise RuntimeError(f"C2R4 did not reproduce C2R3 stagnation: {failure}")
    diagnostics = failure["diagnostics"]
    if not isinstance(diagnostics, Mapping) or int(diagnostics["step"]) != 3:
        raise RuntimeError(f"C2R4 stagnation did not occur at step 3: {diagnostics}")
    if recording.last is None or len(accepted) != 2:
        raise RuntimeError("C2R4 did not retain the expected accepted/trial state boundary.")

    step = int(diagnostics["step"])
    iteration = int(diagnostics["iterations"])
    load_factor = step / INCREMENTS
    free = np.setdiff1d(np.arange(recording.ndof), case["fixed"])
    capture = _capture(
        case_name="C2-M2",
        accepted=accepted[-1][1],
        trial=recording.last,
        free=free,
        external=case["external"],
        fixed=case["fixed"],
        load_factor=load_factor,
    )
    matrix = csr_matrix(recording.last["tangent"])[free, :][:, free].tocsr()
    rhs = np.asarray(load_factor * case["external"] - recording.last["internal"], dtype=float)[free]
    scale = max(float(np.linalg.norm((load_factor * case["external"])[free])), 1.0)

    direct = NonlinearLinearSolverAdapter(
        _options("off").__class__(linear_solver="direct", linear_preconditioner="none", linear_direct_fallback=False)
    )
    direct_correction, direct_diagnostics = _linear_result(direct, matrix, rhs, None)
    minres_11_correction, minres_11_diagnostics = _linear_result(
        NonlinearLinearSolverAdapter(_options("off")), matrix, rhs, direct_correction
    )
    minres_12_options = _options("off").__class__(
        linear_solver="minres",
        linear_preconditioner="jacobi",
        linear_rtol=1.0e-12,
        linear_atol=MINRES_ATOL,
        linear_maxiter=MINRES_MAXITER,
        linear_residual_tolerance=LINEAR_BACKWARD_ERROR_TOLERANCE,
        linear_backward_error_tolerance=LINEAR_BACKWARD_ERROR_TOLERANCE,
        linear_direct_fallback=False,
        line_search="off",
    )
    minres_12_options.validate()
    minres_12_correction, minres_12_diagnostics = _linear_result(
        NonlinearLinearSolverAdapter(minres_12_options), matrix, rhs, direct_correction
    )

    trial_displacement = np.asarray(recording.last["displacement"], dtype=float)

    def nonlinear_residual(displacement: np.ndarray) -> tuple[float, np.ndarray]:
        internal, _ = case["assembly"].assemble(displacement, tangent_required=False)
        vector = np.asarray(load_factor * case["external"] - internal, dtype=float)
        return float(np.linalg.norm(vector[free]) / scale), np.asarray(internal, dtype=float)

    residual_before, trial_internal = nonlinear_residual(trial_displacement)

    def after(correction: np.ndarray) -> float:
        isolated = np.array(trial_displacement, copy=True)
        isolated[free] += correction
        return nonlinear_residual(isolated)[0]

    after_minres_11 = after(minres_11_correction)
    after_minres_12 = after(minres_12_correction)
    after_direct = after(direct_correction)
    reassembly = [nonlinear_residual(trial_displacement)[0] for _ in range(5)]
    equilibrium_case = {**case, "external": load_factor * case["external"]}
    equilibrium = _equilibrium(equilibrium_case, trial_displacement, trial_internal)
    trial_displacement_norm = float(np.linalg.norm(trial_displacement))
    relative_correction = float(np.linalg.norm(direct_correction) / max(trial_displacement_norm, 1.0e-14))
    telemetry_rss = [int(item["RSS_bytes"]) for item in events if isinstance(item.get("RSS_bytes"), int)]
    telemetry_private = [
        int(item["private_or_USS_bytes"])
        for item in events
        if isinstance(item.get("private_or_USS_bytes"), int)
    ]
    if after_direct <= NEWTON_TOLERANCE:
        root_cause = "ITERATIVE_ROUTE_PRECISION_LIMITATION"
    elif max(reassembly) - min(reassembly) == 0.0 and relative_correction <= 1.0e-12:
        root_cause = "NONLINEAR_RESIDUAL_NUMERICAL_FLOOR"
    else:
        root_cause = "UNRESOLVED_SAME_STATE_DIAGNOSIS"
    return {
        "case": "C2-M2",
        "started_timestamp": datetime.now(timezone.utc).isoformat(),
        "wall_time_s": perf_counter() - started,
        "cpu_time_s": process_time() - started_cpu,
        "expected_route": {
            "linear_solver": "minres",
            "preconditioner": "jacobi",
            "rtol": MINRES_RTOL,
            "atol": MINRES_ATOL,
            "maxiter": MINRES_MAXITER,
            "direct_fallback": False,
            "line_search": "off",
            "newton_tolerance": NEWTON_TOLERANCE,
            "increments": INCREMENTS,
        },
        "stagnation": {
            "reproduced": True,
            "step": step,
            "iteration": iteration,
            "load_factor": load_factor,
            "failure": failure,
            "capture": capture,
        },
        "same_state_linear_forensics": {
            "residual_before": residual_before,
            "direct": {"correction_norm": float(np.linalg.norm(direct_correction)), "diagnostics": direct_diagnostics, "residual_after": after_direct},
            "minres_rtol_1e11": {"correction_norm": float(np.linalg.norm(minres_11_correction)), "diagnostics": minres_11_diagnostics, "residual_after": after_minres_11},
            "minres_rtol_1e12": {"correction_norm": float(np.linalg.norm(minres_12_correction)), "diagnostics": minres_12_diagnostics, "residual_after": after_minres_12},
            "relative_correction_norm": relative_correction,
        },
        "reassembly": {
            "samples": reassembly,
            "min": min(reassembly),
            "max": max(reassembly),
            "mean": float(np.mean(reassembly)),
            "spread": max(reassembly) - min(reassembly),
        },
        "force_moment_at_stagnation": equilibrium,
        "root_cause_classification": root_cause,
        "telemetry_path": str(telemetry_path),
        "memory": {
            "peak_rss_process": max(memory.peak_rss or 0, *(telemetry_rss or [0])) or None,
            "peak_private_or_uss_process": max(memory.peak_private or 0, *(telemetry_private or [0])) or None,
            "telemetry_sample_peak_rss": max(telemetry_rss) if telemetry_rss else None,
            "telemetry_sample_peak_private": max(telemetry_private) if telemetry_private else None,
        },
    }


def _run_canonical_line_search() -> dict[str, Any]:
    """Run the one bounded protocol-correction experiment after C2R3 drift."""

    from solveur.core.analyses.geometric_nonlinear import _newton_dead_load
    from solveur.core.errors import NumericalConvergenceError
    from solveur.core.nonlinear.state import NonlinearState
    from solveur.core.nonlinear.telemetry import JsonlNonlinearTelemetry
    from tests.verification.test_wp04_c2_tet4_requalification import _case

    started = perf_counter()
    case = _case("C2-M2")
    telemetry_path = OUTPUT / "m2_canonical_line_search_telemetry.jsonl"
    accepted: list[dict[str, Any]] = []
    failure: dict[str, Any] | None = None
    try:
        with JsonlNonlinearTelemetry(telemetry_path) as telemetry:
            _newton_dead_load(
                case["assembly"],
                case["external"],
                case["fixed"],
                increments=INCREMENTS,
                tolerance=NEWTON_TOLERANCE,
                max_iterations=MAX_NEWTON_ITERATIONS,
                robustness_options=_options("existing"),
                initial_state=NonlinearState(
                    np.zeros(case["assembly"].ndof), load_factor=0.0, continuation_state={"accepted_step": 0}
                ),
                target_load_factors=[step / INCREMENTS for step in range(1, INCREMENTS + 1)],
                accepted_state_callback=lambda step, state: accepted.append(
                    {"step": int(step), "load_factor": float(state.load_factor), "digest": state.digest}
                ),
                telemetry_observer=telemetry,
            )
    except NumericalConvergenceError as exc:
        failure = {
            "reason": exc.reason.value if exc.reason is not None else None,
            "message": str(exc),
            "diagnostics": _jsonable(exc.diagnostics),
        }
    return {
        "attempted": True,
        "line_search": "existing",
        "wall_time_s": perf_counter() - started,
        "accepted_records": accepted,
        "status": "COMPLETED" if failure is None else "NUMERICAL_FAILURE",
        "failure": failure,
        "telemetry_path": str(telemetry_path),
    }


def main() -> int:
    primary = _run_primary()
    # Static source/evidence audit: C2/C2R2 call with no options (existing
    # compatibility line search); R2B uses options whose default is existing;
    # C2R3 explicitly selects the experimental line-search-off override.
    protocol = {
        "original_c2_line_search": "existing/enabled (no robustness_options supplied)",
        "r2b_direct_line_search": "existing/enabled (default robustness option)",
        "r2b_minres_line_search": "existing/enabled (default robustness option)",
        "c2r3_line_search": "off (explicit experimental override)",
        "status": "PROTOCOL_DRIFT",
    }
    canonical = _run_canonical_line_search()
    result = {
        "schema_version": 1,
        "record_id": "QF-SOLVER-0.2.9-WP04-C2R4",
        "start_sha": "0b947bb6c1c684f71f2f7b5ab32ad8b9f9afbcc8",
        "protocol_audit": protocol,
        "nonlinear_residual_contract": {
            "formula": "||lambda*F_ext - F_int(u)||_2 over free DOFs",
            "normalization": "max(||(lambda*F_ext)_free||_2, force_scale when supplied, 1.0)",
            "force_scale": "not supplied by the C2 route",
            "dimensionless_relative_residual": True,
        },
        "m2_reproduction": primary,
        "canonical_line_search_m2": canonical,
        "memory_metric_contract": {
            "peak_rss_process": "maximum psutil process RSS from the C2R4 monitor and telemetry samples",
            "peak_private_or_uss_process": "maximum psutil USS/private value from the C2R4 monitor and telemetry samples",
            "telemetry_sample_peak_rss": "maximum per-Newton telemetry RSS sample only",
            "telemetry_sample_peak_private": "maximum per-Newton telemetry private/USS sample only",
            "historical_note": "C2R3 sampler/status/result/master values are retained unchanged; Windows PrivateMemorySize and psutil USS are distinct measures.",
        },
        "governance": {
            "wp04_status": "HOLD",
            "g04_10": "UNRESOLVED",
            "wp04_points": "0/12",
            "validated_total": "29/100",
            "m3_run": False,
            "m4_run": False,
            "petsc_work": False,
            "full_test_suite_run": False,
        },
    }
    _write_json(OUTPUT / "near_tolerance_audit_result.json", result)
    print(json.dumps(_jsonable(result), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
