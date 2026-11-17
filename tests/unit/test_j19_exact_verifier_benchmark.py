from __future__ import annotations

import json
import time
import tracemalloc
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix

from research.j17.exact_residual import evaluate_exact_residual
from research.j19.checkpoint import write_atomic_json


OUTPUT = Path(__file__).resolve().parents[2] / "research" / "j19" / "results" / "exact_benchmark_001" / "benchmark.json"


def _make_system(dimension: int, structure: str) -> tuple[object, np.ndarray, np.ndarray, int]:
    solution = np.ones(dimension, dtype=np.complex128)
    if structure == "dense":
        matrix = np.zeros((dimension, dimension), dtype=np.complex128)
        np.fill_diagonal(matrix, 2.0 + 1.0j)
        if dimension > 1:
            matrix[np.arange(dimension - 1), np.arange(1, dimension)] = 0.25 - 0.5j
        rhs = matrix @ solution
        return matrix, rhs, solution, int(np.count_nonzero(matrix))

    data: list[complex] = []
    indices: list[int] = []
    indptr = [0]
    for row in range(dimension):
        if structure == "diagonal":
            entries = [(row, 2.0 + 1.0j)]
        elif structure == "banded":
            entries = []
            if row > 0:
                entries.append((row - 1, 0.25 - 0.5j))
            entries.append((row, 2.0 + 1.0j))
            if row + 1 < dimension:
                entries.append((row + 1, -0.25 + 0.5j))
        elif structure == "duplicates":
            entries = [(row, 2.0 + 1.0j), (row, 0.5 + 0.25j), (row, -0.5 - 0.25j)]
            if row + 1 < dimension:
                entries.append((row + 1, 0.25 - 0.5j))
        else:
            raise ValueError(structure)
        for column, value in entries:
            indices.append(column)
            data.append(value)
        indptr.append(len(data))
    matrix = csr_matrix(
        (np.asarray(data, dtype=np.complex128), np.asarray(indices, dtype=np.int32), np.asarray(indptr, dtype=np.int32)),
        shape=(dimension, dimension),
    )
    # All coefficients and x=1 are binary-exact small values; duplicate terms cancel exactly.
    rhs = np.asarray(matrix @ solution, dtype=np.complex128)
    return matrix, rhs, solution, int(matrix.nnz)


def test_j19_exact_verifier_bounded_scaling_profile() -> None:
    if OUTPUT.exists():
        raise RuntimeError("J19 benchmark output already exists; refusing to overwrite a prior attempt")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, object] = {
        "schema": "qfsolver-j19-exact-benchmark-v1",
        "status": "RUNNING",
        "method": "Exact represented-system verifier; per-case elapsed-time budget 5 seconds; Python allocation peak from tracemalloc.",
        "cases": [],
    }
    write_atomic_json(OUTPUT, record)
    cases = [(size, "dense") for size in (16, 64, 128, 175, 256)]
    cases += [(size, structure) for size in (16, 64, 128, 175, 256) for structure in ("diagonal", "banded", "duplicates")]
    for dimension, structure in cases:
        matrix, rhs, solution, stored = _make_system(dimension, structure)
        tracemalloc.start()
        started = time.perf_counter()
        result = evaluate_exact_residual(
            matrix,
            rhs,
            solution,
            max_elapsed_seconds=5.0,
        )
        elapsed = time.perf_counter() - started
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        case_record = {
            "dimension": dimension,
            "structure": structure,
            "stored_entries": stored,
            "elapsed_seconds": elapsed,
            "python_peak_tracemalloc_bytes": peak_bytes,
            "status": result.status,
            "reason": result.reason,
        }
        record["cases"].append(case_record)
        write_atomic_json(OUTPUT, record)
        assert result.status in {"PASS", "INCONCLUSIVE"}, case_record
        if result.status == "PASS":
            assert result.residual_squared == 0, case_record
        else:
            assert "budget" in result.reason or "limit" in result.reason, case_record
    record["status"] = "COMPLETE"
    write_atomic_json(OUTPUT, record)
    assert len(record["cases"]) == len(cases)
