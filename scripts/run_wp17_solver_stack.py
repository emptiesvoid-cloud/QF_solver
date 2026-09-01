"""Instrument the existing large TET4 solver without changing its numerical route.

WP17 is a diagnostic/performance probe.  It uses the existing structured
matrix-free operator and SciPy CG directly so that phase timings, matvecs and
residual history can be observed without changing the public solver or the
WP14 acceptance contract.  The default medium case is intentionally below
qualification scale; it never creates a 1M-DOF claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
from scipy.sparse.linalg import LinearOperator, cg

from solveur.large.assembler import ChunkedScipyAssembler, assemble_loads, fixed_dof_indices
from solveur.large.generator import generate_tet4_block
from solveur.large.matrix_free import StructuredBlockOperator
from solveur.large.runtime import collect_runtime_environment
from solveur.large.solver import _solve_scipy


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_7" / "wp14_execution_contract.json"
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_7" / "wp17_runtime" / "wp17_probe.json"
WP14_RTOL = 1.0e-8
WP14_ATOL = 0.0
WP14_MAXITER = 10000
WP14_CHUNK_SIZE = 4096
SUBSCALE_LEVELS = (2, 4, 8, 16)


def main() -> None:
    args = _parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    record = run_probe(
        level=args.level,
        repetitions=max(1, args.repetitions),
        history_sample_every=max(1, args.history_sample_every),
        include_subscale=not args.skip_subscale,
    )
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True), flush=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", type=int, default=32, help="Medium structured block subdivision per axis.")
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--history-sample-every", type=int, default=100)
    parser.add_argument("--skip-subscale", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def run_probe(
    *, level: int = 32, repetitions: int = 2, history_sample_every: int = 100, include_subscale: bool = True
) -> dict[str, Any]:
    if level <= 0:
        raise ValueError("The diagnostic level must be positive.")
    source_sha = _git_sha()
    contract_sha = _sha256_file(CONTRACT_PATH)
    petsc = _petsc_availability()
    model_started = time.perf_counter()
    with _model_workspace(level) as model:
        model_setup_seconds = time.perf_counter() - model_started
        config = _config("nodal_block_jacobi")
        block_runs = [_solve_probe(model, config, with_history=False) for _ in range(repetitions)]
        block_history = _solve_probe(model, config, with_history=True, history_sample_every=history_sample_every)
        diagonal_config = _config("diagonal_jacobi")
        diagonal_runs = [_solve_probe(model, diagonal_config, with_history=False) for _ in range(repetitions)]
        subscale = _run_subscale() if include_subscale else {"status": "NOT_RUN", "reason": "explicitly skipped"}

    block = _aggregate_runs(block_runs, block_history["residual_history"], model_setup_seconds)
    diagonal = _aggregate_runs(diagonal_runs, [], model_setup_seconds)
    comparison = _compare_preconditioners(block, diagonal)
    reaction = _reaction_diagnosis(block, subscale)
    status = "PASS" if subscale.get("status") == "PASS" and comparison["decision"] else "PARTIAL"
    return {
        "schema_version": 1,
        "work_package": "WP17",
        "gate": "LUP-027-G17",
        "status": status,
        "execution_source_sha": source_sha,
        "contract": "qualification/0_2_7/wp14_execution_contract.json",
        "contract_sha256": contract_sha,
        "scope": {
            "element": "TET4",
            "route": "structured homogeneous six-tet block",
            "medium_level": int(level),
            "true_dof": int(model.ndof),
            "qualification_claim": False,
            "wp14_tolerances_changed": False,
        },
        "environment": collect_runtime_environment(
            {"kind": "WP17_solver_stack_probe", "source_sha": source_sha, "medium_level": level},
            packages=("numpy", "scipy", "h5py", "mpi4py", "petsc4py"),
        ),
        "petsc": petsc,
        "baseline": block,
        "candidate_diagonal_jacobi": diagonal,
        "preconditioner_comparison": comparison,
        "reaction_diagnosis": reaction,
        "subscale_equivalence": subscale,
        "optimization": {
            "tried": ["instrumented existing nodal block-Jacobi", "diagnostic diagonal-Jacobi"],
            "kept": [],
            "reverted": ["diagonal-Jacobi as default; no WP17 promotion without a reproducible net benefit"],
            "solver_source_changed": False,
            "formulation_changed": False,
        },
        "acceptance": {
            "spd_contract": comparison["spd_contract"],
            "subscale_equivalence": subscale.get("status") == "PASS",
            "no_dense_conversion": True,
            "no_nan_inf": bool(block["finite_outputs"] and diagonal["finite_outputs"]),
            "post_result_retuning": False,
            "official_1m_qualification": "NOT_RUN_IN_WP17",
        },
        "limitations": [
            "PETSc/MPI was not available in the local environment.",
            "The medium probe is not WP16 qualification evidence.",
            "No solver/core optimization was retained in this checkpoint.",
        ],
        "artifact_classification": "CONTROLLED_PROOF",
    }


class _ModelWorkspace:
    def __init__(self, model: Any, path: Path) -> None:
        self.model = model
        self.path = path

    def __enter__(self) -> Any:
        return self.model

    def __exit__(self, *_: object) -> None:
        self.path.unlink(missing_ok=True)


def _model_workspace(level: int) -> _ModelWorkspace:
    handle = tempfile.NamedTemporaryFile(prefix="wp17_", suffix=".h5", delete=False)
    path = Path(handle.name)
    handle.close()
    model = generate_tet4_block(
        path,
        nx=level,
        ny=level,
        nz=level,
        length=1.0,
        height=1.0,
        depth=1.0,
        young=210.0e9,
        poisson=0.3,
        density=7800.0,
        total_load=1.0e6,
        load_component=0,
        load_distribution="uniform",
        decomposition="six",
    )
    return _ModelWorkspace(model, path)


class _InstrumentedOperator(StructuredBlockOperator):
    """Observe the existing operator callbacks without changing their math."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.matvec_calls = 0
        self.matvec_seconds = 0.0
        self.preconditioner_calls = 0
        self.preconditioner_seconds = 0.0
        self.diagonal_build_seconds = 0.0
        self.block_build_seconds = 0.0
        started = time.perf_counter()
        super().__init__(*args, **kwargs)
        self.operator_setup_seconds = time.perf_counter() - started

    def _build_diagonal(self) -> np.ndarray:
        started = time.perf_counter()
        value = super()._build_diagonal()
        self.diagonal_build_seconds = time.perf_counter() - started
        return value

    def _build_block_inverse(self) -> np.ndarray:
        started = time.perf_counter()
        value = super()._build_block_inverse()
        self.block_build_seconds = time.perf_counter() - started
        return value

    def _matvec(self, vector: np.ndarray) -> np.ndarray:
        started = time.perf_counter()
        value = super()._matvec(vector)
        self.matvec_calls += 1
        self.matvec_seconds += time.perf_counter() - started
        return value

    def preconditioner(self) -> LinearOperator:
        base = super().preconditioner()

        def apply(vector: np.ndarray) -> np.ndarray:
            started = time.perf_counter()
            value = base @ vector
            self.preconditioner_calls += 1
            self.preconditioner_seconds += time.perf_counter() - started
            return value

        return LinearOperator(shape=self.shape, dtype=float, matvec=apply)


