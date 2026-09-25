"""Sequential source-bound WP07-D contact-mechanics requalification R2.

This orchestration performs only the exact frozen WP07-D primary, independent
reference, and contract-required replay cases. It never runs WP07-E or awards
points. Each solver/reference invocation is a separate sequential process.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.wp07d_execution_binding import (  # noqa: E402
    CONTACT_REQUAL_R2_BINDING_PATH,
    CONTACT_REQUAL_R2_AUTH_ROOT,
    CONTACT_REQUAL_R2_OWNER_DECISION_PATH,
    CONTACT_REQUAL_R2_RUN_ROOT,
    CONTACT_REQUAL_R2_REPLAY_GATE_PATH,
    CONTACT_REQUAL_R2_TOKEN,
    EXPECTED_LEVELS,
    EXPECTED_ROUTES,
    _file_sha256,
    coordinate_grading_from_authorization,
    formal_contract_identity,
    load_binding,
    mesh_axis_fractions_from_authorization,
    mesh_cell_counts_from_authorization,
    penalty_integration_from_authorization,
    validate_authorized_execution_source,
    validate_binding,
    validate_formal_requalification_authorization,
)

ARTIFACT_ROOT = Path("qualification/0_2_9/wp07d_contact_requalification_r2")
RUN_ROOT = CONTACT_REQUAL_R2_RUN_ROOT
AUTH_ROOT = CONTACT_REQUAL_R2_AUTH_ROOT
REPLAY_GATE = CONTACT_REQUAL_R2_REPLAY_GATE_PATH.relative_to(ROOT)
FINAL_REPORT = ARTIFACT_ROOT / "analysis_final_r2_2.json"
PROGRESS = ARTIFACT_ROOT / "progress_r2_2.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _write_json(path: Path, value: object, *, overwrite: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if overwrite else "x"
    rendered = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with path.open(mode, encoding="utf-8", newline="\n") as stream:
        stream.write(rendered)
        stream.flush()


def _validate_frozen_source(execution_sha: str) -> tuple[dict[str, Any], dict[str, Any]]:
    binding = load_binding(CONTACT_REQUAL_R2_BINDING_PATH)
    validate_binding(binding)
    identity = formal_contract_identity(binding)
    if identity is None:
        raise PermissionError("WP07-D contact R2 formal contract identity is unavailable.")
    decision = _read(CONTACT_REQUAL_R2_OWNER_DECISION_PATH)
    if _git("branch", "--show-current") != "codex/contact-active-set-remediation":
        raise PermissionError("WP07-D contact R2 execution is on the wrong branch.")
    if _git("rev-parse", "HEAD") != execution_sha:
        raise PermissionError("WP07-D contact R2 exact execution SHA changed.")
    validate_authorized_execution_source({"execution_sha": execution_sha})
    decision_data = decision.get("decisions", {})
    if (
        decision_data.get("OWNER_AUTHORIZES_WP07D_M1_M2_M3_REQUALIFICATION") is not True
        or decision_data.get("OWNER_AUTHORIZES_WP07D_INDEPENDENT_REFERENCES") is not True
        or decision_data.get("OWNER_AUTHORIZES_WP07D_CONTRACT_REQUIRED_REPLAYS") is not True
        or decision_data.get("OWNER_AUTHORIZES_WP07E_OR_WP08E") is not False
        or decision_data.get("OWNER_AWARDS_POINTS") is not False
    ):
        raise PermissionError("The bound Owner decision does not authorize exactly the R2 campaign.")
    return binding, identity


def _authorization(
    binding: dict[str, Any],
    *,
    binding_sha: str,
    execution_sha: str,
    route: str,
    mesh: str,
    kind: str,
    gate_sha: str | None = None,
) -> dict[str, Any]:
    identity = formal_contract_identity(binding)
    if identity is None:
        raise ValueError("The frozen parent WP07-D contract is unavailable.")
    production = kind in {"PRIMARY_PRODUCTION", "REPLAY"}
    record: dict[str, Any] = {
        "schema_version": 1,
        "artifact_id": f"QF-029-WP07-D-CONTACT-R2-AUTH-{kind}-{route}-{mesh}",
        "status": "OWNER_AUTHORIZED_FROZEN_CASE",
        "token": CONTACT_REQUAL_R2_TOKEN,
        "authorization_basis": "OWNER_EXPLICIT_M1_M2_M3_WP07_WP08_REQUALIFICATION_REQUEST",
        "authorized_base_sha": binding["governing"]["authorized_base_sha"],
        "execution_sha": execution_sha,
        "binding_path": CONTACT_REQUAL_R2_BINDING_PATH.relative_to(ROOT).as_posix(),
        "binding_file_sha256": binding_sha,
        "formal_contract_file_sha256": identity["file_sha256"],
        "source_requalification_contract_file_sha256": binding["source_requalification"]["sha256"],
        "owner_decision_path": binding["owner_decision"]["path"],
        "owner_decision_file_sha256": binding["owner_decision"]["file_sha256"],
        "policy_digest": binding["governing"]["policy_digest"],
        "route": route,
        "mesh": mesh,
        "execution_kind": kind,
        "structural_solves_allowed": production,
        "independent_references_allowed": kind == "INDEPENDENT_REFERENCE",
        "replay_allowed": kind == "REPLAY",
        "wp07e_allowed": False,
        "coordinate_grading_exponent": float(binding["mesh_definition"]["coordinate_grading_exponent"]),
        "mesh_cell_counts": list(binding["mesh_definition"]["cell_counts_by_level"][mesh]),
        "mesh_axis_fractions": binding["mesh_definition"].get("axis_fractions_by_level", {}).get(mesh),
    }
    if route == "PENALTY":
        record["penalty_integration"] = binding["routes"][route]["penalty_integration"]
    if kind == "REPLAY":
        if gate_sha is None:
            raise ValueError("Replay authorization requires a completed raw-evidence gate.")
        record["replay_gate_path"] = REPLAY_GATE.as_posix()
        record["replay_gate_file_sha256"] = gate_sha
    validate_formal_requalification_authorization(
        record,
        binding,
        CONTACT_REQUAL_R2_BINDING_PATH,
        route=route,
        mesh=mesh,
        execution_kind=kind,
    )
    penalty_integration_from_authorization(binding, record, route=route)
    coordinate_grading_from_authorization(binding, record)
    mesh_cell_counts_from_authorization(binding, record, level=mesh)
    mesh_axis_fractions_from_authorization(binding, record, level=mesh)
    return record


def _invoke(label: str, command: list[str], output: Path, *, execution_sha: str, route: str, mesh: str, kind: str) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    stdout_path = output / "runner.stdout.log"
    stderr_path = output / "runner.stderr.log"
    if stdout_path.exists() or stderr_path.exists():
        raise FileExistsError(f"Refusing to overwrite prior runner logs for {label}.")
    started = _utc_now()
    process: subprocess.Popen[str] | None = None
    exit_code: int | None = None
    invocation_error: str | None = None
    with stdout_path.open("x", encoding="utf-8", newline="") as stdout, stderr_path.open(
        "x", encoding="utf-8", newline=""
    ) as stderr:
        try:
            process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr, text=True)
            exit_code = process.wait()
        except Exception as error:  # preserve orchestration failure separately from solver outcome
            invocation_error = f"{type(error).__name__}: {error}"
            if process is not None:
                exit_code = process.poll()
    record = {
        "schema_version": 1,
        "case": label,
        "route": route,
        "mesh": mesh,
        "execution_kind": kind,
        "execution_sha": execution_sha,
        "command": command,
        "started_utc": started,
        "ended_utc": _utc_now(),
        "pid": process.pid if process is not None else None,
        "exit_code": exit_code,
        "invocation_error": invocation_error,
        "stdout_sha256": _file_sha256(stdout_path),
        "stderr_sha256": _file_sha256(stderr_path),
    }
    _write_json(output / "runner_process.json", record)
    return record


def _progress(phase: str, statuses: Mapping[str, Any]) -> None:
    _write_json(
        ROOT / PROGRESS,
        {"status": "RUNNING", "phase": phase, "updated_utc": _utc_now(), "case_statuses": dict(statuses)},
        overwrite=True,
    )


def _case_status(path: Path, route: str, kind: str) -> str:
    result = _read(path)
    if kind == "INDEPENDENT_REFERENCE":
        return "PASS" if result.get("status") == "PASS" else str(result.get("terminal_classification", "FAIL_CLOSED"))
    if route == "ACTIVE_SET":
        return "PASS" if result.get("status") == "PASS" else str(result.get("status", "FAIL_CLOSED"))
    return "PASS" if str(result.get("status", "")).lower() in {"pass", "success"} else str(result.get("status", "FAIL_CLOSED"))


def run_campaign(execution_sha: str) -> dict[str, Any]:
    reserved_outputs = (
        ROOT / RUN_ROOT,
        ROOT / AUTH_ROOT,
        ROOT / REPLAY_GATE,
        ROOT / FINAL_REPORT,
        ROOT / PROGRESS,
    )
    existing = [path.as_posix() for path in reserved_outputs if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to mix with or overwrite prior WP07-D R2 evidence: {existing}")
    if _git("status", "--porcelain"):
        raise PermissionError("WP07-D R2 campaign requires a clean worktree before its first child process.")
    binding, identity = _validate_frozen_source(execution_sha)
    binding_sha = _file_sha256(CONTACT_REQUAL_R2_BINDING_PATH)
    statuses: dict[str, Any] = {}
    primary_processes: dict[str, Any] = {}
    reference_processes: dict[str, Any] = {}
    replay_processes: dict[str, Any] = {}

    # All primary solves are completed before any reference or replay, one process at a time.
    for route in EXPECTED_ROUTES:
        for mesh in EXPECTED_LEVELS:
            case_id = f"{route}/{mesh}/PRIMARY_PRODUCTION"
            output = ROOT / RUN_ROOT / route / mesh / "primary"
            authorization = _authorization(
                binding,
                binding_sha=binding_sha,
                execution_sha=execution_sha,
                route=route,
                mesh=mesh,
                kind="PRIMARY_PRODUCTION",
            )
            auth_path = ROOT / AUTH_ROOT / "PRIMARY_PRODUCTION" / f"{route}_{mesh}.json"
            auth_path.parent.mkdir(parents=True, exist_ok=True)
            if auth_path.exists():
                raise FileExistsError(f"Refusing to overwrite prior authorization {auth_path}.")
            _write_json(auth_path, authorization)
            command = [
                sys.executable,
                str(ROOT / "scripts/run_wp07d_structural.py"),
                "--route", route,
                "--mesh", mesh,
                "--authorization", str(auth_path),
                "--binding", str(CONTACT_REQUAL_R2_BINDING_PATH),
                "--output", str(output),
                "--execution-kind", "PRIMARY_PRODUCTION",
            ]
            process = _invoke(case_id, command, output, execution_sha=execution_sha, route=route, mesh=mesh, kind="PRIMARY_PRODUCTION")
            primary_processes[case_id] = process
            result_path = output / "result.json"
            statuses[case_id] = (
                _case_status(result_path, route, "PRIMARY_PRODUCTION")
                if result_path.is_file() and process["exit_code"] == 0
                else "FAIL_CLOSED_PROCESS_EXIT"
            )
            if process["exit_code"] != 0 and not (output / "failure.json").is_file():
                statuses[case_id] = "FAIL_CLOSED_NO_RESULT"
            _progress(case_id, statuses)

    for route in EXPECTED_ROUTES:
        for mesh in EXPECTED_LEVELS:
            primary_id = f"{route}/{mesh}/PRIMARY_PRODUCTION"
            case_id = f"{route}/{mesh}/INDEPENDENT_REFERENCE"
            if statuses.get(primary_id) != "PASS":
                statuses[case_id] = "NOT_RUN_PRIMARY_NOT_PASS"
                _progress(case_id, statuses)
                continue
            output = ROOT / RUN_ROOT / route / mesh / "reference"
            authorization = _authorization(
                binding,
                binding_sha=binding_sha,
                execution_sha=execution_sha,
                route=route,
                mesh=mesh,
                kind="INDEPENDENT_REFERENCE",
            )
            auth_path = ROOT / AUTH_ROOT / "INDEPENDENT_REFERENCE" / f"{route}_{mesh}.json"
            auth_path.parent.mkdir(parents=True, exist_ok=True)
            if auth_path.exists():
                raise FileExistsError(f"Refusing to overwrite prior authorization {auth_path}.")
            _write_json(auth_path, authorization)
            command = [
                sys.executable,
                str(ROOT / "scripts/wp07d_independent_reference.py"),
                "--route", route,
                "--mesh", mesh,
                "--authorization", str(auth_path),
                "--binding", str(CONTACT_REQUAL_R2_BINDING_PATH),
                "--output", str(output),
            ]
            process = _invoke(case_id, command, output, execution_sha=execution_sha, route=route, mesh=mesh, kind="INDEPENDENT_REFERENCE")
            reference_processes[case_id] = process
            result_path = output / "result.json"
            statuses[case_id] = (
                _case_status(result_path, route, "INDEPENDENT_REFERENCE")
                if result_path.is_file() and process["exit_code"] == 0
                else "FAIL_CLOSED_PROCESS_EXIT"
            )
            _progress(case_id, statuses)

    # The analyzer recomputes every metric and hashes raw evidence before any replay is enabled.
    import scripts.analyze_wp07d_formal_rebind_r1 as analysis

    analysis.ARTIFACT_ROOT = ARTIFACT_ROOT
    analysis.RUN_ROOT = RUN_ROOT
    analysis.AUTH_ROOT = AUTH_ROOT
    analysis.PRE_REPLAY_REPORT = REPLAY_GATE
    analysis.REPLAY_GATE_PATH = REPLAY_GATE
    analysis.FINAL_REPORT = FINAL_REPORT
    analysis.ACTIVE_BINDING_PATH = CONTACT_REQUAL_R2_BINDING_PATH
    gate = analysis.build_pre_replay_report(CONTACT_REQUAL_R2_BINDING_PATH)
    gate["binding_path"] = CONTACT_REQUAL_R2_BINDING_PATH.relative_to(ROOT).as_posix()
    gate["binding_file_sha256"] = binding_sha
    gate["requalification_contract_sha256"] = binding["source_requalification"]["sha256"]
    gate["run_root"] = RUN_ROOT.as_posix()
    gate["authorization_root"] = AUTH_ROOT.as_posix()
    gate["production_process_manifests"] = {}
    gate["reference_process_manifests"] = {}
    gate["sequential_process_order"] = list(primary_processes) + list(reference_processes)
    for route in EXPECTED_ROUTES:
        for mesh in EXPECTED_LEVELS:
            case_key = f"{route}/{mesh}"
            for role, processes in (("production", primary_processes), ("reference", reference_processes)):
                record = processes.get(f"{case_key}/{ 'PRIMARY_PRODUCTION' if role == 'production' else 'INDEPENDENT_REFERENCE'}")
                if record is not None:
                    process_path = RUN_ROOT / route / mesh / ("primary" if role == "production" else "reference") / "runner_process.json"
                    gate[f"{role}_process_manifests"][case_key] = {
                        "path": process_path.as_posix(),
                        "sha256": _file_sha256(ROOT / process_path),
                        "pid": record.get("pid"),
                        "exit_code": record.get("exit_code"),
                    }
    if REPLAY_GATE.exists():
        raise FileExistsError(f"Refusing to overwrite replay gate: {REPLAY_GATE}")
    analysis.write_new(ROOT / REPLAY_GATE, gate)

    # Replays occur only at contract-defined levels and only after raw-evidence gates pass.
    for route in EXPECTED_ROUTES:
        route_gate = gate.get("routes", {}).get(route, {})
        if route_gate.get("status") != "PASS_READY_FOR_REPLAY":
            continue
        mesh = str(route_gate["replay_level"])
        case_id = f"{route}/{mesh}/REPLAY"
        auth_path = ROOT / AUTH_ROOT / "REPLAY" / f"{route}_{mesh}.json"
        auth_path.parent.mkdir(parents=True, exist_ok=True)
        authorization = _authorization(
            binding,
            binding_sha=binding_sha,
            execution_sha=execution_sha,
            route=route,
            mesh=mesh,
            kind="REPLAY",
            gate_sha=_file_sha256(ROOT / REPLAY_GATE),
        )
        if auth_path.exists():
            raise FileExistsError(f"Refusing to overwrite prior replay authorization {auth_path}.")
        _write_json(auth_path, authorization)
        output = ROOT / RUN_ROOT / route / mesh / "replay"
        command = [
            sys.executable,
            str(ROOT / "scripts/run_wp07d_structural.py"),
            "--route", route,
            "--mesh", mesh,
            "--authorization", str(auth_path),
            "--binding", str(CONTACT_REQUAL_R2_BINDING_PATH),
            "--output", str(output),
            "--execution-kind", "REPLAY",
        ]
        process = _invoke(case_id, command, output, execution_sha=execution_sha, route=route, mesh=mesh, kind="REPLAY")
        replay_processes[case_id] = process
        statuses[case_id] = "PASS" if process["exit_code"] == 0 and (output / "result.json").is_file() else "FAIL_CLOSED_PROCESS_EXIT"
        _progress(case_id, statuses)

    final = analysis.build_final_report(CONTACT_REQUAL_R2_BINDING_PATH)
    final["requalification_contract_sha256"] = binding["source_requalification"]["sha256"]
    final["primary_processes"] = primary_processes
    final["reference_processes"] = reference_processes
    final["replay_processes"] = replay_processes
    final["production_mechanics_changed_by_requalification"] = True
    final["wp07e_run"] = False
    final["score_awarded"] = False
    final["ledger_updated"] = False
    final["push_or_merge_performed"] = False
    final["final_status"] = final.get("status")
    if FINAL_REPORT.exists():
        raise FileExistsError(f"Refusing to overwrite final WP07-D R2 report: {FINAL_REPORT}")
    analysis.write_new(ROOT / FINAL_REPORT, final)
    _write_json(
        ROOT / PROGRESS,
        {"status": final.get("status"), "phase": "RUN_END", "updated_utc": _utc_now(), "case_statuses": statuses},
        overwrite=True,
    )
    return final


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-sha", required=True)
    args = parser.parse_args(argv)
    try:
        report = run_campaign(args.execution_sha)
    except Exception as error:
        print(f"WP07D_CONTACT_R2_FAIL_CLOSED: {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"status": report.get("status"), "execution_sha": args.execution_sha}, sort_keys=True))
    return 0 if report.get("status") == "READY_FOR_OWNER_REVIEW" else 3


if __name__ == "__main__":
    raise SystemExit(main())
