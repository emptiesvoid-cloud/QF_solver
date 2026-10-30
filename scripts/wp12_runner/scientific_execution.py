"""Fail-closed authorization, preflight and one-unit WP12 pilot execution.

This module never treats the conversation-level agreement as authorization. The
only trusted entry point is a signed Owner decision verified against the
machine-pinned Windows trust store. Until the separate checkouts, isolated
environment, filesystem ACLs, administrator-controlled archive worker and
independent review are all verified, EXECUTE records a denial and starts no
scientific process.
"""

from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import csv
import io
from typing import Any, Mapping

from .contracts import (
    EXECUTION_SCHEMA_V4,
    OWNER_DECISION_SCHEMA,
    ContractError,
    assess_manifest,
    execution_gate_blockers,
    inspect_git,
    load_json,
    owner_decision_binding_errors,
    sha256_file,
    safe_repo_relative_path,
    validate_manifest_schema,
    verify_file_hashes,
)
from .import_probe import probe_solver_import
from .inline_fixtures import PILOT_NODEID, fixture_sha256, projection_pilot_fixture
from .owner_trust import load_machine_trust_store, verify_owner_decision
from .runtime_probe import probe_runtime_environment, runtime_environment_mismatches


_ARCHIVE_TASK_QUERY = r"$ErrorActionPreference='Stop'; $t=Get-ScheduledTask -TaskPath '\QFSolverWP12\' -TaskName 'ArchiveWorker'; $a=$t.Actions | Select-Object -First 1; [Console]::WriteLine(([ordered]@{state=$t.State.ToString(); principal=$t.Principal.UserId; execute=$a.Execute; arguments=$a.Arguments} | ConvertTo-Json -Compress))"


