"""Run source-bound WP08-D M1/M2/M3 production, reference, and replay cases.

The historical preparation contract remains unchanged. This orchestration
requires a separate exact-HEAD Owner authorization and binds its output to the
new requalification record before importing any production solver module.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

CONTRACT_PATH = ROOT / "qualification/0_2_9/wp08d_contact_requalification_r1.json"
PARENT_CONTRACT_PATH = ROOT / "qualification/0_2_9/wp08d_structural_reference_contract.json"
PARENT_CONTRACT_DIGEST = "d2d9533c873000996ab3fad992c653dfed37f533ed12d85af97b3696740f179a"
POLICY_DIGEST = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
GOVERNING_BASE_SHA = "b2485f98260c7ca9892997eefa3a327637d83cd3"
REQUIRED_BRANCH = "codex/contact-active-set-remediation"
MESHES = ("M1", "M2", "M3")
OWNER_TOKEN = "OWNER_AUTHORIZED_WP07_WP08_CONTACT_REQUALIFICATION"
OWNER_DECISION_PATH = ROOT / "qualification/0_2_9/wp07d_contact_requalification_r2/owner_execution_decision.json"
DEFAULT_OUTPUT_ROOT = ROOT / "qualification/0_2_9/wp08d_contact_requalification_r1_runs/raw_retry_1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def _git_dir() -> Path:
    """Resolve the actual Git metadata directory, including linked worktrees."""

    return Path(_git("rev-parse", "--absolute-git-dir")).resolve()


def _owner_authorization_path(execution_sha: str) -> Path:
    return _git_dir() / f"wp08_contact_requalification_owner_authorization_{execution_sha}.json"


def _case_authorization_path(execution_sha: str, mesh: str, execution_kind: str) -> Path:
    return _git_dir() / (
        f"wp08_contact_requalification_{execution_sha}_{mesh.lower()}_{execution_kind.lower()}_authorization.json"
    )


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _validate(contract: dict[str, Any], authorization: dict[str, Any], output: Path) -> str:
    if contract.get("status") != "FROZEN_FOR_OWNER_AUTHORIZED_REQUALIFICATION":
        raise PermissionError("WP08-D requalification contract is not frozen.")
    parent = _json(PARENT_CONTRACT_PATH)
    canonical_parent = json.dumps(
        parent, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    if hashlib.sha256(canonical_parent).hexdigest() != PARENT_CONTRACT_DIGEST:
        raise PermissionError("The frozen WP08-D parent contract digest changed.")
    if contract.get("parent_contract", {}).get("canonical_sha256") != PARENT_CONTRACT_DIGEST:
        raise PermissionError("The requalification contract does not bind the frozen WP08-D contract.")
    if contract.get("governing", {}).get("base_sha") != GOVERNING_BASE_SHA:
        raise PermissionError("Unexpected governing base in WP08-D requalification contract.")
    if contract.get("governing", {}).get("policy_digest") != POLICY_DIGEST:
        raise PermissionError("Unexpected governing policy digest.")
    owner_decision = contract.get("owner_decision", {})
    if (
        owner_decision.get("path") != OWNER_DECISION_PATH.relative_to(ROOT).as_posix()
        or not OWNER_DECISION_PATH.is_file()
        or owner_decision.get("sha256") != _sha256(OWNER_DECISION_PATH)
    ):
        raise PermissionError("WP08-D contract does not bind the committed Owner execution decision.")
    owner_record = _json(OWNER_DECISION_PATH)
    decisions = owner_record.get("decisions", {})
    if (
        owner_record.get("status") != "AUTHORIZED_FOR_SOURCE_BOUND_REQUALIFICATION"
        or decisions.get("OWNER_AUTHORIZES_WP08D_M1_M2_M3_REQUALIFICATION") is not True
        or decisions.get("OWNER_AUTHORIZES_WP08D_INDEPENDENT_REFERENCES") is not True
        or decisions.get("OWNER_AUTHORIZES_WP08D_CONTRACT_REQUIRED_REPLAY") is not True
        or decisions.get("OWNER_AUTHORIZES_WP07E_OR_WP08E") is not False
        or decisions.get("OWNER_AWARDS_POINTS") is not False
    ):
        raise PermissionError("The recorded Owner decision does not authorize exactly this WP08-D scope.")
    if authorization.get("token") != OWNER_TOKEN or authorization.get("owner_authorized") is not True:
        raise PermissionError("Explicit Owner execution authorization is missing.")
    if authorization.get("status") != "OWNER_AUTHORIZED_EXACT_SOURCE_REQUALIFICATION":
        raise PermissionError("WP08-D exact-source Owner authorization has an invalid status.")
    if (
        authorization.get("wp08e_allowed") is not False
        or authorization.get("points_awarded") is not False
        or authorization.get("merge_or_push_allowed") is not False
    ):
        raise PermissionError("WP08-D authorization must not include closure, score, merge, or push authority.")
    if (
        authorization.get("owner_decision_path") != owner_decision.get("path")
        or authorization.get("owner_decision_sha256") != owner_decision.get("sha256")
        or authorization.get("meshes") != list(MESHES)
        or authorization.get("replay_meshes") != contract.get("campaign", {}).get("replay_meshes")
    ):
        raise PermissionError("Owner authorization scope differs from the frozen WP08-D contract.")
    if authorization.get("requalification_contract_sha256") != _sha256(CONTRACT_PATH):
        raise PermissionError("Owner authorization does not bind the exact WP08-D requalification contract.")
    if authorization.get("parent_contract_digest") != PARENT_CONTRACT_DIGEST:
        raise PermissionError("Owner authorization is bound to a different parent contract.")
    if authorization.get("policy_digest") != POLICY_DIGEST:
        raise PermissionError("Owner authorization is bound to a different policy.")
    if authorization.get("branch") != REQUIRED_BRANCH or _git("branch", "--show-current") != REQUIRED_BRANCH:
        raise PermissionError("Execution branch differs from the authorized branch.")
    execution_sha = _git("rev-parse", "HEAD")
    if authorization.get("execution_sha") != execution_sha:
        raise PermissionError("Execution SHA differs from the exact Owner-authorized SHA.")
    if _git("status", "--porcelain"):
        raise PermissionError("Source worktree must be clean before the campaign starts.")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", GOVERNING_BASE_SHA, execution_sha],
        cwd=ROOT,
        check=False,
    ).returncode:
        raise PermissionError("Execution source is not descended from the governing base.")
    remediation_sha = contract.get("mechanics_requalification", {}).get("change_commit")
    if not isinstance(remediation_sha, str) or subprocess.run(
        ["git", "merge-base", "--is-ancestor", remediation_sha, execution_sha],
        cwd=ROOT,
        check=False,
    ).returncode:
        raise PermissionError("WP08-D execution source does not contain the authorized contact-mechanics correction.")
    source_diff = subprocess.run(
        ["git", "diff", "--binary", GOVERNING_BASE_SHA, execution_sha, "--", "src"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    if hashlib.sha256(source_diff).hexdigest() != contract.get("mechanics_requalification", {}).get(
        "source_diff_sha256_since_governing_base"
    ):
        raise PermissionError("WP08-D production-source diff differs from the reviewed contact remediation lineage.")
    if authorization.get("meshes") != list(MESHES):
        raise PermissionError("Owner authorization must name exactly M1, M2, and M3.")
    if authorization.get("include_independent_references") is not True or authorization.get("include_replays") is not True:
        raise PermissionError("Reference and replay execution are not explicitly authorized.")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty output directory: {output}")
    if output.resolve() != DEFAULT_OUTPUT_ROOT.resolve():
        raise PermissionError("WP08-D output must use the frozen, dedicated requalification evidence root.")
    replay_auth_meshes = tuple(contract.get("campaign", {}).get("replay_meshes", []))
    expected_auth_paths = [
        _case_authorization_path(execution_sha, mesh, "PRIMARY_PRODUCTION")
        for mesh in MESHES
    ] + [
        _case_authorization_path(execution_sha, mesh, "REPLAY")
        for mesh in replay_auth_meshes
    ]
    existing_auth = [str(path) for path in expected_auth_paths if path.exists()]
    if existing_auth:
        raise FileExistsError(f"Refusing partial/previous WP08-D authorization set: {existing_auth}")
    return execution_sha


def _issue_owner_authorization(path: Path) -> dict[str, Any]:
    """Materialize the current explicit Owner decision against the frozen HEAD."""

    contract = _json(CONTRACT_PATH)
    decision_ref = contract.get("owner_decision", {})
    if (
        contract.get("status") != "FROZEN_FOR_OWNER_AUTHORIZED_REQUALIFICATION"
        or decision_ref.get("path") != OWNER_DECISION_PATH.relative_to(ROOT).as_posix()
        or not OWNER_DECISION_PATH.is_file()
        or decision_ref.get("sha256") != _sha256(OWNER_DECISION_PATH)
    ):
        raise PermissionError("WP08-D frozen contract does not bind the current Owner decision.")
    owner_record = _json(OWNER_DECISION_PATH)
    decisions = owner_record.get("decisions", {})
    if (
        decisions.get("OWNER_AUTHORIZES_WP08D_M1_M2_M3_REQUALIFICATION") is not True
        or decisions.get("OWNER_AUTHORIZES_WP08D_INDEPENDENT_REFERENCES") is not True
        or decisions.get("OWNER_AUTHORIZES_WP08D_CONTRACT_REQUIRED_REPLAY") is not True
        or decisions.get("OWNER_AUTHORIZES_WP07E_OR_WP08E") is not False
        or decisions.get("OWNER_AWARDS_POINTS") is not False
    ):
        raise PermissionError("Owner decision does not authorize exactly the frozen WP08-D scope.")
    branch = _git("branch", "--show-current")
    execution_sha = _git("rev-parse", "HEAD")
    if branch != REQUIRED_BRANCH or _git("status", "--porcelain"):
        raise PermissionError("WP08-D authorization requires the designated branch and a clean worktree.")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", GOVERNING_BASE_SHA, execution_sha],
        cwd=ROOT,
        check=False,
        capture_output=True,
    ).returncode:
        raise PermissionError("WP08-D exact execution source is outside the governing lineage.")
    record = {
        "schema_version": 1,
        "artifact_id": "QF-029-WP08-D-OWNER-EXECUTION-AUTHORIZATION-CONTACT-R1-001",
        "status": "OWNER_AUTHORIZED_EXACT_SOURCE_REQUALIFICATION",
        "token": OWNER_TOKEN,
        "owner_authorized": True,
        "authorization_basis": owner_record.get("authorization_basis"),
        "owner_decision_path": decision_ref["path"],
        "owner_decision_sha256": decision_ref["sha256"],
        "requalification_contract_sha256": _sha256(CONTRACT_PATH),
        "parent_contract_digest": PARENT_CONTRACT_DIGEST,
        "policy_digest": POLICY_DIGEST,
        "branch": branch,
        "execution_sha": execution_sha,
        "meshes": list(MESHES),
        "replay_meshes": contract.get("campaign", {}).get("replay_meshes"),
        "include_independent_references": True,
        "include_replays": True,
        "wp08e_allowed": False,
        "points_awarded": False,
        "merge_or_push_allowed": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
    return record


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(rendered)
        stream.flush()


def _read_if_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _audit_process_sequence(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify every child invocation and prove the actual campaign order is serial."""

    expected_rank = {
        f"WP08D-{mesh}-PRIMARY_PRODUCTION": index for index, mesh in enumerate(MESHES)
    }
    offset = len(expected_rank)
    expected_rank.update(
        {f"WP08D-{mesh}-INDEPENDENT_REFERENCE": offset + index for index, mesh in enumerate(MESHES)}
    )
    expected_rank["WP08D-M1-REPLAY"] = offset + len(MESHES)
    expected_labels = [
        *(f"WP08D-{mesh}-PRIMARY_PRODUCTION" for mesh in MESHES),
        *(f"WP08D-{mesh}-INDEPENDENT_REFERENCE" for mesh in MESHES),
        "WP08D-M1-REPLAY",
    ]
    errors: list[str] = []
    intervals: list[tuple[datetime, datetime, str]] = []
    ranks: list[int] = []
    seen: set[str] = set()
    for item in records:
        label = str(item.get("case", ""))
        if label not in expected_rank or label in seen:
            errors.append(f"unexpected or duplicate process case: {label}")
            continue
        seen.add(label)
        ranks.append(expected_rank[label])
        relative = item.get("process_manifest")
        if not isinstance(relative, str):
            errors.append(f"missing process manifest path: {label}")
            continue
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file() or _sha256(path) != item.get("sha256"):
            errors.append(f"process manifest path/hash mismatch: {label}")
            continue
        record = _read_if_object(path)
        if (
            record is None
            or record.get("case") != label
            or record.get("exit_code") != 0
            or record.get("invocation_error") is not None
            or not isinstance(record.get("pid"), int)
            or record["pid"] <= 0
            or item.get("pid") != record.get("pid")
            or item.get("exit_code") != 0
        ):
            errors.append(f"process identity/exit check failed: {label}")
            continue
        for filename, field in (("runner.stdout.log", "stdout_sha256"), ("runner.stderr.log", "stderr_sha256")):
            log = path.parent / filename
            if not log.is_file() or _sha256(log) != record.get(field):
                errors.append(f"process log hash mismatch: {label}/{filename}")
        try:
            started = datetime.fromisoformat(str(record["started_utc"]).replace("Z", "+00:00"))
            ended = datetime.fromisoformat(str(record["ended_utc"]).replace("Z", "+00:00"))
            if started.tzinfo is None or ended.tzinfo is None or ended < started:
                raise ValueError("invalid timestamp interval")
            intervals.append((started, ended, label))
        except (KeyError, TypeError, ValueError):
            errors.append(f"invalid process timestamps: {label}")
    if ranks != sorted(ranks) or len(ranks) != len(set(ranks)):
        errors.append("child processes do not follow primary -> reference -> contract replay order")
    if [str(item.get("case", "")) for item in records] != expected_labels:
        errors.append("the complete three-primary, three-reference, M1-replay process set is not present")
    for previous, current in zip(intervals, intervals[1:]):
        if current[0] < previous[1] or current[0] < previous[0]:
            errors.append(f"child processes overlap or timestamps regress: {previous[2]} -> {current[2]}")
    return {
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "invocation_count": len(records),
        "sequential": not errors,
        "errors": errors,
        "process_manifest_sha256": [item.get("sha256") for item in records],
    }