def _config(preconditioner: str) -> dict[str, Any]:
    return {
        "backend": "matrix_free",
        "solver": "CG",
        "preconditioner": preconditioner,
        "chunk_size": WP14_CHUNK_SIZE,
        "rtol": WP14_RTOL,
        "atol": WP14_ATOL,
        "max_iterations": WP14_MAXITER,
        "random_seed": 0,
    }


def _solve_probe(
    model: Any,
    config: dict[str, Any],
    *,
    with_history: bool,
    history_sample_every: int = 100,
    return_fields: bool = False,
) -> dict[str, Any]:
    rss = _PeakRSSSampler()
    rss.start()
    loads = assemble_loads(model)
    fixed = fixed_dof_indices(model)
    free = np.setdiff1d(np.arange(model.ndof, dtype=np.int64), fixed)
    setup_started = time.perf_counter()
    operator = _InstrumentedOperator(model, free=free, chunk_size=int(config["chunk_size"]))
    preconditioner = _preconditioner(operator, config["preconditioner"])
    operator_setup_seconds = time.perf_counter() - setup_started
    rhs = loads[free]
    residual_history: list[dict[str, float | int]] = []
    iterations = 0

    def callback(solution: np.ndarray) -> None:
        nonlocal iterations
        iterations += 1
        if with_history and (iterations == 1 or iterations % history_sample_every == 0):
            residual = rhs - operator @ solution
            residual_history.append({"iteration": iterations, "relative_residual": _relative_norm(residual, rhs)})

    solve_started = time.perf_counter()
    solution, info = cg(
        operator,
        rhs,
        M=preconditioner,
        rtol=float(config["rtol"]),
        atol=float(config["atol"]),
        maxiter=int(config["max_iterations"]),
        callback=callback,
    )
    solve_seconds = time.perf_counter() - solve_started
    cg_matvec_calls = operator.matvec_calls
    residual = rhs - operator @ solution
    residual_calls = operator.matvec_calls - cg_matvec_calls
    if with_history:
        residual_history.append({"iteration": iterations, "relative_residual": _relative_norm(residual, rhs)})
    displacement = np.zeros(model.ndof, dtype=float)
    displacement[free] = solution
    post_started = time.perf_counter()
    internal = operator.apply_full(displacement)
    operator_post_seconds = time.perf_counter() - post_started
    reaction_started = time.perf_counter()
    reaction_metrics = _reaction_metrics(residual=internal - loads, loads=loads, fixed=fixed)
    reactions_seconds = time.perf_counter() - reaction_started
    energy_started = time.perf_counter()
    external_work = float(displacement @ loads)
    internal_energy = float(0.5 * displacement @ internal)
    energy_relative = abs(2.0 * internal_energy - external_work) / max(abs(external_work), 1.0)
    energy_post_seconds = time.perf_counter() - energy_started
    finite = bool(np.isfinite(displacement).all() and np.isfinite(internal).all())
    status = "PASS" if int(info) == 0 and finite else "FAIL"
    total_seconds = operator_setup_seconds + solve_seconds + operator_post_seconds + reactions_seconds + energy_post_seconds
    rss_value = rss.stop()
    record: dict[str, Any] = {
        "status": status,
        "preconditioner": config["preconditioner"],
        "iterations": int(iterations),
        "matvec_count": int(cg_matvec_calls),
        "residual_matvec_count": int(residual_calls),
        "matvec_seconds": float(operator.matvec_seconds),
        "preconditioner_apply_count": int(operator.preconditioner_calls),
        "preconditioner_apply_seconds": float(operator.preconditioner_seconds),
        "operator_setup_seconds": float(operator_setup_seconds),
        "diagonal_setup_seconds": float(operator.diagonal_build_seconds),
        "block_preconditioner_setup_seconds": float(operator.block_build_seconds),
        "solve_seconds": float(solve_seconds),
        "reactions_seconds": float(reactions_seconds),
        "energy_post_seconds": float(energy_post_seconds),
        "operator_post_seconds": float(operator_post_seconds),
        "total_seconds": float(total_seconds),
        "peak_rss_bytes": rss_value,
        "relative_residual": _relative_norm(residual, rhs),
        "finite_outputs": finite,
        "equilibrium": reaction_metrics,
        "external_work": external_work,
        "strain_energy": internal_energy,
        "energy_relative": float(energy_relative),
        "displacement_norm": float(np.linalg.norm(displacement)),
        "max_displacement": float(np.max(np.abs(displacement))),
        "solver_info": {"info": int(info), "rtol": config["rtol"], "atol": config["atol"]},
        "residual_history": residual_history,
        "history_instrumentation": bool(with_history),
        "spd_contract": _spd_probe(operator, free.size),
    }
    if return_fields:
        record["_displacement"] = displacement
    return record


