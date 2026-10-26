"""Static validation, synthetic runner checks, and gated one-unit execution."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping, Sequence

from .contracts import (
    ContractError,
    assess_manifest,
    inspect_git,
    load_json,
    safe_repo_relative_path,
    validate_manifest_schema,
    verify_manifest_input_identities,
)
from .evidence import record_refusal
from .environment import collect_environment_provenance
from .git_remote import sync_remote_identity, write_sync_receipt
from .synthetic_orchestrator import SYNTHETIC_CASES, run_synthetic_orchestration
from .scientific_execution import execute_pilot


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_USER_AUDIT_ROOT = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()).resolve(strict=True)
DEFAULT_AUDIT_DIRECTORY = _USER_AUDIT_ROOT / "QFSolverWP12" / "runner-audit"


def _json_print(value: Mapping[str, Any], *, stream: Any | None = None) -> None:
    print(json.dumps(dict(value), indent=2, sort_keys=True, ensure_ascii=False), file=stream or sys.stdout)


def _write_refusal(event: Mapping[str, Any]) -> Path:
    parent = DEFAULT_AUDIT_DIRECTORY.parent
    parent.mkdir(parents=True, exist_ok=True)
    return record_refusal(DEFAULT_AUDIT_DIRECTORY, event, allowed_root=parent)


def _git_report(manifest: Mapping[str, Any], root: Path) -> tuple[dict[str, Any], tuple[str, ...]]:
    try:
        snapshot = inspect_git(root)
    except (OSError, ContractError) as exc:
        return {"available": False, "error": str(exc)}, ("GIT_IDENTITY_UNAVAILABLE",)
    target = manifest.get("target")
    issues = []
    if isinstance(target, Mapping):
        from .contracts import git_identity_issues

        issues = list(git_identity_issues(target, snapshot))
    else:
        issues.append("MANIFEST_TARGET_INVALID")
    details = {
        "available": True,
        "branch": snapshot.branch,
        "commit": snapshot.commit,
        "git_tree": snapshot.tree,
        "clean": snapshot.clean,
        "status_porcelain": snapshot.status_porcelain,
        "issues": issues,
    }
    return details, tuple(issues)


def _validate_mode(manifest_path: Path, root: Path) -> int:
    try:
        manifest, digest = load_json(manifest_path)
        schema_errors = validate_manifest_schema(manifest)
        assessment = assess_manifest(manifest, digest)
        git_details, git_issues = _git_report(manifest, root)
        try:
            input_errors, input_records = verify_manifest_input_identities(root, manifest)
        except (OSError, ContractError) as exc:
            input_errors, input_records = (f"INPUT_IDENTITY_CHECK_FAILED:{type(exc).__name__}",), ()
        source_identity = manifest.get("source_and_test_identity", {})
        source_files = source_identity.get("tracked_source_files", []) if isinstance(source_identity, Mapping) else []
        test_files = source_identity.get("tracked_test_files", []) if isinstance(source_identity, Mapping) else []
        identity_entries = manifest.get("code_identity", {})
        if isinstance(identity_entries, Mapping):
            source_files = list(source_files) + list(identity_entries.get("source_files_sha256", {}))
            test_files = list(test_files) + list(identity_entries.get("test_files_sha256", {}))
        fixture_section = manifest.get("fixtures", {})
        fixture_entries = fixture_section.get("entries", []) if isinstance(fixture_section, Mapping) else []
        fixture_files = [
            entry["path"]
            for entry in fixture_entries
            if isinstance(entry, Mapping) and isinstance(entry.get("path"), str)
        ]
        environment_provenance = collect_environment_provenance(
            declared=dict(manifest.get("environment", {})) if isinstance(manifest.get("environment"), Mapping) else {},
            repository_root=root,
            source_files=(path for path in source_files if isinstance(path, str)),
            test_files=(path for path in test_files if isinstance(path, str)),
            fixture_files=fixture_files,
        )
    except (OSError, ContractError) as exc:
        _json_print({"mode": "VALIDATE", "state": "INVALID", "error": str(exc)}, stream=sys.stderr)
        return 2
    blockers = [*schema_errors, *assessment.execution_blockers]
    blockers.extend(git_issues)
    if input_errors:
        blockers.append("MANIFEST_INPUT_IDENTITY_PROBLEMS")
    if schema_errors or assessment.structural_errors:
        state = "INVALID"
    elif git_issues or input_errors:
        state = "BLOCKED"
    else:
        state = "STRUCTURALLY_VALID_NOT_AUTHORIZED"
    _json_print(
        {
            "mode": "VALIDATE",
            "state": state,
            "manifest_sha256": digest,
            "campaign_id": assessment.campaign_id,
            "structural_errors": list(assessment.structural_errors),
            "execution_blockers": list(dict.fromkeys(blockers)),
            "input_identity_errors": list(input_errors),
            "input_identity_records": list(input_records),
            "git": git_details,
            "environment_provenance": environment_provenance,
            "execution_started": False,
        }
    )
    return 0 if state == "STRUCTURALLY_VALID_NOT_AUTHORIZED" else 2


def _self_test_mode(case: str) -> int:
    try:
        report = run_synthetic_orchestration(case)
    except (OSError, ContractError) as exc:
        _json_print(
            {
                "mode": "SELF_TEST",
                "campaign_id": "WP12-X-SYNTHETIC-ORCHESTRATOR",
                "result_kind": "SYNTHETIC_RUNNER_SELF_TEST",
                "state": "INFRA_ERROR",
                "error": type(exc).__name__,
                "scientific_execution": False,
                "real_execute_enabled": False,
            },
            stream=sys.stderr,
        )
        return 2
    _json_print(report)
    return 0 if report["state"] in {"PASS", "PASS_WITH_NOT_APPLICABLE"} else 1


def _resolve_exact_argv(manifest: Mapping[str, Any], nodeid: str | None) -> Sequence[str] | None:
    tests = manifest.get("tests")
    if not isinstance(tests, Mapping):
        return None
    if tests.get("nodeid") == nodeid and isinstance(tests.get("argv"), list):
        argv = tests["argv"]
        return argv if all(isinstance(argument, str) for argument in argv) else None
    units = tests.get("execution_units")
    if not isinstance(units, list):
        return None
    matches = [unit for unit in units if isinstance(unit, Mapping) and unit.get("nodeid") == nodeid]
    if len(matches) != 1 or not isinstance(matches[0].get("argv"), list):
        return None
    argv = matches[0]["argv"]
    return argv if all(isinstance(argument, str) for argument in argv) else None


def _destination_exists(root: Path, manifest: Mapping[str, Any]) -> bool:
    destination = manifest.get("destination")
    if not safe_repo_relative_path(destination):
        return False
    path = root.joinpath(*Path(destination).parts)
    return path.exists() or path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())


def _execute_mode(
    manifest_path: Path,
    owner_path: Path | None,
    supplied_sha256: str | None,
    nodeid: str | None,
    root: Path,
) -> int:
    event = execute_pilot(
        runner_root=root,
        manifest_path=manifest_path,
        owner_decision_path=owner_path,
        supplied_manifest_sha256=supplied_sha256,
    )
    try:
        event["refusal_record"] = str(_write_refusal(event))
    except (OSError, ContractError) as exc:
        event["refusal_record_error"] = f"{type(exc).__name__}: {exc}"
    _json_print(event, stream=sys.stderr)
    return 0 if event.get("status") in {"PASS", "FAIL", "INCONCLUSIVE"} else 3


def _log_execute_argument_refusal(blocker: str) -> None:
    event: dict[str, Any] = {
        "mode": "EXECUTE",
        "event": "DENY_EXECUTION",
        "execution_started": False,
        "blockers": [blocker],
    }
    try:
        event["refusal_record"] = str(_write_refusal(event))
    except (OSError, ContractError) as exc:
        event["refusal_record_error"] = f"{type(exc).__name__}: {exc}"
    _json_print(event, stream=sys.stderr)


def _trust_status_mode(root: Path) -> int:
    from .owner_trust import load_machine_trust_store

    try:
        trusted_keys, trust_store_sha = load_machine_trust_store(root)
    except (OSError, ContractError) as exc:
        _json_print(
            {
                "mode": "TRUST_STATUS",
                "state": "NOT_CONFIGURED_OR_INVALID",
                "error": str(exc),
                "private_key_accessed": False,
            },
            stream=sys.stderr,
        )
        return 2
    _json_print(
        {
            "mode": "TRUST_STATUS",
            "state": "VERIFIED_READ_ONLY",
            "trust_store_sha256": trust_store_sha,
            "keys": [
                {
                    "key_id": key.key_id,
                    "principal": key.principal,
                    "revoked": key.revoked,
                    "public_key_sha256": hashlib.sha256(base64.b64decode(key.public_key_base64)).hexdigest(),
                }
                for key in sorted(trusted_keys.values(), key=lambda item: item.key_id)
            ],
            "private_key_accessed": False,
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="WP12 static validation, trust inspection, synthetic self-tests, and authenticated single-unit EXECUTE"
    )
    parser.add_argument("--mode", choices=("VALIDATE", "TRUST_STATUS", "SELF_TEST", "SYNC", "EXECUTE"), required=True)
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--owner-decision", type=Path)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--nodeid")
    parser.add_argument("--case", choices=("all", *SYNTHETIC_CASES))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    supplied_args = list(argv) if argv is not None else sys.argv[1:]
    try:
        args = parser.parse_args(supplied_args)
    except SystemExit:
        mode_is_execute = "--mode=EXECUTE" in supplied_args or any(
            supplied_args[index : index + 2] == ["--mode", "EXECUTE"] for index in range(max(0, len(supplied_args) - 1))
        )
        if mode_is_execute:
            _log_execute_argument_refusal("EXECUTE_ARGUMENT_VALIDATION_FAILED")
        raise
    if args.mode == "SELF_TEST":
        if any(value is not None for value in (args.manifest, args.owner_decision, args.manifest_sha256, args.nodeid)):
            parser.error("SELF_TEST accepts no manifest, Owner decision, nodeid, or command selector")
        return _self_test_mode(args.case or "all")
    if args.mode == "TRUST_STATUS":
        if any(
            value is not None
            for value in (args.manifest, args.owner_decision, args.manifest_sha256, args.nodeid, args.case)
        ):
            parser.error("TRUST_STATUS reads only the machine-pinned Owner trust root")
        if args.root.resolve(strict=False) != REPOSITORY_ROOT.resolve(strict=False):
            parser.error("TRUST_STATUS must run from the configured runner checkout")
        return _trust_status_mode(REPOSITORY_ROOT)
    if args.mode == "VALIDATE":
        if args.manifest is None:
            parser.error("VALIDATE requires --manifest")
        if any(value is not None for value in (args.owner_decision, args.manifest_sha256, args.nodeid, args.case)):
            parser.error("VALIDATE is static and does not accept execution authorization or node selectors")
        return _validate_mode(args.manifest, args.root)
    if args.mode == "SYNC":
        if any(
            value is not None
            for value in (args.manifest, args.owner_decision, args.manifest_sha256, args.nodeid, args.case)
        ):
            parser.error("SYNC refreshes only the exact configured remote branch and accepts no manifest selectors")
        try:
            identity = sync_remote_identity(args.root)
            receipt_path = write_sync_receipt(args.root, identity, DEFAULT_AUDIT_DIRECTORY)
        except (OSError, ContractError) as exc:
            _json_print(
                {"mode": "SYNC", "state": "BLOCKED", "error": str(exc), "execution_started": False}, stream=sys.stderr
            )
            return 2
        _json_print(
            {"mode": "SYNC", "state": "SYNCHRONIZED", "remote": identity.__dict__, "receipt": str(receipt_path)}
        )
        return 0
    if args.manifest is None:
        _log_execute_argument_refusal("MANIFEST_ABSENT")
        return 3
    if args.case is not None:
        _log_execute_argument_refusal("EXECUTE_SYNTHETIC_CASE_SELECTOR_REJECTED")
        return 3
    return _execute_mode(
        args.manifest,
        args.owner_decision,
        args.manifest_sha256,
        args.nodeid,
        args.root,
    )
