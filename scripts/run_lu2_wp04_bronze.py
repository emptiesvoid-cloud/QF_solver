"""Run the LU2-WP04 Bronze readiness path without solving the system."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from mpi4py import MPI
from petsc4py import PETSc

from solveur.large.assembler import PetscTET4Assembler, fixed_dof_indices
from solveur.large.distributed_model import inspect_distributed_large_model, load_distributed_large_model
from solveur.large.mpi_guardrails import raise_if_rank_failures, require_global_readiness
from solveur.large.mpi_diagnostics import petsc_ksp_diagnostics
from solveur.large.memory import process_memory_snapshot
from solveur.large.telemetry import AssemblyTelemetry, RankPhaseTelemetry
from solveur.verification.observatory import canonical_digest, canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_7" / "wp04_execution_contract.json"
FREEZE_ID = "LU2-WP02-FREEZE-bfd1975b012453a3"
FREEZE_DIGEST = "bfd1975b012453a3b492cc79c968ceeba6ae6951a293e3ce65ddda548d8339a1"
RUNTIME_IMAGE = "qf-solver-large@sha256:d6a1718001fc36772906d1a9505637bbd0a4b7e1d8ccc9afdbcb6f67b7ff6d0e"
EXPECTED_DOF = 5_012_640
EXPECTED_ELEMENTS = 9_773_946
EXPECTED_NODES = 1_670_880


def main() -> int:
    args = _parse_args()
    record = run_case(args)
    if MPI.COMM_WORLD.rank == 0:
        print(json.dumps(record, indent=2, sort_keys=True), flush=True)
    return 0 if record.get("status") == "PASS" else 1


def run_case(args: argparse.Namespace) -> dict[str, Any]:
    comm = MPI.COMM_WORLD
    rank = int(comm.rank)
    size = int(comm.size)
    started = time.perf_counter()
    output = args.output.resolve()
    output_error: BaseException | None = None
    if rank == 0:
        try:
            output.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            output_error = exc
    raise_if_rank_failures(comm, rank, "OUTPUT_DIRECTORY", output_error)
    comm.Barrier()
    record: dict[str, Any] = {
        "schema_version": 1,
        "record_type": "lu2_wp04_5m_bronze_raw_run",
        "work_package": "LU2-WP04",
        "gate": "LU2-027-G04",
        "run_id": args.run_id,
        "status": "FAIL",
        "solve_executed": False,
        "source_sha": args.source_sha,
        "freeze": {"freeze_id": FREEZE_ID, "freeze_digest_sha256": FREEZE_DIGEST},
        "configuration": {
            "backend": "petsc",
            "matrix_format": "aij",
            "ksp": "cg",
            "preconditioner": "gamg",
            "mpi_ranks": size,
            "partition_strategy": "contiguous",
            "chunk_size": 4096,
            "solver_rtol": 1.0e-10,
            "acceptance_rtol": 1.0e-8,
            "petsc_options": {"ksp_norm_type": "unpreconditioned", "ksp_rtol": 1.0e-10, "pc_gamg_repartition": True},
        },
    }
    matrix = None
    ksp = None
    rhs = None
    telemetry = AssemblyTelemetry(
        args.telemetry_log,
        EXPECTED_ELEMENTS,
        rank=rank,
        rank_count=size,
        local_elements_total=max(1, (EXPECTED_ELEMENTS + max(size, 1) - 1) // max(size, 1)),
        global_progress=lambda local_processed: int(comm.allreduce(int(local_processed), op=MPI.SUM)),
        run_id=args.run_id,
        source_sha=args.source_sha,
    )
    rank_telemetry = RankPhaseTelemetry(
        args.telemetry_log,
        rank=rank,
        rank_count=size,
        run_id=args.run_id,
        source_sha=args.source_sha,
    )
    try:
        _validate_runtime(args, size)
        telemetry.phase("GENERATING")
        input_digest = _sha256_file(args.input) if rank == 0 else None
        input_digest = comm.bcast(input_digest, root=0)
        build = _read_json(args.build_metadata)
        _validate_build(build, input_digest, args.source_sha)
        memory_before = comm.gather(process_memory_snapshot(), root=0)

        load_started = time.perf_counter()
        model = load_distributed_large_model(args.input, comm, partition_strategy="contiguous")
        load_seconds = _max_time(comm, time.perf_counter() - load_started)
        _validate_model(model, input_digest)
        telemetry.set_local_total(model.local_element_count)
        audit = inspect_distributed_large_model(model, comm)
        if audit.status == "FAIL":
            raise RuntimeError("Distributed model audit failed: " + "; ".join(audit.errors))

        local_partition = _partition_row(model, rank)
        partition_rows = comm.gather(local_partition, root=0)
        partition_digest = canonical_digest(partition_rows) if rank == 0 else None
        partition_digest = comm.bcast(partition_digest, root=0)

        assembly_started = time.perf_counter()
        telemetry.phase("ASSEMBLING")
        matrix = PetscTET4Assembler(chunk_size=4096, matrix_format="aij", telemetry=telemetry).assemble(model)
        matrix_seconds = _max_time(comm, time.perf_counter() - assembly_started)

        rhs_started = time.perf_counter()
        telemetry.phase("RHS")
        rhs = matrix.createVecRight()
        _assemble_rhs(rhs, model)
        rhs_seconds = _max_time(comm, time.perf_counter() - rhs_started)

        options = PETSc.Options()
        options["ksp_norm_type"] = "unpreconditioned"
        options["ksp_rtol"] = 1.0e-10
        options["pc_gamg_repartition"] = True
        ksp = PETSc.KSP().create()
        ksp.setOperators(matrix)
        ksp.setType("cg")
        ksp.getPC().setType("gamg")
        ksp.setTolerances(rtol=1.0e-10, atol=0.0, max_it=10000)
        ksp.setFromOptions()
        pc_started = time.perf_counter()
        telemetry.phase("PCSETUP")
        rank_telemetry.marker("PRE_SETUP", phase="PCSETUP")
        setup_error: BaseException | None = None
        try:
            ksp.setUp()
        except Exception as exc:
            setup_error = exc
            rank_telemetry.marker("EXCEPTION", phase="PCSETUP", error=exc)
        else:
            rank_telemetry.marker("POST_SETUP", phase="PCSETUP")
        raise_if_rank_failures(comm, rank, "PCSETUP", setup_error)
        pc_seconds = _max_time(comm, time.perf_counter() - pc_started)

        diagnostics_error: BaseException | None = None
        diagnostics: dict[str, Any] = {}
        try:
            diagnostics = petsc_ksp_diagnostics(ksp, matrix)
        except Exception as exc:
            diagnostics_error = exc
            rank_telemetry.marker("EXCEPTION", phase="PCSETUP", error=exc)
        raise_if_rank_failures(comm, rank, "PETSC_DIAGNOSTICS", diagnostics_error)

        ownership_error: BaseException | None = None
        ownership_rows: list[dict[str, Any]] | None = None
        rank_telemetry.marker("PRE_OWNERSHIP_GATHER", phase="PCSETUP")
        try:
            ownership_rows = comm.gather({"rank": rank, "range": list(matrix.getOwnershipRange())}, root=0)
        except Exception as exc:
            ownership_error = exc
            rank_telemetry.marker("EXCEPTION", phase="PCSETUP", error=exc)
        else:
            rank_telemetry.marker("POST_OWNERSHIP_GATHER", phase="PCSETUP")
        raise_if_rank_failures(comm, rank, "OWNERSHIP_GATHER", ownership_error)

        ownership_digest_error: BaseException | None = None
        ownership_digest = None
        if rank == 0:
            try:
                ownership_digest = canonical_digest(ownership_rows)
            except Exception as exc:
                ownership_digest_error = exc
                rank_telemetry.marker("EXCEPTION", phase="PCSETUP", error=exc)
        raise_if_rank_failures(comm, rank, "OWNERSHIP_DIGEST", ownership_digest_error)
        ownership_digest = comm.bcast(ownership_digest, root=0)

        readiness_error: BaseException | None = None
        local_finite = False
        actual_matrix_type = "UNAVAILABLE"
        actual_ksp = "UNAVAILABLE"
        actual_pc = "UNAVAILABLE"
        try:
            local_finite = bool(np_is_finite_model(model))
            actual_matrix_type = str(matrix.getType()).lower()
            actual_ksp = str(ksp.getType()).lower()
            actual_pc = str(ksp.getPC().getType()).lower()
        except Exception as exc:
            readiness_error = exc
            rank_telemetry.marker("EXCEPTION", phase="PCSETUP", error=exc)
        raise_if_rank_failures(comm, rank, "READINESS_INSPECTION", readiness_error)
        finite_state = bool(comm.allreduce(local_finite, op=MPI.LAND))
        rank_telemetry.marker("PRE_PC_READY", phase="PC_READY_LOCAL")
        readiness_rows = require_global_readiness(
            comm,
            rank,
            {
                "pc_ready": actual_matrix_type.endswith("aij") and actual_ksp == "cg" and actual_pc == "gamg",
                "matrix_type": actual_matrix_type,
                "ksp_type": actual_ksp,
                "pc_type": actual_pc,
            },
        )
        rank_telemetry.marker("PC_READY", phase="PC_READY_GLOBAL", context={"scope": "GLOBAL"})
        telemetry.phase("PC_READY")
        telemetry.phase("PC_READY_GLOBAL")
        rank_telemetry.marker("PRE_MEMORY_GATHER", phase="PC_READY_GLOBAL")
        memory_error: BaseException | None = None
        memory_after: list[dict[str, Any]] | None = None
        try:
            memory_after = comm.gather(process_memory_snapshot(), root=0)
        except Exception as exc:
            memory_error = exc
            rank_telemetry.marker("EXCEPTION", phase="PC_READY_GLOBAL", error=exc)
        else:
            rank_telemetry.marker("POST_MEMORY_GATHER", phase="PC_READY_GLOBAL")
        raise_if_rank_failures(comm, rank, "MEMORY_GATHER", memory_error)

        disk_error: BaseException | None = None
        disk = None
        if rank == 0:
            try:
                disk = shutil.disk_usage(args.input.parent)
            except OSError as exc:
                disk_error = exc
                rank_telemetry.marker("EXCEPTION", phase="EVIDENCE", error=exc)
        raise_if_rank_failures(comm, rank, "DISK_SNAPSHOT", disk_error)

        # This reduction must be entered by every rank.  Keeping it in the
        # rank-zero evidence block mismatches the non-root finalization barrier.
        total_seconds = _max_time(comm, time.perf_counter() - started)
        record_error: BaseException | None = None
        if rank == 0:
            try:
                matrix_metadata = {
                    "type": actual_matrix_type,
                    "format": "aij" if actual_matrix_type.endswith("aij") else actual_matrix_type,
                    "global_size": list(matrix.getSize()),
                    "local_size": list(matrix.getLocalSize()),
                    "ownership_ranges": ownership_rows,
                    "info": diagnostics.get("matrix_info"),
                    "metadata_digest": canonical_digest(diagnostics),
                }
                record.update(
                    {
                    "status": "PASS" if finite_state else "FAIL",
                    "model": {
                        "model_id": build["workload"]["model_id"],
                        "node_count": model.node_count,
                        "element_count": model.element_count,
                        "true_dof": model.ndof,
                        "fixed_dof_count": model.global_fixed_dof_count,
                        "load_count": model.global_load_count,
                        "minimum_signed_volume": audit.details["minimum_signed_volume"],
                    },
                    "input_digest_sha256": input_digest,
                    "partition_digest": partition_digest,
                    "ownership_digest": ownership_digest,
                    "partition": {"strategy": model.partition_strategy, "rows": partition_rows},
                    "matrix": matrix_metadata,
                    "petsc": {
                        "version": list(PETSc.Sys.getVersion()),
                        "ksp_type": actual_ksp,
                        "pc_type": actual_pc,
                        "pc_ready": True,
                        "global_readiness": readiness_rows,
                        "diagnostics": diagnostics,
                        "solve_called": False,
                    },
                    "environment": _environment(size),
                    "phases": {
                        "model_setup_seconds": load_seconds,
                        "assembly_operator_seconds": matrix_seconds + rhs_seconds,
                        "matrix_assembly_seconds": matrix_seconds,
                        "rhs_setup_seconds": rhs_seconds,
                        "pc_setup_seconds": pc_seconds,
                        "solve_seconds": "NOT_RUN",
                        "post_processing_seconds": "NOT_RUN",
                        "total_seconds": total_seconds,
                    },
                    "resources": {
                        "peak_rss_total_bytes": sum(
                            int(item["peak_rss_bytes"]) for item in memory_after if item.get("peak_rss_bytes") is not None
                        ),
                        "peak_rss_per_rank_bytes": max(
                            int(item["peak_rss_bytes"]) for item in memory_after if item.get("peak_rss_bytes") is not None
                        ),
                        "peak_rss_by_rank": memory_after,
                        "input_file_bytes": args.input.stat().st_size,
                        "free_disk_bytes_after": int(disk.free) if disk is not None else None,
                        "disk_total_bytes": int(disk.total) if disk is not None else None,
                        "memory_before_by_rank": memory_before,
                    },
                    "finite_state": finite_state,
                    "checks": {
                        "actual_size": model.ndof == EXPECTED_DOF and model.element_count == EXPECTED_ELEMENTS and model.node_count == EXPECTED_NODES,
                        "model_audit": audit.status,
                        "matrix_accepted": matrix_metadata["global_size"] == [EXPECTED_DOF, EXPECTED_DOF]
                        and matrix_metadata["format"] == "aij",
                        "petsc_initialized": True,
                        "gamg_ready": True,
                        "finite_state": finite_state,
                        "no_solve": True,
                        "no_silent_fallback": True,
                    },
                    "provenance": {
                        "source_sha": args.source_sha,
                        "contract_path": "qualification/0_2_7/wp04_execution_contract.json",
                        "contract_digest_sha256": _sha256_file(CONTRACT_PATH),
                        "runtime_image": RUNTIME_IMAGE,
                        "input_digest_sha256": input_digest,
                        "command": [str(value) for value in sys.argv],
                        "artifact_classification": "CONTROLLED_PROOF",
                    },
                    }
                )
            except Exception as exc:
                record_error = exc
                rank_telemetry.marker("EXCEPTION", phase="EVIDENCE", error=exc)
        raise_if_rank_failures(comm, rank, "RANK_ZERO_EVIDENCE", record_error)
        record = comm.bcast(record if rank == 0 else None, root=0)
        telemetry.phase("COMPLETED")
        record["telemetry_status"] = telemetry.status

        raw_write_error: BaseException | None = None
        if rank == 0:
            try:
                _write(args.output / "wp04_bronze_raw.json", record)
            except OSError as exc:
                raw_write_error = exc
                rank_telemetry.marker("EXCEPTION", phase="EVIDENCE", error=exc)
        raise_if_rank_failures(comm, rank, "RAW_REPORT_WRITE", raw_write_error)
    except Exception as exc:  # pragma: no cover - exercised in Docker failure paths
        rank_telemetry.marker("EXCEPTION", phase="FAILED", error=exc)
        telemetry.phase("FAILED")
        record.update(
            {
                "status": "FAIL",
                "failure_type": type(exc).__name__,
                "failure_reason": str(exc),
                "phases": {"total_seconds": _max_time(comm, time.perf_counter() - started)},
                "provenance": {
                    "source_sha": args.source_sha,
                    "runtime_image": RUNTIME_IMAGE,
                    "command": [str(value) for value in sys.argv],
                    "artifact_classification": "CONTROLLED_PROOF",
                },
                "telemetry_status": telemetry.status,
            }
        )
    finally:
        rank_telemetry.marker("FINALIZE_ENTER", phase="FINALIZING")
        for handle in (rhs, ksp, matrix):
            if handle is not None:
                try:
                    handle.destroy()
                except Exception:
                    pass
        comm.Barrier()
        rank_telemetry.marker("FINALIZE_EXIT", phase="FINALIZED")
    telemetry.close()
    rank_telemetry.close()
    comm.Barrier()
    return record


def _assemble_rhs(rhs: Any, model: Any) -> None:
    fixed = fixed_dof_indices(model).astype(PETSc.IntType)
    load_indices = np_dof_index(model.load_nodes, model.load_components).astype(PETSc.IntType)
    if load_indices.size:
        rhs.setValues(load_indices, model.load_values, addv=PETSc.InsertMode.ADD_VALUES)
    rhs.assemble()
    row_start, row_stop = rhs.getOwnershipRange()
    for dof in fixed[(fixed >= row_start) & (fixed < row_stop)]:
        rhs.setValue(int(dof), 0.0, addv=PETSc.InsertMode.INSERT_VALUES)
    rhs.assemble()


def _validate_runtime(args: argparse.Namespace, size: int) -> None:
    if size != 8:
        raise RuntimeError(f"WP02 freeze requires 8 MPI ranks, received {size}.")
    if os.environ.get("PETSC_OPTIONS"):
        raise RuntimeError("PETSC_OPTIONS must be unset; frozen options are explicit.")
    if args.runtime_image != RUNTIME_IMAGE:
        raise RuntimeError("Runtime image differs from the WP02 freeze.")
    if args.freeze_digest != FREEZE_DIGEST or args.freeze_id != FREEZE_ID:
        raise RuntimeError("WP02 freeze identity differs from the WP04 contract.")


def _validate_build(build: dict[str, Any], input_digest: str, source_sha: str) -> None:
    workload = build.get("workload", {})
    if build.get("status") != "PASS" or workload.get("input_digest_sha256") != input_digest:
        raise RuntimeError("Workload build metadata does not match the input bytes.")
    if build.get("source_sha") != source_sha:
        raise RuntimeError("Workload build and Bronze source snapshots differ.")
    if workload.get("true_dof") != EXPECTED_DOF or workload.get("elements") != EXPECTED_ELEMENTS:
        raise RuntimeError("Workload build size is not the predeclared 5M workload.")


def _validate_model(model: Any, input_digest: str) -> None:
    if model.ndof != EXPECTED_DOF or model.element_count != EXPECTED_ELEMENTS or model.node_count != EXPECTED_NODES:
        raise RuntimeError(
            f"Actual model size differs: nodes={model.node_count}, elements={model.element_count}, dof={model.ndof}."
        )
    if input_digest is None:
        raise RuntimeError("Input digest was not captured.")
    if model.analysis.get("type") != "linear_static":
        raise RuntimeError("Bronze workload is not linear_static.")
    if len(model.material_names) != 1 or model.material_names[0] != "steel":
        raise RuntimeError("Bronze workload material contract differs.")


def _partition_row(model: Any, rank: int) -> dict[str, Any]:
    owned_start = model.global_node_count * rank // 8
    owned_stop = model.global_node_count * (rank + 1) // 8
    return {
        "rank": rank,
        "local_element_start": model.local_element_start,
        "local_element_count": model.local_element_count,
        "local_node_count": model.local_node_count,
        "global_element_ids_digest": _sha256_array(model.global_element_ids),
        "global_node_ids_digest": _sha256_array(model.global_node_ids),
        "owned_node_range": [owned_start, owned_stop],
    }


def _environment(size: int) -> dict[str, Any]:
    return {
        "hostname": "lu2-wp04-docker-runtime",
        "os": "Linux container",
        "cpu": os.environ.get("HOST_CPU", "container-cpu-not-exported"),
        "python_version": sys.version,
        "petsc_version": ".".join(str(value) for value in PETSc.Sys.getVersion()),
        "mpi_version": MPI.Get_library_version().strip(),
        "container_digest": RUNTIME_IMAGE,
        "ram_bytes": None,
        "threads": 1,
        "rank_count": size,
    }


def np_is_finite_model(model: Any) -> bool:
    return bool(
        np.isfinite(model.nodes).all()
        and np.isfinite(model.load_values).all()
        and (model.tet4 >= 0).all()
        and (model.tet4 < model.local_node_count).all()
    )


def np_dof_index(nodes: Any, components: Any) -> Any:
    return (3 * np.asarray(nodes, dtype=np.int64) + np.asarray(components, dtype=np.int64)).astype(np.int64)


def _max_time(comm: Any, value: float) -> float:
    return float(comm.allreduce(float(value), op=MPI.MAX))


def _sha256_array(values: Any) -> str:
    array = np.ascontiguousarray(values)
    return hashlib.sha256(array.tobytes()).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--build-metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", choices=("run1", "run2"), required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--freeze-id", default=FREEZE_ID)
    parser.add_argument("--freeze-digest", default=FREEZE_DIGEST)
    parser.add_argument("--runtime-image", default=RUNTIME_IMAGE)
    parser.add_argument("--telemetry-log", type=Path, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
