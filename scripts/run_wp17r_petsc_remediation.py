"""Run the WP17-R PETSc remediation probe without changing FEM numerics.

The runner uses the existing large-model solver with the frozen WP14 settings.
It is intended to run inside the pinned PETSc container.  PETSc is selected
explicitly; no fallback is permitted.  Reaction and energy checks are a
post-solve diagnostic using the existing structured TET4 operator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from solveur.large.assembler import assemble_loads, fixed_dof_indices
from solveur.large.io import load_large_model
from solveur.large.matrix_free import StructuredBlockOperator, solve_structured_matrix_free
from solveur.large.memory import process_memory_snapshot
from solveur.large.runtime import collect_runtime_environment
from solveur.large.solver import solve_large_model


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_7" / "wp14_execution_contract.json"
WP14_RTOL = 1.0e-8
WP14_ATOL = 0.0
WP14_MAXITER = 10000
WP14_CHUNK_SIZE = 4096
DEFAULT_RUNTIME_IMAGE = os.environ.get("QF_SOLVER_RUNTIME_IMAGE", "qf-solver-large:0.2.0")
MONITOR_PATTERN = re.compile(
    r"^\s*(?P<iteration>\d+)\s+KSP(?: .*?)?true resid norm\s+"
    r"(?P<true>[-+0-9.eE]+).*?\|\|r\(i\)\|\|/\|\|b\|\|\s+"
    r"(?P<relative>[-+0-9.eE]+)\s*$",
    re.MULTILINE,
)


def main() -> None:
    args = _parse_args()
    record = run_case(
        input_path=args.input.resolve(),
        output_dir=args.output.resolve(),
        backend=args.backend,
        preconditioner=args.preconditioner,
        partition_strategy=args.partition_strategy,
        graph_partitioner=args.graph_partitioner,
        runtime_image=args.runtime_image,
        source_sha=args.source_sha,
        monitor=not args.no_monitor,
        compare_matrix_free=args.compare_matrix_free,
    )
    print(json.dumps(record, indent=2, sort_keys=True), flush=True)
    if record["status"] != "PASS":
        raise SystemExit(1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend", choices=("petsc", "matrix_free"), default="petsc")
    parser.add_argument("--preconditioner", default="gamg")
    parser.add_argument("--partition-strategy", choices=("contiguous", "graph"), default="contiguous")
    parser.add_argument("--graph-partitioner", default="ptscotch")
    parser.add_argument("--runtime-image", default=DEFAULT_RUNTIME_IMAGE)
    parser.add_argument("--source-sha", default=None, help="Qualified source SHA when the Docker worktree has no readable .git path.")
    parser.add_argument("--no-monitor", action="store_true")
    parser.add_argument("--compare-matrix-free", action="store_true")
    return parser.parse_args()


def run_case(
    *,
    input_path: Path,
    output_dir: Path,
    backend: str = "petsc",
    preconditioner: str = "gamg",
    partition_strategy: str = "contiguous",
    graph_partitioner: str = "ptscotch",
    runtime_image: str = DEFAULT_RUNTIME_IMAGE,
    source_sha: str | None = None,
    monitor: bool = True,
    compare_matrix_free: bool = False,
) -> dict[str, Any]:
    """Run one explicit backend and return a portable evidence record."""
    if backend == "matrix_free" and _mpi_size() > 1:
        raise ValueError("The diagnostic matrix-free route is serial-only; use PETSc for MPI runs.")
    output_dir.mkdir(parents=True, exist_ok=True)
    comm = _mpi_comm()
    rank = int(comm.rank) if comm is not None else 0
    size = int(comm.size) if comm is not None else 1
    input_digest = _sha256_file(input_path) if rank == 0 else None
    input_digest = comm.bcast(input_digest, root=0) if comm is not None else input_digest
    source_sha = _validate_sha(source_sha or _git_sha())
    config = _frozen_config(backend, preconditioner, monitor, size, partition_strategy)
    config_digest = _digest_json(config)
    started = time.perf_counter()
    local_memory_before = process_memory_snapshot()
    memory_before_all = comm.gather(local_memory_before, root=0) if comm is not None else [local_memory_before]
    memory_before = memory_before_all[0] if rank == 0 else None
    record: dict[str, Any] = {
        "schema_version": 1,
        "case_id": "WP17R-PETSC-LARGE-ROUTE-001",
        "tier": "T1_DIAGNOSTIC",
        "status": "RUNNING",
        "source_sha": source_sha,
        "contract_id": "QF-027-WP14-LARGE-EXECUTION-001",
        "contract_path": "qualification/0_2_7/wp14_execution_contract.json",
        "input_path": input_path.name,
        "input_digest_sha256": input_digest,
        "configuration": config,
        "configuration_digest_sha256": config_digest,
        "runtime_image": runtime_image,
        "mpi_size": size,
        "monitor": {"enabled": monitor, "pattern": "PETSc ksp_monitor_true_residual"},
    }
    # PETSc initialization may perform MPI collectives.  Keep provenance
    # collection symmetric across ranks, then retain the root snapshot.
    runtime_metadata = _runtime_metadata(source_sha, input_digest, runtime_image, size)
    if rank == 0:
        record["environment"] = runtime_metadata
    _write_record(output_dir / "wp17r_case_running.json", record, rank)
    try:
        load_started = time.perf_counter()
        model = _load_model(input_path, comm, partition_strategy, graph_partitioner, backend)
        load_seconds = _max_seconds(time.perf_counter() - load_started, comm)
        solve_started = time.perf_counter()
        monitor_path = output_dir / f"petsc_monitor.rank{rank}.log"
        capture = _capture_stdout(monitor_path) if monitor else nullcontext()
        with capture:
            result = solve_large_model(
                model,
                output_dir=output_dir,
                solver_backend=backend,
                preconditioner=preconditioner,
                chunk_size=WP14_CHUNK_SIZE,
                parameters={
                    "rtol": WP14_RTOL,
                    "atol": WP14_ATOL,
                    "max_it": WP14_MAXITER,
                    "matrix_format": "aij",
                    "ksp_type": "cg",
                    "petsc_options": config["petsc_options"],
                },
            )
        solve_seconds = _max_seconds(time.perf_counter() - solve_started, comm)
        if comm is not None:
            comm.Barrier()
        post_started = time.perf_counter()
        if rank == 0:
            serial_model = load_large_model(input_path) if size > 1 else model
            displacement = _read_displacement(output_dir, serial_model.node_count)
            post = _reaction_diagnostics(serial_model, displacement)
            comparison = (
                _compare_matrix_free(serial_model, displacement, post)
                if compare_matrix_free and backend == "petsc"
                else {"status": "NOT_RUN", "reason": "subscale comparison not requested"}
            )
            history = _monitor_evidence(monitor_path) if monitor else {"status": "NOT_RUN"}
        else:
            post = None
            comparison = None
            history = None
        if comm is not None:
            post = comm.bcast(post, root=0)
            comparison = comm.bcast(comparison, root=0)
            history = comm.bcast(history, root=0)
        local_memory_after = process_memory_snapshot()
        memory_after_all = comm.gather(local_memory_after, root=0) if comm is not None else [local_memory_after]
        post_seconds = _max_seconds(time.perf_counter() - post_started, comm)
        summary = dict(result.summary)
        solver = dict(summary.get("solver", {}))
        iterations = int(solver.get("iterations", 0))
        record.update(
            {
                "status": "PASS" if result.status == "PASS" and post["finite_outputs"] else "FAIL",
                "node_count": int(model.node_count),
                "element_count": int(model.element_count),
                "true_dof": int(model.ndof),
                "fixed_dof": int(post["fixed_dof_count"]),
                "load_node_count": int(post["load_node_count"]),
                "reference_force_total_n": float(post["reference_force_total_n"]),
                "backend": result.backend,
                "solver": solver,
                "matvec_count": iterations if solver.get("method") == "cg" else None,
                "matvec_count_policy": (
                    "CG iteration count; one PETSc MatMult per converged CG iteration; "
                    "the existing public route exposes no separate PETSc event counter."
                ),
                "residual_history": history,
                "post": post,
                "subscale_equivalence": comparison,
                "phases": {
                    "model_setup_seconds": load_seconds,
                    "operator_preconditioner_setup_seconds": float(summary.get("assembly_time_seconds", 0.0))
                    + float(solver.get("setup_time_seconds", 0.0)),
                    "solve_seconds": float(solver.get("iteration_time_seconds", summary.get("solve_time_seconds", 0.0))),
                    "reactions_seconds": float(post_seconds),
                    "energy_post_seconds": float(post.get("energy_seconds", 0.0)),
                    "total_seconds": float(time.perf_counter() - started),
                    "solver_pipeline_seconds": float(solve_seconds),
                },
                "peak_rss_bytes": _max_peak_rss(memory_after_all) if rank == 0 else None,
                "peak_rss_by_rank": [item.get("peak_rss_bytes") for item in memory_after_all]
                if rank == 0
                else None,
                "memory_before": memory_before,
                "memory_before_by_rank": memory_before_all if rank == 0 else None,
                "memory_after": memory_after_all[0] if rank == 0 else None,
                "memory_after_by_rank": memory_after_all if rank == 0 else None,
                "acceptance": _acceptance(post, solver, comparison),
                "provenance": {
                    "source_sha": source_sha,
                    "input_digest_sha256": input_digest,
                    "configuration_digest_sha256": config_digest,
                    "runtime_image": runtime_image,
                    "contract_sha256": _sha256_file(CONTRACT_PATH),
                    "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                },
                "artifact_classification": "CONTROLLED_PROOF",
            }
        )
        if record["status"] == "PASS" and record["acceptance"]["verdict"] != "PASS":
            record["status"] = "FAIL"
    except Exception as exc:  # pragma: no cover - exercised in Docker failure paths
        record.update(
            {
                "status": "FAIL",
                "failure_type": type(exc).__name__,
                "failure_reason": str(exc),
                "phases": {"total_seconds": float(time.perf_counter() - started)},
            }
        )
    if rank == 0:
        _write_record(output_dir / "wp17r_case.json", record, rank)
    if comm is not None:
        comm.Barrier()
    return record


def _frozen_config(backend: str, preconditioner: str, monitor: bool, mpi_size: int, partition: str) -> dict[str, Any]:
    petsc_options: dict[str, Any] = {}
    if backend == "petsc":
        # WP14 measures the physical residual, not PETSc's default preconditioned norm.
        petsc_options["ksp_norm_type"] = "unpreconditioned"
        if monitor:
            petsc_options["ksp_monitor_true_residual"] = None
    return {
        "backend": backend,
        "solver": "CG",
        "preconditioner": preconditioner,
        "matrix_format": "aij",
        "chunk_size": WP14_CHUNK_SIZE,
        "rtol": WP14_RTOL,
        "atol": WP14_ATOL,
        "max_iterations": WP14_MAXITER,
        "mpi_size": mpi_size,
        "partition_strategy": partition,
        "monitor": monitor,
        "petsc_options": petsc_options,
        "stopping_norm": "unpreconditioned" if backend == "petsc" else "solver-native",
        "wp14_tolerance_source": "qualification/0_2_7/wp14_execution_contract.json",
        "fallback_policy": "no implicit fallback; backend selection is explicit and unavailable routes fail closed",
    }


def _load_model(
    input_path: Path,
    comm: Any,
    partition_strategy: str,
    graph_partitioner: str,
    backend: str,
) -> Any:
    if comm is not None and int(comm.size) > 1:
        if backend != "petsc":
            raise ValueError("Distributed models require the PETSc backend.")
        from solveur.large.distributed_model import load_distributed_large_model

        return load_distributed_large_model(
            input_path,
            comm,
            partition_strategy=partition_strategy,
            graph_partitioner=graph_partitioner,
        )
    return load_large_model(input_path)


def _reaction_diagnostics(model: Any, displacement: np.ndarray) -> dict[str, Any]:
    started = time.perf_counter()
    loads = assemble_loads(model)
    fixed = fixed_dof_indices(model)
    free = np.setdiff1d(np.arange(model.ndof, dtype=np.int64), fixed)
    operator = StructuredBlockOperator(model, free=free, chunk_size=WP14_CHUNK_SIZE)
    internal = operator.apply_full(displacement)
    residual = internal - loads
    applied_resultant = np.sum(loads.reshape((-1, 3)), axis=0)
    reaction = np.zeros_like(residual)
    reaction[fixed] = residual[fixed]
    reaction_resultant = np.sum(reaction.reshape((-1, 3)), axis=0)
    reaction_resultant_compensated = np.array(
        [math.fsum(float(value) for value in reaction.reshape((-1, 3))[:, component]) for component in range(3)]
    )
    equilibrium = reaction_resultant + applied_resultant
    free_resultant = np.sum(residual[free].reshape((-1, 3)), axis=0)
    equilibrium_compensated = reaction_resultant_compensated + applied_resultant
    force_scale = max(float(np.linalg.norm(loads)), 1.0)
    free_norm = float(np.linalg.norm(residual[free]))
    free_load_norm = float(np.linalg.norm(loads[free]))
    external_work = float(displacement @ loads)
    strain_energy = float(0.5 * displacement @ internal)
    energy_relative = abs(2.0 * strain_energy - external_work) / max(abs(external_work), 1.0)
    return {
        "fixed_dof_count": int(fixed.size),
        "load_node_count": int(model.load_nodes.size),
        "reference_force_total_n": float(applied_resultant[0]),
        "applied_resultant": applied_resultant.tolist(),
        "reaction_resultant": reaction_resultant.tolist(),
        "reaction_resultant_compensated": reaction_resultant_compensated.tolist(),
        "equilibrium_vector": equilibrium.tolist(),
        "equilibrium_relative": float(np.linalg.norm(equilibrium) / force_scale),
        "equilibrium_compensated_relative": float(np.linalg.norm(equilibrium_compensated) / force_scale),
        "free_residual_resultant": free_resultant.tolist(),
        "free_residual_equilibrium_identity_relative": float(np.linalg.norm(equilibrium + free_resultant) / force_scale),
        "reduction_difference_relative": float(
            np.linalg.norm(equilibrium - equilibrium_compensated) / force_scale
        ),
        "free_residual_norm": free_norm,
        "free_relative_residual": free_norm / max(free_load_norm, 1.0),
        "displacement_norm": float(np.linalg.norm(displacement)),
        "strain_energy": strain_energy,
        "external_work": external_work,
        "energy_relative": float(energy_relative),
        "finite_outputs": bool(np.isfinite(displacement).all() and np.isfinite(internal).all()),
        "energy_seconds": float(time.perf_counter() - started),
        "operator_route": "existing StructuredBlockOperator post-solve diagnostic",
    }


def _compare_matrix_free(model: Any, petsc_displacement: np.ndarray, petsc_post: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    matrix_free = solve_structured_matrix_free(
        model,
        chunk_size=WP14_CHUNK_SIZE,
        rtol=WP14_RTOL,
        atol=WP14_ATOL,
        maxiter=WP14_MAXITER,
    )
    mf_post = _reaction_diagnostics(model, matrix_free.displacement)
    displacement_error = float(
        np.linalg.norm(petsc_displacement - matrix_free.displacement)
        / max(float(np.linalg.norm(matrix_free.displacement)), 1.0)
    )
    return {
        "status": "PASS"
        if displacement_error <= WP14_RTOL
        and abs(petsc_post["equilibrium_relative"] - mf_post["equilibrium_relative"]) <= WP14_RTOL
        and abs(petsc_post["energy_relative"] - mf_post["energy_relative"]) <= WP14_RTOL
        else "FAIL",
        "displacement_relative_error": displacement_error,
        "equilibrium_relative_difference": abs(
            petsc_post["equilibrium_relative"] - mf_post["equilibrium_relative"]
        ),
        "energy_relative_difference": abs(petsc_post["energy_relative"] - mf_post["energy_relative"]),
        "matrix_free_iterations": int(matrix_free.solver_info.get("iterations", 0)),
        "matrix_free_residual_relative": float(matrix_free.solver_info.get("relative_residual", float("nan"))),
        "elapsed_seconds": float(time.perf_counter() - started),
        "tolerance": WP14_RTOL,
    }


def _acceptance(post: dict[str, Any], solver: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "residual": float(post["free_relative_residual"]) <= WP14_RTOL,
        "equilibrium": float(post["equilibrium_relative"]) <= WP14_RTOL,
        "energy": float(post["energy_relative"]) <= WP14_RTOL,
        "finite": bool(post["finite_outputs"]),
        "cg": str(solver.get("method", "")).lower() == "cg",
        "subscale": comparison.get("status", "NOT_RUN") in {"PASS", "NOT_RUN"},
    }
    return {"verdict": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "tolerance": WP14_RTOL}


def _monitor_evidence(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "MISSING", "path": path.name}
    text = path.read_text(encoding="utf-8", errors="replace")
    entries = [
        {
            "iteration": int(match.group("iteration")),
            "true_residual": float(match.group("true")),
            "relative_residual": float(match.group("relative")),
        }
        for match in MONITOR_PATTERN.finditer(text)
    ]
    sampled = _sample_history(entries)
    return {
        "status": "PASS" if entries else "EMPTY",
        "path": path.name,
        "entry_count": len(entries),
        "last_iteration": entries[-1]["iteration"] if entries else None,
        "sampled": sampled,
        "raw_log_sha256": _sha256_file(path),
        "raw_log_bytes": path.stat().st_size,
    }


def _sample_history(entries: list[dict[str, Any]], maximum: int = 12) -> list[dict[str, Any]]:
    if len(entries) <= maximum:
        return entries
    indices = np.linspace(0, len(entries) - 1, maximum, dtype=int)
    return [entries[int(index)] for index in np.unique(indices)]


def _compare_replays(first: dict[str, Any], second: dict[str, Any], tolerance: float = WP14_RTOL) -> dict[str, Any]:
    fields = ("true_dof", "matvec_count", "residual_relative", "equilibrium_relative", "energy_relative")
    deltas: dict[str, float] = {}
    mismatches: list[str] = []
    for field in fields:
        left = _nested_value(first, field)
        right = _nested_value(second, field)
        if left is None or right is None:
            mismatches.append(field)
            continue
        delta = abs(float(left) - float(right))
        deltas[field] = delta
        if delta > tolerance:
            mismatches.append(field)
    same_source = first.get("source_sha") == second.get("source_sha")
    same_input = first.get("input_digest_sha256") == second.get("input_digest_sha256")
    same_config = first.get("configuration_digest_sha256") == second.get("configuration_digest_sha256")
    return {
        "status": "PASS" if same_source and same_input and same_config and not mismatches else "FAIL",
        "same_source": same_source,
        "same_input": same_input,
        "same_configuration": same_config,
        "absolute_deltas": deltas,
        "mismatches": mismatches,
        "tolerance": tolerance,
    }


def _nested_value(record: dict[str, Any], field: str) -> Any:
    if field in record:
        return record[field]
    if field in {"residual_relative", "equilibrium_relative", "energy_relative"}:
        post = record.get("post", {})
        if field == "residual_relative":
            # The runner's canonical post-solve name is explicit about the
            # free-DOF residual; retain the generic alias for older evidence.
            return post.get("residual_relative", post.get("free_relative_residual"))
        return post.get(field)
    return None


def _runtime_metadata(source_sha: str, input_digest: str, image: str, mpi_size: int) -> dict[str, Any]:
    metadata = collect_runtime_environment(
        {
            "kind": "WP17R_PETSc_remediation",
            "source_sha": source_sha,
            "input_digest_sha256": input_digest,
            "runtime_image": image,
            "mpi_size": mpi_size,
        },
        packages=("numpy", "scipy", "h5py", "mpi4py", "petsc4py"),
    )
    try:
        from mpi4py import MPI
        from petsc4py import PETSc

        metadata["mpi"] = {"version": list(MPI.Get_version()), "library": MPI.Get_library_version().splitlines()[0]}
        metadata["petsc"] = {"version": list(PETSc.Sys.getVersion())}
    except ImportError:
        metadata["mpi"] = {"status": "UNAVAILABLE"}
        metadata["petsc"] = {"status": "UNAVAILABLE"}
    return metadata


def _read_displacement(output_dir: Path, node_count: int) -> np.ndarray:
    binary = output_dir / "displacements.bin"
    if binary.exists():
        metadata = json.loads((output_dir / "displacements_metadata.json").read_text(encoding="utf-8"))
        dtype = np.dtype("<f8" if metadata.get("byte_order", "little") == "little" else ">f8")
        result = np.fromfile(binary, dtype=dtype)
        if result.size != 3 * node_count or tuple(metadata.get("shape", ())) != (node_count, 3):
            raise ValueError("Distributed displacement artifact does not match the model topology.")
        return np.asarray(result, dtype=float)
    hdf5 = output_dir / "displacements.h5"
    if hdf5.exists():
        import h5py

        with h5py.File(hdf5, "r") as handle:
            result = np.asarray(handle["displacements"], dtype=float).reshape(-1)
        if result.size != 3 * node_count:
            raise ValueError("HDF5 displacement artifact does not match the model topology.")
        return result
    npz = output_dir / "displacements.npz"
    if npz.exists():
        with np.load(npz, allow_pickle=False) as data:
            result = np.asarray(data["displacements"], dtype=float).reshape(-1)
        if result.size != 3 * node_count:
            raise ValueError("NPZ displacement artifact does not match the model topology.")
        return result
    raise FileNotFoundError("No displacement artifact was written by the selected solver route.")


class _CaptureStdout:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._saved: int | None = None
        self._handle: Any = None

    def __enter__(self) -> "_CaptureStdout":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        sys.stdout.flush()
        self._saved = os.dup(1)
        self._handle = self.path.open("w", encoding="utf-8")
        os.dup2(self._handle.fileno(), 1)
        return self

    def __exit__(self, *_: object) -> None:
        sys.stdout.flush()
        if self._saved is not None:
            os.dup2(self._saved, 1)
            os.close(self._saved)
        if self._handle is not None:
            self._handle.close()


def _capture_stdout(path: Path) -> _CaptureStdout:
    return _CaptureStdout(path)


def _mpi_comm() -> Any:
    try:
        from mpi4py import MPI
    except ImportError:
        return None
    return MPI.COMM_WORLD


def _mpi_size() -> int:
    comm = _mpi_comm()
    return int(comm.size) if comm is not None else 1


def _max_seconds(value: float, comm: Any) -> float:
    if comm is None:
        return float(value)
    from mpi4py import MPI

    return float(comm.allreduce(value, op=MPI.MAX))


def _max_peak_rss(snapshots: list[dict[str, Any]]) -> int | None:
    values = [snapshot.get("peak_rss_bytes") for snapshot in snapshots]
    finite = [int(value) for value in values if value is not None]
    return max(finite) if finite else None


def _write_record(path: Path, record: dict[str, Any], rank: int) -> None:
    if rank == 0:
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _digest_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _validate_sha(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError(f"source_sha must be a 40-character hexadecimal commit id, got {value!r}.")
    return value


if __name__ == "__main__":
    main()
