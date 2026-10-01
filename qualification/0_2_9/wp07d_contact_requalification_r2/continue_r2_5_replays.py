"""Resume only the two frozen WP07-D R2.3 replay checkpoints.

The primary and independent-reference campaigns are read-only inputs here.
This evidence-side continuation normalizes the analyzer's raw ``success``
status into the process-audit enum ``PASS`` only after the frozen analyzer has
recomputed and passed the case gates. No source under ``src`` or ``scripts``
is modified by this helper.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXPECTED_EXECUTION_SHA = "3c749f30f95a53b4eaadb2159accb4349e6d7ee7"
EXPECTED_ROUTES = ("ACTIVE_SET", "PENALTY")
EXPECTED_LEVELS = ("M1", "M2", "M3")


def canonical_primary_status(raw_status: Any, *, case_pass: bool, result_present: bool = True) -> str:
    """Map a raw production status to the process-audit enum, never promoting a failed case."""

    if not result_present:
        return "MISSING"
    if not case_pass or str(raw_status).strip().lower() not in {"pass", "success"}:
        return "FAIL_CLOSED"
    return "PASS"


def normalize_pre_replay_gate(
    gate: Mapping[str, Any],
    *,
    expected_replay_levels: Mapping[str, str],
    postprocessor_path: str,
    postprocessor_sha256: str,
    source_gate_path: str,
    source_gate_sha256: str,
) -> dict[str, Any]:
    """Return a copy with only status-enum normalization and its provenance recorded."""

    if (
        gate.get("status") != "PASS_REPLAY_GATES_EVALUATED"
        or gate.get("replay_run") is not False
        or gate.get("replay_authorizations_created") is not False
    ):
        raise ValueError("The source gate is not an untouched passing pre-replay gate.")
    routes = gate.get("routes")
    if not isinstance(routes, Mapping) or set(routes) != set(EXPECTED_ROUTES):
        raise ValueError("The pre-replay gate must contain exactly both frozen routes.")
    if set(expected_replay_levels) != set(EXPECTED_ROUTES):
        raise ValueError("Replay levels must be supplied for exactly both frozen routes.")

    expected_case_keys = {f"{route}/{level}" for route in EXPECTED_ROUTES for level in EXPECTED_LEVELS}
    for field in ("production_process_manifests", "reference_process_manifests"):
        records = gate.get(field)
        if not isinstance(records, Mapping) or set(records) != expected_case_keys:
            raise ValueError(f"The source gate has incomplete {field} coverage.")
    expected_order = [
        f"{route}/{level}/PRIMARY_PRODUCTION" for route in EXPECTED_ROUTES for level in EXPECTED_LEVELS
    ] + [
        f"{route}/{level}/INDEPENDENT_REFERENCE" for route in EXPECTED_ROUTES for level in EXPECTED_LEVELS
    ]
    if gate.get("sequential_process_order") != expected_order:
        raise ValueError("The source gate process order is incomplete or not sequential.")

    normalized = copy.deepcopy(dict(gate))
    changes: list[dict[str, str]] = []
    for route in EXPECTED_ROUTES:
        route_gate = normalized["routes"][route]
        if (
            route_gate.get("status") != "PASS_READY_FOR_REPLAY"
            or route_gate.get("replay_level") != expected_replay_levels[route]
            or route_gate.get("production_and_reference_cases_pass") is not True
            or route_gate.get("convergence_gates_pass") is not True
        ):
            raise ValueError(f"{route} is not fully eligible for its frozen replay checkpoint.")
        cases = route_gate.get("cases")
        if not isinstance(cases, Mapping) or set(cases) != set(EXPECTED_LEVELS):
            raise ValueError(f"{route} does not contain exactly M1/M2/M3 evidence.")
        for level in EXPECTED_LEVELS:
            case = cases[level]
            if (
                case.get("status") != "PASS"
                or case.get("problems") != []
                or case.get("production_run_status") != "COMPLETED"
                or case.get("reference_status") != "PASS"
                or case.get("reference_run_status") != "COMPLETED"
                or case.get("production_telemetry_status") not in {"HEALTHY", "PASS"}
                or case.get("reference_telemetry_status") not in {"HEALTHY", "PASS"}
            ):
                raise ValueError(f"{route}/{level} is not a complete passing production/reference case.")
            for field in (
                "production_result_sha256",
                "production_run_sha256",
                "reference_result_sha256",
                "reference_run_sha256",
            ):
                digest = case.get(field)
                if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                    raise ValueError(f"{route}/{level} has invalid hash metadata in {field}.")
            raw_status = case.get("production_status")
            canonical = canonical_primary_status(raw_status, case_pass=True)
            if canonical != "PASS":
                raise ValueError(f"{route}/{level} raw production status cannot be normalized to PASS.")
            case["production_status_raw"] = raw_status
            case["production_status"] = canonical
            if raw_status != canonical:
                changes.append({"case": f"{route}/{level}", "from": str(raw_status), "to": canonical})

    normalized["status_normalization"] = {
        "status": "PASS",
        "classification": "EVIDENCE_TOOLING_STATUS_ENUM_NORMALIZATION",
        "postprocessor_path": postprocessor_path,
        "postprocessor_sha256": postprocessor_sha256,
        "source_gate_path": source_gate_path,
        "source_gate_sha256": source_gate_sha256,
        "rule": (
            "Normalize raw production status success/pass to PASS only when the frozen analyzer case is PASS, "
            "the production run is COMPLETED, the reference is PASS, and the convergence route gate is PASS."
        ),
        "normalized_cases": changes,
        "raw_result_files_modified": False,
        "solver_source_or_parameters_modified": False,
        "thresholds_modified": False,
    }
    return normalized


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _write_json(path: Path, value: object, *, overwrite: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if overwrite else "x"
    rendered = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with path.open(mode, encoding="utf-8", newline="\n") as stream:
        stream.write(rendered)
        stream.flush()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _assert_no_live_campaign_process() -> None:
    command = (
        "$matches = Get-CimInstance Win32_Process -Filter \"Name='python.exe' or Name='pythonw.exe'\" "
        "| Where-Object { $_.CommandLine -match 'run_wp07d_contact_requalification_r2\\.py|"
        "run_wp07d_structural\\.py|wp07d_independent_reference\\.py' }; "
        "if ($matches) { $matches | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress }"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("Could not verify that all WP07-D campaign processes have exited.")
    if result.stdout.strip():
        raise PermissionError(f"A WP07-D campaign process is still active: {result.stdout.strip()}")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _records_from_gate(root: Path, manifests: Mapping[str, Any], kind: str) -> dict[str, Any]:
    records: dict[str, Any] = {}
    for route in EXPECTED_ROUTES:
        for level in EXPECTED_LEVELS:
            key = f"{route}/{level}"
            metadata = manifests[key]
            path = (root / str(metadata["path"])).resolve()
            if not path.is_relative_to(root.resolve()) or _sha256_file(path) != metadata.get("sha256"):
                raise PermissionError(f"Process manifest hash mismatch for {key}/{kind}.")
            records[f"{key}/{kind}"] = _read_json(path)
    return records


def resume_replays(execution_sha: str, binding_path: Path) -> dict[str, Any]:
    from scripts import analyze_wp07d_formal_rebind_r1 as analysis
    from scripts.run_wp07d_contact_requalification_r2 import (
        _authorization,
        _invoke,
        _validate_frozen_source,
    )
    from scripts.wp07d_execution_binding import (
        EXPECTED_LEVELS as BINDING_LEVELS,
        EXPECTED_ROUTES as BINDING_ROUTES,
        _validate_contact_r2_process_evidence,
        contact_requalification_profile,
        load_binding,
        validate_binding,
    )

    if execution_sha != EXPECTED_EXECUTION_SHA or BINDING_LEVELS != EXPECTED_LEVELS or BINDING_ROUTES != EXPECTED_ROUTES:
        raise PermissionError("Recovery request differs from the frozen WP07-D R2.5 campaign identity.")
    _assert_no_live_campaign_process()
    binding_path = binding_path.resolve()
    binding, _identity = _validate_frozen_source(execution_sha, binding_path)
    validate_binding(binding)
    loaded_binding = load_binding(binding_path)
    if _canonical_json(binding) != _canonical_json(loaded_binding):
        raise PermissionError("Frozen binding changed during recovery preflight.")

    profile = contact_requalification_profile(str(binding["artifact_id"]))
    artifact_root = Path(profile["artifact_root"])
    run_root = Path(profile["run_root"])
    auth_root = Path(profile["authorization_root"])
    gate_path = Path(profile["replay_gate_path"]).resolve()
    final_path = Path(profile["final_report"]).resolve()
    progress_path = Path(profile["progress"]).resolve()
    if not gate_path.is_file() or final_path.exists():
        raise FileNotFoundError("Expected the failed pre-replay gate and no final report.")
    for route in EXPECTED_ROUTES:
        mesh = str(binding["routes"][route]["replay_level"])
        if (ROOT / run_root / route / mesh / "replay").exists():
            raise FileExistsError(f"Refusing to overwrite existing replay output for {route}/{mesh}.")
        if (ROOT / auth_root / "REPLAY" / f"{route}_{mesh}.json").exists():
            raise FileExistsError(f"Refusing to overwrite existing replay authorization for {route}/{mesh}.")

    recovery_path = artifact_root / "replay_gate_normalization_r2_5.json"
    backup_gate_path = artifact_root / "replay_authorization_gate_r2_5_pre_normalization.json"
    candidate_gate_path = artifact_root / "replay_authorization_gate_r2_5_normalized_candidate.json"
    backup_progress_path = artifact_root / "progress_r2_5_before_resume.json"
    if any(path.exists() for path in (recovery_path, backup_gate_path, candidate_gate_path, backup_progress_path)):
        raise FileExistsError("A WP07-D R2.5 recovery artifact already exists; refusing to overwrite it.")

    previous_gate_bytes = gate_path.read_bytes()
    previous_gate_sha = _sha256_bytes(previous_gate_bytes)
    previous_gate = json.loads(previous_gate_bytes)
    if not isinstance(previous_gate, dict):
        raise ValueError("Prior replay gate is not a JSON object.")
    fresh_gate = analysis.build_pre_replay_report(binding_path)
    if _canonical_json(previous_gate.get("routes")) != _canonical_json(fresh_gate.get("routes")):
        raise PermissionError("Recomputed frozen gates differ from the preserved pre-replay gate.")
    for field in (
        "artifact_id",
        "execution_sha",
        "binding_path",
        "binding_file_sha256",
        "requalification_contract_sha256",
        "policy_digest",
        "formal_contract_provenance",
        "owner_decision",
    ):
        if previous_gate.get(field) != fresh_gate.get(field):
            raise PermissionError(f"Pre-replay gate provenance changed in {field}.")
    for field in ("run_root", "authorization_root", "production_process_manifests", "reference_process_manifests", "sequential_process_order"):
        if field not in previous_gate:
            raise PermissionError(f"Original gate lacks {field}.")
        fresh_gate[field] = previous_gate[field]

    tool_path = Path(__file__).resolve()
    tool_sha = _sha256_file(tool_path)
    gate = normalize_pre_replay_gate(
        fresh_gate,
        expected_replay_levels={route: str(binding["routes"][route]["replay_level"]) for route in EXPECTED_ROUTES},
        postprocessor_path=tool_path.relative_to(ROOT).as_posix(),
        postprocessor_sha256=tool_sha,
        source_gate_path=gate_path.relative_to(ROOT).as_posix(),
        source_gate_sha256=previous_gate_sha,
    )
    if gate.get("execution_sha") != execution_sha:
        raise PermissionError("Rebuilt replay gate is not bound to the frozen execution SHA.")

    # Preserve the failed gate byte-for-byte, then install the separately
    # annotated candidate at the path hard-bound by the existing authorization.
    with backup_gate_path.open("xb") as stream:
        stream.write(previous_gate_bytes)
        stream.flush()
    if _sha256_file(backup_gate_path) != previous_gate_sha:
        raise IOError("Preserved original gate hash does not match its source hash.")
    _write_json(candidate_gate_path, gate)
    candidate_sha = _sha256_file(candidate_gate_path)
    os.replace(candidate_gate_path, gate_path)
    gate_sha = _sha256_file(gate_path)
    if gate_sha != candidate_sha:
        raise IOError("Installed normalized gate hash differs from the staged candidate.")

    previous_progress_bytes = progress_path.read_bytes() if progress_path.is_file() else b""
    if previous_progress_bytes:
        with backup_progress_path.open("xb") as stream:
            stream.write(previous_progress_bytes)
            stream.flush()
    progress_state: dict[str, Any] = {
        "status": "RUNNING",
        "phase": "PRE_REPLAY_GATE_REVALIDATED",
        "updated_utc": _utc_now(),
        "case_statuses": {
            f"{route}/{level}/{kind}": "PASS"
            for route in EXPECTED_ROUTES
            for level in EXPECTED_LEVELS
            for kind in ("PRIMARY_PRODUCTION", "INDEPENDENT_REFERENCE")
        },
    }
    _write_json(progress_path, progress_state, overwrite=True)

    recovery: dict[str, Any] = {
        "schema_version": 1,
        "artifact_id": "QF-029-WP07-D-CONTACT-R2-5-STATUS-NORMALIZATION-AND-REPLAY-RESUME-001",
        "status": "NORMALIZED_GATE_PENDING_VALIDATION",
        "execution_sha": execution_sha,
        "binding_path": binding_path.relative_to(ROOT).as_posix(),
        "binding_sha256": _sha256_file(binding_path),
        "source_gate_original_path": gate_path.relative_to(ROOT).as_posix(),
        "source_gate_preserved_path": backup_gate_path.relative_to(ROOT).as_posix(),
        "source_gate_sha256": previous_gate_sha,
        "normalized_gate_path": gate_path.relative_to(ROOT).as_posix(),
        "normalized_gate_sha256": gate_sha,
        "postprocessor_path": tool_path.relative_to(ROOT).as_posix(),
        "postprocessor_sha256": tool_sha,
        "source_analysis_script_sha256": gate.get("analysis_script_sha256"),
        "normalized_cases": gate["status_normalization"]["normalized_cases"],
        "recomputed_routes_identical_to_original": True,
        "primary_or_reference_rerun": False,
        "thresholds_changed": False,
        "solver_source_changed": False,
        "formal_points_awarded": 0,
    }
    _write_json(recovery_path, recovery)

    _validate_contact_r2_process_evidence(gate, root=ROOT, run_root=run_root)
    binding_sha = _sha256_file(binding_path)
    gate_relative = gate_path.relative_to(ROOT)
    authorizations: dict[str, tuple[Path, dict[str, Any]]] = {}
    for route in EXPECTED_ROUTES:
        mesh = str(binding["routes"][route]["replay_level"])
        authorization = _authorization(
            binding,
            binding_sha=binding_sha,
            execution_sha=execution_sha,
            route=route,
            mesh=mesh,
            kind="REPLAY",
            binding_path=binding_path,
            replay_gate_path=gate_relative,
            gate_sha=gate_sha,
        )
        auth_path = ROOT / auth_root / "REPLAY" / f"{route}_{mesh}.json"
        authorizations[route] = (auth_path, authorization)
    for auth_path, authorization in authorizations.values():
        _write_json(auth_path, authorization)

    original_process_maps = {
        "production": gate["production_process_manifests"],
        "reference": gate["reference_process_manifests"],
    }
    primary_processes = _records_from_gate(ROOT, original_process_maps["production"], "PRIMARY_PRODUCTION")
    reference_processes = _records_from_gate(ROOT, original_process_maps["reference"], "INDEPENDENT_REFERENCE")
    replay_processes: dict[str, Any] = {}
    for route in EXPECTED_ROUTES:
        mesh = str(binding["routes"][route]["replay_level"])
        auth_path, _authorization_record = authorizations[route]
        output = ROOT / run_root / route / mesh / "replay"
        command = [
            sys.executable,
            str(ROOT / "scripts/run_wp07d_structural.py"),
            "--route",
            route,
            "--mesh",
            mesh,
            "--authorization",
            str(auth_path),
            "--binding",
            str(binding_path),
            "--output",
            str(output),
            "--execution-kind",
            "REPLAY",
        ]
        case_id = f"{route}/{mesh}/REPLAY"
        process = _invoke(
            case_id,
            command,
            output,
            execution_sha=execution_sha,
            route=route,
            mesh=mesh,
            kind="REPLAY",
        )
        replay_processes[case_id] = process
        progress_state["phase"] = case_id
        progress_state["updated_utc"] = _utc_now()
        progress_state["case_statuses"][case_id] = (
            "PASS" if process.get("exit_code") == 0 and (output / "result.json").is_file() else "FAIL_CLOSED_PROCESS_EXIT"
        )
        _write_json(progress_path, progress_state, overwrite=True)

    final = analysis.build_final_report(binding_path)
    for route in EXPECTED_ROUTES:
        cases = final["routes"][route]["cases"]
        for level in EXPECTED_LEVELS:
            case = cases[level]
            raw = case.get("production_status")
            case["production_status_raw"] = raw
            case["production_status"] = canonical_primary_status(raw, case_pass=case.get("status") == "PASS")
    final["primary_processes"] = primary_processes
    final["reference_processes"] = reference_processes
    final["replay_processes"] = replay_processes
    final["pre_replay_gate_path"] = gate_path.relative_to(ROOT).as_posix()
    final["pre_replay_gate_sha256"] = gate_sha
    final["superseded_pre_replay_gate"] = {
        "path": backup_gate_path.relative_to(ROOT).as_posix(),
        "sha256": previous_gate_sha,
        "classification": "FAIL_CLOSED_STATUS_ENUM_MISMATCH_PRESERVED",
    }
    final["status_normalization_record_path"] = recovery_path.relative_to(ROOT).as_posix()
    final["primary_and_reference_rerun"] = False
    final["production_mechanics_changed_by_requalification"] = True
    final["thresholds_changed"] = False
    final["wp07e_run"] = False
    final["score_awarded"] = False
    final["ledger_updated"] = False
    final["push_or_merge_performed"] = False

    penalty_m1_path = ROOT / run_root / "PENALTY" / "M1" / "primary" / "result.json"
    penalty_m1 = _read_json(penalty_m1_path)
    final["run_verdict_observations"] = [
        {
            "case": "PENALTY/M1",
            "raw_run_verdict": penalty_m1.get("run_verdict"),
            "solver_converged": penalty_m1.get("solver", {}).get("converged"),
            "final_relative_residual": penalty_m1.get("solver", {}).get("final_relative_residual"),
            "maturity": penalty_m1.get("solver", {}).get("maturity"),
            "interpretation": "Preserved as a qualification warning; not rewritten or used to weaken a frozen numerical gate.",
        }
    ]
    if final_path.exists():
        raise FileExistsError(f"Refusing to overwrite final report: {final_path}")
    _write_json(final_path, final)

    progress_state["status"] = final.get("status")
    progress_state["phase"] = "RUN_END"
    progress_state["updated_utc"] = _utc_now()
    _write_json(progress_path, progress_state, overwrite=True)
    recovery.update(
        {
            "status": final.get("status"),
            "replay_processes": replay_processes,
            "final_report_path": final_path.relative_to(ROOT).as_posix(),
            "final_report_sha256": _sha256_file(final_path),
            "completed_utc": _utc_now(),
        }
    )
    _write_json(recovery_path, recovery, overwrite=True)
    return final


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-sha", required=True)
    parser.add_argument(
        "--binding",
        type=Path,
        default=ROOT / "qualification/0_2_9/wp07d_contact_requalification_r2/execution_binding_r2_3.json",
    )
    args = parser.parse_args(argv)
    try:
        report = resume_replays(args.execution_sha, args.binding)
    except Exception as error:
        print(f"WP07D_CONTACT_R2_REPLAY_RESUME_FAIL_CLOSED: {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"status": report.get("status"), "execution_sha": args.execution_sha}, sort_keys=True))
    return 0 if report.get("status") == "READY_FOR_OWNER_REVIEW" else 3


if __name__ == "__main__":
    raise SystemExit(main())
