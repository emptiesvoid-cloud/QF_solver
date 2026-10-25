"""Command-line modes for static validation and synthetic runner checks."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping, Sequence

from .contracts import (
    ContractError,
    assess_manifest,
    execution_gate_blockers,
    inspect_git,
    load_json,
    safe_repo_relative_path,
    validate_manifest_schema,
    validate_owner_decision_structure,
    verify_manifest_input_identities,
)
from .evidence import record_refusal, verify_receipt, write_receipt
from .environment import collect_environment_provenance
from .git_remote import sync_remote_identity, write_sync_receipt
from .owner_trust import load_machine_trust_store, verify_owner_decision
from .process import FAKE_CASES, ProcessOutcome, run_fake_process


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUDIT_DIRECTORY = REPOSITORY_ROOT / ".codex" / "wp12_runner_audit"


def _json_print(value: Mapping[str, Any], *, stream: Any = sys.stdout) -> None:
    print(json.dumps(dict(value), indent=2, sort_keys=True, ensure_ascii=False), file=stream)


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


def _expected_self_test_result(case: str, outcome: ProcessOutcome) -> tuple[bool, str]:
    if case == "memory":
        passed = (
            outcome.state == "PROCESS_EXITED" and outcome.return_code not in (None, 0) and outcome.hard_job_enforced
        )
        return (
            passed,
            "Windows Job Object memory ceiling terminated the synthetic child"
            if passed
            else "hard memory ceiling was not demonstrated",
        )
    expected = {
        "success": ("PROCESS_EXITED", 0),
        "exit": ("PROCESS_EXITED", 17),
        "sleep": ("TIMEOUT", None),
        "tree": ("TIMEOUT", None),
        "flood": ("RESOURCE_LIMIT", None),
    }[case]
    passed = outcome.state == expected[0]
    if expected[1] is not None:
        passed = passed and outcome.return_code == expected[1]
    if case == "tree":
        passed = passed and not outcome.child_pids_remaining
    return (
        passed,
        "synthetic supervisor behavior matched its fixture expectation"
        if passed
        else "unexpected synthetic process result",
    )


def _self_test_mode(case: str) -> int:
    cases = sorted(FAKE_CASES) if case == "all" else [case]
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="qf-wp12-runner-self-test-") as temporary:
        root = Path(temporary)
        for selected in cases:
            if selected == "memory" and os.name != "nt":
                results.append(
                    {
                        "case": selected,
                        "self_test": "NOT_APPLICABLE",
                        "explanation": "Windows Job Object resource enforcement is platform-specific",
                        "scientific_result": False,
                    }
                )
                continue
            run_directory = root / selected
            timeout = 0.35 if selected in {"sleep", "tree"} else 2.0
            output_limit = 256 if selected == "flood" else 64 * 1024
            outcome = run_fake_process(
                selected,
                run_directory,
                timeout_seconds=timeout,
                output_byte_limit=output_limit,
                process_count_limit=8,
                memory_hard_limit_bytes=64 * 1024 * 1024 if selected == "memory" else None,
            )
            passed, explanation = _expected_self_test_result(selected, outcome)
            receipt_hash, _receipt_path = write_receipt(
                run_directory,
                {
                    "mode": "SELF_TEST",
                    "case": selected,
                    "supervisor_state": outcome.state,
                    "scientific_result": False,
                },
            )
            receipt_issues = verify_receipt(run_directory)
            passed = passed and not receipt_issues
            results.append(
                {
                    "case": selected,
                    "self_test": "PASS" if passed else "FAIL",
                    "explanation": explanation,
                    "supervisor_state": outcome.state,
                    "return_code": outcome.return_code,
                    "stop_reason": outcome.stop_reason,
                    "elapsed_seconds": round(outcome.elapsed_seconds, 6),
                    "stdout_bytes_seen": outcome.stdout_bytes,
                    "stderr_bytes_seen": outcome.stderr_bytes,
                    "sampled_peak_rss_bytes": outcome.sampled_peak_rss_bytes,
                    "sampled_peak_process_count": outcome.sampled_peak_process_count,
                    "child_pids_remaining": list(outcome.child_pids_remaining),
                    "hard_job_enforced": outcome.hard_job_enforced,
                    "receipt_sha256": receipt_hash,
                    "receipt_issues": list(receipt_issues),
                }
            )
    all_pass = all(result["self_test"] in {"PASS", "NOT_APPLICABLE"} for result in results)
    has_not_applicable = any(result["self_test"] == "NOT_APPLICABLE" for result in results)
    _json_print(
        {
            "mode": "SELF_TEST",
            "state": "PASS_WITH_NOT_APPLICABLE" if all_pass and has_not_applicable else "PASS" if all_pass else "FAIL",
            "scientific_execution": False,
            "results": results,
        }
    )
    return 0 if all_pass else 1


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
    event: dict[str, Any] = {"mode": "EXECUTE", "event": "DENY_EXECUTION", "execution_started": False}
    manifest: dict[str, Any] = {}
    digest = ""
    assessment = None
    decision = None
    git_snapshot = None
    try:
        manifest, digest = load_json(manifest_path)
        assessment = assess_manifest(manifest, digest)
        event.update({"campaign_id": assessment.campaign_id, "manifest_sha256": digest})
        input_errors, input_records = verify_manifest_input_identities(root, manifest)
        event["input_identity_errors"] = list(input_errors)
        event["input_identity_records"] = list(input_records)
        if owner_path is not None:
            decision, _decision_sha = load_json(owner_path)
            event["owner_decision_sha256"] = _decision_sha
        try:
            git_snapshot = inspect_git(root)
        except (OSError, ContractError) as exc:
            event["git_error"] = str(exc)
        argv = _resolve_exact_argv(manifest, nodeid)
        owner_authenticated = False
        if decision is not None:
            event["owner_decision_structural_errors"] = list(validate_owner_decision_structure(decision))
            try:
                trusted_keys, trust_store_sha256 = load_machine_trust_store(root)
                target = manifest.get("target", {})
                declared_scientific = manifest.get("scientific_identity", target)
                if isinstance(declared_scientific, Mapping):
                    scientific_identity = {
                        "commit": str(declared_scientific.get("commit", "")),
                        "git_tree": str(declared_scientific.get("git_tree", "")),
                    }
                else:
                    scientific_identity = {"commit": "", "git_tree": ""}
                runner_identity = (
                    {"commit": git_snapshot.commit, "git_tree": git_snapshot.tree}
                    if git_snapshot is not None
                    else {"commit": "", "git_tree": ""}
                )
                authentication = verify_owner_decision(
                    decision,
                    trusted_keys=trusted_keys,
                    manifest_sha256=digest,
                    expected_campaign_id=str(manifest.get("campaign_id", "")),
                    expected_scientific_identity=scientific_identity,
                    expected_runner_identity=runner_identity,
                )
                event["owner_authentication"] = {
                    "authenticated": authentication.authenticated,
                    "key_id": authentication.key_id,
                    "principal": authentication.principal,
                    "payload_sha256": authentication.payload_sha256,
                    "trust_store_sha256": trust_store_sha256,
                    "errors": list(authentication.errors),
                }
                owner_authenticated = authentication.authenticated
            except (OSError, ContractError) as exc:
                event["owner_authentication"] = {
                    "authenticated": False,
                    "errors": [str(exc)],
                }
        blockers = list(
            execution_gate_blockers(
                assessment=assessment,
                manifest=manifest,
                supplied_manifest_sha256=supplied_sha256,
                owner_decision=decision,
                git_snapshot=git_snapshot,
                nodeid=nodeid,
                argv=argv,
                previous_attempts=0,
                attempt_number=1,
                destination_exists=_destination_exists(root, manifest),
                owner_authenticated=owner_authenticated,
            )
        )
        blockers.extend(f"MANIFEST_INPUT_IDENTITY:{error}" for error in input_errors)
        if decision is not None and not owner_authenticated:
            auth_errors = event.get("owner_authentication", {}).get("errors", [])
            if any("trust root" in error.lower() or "trust-store" in error.lower() for error in auth_errors):
                blockers.append("OWNER_TRUST_ROOT_UNAVAILABLE")
        event["blockers"] = list(dict.fromkeys(blockers))
    except (OSError, ContractError) as exc:
        event["blockers"] = ["INPUT_INVALID", str(exc)]
    try:
        refusal_path = record_refusal(DEFAULT_AUDIT_DIRECTORY, event, allowed_root=REPOSITORY_ROOT)
        event["refusal_record"] = str(refusal_path)
    except (OSError, ContractError) as exc:
        event["refusal_record_error"] = str(exc)
    _json_print(event, stream=sys.stderr)
    return 3


def _log_execute_argument_refusal(blocker: str) -> None:
    event: dict[str, Any] = {
        "mode": "EXECUTE",
        "event": "DENY_EXECUTION",
        "execution_started": False,
        "blockers": [blocker],
    }
    try:
        event["refusal_record"] = str(record_refusal(DEFAULT_AUDIT_DIRECTORY, event, allowed_root=REPOSITORY_ROOT))
    except (OSError, ContractError) as exc:
        event["refusal_record_error"] = f"{type(exc).__name__}: {exc}"
    _json_print(event, stream=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WP12 fail-closed preparation and runner self-test utility")
    parser.add_argument("--mode", choices=("VALIDATE", "SELF_TEST", "SYNC", "EXECUTE"), required=True)
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--owner-decision", type=Path)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--nodeid")
    parser.add_argument("--case", choices=("all", *sorted(FAKE_CASES)))
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