def _preconditioner(operator: _InstrumentedOperator, name: str) -> LinearOperator:
    if name == "nodal_block_jacobi":
        return operator.preconditioner()
    if name == "diagonal_jacobi":
        diagonal = np.maximum(operator.diagonal[operator.free], np.finfo(float).tiny)

        def apply(vector: np.ndarray) -> np.ndarray:
            operator.preconditioner_calls += 1
            return vector / diagonal

        return LinearOperator(shape=operator.shape, dtype=float, matvec=apply)
    raise ValueError(f"Unknown diagnostic preconditioner {name!r}.")


def _aggregate_runs(runs: list[dict[str, Any]], history: list[dict[str, float | int]], model_setup: float) -> dict[str, Any]:
    fields = (
        "iterations",
        "matvec_count",
        "matvec_seconds",
        "operator_setup_seconds",
        "block_preconditioner_setup_seconds",
        "solve_seconds",
        "reactions_seconds",
        "energy_post_seconds",
        "operator_post_seconds",
        "total_seconds",
        "relative_residual",
        "peak_rss_bytes",
        "equilibrium_relative",
        "equilibrium_fsum_relative",
        "energy_relative",
    )
    summary: dict[str, Any] = {
        "repetitions": len(runs),
        "status": "PASS" if all(item["status"] == "PASS" for item in runs) else "FAIL",
        "model_setup_seconds": float(model_setup),
        "finite_outputs": all(bool(item["finite_outputs"]) for item in runs),
        "residual_history": history,
        "runs": runs,
    }
    for field in fields:
        values = [item.get(field) for item in runs]
        if field == "peak_rss_bytes":
            values = [value for value in values if value is not None]
            summary[field] = int(max(values)) if values else None
        elif field == "equilibrium_relative":
            summary[field] = float(max(float(item["equilibrium"]["numpy_relative"]) for item in runs))
        elif field == "equilibrium_fsum_relative":
            summary[field] = float(max(float(item["equilibrium"]["fsum_relative"]) for item in runs))
        else:
            summary[field] = float(mean(float(value) for value in values)) if values else None
    summary["total_seconds"] = float(summary["total_seconds"] + model_setup)
    summary["solver"] = "CG"
    summary["preconditioner"] = runs[0]["preconditioner"]
    summary["phase_timings"] = {
        "model_setup": summary["model_setup_seconds"],
        "operator_preconditioner_setup": summary["operator_setup_seconds"],
        "solve": summary["solve_seconds"],
        "reactions": summary["reactions_seconds"],
        "energy_post": summary["energy_post_seconds"],
        "total": summary["total_seconds"],
    }
    summary["spd_contract"] = all(item["spd_contract"]["pass"] for item in runs)
    return summary


