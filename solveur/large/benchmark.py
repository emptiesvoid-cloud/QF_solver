"""Benchmark runner for large-scale TET4 solves."""

from __future__ import annotations

import json
import time
import tracemalloc
from pathlib import Path
from typing import Any

from solveur.core.errors import InputValidationError
from solveur.io.evidence_verifier import EvidenceBundleVerifier
from solveur.io.manifest import sha256, write_json_file
from solveur.large.evidence import write_large_manifest
from solveur.large.distributed_model import DistributedLargeModel, load_distributed_large_model
from solveur.large.io import load_large_model
from solveur.large.memory import process_memory_snapshot
from solveur.large.runtime import write_runtime_environment
from solveur.large.solver import solve_large_model


def benchmark_large_model(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    solver_backend: str = "scipy",
    preconditioner: str | None = None,
    chunk_size: int = 4096,
    matrix_format: str = "baij",
    partition_strategy: str = "contiguous",
    graph_partitioner: str = "ptscotch",
    restart_from: str | Path | None = None,
) -> dict[str, Any]:
    """Solve a large model and write benchmark/evidence artifacts."""
    source = Path(input_path)
    output = Path(output_dir)
    comm = _mpi_comm(solver_backend)
    rank = comm.rank if comm is not None else 0
    if rank == 0:
        output.mkdir(parents=True, exist_ok=True)
    if comm is not None:
        comm.Barrier()
    if comm is not None:
        fingerprint_payload = _input_fingerprint(source) if rank == 0 else None
        input_fingerprint = comm.bcast(fingerprint_payload, root=0)
    else:
        input_fingerprint = _input_fingerprint(source)
    restart_path = _validated_restart_checkpoint(restart_from, input_fingerprint) if restart_from is not None else None
    trace_was_running = tracemalloc.is_tracing()
    if not trace_was_running:
        tracemalloc.start()
    process_memory_before = process_memory_snapshot()
    load_start = time.perf_counter()
    model = (
        load_distributed_large_model(
            source,
            comm,
            partition_strategy=partition_strategy,
            graph_partitioner=graph_partitioner,
        )
        if comm is not None and comm.size > 1
        else load_large_model(source)
    )
    load_time = time.perf_counter() - load_start
    solve_start = time.perf_counter()
    result = solve_large_model(
        model,
        output_dir=output,
        solver_backend=solver_backend,
        preconditioner=preconditioner or ("gamg" if solver_backend == "petsc" else "jacobi"),
        chunk_size=chunk_size,
        parameters={"matrix_format": matrix_format, "restart_from": str(restart_path) if restart_path else None},
    )
    total_solve_time = time.perf_counter() - solve_start
    current_memory, peak_memory = tracemalloc.get_traced_memory()
    process_memory_after = process_memory_snapshot()
    if not trace_was_running:
        tracemalloc.stop()
    local_telemetry = {
        "rank": int(rank),
        "load_time_seconds": float(load_time),
        "solve_pipeline_time_seconds": float(total_solve_time),
        "python_tracemalloc_current_bytes": int(current_memory),
        "python_tracemalloc_peak_bytes": int(peak_memory),
        "process_current_rss_before_bytes": process_memory_before.get("current_rss_bytes"),
        "process_current_rss_after_bytes": process_memory_after.get("current_rss_bytes"),
        "process_peak_rss_bytes": process_memory_after.get("peak_rss_bytes"),
        "process_memory_source": process_memory_after.get("source"),
    }
    rank_telemetry = comm.gather(local_telemetry, root=0) if comm is not None else [local_telemetry]
    if rank != 0:
        return comm.bcast(None, root=0)
    load_time = max(float(item["load_time_seconds"]) for item in rank_telemetry)
    total_solve_time = max(float(item["solve_pipeline_time_seconds"]) for item in rank_telemetry)
    write_json_file(output / "input_fingerprint.json", input_fingerprint)
    runtime_path = write_runtime_environment(
        output,
        {
            "kind": "large_benchmark",
            "input": str(source.resolve()),
            "backend": result.backend,
            "node_count": model.node_count,
            "element_count": model.element_count,
            "ndof": model.ndof,
            "chunk_size": int(chunk_size),
            "matrix_format": matrix_format,
            "mpi_size": len(rank_telemetry),
            "partitioned_hdf5_input": isinstance(model, DistributedLargeModel),
            "partition_strategy": getattr(model, "partition_strategy", "serial"),
            "graph_partitioner": graph_partitioner if partition_strategy == "graph" else None,
            "restart_from": str(restart_path) if restart_path else None,
        },
    )
    artifact_policy = _artifact_policy(output, result.output_files)
    benchmark = {
        "status": result.status,
        "input": str(source.resolve()),
        "node_count": model.node_count,
        "element_count": model.element_count,
        "ndof": model.ndof,
        "backend": result.backend,
        "chunk_size": int(chunk_size),
        "matrix_format": matrix_format,
        "partition_strategy": getattr(model, "partition_strategy", "serial"),
        "partition_details": getattr(model, "partition_details", None),
        "restart": {
            "used": restart_path is not None,
            "source": str(restart_path) if restart_path else None,
            "validated_input_sha256": input_fingerprint["sha256"] if restart_path else None,
        },
        "load_time_seconds": float(load_time),
        "solve_pipeline_time_seconds": float(total_solve_time),
        "assembly_time_seconds": result.summary["assembly_time_seconds"],
        "solve_time_seconds": result.summary["solve_time_seconds"],
        "estimated_core_memory_bytes": result.summary["estimated_core_memory_bytes"],
        "memory_telemetry": _aggregate_memory(rank_telemetry),
        "mpi": {"size": len(rank_telemetry), "rank_telemetry": rank_telemetry},
        "partitioned_input": {
            "enabled": isinstance(model, DistributedLargeModel),
            "local_element_count": getattr(model, "local_element_count", model.element_count),
            "local_compact_node_count": getattr(model, "local_node_count", model.node_count),
        },
        "input_fingerprint": input_fingerprint,
        "runtime_environment": runtime_path.name,
        "artifact_policy": artifact_policy,
        "solver": result.summary["solver"],
        "audit_status": result.audit.status,
        "output_files": result.output_files,
    }
    benchmark_path = output / "benchmark_large.json"
    write_json_file(benchmark_path, benchmark)
    (output / "benchmark_large.md").write_text(_benchmark_markdown(benchmark), encoding="utf-8")
    manifest_path = write_large_manifest(
        output,
        {
            "input": str(source.resolve()),
            "backend": result.backend,
            "ndof": model.ndof,
            "element_count": model.element_count,
        },
    )
    evidence_report = EvidenceBundleVerifier().verify(manifest_path)
    final = {**benchmark, "evidence_manifest": str(manifest_path), "evidence_verification": evidence_report.to_dict()}
    if comm is not None:
        final = comm.bcast(final, root=0)
    return final