def _archive_worker_blockers(
    runner_root: Path,
    archive: Mapping[str, Any],
    request_root: Path | None,
    evidence_root: Path | None,
    archive_root: Path | None,
    owner_decision_root: Path | None,
    expected_python: Path | None,
    expected_manifest_sha256: str,
) -> tuple[str, ...]:
    if archive.get("status") != "CONFIGURED":
        return ("INDEPENDENT_EVIDENCE_ARCHIVE_NOT_CONFIGURED",)
    blockers: list[str] = []
    # The current SYSTEM worker archives bytes only. This blocker remains
    # unconditional until a protected launcher observes the child itself.
    blockers.append("SYSTEM_WORKER_DOES_NOT_ATTEST_TEST_PROCESS")
    expected_task = r"\QFSolverWP12\ArchiveWorker"
    if archive.get("worker_task_name") != expected_task:
        blockers.append("ARCHIVE_WORKER_TASK_NAME_MISMATCH")
    worker_path = _safe_path(archive.get("worker_script_path"))
    expected_path = (
        runner_root / "scripts" / "wp12_runner" / "windows" / "Invoke-WP12EvidenceArchiveWorker.ps1"
    ).resolve(strict=False)
    if worker_path is None or worker_path != expected_path:
        blockers.append("ARCHIVE_WORKER_SCRIPT_PATH_MISMATCH")
    elif sha256_file(worker_path) != archive.get("worker_script_sha256"):
        blockers.append("ARCHIVE_WORKER_SCRIPT_HASH_MISMATCH")
    verifier_path = _safe_path(archive.get("decision_verifier_script_path"))
    expected_verifier = (runner_root / "scripts" / "wp12_runner" / "owner_decision_verifier.py").resolve(strict=False)
    if verifier_path is None or verifier_path != expected_verifier:
        blockers.append("OWNER_DECISION_VERIFIER_PATH_MISMATCH")
    elif sha256_file(verifier_path) != archive.get("decision_verifier_script_sha256"):
        blockers.append("OWNER_DECISION_VERIFIER_HASH_MISMATCH")
    trusted_modules = (
        ("scripts/wp12_runner/contracts.py", "contracts_script_sha256"),
        ("scripts/wp12_runner/owner_trust.py", "owner_trust_script_sha256"),
        ("scripts/wp12_owner_canonicalization.py", "canonicalization_script_sha256"),
    )
    for relative, field in trusted_modules:
        module_path = (runner_root / Path(relative)).resolve(strict=False)
        declared_digest = archive.get(field)
        if not module_path.is_file() or not isinstance(declared_digest, str):
            blockers.append(f"OWNER_VERIFIER_DEPENDENCY_PIN_MISSING:{relative}")
        elif sha256_file(module_path) != declared_digest:
            blockers.append(f"OWNER_VERIFIER_DEPENDENCY_HASH_MISMATCH:{relative}")
    declared_python = _safe_path(archive.get("python_executable"))
    if expected_python is None or declared_python != expected_python:
        blockers.append("ARCHIVE_VERIFIER_PYTHON_PATH_MISMATCH")
    elif sha256_file(declared_python) != archive.get("python_executable_sha256"):
        blockers.append("ARCHIVE_VERIFIER_PYTHON_HASH_MISMATCH")
    manifest_path = _safe_path(archive.get("manifest_path"))
    if manifest_path is None or owner_decision_root is None:
        blockers.append("ARCHIVE_WORKER_MANIFEST_PATH_INVALID")
    elif not manifest_path.is_relative_to(owner_decision_root / "WP12-1-PILOT-001"):
        blockers.append("ARCHIVE_WORKER_MANIFEST_OUTSIDE_PROTECTED_DECISION_ROOT")
    elif not manifest_path.is_file():
        blockers.append("ARCHIVE_WORKER_MANIFEST_ABSENT")
    elif sha256_file(manifest_path) != expected_manifest_sha256:
        blockers.append("ARCHIVE_WORKER_MANIFEST_HASH_MISMATCH")
    if request_root is None or not os.access(request_root, os.W_OK):
        blockers.append("ARCHIVE_REQUEST_ROOT_NOT_WRITABLE")
    if owner_decision_root is None or os.access(owner_decision_root, os.W_OK):
        blockers.append("OWNER_DECISION_ROOT_NOT_PROTECTED")
    if os.name != "nt":
        blockers.append("WINDOWS_ARCHIVE_WORKER_REQUIRED")
        return tuple(blockers)
    powershell = (
        Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    )
    try:
        completed = subprocess.run(
            [str(powershell), "-NoProfile", "-NonInteractive", "-Command", _ARCHIVE_TASK_QUERY],
            capture_output=True,
            text=True,
            timeout=20,
            shell=False,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return tuple(blockers + ["ARCHIVE_WORKER_TASK_QUERY_FAILED"])
    if completed.returncode != 0:
        blockers.append("ARCHIVE_WORKER_TASK_NOT_REGISTERED")
        return tuple(blockers)
    try:
        task = json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return tuple(blockers + ["ARCHIVE_WORKER_TASK_REPORT_INVALID"])
    if (
        not isinstance(task, Mapping)
        or task.get("state") != "Running"
        or str(task.get("principal", "")).upper() != "SYSTEM"
    ):
        blockers.append("ARCHIVE_WORKER_NOT_RUNNING_AS_SYSTEM")
    arguments = str(task.get("arguments", "")) if isinstance(task, Mapping) else ""
    if worker_path is not None:
        expected_arguments = [
            str(worker_path),
            str(request_root) if request_root is not None else "",
            str(evidence_root) if evidence_root is not None else "",
            str(archive_root) if archive_root is not None else "",
            str(owner_decision_root) if owner_decision_root is not None else "",
            str(declared_python) if declared_python is not None else "",
            str(archive.get("python_executable_sha256", "")),
            str(archive.get("decision_verifier_script_sha256", "")),
            str(archive.get("contracts_script_sha256", "")),
            str(archive.get("owner_trust_script_sha256", "")),
            str(archive.get("canonicalization_script_sha256", "")),
            str(archive.get("worker_script_sha256", "")),
            str(archive.get("manifest_path", "")),
            expected_manifest_sha256,
        ]
        for required in expected_arguments:
            if not required:
                blockers.append("ARCHIVE_WORKER_ROOT_CONFIGURATION_MISSING")
                continue
            if required.casefold() not in arguments.casefold():
                blockers.append("ARCHIVE_WORKER_TASK_ACTION_MISMATCH")
                break
    return tuple(dict.fromkeys(blockers))


def _denial(*blockers: str, campaign_id: str | None = None) -> dict[str, Any]:
    return {
        "mode": "EXECUTE",
        "campaign_id": campaign_id,
        "event": "DENY_EXECUTION",
        "status": "DENY_EXECUTION",
        "execution_started": False,
        "attempt_reserved": False,
        "blockers": list(dict.fromkeys(blockers)),
    }


def _windows_identity_blockers(expected_account: str, expected_sid: str) -> tuple[str, ...]:
    if os.name != "nt":
        return ("WINDOWS_RUNNER_REQUIRED",)
    try:
        import ctypes
        from ctypes import wintypes

        username_buffer = ctypes.create_unicode_buffer(256)
        username_length = ctypes.c_ulong(len(username_buffer))
        if not ctypes.windll.advapi32.GetUserNameW(username_buffer, ctypes.byref(username_length)):
            return ("WINDOWS_ACCOUNT_IDENTITY_UNAVAILABLE",)
        account_name = username_buffer.value.rsplit("\\", 1)[-1]
        if account_name.casefold() != expected_account.casefold():
            return ("DEDICATED_RUNNER_ACCOUNT_MISMATCH",)
        if not isinstance(expected_sid, str) or not expected_sid.startswith("S-1-"):
            return ("DEDICATED_RUNNER_SID_NOT_PINNED",)

        class _SidAndAttributes(ctypes.Structure):
            _fields_ = [("sid", ctypes.c_void_p), ("attributes", wintypes.DWORD)]

        class _TokenUser(ctypes.Structure):
            _fields_ = [("user", _SidAndAttributes)]

        kernel = ctypes.windll.kernel32
        advapi = ctypes.windll.advapi32
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        kernel.LocalFree.argtypes = [wintypes.HANDLE]
        advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        advapi.OpenProcessToken.restype = wintypes.BOOL
        advapi.GetTokenInformation.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        advapi.GetTokenInformation.restype = wintypes.BOOL
        advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
        advapi.ConvertSidToStringSidW.restype = wintypes.BOOL
        token = wintypes.HANDLE()
        if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
            return ("WINDOWS_ACCOUNT_SID_UNAVAILABLE",)
        try:
            required = wintypes.DWORD()
            advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(required))
            if required.value < ctypes.sizeof(_TokenUser):
                return ("WINDOWS_ACCOUNT_SID_UNAVAILABLE",)
            buffer = ctypes.create_string_buffer(required.value)
            if not advapi.GetTokenInformation(token, 1, buffer, required.value, ctypes.byref(required)):
                return ("WINDOWS_ACCOUNT_SID_UNAVAILABLE",)
            token_user = ctypes.cast(buffer, ctypes.POINTER(_TokenUser)).contents
            sid_buffer = wintypes.LPWSTR()
            if not advapi.ConvertSidToStringSidW(token_user.user.sid, ctypes.byref(sid_buffer)):
                return ("WINDOWS_ACCOUNT_SID_UNAVAILABLE",)
            try:
                actual_sid = sid_buffer.value
            finally:
                kernel.LocalFree(ctypes.cast(sid_buffer, wintypes.HANDLE))
        finally:
            kernel.CloseHandle(token)
        if actual_sid.casefold() != expected_sid.casefold():
            return ("DEDICATED_RUNNER_SID_MISMATCH",)
        system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        group_report = subprocess.run(
            [str(system_root / "System32" / "whoami.exe"), "/groups", "/fo", "csv", "/nh"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            shell=False,
            check=False,
        )
        if group_report.returncode != 0:
            return ("WINDOWS_ACCOUNT_GROUP_MEMBERSHIP_UNAVAILABLE",)
        try:
            group_rows = list(csv.reader(io.StringIO(group_report.stdout)))
        except csv.Error:
            return ("WINDOWS_ACCOUNT_GROUP_MEMBERSHIP_UNAVAILABLE",)
        if any("S-1-5-32-544" in {field.strip().casefold() for field in row} for row in group_rows):
            return ("RUNNER_ACCOUNT_BELONGS_TO_ADMINISTRATORS",)
        if ctypes.windll.shell32.IsUserAnAdmin():
            return ("RUNNER_ACCOUNT_IS_ADMINISTRATOR",)
    except Exception:
        return ("WINDOWS_ACCOUNT_PRIVILEGE_CHECK_UNAVAILABLE",)
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
            build = int(winreg.QueryValueEx(key, "CurrentBuildNumber")[0])
            ubr = int(winreg.QueryValueEx(key, "UBR")[0])
    except (OSError, ValueError):
        return ("WINDOWS_PATCH_LEVEL_UNAVAILABLE",)
    if build != 19045 or ubr < 7807:
        return ("WINDOWS_10_ENTERPRISE_ESU_BASELINE_NOT_MET",)
    return ()


def _safe_path(path_value: Any, *, must_exist: bool = True) -> Path | None:
    if not isinstance(path_value, str):
        return None
    path = Path(path_value)
    if not path.is_absolute():
        return None
    try:
        lexical = Path(os.path.abspath(path))
        current = Path(lexical.anchor)
        for part in lexical.parts[1:]:
            current = current / part
            if current.is_symlink() or bool(getattr(current, "is_junction", lambda: False)()):
                return None
        resolved = path.resolve(strict=must_exist)
    except (OSError, RuntimeError):
        return None
    if resolved.is_symlink() or bool(getattr(resolved, "is_junction", lambda: False)()):
        return None
    current = Path(resolved.anchor)
    for part in resolved.parts[1:]:
        current = current / part
        if current.is_symlink() or bool(getattr(current, "is_junction", lambda: False)()):
            return None
    return resolved


def _pilot_inline_fixture_errors(
    science_root: Path,
    manifest: Mapping[str, Any],
    context: Mapping[str, Any],
    nodeid: str,
) -> tuple[str, ...]:
    """Bind the frozen inline fixture to the exact test source without imports."""
    summary = context.get("inline_fixture")
    fixtures = manifest.get("fixtures")
    inline = fixtures.get("inline") if isinstance(fixtures, Mapping) else None
    if not isinstance(summary, Mapping) or not isinstance(inline, list) or len(inline) != 1:
        return ("PILOT_INLINE_FIXTURE_IDENTITY_MISSING",)
    spec = inline[0]
    if not isinstance(spec, Mapping):
        return ("PILOT_INLINE_FIXTURE_IDENTITY_MALFORMED",)
    errors: list[str] = []
    source_file = spec.get("source_file")
    if nodeid != PILOT_NODEID or spec.get("nodeid") != nodeid:
        errors.append("PILOT_INLINE_FIXTURE_NODEID_MISMATCH")
    if (
        not isinstance(source_file, str)
        or not safe_repo_relative_path(source_file)
        or source_file != nodeid.partition("::")[0]
    ):
        errors.append("PILOT_INLINE_FIXTURE_SOURCE_FILE_MISMATCH")
        return tuple(errors)
    source_path = science_root.joinpath(*Path(source_file).parts)
    safe_source = _safe_path(str(source_path))
    if safe_source is None or not safe_source.is_relative_to(science_root):
        return tuple(errors + ["PILOT_INLINE_FIXTURE_SOURCE_FILE_UNSAFE"])
    try:
        source_bytes = safe_source.read_bytes()
        source_digest = sha256_file(safe_source)
        code_identity = manifest.get("code_identity")
        test_inventory = code_identity.get("test_files_sha256") if isinstance(code_identity, Mapping) else None
        fixture_inventory = code_identity.get("fixture_files_sha256") if isinstance(code_identity, Mapping) else None
        if source_digest != spec.get("source_file_sha256"):
            errors.append("PILOT_INLINE_FIXTURE_SOURCE_HASH_MISMATCH")
        if not isinstance(test_inventory, Mapping) or test_inventory.get(source_file) != source_digest:
            errors.append("PILOT_INLINE_FIXTURE_NOT_BOUND_TO_TEST_INVENTORY")
        if not isinstance(fixture_inventory, Mapping) or fixture_inventory.get(source_file) != source_digest:
            errors.append("PILOT_INLINE_FIXTURE_NOT_BOUND_TO_FIXTURE_INVENTORY")
        fixture = projection_pilot_fixture(source_bytes)
    except (OSError, ContractError, KeyError, TypeError, ValueError):
        return tuple(errors + ["PILOT_INLINE_FIXTURE_COULD_NOT_BE_VERIFIED"])
    if (
        fixture.get("fixture_id") != spec.get("id")
        or spec.get("canonicalization") != "qf-wp12-inline-fixture-v1"
        or fixture_sha256(fixture) != spec.get("sha256")
        or summary.get("schema") != "qf-wp12-inline-fixture-v1"
        or summary.get("fixture_id") != spec.get("id")
        or summary.get("canonicalization") != spec.get("canonicalization")
        or summary.get("sha256") != spec.get("sha256")
    ):
        errors.append("PILOT_INLINE_FIXTURE_CANONICAL_HASH_MISMATCH")
    return tuple(dict.fromkeys(errors))


def _read_only_tree_errors(path: Path) -> tuple[str, ...]:
    errors: list[str] = []
    try:
        candidates = [path, *path.rglob("*")]
    except OSError:
        return ("READ_ONLY_TREE_SCAN_FAILED",)
    for candidate in candidates:
        if candidate.is_symlink() or bool(getattr(candidate, "is_junction", lambda: False)()):
            errors.append("READ_ONLY_TREE_CONTAINS_REPARSE_POINT")
            break
        if os.access(candidate, os.W_OK):
            errors.append("RUNNER_CAN_WRITE_PROTECTED_TREE")
            break
    return tuple(errors)


def _verified_remote_commit(runner_root: Path, expected_commit: str) -> tuple[str, ...]:
    try:
        origin = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=runner_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
            shell=False,
        )
        if origin.returncode or origin.stdout.strip() not in {
            "https://github.com/emptiesvoid-cloud/QF_solver.git",
            "https://github.com/emptiesvoid-cloud/QF_solver",
        }:
            return ("RUNNER_ORIGIN_MISMATCH",)
        advertised = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", "refs/heads/emptiesvoids-cloud/0.2.12"],
            cwd=runner_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ("REMOTE_IDENTITY_UNAVAILABLE",)
    if advertised.returncode:
        return ("REMOTE_IDENTITY_UNAVAILABLE",)
    rows = [line.split("\t") for line in advertised.stdout.splitlines() if line]
    if len(rows) != 1 or rows[0][1] != "refs/heads/emptiesvoids-cloud/0.2.12":
        return ("REMOTE_TARGET_BRANCH_UNAVAILABLE_OR_AMBIGUOUS",)
    advertised_commit = rows[0][0]
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", expected_commit, advertised_commit],
        cwd=runner_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
        shell=False,
    )
    if ancestry.returncode == 1:
        return ("SIGNED_RUNNER_COMMIT_NOT_ANCESTOR_OF_ADVERTISED_REMOTE_HEAD",)
    if ancestry.returncode != 0:
        return ("REMOTE_ADVERTISED_COMMIT_NOT_AVAILABLE_LOCALLY",)
    return ()