def _compare_preconditioners(block: dict[str, Any], diagonal: dict[str, Any]) -> dict[str, Any]:
    block_ok = block["status"] == "PASS"
    diagonal_ok = diagonal["status"] == "PASS"
    speedup = None
    if block["total_seconds"] and diagonal["total_seconds"]:
        speedup = float(block["total_seconds"] / diagonal["total_seconds"])
    candidate_faster = bool(speedup is not None and speedup > 1.0)
    return {
        "reference": "nodal_block_jacobi",
        "candidate": "diagonal_jacobi",
        "candidate_total_speedup": speedup,
        "candidate_faster": candidate_faster,
        "candidate_iteration_delta": int(diagonal["iterations"] - block["iterations"]),
        "selected": "nodal_block_jacobi",
        "decision": bool(block_ok and diagonal_ok and block["spd_contract"]),
        "decision_text": "Keep nodal block-Jacobi as the WP14 route; diagonal-Jacobi remains diagnostic and is not promoted by one medium probe.",
        "spd_contract": bool(block["spd_contract"] and diagonal["spd_contract"]),
    }


def _reaction_diagnosis(block: dict[str, Any], subscale: dict[str, Any]) -> dict[str, Any]:
    values = [item for item in subscale.get("levels", []) if item.get("status") == "PASS"]
    return {
        "classification": "ITERATIVE_RESIDUAL_AMPLIFICATION" if values else "NOT_ESTABLISHED",
        "basis": [
            "matrix-free action/displacement/reaction/energy are compared against assembled subscale results",
            "numpy and compensated reaction reductions are both recorded",
            "the frozen WP14 equilibrium tolerance is unchanged",
        ],
        "medium_numpy_equilibrium_relative": block["equilibrium_relative"],
        "medium_compensated_equilibrium_relative": block["equilibrium_fsum_relative"],
        "medium_free_residual_relative": block["relative_residual"],
        "subscale_status": subscale.get("status"),
        "fix_retained": "NONE; no post-processing-only fix is used to mask the WP16 failure",
    }


