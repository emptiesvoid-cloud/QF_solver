"""Read-only preflight and one-node local V&V execution workflow."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .manifest import (
    LocalVVError,
    _checkout_path,
    _execution_environment,
    inspect_checkout,
    load_json,
    probe_import_origin,
    sha256_bytes,
    sha256_file,
    validate_manifest_shape,
    validate_owner_decision,
    verify_environment,
    verify_file_inventory,
    verify_runner_entrypoint,
)
from .process import (
    _case_command,
    _check_evidence_root,
    _read_selection,
    _write_hash_inventory,
    _write_new_json,
    classify_junit,
    extract_numeric_payload,
    supervise_process,
)
from .manifest import COMMAND_PROFILE_V2
from .results import classify_v2_result


def _preflight(manifest: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    runner_entrypoint = verify_runner_entrypoint(manifest)
    identities = {key: inspect_checkout(value) for key, value in manifest["identities"].items()}
    files = verify_file_inventory(manifest, case)
    environment = verify_environment(manifest)
    probe_environment = _execution_environment(manifest)
    source = probe_import_origin(manifest, probe_environment)
    return {
        "runner_entrypoint": runner_entrypoint,
        "identities": identities,
        "files": files,
        "environment": environment,
        "import_origin": source,
    }


def run_case(
    manifest: dict[str, Any],
    manifest_raw: bytes,
    decision: dict[str, Any],
    case: dict[str, Any],
    decision_raw: bytes | None = None,
) -> dict[str, Any]:
    manifest_sha = sha256_bytes(manifest_raw)
    decision_errors = validate_owner_decision(manifest, case, decision, manifest_sha)
    if decision_errors:
        raise LocalVVError("DENY_EXECUTION: " + "; ".join(decision_errors))
    shape_errors = validate_manifest_shape(manifest)
    if shape_errors:
        raise LocalVVError("DENY_EXECUTION: " + "; ".join(shape_errors))
    evidence_root = _check_evidence_root(manifest)
    preflight = _preflight(manifest, case)
    campaign_root = evidence_root / manifest["campaign_id"]
    attempts_root = campaign_root / "_attempts"
    attempts_root.mkdir(parents=True, exist_ok=True)
    attempt_record = attempts_root / f"{case['case_id']}.json"
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]
    case_root = campaign_root / case["case_id"]
    case_root.mkdir(parents=True, exist_ok=True)
    run_dir = case_root / run_id
    run_dir.mkdir(exist_ok=False)
    temporary = run_dir / "tmp"
    temporary.mkdir(exist_ok=False)
    try:
        _write_new_json(
            attempt_record,
            {
                "schema": "qf-local-vv-attempt-reservation-v1",
                "campaign_id": manifest["campaign_id"],
                "manifest_sha256": manifest_sha,
                "case_id": case["case_id"],
                "nodeid": case["nodeid"],
                "run_id": run_id,
                "attempt_number": 1,
                "status": "RESERVED",
                "reserved_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            },
        )
    except FileExistsError as exc:
        raise LocalVVError(
            f"DENY_EXECUTION: the one permitted attempt is already reserved for {case['case_id']}"
        ) from exc
    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"
    junit_path = run_dir / "junit.xml"
    argv, cwd, environment = _case_command(manifest, case, run_dir)
    process_result: dict[str, Any]
    started_at_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        process_result = supervise_process(
            argv,
            cwd=cwd,
            environment=environment,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            timeout_seconds=case["timeout_seconds"],
            output_limit_bytes=case["output_limit_bytes"],
        )
    except KeyboardInterrupt:
        process_result = {"exit_code": None, "timed_out": False, "output_limited": False, "interrupted": True}
    except (OSError, LocalVVError) as exc:
        process_result = {"exit_code": None, "timed_out": False, "output_limited": False, "interrupted": False}
        (run_dir / "infrastructure_error.txt").write_text(str(exc), encoding="utf-8")
    selected = _read_selection(run_dir / "selection.json")
    selected_nodeids = selected.get("collected_nodeids") if selected is not None else None
    expected_import = str((_checkout_path(manifest, "science") / "src" / "solveur" / "__init__.py").resolve())
    status = classify_junit(
        junit_path,
        case["nodeid"],
        selected_nodeids,
        process_result.get("exit_code"),
        timed_out=bool(process_result.get("timed_out") or process_result.get("output_limited")),
        interrupted=bool(process_result.get("interrupted")),
    )
    if selected is not None and selected.get("source_import") != expected_import:
        status = "INFRA_ERROR"
    if process_result.get("output_limited"):
        status = "RESOURCE_LIMIT"
    if not (status == "TIMEOUT" or status == "INTERRUPTED"):
        try:
            postflight = {key: inspect_checkout(value) for key, value in manifest["identities"].items()}
            post_files = verify_file_inventory(manifest, case)
        except LocalVVError:
            postflight = {}
            post_files = []
            status = "INFRA_ERROR"
    else:
        postflight = {}
        post_files = []
    scientific_result: dict[str, Any] | None = None
    try:
        numeric_status, numeric_payload = (
            extract_numeric_payload(stdout_path, strict=case.get("command_profile") == COMMAND_PROFILE_V2)
            if stdout_path.exists()
            else ("NOT_EXPOSED", None)
        )
        expected_payload_schema = case.get("numeric_payload_schema")
        if case.get("command_profile") == COMMAND_PROFILE_V2:
            pytest_status = "PASS" if status == "PYTEST_PASS_ONLY" else "FAIL" if status == "FAIL" else "INCOMPLETE"
            if numeric_payload is not None and numeric_payload.get("schema") != expected_payload_schema:
                numeric_status = "MALFORMED"
            scientific_result = classify_v2_result(
                numeric_status,
                numeric_payload,
                case_id=case["case_id"],
                pytest_execution_status=pytest_status,
            )
            scientific_result["pytest_execution_status"] = pytest_status
            numeric_error = scientific_result["error"]
        elif expected_payload_schema is not None:
            if numeric_payload is None:
                numeric_error = "required numeric result marker is missing"
                if status == "PYTEST_PASS_ONLY":
                    status = "INFRA_ERROR"
            elif numeric_payload.get("schema") != expected_payload_schema:
                raise LocalVVError("numeric result marker schema does not match the prepared case")
        else:
            numeric_error = None
        if (
            case.get("command_profile") != COMMAND_PROFILE_V2
            and numeric_payload is not None
            and numeric_payload.get("case_id") != case["case_id"]
        ):
            raise LocalVVError("numeric result marker case_id does not match the approved case")
        if case.get("command_profile") != COMMAND_PROFILE_V2 and numeric_payload is not None:
            numeric_error = None
    except (OSError, ValueError, json.JSONDecodeError, LocalVVError) as exc:
        numeric_status, numeric_payload, numeric_error = "MALFORMED", None, str(exc)
        if case.get("command_profile") == COMMAND_PROFILE_V2:
            scientific_result = classify_v2_result(
                "MALFORMED",
                None,
                case_id=case["case_id"],
                pytest_execution_status="PASS"
                if status == "PYTEST_PASS_ONLY"
                else "FAIL"
                if status == "FAIL"
                else "INCOMPLETE",
            )
            scientific_result["pytest_execution_status"] = (
                "PASS" if status == "PYTEST_PASS_ONLY" else "FAIL" if status == "FAIL" else "INCOMPLETE"
            )
            numeric_error = scientific_result["error"]
        elif status == "PYTEST_PASS_ONLY":
            status = "INFRA_ERROR"
    output_hashes = _write_hash_inventory(run_dir)
    receipt = {
        "schema": "qf-local-vv-run-receipt-v1",
        "campaign_id": manifest["campaign_id"],
        "manifest_sha256": manifest_sha,
        "owner_decision_sha256": sha256_bytes(
            decision_raw
            if decision_raw is not None
            else json.dumps(decision, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ),
        "case_id": case["case_id"],
        "nodeid": case["nodeid"],
        "run_id": run_id,
        "attempt_number": 1,
        "status": status,
        "interpretation": "PYTEST_PASS_ONLY is not an oracle verdict or qualification decision",
        "started_at_utc": started_at_utc,
        "process": process_result,
        "command_argv": argv,
        "working_directory": str(cwd),
        "identities_before": preflight["identities"],
        "identities_after": postflight,
        "source_import": preflight["import_origin"],
        "environment": preflight["environment"],
        "file_inventory_before": preflight["files"],
        "file_inventory_after": post_files,
        "selected_nodeids": selected_nodeids,
        "selection_record": selected,
        "numeric_observables": {"status": numeric_status, "payload": numeric_payload, "error": numeric_error},
        **({"scientific_result": scientific_result} if scientific_result is not None else {}),
        **(
            {
                "pytest_execution_status": scientific_result["pytest_execution_status"],
                "overall_scientific_status": scientific_result["status"],
            }
            if scientific_result is not None
            else {}
        ),
        "output_hashes": output_hashes,
        "limitations": [
            "Local process monitoring is not a filesystem sandbox.",
            "This runner does not attest cryptographic authorship or provide hard CPU/RAM/process-tree isolation.",
            "A pytest pass is not a scientific oracle verdict or work-package qualification.",
        ],
    }
    receipt_path = run_dir / "receipt.json"
    _write_new_json(receipt_path, receipt)
    receipt_hash = sha256_file(receipt_path)
    _write_new_json(run_dir / "receipt.sha256.json", {"sha256": receipt_hash, "path": "receipt.json"})
    attempt_result = {
        "case_id": case["case_id"],
        "run_id": run_id,
        "status": status,
        "receipt_sha256": receipt_hash,
    }
    if scientific_result is not None:
        attempt_result.update(
            {
                "pytest_execution_status": scientific_result["pytest_execution_status"],
                "gamma_scientific_status": scientific_result["gamma_scientific_status"],
                "overall_scientific_status": scientific_result["status"],
            }
        )
    _write_new_json(attempts_root / f"{case['case_id']}-result-{run_id}.json", attempt_result)
    result = {"status": status, "run_id": run_id, "receipt": str(receipt_path), "receipt_sha256": receipt_hash}
    if scientific_result is not None:
        result["pytest_execution_status"] = scientific_result["pytest_execution_status"]
        result["overall_scientific_status"] = scientific_result["status"]
    return result


def validate_manifest_file(path: Path) -> tuple[dict[str, Any], bytes, list[str]]:
    manifest, raw = load_json(path)
    errors = validate_manifest_shape(manifest)
    return manifest, raw, errors


def validate_all_cases(manifest: dict[str, Any]) -> dict[str, Any]:
    _check_evidence_root(manifest)
    runner_entrypoint = verify_runner_entrypoint(manifest)
    identities = {key: inspect_checkout(value) for key, value in manifest["identities"].items()}
    file_inventory: dict[str, list[dict[str, str]]] = {}
    for case in manifest["cases"]:
        file_inventory[case["case_id"]] = verify_file_inventory(manifest, case)
    environment = verify_environment(manifest)
    import_origin = probe_import_origin(manifest, _execution_environment(manifest))
    return {
        "identities": identities,
        "runner_entrypoint": runner_entrypoint,
        "file_inventory": file_inventory,
        "environment": environment,
        "source_import": import_origin,
    }