def _execute_pilot_preflight(
    *,
    runner_root: Path,
    manifest_path: Path,
    owner_decision_path: Path | None,
    supplied_manifest_sha256: str | None,
) -> dict[str, Any]:
    """Authenticate first, then compare all declared identities before any attempt."""
    if owner_decision_path is None:
        return _denial("OWNER_DECISION_ABSENT")
    try:
        trusted_keys, trust_store_sha256 = load_machine_trust_store(runner_root)
    except (OSError, ContractError):
        return _denial("OWNER_TRUST_STORE_NOT_CONFIGURED_OR_INVALID")

    try:
        decision, decision_sha256 = load_json(owner_decision_path)
    except (OSError, ContractError):
        return _denial("OWNER_DECISION_UNAVAILABLE_OR_INVALID")
    if decision.get("schema") != OWNER_DECISION_SCHEMA:
        return _denial("OWNER_DECISION_SCHEMA_V4_WITH_RUN_BINDING_REQUIRED")
    expected_manifest_sha256 = decision.get("manifest_sha256")
    campaign_id = decision.get("campaign_id") if isinstance(decision.get("campaign_id"), str) else None
    science_identity = decision.get("scientific_identity")
    runner_identity = decision.get("runner_identity")
    if (
        not isinstance(expected_manifest_sha256, str)
        or not isinstance(science_identity, Mapping)
        or not isinstance(runner_identity, Mapping)
    ):
        return _denial("OWNER_DECISION_BINDING_FIELDS_MISSING", campaign_id=campaign_id)
    authentication = verify_owner_decision(
        decision,
        trusted_keys=trusted_keys,
        manifest_sha256=expected_manifest_sha256,
        expected_campaign_id=campaign_id or "",
        expected_scientific_identity=dict(science_identity),
        expected_runner_identity=dict(runner_identity),
    )
    if not authentication.authenticated:
        return _denial("OWNER_DECISION_AUTHENTICATION_FAILED", *authentication.errors, campaign_id=campaign_id)
    if supplied_manifest_sha256 != expected_manifest_sha256:
        return _denial("CLI_MANIFEST_DIGEST_DIFFERS_FROM_SIGNED_DECISION", campaign_id=campaign_id)

    try:
        manifest, manifest_sha256 = load_json(manifest_path)
    except (OSError, ContractError):
        return _denial("SIGNED_MANIFEST_UNAVAILABLE_OR_INVALID", campaign_id=campaign_id)
    if manifest_sha256 != expected_manifest_sha256:
        return _denial("MANIFEST_SHA256_DIFFERS_FROM_OWNER_DECISION", campaign_id=campaign_id)
    if manifest.get("schema") != EXECUTION_SCHEMA_V4:
        return _denial("EXECUTABLE_MANIFEST_V4_REQUIRED", campaign_id=campaign_id)

    structural_errors = validate_manifest_schema(manifest)
    assessment = assess_manifest(manifest, manifest_sha256)
    context = manifest.get("execution_context")
    tests = manifest.get("tests")
    nodeid = tests.get("nodeid") if isinstance(tests, Mapping) else None
    argv = tests.get("argv") if isinstance(tests, Mapping) else None
    if not isinstance(context, Mapping) or not isinstance(nodeid, str) or not isinstance(argv, list):
        return _denial("EXECUTION_CONTEXT_INCOMPLETE", campaign_id=campaign_id)

    blockers: list[str] = list(structural_errors)
    blockers.extend(assessment.structural_errors)
    blockers.extend(
        blocker for blocker in assessment.execution_blockers if blocker != "SEPARATE_OWNER_DECISION_REQUIRED"
    )
    blockers.extend(owner_decision_binding_errors(decision, manifest, manifest_sha256))
    if decision_sha256 == "":
        blockers.append("OWNER_DECISION_IDENTITY_UNAVAILABLE")

    science_data = context.get("science_checkout")
    runner_data = context.get("runner_checkout")
    science_root = _safe_path(science_data.get("path") if isinstance(science_data, Mapping) else None)
    expected_runner = _safe_path(runner_data.get("path") if isinstance(runner_data, Mapping) else None)
    actual_runner = _safe_path(str(runner_root))
    if science_root is None:
        blockers.append("SCIENTIFIC_CHECKOUT_PATH_INVALID")
    if expected_runner is None or actual_runner is None or expected_runner != actual_runner:
        blockers.append("RUNNER_CHECKOUT_PATH_MISMATCH")
    evidence_root = _safe_path(context.get("evidence_root"))
    temporary_root = _safe_path(context.get("temporary_root"))
    destination_path = _safe_path(context.get("destination_path"), must_exist=False)
    archive_context = context.get("archive")
    owner_decision_root = _safe_path(
        archive_context.get("owner_decision_root") if isinstance(archive_context, Mapping) else None
    )
    if owner_decision_root is None:
        blockers.append("OWNER_DECISION_ROOT_NOT_CONFIGURED")
    else:
        decision_id = decision.get("decision_id")
        if not isinstance(decision_id, str):
            blockers.append("OWNER_DECISION_ID_MISSING")
        else:
            expected_decision_path = owner_decision_root / campaign_id / f"{decision_id}.json"
            try:
                actual_decision_path = owner_decision_path.resolve(strict=True)
                if (
                    owner_decision_path.is_symlink()
                    or bool(getattr(owner_decision_path, "is_junction", lambda: False)())
                    or actual_decision_path != expected_decision_path.resolve(strict=True)
                ):
                    blockers.append("OWNER_DECISION_NOT_IN_PROTECTED_DECISION_ROOT")
            except (OSError, RuntimeError):
                blockers.append("OWNER_DECISION_NOT_IN_PROTECTED_DECISION_ROOT")
    protected_manifest_path = (
        _safe_path(archive_context.get("manifest_path")) if isinstance(archive_context, Mapping) else None
    )
    actual_manifest_path = _safe_path(str(manifest_path))
    if (
        protected_manifest_path is None
        or actual_manifest_path is None
        or protected_manifest_path != actual_manifest_path
    ):
        blockers.append("MANIFEST_NOT_LOADED_FROM_PROTECTED_OWNER_ROOT")
    archive_request_root = _safe_path(
        archive_context.get("request_root") if isinstance(archive_context, Mapping) else None
    )
    archive_root = _safe_path(archive_context.get("destination") if isinstance(archive_context, Mapping) else None)
    if evidence_root is None or temporary_root is None or destination_path is None:
        blockers.append("EVIDENCE_OR_TEMPORARY_PATH_INVALID")
    elif not destination_path.is_relative_to(evidence_root):
        blockers.append("EVIDENCE_DESTINATION_OUTSIDE_EXCLUSIVE_ROOT")
    declared_destination = manifest.get("destination")
    if evidence_root is not None and destination_path is not None and isinstance(declared_destination, str):
        destination_parts = PurePosixPath(declared_destination).parts
        if len(destination_parts) != 5 or destination_parts[:3] != (
            "qualification",
            "0_2_12",
            "wp12_evidence",
        ):
            blockers.append("MANIFEST_EVIDENCE_DESTINATION_INVALID")
        elif destination_path != evidence_root.joinpath(*destination_parts[3:]):
            blockers.append("ABSOLUTE_EVIDENCE_DESTINATION_DIFFERS_FROM_SIGNED_MANIFEST")
    for label, protected in (
        ("science", science_root),
        ("runner", expected_runner),
        ("venv", _safe_path(context.get("venv_root"))),
    ):
        if destination_path is not None and protected is not None and destination_path.is_relative_to(protected):
            blockers.append(f"EVIDENCE_DESTINATION_INSIDE_{label.upper()}_CHECKOUT")
    for label, protected in (("ARCHIVE", archive_root), ("ARCHIVE_REQUEST", archive_request_root)):
        if destination_path is not None and protected is not None and destination_path.is_relative_to(protected):
            blockers.append(f"EVIDENCE_DESTINATION_INSIDE_{label}_ROOT")
    science_snapshot = None
    runner_snapshot = None
    if science_root is not None:
        try:
            science_snapshot = inspect_git(science_root)
        except (OSError, ContractError):
            blockers.append("SCIENTIFIC_GIT_IDENTITY_UNAVAILABLE")
    if actual_runner is not None:
        try:
            runner_snapshot = inspect_git(actual_runner)
        except (OSError, ContractError):
            blockers.append("RUNNER_GIT_IDENTITY_UNAVAILABLE")
    if science_snapshot is not None and isinstance(science_data, Mapping):
        if (
            science_snapshot.commit != science_data.get("commit")
            or science_snapshot.tree != science_data.get("git_tree")
            or not science_snapshot.clean
        ):
            blockers.append("SCIENTIFIC_CHECKOUT_IDENTITY_OR_CLEANLINESS_MISMATCH")
    if runner_snapshot is not None:
        blockers.extend(
            execution_gate_blockers(
                assessment=assessment,
                manifest=manifest,
                supplied_manifest_sha256=supplied_manifest_sha256,
                owner_decision=decision,
                git_snapshot=runner_snapshot,
                nodeid=nodeid,
                argv=argv,
                previous_attempts=0,
                attempt_number=1,
                destination_exists=(
                    destination_path is None
                    or destination_path.exists()
                    or destination_path.is_symlink()
                    or bool(getattr(destination_path, "is_junction", lambda: False)())
                ),
                owner_authenticated=True,
            )
        )
        if isinstance(runner_data, Mapping) and (
            runner_snapshot.commit != runner_data.get("commit")
            or runner_snapshot.tree != runner_data.get("git_tree")
            or not runner_snapshot.clean
        ):
            blockers.append("RUNNER_CHECKOUT_IDENTITY_OR_CLEANLINESS_MISMATCH")
        blockers.extend(_verified_remote_commit(actual_runner, runner_snapshot.commit))

    if science_root is not None:
        for inventory_name in ("source_files_sha256", "test_files_sha256", "fixture_files_sha256"):
            inventory = manifest.get("code_identity", {}).get(inventory_name, {})
            if isinstance(inventory, Mapping):
                blockers.extend(verify_file_hashes(science_root, inventory))
        blockers.extend(_pilot_inline_fixture_errors(science_root, manifest, context, nodeid))
    if actual_runner is not None:
        lock_path = actual_runner / "requirements" / "wp12-windows-lock.txt"
        try:
            if sha256_file(lock_path) != context.get("requirements_lock_sha256"):
                blockers.append("WP12_REQUIREMENTS_LOCK_HASH_MISMATCH")
        except OSError:
            blockers.append("WP12_REQUIREMENTS_LOCK_UNAVAILABLE")
    runner_hashes = context.get("runner_files_sha256")
    if actual_runner is not None and isinstance(runner_hashes, Mapping):
        blockers.extend(verify_file_hashes(actual_runner, runner_hashes))
        plugin_relative = "scripts/wp12_runner/pytest_provenance_plugin.py"
        declared_plugin = _safe_path(context.get("plugin_path"))
        expected_plugin = (actual_runner / plugin_relative).resolve(strict=False)
        if declared_plugin is None or declared_plugin != expected_plugin:
            blockers.append("PROVENANCE_PLUGIN_PATH_DIFFERS_FROM_RUNNER_CHECKOUT")
        elif runner_hashes.get(plugin_relative) != sha256_file(expected_plugin):
            blockers.append("PROVENANCE_PLUGIN_HASH_NOT_PINNED")
        expected_pythonpath = [str(actual_runner), str(science_root / "src")] if science_root is not None else []
        if context.get("pythonpath") != expected_pythonpath:
            blockers.append("CHILD_PYTHONPATH_DIFFERS_FROM_APPROVED_CHECKOUTS")

    expected_python = _safe_path(context.get("python_executable"))
    venv_root = _safe_path(context.get("venv_root"))
    python_base_root = _safe_path(context.get("python_base_root"))
    observed_environment: Mapping[str, Any] | None = None
    import_report: Mapping[str, Any] | None = None
    if expected_python is None or venv_root is None or python_base_root is None:
        blockers.append("PINNED_PYTHON_PATH_INVALID")
    elif not expected_python.is_relative_to(venv_root):
        blockers.append("PYTHON_EXECUTABLE_OUTSIDE_PINNED_VENV")
    elif expected_python != Path(str(manifest.get("environment", {}).get("python_executable_path", ""))).resolve(
        strict=False
    ):
        blockers.append("PYTHON_EXECUTABLE_DIFFERS_FROM_DECLARATION")
    else:
        try:
            observed_environment = probe_runtime_environment(
                expected_python,
                thread_environment=context.get("thread_environment", {}),
            )
            blockers.extend(
                runtime_environment_mismatches(
                    observed_environment,
                    expected_python_sha256=manifest["environment"]["python_executable_sha256"],
                    expected_python_version=manifest["environment"]["python_version"],
                    expected_packages=context.get("expected_packages", {}),
                    expected_native_hashes=context.get("expected_native_libraries_sha256", {}),
                    expected_threads=context.get("thread_environment", {}),
                    expected_venv_root=venv_root,
                    expected_base_root=python_base_root,
                )
            )
        except (OSError, ContractError, KeyError, subprocess.TimeoutExpired):
            blockers.append("PINNED_PYTHON_ENVIRONMENT_PROBE_FAILED")
    if science_root is not None and expected_python is not None and actual_runner is not None:
        try:
            import_report = probe_solver_import(expected_python, science_root)
            if import_report.get("version") is None:
                blockers.append("SOLVER_IMPORT_VERSION_UNAVAILABLE")
            if import_report.get("installed_qf_solver_distribution") is not None:
                blockers.append("INSTALLED_QF_SOLVER_DISTRIBUTION_CONFLICTS_WITH_SOURCE_CHECKOUT")
            if import_report.get("fem_or_analysis_api_called") is not False:
                blockers.append("IMPORT_DIAGNOSTIC_CALLED_ANALYSIS_API")
        except (OSError, ContractError, subprocess.TimeoutExpired):
            blockers.append("SOLVER_SOURCE_IMPORT_ORIGIN_NOT_VERIFIED")

    isolation_assessment = manifest.get("isolation_assessment")
    if not isinstance(isolation_assessment, Mapping):
        blockers.append("RUNNER_ACCOUNT_IDENTITY_NOT_PINNED")
    else:
        expected_account = isolation_assessment.get("runner_account")
        expected_sid = isolation_assessment.get("runner_account_sid")
        if not isinstance(expected_account, str) or not isinstance(expected_sid, str):
            blockers.append("RUNNER_ACCOUNT_IDENTITY_NOT_PINNED")
        else:
            blockers.extend(_windows_identity_blockers(expected_account, expected_sid))
    for label, protected in (
        ("SCIENTIFIC", science_root),
        ("RUNNER", expected_runner),
        ("PYTHON", venv_root),
        ("PYTHON_BASE", python_base_root),
        ("HISTORICAL_ARCHIVE", science_root / "qualification" / "0_2_11" if science_root else None),
        ("SEALED_ARCHIVE", archive_root),
        ("OWNER_DECISION", owner_decision_root),
    ):
        if protected is not None and protected.is_dir():
            if _read_only_tree_errors(protected):
                blockers.append(f"{label}_TREE_NOT_READ_ONLY_TO_RUNNER")
    for label, writable in (
        ("EVIDENCE", evidence_root),
        ("TEMPORARY", temporary_root),
        ("ARCHIVE_REQUEST", archive_request_root),
    ):
        if writable is not None and not os.access(writable, os.W_OK):
            blockers.append(f"{label}_ROOT_NOT_WRITABLE_TO_RUNNER")
    if archive_root is not None and os.access(archive_root, os.W_OK):
        blockers.append("SEALED_ARCHIVE_ROOT_WRITABLE_TO_RUNNER")
    resource_limits = manifest.get("resource_limits")
    enforcement = resource_limits.get("enforcement") if isinstance(resource_limits, Mapping) else None
    if isinstance(enforcement, Mapping):
        hard_supported = {"wall", "cpu", "memory", "process_tree", "logs"}
        for control, strength in enforcement.items():
            if strength == "hard" and control not in hard_supported:
                blockers.append(f"HARD_RESOURCE_LIMIT_NOT_IMPLEMENTED:{control}")
    archive = context.get("archive")
    if isinstance(archive, Mapping) and actual_runner is not None:
        blockers.extend(
            _archive_worker_blockers(
                actual_runner,
                archive,
                archive_request_root,
                evidence_root,
                archive_root,
                owner_decision_root,
                expected_python,
                manifest_sha256,
            )
        )
    else:
        blockers.append("INDEPENDENT_EVIDENCE_ARCHIVE_NOT_CONFIGURED")
    isolation = context.get("isolation_attestation")
    review = context.get("security_review")
    if not isinstance(isolation, Mapping) or isolation.get("status") != "VERIFIED":
        blockers.append("WINDOWS_ISOLATION_NOT_VERIFIED")
    if not isinstance(review, Mapping) or review.get("status") != "INDEPENDENTLY_REVIEWED":
        blockers.append("INDEPENDENT_SECURITY_REVIEW_NOT_RECORDED")
    if not os.name == "nt":
        blockers.append("WINDOWS_JOB_OBJECT_EXECUTION_REQUIRED")
    else:
        try:
            from .windows_job import windows_job_available

            if not windows_job_available():
                blockers.append("WINDOWS_JOB_OBJECT_UNAVAILABLE")
        except (ImportError, OSError):
            blockers.append("WINDOWS_JOB_OBJECT_UNAVAILABLE")

    unique_blockers = tuple(dict.fromkeys(blockers))
    if unique_blockers:
        return _denial(*unique_blockers, campaign_id=campaign_id)
    from .pilot_execution import execute_authenticated_pilot_unit

    execution_fingerprint = {
        "runtime": dict(observed_environment or {}),
        "solver_import": dict(import_report or {}),
        "trust_store_sha256": trust_store_sha256,
    }
    event = execute_authenticated_pilot_unit(
        manifest=manifest,
        manifest_sha256=manifest_sha256,
        owner_decision_sha256=decision_sha256,
        owner_decision_id=str(decision["decision_id"]),
        context=context,
        environment_report=execution_fingerprint,
    )
    event["trust_store_sha256"] = trust_store_sha256
    return event


def execute_pilot(
    *,
    runner_root: Path,
    manifest_path: Path,
    owner_decision_path: Path | None,
    supplied_manifest_sha256: str | None,
) -> dict[str, Any]:
    """Run authorization and preflight gates; deny without a genuine trust root."""
    try:
        return _execute_pilot_preflight(
            runner_root=runner_root,
            manifest_path=manifest_path,
            owner_decision_path=owner_decision_path,
            supplied_manifest_sha256=supplied_manifest_sha256,
        )
    except (OSError, ContractError, KeyError, TypeError, ValueError) as exc:
        return _denial(f"PREFLIGHT_ERROR:{type(exc).__name__}")