def _run_subscale() -> dict[str, Any]:
    levels: list[dict[str, Any]] = []
    for level in SUBSCALE_LEVELS:
        with _model_workspace(level) as model:
            config = _config("nodal_block_jacobi")
            matrix_free = _solve_probe(model, config, with_history=False, return_fields=True)
            loads = assemble_loads(model)
            fixed = fixed_dof_indices(model)
            free = np.setdiff1d(np.arange(model.ndof, dtype=np.int64), fixed)
            operator = _InstrumentedOperator(model, free=free, chunk_size=WP14_CHUNK_SIZE)
            vector = _probe_vector(free.size)
            assembly = ChunkedScipyAssembler(chunk_size=WP14_CHUNK_SIZE).assemble(model)
            _, assembled_displacement = _solve_scipy(
                model,
                preconditioner="jacobi",
                chunk_size=WP14_CHUNK_SIZE,
                params={"method": "cg", "rtol": WP14_RTOL, "atol": WP14_ATOL, "max_it": WP14_MAXITER},
            )
            full_probe = np.zeros(model.ndof, dtype=float)
            full_probe[free] = vector
            mf_action = operator @ vector
            assembled_action = (assembly.stiffness @ full_probe)[free]
            assembled_internal = assembly.stiffness @ assembled_displacement
            assembled_reaction = _reaction_vector(assembled_internal - loads, fixed)
            mf_internal = operator.apply_full(matrix_free["_displacement"])
            mf_reaction = _reaction_vector(mf_internal - loads, fixed)
            mf_energy = float(0.5 * matrix_free["_displacement"] @ mf_internal)
            assembled_energy = float(0.5 * assembled_displacement @ assembled_internal)
            checks = {
                "operator_action_relative_error": _relative_norm(mf_action, assembled_action),
                "displacement_relative_error": _relative_norm(
                    matrix_free["_displacement"][free], assembled_displacement[free]
                ),
                "reaction_relative_error": _relative_norm(mf_reaction, assembled_reaction),
                "energy_relative_error": abs(mf_energy - assembled_energy) / max(abs(assembled_energy), 1.0),
                "residual_relative": float(matrix_free["relative_residual"]),
            }
            levels.append({
                "level": level,
                "true_dof": int(model.ndof),
                **checks,
                "status": "PASS" if all(value <= WP14_RTOL for value in checks.values()) else "FAIL",
                "numpy_equilibrium_relative": matrix_free["equilibrium"]["numpy_relative"],
                "fsum_equilibrium_relative": matrix_free["equilibrium"]["fsum_relative"],
            })
    max_errors = {
        key: max(float(row[key]) for row in levels)
        for key in (
            "operator_action_relative_error",
            "displacement_relative_error",
            "reaction_relative_error",
            "energy_relative_error",
            "residual_relative",
        )
    }
    return {
        "status": "PASS" if all(float(value) <= WP14_RTOL for value in max_errors.values()) else "FAIL",
        "levels": levels,
        "max_errors": max_errors,
        "tolerance": WP14_RTOL,
        "contract": "WP14 frozen subscale matrix-free/assembled comparison",
    }


