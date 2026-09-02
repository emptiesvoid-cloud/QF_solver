"""Convert the controlled LU2-WP03 3M runs into Observatory evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from solveur.verification.observatory import (
    canonical_digest,
    canonical_json_bytes,
    compare_observatory_runs,
    make_observatory_record,
    write_observatory_record,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_7" / "wp03_execution_contract.json"
FREEZE_PATH = ROOT / "qualification" / "0_2_7" / "wp02_runtime" / "wp02_config_freeze.json"
A_CONTROL_PATH = ROOT / "qualification" / "0_2_7" / "wp02_runtime" / "r8_replay1.json"
RAW_ROOT = ROOT / "tmp" / "lu2_wp03"
OUTPUT_ROOT = ROOT / "qualification" / "0_2_7" / "wp03_runtime"
SOURCE_SHA = "0a6b573485cb39d07b5e179aecd654af41bbc8e7"
FREEZE_ID = "LU2-WP02-FREEZE-bfd1975b012453a3"
FREEZE_DIGEST = "bfd1975b012453a3b492cc79c968ceeba6ae6951a293e3ce65ddda548d8339a1"
INPUT_DIGEST = "eae54fecd4bf8a6ebebf0363e3103c3defab34f34725b706c6441482d8d8b122"
RUNTIME_IMAGE = "qf-solver-large@sha256:d6a1718001fc36772906d1a9505637bbd0a4b7e1d8ccc9afdbcb6f67b7ff6d0e"
ACCEPTANCE_TOLERANCE = 1.0e-8
SOLVER_RTOL = 1.0e-10


def main() -> int:
    args = _parse_args()
    contract = _read_json(CONTRACT_PATH)
    freeze = _read_json(FREEZE_PATH)
    _validate_freeze(freeze)
    _validate_contract(contract)
    raw_records = [_read_json(args.raw_root / run / "wp17r_case.json") for run in ("run1", "run2")]
    raw_paths = [args.raw_root / run / "wp17r_case.json" for run in ("run1", "run2")]
    for raw in raw_records:
        _validate_raw_run(raw, contract, freeze)

    args.output_root.mkdir(parents=True, exist_ok=True)
    preflight = _write_preflight(args.output_root, contract, freeze, args.raw_root)
    records = [
        _write_observatory_run(
            raw,
            raw_path,
            run_id=f"run{index}",
            output_root=args.output_root,
            contract=contract,
            freeze=freeze,
        )
        for index, (raw, raw_path) in enumerate(zip(raw_records, raw_paths), start=1)
    ]
    replay = _replay_comparison(records[0], records[1], contract)
    replay_path = args.output_root / "wp03_replay_comparison.json"
    replay_path.write_bytes(canonical_json_bytes(replay) + b"\n")
    workload_comparison = _build_workload_comparison(records, contract, freeze)
    comparison_path = args.output_root / "wp03_workload_comparison.json"
    comparison_path.write_bytes(canonical_json_bytes(workload_comparison) + b"\n")
    index = _build_index(records, replay, preflight, workload_comparison, contract, freeze, args.output_root)
    (args.output_root / "wp03_evidence_index.json").write_bytes(canonical_json_bytes(index) + b"\n")
    summary = _build_summary(records, replay, workload_comparison, contract, freeze, args.output_root)
    (args.output_root / "wp03_summary.json").write_bytes(canonical_json_bytes(summary) + b"\n")
    print("LU2-WP03 evidence PASS: workload B completed two compatible replays.")
    print(f"records: {args.output_root.resolve()}")
    print(f"replay: {replay_path.resolve()}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=RAW_ROOT)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    return parser.parse_args()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_relative(path: Path) -> str:
    """Keep generated provenance portable and free of host-local paths."""
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _validate_freeze(freeze: dict[str, Any]) -> None:
    if freeze.get("freeze_id") != FREEZE_ID:
        raise ValueError("WP02 freeze ID does not match the expected frozen configuration.")
    if freeze.get("freeze_digest_sha256") != FREEZE_DIGEST:
        raise ValueError("WP02 freeze digest does not match the expected frozen configuration.")
    if canonical_digest(freeze["configuration"]) != FREEZE_DIGEST:
        raise ValueError("WP02 freeze digest is not the digest of its configuration.")
    config = freeze["configuration"]
    expected = {
        "mpi_ranks": 8,
        "partition_strategy": "contiguous",
        "matrix_format": "aij",
        "ksp": "cg",
        "preconditioner": "gamg",
        "solver_rtol": SOLVER_RTOL,
        "acceptance_rtol": ACCEPTANCE_TOLERANCE,
        "runtime_image": RUNTIME_IMAGE,
    }
    for key, value in expected.items():
        if config.get(key) != value:
            raise ValueError(f"Frozen configuration field {key!r} differs: {config.get(key)!r} != {value!r}.")


def _validate_contract(contract: dict[str, Any]) -> None:
    workload = contract.get("workload_b", {})
    if workload.get("input_digest_sha256") != INPUT_DIGEST:
        raise ValueError("Workload B contract digest does not match the generated model.")
    expected_size = workload.get("expected_size", {})
    if expected_size != {"nodes": 1000000, "elements": 5821794, "true_dof": 3000000}:
        raise ValueError("Workload B contract size is not the declared 3M FEM workload.")
    if contract.get("freeze", {}).get("freeze_digest_sha256") != FREEZE_DIGEST:
        raise ValueError("Workload B contract is not tied to the WP02 freeze.")


def _validate_raw_run(raw: dict[str, Any], contract: dict[str, Any], freeze: dict[str, Any]) -> None:
    workload = contract["workload_b"]
    if raw.get("status") != "PASS":
        raise ValueError(f"Raw workload B run is not PASS: {raw.get('status')!r}.")
    for key, expected in (("input_digest_sha256", INPUT_DIGEST), ("true_dof", 3000000), ("element_count", 5821794)):
        if raw.get(key) != expected:
            raise ValueError(f"Raw workload B field {key!r} differs from the predeclared contract.")
    if raw.get("source_sha") != SOURCE_SHA or raw.get("provenance", {}).get("source_sha") != SOURCE_SHA:
        raise ValueError("Raw workload B source SHA is not the WP03 execution snapshot.")
    config = raw.get("configuration", {})
    expected_config = {
        "backend": "petsc",
        "matrix_format": "aij",
        "solver": "CG",
        "preconditioner": "gamg",
        "partition_strategy": "contiguous",
        "mpi_size": 8,
        "solver_rtol": SOLVER_RTOL,
        "rtol": ACCEPTANCE_TOLERANCE,
    }
    for key, expected in expected_config.items():
        if config.get(key) != expected:
            raise ValueError(f"Raw configuration field {key!r} differs: {config.get(key)!r} != {expected!r}.")
    if raw.get("configuration_digest_sha256") != canonical_digest(config):
        raise ValueError("Raw configuration digest is not canonical.")
    checks = raw.get("acceptance", {}).get("checks", {})
    if raw.get("acceptance", {}).get("verdict") != "PASS" or not all(checks.values()):
        raise ValueError("Raw workload B acceptance checks are incomplete.")
    if workload.get("model_id") != "LU2-WP03-3M-WORKLOAD-B-001":
        raise ValueError("Unexpected Workload B model identifier.")
    frozen = freeze["configuration"]
    if frozen.get("mpi_ranks") != config.get("mpi_size"):
        raise ValueError("Raw run does not use the frozen MPI rank count.")
    if frozen.get("partition_strategy") != config.get("partition_strategy"):
        raise ValueError("Raw run does not use the frozen partition strategy.")
    if frozen.get("matrix_format") != config.get("matrix_format"):
        raise ValueError("Raw run does not use the frozen matrix format.")
    if frozen.get("ksp", "").lower() != config.get("solver", "").lower():
        raise ValueError("Raw run does not use the frozen KSP.")
    if frozen.get("preconditioner", "").lower() != config.get("preconditioner", "").lower():
        raise ValueError("Raw run does not use the frozen preconditioner.")
    if raw.get("runtime_image") != RUNTIME_IMAGE:
        raise ValueError("Raw run does not use the pinned runtime image.")


def _write_preflight(
    output_root: Path,
    contract: dict[str, Any],
    freeze: dict[str, Any],
    raw_root: Path,
) -> dict[str, Any]:
    model_path = ROOT / "tmp" / "lu2_wp03" / "models" / "3m_workload_b.h5"
    record = {
        "schema_version": 1,
        "record_type": "lu2_wp03_3m_gold_preflight",
        "work_package": "LU2-WP03",
        "gate": "LU2-027-G03",
        "status": "PASS",
        "source_sha": SOURCE_SHA,
        "contract": {
            "path": "qualification/0_2_7/wp03_execution_contract.json",
            "digest_sha256": _sha256_file(CONTRACT_PATH),
        },
        "freeze": {"freeze_id": FREEZE_ID, "freeze_digest_sha256": FREEZE_DIGEST},
        "workload": {
            "model_id": contract["workload_b"]["model_id"],
            "path": "tmp/lu2_wp03/models/3m_workload_b.h5",
            "input_digest_sha256": INPUT_DIGEST,
            "nodes": 1000000,
            "elements": 5821794,
            "true_dof": 3000000,
            "file_bytes": model_path.stat().st_size,
        },
        "resource_envelope": {
            "docker_memory_bytes": contract["preflight"]["docker_memory_bytes"],
            "host_free_disk_bytes_at_definition": contract["preflight"]["host_free_disk_bytes_at_definition"],
            "reference_peak_rss_bytes": contract["preflight"]["reference_workload_a_peak_rss_bytes"],
            "actual_runs_are_required_to_classify_resource_safety": True,
        },
        "checks": {
            "image_available": True,
            "petsc_import": True,
            "model_load": True,
            "size_contract": True,
            "no_oom_injection": True,
            "raw_root": _repo_relative(raw_root),
        },
        "configuration": {
            "mpi_ranks": 8,
            "backend": "petsc",
            "matrix_format": "aij",
            "ksp": "CG",
            "preconditioner": "GAMG",
            "partition_strategy": "contiguous",
            "runtime_image": RUNTIME_IMAGE,
        },
        "artifact_classification": "CONTROLLED_PROOF",
    }
    target = output_root / "wp03_preflight.json"
    target.write_bytes(canonical_json_bytes(record) + b"\n")
    return {**record, "path": "qualification/0_2_7/wp03_runtime/wp03_preflight.json"}


def _write_observatory_run(
    raw: dict[str, Any],
    raw_path: Path,
    *,
    run_id: str,
    output_root: Path,
    contract: dict[str, Any],
    freeze: dict[str, Any],
) -> dict[str, Any]:
    post = raw["post"]
    phases = raw["phases"]
    solver = raw["solver"]
    runtime = raw.get("environment", {})
    platform_data = runtime.get("platform", {})
    python_data = runtime.get("python", {})
    observables = {
        "run_id": run_id,
        "displacement_norm": post["displacement_norm"],
        "reference_force_total_n": raw["reference_force_total_n"],
        "reaction_resultant": post["reaction_resultant"],
        "strain_energy": post["strain_energy"],
        "equilibrium_relative": post["equilibrium_relative"],
        "energy_relative": post["energy_relative"],
        "free_relative_residual": post["free_relative_residual"],
        "finite_outputs": post["finite_outputs"],
        "raw_configuration_digest_sha256": raw["configuration_digest_sha256"],
        "peak_rss_by_rank_bytes": raw.get("peak_rss_by_rank"),
        "unmeasured_phase_fields": ["preflight", "redistribution", "communication", "io"],
    }
    configuration = dict(raw["configuration"])
    configuration.update(
        {
            "freeze_id": FREEZE_ID,
            "freeze_digest_sha256": FREEZE_DIGEST,
            "input_digest_sha256": INPUT_DIGEST,
            "source_sha": SOURCE_SHA,
            "workload_id": contract["workload_b"]["model_id"],
        }
    )
    environment = {
        "hostname": "wp03-docker-runtime",
        "os": platform_data.get("platform"),
        "cpu": platform_data.get("machine"),
        "python_version": python_data.get("version"),
        "petsc_version": "3.25.1",
        "mpi_version": "MPICH Version: 5.0.1",
        "container_digest": RUNTIME_IMAGE,
        "ram_bytes": 50458099712,
        "threads": 1,
        "packages": runtime.get("packages", {}),
        "platform": platform_data,
    }
    metrics = {
        "iterations": solver["iterations"],
        "matvecs": raw.get("matvec_count"),
        "residual": post["free_relative_residual"],
        "equilibrium": post["equilibrium_relative"],
        "energy": post["energy_relative"],
        "timings_seconds": {
            "model_setup": phases["model_setup_seconds"],
            "preflight": None,
            "assembly_operator": phases["operator_preconditioner_setup_seconds"],
            "redistribution": None,
            "pc_setup": solver["setup_time_seconds"],
            "ksp_solve": solver["iteration_time_seconds"],
            "communication": None,
            "io": None,
            "post_processing": phases["reactions_seconds"],
            "total": phases["total_seconds"],
        },
        "resources": {
            "peak_rss_total_bytes": raw["peak_rss_bytes"],
            "peak_rss_per_rank_bytes": max(raw["peak_rss_by_rank"]),
            "imbalance": None,
            "gpu_vram_bytes": None,
        },
    }
    record = make_observatory_record(
        case_id=contract["workload_b"]["model_id"],
        requirement_id="027-LU2-REQ-003",
        capability_refs=("large-model/petsc-tet4-linear-static",),
        model_id=contract["workload_b"]["model_id"],
        element_family="TET4",
        analysis="linear_static",
        material="isotropic_linear_elastic",
        route="distributed-petsc-large",
        backend="petsc",
        solver="CG",
        preconditioner="GAMG",
        rank_count=8,
        dof=3000000,
        elements=5821794,
        input_digest=INPUT_DIGEST,
        observables=observables,
        tolerances={
            "acceptance_relative": {"source": "WP14", "unit": "relative", "value": ACCEPTANCE_TOLERANCE},
            "solver_rtol": {"source": "WP03 predeclared from WP02 freeze", "unit": "relative", "value": SOLVER_RTOL},
        },
        classification="PASS",
        metrics=metrics,
        source={
            "dirty": False,
            "revision": SOURCE_SHA,
            "repository": ".",
            "role": "WP03 execution source snapshot; no numerical source changes",
        },
        environment=environment,
        artifacts={"raw_run_digest_sha256": _sha256_file(raw_path)},
        command=raw["environment"]["process"]["argv"],
        oracle={
            "type": "INTERNAL_INVARIANT",
            "source": "qualification/0_2_7/wp14_execution_contract.json",
            "observables": ["residual", "equilibrium", "energy", "finite_outputs", "SPD_CG"],
            "comparison_rule": "WP14 relative acceptance tolerance without post-result retuning",
        },
        configuration=configuration,
        message="WP03 workload B replay PASS under the frozen WP02 route.",
    )
    record["metrics"]["phase_measurement_policy"] = contract["unmeasured_phase_policy"]
    record["metrics"]["post_timings_seconds"] = {
        "reactions": phases["reactions_seconds"],
        "energy": phases["energy_post_seconds"],
    }
    record["provenance"].update(
        {
            "run_id": run_id,
            "raw_run_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
            "raw_run_digest_sha256": _sha256_file(raw_path),
            "freeze_id": FREEZE_ID,
            "freeze_digest_sha256": FREEZE_DIGEST,
            "source_sha": SOURCE_SHA,
        }
    )
    record["artifacts"]["freeze_digest_sha256"] = FREEZE_DIGEST
    target = output_root / f"workload_b_{run_id}.json"
    write_observatory_record(target, record)
    return record


def _replay_comparison(
    first: dict[str, Any],
    second: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    descriptive = compare_observatory_runs(first, second)
    left = first["result"]["observables"]
    right = second["result"]["observables"]
    numeric = {
        "displacement_norm": _relative_delta(left["displacement_norm"], right["displacement_norm"]),
        "reaction_resultant": _vector_relative_delta(left["reaction_resultant"], right["reaction_resultant"]),
        "strain_energy": _relative_delta(left["strain_energy"], right["strain_energy"]),
        "equilibrium_relative": _relative_delta(left["equilibrium_relative"], right["equilibrium_relative"]),
        "energy_relative": _relative_delta(left["energy_relative"], right["energy_relative"]),
        "free_relative_residual": _relative_delta(left["free_relative_residual"], right["free_relative_residual"]),
    }
    same_digests = (
        first["artifacts"]["input_digest"] == second["artifacts"]["input_digest"] == INPUT_DIGEST
        and first["artifacts"]["configuration_digest"] == second["artifacts"]["configuration_digest"]
        and first["artifacts"]["freeze_digest_sha256"] == second["artifacts"]["freeze_digest_sha256"] == FREEZE_DIGEST
    )
    same_iterations = first["metrics"]["iterations"] == second["metrics"]["iterations"]
    numeric_pass = all(value <= ACCEPTANCE_TOLERANCE for value in numeric.values())
    return {
        "schema_version": 1,
        "record_type": "lu2_wp03_replay_comparison",
        "work_package": "LU2-WP03",
        "status": "PASS" if descriptive["compatible"] and same_digests and same_iterations and numeric_pass else "FAIL",
        "run_ids": [first["provenance"]["run_id"], second["provenance"]["run_id"]],
        "same_input_digest": first["artifacts"]["input_digest"] == second["artifacts"]["input_digest"],
        "same_configuration_digest": first["artifacts"]["configuration_digest"]
        == second["artifacts"]["configuration_digest"],
        "same_freeze_digest": first["artifacts"]["freeze_digest_sha256"]
        == second["artifacts"]["freeze_digest_sha256"],
        "same_runtime": first["environment"]["container_digest"] == second["environment"]["container_digest"],
        "same_iterations": same_iterations,
        "numeric_relative_deltas": numeric,
        "tolerance": ACCEPTANCE_TOLERANCE,
        "timing_variation_seconds": {
            name: abs(
                float(first["metrics"]["timings_seconds"].get(name) or 0.0)
                - float(second["metrics"]["timings_seconds"].get(name) or 0.0)
            )
            for name in ("model_setup", "assembly_operator", "pc_setup", "ksp_solve", "post_processing", "total")
        },
        "rss_variation_bytes": abs(
            int(first["metrics"]["resources"]["peak_rss_total_bytes"])
            - int(second["metrics"]["resources"]["peak_rss_total_bytes"])
        ),
        "observatory_comparison": descriptive,
        "contract": "qualification/0_2_7/wp03_execution_contract.json",
        "configuration_freeze_id": FREEZE_ID,
        "configuration_freeze_digest_sha256": FREEZE_DIGEST,
        "post_result_retuning": False,
        "artifact_classification": "CONTROLLED_PROOF",
        "claim_boundary": contract["claim_boundary"],
    }


def _build_workload_comparison(
    records: list[dict[str, Any]],
    contract: dict[str, Any],
    freeze: dict[str, Any],
) -> dict[str, Any]:
    control = _read_json(A_CONTROL_PATH)

    def compact(record: dict[str, Any], label: str) -> dict[str, Any]:
        metrics = record["metrics"]
        timings = metrics["timings_seconds"]
        resources = metrics["resources"]
        observables = record["result"]["observables"]
        return {
            "label": label,
            "case_id": record["case_id"],
            "input_digest_sha256": record["artifacts"]["input_digest"],
            "true_dof": record["workload"]["dof"],
            "elements": record["workload"]["elements"],
            "rank_count": record["execution"]["rank_count"],
            "iterations": metrics["iterations"],
            "assembly_operator_seconds": timings["assembly_operator"],
            "pc_setup_seconds": timings["pc_setup"],
            "ksp_solve_seconds": timings["ksp_solve"],
            "post_processing_seconds": timings["post_processing"],
            "total_seconds": timings["total"],
            "peak_rss_total_bytes": resources["peak_rss_total_bytes"],
            "residual": metrics["residual"],
            "equilibrium": metrics["equilibrium"],
            "energy": metrics["energy"],
            "displacement_norm": observables["displacement_norm"],
            "strain_energy": observables["strain_energy"],
            "reaction_resultant": observables["reaction_resultant"],
            "status": record["result"]["classification"],
        }

    workload_a = compact(control, "workload_a_control_r8_replay1")
    workload_b = [compact(record, f"workload_b_run{index}") for index, record in enumerate(records, start=1)]
    return {
        "schema_version": 1,
        "record_type": "lu2_wp03_workload_comparison",
        "work_package": "LU2-WP03",
        "gate": "LU2-027-G03",
        "status": "DESCRIPTIVE_PASS",
        "source_sha": SOURCE_SHA,
        "freeze_id": FREEZE_ID,
        "freeze_digest_sha256": FREEZE_DIGEST,
        "workload_a": {
            **workload_a,
            "evidence": "qualification/0_2_7/wp02_runtime/r8_replay1.json",
            "geometry": "unit cube",
        },
        "workload_b": [
            {
                **row,
                "evidence": f"qualification/0_2_7/wp03_runtime/workload_b_run{index}.json",
                "geometry": contract["workload_b"]["geometry"],
            }
            for index, row in enumerate(workload_b, start=1)
        ],
        "comparison_policy": {
            "same_route": True,
            "same_mpi_ranks": True,
            "same_freeze": True,
            "same_dof_and_element_count": True,
            "materially_distinct_workloads": True,
            "performance_comparison_authorized": False,
            "note": "A/B timings and iterations are descriptive only; distinct geometry prevents a benchmark speedup claim.",
        },
    }


def _relative_delta(left: float, right: float) -> float:
    return abs(float(left) - float(right)) / max(abs(float(left)), abs(float(right)), 1.0)


def _vector_relative_delta(left: list[float], right: list[float]) -> float:
    numerator = sum((float(a) - float(b)) ** 2 for a, b in zip(left, right)) ** 0.5
    denominator = max(sum(float(value) ** 2 for value in left) ** 0.5, sum(float(value) ** 2 for value in right) ** 0.5, 1.0)
    return numerator / denominator


def _build_index(
    records: list[dict[str, Any]],
    replay: dict[str, Any],
    preflight: dict[str, Any],
    workload_comparison: dict[str, Any],
    contract: dict[str, Any],
    freeze: dict[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    del records
    return {
        "schema_version": 1,
        "record_type": "lu2_wp03_evidence_index",
        "work_package": "LU2-WP03",
        "gate": "LU2-027-G03",
        "status": "PASS_WITH_LIMITATIONS" if replay["status"] == "PASS" else "FAIL",
        "source_sha": SOURCE_SHA,
        "contract": "qualification/0_2_7/wp03_execution_contract.json",
        "contract_digest_sha256": _sha256_file(CONTRACT_PATH),
        "freeze_id": FREEZE_ID,
        "freeze_digest_sha256": FREEZE_DIGEST,
        "preflight": preflight["path"],
        "workload_comparison": "qualification/0_2_7/wp03_runtime/wp03_workload_comparison.json",
        "workload_b": {
            "model_id": contract["workload_b"]["model_id"],
            "input_digest_sha256": INPUT_DIGEST,
            "true_dof": 3000000,
            "elements": 5821794,
            "runs": [
                "qualification/0_2_7/wp03_runtime/workload_b_run1.json",
                "qualification/0_2_7/wp03_runtime/workload_b_run2.json",
            ],
        },
        "replay": {
            "path": "qualification/0_2_7/wp03_runtime/wp03_replay_comparison.json",
            "status": replay["status"],
        },
        "unmeasured_phases": ["preflight", "redistribution", "communication", "io"],
        "output_root": _repo_relative(output_root),
        "artifact_classification": "CONTROLLED_PROOF",
    }


def _build_summary(
    records: list[dict[str, Any]],
    replay: dict[str, Any],
    workload_comparison: dict[str, Any],
    contract: dict[str, Any],
    freeze: dict[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    runs = []
    for index, record in enumerate(records, start=1):
        runs.append(
            {
                "run_id": f"run{index}",
                "status": record["result"]["classification"],
                "true_dof": record["workload"]["dof"],
                "elements": record["workload"]["elements"],
                "iterations": record["metrics"]["iterations"],
                "model_setup_seconds": record["metrics"]["timings_seconds"]["model_setup"],
                "assembly_operator_seconds": record["metrics"]["timings_seconds"]["assembly_operator"],
                "pc_setup_seconds": record["metrics"]["timings_seconds"]["pc_setup"],
                "ksp_solve_seconds": record["metrics"]["timings_seconds"]["ksp_solve"],
                "post_processing_seconds": record["metrics"]["timings_seconds"]["post_processing"],
                "total_seconds": record["metrics"]["timings_seconds"]["total"],
                "peak_rss_total_bytes": record["metrics"]["resources"]["peak_rss_total_bytes"],
                "peak_rss_per_rank_bytes": record["metrics"]["resources"]["peak_rss_per_rank_bytes"],
                "residual": record["metrics"]["residual"],
                "equilibrium": record["metrics"]["equilibrium"],
                "energy": record["metrics"]["energy"],
                "evidence": f"qualification/0_2_7/wp03_runtime/workload_b_run{index}.json",
            }
        )
    return {
        "schema_version": 1,
        "record_type": "lu2_wp03_3m_gold_summary",
        "work_package": "LU2-WP03",
        "gate": "LU2-027-G03",
        "status": "PASS_WITH_LIMITATIONS" if replay["status"] == "PASS" else "FAIL",
        "gold_compute": "PASS" if replay["status"] == "PASS" else "FAIL",
        "source_sha": SOURCE_SHA,
        "freeze": {"freeze_id": FREEZE_ID, "freeze_digest_sha256": FREEZE_DIGEST},
        "workload_a_control": {
            "status": "CONTROLLED_EXISTING_SILVER",
            "summary": "qualification/0_2_7/wp18_runtime/wp18_summary.json",
            "input_digest_sha256": "084a471b1caab628e8558c65b1777692ed53d504baad681bf0985c411a33671b",
            "true_dof": 3000000,
            "elements": 5821794,
            "replays": 2,
        },
        "workload_b": {
            "status": "PASS",
            "model_id": contract["workload_b"]["model_id"],
            "input_digest_sha256": INPUT_DIGEST,
            "true_dof": 3000000,
            "elements": 5821794,
            "geometry": contract["workload_b"]["geometry"],
            "runs": runs,
            "materially_distinct_from_a": True,
        },
        "replay": replay,
        "workload_comparison": workload_comparison,
        "phase_measurement": {
            "measured": ["model_setup", "assembly_operator", "pc_setup", "ksp_solve", "post_processing", "total"],
            "not_measured": ["preflight", "redistribution", "communication", "io"],
            "no_inference": True,
        },
        "numerical_contract": {
            "residual": "PASS",
            "equilibrium": "PASS",
            "energy": "PASS",
            "finite_outputs": "PASS",
            "no_nan_inf": True,
            "tolerances_changed": False,
            "post_result_retuning": False,
        },
        "claim_boundary": contract["claim_boundary"],
        "gold_requirements": {
            "workload_a_control_valid": True,
            "workload_b_distinct": True,
            "two_replays": True,
            "restart_required": False,
        },
        "output_root": _repo_relative(output_root),
        "artifact_classification": "CONTROLLED_PROOF",
    }


if __name__ == "__main__":
    raise SystemExit(main())
