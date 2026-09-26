"""Freeze and run one M4 slip-only diagnostic with lossless failure evidence.

This is a new prospective forensic attempt. It does not modify solver
mechanics, thresholds, loads, mesh, iteration limits, or fallback behavior.
The previously recorded M4 failure and all M1/M2/M3 evidence are read-only.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter
from typing import Any

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts import run_wp08_area_supported_m4_diagnostic_r1_10 as base  # noqa: E402

ARTIFACT_ID = "QF-029-WP08-AREA-SUPPORTED-CONTACT-M4-SLIP-FORENSIC-R2"
OUTPUT_REL = Path(
    "qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_10_m4_slip_forensic_r2_20260926"
)
DOC_REL = Path("docs/verification/0_2_9/wp08-area-supported-contact-m4-slip-forensic-r2.md")
OLD_M4_ROOT_REL = base.OUTPUT_REL
MAX_INLINE_VALUES = 512
SPARSE_ZERO_TOLERANCE = 0.0


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _binding_sha(binding: Mapping[str, Any]) -> str:
    normalized = dict(binding)
    normalized["execution_binding_sha256"] = None
    return _canonical_sha(normalized)


def _write_json(path: Path, value: object, *, exclusive: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def _source_inventory() -> dict[str, str]:
    files = {
        path
        for folder in (ROOT / "src", ROOT / "scripts")
        for path in folder.rglob("*.py")
        if "__pycache__" not in path.parts
    }
    files.update(ROOT / relative for relative in base.SOURCE_TESTS)
    missing = [path for path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing bound source/test file: {missing[0]}")
    return {
        path.relative_to(ROOT).as_posix(): _sha(path)
        for path in sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())
    }


def _old_m4_evidence() -> dict[str, Any]:
    root = ROOT / OLD_M4_ROOT_REL
    contract_path = root / "contract.json"
    binding_path = root / "execution_binding.json"
    audit_path = root / "m4_final_audit.json"
    failure_path = root / "M4" / "slip_target" / "failure.json"
    telemetry_path = root / "M4" / "slip_target" / "telemetry.jsonl"
    process_path = root / "_process_logs" / "M4_slip_target.process.json"
    stderr_path = root / "_process_logs" / "M4_slip_target.stderr.log"
    required = (contract_path, binding_path, audit_path, failure_path, telemetry_path, process_path, stderr_path)
    if not all(path.is_file() for path in required):
        raise FileNotFoundError("The original M4 slip failure package is incomplete.")

    contract, binding = _read_json(contract_path), _read_json(binding_path)
    audit, failure = _read_json(audit_path), _read_json(failure_path)
    process = _read_json(process_path)
    if contract.get("status") != "FROZEN_PROSPECTIVE_EXPERIMENTAL_M4_ONLY":
        raise RuntimeError("Original M4 contract is not the expected frozen diagnostic.")
    if _sha(contract_path) != binding.get("contract_sha256"):
        raise RuntimeError("Original M4 contract hash mismatch.")
    if binding.get("execution_binding_sha256") != _binding_sha(binding):
        raise RuntimeError("Original M4 execution binding hash mismatch.")
    prior = audit.get("results", {}).get("slip_target", {})
    if (
        audit.get("classification") != "EXPERIMENTAL_EXECUTION_PARTIAL_FAIL_CLOSED"
        or prior.get("status") != "FAIL_CLOSED"
        or prior.get("failure_type") != "NumericalConvergenceError"
        or process.get("exit_code") != 1
        or failure.get("error_type") != "NumericalConvergenceError"
    ):
        raise RuntimeError("Original M4 failure is not the expected numerical FAIL_CLOSED record.")
    file_hashes = {
        "contract": _sha(contract_path),
        "execution_binding": _sha(binding_path),
        "final_audit": _sha(audit_path),
        "failure": _sha(failure_path),
        "telemetry": _sha(telemetry_path),
        "process_manifest": _sha(process_path),
        "stderr": _sha(stderr_path),
    }
    for key, field in (
        ("failure", "failure_sha256"),
        ("telemetry", "telemetry_sha256"),
        ("stderr", "stderr_sha256"),
        ("process_manifest", "process_manifest_sha256"),
    ):
        if prior.get(field) != file_hashes[key]:
            raise RuntimeError(f"Original M4 audit does not bind {key} bytes.")
    if process.get("failure_sha256") != file_hashes["failure"]:
        raise RuntimeError("Original M4 process manifest failure hash mismatch.")
    if process.get("telemetry_sha256") != file_hashes["telemetry"]:
        raise RuntimeError("Original M4 process manifest telemetry hash mismatch.")
    if process.get("stderr_sha256") != file_hashes["stderr"]:
        raise RuntimeError("Original M4 process manifest stderr hash mismatch.")
    return {
        "root": OLD_M4_ROOT_REL.as_posix(),
        "classification": audit["classification"],
        "failure_step": prior.get("failure_step"),
        "accepted_steps_before_failure": prior.get("accepted_steps_before_failure"),
        "active_slip_residual": prior.get("active_slip_residual"),
        "active_slip_tolerance": prior.get("active_slip_tolerance"),
        "files": {
            key: {"path": path.relative_to(ROOT).as_posix(), "sha256": file_hashes[key]}
            for key, path in (
                ("contract", contract_path),
                ("execution_binding", binding_path),
                ("final_audit", audit_path),
                ("failure", failure_path),
                ("telemetry", telemetry_path),
                ("process_manifest", process_path),
                ("stderr", stderr_path),
            )
        },
    }


def _sparse_vector(value: object) -> dict[str, Any]:
    vector = np.asarray(value, dtype=np.float64).reshape(-1)
    keep = np.flatnonzero((np.abs(vector) > SPARSE_ZERO_TOLERANCE) | ~np.isfinite(vector))
    return {
        "encoding": "exact_sparse_float64",
        "length": int(vector.size),
        "indices": keep.astype(int).tolist(),
        "values": [_json_safe(float(vector[index])) for index in keep],
        "dense_little_endian_sha256": hashlib.sha256(
            np.asarray(vector, dtype="<f8").tobytes(order="C")
        ).hexdigest(),
    }


def _array_summary(value: object) -> dict[str, Any]:
    array = np.asarray(value)
    numeric = np.asarray(array, dtype=np.float64)
    finite = numeric[np.isfinite(numeric)]
    nonfinite_indices = np.flatnonzero(~np.isfinite(numeric.reshape(-1)))
    return {
        "encoding": "bounded_numeric_array_summary",
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "finite_count": int(finite.size),
        "nonfinite_count": int(numeric.size - finite.size),
        "nonfinite_entries_sample": [
            {"flat_index": int(index), "value": _json_safe(float(numeric.reshape(-1)[index]))}
            for index in nonfinite_indices[:MAX_INLINE_VALUES]
        ],
        "nonfinite_entries_truncated": bool(nonfinite_indices.size > MAX_INLINE_VALUES),
        "l2_norm_finite_part": float(np.linalg.norm(finite)) if finite.size else 0.0,
        "minimum_finite": float(np.min(finite)) if finite.size else None,
        "maximum_finite": float(np.max(finite)) if finite.size else None,
        "little_endian_float64_sha256": hashlib.sha256(
            np.asarray(numeric, dtype="<f8").tobytes(order="C")
        ).hexdigest(),
    }


def _json_safe(value: Any, *, key: str | None = None) -> Any:
    if key == "tangential_basis" and isinstance(value, (list, tuple)):
        return [_sparse_vector(vector) for vector in value]
    if isinstance(value, Mapping):
        return {str(item_key): _json_safe(item_value, key=str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, np.ndarray):
        if value.size > MAX_INLINE_VALUES:
            return _array_summary(value)
        return _json_safe(value.tolist())
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_INLINE_VALUES and all(
            isinstance(item, (int, float, np.number)) for item in value
        ):
            return _array_summary(value)
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        return numeric if np.isfinite(numeric) else f"NONFINITE:{numeric!r}"
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if value is None or isinstance(value, (str, int)):
        return value
    return repr(value)


def _exception_record(error: BaseException, *, depth: int = 0) -> dict[str, Any]:
    record: dict[str, Any] = {"type": type(error).__name__, "message": str(error)}
    to_dict = getattr(error, "to_dict", None)
    if callable(to_dict):
        try:
            record["solver_error_record"] = _json_safe(to_dict())
        except Exception as serialization_error:  # forensic serialization must remain explicit
            record["solver_error_serialization_error"] = (
                f"{type(serialization_error).__name__}: {serialization_error}"
            )
    diagnostics = getattr(error, "diagnostics", None)
    if diagnostics is not None:
        record["diagnostics"] = _json_safe(diagnostics)
    reason = getattr(error, "reason", None)
    if reason is not None:
        record["reason"] = getattr(reason, "value", str(reason))
    cause = error.__cause__ or error.__context__
    if cause is not None and depth < 5:
        record["cause_chain"] = _exception_record(cause, depth=depth + 1)
    return record


def _contract_payload(inventory: dict[str, str], parent: dict[str, Any], old_m4: dict[str, Any]) -> dict[str, Any]:
    prior_contract_path = ROOT / OLD_M4_ROOT_REL / "contract.json"
    prior_contract = _read_json(prior_contract_path)
    return {
        "schema": "qf.wp08.area_supported_contact_m4_slip_forensic_contract.r1",
        "artifact_id": ARTIFACT_ID,
        "status": "FROZEN_PROSPECTIVE_SINGLE_ATTEMPT",
        "frozen_utc": _utc(),
        "contract_document": DOC_REL.as_posix(),
        "contract_document_sha256": _sha(ROOT / DOC_REL),
        "execution": {
            "output_root": OUTPUT_REL.as_posix(),
            "attempts": 1,
            "overwrite_or_retry": False,
            "sequence": ["M4/slip_target"],
            "one_solver_process_at_a_time": True,
            "rerun_stick": False,
            "rerun_M1_M2_M3": False,
            "reference_or_replay": False,
        },
        "purpose": "Capture the full nested numerical failure diagnostics from one fresh reproduction of the already failed M4 slip case; do not tune or qualify.",
        "frozen_case_inputs": {
            "parent_contract_sha256": _sha(prior_contract_path),
            "parent_contract_artifact_id": prior_contract.get("artifact_id"),
            "parent_mesh": prior_contract.get("mesh"),
            "parent_benchmark": prior_contract.get("benchmark"),
            "parent_diagnostic_gates": prior_contract.get("diagnostic_gates"),
            "parent_policy_context_only": prior_contract.get("policy_context_only"),
            "source_bundle_sha256": _canonical_sha(inventory),
            "parent_m1_m2_m3_read_only": parent,
            "original_m4_failure_read_only": old_m4,
        },
        "diagnostic_capture": {
            "capture_exception_to_dict": True,
            "capture_nested_causes": True,
            "capture_optimizer_status_message_nfev": True,
            "capture_per_contact_residuals": True,
            "dense_global_tangential_basis_encoding": "exact sparse nonzero indices/values plus SHA-256 of full float64 vector",
            "oversized_numeric_vectors": "bounded summary with shape, finite counts, norm, extrema and SHA-256",
            "nonfinite_values": "explicit NONFINITE string; never silently converted to PASS",
        },
        "change_policy": {
            "production_source_changed": False,
            "thresholds_changed": False,
            "mesh_load_material_friction_or_stiffness_changed": False,
            "iteration_or_fallback_policy_changed": False,
            "historical_evidence_overwritten": False,
        },
        "policy_digest_context_only": base.POLICY_DIGEST_CONTEXT,
        "source_manifest_sha256": _canonical_sha(inventory),
        "owner_authorization": {
            "authorized": True,
            "recorded_from": "Owner instruction: freeze the runner and launch execution; explicit green light.",
            "scope": "Exactly one fresh M4/slip_target diagnostic attempt with the R1.10 frozen inputs, separate output directory, and enriched failure serialization; no retry, no tuning, no formal qualification or points.",
        },
    }


def freeze() -> dict[str, Any]:
    output = ROOT / OUTPUT_REL
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite forensic output root: {output}")
    if _git("status", "--porcelain"):
        raise RuntimeError("Runner freeze requires a clean tracked/untracked source checkout.")
    parent = base._parent_evidence()
    old_m4 = _old_m4_evidence()
    inventory = _source_inventory()
    contract = _contract_payload(inventory, parent, old_m4)
    output.mkdir(parents=True, exist_ok=False)
    _write_json(output / "contract.json", contract)
    _write_json(output / "source_manifest.json", inventory)
    binding: dict[str, Any] = {
        "schema": "qf.wp08.area_supported_contact_m4_slip_forensic_binding.r1",
        "artifact_id": ARTIFACT_ID,
        "frozen_utc": contract["frozen_utc"],
        "contract_sha256": _sha(output / "contract.json"),
        "source_bundle_sha256": _canonical_sha(inventory),
        "runner_sha256": _sha(Path(__file__).resolve()),
        "contract_document_sha256": _sha(ROOT / DOC_REL),
        "source_head": _git("rev-parse", "HEAD"),
        "git": {
            "branch": _git("branch", "--show-current"),
            "head": _git("rev-parse", "HEAD"),
            "status_porcelain_at_freeze": _git("status", "--porcelain"),
        },
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "parent_m1_m2_m3_evidence_sha256": _canonical_sha(parent),
        "original_m4_failure_evidence_sha256": _canonical_sha(old_m4),
        "owner_authorization": contract["owner_authorization"],
        "execution_binding_sha256": None,
    }
    binding["execution_binding_sha256"] = _binding_sha(binding)
    _write_json(output / "execution_binding.json", binding)
    record = {
        "status": "FROZEN_READY_TO_EXECUTE",
        "artifact_id": ARTIFACT_ID,
        "frozen_utc": binding["frozen_utc"],
        "contract_sha256": binding["contract_sha256"],
        "runner_sha256": binding["runner_sha256"],
        "source_bundle_sha256": binding["source_bundle_sha256"],
        "execution_binding_sha256": binding["execution_binding_sha256"],
        "source_head": binding["source_head"],
        "owner_authorization": binding["owner_authorization"],
    }
    _write_json(output / "freeze_record.json", record)
    return record


def _verify_frozen(output: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if output.resolve() != (ROOT / OUTPUT_REL).resolve():
        raise PermissionError("Forensic output path differs from the frozen dedicated path.")
    contract_path, binding_path = output / "contract.json", output / "execution_binding.json"
    contract, binding = _read_json(contract_path), _read_json(binding_path)
    manifest = _read_json(output / "source_manifest.json")
    if contract.get("status") != "FROZEN_PROSPECTIVE_SINGLE_ATTEMPT":
        raise RuntimeError("Forensic contract is not frozen for prospective execution.")
    if _sha(contract_path) != binding.get("contract_sha256"):
        raise RuntimeError("Forensic contract hash mismatch.")
    if binding.get("execution_binding_sha256") != _binding_sha(binding):
        raise RuntimeError("Forensic execution-binding hash mismatch.")
    if manifest != _source_inventory() or _canonical_sha(manifest) != binding.get("source_bundle_sha256"):
        raise RuntimeError("Source inventory changed after the forensic freeze.")
    if _sha(Path(__file__).resolve()) != binding.get("runner_sha256"):
        raise RuntimeError("Forensic runner changed after freeze.")
    if _sha(ROOT / DOC_REL) != binding.get("contract_document_sha256"):
        raise RuntimeError("Forensic contract document changed after freeze.")
    if _git("rev-parse", "HEAD") != binding.get("source_head"):
        raise RuntimeError("Git HEAD changed after the forensic freeze.")
    if _git("branch", "--show-current") != binding.get("git", {}).get("branch"):
        raise RuntimeError("Git branch changed after the forensic freeze.")
    if not _git_status_is_only_frozen_output(_git("status", "--porcelain")):
        raise RuntimeError("Source checkout changed after freeze outside the dedicated evidence directory.")
    parent = base._parent_evidence()
    old_m4 = _old_m4_evidence()
    if _canonical_sha(parent) != binding.get("parent_m1_m2_m3_evidence_sha256"):
        raise RuntimeError("Read-only parent campaign evidence changed after freeze.")
    if _canonical_sha(old_m4) != binding.get("original_m4_failure_evidence_sha256"):
        raise RuntimeError("Historical M4 failure evidence changed after freeze.")
    if contract.get("source_manifest_sha256") != binding.get("source_bundle_sha256"):
        raise RuntimeError("Contract/source binding mismatch.")
    if contract.get("owner_authorization", {}).get("authorized") is not True:
        raise PermissionError("No explicit authorization is recorded in the frozen contract.")
    return contract, binding


def _git_status_is_only_frozen_output(status: str) -> bool:
    output_prefix = OUTPUT_REL.as_posix().rstrip("/") + "/"
    for line in status.splitlines():
        if not line.startswith("?? "):
            return False
        relative = line[3:].replace("\\", "/")
        if not relative.startswith(output_prefix):
            return False
    return True


def _worker(output: Path, binding_sha: str) -> int:
    contract, binding = _verify_frozen(output.resolve())
    if binding.get("execution_binding_sha256") != binding_sha:
        raise RuntimeError("Worker execution binding argument mismatch.")
    case_dir = output / "M4" / "slip_target"
    case_dir.mkdir(parents=True, exist_ok=False)
    from solveur.api.public import solve_model
    from solveur.core.telemetry.jsonl import JsonlSink
    from solveur.core.telemetry.observer import TelemetryEmitter

    model, body, slave_nodes, area_by_node = base._build_model("slip_target")
    sink = JsonlSink(case_dir / "telemetry.jsonl", fsync=True, sink_identifier="wp08_area_m4_slip_forensic_r2")
    telemetry = TelemetryEmitter(
        analysis_id=f"{ARTIFACT_ID}-M4-slip_target",
        analysis_type="linear_static",
        route="linear_static",
        sinks=(sink,),
        metadata={
            "contract_sha256": binding["contract_sha256"],
            "execution_binding_sha256": binding_sha,
            "source_bundle_sha256": binding["source_bundle_sha256"],
            "mesh": "M4",
            "case": "slip_target",
            "forensic_capture": True,
        },
    )
    started = perf_counter()
    try:
        result = solve_model(model, enforce_policy=False, telemetry=telemetry)
        payload = result.to_dict()
        diagnostic = base._case_gates(payload, "slip_target", body, slave_nodes, area_by_node)
        payload.update(
            {
                "artifact_id": ARTIFACT_ID,
                "execution_kind": "PROSPECTIVE_M4_SLIP_FORENSIC_R2",
                "mesh": "M4",
                "case": "slip_target",
                "contract_sha256": binding["contract_sha256"],
                "execution_binding_sha256": binding_sha,
                "source_bundle_sha256": binding["source_bundle_sha256"],
                "policy_digest_context_only": base.POLICY_DIGEST_CONTEXT,
                "diagnostic": {**diagnostic, "elapsed_seconds": perf_counter() - started},
                "formal_wp08_qualification": False,
                "points_awarded": False,
            }
        )
        _write_json(case_dir / "result.json", payload)
        return 0 if all(diagnostic["gates"].values()) else 3
    except BaseException as error:
        _write_json(
            case_dir / "failure.json",
            {
                "artifact_id": ARTIFACT_ID,
                "execution_kind": "PROSPECTIVE_M4_SLIP_FORENSIC_R2",
                "mesh": "M4",
                "case": "slip_target",
                "contract_sha256": binding["contract_sha256"],
                "execution_binding_sha256": binding_sha,
                "source_bundle_sha256": binding["source_bundle_sha256"],
                "error": _exception_record(error),
                "failed_utc": _utc(),
                "elapsed_seconds": perf_counter() - started,
            },
        )
        raise
    finally:
        telemetry.close()


def _invoke(output: Path, binding: dict[str, Any]) -> dict[str, Any]:
    logs = output / "_process_logs"
    logs.mkdir(exist_ok=True)
    stdout_path, stderr_path = logs / "M4_slip_target.stdout.log", logs / "M4_slip_target.stderr.log"
    command = [
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        "--worker",
        "--output-root",
        str(output),
        "--execution-binding-sha256",
        str(binding["execution_binding_sha256"]),
    ]
    started_utc = _utc()
    timer = perf_counter()
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        exit_code = process.wait()
    record: dict[str, Any] = {
        "artifact_id": ARTIFACT_ID,
        "mesh": "M4",
        "case": "slip_target",
        "execution_kind": "PROSPECTIVE_M4_SLIP_FORENSIC_R2",
        "pid": process.pid,
        "command": command,
        "started_utc": started_utc,
        "ended_utc": _utc(),
        "elapsed_seconds": perf_counter() - timer,
        "exit_code": exit_code,
        "contract_sha256": binding["contract_sha256"],
        "execution_binding_sha256": binding["execution_binding_sha256"],
        "source_bundle_sha256": binding["source_bundle_sha256"],
        "stdout_path": stdout_path.relative_to(output).as_posix(),
        "stdout_sha256": _sha(stdout_path),
        "stderr_path": stderr_path.relative_to(output).as_posix(),
        "stderr_sha256": _sha(stderr_path),
    }
    case_dir = output / "M4" / "slip_target"
    for filename, key in (("result.json", "result"), ("failure.json", "failure"), ("telemetry.jsonl", "telemetry")):
        path = case_dir / filename
        if path.is_file():
            record[f"{key}_path"] = path.relative_to(output).as_posix()
            record[f"{key}_sha256"] = _sha(path)
    _write_json(logs / "M4_slip_target.process.json", record)
    return record


def execute() -> int:
    output = ROOT / OUTPUT_REL
    _, binding = _verify_frozen(output)
    run_root = output / "M4"
    if run_root.exists():
        raise FileExistsError("Forensic M4 output exists; refusing any retry or overwrite.")
    run_root.mkdir(parents=True, exist_ok=False)
    _write_json(run_root / "progress.json", {"status": "RUNNING", "started_utc": _utc()}, exclusive=False)
    process = _invoke(output, binding)
    case_dir = run_root / "slip_target"
    failure_path = case_dir / "failure.json"
    result_path = case_dir / "result.json"
    if failure_path.is_file() and process["exit_code"] != 0:
        status = "DIAGNOSTIC_CAPTURED_NUMERICAL_FAILURE"
    elif result_path.is_file() and process["exit_code"] == 0:
        status = "DIAGNOSTIC_RUN_COMPLETED_REVIEW_GATES"
    else:
        status = "FAIL_CLOSED_INCOMPLETE_PROCESS_ARTIFACTS"
    final = {
        "artifact_id": ARTIFACT_ID,
        "status": status,
        "contract_sha256": binding["contract_sha256"],
        "execution_binding_sha256": binding["execution_binding_sha256"],
        "source_bundle_sha256": binding["source_bundle_sha256"],
        "source_head": binding["source_head"],
        "execution_process": process,
        "failure_path": failure_path.relative_to(output).as_posix() if failure_path.is_file() else None,
        "failure_sha256": _sha(failure_path) if failure_path.is_file() else None,
        "result_path": result_path.relative_to(output).as_posix() if result_path.is_file() else None,
        "result_sha256": _sha(result_path) if result_path.is_file() else None,
        "telemetry_path": (case_dir / "telemetry.jsonl").relative_to(output).as_posix()
        if (case_dir / "telemetry.jsonl").is_file()
        else None,
        "telemetry_sha256": _sha(case_dir / "telemetry.jsonl")
        if (case_dir / "telemetry.jsonl").is_file()
        else None,
        "m1_m2_m3_rerun": False,
        "stick_case_rerun": False,
        "reference_or_replay_run": False,
        "production_mechanics_changed": False,
        "thresholds_changed": False,
        "formal_wp08_qualification": False,
        "points_awarded": False,
    }
    _write_json(run_root / "final.json", final)
    _write_json(run_root / "progress.json", {"status": "COMPLETED", "completed_utc": _utc(), **final}, exclusive=False)
    print(json.dumps(final, indent=2, sort_keys=True))
    return 0 if status == "DIAGNOSTIC_RUN_COMPLETED_REVIEW_GATES" else 3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--output-root", type=Path, default=ROOT / OUTPUT_REL)
    parser.add_argument("--execution-binding-sha256")
    args = parser.parse_args()
    if args.freeze:
        print(json.dumps(freeze(), indent=2, sort_keys=True))
        return 0
    if args.execute:
        return execute()
    if args.worker and args.execution_binding_sha256:
        return _worker(args.output_root.resolve(), args.execution_binding_sha256)
    parser.error("Choose --freeze, --execute, or worker with output and binding SHA.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
