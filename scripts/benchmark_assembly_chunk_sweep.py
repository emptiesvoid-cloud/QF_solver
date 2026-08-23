"""Measure the time/memory trade-off of large-model assembly chunk sizes.

This is a manual V&V campaign.  It does not change the default assembler
configuration and deliberately omits host identity and absolute paths from
the archived report.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.benchmark_assembly_scaling import run_campaign
except ModuleNotFoundError:
    from benchmark_assembly_scaling import run_campaign  # type: ignore[no-redef]

CHUNK_ENTRY_BYTES = 24


def recommend_chunk_size(
    rows: list[dict[str, object]],
    *,
    memory_budget_bytes: int | None = None,
    default_chunk_size: int = 4096,
) -> dict[str, object]:
    """Select the fastest measured chunk that fits an optional memory budget.

    The recommendation is deliberately advisory: it uses only measured sweep
    rows, keeps the default assembler unchanged, and reports the conservative
    sparse-entry estimate used for the budget gate.
    """
    if not rows:
        raise ValueError("chunk sweep rows must not be empty")
    if default_chunk_size <= 0:
        raise ValueError("default_chunk_size must be positive")
    if memory_budget_bytes is not None and memory_budget_bytes <= 0:
        raise ValueError("memory_budget_bytes must be positive")
    normalized: list[dict[str, object]] = []
    for row in rows:
        chunk_size = int(row["chunk_size"])
        peak_nnz = int(row["peak_chunk_nnz"])
        assembly_seconds = float(row["assembly_seconds"])
        if chunk_size <= 0 or peak_nnz < 0 or assembly_seconds < 0.0:
            raise ValueError("chunk sweep rows contain invalid measurements")
        normalized.append(
            {
                **row,
                "estimated_peak_chunk_bytes": peak_nnz * CHUNK_ENTRY_BYTES,
            }
        )
    feasible = [
        row
        for row in normalized
        if memory_budget_bytes is None
        or int(row["estimated_peak_chunk_bytes"]) <= memory_budget_bytes
    ]
    if not feasible:
        return {
            "status": "BLOCKED",
            "selected_chunk_size": None,
            "default_chunk_size": int(default_chunk_size),
            "memory_budget_bytes": memory_budget_bytes,
            "candidate_count": 0,
            "reason": "no measured chunk fits the memory budget",
        }
    selected = min(feasible, key=lambda row: (float(row["assembly_seconds"]), int(row["chunk_size"])))
    return {
        "status": "PASS",
        "selected_chunk_size": int(selected["chunk_size"]),
        "default_chunk_size": int(default_chunk_size),
        "memory_budget_bytes": memory_budget_bytes,
        "candidate_count": len(feasible),
        "estimated_peak_chunk_bytes": int(selected["estimated_peak_chunk_bytes"]),
        "selection_basis": "minimum measured assembly_seconds within budget",
    }


def run_sweep(
    target_dofs: int,
    chunk_sizes: list[int],
    output: Path | None = None,
    *,
    repeats: int = 3,
    memory_budget_bytes: int | None = None,
) -> dict[str, object]:
    """Compare deterministic chunk sizes on the same generated model."""
    if target_dofs < 2:
        raise ValueError("target_dofs must be at least 2")
    if not chunk_sizes or any(size <= 0 for size in chunk_sizes):
        raise ValueError("chunk_sizes must contain positive values")
    if repeats <= 0:
        raise ValueError("repeats must be positive")
    if memory_budget_bytes is not None and memory_budget_bytes <= 0:
        raise ValueError("memory_budget_bytes must be positive")

    rows: list[dict[str, object]] = []
    for chunk_size in chunk_sizes:
        report = run_campaign([target_dofs], chunk_size=chunk_size, repeats=repeats)
        source = report["sizes"][0]
        diagnostics = source["assembly_diagnostics"]
        rows.append(
            {
                "chunk_size": int(chunk_size),
                "target_dofs": int(source["target_dofs"]),
                "dofs": int(source["dofs"]),
                "elements": int(source["elements"]),
                "assembly_seconds": float(source["assembly_seconds"]),
                "assembly_seconds_samples": list(source["assembly_seconds_samples"]),
                "repeat_count": int(source["repeat_count"]),
                "final_nnz": int(diagnostics["final_nnz"]),
                "peak_chunk_nnz": int(diagnostics["peak_chunk_nnz"]),
                "sparse_memory_bytes": int(diagnostics["sparse_memory_bytes"]),
                "assembly_phase_seconds": dict(diagnostics["assembly_phase_seconds"]),
            }
        )
    report = {
        "schema_version": 1,
        "campaign": "qf-solver-tet4-assembly-chunk-sweep-0.2.2-alpha",
        "environment": "local reproducibility sample; host identity intentionally omitted",
        "target_dofs": int(target_dofs),
        "chunk_sizes": [int(size) for size in chunk_sizes],
        "repeats": int(repeats),
        "sizes": rows,
        "recommendation": recommend_chunk_size(rows, memory_budget_bytes=memory_budget_bytes),
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-dofs", type=int, default=100_000)
    parser.add_argument("--chunk-sizes", nargs="+", type=int, default=[1024, 2048, 4096, 8192, 16384])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--memory-budget-mb", type=int, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("qualification/benchmarks/qf_solver_0_2_2_assembly_chunk_sweep_reference.json"),
    )
    args = parser.parse_args()
    if args.target_dofs < 2:
        parser.error("target-dofs must be at least 2")
    if any(size <= 0 for size in args.chunk_sizes):
        parser.error("chunk-sizes must be positive")
    if args.repeats <= 0:
        parser.error("repeats must be positive")
    if args.memory_budget_mb is not None and args.memory_budget_mb <= 0:
        parser.error("memory-budget-mb must be positive")
    memory_budget_bytes = args.memory_budget_mb * 1024 * 1024 if args.memory_budget_mb is not None else None
    print(
        json.dumps(
            run_sweep(
                args.target_dofs,
                args.chunk_sizes,
                args.output,
                repeats=args.repeats,
                memory_budget_bytes=memory_budget_bytes,
            ),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
