"""Controlled R2 sweep for the frozen WP04 C2-M1 reduced linear system.

The preparation and each candidate run are separate invocations so peak RSS is
not contaminated by a previous factorization.  Candidate runs may request the
adapter's explicitly diagnostic ``allow_unverified_krylov`` mode; the frozen
R2 acceptance contract is evaluated in this script and is never changed for
normal nonlinear solves.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
from pathlib import Path
from time import perf_counter, sleep
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve

from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.linear_solver import NonlinearLinearSolverAdapter
from solveur.core.nonlinear.robustness import NonlinearRobustnessOptions
from solveur.core.nonlinear.telemetry import JsonlNonlinearTelemetry, process_memory_bytes


ROOT = Path(__file__).resolve().parents[1]
START_SHA = "12304a5e79d720b2cea8dca60f638239f045bdef"
INPUT_FILE = "c2_m1_zero_state_reduced.npz"
METADATA_FILE = "c2_m1_zero_state_metadata.json"


def _json_safe(value: Any) -> Any:
    """Convert NumPy scalar/container values without losing numeric meaning."""

    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


class _PeakSampler:
    def __init__(self, interval_seconds: float = 0.05) -> None:
        self.interval_seconds = interval_seconds
        self.stop_event = threading.Event()
        self.peak_rss: int | None = None
        self.peak_private: int | None = None
        self.thread = threading.Thread(target=self._run, name="r2-memory-sampler", daemon=True)

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


def _build_matrix() -> tuple[csr_matrix, np.ndarray, dict[str, Any]]:
    # Reuse the exact frozen C2-M1 mesh/load definition; this is qualification
    # infrastructure, not a second mechanics implementation.
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tests.verification.test_wp04_c2_tet4_requalification import _case, _free

    case = _case("C2-M1")
    assembly = case["assembly"]
    _, tangent = assembly.assemble(np.zeros(assembly.ndof, dtype=float), tangent_required=True)
    if tangent is None:
        raise RuntimeError("C2-M1 zero-state tangent was not assembled.")
    free = _free(assembly.ndof, case["fixed"])
    reduced = csr_matrix(tangent[free, :][:, free], dtype=float)
    rhs = np.asarray(case["external"][free], dtype=float)
    metadata = {
        "source_sha": START_SHA,
        "case": "WP04-C2-M1 zero-state linear preflight",
        "cells": [32, 16, 16],
        "full_dofs": int(assembly.ndof),
        "free_dofs": int(free.size),
        "matrix_shape": list(reduced.shape),
        "matrix_nnz": int(reduced.nnz),
        "symmetry_defect": 0.0,
        "assembly": "tests.verification.test_wp04_c2_tet4_requalification._case",
    }
    return reduced, rhs, metadata


def prepare(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    matrix, rhs, metadata = _build_matrix()
    direct = np.asarray(spsolve(matrix, rhs), dtype=float)
    np.savez_compressed(
        output_dir / INPUT_FILE,
        data=np.asarray(matrix.data, dtype=float),
        indices=np.asarray(matrix.indices, dtype=np.int64),
        indptr=np.asarray(matrix.indptr, dtype=np.int64),
        shape=np.asarray(matrix.shape, dtype=np.int64),
        rhs=rhs,
        direct=direct,
    )
    metadata["direct_reference"] = "spsolve computed during preparation; candidate runs are separate processes"
    metadata["direct_reference_solution_norm"] = float(np.linalg.norm(direct))
    (output_dir / METADATA_FILE).write_text(
        json.dumps(_json_safe(metadata), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )


def _load_input(input_dir: Path) -> tuple[csr_matrix, np.ndarray, np.ndarray, dict[str, Any]]:
    with np.load(input_dir / INPUT_FILE, allow_pickle=False) as data:
        matrix = csr_matrix(
            (
                np.asarray(data["data"], dtype=float),
                np.asarray(data["indices"], dtype=np.int64),
                np.asarray(data["indptr"], dtype=np.int64),
            ),
            shape=tuple(np.asarray(data["shape"], dtype=np.int64).tolist()),
        )
        rhs = np.asarray(data["rhs"], dtype=float)
        direct = np.asarray(data["direct"], dtype=float)
    metadata = json.loads((input_dir / METADATA_FILE).read_text(encoding="utf-8"))
    return matrix, rhs, direct, metadata


def _candidate_options(name: str) -> tuple[NonlinearRobustnessOptions, bool, dict[str, Any]]:
    if name == "direct":
        return NonlinearRobustnessOptions(linear_solver="direct", linear_direct_fallback=False), False, {}
    if name.startswith("cg-"):
        rtol = float(name.removeprefix("cg-"))
        return NonlinearRobustnessOptions(
            linear_solver="cg",
            linear_preconditioner="jacobi",
            linear_assume_spd=True,
            linear_rtol=rtol,
            linear_direct_fallback=False,
        ), True, {"rtol": rtol}
    if name.startswith("minres-"):
        rtol = float(name.removeprefix("minres-"))
        return NonlinearRobustnessOptions(
            linear_solver="minres",
            linear_preconditioner="jacobi",
            linear_rtol=rtol,
            linear_direct_fallback=False,
        ), True, {"rtol": rtol}
    if name == "gmres-ilu-a":
        return NonlinearRobustnessOptions(
            linear_solver="gmres",
            linear_preconditioner="ilu",
            linear_direct_fallback=False,
            gmres_restart=50,
            ilu_drop_tol=1.0e-4,
            ilu_fill_factor=10.0,
        ), True, {"restart": 50, "drop_tol": 1.0e-4, "fill_factor": 10.0}
    if name == "gmres-ilu-b":
        return NonlinearRobustnessOptions(
            linear_solver="gmres",
            linear_preconditioner="ilu",
            linear_direct_fallback=False,
            gmres_restart=50,
            ilu_drop_tol=1.0e-5,
            ilu_fill_factor=10.0,
        ), True, {"restart": 50, "drop_tol": 1.0e-5, "fill_factor": 10.0}
    raise ValueError(f"Unknown R2 candidate {name!r}.")


def run_candidate(input_dir: Path, name: str, output_path: Path) -> None:
    matrix, rhs, direct, metadata = _load_input(input_dir)
    options, is_krylov, candidate_parameters = _candidate_options(name)
    before_rss, before_private = process_memory_bytes()
    started = perf_counter()
    error: str | None = None
    error_diagnostics: dict[str, Any] = {}
    diagnostics: dict[str, Any] = {}
    with _PeakSampler() as sampler:
        try:
            _, diagnostics = NonlinearLinearSolverAdapter(options).solve(
                matrix,
                rhs,
                reference_solution=direct,
                # R2 diagnostic runs use the normal scale-aware adapter
                # contract; raw residual is intentionally only recorded.
                allow_unverified_krylov=False,
            )
        except NumericalConvergenceError as exc:
            error = str(exc)
            error_diagnostics = dict(exc.diagnostics)
        finally:
            sleep(0.01)
    after_rss, after_private = process_memory_bytes()
    elapsed = perf_counter() - started
    solution_difference = diagnostics.get("solution_relative_difference")
    backward_error = diagnostics.get("backward_error_eta_inf")
    contract_satisfied = bool(diagnostics.get("post_solve_residual_contract_satisfied", False))
    accepted = (
        error is None
        and solution_difference is not None
        and float(solution_difference) <= 1.0e-8
        and backward_error is not None
        and float(backward_error) <= 1.0e-10
        and np.isfinite(float(solution_difference))
        and np.isfinite(float(backward_error))
    )
    result: dict[str, Any] = {
        "schema_version": 1,
        "record_id": "QF-SOLVER-0.2.9-LINEAR-SOLVER-REMEDIATION-R2-CANDIDATE-001",
        "source_sha": START_SHA,
        "candidate": name,
        "matrix": metadata,
        "candidate_parameters": candidate_parameters,
        "status": "PASS_R2_EQUIVALENCE" if accepted else "FAIL_R2_EQUIVALENCE" if error is None else "SOLVER_FAILURE",
        "error": error,
        "error_diagnostics": error_diagnostics,
        "diagnostics": diagnostics,
        "r2_acceptance": {
            "solution_relative_difference_vs_direct": solution_difference,
            "backward_error_eta_inf": backward_error,
            "raw_relative_residual": diagnostics.get("raw_relative_residual"),
            "strict_residual_contract_satisfied": contract_satisfied,
            "accepted": accepted,
        },
        "timing": {
            "total_seconds": elapsed,
            "preconditioner_setup_seconds": diagnostics.get("preconditioner_setup_seconds"),
            "linear_solve_seconds": diagnostics.get("linear_solve_seconds"),
        },
        "memory": {
            "rss_before_solve_bytes": before_rss,
            "rss_after_solve_bytes": after_rss,
            "peak_rss_during_solve_bytes": sampler.peak_rss,
            "private_before_solve_bytes": before_private,
            "private_after_solve_bytes": after_private,
            "peak_private_during_solve_bytes": sampler.peak_private,
            "preconditioner_rss_before_bytes": diagnostics.get("preconditioner_rss_before_bytes"),
            "preconditioner_rss_after_bytes": diagnostics.get("preconditioner_rss_after_bytes"),
            "preconditioner_private_before_bytes": diagnostics.get("preconditioner_private_before_bytes"),
            "preconditioner_private_after_bytes": diagnostics.get("preconditioner_private_after_bytes"),
        },
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(_json_safe(result), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )


def aggregate(input_dir: Path, output_path: Path) -> None:
    candidates = {}
    for path in sorted(input_dir.glob("candidate-*.json")):
        candidates[path.stem.removeprefix("candidate-")] = json.loads(path.read_text(encoding="utf-8"))
    accepted = [name for name, row in candidates.items() if row.get("r2_acceptance", {}).get("accepted")]
    result = {
        "schema_version": 1,
        "record_id": "QF-SOLVER-0.2.9-LINEAR-SOLVER-REMEDIATION-R2-001",
        "source_sha": START_SHA,
        "status": "STAGE_B_CANDIDATES_RECORDED",
        "r2_contract": json.loads(
            (ROOT / "qualification" / "0_2_9" / "wp04_linear_solver_r2_contract.json").read_text(encoding="utf-8")
        ),
        "candidates": candidates,
        "accepted_stage_c_candidates": accepted,
        "stage_c": "NOT_STARTED_AUTOMATICALLY",
        "wp04_status": "HOLD",
        "g04_10": "UNRESOLVED_LINEAR_SOLVER_REMEDIATION",
        "validated_total": 29,
        "full_test_suite_run": False,
    }
    output_path.write_text(
        json.dumps(_json_safe(result), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )


def _stage_c_options(candidate: str) -> NonlinearRobustnessOptions:
    if candidate == "direct":
        return NonlinearRobustnessOptions(linear_solver="direct", linear_direct_fallback=False)
    if candidate == "cg-1e-10":
        return NonlinearRobustnessOptions(
            linear_solver="cg",
            linear_preconditioner="jacobi",
            linear_assume_spd=True,
            linear_rtol=1.0e-10,
            linear_direct_fallback=False,
        )
    raise ValueError(f"Unsupported Stage-C candidate {candidate!r}.")


def _array_digest(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def run_stage_c(candidate: str, output_path: Path) -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from solveur.core.analyses.geometric_nonlinear import _newton_dead_load
    from solveur.core.nonlinear.state import NonlinearState
    from tests.verification.test_wp04_c2_tet4_requalification import _case, _equilibrium, _observe

    case = _case("C2-M1")
    options = _stage_c_options(candidate)
    accepted: list[NonlinearState] = []
    events: list[dict[str, object]] = []
    telemetry_path = output_path.with_suffix(".jsonl")
    started = perf_counter()
    before_rss, before_private = process_memory_bytes()
    error: str | None = None
    error_diagnostics: dict[str, Any] = {}
    displacement: np.ndarray | None = None
    diagnostics: dict[str, Any] = {}
    with JsonlNonlinearTelemetry(telemetry_path) as telemetry, _PeakSampler() as sampler:
        try:
            displacement, diagnostics = _newton_dead_load(
                case["assembly"],
                case["external"],
                case["fixed"],
                increments=12,
                tolerance=1.0e-10,
                max_iterations=40,
                robustness_options=options,
                initial_state=NonlinearState(np.zeros(case["assembly"].ndof, dtype=float)),
                target_load_factors=[step / 12 for step in range(1, 13)],
                accepted_state_callback=lambda _step, state: accepted.append(state.detached_copy()),
                telemetry_observer=lambda event: events.append(dict(event)) or telemetry(event),
            )
        except NumericalConvergenceError as exc:
            error = str(exc)
            error_diagnostics = dict(exc.diagnostics)
        finally:
            sleep(0.01)
    after_rss, after_private = process_memory_bytes()
    elapsed = perf_counter() - started
    row: dict[str, Any] = {
        "schema_version": 1,
        "record_id": "QF-SOLVER-0.2.9-LINEAR-SOLVER-REMEDIATION-R2-STAGE-C-001",
        "source_sha": START_SHA,
        "candidate": candidate,
        "case": {"cells": [32, 16, 16], "full_dofs": 28611, "increments": 12},
        "status": "PASS_STAGE_C" if error is None else "SOLVER_FAILURE",
        "error": error,
        "error_diagnostics": error_diagnostics,
        "timing": {"total_seconds": elapsed},
        "memory": {
            "rss_before_bytes": before_rss,
            "rss_after_bytes": after_rss,
            "peak_rss_bytes": sampler.peak_rss,
            "private_before_bytes": before_private,
            "private_after_bytes": after_private,
            "peak_private_bytes": sampler.peak_private,
        },
        "telemetry": {"path": str(telemetry_path), "events": len(events)},
    }
    if displacement is not None:
        internal, _ = case["assembly"].assemble(displacement, tangent_required=False)
        observed, _ = _observe(case, displacement)
        observed["equilibrium"] = _equilibrium(case, displacement, internal)
        increment_rows = diagnostics.get("increments", [])
        total_linear_solves = 0
        iterative_success = 0
        direct_fallbacks = 0
        krylov_iterations = 0
        line_search_alphas: list[float] = []
        newton_iterations = 0
        if isinstance(increment_rows, list):
            for increment in increment_rows:
                if not isinstance(increment, dict):
                    continue
                newton_iterations += int(increment.get("iterations", 0))
                systems = increment.get("linear_system_diagnostics", [])
                if isinstance(systems, list):
                    for system in systems:
                        if not isinstance(system, dict):
                            continue
                        total_linear_solves += 1
                        method = str(system.get("linear_method", ""))
                        if method in {"cg", "minres", "gmres"}:
                            iterative_success += 1
                            krylov_iterations += int(system.get("krylov_iterations", 0))
                        if bool(system.get("fallback_used", False)):
                            direct_fallbacks += 1
                        alpha = system.get("line_search_alpha")
                        if isinstance(alpha, (int, float)):
                            line_search_alphas.append(float(alpha))
        row["observables"] = observed
        row["state"] = {
            "displacement_digest": _array_digest(displacement),
            "displacement_norm": float(np.linalg.norm(displacement)),
            "accepted_steps": len(accepted),
            "accepted_load_factors": [float(state.load_factor) for state in accepted],
            "accepted_digests": [state.digest for state in accepted],
            "final_digest": accepted[-1].digest if accepted else None,
        }
        row["newton_iterations"] = newton_iterations
        row["line_search_alphas"] = line_search_alphas
        row["linear_solves"] = {
            "total": total_linear_solves,
            "iterative_success": iterative_success,
            "direct_fallbacks": direct_fallbacks,
            "fallback_rate": direct_fallbacks / total_linear_solves if total_linear_solves else 0.0,
            "krylov_iterations": krylov_iterations,
        }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(_json_safe(row), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", type=Path)
    parser.add_argument("--candidate", choices=("direct", "cg-1e-10", "cg-1e-11", "cg-1e-12", "cg-1e-13", "minres-1e-10", "minres-1e-11", "minres-1e-12", "gmres-ilu-a", "gmres-ilu-b"))
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--aggregate", action="store_true")
    parser.add_argument("--stage-c", choices=("direct", "cg-1e-10"))
    args = parser.parse_args()
    if args.prepare is not None:
        prepare(args.prepare)
    elif args.aggregate:
        if args.input_dir is None or args.output is None:
            parser.error("--aggregate requires --input-dir and --output")
        aggregate(args.input_dir, args.output)
    elif args.candidate is not None:
        if args.input_dir is None or args.output is None:
            parser.error("--candidate requires --input-dir and --output")
        run_candidate(args.input_dir, args.candidate, args.output)
    elif args.stage_c is not None:
        if args.output is None:
            parser.error("--stage-c requires --output")
        run_stage_c(args.stage_c, args.output)
    else:
        parser.error("choose --prepare, --candidate or --aggregate")


if __name__ == "__main__":
    main()