def _aggregate_memory(rank_telemetry: list[dict[str, Any]]) -> dict[str, Any]:
    def maximum(name: str) -> int | None:
        values = [int(item[name]) for item in rank_telemetry if item.get(name) is not None]
        return max(values) if values else None

    return {
        "python_tracemalloc_current_bytes": maximum("python_tracemalloc_current_bytes"),
        "python_tracemalloc_peak_bytes": maximum("python_tracemalloc_peak_bytes"),
        "process_current_rss_before_bytes": maximum("process_current_rss_before_bytes"),
        "process_current_rss_after_bytes": maximum("process_current_rss_after_bytes"),
        "process_peak_rss_bytes": maximum("process_peak_rss_bytes"),
        "process_peak_rss_sum_bytes": sum(
            int(item["process_peak_rss_bytes"])
            for item in rank_telemetry
            if item.get("process_peak_rss_bytes") is not None
        ),
        "process_memory_source": rank_telemetry[0].get("process_memory_source"),
        "rank_count": len(rank_telemetry),
    }


def _mpi_comm(solver_backend: str) -> Any | None:
    if solver_backend.lower() != "petsc":
        return None
    try:
        from mpi4py import MPI
    except ImportError:
        return None
    return MPI.COMM_WORLD


def _benchmark_markdown(data: dict[str, Any]) -> str:
    solver = data.get("solver", {})
    memory = data.get("memory_telemetry", {})
    policy = data.get("artifact_policy", {})
    lines = [
        "# Benchmark grand modele",
        "",
        f"Statut: **{data['status']}**",
        "",
        f"- Backend: `{data['backend']}`",
        f"- Noeuds: {data['node_count']}",
        f"- Elements: {data['element_count']}",
        f"- DDL: {data['ndof']}",
        f"- Temps chargement: {data['load_time_seconds']:.6g} s",
        f"- Temps assemblage: {data['assembly_time_seconds']:.6g} s",
        f"- Temps resolution: {data['solve_time_seconds']:.6g} s",
        f"- Temps pipeline solve: {data['solve_pipeline_time_seconds']:.6g} s",
        f"- Memoire coeur estimee: {data['estimated_core_memory_bytes']} octets",
        f"- Pic memoire Python trace: {memory.get('python_tracemalloc_peak_bytes', '')} octets",
        f"- Pic RSS processus: {memory.get('process_peak_rss_bytes', '')} octets",
        f"- Somme des pics RSS par rang: {memory.get('process_peak_rss_sum_bytes', '')} octets",
        f"- Rangs MPI: {memory.get('rank_count', 1)}",
        f"- Environnement runtime: `{data.get('runtime_environment', '')}`",
        f"- Deplacements en fichier: `{policy.get('displacement_output', '')}`",
        f"- Deplacements complets en JSON: {policy.get('monolithic_displacements_in_json', '')}",
        f"- Iterations: {solver.get('iterations', '')}",
        f"- Residu final: {solver.get('residual_norm', '')}",
        f"- Audit: {data['audit_status']}",
        "",
    ]
    return "\n".join(lines)


