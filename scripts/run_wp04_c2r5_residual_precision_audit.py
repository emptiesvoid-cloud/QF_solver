"""C2R5 canonical M2 capture and offline residual-precision diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from time import perf_counter, process_time
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUTPUT = ROOT / "qualification" / "0_2_9" / "c2r5"
FORENSICS_ROOT = Path(tempfile.gettempdir()) / "qf_solver_029_c2r5_forensics"
INCREMENTS = 12
NEWTON_TOLERANCE = 1.0e-10
MAX_NEWTON_ITERATIONS = 40
MINRES_RTOL = 1.0e-11
MINRES_ATOL = 1.0e-14
MINRES_MAXITER = 10_000
BACKWARD_ERROR_TOLERANCE = 1.0e-10


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


def _local_internal_contributions(assembly: Any, displacement: np.ndarray) -> np.ndarray:
    """Recompute float64 element force contributions without altering assembly."""

    local_displacement = assembly._local_displacements(displacement)
    deformation, stress = assembly._kinematics(local_displacement)
    first_piola = np.einsum("miI,mIJ->miJ", deformation, stress, optimize=True)
    return assembly.volumes[:, None, None] * np.einsum(
        "miJ,maJ->mai", first_piola, assembly.gradients, optimize=True
    )


def _pairwise_sum(values: np.ndarray) -> float:
    work = np.asarray(values, dtype=float).copy()
    while work.size > 1:
        pairs = (work.size // 2) * 2
        reduced = np.sum(work[:pairs].reshape(-1, 2), axis=1, dtype=float)
        work = np.concatenate((reduced, work[pairs:]))
    return float(work[0]) if work.size else 0.0


def _accumulate_methods(
    assembly: Any,
    displacement: np.ndarray,
    target: np.ndarray,
    free: np.ndarray,
    scale: float,
) -> dict[str, Any]:
    contributions = _local_internal_contributions(assembly, displacement)
    edofs = np.asarray(assembly.element_dofs, dtype=np.int64)
    flat_dofs = edofs.ravel()
    flat_values = contributions.ravel()
    float64_internal = np.zeros(assembly.ndof, dtype=float)
    np.add.at(float64_internal, flat_dofs, flat_values)

    order = np.argsort(flat_dofs, kind="stable")
    sorted_dofs = flat_dofs[order]
    sorted_values = flat_values[order]
    unique, starts = np.unique(sorted_dofs, return_index=True)
    ends = np.concatenate((starts[1:], np.asarray([sorted_values.size], dtype=np.int64)))
    pairwise_internal = np.zeros(assembly.ndof, dtype=float)
    longdouble_internal = np.zeros(assembly.ndof, dtype=np.longdouble)
    compensated_internal = np.zeros(assembly.ndof, dtype=float)
    for dof, start, end in zip(unique, starts, ends):
        values = sorted_values[int(start) : int(end)]
        pairwise_internal[int(dof)] = _pairwise_sum(values)
        longdouble_internal[int(dof)] = np.sum(values, dtype=np.longdouble)
        total = 0.0
        correction = 0.0
        for value in values:
            adjusted = float(value) - correction
            updated = total + adjusted
            correction = (updated - total) - adjusted
            total = updated
        compensated_internal[int(dof)] = total

    def metric(internal: np.ndarray) -> dict[str, Any]:
        residual = np.asarray(target[free], dtype=np.longdouble) - np.asarray(internal[free], dtype=np.longdouble)
        absolute = float(np.sqrt(np.sum(residual * residual, dtype=np.longdouble)))
        return {"absolute_residual": absolute, "normalized_residual": absolute / scale}

    float64_metrics = metric(float64_internal)
    return {
        "float64": float64_metrics,
        "pairwise": metric(pairwise_internal),
        "compensated_kahan": metric(compensated_internal),
        "longdouble_accumulation": {
            **metric(longdouble_internal),
            "dtype": str(np.dtype(np.longdouble)),
            "itemsize": int(np.dtype(np.longdouble).itemsize),
        },
        "difference_from_float64": {
            "pairwise": float(np.linalg.norm(pairwise_internal[free] - float64_internal[free])),
            "compensated_kahan": float(np.linalg.norm(compensated_internal[free] - float64_internal[free])),
            "longdouble_accumulation": float(
                np.sqrt(
                    np.sum(
                        (np.asarray(longdouble_internal[free], dtype=np.longdouble) - float64_internal[free]) ** 2,
                        dtype=np.longdouble,
                    )
                )
            ),
        },
        "element_evaluation_precision": "float64; local constitutive/kinematic values were not recomputed in higher precision",
        "global_accumulation_precision": ["float64 np.add.at", "float64 pairwise", "float64 compensated Kahan", "longdouble sum of float64 local contributions"],
        "contribution_count": int(flat_values.size),
        "contributions_per_dof": {
            "min": int(np.min(np.bincount(flat_dofs, minlength=assembly.ndof))),
            "max": int(np.max(np.bincount(flat_dofs, minlength=assembly.ndof))),
            "mean": float(flat_values.size / assembly.ndof),
        },
        "max_abs_local_contribution": float(np.max(np.abs(flat_values), initial=0.0)),
        "sum_abs_internal_contributions_free_norm": float(
            np.linalg.norm(_sum_abs_by_dof(flat_dofs, flat_values)[free])
        ),
        "internal_float64": float64_internal,
        "contributions": contributions,
    }


def _sum_abs_by_dof(dofs: np.ndarray, values: np.ndarray) -> np.ndarray:
    result: np.ndarray = np.zeros(int(np.max(dofs, initial=-1)) + 1, dtype=float)
    np.add.at(result, dofs, np.abs(values))
    return result


def _capture(
    *,
    case: Mapping[str, Any],
    recording: Any,
    accepted: Any,
    load_factor: float,
    step: int,
    iteration: int,
) -> dict[str, Any]:
    free = np.setdiff1d(np.arange(recording.ndof), np.asarray(case["fixed"], dtype=int))
    tangent = csr_matrix(recording.last["tangent"])[free, :][:, free].tocsr()
    internal = np.asarray(recording.last["internal"], dtype=float)
    trial = np.asarray(recording.last["displacement"], dtype=float)
    target = load_factor * np.asarray(case["external"], dtype=float)
    rhs = (target - internal)[free]
    FORENSICS_ROOT.mkdir(parents=True, exist_ok=True)
    target_path = FORENSICS_ROOT / "c2_m2_canonical_step4_failure.npz"
    np.savez_compressed(
        target_path,
        data=np.asarray(tangent.data),
        indices=np.asarray(tangent.indices),
        indptr=np.asarray(tangent.indptr),
        shape=np.asarray(tangent.shape, dtype=np.int64),
        rhs=rhs,
        trial_displacement=trial,
        trial_internal_force=internal,
        accepted_displacement=np.asarray(accepted.displacement),
        external=np.asarray(case["external"], dtype=float),
        fixed=np.asarray(case["fixed"], dtype=np.int64),
        free=np.asarray(free, dtype=np.int64),
        load_factor=np.asarray([load_factor], dtype=float),
    )
    return {
        "path": str(target_path),
        "sha256": _sha256(target_path),
        "size_bytes": int(target_path.stat().st_size),
        "shape": [int(item) for item in tangent.shape],
        "nnz": int(tangent.nnz),
        "step": step,
        "newton_iteration": iteration,
        "load_factor": load_factor,
        "accepted_state_before_step": {
            "load_factor": float(accepted.load_factor),
            "displacement_norm": float(np.linalg.norm(accepted.displacement)),
            "digest": accepted.digest,
            "component_digests": accepted.component_digests,
        },
        "trial_displacement_norm": float(np.linalg.norm(trial)),
    }


def _linear_forensics(case: Mapping[str, Any], capture: Mapping[str, Any], direct_class: Any) -> dict[str, Any]:
    from solveur.core.nonlinear.linear_solver import NonlinearLinearSolverAdapter
    from solveur.core.nonlinear.robustness import NonlinearRobustnessOptions

    with np.load(str(capture["path"]), allow_pickle=False) as data:
        matrix = csr_matrix((data["data"], data["indices"], data["indptr"]), shape=tuple(data["shape"]))
        rhs = np.asarray(data["rhs"], dtype=float)
        trial = np.asarray(data["trial_displacement"], dtype=float)
        free = np.asarray(data["free"], dtype=int)
        load_factor = float(data["load_factor"][0])
    direct_options = NonlinearRobustnessOptions(
        linear_solver="direct", linear_preconditioner="none", linear_direct_fallback=False, line_search="existing"
    )
    direct_options.validate()
    minres_11_options = direct_class("minres", "jacobi", 1.0e-11)
    minres_12_options = direct_class("minres", "jacobi", 1.0e-12)
    direct, direct_diag = NonlinearLinearSolverAdapter(direct_options).solve(matrix, rhs)
    minres_11, minres_11_diag = NonlinearLinearSolverAdapter(minres_11_options).solve(
        matrix, rhs, reference_solution=direct
    )
    minres_12, minres_12_diag = NonlinearLinearSolverAdapter(minres_12_options).solve(
        matrix, rhs, reference_solution=direct
    )
    scale = max(float(np.linalg.norm((load_factor * np.asarray(case["external"]))[free])), 1.0)
    trial_scale = max(float(np.linalg.norm(trial)), 1.0e-14)

    def apply(correction: np.ndarray) -> dict[str, Any]:
        displacement = np.array(trial, copy=True)
        displacement[free] += correction
        normal_internal, _ = case["assembly"].assemble(displacement, tangent_required=False)
        accumulated = _accumulate_methods(case["assembly"], displacement, load_factor * case["external"], free, scale)
        normal_residual = float(np.linalg.norm((load_factor * case["external"] - normal_internal)[free]) / scale)
        return {
            "correction_norm": float(np.linalg.norm(correction)),
            "relative_correction_norm": float(np.linalg.norm(correction) / trial_scale),
            "normal_float64_residual_after": normal_residual,
            "precision_residuals_after": {
                key: value["normalized_residual"] for key, value in accumulated.items() if key in {"float64", "pairwise", "compensated_kahan", "longdouble_accumulation"}
            },
            "diagnostics": _jsonable({**direct_diag} if correction is direct else {}),
        }

    return {
        "direct": {"correction_norm": float(np.linalg.norm(direct)), "relative_correction_norm": float(np.linalg.norm(direct) / trial_scale), "diagnostics": direct_diag, "after": apply(direct)},
        "minres_rtol_1e11": {"correction_norm": float(np.linalg.norm(minres_11)), "relative_correction_norm": float(np.linalg.norm(minres_11) / trial_scale), "diagnostics": minres_11_diag, "after": apply(minres_11)},
        "minres_rtol_1e12": {"correction_norm": float(np.linalg.norm(minres_12)), "relative_correction_norm": float(np.linalg.norm(minres_12) / trial_scale), "diagnostics": minres_12_diag, "after": apply(minres_12)},
    }


def _build_options(cls: Any, method: str, rtol: float) -> Any:
    result = cls(
        linear_solver=method,
        linear_preconditioner="jacobi" if method == "minres" else "none",
        linear_rtol=rtol,
        linear_atol=MINRES_ATOL,
        linear_maxiter=MINRES_MAXITER,
        linear_residual_tolerance=BACKWARD_ERROR_TOLERANCE,
        linear_backward_error_tolerance=BACKWARD_ERROR_TOLERANCE,
        linear_direct_fallback=False,
        line_search="existing",
    )
    result.validate()
    return result


def main() -> int:
    sys.path.insert(0, str(SRC))
    sys.path.insert(0, str(ROOT))
    from solveur.core.analyses.geometric_nonlinear import _newton_dead_load
    from solveur.core.errors import NumericalConvergenceError
    from solveur.core.nonlinear.robustness import NonlinearRobustnessOptions
    from solveur.core.nonlinear.state import NonlinearState
    from solveur.core.nonlinear.telemetry import JsonlNonlinearTelemetry, process_memory_bytes
    from tests.verification.test_wp04_c2_tet4_requalification import _case
    from scripts.run_wp04_c2r4_near_tolerance_audit import _PeakProcessMemory, _RecordingAssembly

    OUTPUT.mkdir(parents=True, exist_ok=True)
    telemetry_path = OUTPUT / "m2_canonical_telemetry.jsonl"
    case = _case("C2-M2")
    recording = _RecordingAssembly(case["assembly"])
    accepted: list[NonlinearState] = []
    events: list[dict[str, Any]] = []
    started = perf_counter()
    started_cpu = process_time()
    failure: dict[str, Any] | None = None

    def observe(event: Mapping[str, object]) -> None:
        row = {**dict(event), "case": "C2-M2", "phase": "C2R5_CANONICAL"}
        events.append(_jsonable(row))
        telemetry(row)

    def accepted_callback(_step: int, state: NonlinearState) -> None:
        accepted.append(state.detached_copy())

    options = _build_options(NonlinearRobustnessOptions, "minres", MINRES_RTOL)
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
                failure = {"reason": exc.reason.value if exc.reason is not None else None, "message": str(exc), "diagnostics": _jsonable(exc.diagnostics)}
    if failure is None or failure["reason"] != "LINE_SEARCH_FAILURE" or recording.last is None or len(accepted) != 3:
        raise RuntimeError(f"C2R5 did not reproduce canonical M2 step-4 line-search failure: {failure}")
    diagnostics = failure["diagnostics"]
    step = int(diagnostics["step"])
    iteration = int(diagnostics["iterations"])
    load_factor = step / INCREMENTS
    capture = _capture(case=case, recording=recording, accepted=accepted[-1], load_factor=load_factor, step=step, iteration=iteration)

    with np.load(capture["path"], allow_pickle=False) as data:
        target = load_factor * np.asarray(data["external"], dtype=float)
        internal = np.asarray(data["trial_internal_force"], dtype=float)
        trial = np.asarray(data["trial_displacement"], dtype=float)
        free = np.asarray(data["free"], dtype=int)
    scale = max(float(np.linalg.norm(target[free])), 1.0)
    imbalance = target - internal
    ext_free = target[free]
    int_free = internal[free]
    imbalance_free = imbalance[free]
    ext_norm = float(np.linalg.norm(ext_free))
    int_norm = float(np.linalg.norm(int_free))
    imbalance_norm = float(np.linalg.norm(imbalance_free))
    ext_inf = float(np.max(np.abs(ext_free), initial=0.0))
    int_inf = float(np.max(np.abs(int_free), initial=0.0))
    imbalance_inf = float(np.max(np.abs(imbalance_free), initial=0.0))
    precision = _accumulate_methods(case["assembly"], trial, target, free, scale)
    raw_contributions = precision.pop("contributions")
    sum_abs = _sum_abs_by_dof(np.asarray(case["assembly"].element_dofs, dtype=np.int64).ravel(), raw_contributions.ravel())
    counts = np.bincount(np.asarray(case["assembly"].element_dofs, dtype=np.int64).ravel(), minlength=case["assembly"].ndof)
    epsilon = float(np.finfo(np.float64).eps)
    gamma = np.where(counts * epsilon < 1.0, (counts * epsilon) / (1.0 - counts * epsilon), np.inf)
    bound = gamma * sum_abs
    estimated_floor = float(np.linalg.norm(bound[free]) / scale)

    class _OptionFactory:
        def __new__(cls, method: str, preconditioner: str, rtol: float) -> Any:
            return _build_options(NonlinearRobustnessOptions, method, rtol)

    linear = _linear_forensics(case, capture, _OptionFactory)
    line_diag = diagnostics
    merits = [float(value) for value in line_diag.get("merit_history", [])]
    alphas = [float(0.5**index) for index in range(len(merits))]
    initial_merit = float(line_diag.get("initial_merit", line_diag.get("residual_final", 0.0)))
    line_trials = [
        {"alpha": alpha, "merit": merit, "normalized_merit": merit / scale, "delta_from_initial": merit - initial_merit, "relative_delta_from_initial": (merit - initial_merit) / max(abs(initial_merit), 1.0e-300)}
        for alpha, merit in zip(alphas, merits)
    ]
    result = {
        "schema_version": 1,
        "record_id": "QF-SOLVER-0.2.9-WP04-C2R5",
        "start_sha": "571b7f64450ec556e1f9a59ecc65826cf49675d5",
        "route": {"mesh": "C2-M2", "linear_solver": "MINRES", "preconditioner": "Jacobi", "rtol": MINRES_RTOL, "atol": MINRES_ATOL, "maxiter": MINRES_MAXITER, "direct_fallback": False, "line_search": "existing/enabled", "newton_tolerance": NEWTON_TOLERANCE, "increments": INCREMENTS},
        "reproduction": {"status": "REPRODUCED", "failure": failure, "accepted_step_count": len(accepted), "wall_time_s": perf_counter() - started, "cpu_time_s": process_time() - started_cpu, "telemetry_path": str(telemetry_path)},
        "capture": capture,
        "force_cancellation_free_dofs": {"target_external_norm_2": ext_norm, "internal_norm_2": int_norm, "imbalance_norm_2": imbalance_norm, "cancellation_indicator_2": (ext_norm + int_norm) / max(imbalance_norm, 1.0e-300), "target_external_norm_inf": ext_inf, "internal_norm_inf": int_inf, "imbalance_norm_inf": imbalance_inf, "cancellation_indicator_inf": (ext_inf + int_inf) / max(imbalance_inf, 1.0e-300), "norm_domain": "free DOFs; target external force is lambda*F_ext"},
        "precision_diagnostics": precision,
        "rounding_error_bound": {"machine_epsilon": epsilon, "model": "per-DOF gamma_n times sum of absolute float64 local contributions", "max_contributions_per_dof": int(np.max(counts)), "estimated_float64_residual_floor": estimated_floor, "observed_float64_residual": precision["float64"]["normalized_residual"], "observed_to_estimated_floor_ratio": precision["float64"]["normalized_residual"] / max(estimated_floor, 1.0e-300)},
        "same_state_linear_forensics": linear,
        "line_search_forensics": {"initial_merit": initial_merit, "trials": line_trials, "classification": "LINE_SEARCH_TRUE_REJECTION" if all(item["merit"] >= initial_merit for item in line_trials) else "LINE_SEARCH_NUMERICAL_FLOOR_REJECTION"},
        "trial_state": {"relative_correction_norm_direct": linear["direct"]["relative_correction_norm"], "normal_float64_residual_before": precision["float64"]["normalized_residual"], "trial_displacement_norm": float(np.linalg.norm(trial))},
        "memory": {"peak_rss_process": memory.peak_rss, "peak_private_or_uss_process": memory.peak_private, "telemetry_sample_peak_rss": max((int(item["RSS_bytes"]) for item in events if isinstance(item.get("RSS_bytes"), int)), default=None), "telemetry_sample_peak_private": max((int(item["private_or_USS_bytes"]) for item in events if isinstance(item.get("private_or_USS_bytes"), int)), default=None)},
        "governance": {"wp04_status": "HOLD", "g04_10": "UNRESOLVED", "wp04_points": "0/12", "validated_total": "29/100", "m3_run": False, "m4_run": False, "petsc_work": False, "thresholds_changed": False, "mechanics_changed": False},
    }
    _write_json(OUTPUT / "residual_precision_audit.json", result)
    print(json.dumps(_jsonable(result), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
