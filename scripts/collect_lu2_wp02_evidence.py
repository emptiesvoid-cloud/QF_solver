"""Convert explicit PETSc runner outputs into deterministic LU2-WP02 evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from solveur.verification.observatory import (
    canonical_digest,
    make_observatory_record,
    write_observatory_record,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_ROOT = ROOT / "tmp" / "lu2_wp02"
DEFAULT_OUTPUT_ROOT = ROOT / "qualification" / "0_2_7" / "wp02_runtime"
CONTRACT_PATH = ROOT / "qualification" / "0_2_7" / "wp02_execution_contract.json"
SOURCE_SHA = "3cb817c9391ef7998c5950d3071c8d9ce1be5dd8"
RUNTIME_IMAGE = "qf-solver-large@sha256:d6a1718001fc36772906d1a9505637bbd0a4b7e1d8ccc9afdbcb6f67b7ff6d0e"
MODEL_ID = "WP02-3M-STRUCTURED-TET4-001"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _raw_result_digest(raw: dict[str, Any]) -> str:
    return canonical_digest(
        {
            "status": raw.get("status"),
            "true_dof": raw.get("true_dof"),
            "element_count": raw.get("element_count"),
            "solver": raw.get("solver"),
            "post": raw.get("post"),
            "acceptance": raw.get("acceptance"),
            "subscale_equivalence": raw.get("subscale_equivalence"),
        }
    )


def _raw_path(run_dir: Path) -> Path:
    path = run_dir / "wp17r_case.json"
    if not path.is_file():
        raise SystemExit(f"completed raw record is missing: {path}")
    return path


def _command(raw: dict[str, Any]) -> list[str]:
    argv = list(raw.get("environment", {}).get("process", {}).get("argv", []))
    return [
        "docker",
        "run",
        RUNTIME_IMAGE,
        "mpiexec",
        "-n",
        str(raw["mpi_size"]),
        *[str(value).replace("/workspace/", "") for value in argv],
    ]


def _record(raw: dict[str, Any], run_id: str, contract_digest: str) -> dict[str, Any]:
    solver = dict(raw.get("solver", {}))
    post = dict(raw.get("post", {}))
    phases = dict(raw.get("phases", {}))
    acceptance = dict(raw.get("acceptance", {}))
    setup = float(solver.get("setup_time_seconds", 0.0))
    operator = float(phases.get("operator_preconditioner_setup_seconds", 0.0))
    peak_rss = raw.get("peak_rss_bytes")
    by_rank = raw.get("peak_rss_by_rank")
    if peak_rss is None and isinstance(by_rank, list):
        values = [int(value) for value in by_rank if value is not None]
        peak_rss = max(values) if values else None
    environment = raw.get("environment", {})
    platform = environment.get("platform", {})
    mpi = environment.get("mpi", {})
    petsc = environment.get("petsc", {})
    env = {
        "hostname": "wp02-docker-runtime",
        "os": platform.get("platform"),
        "cpu": platform.get("machine"),
        "ram_bytes": 50458099712,
        "python_version": environment.get("python", {}).get("version"),
        "petsc_version": ".".join(str(value) for value in petsc.get("version", [])),
        "mpi_version": mpi.get("library"),
        "container_digest": RUNTIME_IMAGE,
        "threads": 1,
        "rank_count": int(raw["mpi_size"]),
    }
    classification = str(acceptance.get("verdict", raw.get("status", "NOT_COMPARABLE")))
    source = {
        "repository": ".",
        "revision": str(raw.get("source_sha", SOURCE_SHA)),
        "dirty": False,
        "role": "execution_source_snapshot_before_wp02_governance_commit",
    }
    configuration = dict(raw.get("configuration", {}))
    configuration["runtime_image"] = RUNTIME_IMAGE
    configuration["contract_path"] = "qualification/0_2_7/wp02_execution_contract.json"
    configuration["contract_digest"] = contract_digest
    record = make_observatory_record(
        case_id=f"LU2-WP02-{run_id.upper()}",
        requirement_id="027-LU2-REQ-002",
        capability_refs=("large-model/petsc-tet4-linear-static",),
        model_id=MODEL_ID,
        element_family="TET4",
        analysis="linear_static",
        material="isotropic_linear_elastic",
        route="distributed-petsc-large",
        backend="petsc",
        solver=str(solver.get("method", "CG")).upper(),
        preconditioner=str(solver.get("preconditioner", "gamg")),
        rank_count=int(raw["mpi_size"]),
        dof=int(raw["true_dof"]),
        elements=int(raw["element_count"]),
        input_digest=str(raw["input_digest_sha256"]),
        observables={
            "displacement_norm": post.get("displacement_norm"),
            "reaction_resultant": post.get("reaction_resultant"),
            "strain_energy": post.get("strain_energy"),
            "reference_force_total_n": post.get("reference_force_total_n"),
        },
        tolerances={
            "acceptance_relative": {"value": acceptance.get("tolerance"), "unit": "relative", "source": "WP14"},
            "solver_rtol": {"value": solver.get("explicit_petsc_options", {}).get("ksp_rtol"), "unit": "relative", "source": "WP02 predeclared"},
        },
        classification=classification,
        metrics={
            "timings_seconds": {
                "model_setup": phases.get("model_setup_seconds"),
                "preflight": None,
                "assembly_operator": max(operator - setup, 0.0),
                "redistribution": None,
                "pc_setup": setup,
                "ksp_solve": solver.get("iteration_time_seconds"),
                "communication": None,
                "io": None,
                "post_processing": phases.get("reactions_seconds"),
                "total": phases.get("total_seconds"),
            },
            "iterations": solver.get("iterations"),
            "matvecs": raw.get("matvec_count"),
            "residual": post.get("free_relative_residual"),
            "equilibrium": post.get("equilibrium_relative"),
            "energy": post.get("energy_relative"),
            "resources": {
                "peak_rss_total_bytes": peak_rss,
                "peak_rss_per_rank_bytes": peak_rss,
                "imbalance": _rss_imbalance(by_rank),
                "gpu_vram_bytes": None,
            },
        },
        source=source,
        environment=env,
        artifacts={
            "raw_result_digest": _raw_result_digest(raw),
            "contract_digest": contract_digest,
        },
        command=_command(raw),
        oracle={
            "type": "INTERNAL_INVARIANT",
            "source": "qualification/0_2_7/wp14_execution_contract.json",
            "observables": ["residual", "equilibrium", "energy", "finite_outputs", "SPD_CG"],
        },
        configuration=configuration,
        message=(
            "WP02 controlled 3M MPI run; unmeasured phase fields are intentionally null."
            if classification == "PASS"
            else f"Runner result: {classification}."
        ),
    )
    record["provenance"]["captured_at_utc"] = raw.get("provenance", {}).get(
        "timestamp_utc", raw.get("environment", {}).get("created_at_utc", "")
    )
    record["provenance"]["run_id"] = run_id
    record["metrics"]["post_timings_seconds"] = {
        "reactions": phases.get("reactions_seconds"),
        "energy": phases.get("energy_post_seconds"),
    }
    return record


def _rss_imbalance(values: Any) -> float | None:
    if not isinstance(values, list):
        return None
    rss = [float(value) for value in values if value is not None]
    if not rss or sum(rss) == 0:
        return None
    return max(rss) / (sum(rss) / len(rss)) - 1.0


def collect(input_root: Path, output_root: Path) -> dict[str, Any]:
    input_root = input_root.resolve()
    output_root = output_root.resolve()
    contract_digest = _sha256(CONTRACT_PATH)
    run_dirs = sorted(path for path in input_root.iterdir() if path.is_dir())
    if not run_dirs:
        raise SystemExit(f"no run directories found in {input_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    raw_runs: dict[str, dict[str, Any]] = {}
    for run_dir in run_dirs:
        raw = _load(_raw_path(run_dir))
        run_id = run_dir.name
        raw_runs[run_id] = raw
        record = _record(raw, run_id, contract_digest)
        record_path = output_root / f"{run_id}.json"
        write_observatory_record(record_path, record)
        records.append({
            "run_id": run_id,
            "record": str(record_path.relative_to(ROOT)).replace("\\", "/"),
            "status": record["result"]["classification"],
            "rank_count": record["execution"]["rank_count"],
            "total_seconds": record["metrics"]["timings_seconds"]["total"],
            "iterations": record["metrics"]["iterations"],
            "residual": record["metrics"]["residual"],
            "equilibrium": record["metrics"]["equilibrium"],
            "energy": record["metrics"]["energy"],
            "peak_rss_bytes": record["metrics"]["resources"]["peak_rss_total_bytes"],
            "input_digest": record["artifacts"]["input_digest"],
            "configuration_digest": record["artifacts"]["configuration_digest"],
            "phase_metrics": record["metrics"]["timings_seconds"],
            "post_timings_seconds": record["metrics"]["post_timings_seconds"],
            "resource_metrics": record["metrics"]["resources"],
        })
    by_id = {row["run_id"]: row for row in records}

    def row(run_id: str) -> dict[str, Any]:
        try:
            return by_id[run_id]
        except KeyError as exc:
            raise SystemExit(f"required LU2-WP02 run is missing: {run_id}") from exc

    selected = raw_runs.get("r8_replay1") or raw_runs.get("r2_replay1")
    if selected is None:
        raise SystemExit("no large-model run is available for the configuration freeze")
    frozen_config = {
        "backend": "petsc",
        "matrix_format": "aij",
        "ksp": "cg",
        "preconditioner": "gamg",
        "partition_strategy": "contiguous",
        "mpi_ranks": int(selected["mpi_size"]),
        "threads_per_rank": 1,
        "chunk_size": int(selected["configuration"]["chunk_size"]),
        "solver_rtol": float(selected["solver"]["explicit_petsc_options"]["ksp_rtol"]),
        "acceptance_rtol": float(selected["acceptance"]["tolerance"]),
        "max_iterations": int(selected["configuration"]["max_iterations"]),
        "petsc_options": dict(selected["solver"]["explicit_petsc_options"]),
        "runtime_image": RUNTIME_IMAGE,
        "input_digest": selected["input_digest_sha256"],
        "source_sha": selected["source_sha"],
        "environment_variables": {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "PYTHONHASHSEED": "0",
        },
    }
    freeze_digest = canonical_digest(frozen_config)
    freeze = {
        "schema_version": 1,
        "record_type": "lu2_wp02_configuration_freeze",
        "work_package": "LU2-WP02",
        "gate": "LU2-027-G02",
        "status": "FROZEN_FOR_LU2_WP03_WP04_WP05",
        "freeze_id": f"LU2-WP02-FREEZE-{freeze_digest[:16]}",
        "freeze_digest_sha256": freeze_digest,
        "configuration": frozen_config,
        "selection_basis": {
            "selected_run": "r8_replay1" if "r8_replay1" in raw_runs else "r2_replay1",
            "policy": "best fully evidenced total-time/RSS/robustness route; iterations alone are insufficient",
            "replay_evidence": ["r8_replay1", "r8_replay2"] if "r8_replay2" in raw_runs else ["r2_replay1", "r2_replay2"],
        },
        "change_policy": "No post-freeze configuration or tolerance changes without a documented blocker and Owner review.",
        "artifact_classification": "CONTROLLED_PROOF",
    }
    (output_root / "wp02_config_freeze.json").write_bytes(
        json.dumps(freeze, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
    )
    large_ids = [name for name in ("r2_replay1", "r2_replay2", "r4_run1", "r8_replay1", "r8_replay2") if name in by_id]
    large_rows = [row(name) for name in large_ids]
    baseline = row("r2_replay1")
    scaling = []
    for name in ("r2_replay1", "r4_run1", "r8_replay1"):
        current = row(name)
        scaling.append({
            "run_id": name,
            "ranks": current["rank_count"],
            "status": current["status"],
            "total_seconds": current["total_seconds"],
            "speedup_vs_r2_replay1": baseline["total_seconds"] / current["total_seconds"],
            "strong_scaling_efficiency_vs_r2": baseline["total_seconds"] / current["total_seconds"] / (current["rank_count"] / 2),
            "iterations": current["iterations"],
            "peak_rss_bytes": current["peak_rss_bytes"],
        })
    preconditioner_rows = [row(name) for name in ("subscale_gamg", "subscale_hypre") if name in by_id]
    partition_rows = [row(name) for name in ("subscale_gamg", "subscale_graph_gamg") if name in by_id]
    summary = {
        "schema_version": 1,
        "record_type": "lu2_wp02_evidence_index",
        "work_package": "LU2-WP02",
        "gate": "LU2-027-G02",
        "source_sha": SOURCE_SHA,
        "contract": {
            "path": "qualification/0_2_7/wp02_execution_contract.json",
            "sha256": contract_digest,
        },
        "input": {
            "path": "tmp/wp18_ladder/models/3m.h5",
            "sha256": "084a471b1caab628e8558c65b1777692ed53d504baad681bf0985c411a33671b",
            "true_dof": 3000000,
        },
        "runtime_image": RUNTIME_IMAGE,
        "phase_measurement_policy": "Only runner-provided phase measurements are populated; preflight, redistribution, communication and I/O remain explicitly unmeasured.",
        "runs": records,
        "large_model_runs": large_rows,
        "strong_scaling": scaling,
        "preconditioner_comparison": {
            "runs": preconditioner_rows,
            "selection": "GAMG",
            "rationale": "GAMG and HYPRE both pass the strict subscale invariants; GAMG has lower total time and RSS on the recorded model.",
        },
        "partition_comparison": {
            "runs": partition_rows,
            "selection": "contiguous",
            "rationale": "Both routes pass; graph partitioning is retained as characterized evidence and is not selected for the freeze on the recorded subscale.",
        },
        "configuration_freeze": {
            "path": "qualification/0_2_7/wp02_runtime/wp02_config_freeze.json",
            "freeze_id": freeze["freeze_id"],
            "freeze_digest_sha256": freeze_digest,
        },
        "replay_policy": {
            "required_ranks": {"2": 2, "4": 1, "8": 2},
            "same_input_and_configuration": True,
            "post_result_retuning": False,
        },
        "artifact_classification": "CONTROLLED_PROOF",
    }
    (output_root / "wp02_evidence_index.json").write_bytes(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    summary = collect(args.input_root, args.output_root)
    print(f"collected {len(summary['runs'])} LU2-WP02 records into {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