def _input_fingerprint(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def _validated_restart_checkpoint(
    restart_from: str | Path,
    input_fingerprint: dict[str, Any],
) -> Path:
    source = Path(restart_from)
    root = source if source.is_dir() else source.parent
    displacement = root / "displacements.bin" if source.is_dir() else source
    fingerprint_path = root / "input_fingerprint.json"
    try:
        stored = json.loads(fingerprint_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"Invalid PETSc restart input fingerprint: {exc}") from exc
    if stored.get("sha256") != input_fingerprint.get("sha256") or stored.get("size_bytes") != input_fingerprint.get(
        "size_bytes"
    ):
        raise InputValidationError("PETSc restart checkpoint was produced from a different input model.")
    if not displacement.is_file():
        raise InputValidationError(f"PETSc restart displacement file is missing: {displacement}")
    return displacement


def _artifact_policy(output: Path, output_files: dict[str, str]) -> dict[str, Any]:
    json_files = sorted(output.glob("*.json"))
    offenders = []
    largest_json = 0
    for path in json_files:
        largest_json = max(largest_json, path.stat().st_size)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if _contains_displacement_array(data):
            offenders.append(path.name)
    displacement_output = str(output_files.get("displacements", ""))
    return {
        "displacement_output": displacement_output,
        "file_backed_displacements": Path(displacement_output).suffix.lower() in {".bin", ".h5", ".hdf5", ".npz"},
        "json_files_checked": len(json_files),
        "largest_json_bytes": int(largest_json),
        "monolithic_displacements_in_json": bool(offenders),
        "offending_json_files": offenders,
    }


def _contains_displacement_array(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in {"displacements", "nodal_displacements"} and isinstance(child, list):
                return True
            if _contains_displacement_array(child):
                return True
    if isinstance(value, list):
        return any(_contains_displacement_array(item) for item in value)
    return False
