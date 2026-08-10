"""Preconditioner comparison and MPI scaling analysis for large models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from solveur.io.manifest import sha256, write_json_file
from solveur.large.benchmark import benchmark_large_model
from solveur.large.evidence import write_large_manifest


def run_large_preconditioner_campaign(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    preconditioners: Sequence[str] = ("gamg", "hypre"),
    chunk_size: int = 4096,
    matrix_format: str = "baij",
    displacement_tolerance: float = 1.0e-8,
    partition_strategy: str = "contiguous",
    graph_partitioner: str = "ptscotch",
) -> dict[str, Any]:
    """Run PETSc preconditioners on one model and compare their solutions."""
    names = _validated_preconditioners(preconditioners)
    root = Path(output_dir)
    rank = _mpi_rank()
    if rank == 0:
        root.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for name in names:
        result = benchmark_large_model(
            input_path,
            root / name,
            solver_backend="petsc",
            preconditioner=name,
            chunk_size=chunk_size,
            matrix_format=matrix_format,
            partition_strategy=partition_strategy,
            graph_partitioner=graph_partitioner,
        )
        records.append(_preconditioner_record(name, result))
    summary: dict[str, Any] | None = None
    if rank == 0:
        reference = root / names[0] / "displacements.bin"
        for record in records:
            candidate = root / record["preconditioner"] / "displacements.bin"
            record["relative_displacement_error"] = _binary_relative_error(reference, candidate)
        status = "PASS" if all(_accepted(record, displacement_tolerance) for record in records) else "FAIL"
        summary = {
            "campaign_schema_version": 1,
            "status": status,
            "kind": "large_preconditioner_comparison",
            "input": str(Path(input_path)),
            "preconditioners": list(names),
            "matrix_format": matrix_format,
            "partition_strategy": partition_strategy,
            "graph_partitioner": graph_partitioner if partition_strategy == "graph" else None,
            "chunk_size": int(chunk_size),
            "displacement_tolerance": float(displacement_tolerance),
            "reference_preconditioner": names[0],
            "runs": records,
        }
        write_json_file(root / "preconditioner_comparison.json", summary)
        (root / "preconditioner_comparison.md").write_text(_preconditioner_markdown(summary), encoding="utf-8")
        manifest = write_large_manifest(root, {"kind": summary["kind"], "status": status})
        summary["evidence_manifest"] = str(manifest)
    return _mpi_broadcast(summary)


def analyze_large_scaling(
    benchmark_paths: Sequence[str | Path],
    output_dir: str | Path,
    *,
    mode: str,
    weak_work_tolerance: float = 0.10,
    efficiency_warning_threshold: float = 0.60,
) -> dict[str, Any]:
    """Build a strong- or weak-scaling report from completed benchmark JSON files."""
    normalized_mode = mode.lower()
    if normalized_mode not in {"strong", "weak"}:
        raise ValueError("Scaling mode must be 'strong' or 'weak'.")
    if not 0.0 < weak_work_tolerance < 1.0:
        raise ValueError("Weak-work tolerance must be between zero and one.")
    if not 0.0 < efficiency_warning_threshold <= 1.0:
        raise ValueError("Efficiency warning threshold must be in (0, 1].")
    records = sorted((_scaling_record(Path(path)) for path in benchmark_paths), key=lambda item: item["ranks"])
    _validate_scaling_records(records, normalized_mode, weak_work_tolerance)
    baseline = records[0]
    for record in records:
        record["speedup"] = baseline["pipeline_time_seconds"] / record["pipeline_time_seconds"]
        record["strong_efficiency"] = record["speedup"] / (record["ranks"] / baseline["ranks"])
        record["weak_efficiency"] = baseline["pipeline_time_seconds"] / record["pipeline_time_seconds"]
        record["throughput_dofs_per_second"] = record["dofs"] / record["pipeline_time_seconds"]
    efficiency_name = "strong_efficiency" if normalized_mode == "strong" else "weak_efficiency"
    minimum_efficiency = min(float(record[efficiency_name]) for record in records)
    summary = {
        "scaling_schema_version": 1,
        "status": "PASS" if minimum_efficiency >= efficiency_warning_threshold else "WARNING",
        "mode": normalized_mode,
        "baseline_ranks": baseline["ranks"],
        "weak_work_tolerance": float(weak_work_tolerance),
        "efficiency_warning_threshold": float(efficiency_warning_threshold),
        "minimum_efficiency": minimum_efficiency,
        "runs": records,
    }
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    write_json_file(root / "large_scaling.json", summary)
    (root / "large_scaling.md").write_text(_scaling_markdown(summary), encoding="utf-8")
    manifest = write_large_manifest(
        root,
        {"kind": f"large_{normalized_mode}_scaling", "status": summary["status"]},
    )
    return {**summary, "evidence_manifest": str(manifest)}


def _validated_preconditioners(values: Sequence[str]) -> tuple[str, ...]:
    names = tuple(str(value).strip().lower() for value in values)
    if not names or any(not value for value in names):
        raise ValueError("At least one non-empty preconditioner is required.")
    if len(set(names)) != len(names):
        raise ValueError("Preconditioner names must be unique.")
    return names


def _preconditioner_record(name: str, result: dict[str, Any]) -> dict[str, Any]:
    solver = dict(result.get("solver", {}))
    memory = dict(result.get("memory_telemetry", {}))
    return {
        "preconditioner": name,
        "status": result.get("status"),
        "evidence_status": dict(result.get("evidence_verification", {})).get("status"),
        "dofs": int(result.get("ndof", 0)),
        "ranks": int(dict(result.get("mpi", {})).get("size", 1)),
        "pipeline_time_seconds": float(result.get("solve_pipeline_time_seconds", 0.0)),
        "assembly_time_seconds": float(result.get("assembly_time_seconds", 0.0)),
        "ksp_setup_time_seconds": solver.get("setup_time_seconds"),
        "ksp_iteration_time_seconds": solver.get("iteration_time_seconds"),
        "iterations": solver.get("iterations"),
        "residual_norm": solver.get("residual_norm"),
        "peak_rss_per_rank_bytes": memory.get("process_peak_rss_bytes"),
        "relative_displacement_error": None,
    }


def _accepted(record: dict[str, Any], tolerance: float) -> bool:
    error = record.get("relative_displacement_error")
    return record.get("status") == "PASS" and record.get("evidence_status") == "PASS" and error is not None and error <= tolerance


def _binary_relative_error(reference_path: Path, candidate_path: Path, chunk_values: int = 1_000_000) -> float:
    reference_metadata = _binary_metadata(reference_path)
    candidate_metadata = _binary_metadata(candidate_path)
    if reference_metadata["shape"] != candidate_metadata["shape"]:
        raise ValueError("Displacement outputs have different shapes.")
    dtype = np.dtype("<f8" if reference_metadata["byte_order"] == "little" else ">f8")
    candidate_dtype = np.dtype("<f8" if candidate_metadata["byte_order"] == "little" else ">f8")
    numerator = 0.0
    denominator = 0.0
    with reference_path.open("rb") as reference, candidate_path.open("rb") as candidate:
        while True:
            left = np.fromfile(reference, dtype=dtype, count=chunk_values)
            right = np.fromfile(candidate, dtype=candidate_dtype, count=chunk_values)
            if left.size != right.size:
                raise ValueError("Displacement outputs have different lengths.")
            if left.size == 0:
                break
            difference = left - right
            numerator += float(np.dot(difference, difference))
            denominator += float(np.dot(left, left))
    return float(np.sqrt(numerator / denominator)) if denominator > 0.0 else float(np.sqrt(numerator))


def _binary_metadata(path: Path) -> dict[str, Any]:
    metadata_path = path.with_name("displacements_metadata.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    flat_size = int(metadata["flat_size"])
    if metadata.get("dtype") != "float64" or path.stat().st_size != flat_size * 8:
        raise ValueError(f"Invalid distributed displacement output: {path}")
    return metadata


def _scaling_record(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    mpi = dict(data.get("mpi", {}))
    ranks = int(mpi.get("size", dict(data.get("memory_telemetry", {})).get("rank_count", 1)))
    dofs = int(data["ndof"])
    return {
        "benchmark": str(path),
        "benchmark_sha256": sha256(path),
        "ranks": ranks,
        "dofs": dofs,
        "dofs_per_rank": dofs / ranks,
        "elements": int(data["element_count"]),
        "pipeline_time_seconds": float(data["solve_pipeline_time_seconds"]),
        "assembly_time_seconds": float(data["assembly_time_seconds"]),
        "solve_time_seconds": float(data["solve_time_seconds"]),
        "iterations": dict(data.get("solver", {})).get("iterations"),
        "residual_norm": dict(data.get("solver", {})).get("residual_norm"),
        "peak_rss_per_rank_bytes": dict(data.get("memory_telemetry", {})).get("process_peak_rss_bytes"),
    }


def _validate_scaling_records(records: list[dict[str, Any]], mode: str, tolerance: float) -> None:
    if len(records) < 2:
        raise ValueError("Scaling analysis requires at least two benchmark files.")
    ranks = [record["ranks"] for record in records]
    if len(set(ranks)) != len(ranks):
        raise ValueError("Scaling benchmarks must use distinct MPI rank counts.")
    if mode == "strong" and len({record["dofs"] for record in records}) != 1:
        raise ValueError("Strong scaling requires the same dof count for every run.")
    if mode == "weak":
        baseline = records[0]["dofs_per_rank"]
        relative_spread = max(abs(record["dofs_per_rank"] / baseline - 1.0) for record in records)
        if relative_spread > tolerance:
            raise ValueError(f"Weak-scaling work per rank differs by {relative_spread:.3%}; limit={tolerance:.3%}.")


def _preconditioner_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Comparaison des preconditionneurs PETSc",
        "",
        f"Statut: **{summary['status']}**",
        "",
        "| PC | Rangs | Pipeline [s] | Setup KSP [s] | Iterations [s] | Iter. | Residu | Pic RSS/rang | Ecart u |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for run in summary["runs"]:
        lines.append(
            f"| {run['preconditioner']} | {run['ranks']} | {_display(run['pipeline_time_seconds'])} | "
            f"{_display(run['ksp_setup_time_seconds'])} | {_display(run['ksp_iteration_time_seconds'])} | "
            f"{_display(run['iterations'])} | {_display(run['residual_norm'])} | "
            f"{_display(run['peak_rss_per_rank_bytes'])} | {_display(run['relative_displacement_error'])} |"
        )
    return "\n".join(lines) + "\n"


def _scaling_markdown(summary: dict[str, Any]) -> str:
    efficiency = "strong_efficiency" if summary["mode"] == "strong" else "weak_efficiency"
    lines = [
        f"# Scalabilite {summary['mode']}",
        "",
        f"Statut: **{summary['status']}**",
        "",
        "| Rangs | DDL | DDL/rang | Pipeline [s] | Speedup | Efficacite | Iter. | Pic RSS/rang |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for run in summary["runs"]:
        lines.append(
            f"| {run['ranks']} | {run['dofs']} | {_display(run['dofs_per_rank'])} | "
            f"{_display(run['pipeline_time_seconds'])} | {_display(run['speedup'])} | "
            f"{_display(run[efficiency])} | {_display(run['iterations'])} | "
            f"{_display(run['peak_rss_per_rank_bytes'])} |"
        )
    return "\n".join(lines) + "\n"


def _display(value: object) -> str:
    if value is None:
        return ""
    return f"{value:.6g}" if isinstance(value, float) else str(value)


def _mpi_rank() -> int:
    try:
        from mpi4py import MPI
    except ImportError:
        return 0
    return int(MPI.COMM_WORLD.rank)


def _mpi_broadcast(value: dict[str, Any] | None) -> dict[str, Any]:
    try:
        from mpi4py import MPI
    except ImportError:
        if value is None:
            raise RuntimeError("Root preconditioner summary is unavailable.")
        return value
    return MPI.COMM_WORLD.bcast(value, root=0)
