"""Small, reproducible WP15 matrix-free TET4 benchmark.

The benchmark deliberately stops at subscale sizes.  It records a baseline
before the matrix-free patch and a final record afterwards; it never claims
the WP16 one-million-DOF qualification.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import tracemalloc
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse.linalg import LinearOperator, cg

from solveur.large.assembler import ChunkedScipyAssembler, assemble_loads, fixed_dof_indices
from solveur.large.generator import generate_tet4_block
from solveur.large.matrix_free import StructuredBlockOperator, solve_structured_matrix_free
from solveur.large.model import LargeModel
from solveur.large.solver import _solve_scipy


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_7" / "wp15_matrix_free_benchmark.json"
WP14_CHUNK_SIZE = 4096
WP14_RTOL = 1.0e-8
WP14_ATOL = 0.0
WP14_MAXITER = 10000
LEVELS = (2, 4, 8, 16)


def main() -> None:
    args = _parse_args()
    output = Path(args.output)
    record = _run_phase(args.phase, output, repetitions=args.repetitions, source_sha=args.source_sha)
    print(json.dumps(record, indent=2, sort_keys=True))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("baseline", "final"), required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--source-sha", default=None, help="Override provenance when replaying a detached source tree.")
    return parser.parse_args()


def _run_phase(phase: str, output: Path, *, repetitions: int, source_sha: str | None) -> dict[str, Any]:
    repetitions = max(1, int(repetitions))
    phase_record = {
        "source_sha": source_sha or _git_sha(),
        "phase": phase,
        "parameters": {
            "chunk_size": WP14_CHUNK_SIZE,
            "rtol": WP14_RTOL,
            "atol": WP14_ATOL,
            "maxiter": WP14_MAXITER,
            "levels": list(LEVELS),
            "load_distribution": "uniform",
            "decomposition": "six",
            "total_load": 1.0e6,
            "material": {"E": 210.0e9, "nu": 0.3, "density": 7800.0},
            "measurement_repetitions": repetitions,
        },
        "levels": [_measure_level(level, repetitions=repetitions) for level in LEVELS],
    }
    if phase == "baseline":
        document = {"schema_version": 1, "baseline": phase_record}
    else:
        if not output.exists():
            raise FileNotFoundError(f"Baseline benchmark is required before final phase: {output}")
        document = json.loads(output.read_text(encoding="utf-8"))
        document["final"] = phase_record
        document["comparison"] = _compare_phases(document["baseline"], phase_record)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return document


def _measure_level(level: int, *, repetitions: int) -> dict[str, Any]:
    with _model_workspace(level) as model:
        loads = assemble_loads(model)
        fixed = fixed_dof_indices(model)
        free = np.setdiff1d(np.arange(model.ndof, dtype=np.int64), fixed)
        setup_started = time.perf_counter()
        operator = StructuredBlockOperator(model, free=free, chunk_size=WP14_CHUNK_SIZE)
        setup_seconds = time.perf_counter() - setup_started
        vector = _probe_vector(free.size)
        matvec = _measure_matvec(operator, vector, repetitions)
        solve_started = time.perf_counter()
        matrix_free = solve_structured_matrix_free(
            model,
            chunk_size=WP14_CHUNK_SIZE,
            rtol=WP14_RTOL,
            atol=WP14_ATOL,
            maxiter=WP14_MAXITER,
        )
        total_solve_seconds = time.perf_counter() - solve_started
        diagnostics = _matrix_free_diagnostics(model, operator, matrix_free.displacement, loads, fixed)
        preconditioner = _preconditioner_comparison(operator, loads[free])
        assembled = _assembled_comparison(model, operator, free, matrix_free.displacement, vector)
        return {
            "level": level,
            "node_count": model.node_count,
            "element_count": model.element_count,
            "ndof": model.ndof,
            "free_dof": int(free.size),
            "setup_seconds": setup_seconds,
            "total_solve_seconds": total_solve_seconds,
            "solve_time_seconds": matrix_free.solve_time_seconds,
            "solver_info": matrix_free.solver_info,
            "operator_memory_bytes": matrix_free.operator_memory_bytes,
            "rss_bytes": _rss_bytes(),
            "matvec": matvec,
            "preconditioner": preconditioner,
            "diagnostics": diagnostics,
            "assembled_equivalence": assembled,
        }


class _ModelWorkspace:
    def __init__(self, model: LargeModel, path: Path) -> None:
        self.model = model
        self.path = path

    def __enter__(self) -> LargeModel:
        return self.model

    def __exit__(self, *_: object) -> None:
        self.path.unlink(missing_ok=True)


def _model_workspace(level: int) -> _ModelWorkspace:
    import tempfile

    dimensions = (level, level, level)
    handle = tempfile.NamedTemporaryFile(prefix="wp15_", suffix=".h5", delete=False)
    path = Path(handle.name)
    handle.close()
    model = generate_tet4_block(
        path,
        nx=dimensions[0],
        ny=dimensions[1],
        nz=dimensions[2],
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


def _probe_vector(size: int) -> np.ndarray:
    values = np.arange(size, dtype=float) + 1.0
    return values / max(float(size), 1.0)


def _measure_matvec(operator: StructuredBlockOperator, vector: np.ndarray, repetitions: int) -> dict[str, Any]:
    for _ in range(2):
        operator @ vector
    tracemalloc.start()
    started = time.perf_counter()
    for _ in range(max(1, repetitions)):
        result = operator @ vector
    elapsed = time.perf_counter() - started
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "repetitions": max(1, repetitions),
        "total_seconds": elapsed,
        "seconds_per_matvec": elapsed / max(1, repetitions),
        "result_norm": float(np.linalg.norm(result)),
        "python_allocation_current_bytes": int(current),
        "python_allocation_peak_bytes": int(peak),
        "allocation_peak_bytes_per_matvec": peak / max(1, repetitions),
    }


def _matrix_free_diagnostics(
    model: LargeModel,
    operator: StructuredBlockOperator,
    displacement: np.ndarray,
    loads: np.ndarray,
    fixed: np.ndarray,
) -> dict[str, float]:
    internal = operator.apply_full(displacement)
    residual = internal - loads
    free = np.setdiff1d(np.arange(model.ndof, dtype=np.int64), fixed)
    load_norm = max(float(np.linalg.norm(loads[free])), 1.0)
    external_work = float(displacement @ loads)
    internal_energy = float(0.5 * displacement @ internal)
    return {
        "free_residual_norm": float(np.linalg.norm(residual[free])),
        "relative_free_residual": float(np.linalg.norm(residual[free]) / load_norm),
        "reaction_norm": float(np.linalg.norm(residual[fixed])),
        "external_work": external_work,
        "internal_energy": internal_energy,
        "energy_relative_difference": abs(2.0 * internal_energy - external_work) / max(abs(external_work), 1.0),
    }


def _preconditioner_comparison(operator: StructuredBlockOperator, rhs: np.ndarray) -> dict[str, Any]:
    block_iterations = 0

    def block_callback(_: np.ndarray) -> None:
        nonlocal block_iterations
        block_iterations += 1

    block_start = time.perf_counter()
    block_solution, block_info = cg(
        operator,
        rhs,
        M=operator.preconditioner(),
        rtol=WP14_RTOL,
        atol=WP14_ATOL,
        maxiter=WP14_MAXITER,
        callback=block_callback,
    )
    block_time = time.perf_counter() - block_start
    diagonal = np.maximum(operator.diagonal[operator.free], np.finfo(float).tiny)
    diagonal_iterations = 0

    def diagonal_callback(_: np.ndarray) -> None:
        nonlocal diagonal_iterations
        diagonal_iterations += 1

    diagonal_preconditioner = LinearOperator(
        shape=operator.shape,
        dtype=float,
        matvec=lambda values: values / diagonal,
    )
    diagonal_start = time.perf_counter()
    diagonal_solution, diagonal_info = cg(
        operator,
        rhs,
        M=diagonal_preconditioner,
        rtol=WP14_RTOL,
        atol=WP14_ATOL,
        maxiter=WP14_MAXITER,
        callback=diagonal_callback,
    )
    diagonal_time = time.perf_counter() - diagonal_start
    return {
        "selected": "nodal_block_jacobi",
        "nodal_block_jacobi": {
            "iterations": block_iterations,
            "info": int(block_info),
            "seconds": block_time,
            "solution_norm": float(np.linalg.norm(block_solution)),
        },
        "diagonal_jacobi": {
            "iterations": diagonal_iterations,
            "info": int(diagonal_info),
            "seconds": diagonal_time,
            "solution_norm": float(np.linalg.norm(diagonal_solution)),
        },
    }


def _assembled_comparison(
    model: LargeModel,
    operator: StructuredBlockOperator,
    free: np.ndarray,
    matrix_free_displacement: np.ndarray,
    vector: np.ndarray,
) -> dict[str, Any]:
    assembly_started = time.perf_counter()
    assembly = ChunkedScipyAssembler(chunk_size=WP14_CHUNK_SIZE).assemble(model)
    assembly_seconds = time.perf_counter() - assembly_started
    full_probe = np.zeros(model.ndof, dtype=float)
    full_probe[free] = vector
    matrix_free_action = operator @ vector
    assembled_action = (assembly.stiffness @ full_probe)[free]
    try:
        _, assembled_displacement = _solve_scipy(
            model,
            preconditioner="jacobi",
            chunk_size=WP14_CHUNK_SIZE,
            params={"method": "cg", "rtol": WP14_RTOL, "atol": WP14_ATOL, "max_it": WP14_MAXITER},
        )
        displacement_error = _relative_norm(matrix_free_displacement[free], assembled_displacement[free])
        matrix_free_energy = float(0.5 * matrix_free_displacement @ (operator.apply_full(matrix_free_displacement)))
        assembled_energy = float(0.5 * assembled_displacement @ (assembly.stiffness @ assembled_displacement))
        energy_error = abs(matrix_free_energy - assembled_energy) / max(abs(assembled_energy), 1.0)
    except Exception as exc:  # pragma: no cover - benchmark reports environmental limits
        displacement_error = None
        energy_error = None
        assembled_error = f"{type(exc).__name__}: {exc}"
    else:
        assembled_error = None
    return {
        "assembly_seconds": assembly_seconds,
        "operator_action_relative_error": _relative_norm(matrix_free_action, assembled_action),
        "displacement_relative_error": displacement_error,
        "energy_relative_error": energy_error,
        "assembled_error": assembled_error,
    }


def _compare_phases(baseline: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    baseline_by_level = {item["level"]: item for item in baseline["levels"]}
    final_by_level = {item["level"]: item for item in final["levels"]}
    levels = sorted(set(baseline_by_level) & set(final_by_level))
    comparisons = []
    for level in levels:
        before = baseline_by_level[level]
        after = final_by_level[level]
        before_matvec = before["matvec"]["seconds_per_matvec"]
        after_matvec = after["matvec"]["seconds_per_matvec"]
        before_solve = before["total_solve_seconds"]
        after_solve = after["total_solve_seconds"]
        comparisons.append(
            {
                "level": level,
                "matvec_speedup": before_matvec / after_matvec if after_matvec else None,
                "total_solve_speedup": before_solve / after_solve if after_solve else None,
                "matvec_seconds_before": before_matvec,
                "matvec_seconds_after": after_matvec,
                "total_solve_seconds_before": before_solve,
                "total_solve_seconds_after": after_solve,
                "iteration_delta": after["solver_info"]["iterations"] - before["solver_info"]["iterations"],
                "operator_memory_delta_bytes": after["operator_memory_bytes"] - before["operator_memory_bytes"],
            }
        )
    return {"levels": comparisons}


def _relative_norm(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right) / max(float(np.linalg.norm(right)), 1.0))


def _git_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _rss_bytes() -> int | None:
    try:
        import psutil
    except ImportError:
        return None
    return int(psutil.Process().memory_info().rss)


if __name__ == "__main__":
    main()