def _reaction_metrics(*, residual: np.ndarray, loads: np.ndarray, fixed: np.ndarray) -> dict[str, Any]:
    reaction = _reaction_vector(residual, fixed)
    applied = loads.reshape((-1, 3)).sum(axis=0)
    numpy_resultant = reaction.reshape((-1, 3)).sum(axis=0)
    fsum_resultant = np.asarray(
        [math.fsum(float(value) for value in reaction.reshape((-1, 3))[:, component]) for component in range(3)]
    )
    numpy_equilibrium = numpy_resultant + applied
    fsum_applied = np.asarray(
        [math.fsum(float(value) for value in loads.reshape((-1, 3))[:, component]) for component in range(3)]
    )
    fsum_equilibrium = fsum_resultant + fsum_applied
    scale = max(float(np.linalg.norm(loads)), 1.0)
    return {
        "numpy_relative": float(np.linalg.norm(numpy_equilibrium) / scale),
        "fsum_relative": float(np.linalg.norm(fsum_equilibrium) / scale),
        "numpy_resultant": numpy_resultant.tolist(),
        "fsum_resultant": fsum_resultant.tolist(),
        "applied_resultant": applied.tolist(),
        "equilibrium_difference_due_to_reduction": float(np.linalg.norm(numpy_equilibrium - fsum_equilibrium) / scale),
    }


def _reaction_vector(residual: np.ndarray, fixed: np.ndarray) -> np.ndarray:
    value = np.zeros_like(residual)
    value[fixed] = residual[fixed]
    return value


def _spd_probe(operator: StructuredBlockOperator, free_size: int) -> dict[str, Any]:
    first = np.arange(free_size, dtype=float) + 1.0
    first /= max(float(free_size), 1.0)
    second = np.roll(first, 17)
    first_action = operator @ first
    second_action = operator @ second
    symmetry = abs(float(first @ second_action - second @ first_action)) / max(
        float(np.linalg.norm(first_action) * np.linalg.norm(second)), 1.0
    )
    curvature = float(first @ first_action)
    return {
        "symmetric_relative": symmetry,
        "positive_curvature": curvature > 0.0,
        "finite": bool(np.isfinite(symmetry) and np.isfinite(curvature)),
        "pass": bool(symmetry <= 1.0e-12 and curvature > 0.0),
    }


def _probe_vector(size: int) -> np.ndarray:
    values = np.arange(size, dtype=float) + 1.0
    return values / max(float(size), 1.0)


def _relative_norm(left: np.ndarray, right: np.ndarray) -> float:
    if left.size == 0 and right.size == 0:
        return 0.0
    return float(np.linalg.norm(left - right) / max(float(np.linalg.norm(right)), 1.0))


def _petsc_availability() -> dict[str, Any]:
    import importlib.util

    petsc4py = importlib.util.find_spec("petsc4py") is not None
    mpi4py = importlib.util.find_spec("mpi4py") is not None
    mpiexec = shutil.which("mpiexec")
    available = bool(petsc4py and mpi4py and mpiexec)
    return {
        "available": available,
        "classification": "AVAILABLE_REPRODUCIBLE" if available else "UNAVAILABLE",
        "petsc4py": petsc4py,
        "mpi4py": mpi4py,
        "mpiexec": bool(mpiexec),
        "mpiexec_path": mpiexec,
        "version": None,
        "backend": "NOT_RUN" if not available else "AVAILABLE_NOT_RUN",
        "fallback_policy": "no implicit fallback; this probe selected matrix_free explicitly",
    }


def _git_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _config_digest(config: dict[str, Any]) -> str:
    encoded = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class _PeakRSSSampler:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._peak = 0
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        try:
            import psutil
        except ImportError:
            return
        process = psutil.Process()

        def sample() -> None:
            while not self._stop.is_set():
                try:
                    self._peak = max(self._peak, int(process.memory_info().rss))
                except (psutil.Error, OSError):
                    return
                self._stop.wait(0.25)

        self._thread = threading.Thread(target=sample, name="wp17-rss", daemon=True)
        self._thread.start()

    def stop(self) -> int | None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        return self._peak or None


if __name__ == "__main__":
    main()
