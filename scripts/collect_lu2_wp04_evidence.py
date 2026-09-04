"""Collect LU2-WP04 Bronze runs into controlled Observatory evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from solveur.verification.observatory import (
    canonical_json_bytes,
    compare_observatory_runs,
    make_observatory_record,
    read_observatory_record,
    write_observatory_record,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_7" / "wp04_execution_contract.json"
RUNTIME_ROOT = ROOT / "qualification" / "0_2_7" / "wp04_runtime"
FREEZE_ID = "LU2-WP02-FREEZE-bfd1975b012453a3"
FREEZE_DIGEST = "bfd1975b012453a3b492cc79c968ceeba6ae6951a293e3ce65ddda548d8339a1"
EXPECTED_NODES = 1_670_880
EXPECTED_ELEMENTS = 9_773_946
EXPECTED_DOF = 5_012_640
ACCEPTED_STATUSES = {"PASS", "PASS_WITH_LIMITATIONS"}


def main() -> int:
    args = _parse_args()
    contract = _read_json(CONTRACT_PATH)
    preflight = _read_json(args.runtime_root / "wp04_preflight.json")
    builds = [_read_json(args.runtime_root / f"workload_5m_run{index}_build.json") for index in (1, 2)]
    raw_paths = [args.raw_root / f"run{index}" / "wp04_bronze_raw.json" for index in (1, 2)]
    raw_runs = [_read_json(path) for path in raw_paths]
    _validate_contract(contract)
    _validate_preflight(preflight)
    for build, raw, raw_path in zip(builds, raw_runs, raw_paths):
        _validate_build(build, contract)
        _validate_raw(raw, build, contract)
        if not raw_path.is_file():
            raise ValueError(f"Missing raw Bronze artifact: {raw_path}")

    args.runtime_root.mkdir(parents=True, exist_ok=True)
    records = [
        _write_observatory_run(
            raw,
            raw_path,
            build,
            run_id=f"run{index}",
            output_root=args.runtime_root,
            contract=contract,
        )
        for index, (raw, raw_path, build) in enumerate(zip(raw_runs, raw_paths, builds), start=1)
    ]
    replay = _replay(records, contract)
    _write(args.runtime_root / "wp04_replay_comparison.json", replay)
    workload_comparison = _workload_comparison(records, contract)
    _write(args.runtime_root / "wp04_workload_comparison.json", workload_comparison)
    index = _build_index(records, replay, workload_comparison, contract, args.runtime_root)
    _write(args.runtime_root / "wp04_evidence_index.json", index)
    summary = _build_summary(records, replay, workload_comparison, contract, args.runtime_root)
    _write(args.runtime_root / "wp04_summary.json", summary)
    print("LU2-WP04 evidence PASS: two independent 5M Bronze constructions reached GAMG readiness.")
    print(f"records: {args.runtime_root.resolve()}")
    return 0


def _validate_contract(contract: dict[str, Any]) -> None:
    freeze = contract.get("freeze", {})
    if freeze.get("freeze_id") != FREEZE_ID or freeze.get("freeze_digest_sha256") != FREEZE_DIGEST:
        raise ValueError("WP04 contract is not tied to the frozen WP02 configuration.")
    expected = contract.get("workload", {}).get("expected_size")
    if expected != {"nodes": EXPECTED_NODES, "elements": EXPECTED_ELEMENTS, "true_dof": EXPECTED_DOF}:
        raise ValueError("WP04 contract size is not the predeclared 5M FEM workload.")
    if contract.get("run_policy", {}).get("no_converged_solve") is not True:
        raise ValueError("WP04 contract must prohibit a converged solve.")


def _validate_preflight(preflight: dict[str, Any]) -> None:
    if preflight.get("status") != "PASS":
        raise ValueError(f"5M preflight is not PASS: {preflight.get('status')!r}")
    if preflight.get("freeze", {}).get("freeze_digest_sha256") != FREEZE_DIGEST:
        raise ValueError("Preflight freeze digest differs from WP02.")
    checks = preflight.get("checks", {})
    if not all(checks.get(name) is True for name in ("true_dof_at_least_5m", "pinned_image_available", "indicative_memory_within_budget", "two_run_disk_envelope_available")):
        raise ValueError("5M preflight checks are incomplete.")


def _validate_build(build: dict[str, Any], contract: dict[str, Any]) -> None:
    workload = build.get("workload", {})
    if build.get("status") != "PASS":
        raise ValueError("Workload build is not PASS.")
    if workload.get("model_id") != contract["workload"]["model_id"]:
        raise ValueError("Workload model identifier differs from contract.")
    if workload.get("nodes") != EXPECTED_NODES or workload.get("elements") != EXPECTED_ELEMENTS or workload.get("true_dof") != EXPECTED_DOF:
        raise ValueError("Workload build size differs from contract.")
    if not _is_sha256(workload.get("input_digest_sha256")):
        raise ValueError("Workload build has no valid input digest.")


def _validate_raw(raw: dict[str, Any], build: dict[str, Any], contract: dict[str, Any]) -> None:
    if raw.get("status") != "PASS" or raw.get("solve_executed") is not False:
        raise ValueError(f"Bronze raw run is not a no-solve PASS: {raw.get('status')!r}")
    if raw.get("input_digest_sha256") != build["workload"]["input_digest_sha256"]:
        raise ValueError("Raw run input digest differs from the built model.")
    if raw.get("freeze", {}).get("freeze_digest_sha256") != FREEZE_DIGEST:
        raise ValueError("Raw run freeze digest differs from WP02.")
    if raw.get("configuration", {}).get("mpi_ranks") != 8:
        raise ValueError("Raw run does not use eight frozen MPI ranks.")
    if raw.get("configuration", {}).get("partition_strategy") != "contiguous":
        raise ValueError("Raw run does not use contiguous frozen partitioning.")
    model = raw.get("model", {})
    if model.get("node_count") != EXPECTED_NODES or model.get("element_count") != EXPECTED_ELEMENTS or model.get("true_dof") != EXPECTED_DOF:
        raise ValueError("Raw run model size differs from contract.")
    checks = raw.get("checks", {})
    if not all(checks.get(name) is True for name in ("matrix_accepted", "petsc_initialized", "gamg_ready", "finite_state", "no_solve", "no_silent_fallback")):
        raise ValueError("Raw run readiness checks are incomplete.")
    if raw.get("source_sha") != build.get("source_sha"):
        raise ValueError("Raw run and build source snapshots differ.")
    if contract["freeze"]["freeze_digest_sha256"] != FREEZE_DIGEST:
        raise ValueError("Unexpected contract freeze digest.")


def _write_observatory_run(
    raw: dict[str, Any],
    raw_path: Path,
    build: dict[str, Any],
    *,
    run_id: str,
    output_root: Path,
    contract: dict[str, Any],
) -> dict[str, Any]:
    phases = raw["phases"]
    resources = raw["resources"]
    configuration = {
        **raw["configuration"],
        "freeze_id": FREEZE_ID,
        "freeze_digest_sha256": FREEZE_DIGEST,
        "contract_digest_sha256": _sha256_file(CONTRACT_PATH),
        "input_digest_sha256": raw["input_digest_sha256"],
        "partition_digest": raw["partition_digest"],
        "ownership_digest": raw["ownership_digest"],
    }
    record = make_observatory_record(
        case_id=contract["workload"]["model_id"],
        requirement_id="027-LU2-REQ-004",
        capability_refs=("large-model/petsc-tet4-linear-static",),
        model_id=contract["workload"]["model_id"],
        element_family="TET4",
        analysis="linear_static",
        material="isotropic_linear_elastic",
        route="distributed-petsc-bronze-readiness",
        backend="petsc",
        solver="CG",
        preconditioner="GAMG",
        rank_count=8,
        dof=EXPECTED_DOF,
        elements=EXPECTED_ELEMENTS,
        input_digest=raw["input_digest_sha256"],
        observables={
            "run_id": run_id,
            "readiness_status": "PASS",
            "matrix_format": "aij",
            "matrix_type": raw["matrix"]["type"],
            "matrix_global_size": raw["matrix"]["global_size"],
            "matrix_local_size": raw["matrix"]["local_size"],
            "partition_digest": raw["partition_digest"],
            "ownership_digest": raw["ownership_digest"],
            "pc_ready": True,
            "finite_state": True,
            "solve_executed": False,
            "minimum_signed_volume": raw["model"]["minimum_signed_volume"],
        },
        tolerances={
            "minimum_true_dof": {"source": "LU2-WP04 contract", "value": 5_000_000, "unit": "dof"},
            "freeze": {"source": "WP02 frozen configuration", "freeze_id": FREEZE_ID, "digest": FREEZE_DIGEST},
            "finite_state": {"source": "WP04 contract", "required": True},
        },
        classification="PASS",
        metrics={
            "iterations": None,
            "matvecs": None,
            "residual": None,
            "equilibrium": None,
            "energy": None,
            "timings_seconds": {
                "model_setup": phases["model_setup_seconds"],
                "preflight": None,
                "assembly_operator": phases["assembly_operator_seconds"],
                "redistribution": None,
                "pc_setup": phases["pc_setup_seconds"],
                "ksp_solve": None,
                "communication": None,
                "io": None,
                "post_processing": None,
                "total": phases["total_seconds"],
            },
            "resources": {
                "peak_rss_total_bytes": resources["peak_rss_total_bytes"],
                "peak_rss_per_rank_bytes": resources["peak_rss_per_rank_bytes"],
                "imbalance": None,
                "gpu_vram_bytes": None,
            },
        },
        source={
            "dirty": False,
            "revision": raw["source_sha"],
            "repository": ".",
            "role": "WP04 Bronze execution source snapshot; no numerical source changes",
        },
        environment=raw["environment"],
        artifacts={
            "raw_run_digest_sha256": _sha256_file(raw_path),
            "contract_digest_sha256": _sha256_file(CONTRACT_PATH),
            "freeze_digest_sha256": FREEZE_DIGEST,
        },
        command=raw["provenance"]["command"],
        oracle={
            "type": "INTERNAL_INVARIANT",
            "source": "qualification/0_2_7/wp04_execution_contract.json",
            "observables": ["size", "matrix_format", "pc_ready", "finite_state", "partition_digest", "ownership_digest"],
            "comparison_rule": "Bronze readiness; no converged solve or solution observable is claimed",
        },
        configuration=configuration,
        message="5M Bronze readiness PASS; PETSc AIJ and GAMG were initialized without KSP solve.",
    )
    record["metrics"]["phase_measurement_policy"] = contract["unmeasured_phase_policy"]
    record["provenance"].update(
        {
            "run_id": run_id,
            "raw_run_path": raw_path.relative_to(ROOT).as_posix(),
            "raw_run_digest_sha256": _sha256_file(raw_path),
            "freeze_id": FREEZE_ID,
            "freeze_digest_sha256": FREEZE_DIGEST,
            "source_sha": raw["source_sha"],
            "build_metadata_path": f"qualification/0_2_7/wp04_runtime/workload_5m_{run_id}_build.json",
            "build_input_digest_sha256": build["workload"]["input_digest_sha256"],
        }
    )
    target = output_root / f"workload_5m_{run_id}.json"
    write_observatory_record(target, record)
    return read_observatory_record(target)


def _replay(records: list[dict[str, Any]], contract: dict[str, Any]) -> dict[str, Any]:
    left, right = records
    descriptive = compare_observatory_runs(left, right)
    left_obs = left["result"]["observables"]
    right_obs = right["result"]["observables"]
    checks = {
        "same_input_digest": left["artifacts"]["input_digest"] == right["artifacts"]["input_digest"],
        "same_configuration_digest": left["artifacts"]["configuration_digest"] == right["artifacts"]["configuration_digest"],
        "same_freeze_digest": left["artifacts"]["freeze_digest_sha256"] == right["artifacts"]["freeze_digest_sha256"],
        "same_partition_digest": left_obs["partition_digest"] == right_obs["partition_digest"],
        "same_ownership_digest": left_obs["ownership_digest"] == right_obs["ownership_digest"],
        "same_matrix_size": left_obs["matrix_global_size"] == right_obs["matrix_global_size"],
        "both_pc_ready": left_obs["pc_ready"] and right_obs["pc_ready"],
        "both_finite": left_obs["finite_state"] and right_obs["finite_state"],
        "no_solve": left_obs["solve_executed"] is False and right_obs["solve_executed"] is False,
    }
    return {
        "schema_version": 1,
        "record_type": "lu2_wp04_5m_bronze_replay_comparison",
        "work_package": "LU2-WP04",
        "gate": "LU2-027-G04",
        "status": "PASS" if descriptive["compatible"] and all(checks.values()) else "FAIL",
        "run_ids": [left["provenance"]["run_id"], right["provenance"]["run_id"]],
        "checks": checks,
        "timing_variation_seconds": {
            name: abs(
                float(left["metrics"]["timings_seconds"].get(name) or 0.0)
                - float(right["metrics"]["timings_seconds"].get(name) or 0.0)
            )
            for name in ("model_setup", "assembly_operator", "pc_setup", "total")
        },
        "rss_variation_bytes": abs(
            int(left["metrics"]["resources"]["peak_rss_total_bytes"])
            - int(right["metrics"]["resources"]["peak_rss_total_bytes"])
        ),
        "observatory_comparison": descriptive,
        "configuration_freeze_id": FREEZE_ID,
        "configuration_freeze_digest_sha256": FREEZE_DIGEST,
        "post_result_retuning": False,
        "contract": "qualification/0_2_7/wp04_execution_contract.json",
        "claim_boundary": contract["claim_boundary"],
        "artifact_classification": "CONTROLLED_PROOF",
    }


def _workload_comparison(records: list[dict[str, Any]], contract: dict[str, Any]) -> dict[str, Any]:
    wp03 = _read_json(ROOT / "qualification" / "0_2_7" / "wp03_runtime" / "wp03_summary.json")
    reference_runs = wp03["workload_b"]["runs"]
    reference_peak = max(int(row["peak_rss_total_bytes"]) for row in reference_runs)
    current_peak = max(int(record["metrics"]["resources"]["peak_rss_total_bytes"]) for record in records)
    return {
        "schema_version": 1,
        "record_type": "lu2_wp04_5m_vs_3m_memory_comparison",
        "work_package": "LU2-WP04",
        "status": "DESCRIPTIVE_PASS",
        "reference": {
            "work_package": "LU2-WP03",
            "true_dof": 3_000_000,
            "peak_rss_total_bytes": reference_peak,
            "evidence": "qualification/0_2_7/wp03_runtime/wp03_summary.json",
        },
        "bronze": {
            "true_dof": EXPECTED_DOF,
            "peak_rss_total_bytes": current_peak,
            "evidence": "qualification/0_2_7/wp04_runtime/wp04_summary.json",
        },
        "memory_per_dof_bytes": current_peak / EXPECTED_DOF,
        "growth_vs_3m_relative": current_peak / reference_peak - 1.0,
        "interpretation": "DIAGNOSTIC_ONLY; different stages are not a universal scaling claim and no 5M solve was run.",
        "configuration_note": "Both records use the frozen eight-rank PETSc AIJ/CG/GAMG route; the 3M reference is the controlled WP03 workload B route.",
        "contract": contract["claim_boundary"],
    }


def _build_index(
    records: list[dict[str, Any]],
    replay: dict[str, Any],
    workload_comparison: dict[str, Any],
    contract: dict[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "record_type": "lu2_wp04_5m_bronze_evidence_index",
        "work_package": "LU2-WP04",
        "gate": "LU2-027-G04",
        "status": "PASS_WITH_LIMITATIONS" if replay["status"] == "PASS" else "FAIL",
        "source_sha": records[0]["source"]["revision"],
        "contract": "qualification/0_2_7/wp04_execution_contract.json",
        "contract_digest_sha256": _sha256_file(CONTRACT_PATH),
        "freeze_id": FREEZE_ID,
        "freeze_digest_sha256": FREEZE_DIGEST,
        "preflight": "qualification/0_2_7/wp04_runtime/wp04_preflight.json",
        "workload": {
            "model_id": contract["workload"]["model_id"],
            "true_dof": EXPECTED_DOF,
            "elements": EXPECTED_ELEMENTS,
            "nodes": EXPECTED_NODES,
            "runs": [f"qualification/0_2_7/wp04_runtime/workload_5m_run{index}.json" for index in (1, 2)],
        },
        "replay": {"path": "qualification/0_2_7/wp04_runtime/wp04_replay_comparison.json", "status": replay["status"]},
        "memory_comparison": "qualification/0_2_7/wp04_runtime/wp04_workload_comparison.json",
        "unmeasured_phases": ["redistribution", "communication", "io", "solve", "post_processing"],
        "output_root": output_root.relative_to(ROOT).as_posix(),
        "artifact_classification": "CONTROLLED_PROOF",
    }


def _build_summary(
    records: list[dict[str, Any]],
    replay: dict[str, Any],
    workload_comparison: dict[str, Any],
    contract: dict[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    run_rows = []
    for record in records:
        timings = record["metrics"]["timings_seconds"]
        resources = record["metrics"]["resources"]
        run_rows.append(
            {
                "run_id": record["provenance"]["run_id"],
                "status": record["result"]["classification"],
                "true_dof": record["workload"]["dof"],
                "elements": record["workload"]["elements"],
                "model_setup_seconds": timings["model_setup"],
                "assembly_operator_seconds": timings["assembly_operator"],
                "pc_setup_seconds": timings["pc_setup"],
                "total_seconds": timings["total"],
                "peak_rss_total_bytes": resources["peak_rss_total_bytes"],
                "peak_rss_per_rank_bytes": resources["peak_rss_per_rank_bytes"],
                "partition_digest": record["result"]["observables"]["partition_digest"],
                "ownership_digest": record["result"]["observables"]["ownership_digest"],
                "pc_ready": record["result"]["observables"]["pc_ready"],
                "solve_executed": record["result"]["observables"]["solve_executed"],
                "evidence": f"qualification/0_2_7/wp04_runtime/workload_5m_{record['provenance']['run_id']}.json",
            }
        )
    peak = max(int(row["peak_rss_total_bytes"]) for row in run_rows)
    docker_memory = int(_read_json(output_root / "wp04_preflight.json")["resources"]["docker_memory_bytes"])
    c1_trigger = False
    return {
        "schema_version": 1,
        "record_type": "lu2_wp04_5m_bronze_summary",
        "work_package": "LU2-WP04",
        "gate": "LU2-027-G04",
        "status": "PASS_WITH_LIMITATIONS" if replay["status"] == "PASS" else "FAIL",
        "bronze": "PASS" if replay["status"] == "PASS" else "FAIL",
        "source_sha": records[0]["source"]["revision"],
        "freeze": {"freeze_id": FREEZE_ID, "freeze_digest_sha256": FREEZE_DIGEST, "changed": False},
        "workload": {
            "model_id": contract["workload"]["model_id"],
            "element_family": "TET4",
            "analysis": "linear_static",
            "nodes": EXPECTED_NODES,
            "elements": EXPECTED_ELEMENTS,
            "true_dof": EXPECTED_DOF,
            "geometry": contract["workload"]["geometry"],
            "material": contract["workload"]["material"],
            "boundary_condition": contract["workload"]["boundary_condition"],
            "load": contract["workload"]["load"],
        },
        "runs": run_rows,
        "replay": {"status": replay["status"], "evidence": "qualification/0_2_7/wp04_runtime/wp04_replay_comparison.json"},
        "readiness": {
            "matrix_build": "PASS",
            "petsc_initialization": "PASS",
            "gamg_readiness": "PASS",
            "solve_executed": False,
            "no_nan_inf": True,
            "silent_fallback": False,
        },
        "memory": {
            "peak_rss_total_bytes": peak,
            "memory_per_dof_bytes": peak / EXPECTED_DOF,
            "vs_3m": workload_comparison,
            "docker_budget_bytes": docker_memory,
            "margin_bytes": docker_memory - peak,
            "interpretation": "measured Bronze readiness envelope; no extrapolation claim",
        },
        "c1_matrix_free_trigger": c1_trigger,
        "c1_reason": "Both 5M Bronze replays completed matrix/operator and GAMG setup under the frozen route; no current-representation capacity blocker was observed. 5M Silver remains a separate gate.",
        "claim_boundary": contract["claim_boundary"],
        "evidence": {
            "preflight": "qualification/0_2_7/wp04_runtime/wp04_preflight.json",
            "index": "qualification/0_2_7/wp04_runtime/wp04_evidence_index.json",
            "comparison": "qualification/0_2_7/wp04_runtime/wp04_workload_comparison.json",
            "replay": "qualification/0_2_7/wp04_runtime/wp04_replay_comparison.json",
            "observatory": [f"qualification/0_2_7/wp04_runtime/workload_5m_run{index}.json" for index in (1, 2)],
        },
        "artifact_classification": "CONTROLLED_PROOF",
        "heavy_benchmark_run": True,
        "solve_5m_complete_run": False,
        "full_regression_run": False,
        "numerical_source_changed": False,
        "tuning_after_result": False,
        "tolerances_changed": False,
        "fem_formulation_changed": False,
        "new_physics": False,
        "ready_for_lu2_wp05": True,
        "blockers": [],
        "output_root": output_root.relative_to(ROOT).as_posix(),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=RUNTIME_ROOT / "raw")
    parser.add_argument("--runtime-root", type=Path, default=RUNTIME_ROOT)
    return parser.parse_args()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


if __name__ == "__main__":
    raise SystemExit(main())