def _run(output: Path, owner_authorization_path: Path, execution_sha: str) -> dict[str, Any]:
    from scripts.wp08d_phase1_common import CONTACT_REQUALIFICATION_OWNER_TOKEN, replay_comparison

    owner_authorization = _json(owner_authorization_path)
    contract = _json(CONTRACT_PATH)
    owner_decision = contract["owner_decision"]
    replay_meshes = tuple(contract.get("campaign", {}).get("replay_meshes", []))
    process_records: list[dict[str, Any]] = []

    def case_authorization(mesh: str, execution_kind: str) -> Path:
        is_solve = execution_kind in {"PRIMARY_PRODUCTION", "REPLAY"}
        payload = {
            "authorization": CONTACT_REQUALIFICATION_OWNER_TOKEN,
            "owner_authorized": True,
            "work_package": "WP08-D",
            "scope": "WP08-D_CONTACT_MECHANICS_REQUALIFICATION",
            "branch": REQUIRED_BRANCH,
            "execution_sha": execution_sha,
            "requalification_contract_sha256": _sha256(CONTRACT_PATH),
            "parent_contract_digest": PARENT_CONTRACT_DIGEST,
            "policy_digest": POLICY_DIGEST,
            "governing_base_sha": GOVERNING_BASE_SHA,
            "working_tree_clean": True,
            "mesh": mesh,
            "meshes": list(MESHES),
            "execution_kind": execution_kind,
            "structural_solves_allowed": is_solve,
            "independent_references_allowed": False,
            "replay_allowed": execution_kind == "REPLAY",
            "owner_authorization_sha256": _sha256(owner_authorization_path),
            "owner_authorization_basis": owner_authorization.get("authorization_basis"),
            "owner_decision_path": owner_decision["path"],
            "owner_decision_sha256": owner_decision["sha256"],
            "authorization_scope": {"diagnostic_load_step_limit": None},
        }
        path = _case_authorization_path(execution_sha, mesh, execution_kind)
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite prior WP08-D case authorization: {path}")
        _write_json(path, payload)
        return path

    def bind_sidecar(case_dir: Path, mesh: str, kind: str) -> None:
        _write_json(
            case_dir / "requalification_binding.json",
            {
                "work_package": "WP08-D",
                "mesh": mesh,
                "execution_kind": kind,
                "execution_sha": execution_sha,
                "requalification_contract_sha256": _sha256(CONTRACT_PATH),
                "parent_contract_digest": PARENT_CONTRACT_DIGEST,
                "policy_digest": POLICY_DIGEST,
                "owner_authorization_sha256": _sha256(owner_authorization_path),
                "owner_decision_sha256": owner_decision["sha256"],
            },
        )

    def invoke(label: str, command: list[str], output_dir: Path) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = output_dir / "runner.stdout.log"
        stderr_path = output_dir / "runner.stderr.log"
        started = _utc_now()
        process: subprocess.Popen[str] | None = None
        error: str | None = None
        exit_code: int | None = None
        try:
            with stdout_path.open("x", encoding="utf-8", newline="") as stdout, stderr_path.open(
                "x", encoding="utf-8", newline=""
            ) as stderr:
                process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr, text=True)
                exit_code = process.wait()
        except Exception as exception:  # preserve invocation failure separately from numerical status
            error = f"{type(exception).__name__}: {exception}"
            if process is not None:
                exit_code = process.poll()
        record = {
            "schema_version": 1,
            "case": label,
            "command": command,
            "started_utc": started,
            "ended_utc": _utc_now(),
            "pid": process.pid if process is not None else None,
            "exit_code": exit_code,
            "invocation_error": error,
            "stdout_sha256": _sha256(stdout_path) if stdout_path.is_file() else None,
            "stderr_sha256": _sha256(stderr_path) if stderr_path.is_file() else None,
        }
        _write_json(output_dir / "process.json", record)
        process_records.append({"case": label, "process_manifest": (output_dir / "process.json").relative_to(ROOT).as_posix(), "sha256": _sha256(output_dir / "process.json"), "pid": record["pid"], "exit_code": exit_code})
        return record

    def checkpoint(phase: str, production_state: dict[str, Any], references_state: dict[str, Any], replay_state: dict[str, Any]) -> None:
        _write_json(
            output / "progress.json",
            {
                "status": "RUNNING",
                "phase": phase,
                "updated_utc": _utc_now(),
                "production": production_state,
                "independent_reference": references_state,
                "replay": replay_state,
            },
        )

    production: dict[str, dict[str, Any]] = {}
    for mesh in MESHES:
        case_dir = output / mesh / "production"
        authorization_path = case_authorization(mesh, "PRIMARY_PRODUCTION")
        command = [
            sys.executable,
            str(ROOT / "scripts/run_wp08d_frictional_structural.py"),
            "--mesh", mesh,
            "--execute-phase1",
            "--execution-kind", "PRIMARY_PRODUCTION",
            "--authorization-file", str(authorization_path),
            "--output-dir", str(case_dir),
        ]
        process = invoke(f"WP08D-{mesh}-PRIMARY_PRODUCTION", command, case_dir)
        result_path = case_dir / mesh / "result.json"
        result = _read_if_object(result_path) or {}
        result["process_exit_code"] = process["exit_code"]
        result["terminal_classification"] = (
            result.get("terminal_classification")
            if process["exit_code"] == 0
            else "FAIL_CLOSED_PROCESS_EXIT"
        )
        production[mesh] = result
        if result_path.is_file():
            bind_sidecar(case_dir / mesh, mesh, "PRIMARY_PRODUCTION")
        checkpoint(f"PRIMARY_{mesh}", production, {}, {})

    references: dict[str, dict[str, Any]] = {}
    for mesh in MESHES:
        if production[mesh].get("terminal_classification") != "PASS":
            references[mesh] = {"status": "NOT_RUN_PRIMARY_NOT_PASS"}
            checkpoint(f"REFERENCE_{mesh}_SKIPPED", production, references, {})
            continue
        prod_path = output / mesh / "production" / mesh / "result.json"
        ref_path = output / mesh / "independent_reference"
        script = "run_wp08d_m1_independent_reference.py" if mesh == "M1" else "run_wp08d_independent_reference.py"
        command = [
            sys.executable,
            str(ROOT / "scripts" / script),
            "--production-result", str(prod_path),
            "--output-dir", str(ref_path),
        ]
        if mesh != "M1":
            command.extend(["--mesh", mesh])
        process = invoke(f"WP08D-{mesh}-INDEPENDENT_REFERENCE", command, ref_path)
        references[mesh] = _read_if_object(ref_path / "result.json") or {
            "status": "FAIL_CLOSED_REFERENCE_RESULT_MISSING"
        }
        references[mesh]["process_exit_code"] = process["exit_code"]
        if process["exit_code"] != 0:
            references[mesh]["status"] = "FAIL_CLOSED_REFERENCE_PROCESS_EXIT"
        if (ref_path / "result.json").is_file():
            bind_sidecar(ref_path, mesh, "INDEPENDENT_REFERENCE")
        checkpoint(f"REFERENCE_{mesh}", production, references, {})

    replays: dict[str, dict[str, Any]] = {}
    comparisons: dict[str, dict[str, Any]] = {}
    for mesh in MESHES:
        if mesh not in replay_meshes:
            replays[mesh] = {"status": "NOT_REQUIRED_BY_FROZEN_CONTRACT"}
            comparisons[mesh] = {"status": "NOT_REQUIRED_BY_FROZEN_CONTRACT"}
            continue
        if production[mesh].get("terminal_classification") != "PASS" or references[mesh].get("status") not in {"PASS", "PASS_REFERENCE"}:
            replays[mesh] = {"status": "NOT_RUN_DEPENDENCY_NOT_PASS"}
            comparisons[mesh] = {"status": "NOT_RUN_DEPENDENCY_NOT_PASS"}
            checkpoint(f"REPLAY_{mesh}_SKIPPED", production, references, replays)
            continue
        replay_dir = output / mesh / "replay"
        authorization_path = case_authorization(mesh, "REPLAY")
        command = [
            sys.executable,
            str(ROOT / "scripts/run_wp08d_frictional_structural.py"),
            "--mesh", mesh,
            "--execute-phase1",
            "--execution-kind", "REPLAY",
            "--authorization-file", str(authorization_path),
            "--output-dir", str(replay_dir),
        ]
        process = invoke(f"WP08D-{mesh}-REPLAY", command, replay_dir)
        replay = _read_if_object(replay_dir / mesh / "result.json") or {}
        replay["process_exit_code"] = process["exit_code"]
        replays[mesh] = replay
        if (replay_dir / mesh / "result.json").is_file():
            bind_sidecar(replay_dir / mesh, mesh, "REPLAY")
        comparisons[mesh] = replay_comparison(production[mesh], replay)
        if process["exit_code"] != 0:
            comparisons[mesh] = {
                **comparisons[mesh],
                "status": "FAIL_CLOSED_REPLAY_PROCESS_EXIT",
                "process_exit_code": process["exit_code"],
            }
        checkpoint(f"REPLAY_{mesh}", production, references, replays)

    return {
        "production": production,
        "independent_reference": references,
        "replay": replays,
        "replay_comparison": comparisons,
        "replay_meshes_required": list(replay_meshes),
        "sequential_process_manifests": process_records,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--owner-authorization", type=Path)
    mode.add_argument("--issue-owner-authorization", action="store_true")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    try:
        if args.issue_owner_authorization:
            execution_sha = _git("rev-parse", "HEAD")
            auth_path = _owner_authorization_path(execution_sha)
            record = _issue_owner_authorization(auth_path)
            print(json.dumps({"status": record["status"], "execution_sha": record["execution_sha"], "authorization_path": str(auth_path)}, indent=2))
            return 0
        contract = _json(CONTRACT_PATH)
        authorization = _json(args.owner_authorization.resolve())
        output = args.output_root.resolve()
        execution_sha = _validate(contract, authorization, output)
        output.mkdir(parents=True, exist_ok=True)
        campaign = _run(output, args.owner_authorization.resolve(), execution_sha)
        all_pass = all(
            campaign["production"].get(mesh, {}).get("terminal_classification") == "PASS"
            and campaign["independent_reference"].get(mesh, {}).get("status") in {"PASS", "PASS_REFERENCE"}
            for mesh in MESHES
        )
        all_pass = all_pass and all(
            campaign["replay_comparison"].get(mesh, {}).get("status") == "PASS"
            for mesh in campaign["replay_meshes_required"]
        )
        process_audit = _audit_process_sequence(campaign["sequential_process_manifests"])
        all_pass = all_pass and process_audit["status"] == "PASS"
        summary = {
            "artifact_id": "QF-029-WP08-D-CONTACT-MECHANICS-REQUALIFICATION-R1-RESULT",
            "status": "PASS_CANDIDATE" if all_pass else "FAIL_CLOSED_OR_INCOMPLETE",
            "execution_sha": execution_sha,
            "branch": REQUIRED_BRANCH,
            "contract_sha256": _sha256(CONTRACT_PATH),
            "parent_contract_digest": PARENT_CONTRACT_DIGEST,
            "policy_digest": POLICY_DIGEST,
            "owner_authorization_sha256": _sha256(args.owner_authorization.resolve()),
            "campaign": campaign,
            "process_audit": process_audit,
            "official_points_awarded": 0,
            "wp08e_run": False,
        }
        _write_json(output / "wp08d_requalification_summary.json", summary)
        _write_json(
            output / "progress.json",
            {"status": summary["status"], "phase": "RUN_END", "updated_utc": _utc_now()},
        )
        print(json.dumps({"status": summary["status"], "execution_sha": execution_sha, "output_root": str(output)}, indent=2))
        return 0 if summary["status"] == "PASS_CANDIDATE" else 3
    except Exception as error:
        print(f"WP08D_REQUALIFICATION_FAIL_CLOSED: {type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
