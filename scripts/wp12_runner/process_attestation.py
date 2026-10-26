"""Synthetic child-process attestation for the WP12 runner.

This module is deliberately incapable of launching QF Solver or pytest. It
exercises the authorization -> fixed command -> observed child -> JUnit ->
create-only receipt chain using a checked-in fake child. The production pilot
entry point remains fail-closed until a separately protected SYSTEM broker
uses the same attestation contract with a dedicated-account token.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import stat
from typing import Any, Mapping

from .contracts import ContractError, sha256_bytes, sha256_file
from .evidence import verify_receipt, write_receipt
from .ledger import AttemptLedger
from .owner_trust import TrustedOwnerKey, verify_owner_decision
from .process import _terminate_tree, classify_pytest_junit


SYNTHETIC_CAMPAIGN_ID = "WP12-C-ATTESTATION-SYNTHETIC"
# These are authorization labels accepted by the existing Owner-decision
# schema. The attestor never passes them to pytest; it starts only the fixed
# ``attestation_fake_child.py`` script below.
SYNTHETIC_NODEIDS = {
    "tests/unit/test_wp12_process_attestation.py::test_success": "success",
    "tests/unit/test_wp12_process_attestation.py::test_nonzero": "nonzero",
    "tests/unit/test_wp12_process_attestation.py::test_no_junit": "no_junit",
    "tests/unit/test_wp12_process_attestation.py::test_contradictory_junit": "contradictory_junit",
    "tests/unit/test_wp12_process_attestation.py::test_junit_substitution": "junit_substitution",
    "tests/unit/test_wp12_process_attestation.py::test_timeout": "timeout",
    "tests/unit/test_wp12_process_attestation.py::test_descendant": "descendant",
}
_FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "wp12_runner" / "attestation_fake_child.py"
_MAX_STDOUT = 64 * 1024
_MAX_STDERR = 64 * 1024
_WALL_TIMEOUT_SECONDS = 3.0


@dataclass(frozen=True)
class SyntheticAttestationResult:
    status: str
    reason: str | None
    run_id: str | None
    receipt_path: str | None
    receipt_sha256: str | None
    process_attestation: Mapping[str, Any] | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "qf-wp12-synthetic-process-attestation-v1",
            "status": self.status,
            "reason": self.reason,
            "run_id": self.run_id,
            "receipt_path": self.receipt_path,
            "receipt_sha256": self.receipt_sha256,
            "process_attestation": dict(self.process_attestation) if self.process_attestation else None,
            "scientific_execution": False,
            "production_execution_enabled": False,
        }


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _owner_authentication_errors(
    *,
    decision: Mapping[str, Any],
    trusted_keys: Mapping[str, TrustedOwnerKey],
    manifest_sha256: str,
    expected_nodeid: str,
    runner_identity: Mapping[str, str],
    now: datetime | None,
) -> tuple[str, ...]:
    # The caller supplies an exact synthetic nodeid, never an argv or command.
    if not isinstance(expected_nodeid, str) or expected_nodeid not in SYNTHETIC_NODEIDS:
        return ("SYNTHETIC_NODEID_NOT_ALLOWLISTED",)
    nodeid = expected_nodeid
    if decision.get("campaign_id") != SYNTHETIC_CAMPAIGN_ID:
        return ("OWNER_DECISION_NOT_FOR_SYNTHETIC_CAMPAIGN",)
    if decision.get("nodeids") != [nodeid]:
        return ("OWNER_DECISION_NODEID_MISMATCH",)
    result = verify_owner_decision(
        decision,
        trusted_keys=trusted_keys,
        manifest_sha256=manifest_sha256,
        expected_campaign_id=SYNTHETIC_CAMPAIGN_ID,
        expected_scientific_identity={"commit": "0" * 40, "git_tree": "0" * 40},
        expected_runner_identity=dict(runner_identity),
        now=now,
    )
    return result.errors


def _process_user_identity(process: subprocess.Popen[bytes]) -> dict[str, str | int | None]:
    """Observe image, command, parent and OS identity from the parent handle."""
    import psutil

    observed = psutil.Process(process.pid)
    image = str(Path(observed.exe()).resolve(strict=True))
    command = observed.cmdline()
    parent_pid = observed.ppid()
    username = observed.username()
    identity: dict[str, str | int | None] = {
        "pid": process.pid,
        "parent_pid": parent_pid,
        "image_path": image,
        "image_sha256": sha256_file(Path(image)),
        "command_line": command,
        "username": username,
        "windows_user_sid": None,
        "created_epoch": observed.create_time(),
    }
    if os.name == "nt":
        identity["windows_user_sid"] = _process_user_sid(process)
    return identity


def _process_user_sid(process: subprocess.Popen[bytes]) -> str:
    """Read TokenUser from this exact child process handle on Windows."""
    import ctypes
    from ctypes import wintypes

    class SidAndAttributes(ctypes.Structure):
        _fields_ = [("sid", ctypes.c_void_p), ("attributes", wintypes.DWORD)]

    class TokenUser(ctypes.Structure):
        _fields_ = [("user", SidAndAttributes)]

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.OpenProcessToken.restype = wintypes.BOOL
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    advapi.GetTokenInformation.restype = wintypes.BOOL
    advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
    advapi.ConvertSidToStringSidW.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [wintypes.HLOCAL]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(wintypes.HANDLE(process._handle), 0x0008, ctypes.byref(token)):
        raise OSError(ctypes.get_last_error(), "OpenProcessToken failed for observed child")
    try:
        needed = wintypes.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(needed))
        if needed.value < ctypes.sizeof(TokenUser):
            raise ContractError("child TokenUser response is too small")
        buffer = ctypes.create_string_buffer(needed.value)
        if not advapi.GetTokenInformation(token, 1, buffer, needed.value, ctypes.byref(needed)):
            raise OSError(ctypes.get_last_error(), "GetTokenInformation failed for observed child")
        token_user = ctypes.cast(buffer, ctypes.POINTER(TokenUser)).contents
        output = wintypes.LPWSTR()
        if not advapi.ConvertSidToStringSidW(token_user.user.sid, ctypes.byref(output)):
            raise OSError(ctypes.get_last_error(), "ConvertSidToStringSidW failed for observed child")
        try:
            return str(output.value)
        finally:
            kernel.LocalFree(ctypes.cast(output, wintypes.HLOCAL))
    finally:
        kernel.CloseHandle(token)


def _write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _safe_directory_path(path: Path) -> Path:
    lexical = Path(os.path.abspath(path))
    current = Path(lexical.anchor)
    for part in lexical.parts[1:]:
        current = current / part
        if current.exists() and (
            current.is_symlink() or bool(getattr(current, "is_junction", lambda: False)())
        ):
            raise ContractError("synthetic evidence path contains a reparse point")
    return lexical.resolve(strict=False)


def verify_attestation_receipt(run_directory: Path) -> tuple[str, ...]:
    """Verify create-only receipt, sidecar and every archived byte."""
    issues = list(verify_receipt(run_directory))
    try:
        receipt = json.loads((run_directory / "receipt.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return tuple(issues + ["attestation receipt JSON is unreadable"])
    if not isinstance(receipt, Mapping) or receipt.get("schema") != "qf-solver-wp12-runner-receipt-v1":
        issues.append("attestation receipt schema is invalid")
    else:
        metadata = receipt.get("metadata")
        if not isinstance(metadata, Mapping) or metadata.get("synthetic_only") is not True:
            issues.append("attestation receipt is not marked synthetic-only")
        if not isinstance(metadata, Mapping) or metadata.get("process_attestation_verified") is not True:
            issues.append("attestation receipt lacks observed process identity")
    return tuple(issues)


def run_synthetic_attested_child(
    *,
    decision: Mapping[str, Any],
    trusted_keys: Mapping[str, TrustedOwnerKey],
    manifest_bytes: bytes,
    expected_manifest_sha256: str,
    nodeid: str,
    runner_identity: Mapping[str, str],
    evidence_root: Path,
    now: datetime | None = None,
) -> SyntheticAttestationResult:
    """Authenticate and supervise one fixed fake child, then seal its receipt.

    This entry point never accepts argv, executable, cwd, environment, JUnit
    destination, timeout or resource limits from its caller. The Owner
    decision may select only one of the synthetic nodeids in this module.
    """
    if nodeid not in SYNTHETIC_NODEIDS:
        return SyntheticAttestationResult("DENY_EXECUTION", "NODEID_NOT_IN_SYNTHETIC_ALLOWLIST", None, None, None, None)
    manifest_digest = sha256_bytes(manifest_bytes)
    if manifest_digest != expected_manifest_sha256:
        return SyntheticAttestationResult("DENY_EXECUTION", "MANIFEST_SHA256_MISMATCH", None, None, None, None)
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return SyntheticAttestationResult("DENY_EXECUTION", "SYNTHETIC_MANIFEST_INVALID", None, None, None, None)
    try:
        evidence_parent = _safe_directory_path(evidence_root.parent)
        resolved_evidence = _safe_directory_path(evidence_root)
    except (OSError, ContractError):
        return SyntheticAttestationResult("DENY_EXECUTION", "EVIDENCE_PATH_UNSAFE", None, None, None, None)
    if (
        not isinstance(manifest, Mapping)
        or manifest.get("schema") != "qf-wp12-synthetic-attestation-plan-v1"
        or manifest.get("campaign_id") != SYNTHETIC_CAMPAIGN_ID
        or manifest.get("nodeid") != nodeid
        or manifest.get("destination") != decision.get("destination")
        or manifest.get("run_id") != decision.get("run_id")
        or manifest.get("materialized_evidence_parent") != str(evidence_parent)
        or manifest.get("scientific_execution") is not False
        or manifest.get("owner_decision_required") is not True
    ):
        return SyntheticAttestationResult("DENY_EXECUTION", "SYNTHETIC_MANIFEST_SCOPE_INVALID", None, None, None, None)
    if decision.get("maximum_attempts") != 1 or decision.get("attempt_number") != 1:
        return SyntheticAttestationResult("DENY_EXECUTION", "SYNTHETIC_ATTEMPT_POLICY_INVALID", None, None, None, None)
    auth_errors = _owner_authentication_errors(
        decision=decision,
        trusted_keys=trusted_keys,
        manifest_sha256=manifest_digest,
        expected_nodeid=nodeid,
        runner_identity=runner_identity,
        now=now,
    )
    if auth_errors:
        return SyntheticAttestationResult("DENY_EXECUTION", ";".join(auth_errors), None, None, None, None)
    if os.name != "nt":
        return SyntheticAttestationResult(
            "DENY_EXECUTION", "SUSPENDED_WINDOWS_PROCESS_REQUIRED_FOR_ATTESTATION", None, None, None, None
        )
    if not _FIXTURE.is_file() or _FIXTURE.is_symlink() or bool(getattr(_FIXTURE, "is_junction", lambda: False)()):
        return SyntheticAttestationResult("INFRA_ERROR", "SYNTHETIC_CHILD_FIXTURE_UNSAFE_OR_MISSING", None, None, None, None)
    fixture_before = sha256_file(_FIXTURE)
    executable = Path(sys.executable).resolve(strict=True)
    executable_digest = sha256_file(executable)
    declared_inputs = manifest.get("inputs")
    declared_environment = manifest.get("environment")
    if (
        not isinstance(declared_inputs, Mapping)
        or declared_inputs.get("fake_child_sha256") != fixture_before
        or not isinstance(declared_environment, Mapping)
        or declared_environment.get("python_executable_sha256") != executable_digest
    ):
        return SyntheticAttestationResult("DENY_EXECUTION", "SYNTHETIC_INPUT_IDENTITY_MISMATCH", None, None, None, None)
    if evidence_root.exists() or evidence_root.is_symlink() or bool(getattr(evidence_root, "is_junction", lambda: False)()):
        return SyntheticAttestationResult("DENY_EXECUTION", "EVIDENCE_DESTINATION_ALREADY_EXISTS_OR_UNSAFE", None, None, None, None)

    run_id = decision.get("run_id")
    if not isinstance(run_id, str) or not run_id or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-" for character in run_id):
        return SyntheticAttestationResult("DENY_EXECUTION", "OWNER_RUN_ID_INVALID", None, None, None, None)
    if resolved_evidence != evidence_parent / run_id:
        return SyntheticAttestationResult("DENY_EXECUTION", "OWNER_DESTINATION_PATH_MISMATCH", None, None, None, None)
    work_parent = evidence_root.parent / f".wp12-c-stage-{run_id}"
    if work_parent.exists() or work_parent.is_symlink():
        return SyntheticAttestationResult("DENY_EXECUTION", "STAGING_DESTINATION_COLLISION", None, None, None, None)
    try:
        evidence_parent.mkdir(parents=True, exist_ok=True)
        if _safe_directory_path(evidence_parent) != evidence_parent:
            raise ContractError("synthetic evidence parent changed during reservation")
        ledger = AttemptLedger(evidence_parent / ".wp12-c-attempt-ledger.jsonl", allowed_root=evidence_parent)
        ledger.verify()
        decision_sha256 = sha256_bytes(_canonical(decision))
        environment_sha256 = sha256_bytes(_canonical(declared_environment))
        ledger.start_attempt(
            campaign_id=SYNTHETIC_CAMPAIGN_ID,
            manifest_sha256=manifest_digest,
            run_id=run_id,
            nodeid=nodeid,
            attempt=1,
            maximum_attempts=1,
            git_identity={
                "scientific_commit": "0" * 40,
                "scientific_tree": "0" * 40,
                "runner_commit": runner_identity["commit"],
                "runner_tree": runner_identity["git_tree"],
            },
            started_utc=datetime.now(timezone.utc).isoformat(),
            owner_decision_sha256=decision_sha256,
            environment_sha256=environment_sha256,
        )
    except (OSError, ContractError, KeyError, TypeError) as exc:
        return SyntheticAttestationResult("DENY_EXECUTION", f"ATTEMPT_RESERVATION_REFUSED:{type(exc).__name__}", None, None, None, None)
    try:
        work_parent.mkdir(parents=False, exist_ok=False)
    except OSError as exc:
        ledger.finish_attempt(
            run_id=run_id,
            status="INFRA_ERROR",
            finished_utc=datetime.now(timezone.utc).isoformat(),
            reason=f"STAGING_RESERVATION_FAILED:{type(exc).__name__}",
            stdout_sha256=None,
            stderr_sha256=None,
            evidence_sha256={},
        )
        return SyntheticAttestationResult("INFRA_ERROR", f"STAGING_RESERVATION_FAILED:{type(exc).__name__}", run_id, None, None, None)
    ledger_started = True
    junit_path = work_parent / "junit.xml"
    stdout_path = work_parent / "stdout.bin"
    stderr_path = work_parent / "stderr.bin"
    scenario = SYNTHETIC_NODEIDS[nodeid]
    command = [str(executable), str(_FIXTURE), scenario, str(junit_path), nodeid]
    environment = {
        name: value
        for name, value in os.environ.items()
        if name in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
    }
    environment.update({"PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8"})
    process: subprocess.Popen[bytes] | None = None
    job: Any = None
    process_observation: dict[str, Any] | None = None
    status = "INFRA_ERROR"
    reason: str | None = None
    stdout = b""
    stderr = b""
    return_code: int | None = None
    started = time.monotonic()
    try:
        # Recheck immediately before launch; the future SYSTEM adapter must
        # additionally hold protected handles/ACLs against path replacement.
        if sha256_file(_FIXTURE) != fixture_before or sha256_file(executable) != executable_digest:
            raise ContractError("pinned input changed between authorization and launch")
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        if os.name == "nt":
            from .windows_job import WindowsJob

            job = WindowsJob(process_count_limit=2, memory_limit_bytes=256 * 1024 * 1024, cpu_time_limit_seconds=2)
            job.__enter__()
            creationflags |= getattr(subprocess, "CREATE_SUSPENDED", 0x00000004)
        process = subprocess.Popen(
            command,
            cwd=work_parent,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            close_fds=True,
            creationflags=creationflags,
            start_new_session=(os.name != "nt"),
        )
        if job is not None:
            job.assign_suspended_process(process, resume=False)
        process_observation = _process_user_identity(process)
        expected_command = [str(executable), str(_FIXTURE), scenario, str(junit_path), nodeid]
        if (
            process_observation["parent_pid"] != os.getpid()
            or os.path.normcase(str(process_observation["image_path"])) != os.path.normcase(str(executable))
            or process_observation["image_sha256"] != executable_digest
            or process_observation["command_line"] != expected_command
        ):
            raise ContractError("observed child identity differs from the fixed synthetic launch")
        if os.name == "nt" and process_observation["windows_user_sid"] == "S-1-5-18":
            raise ContractError("synthetic test child unexpectedly runs as LocalSystem")
        if job is not None:
            job.resume_suspended_process(process.pid)
        try:
            stdout, stderr = process.communicate(timeout=_WALL_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            if job is not None:
                job.terminate()
            else:
                _terminate_tree(process)
            stdout, stderr = process.communicate(timeout=2)
            status, reason = "TIMEOUT", "synthetic child exceeded fixed wall-time limit"
        return_code = process.returncode
        if len(stdout) > _MAX_STDOUT or len(stderr) > _MAX_STDERR:
            status, reason = "RESOURCE_LIMIT", "synthetic child output exceeded fixed byte cap"
        if job is not None and job.active_process_count() != 0:
            job.terminate()
            status, reason = "INFRA_ERROR", "Job Object still contained descendants after child exit"
        if status == "INFRA_ERROR" and reason is None:
            if sha256_file(_FIXTURE) != fixture_before or sha256_file(executable) != executable_digest:
                status, reason = "INFRA_ERROR", "pinned input changed while the child was running"
            elif scenario == "timeout":
                status, reason = "TIMEOUT", "synthetic child exceeded fixed wall-time limit"
            elif not junit_path.is_file() or junit_path.is_symlink():
                status, reason = "INFRA_ERROR", "synthetic child did not produce its JUnit report"
            else:
                junit_status = classify_pytest_junit(junit_path.read_bytes(), nodeid)
                if junit_status == "INFRA_ERROR":
                    status, reason = "INFRA_ERROR", "JUnit selection or counters are missing or contradictory"
                elif junit_status == "FAIL":
                    status, reason = "FAIL", "the fixed synthetic child reported a test failure"
                elif junit_status != "PASS":
                    status, reason = "INCONCLUSIVE", "synthetic child report did not produce one passing testcase"
                elif return_code != 0:
                    status, reason = "INFRA_ERROR", "child exit code contradicts passing JUnit"
                else:
                    status, reason = "PASS", None
        _write_new(stdout_path, stdout[:_MAX_STDOUT])
        _write_new(stderr_path, stderr[:_MAX_STDERR])
        unexpected = []
        for child_path in work_parent.rglob("*"):
            if child_path.is_symlink() or bool(getattr(child_path, "is_junction", lambda: False)()):
                raise ContractError("synthetic child created a reparse point")
            if child_path.is_file():
                mode = child_path.stat().st_mode
                if not stat.S_ISREG(mode):
                    raise ContractError("synthetic child created a non-regular output")
                if child_path.name not in {"junit.xml", "stdout.bin", "stderr.bin", "descendant.pid"}:
                    unexpected.append(child_path.relative_to(work_parent).as_posix())
        if unexpected and status == "PASS":
            status, reason = "INFRA_ERROR", "synthetic child produced unapproved output paths"
    except KeyboardInterrupt:
        status, reason = "INTERRUPTED", "synthetic supervisor received KeyboardInterrupt"
        if process is not None and process.poll() is None:
            try:
                if job is not None:
                    try:
                        job.terminate()
                    except OSError:
                        pass
                else:
                    _terminate_tree(process)
                process.kill()
                process.wait(timeout=2)
            except (OSError, subprocess.SubprocessError):
                reason += ";CHILD_TERMINATION_UNCONFIRMED"
            if process.poll() is None:
                reason += ";CHILD_REMAINS_AFTER_TERMINATION"
    except Exception as exc:
        status, reason = "INFRA_ERROR", f"{type(exc).__name__}:{str(exc)}"
        if process is not None and process.poll() is None:
            try:
                if job is not None:
                    try:
                        job.terminate()
                    except OSError:
                        pass
                # The process may not yet have been assigned to the Job
                # Object; terminate through its own handle as well.
                process.kill()
                process.wait(timeout=2)
            except (OSError, subprocess.SubprocessError):
                reason += ";CHILD_TERMINATION_UNCONFIRMED"
            if process.poll() is None:
                reason += ";CHILD_REMAINS_AFTER_TERMINATION"
    finally:
        if job is not None:
            try:
                job.close()
            except OSError:
                status, reason = "INFRA_ERROR", "WINDOWS_JOB_CLOSE_FAILED"

    if not work_parent.exists():
        return SyntheticAttestationResult("INFRA_ERROR", "SYNTHETIC_STAGING_DISAPPEARED", run_id, None, None, process_observation)
    # The archive writer is the supervising process and uses exclusive
    # create-new copies. This is a synthetic integrity boundary only; the
    # current user has not demonstrated SYSTEM-owned NTFS protection.
    try:
        if evidence_root.exists() or evidence_root.is_symlink():
            raise ContractError("evidence destination appeared concurrently")
        evidence_root.mkdir(parents=True, exist_ok=False)
        for source in sorted(work_parent.rglob("*")):
            if source.is_file() and not source.is_symlink():
                relative = source.relative_to(work_parent)
                if len(relative.parts) != 1:
                    raise ContractError("synthetic output may contain only one path component")
                target = evidence_root / relative.name
                _write_new(target, source.read_bytes())
        if ledger is None or not ledger_started:
            raise ContractError("synthetic attempt was not reserved before child launch")
        ledger_evidence = {
            path.name: sha256_file(path)
            for path in sorted(evidence_root.iterdir())
            if path.is_file() and path.name not in {"receipt.json", "receipt.sha256"}
        }
        ledger.finish_attempt(
            run_id=run_id,
            status=status,
            finished_utc=datetime.now(timezone.utc).isoformat(),
            reason=reason,
            stdout_sha256=ledger_evidence.get("stdout.bin"),
            stderr_sha256=ledger_evidence.get("stderr.bin"),
            evidence_sha256=ledger_evidence,
        )
        ledger_records = ledger.verify()
        ledger_head_sha256 = ledger_records[-1]["record_sha256"] if ledger_records else None
        metadata = {
            "campaign_id": SYNTHETIC_CAMPAIGN_ID,
            "manifest_sha256": manifest_digest,
            "destination": decision.get("destination"),
            "owner_decision_id": decision.get("decision_id"),
            "owner_key_id": decision.get("owner_key_id"),
            "nodeid": nodeid,
            "run_id": run_id,
            "attempt": 1,
            "maximum_attempts": 1,
            "attempt_ledger": ".wp12-c-attempt-ledger.jsonl",
            "attempt_ledger_head_sha256": ledger_head_sha256,
            "status": status,
            "reason": reason,
            "return_code": return_code,
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "runner_identity": dict(runner_identity),
            "command": command,
            "process_attestation_verified": process_observation is not None,
            "process_attestation": process_observation,
            "process_started": process is not None,
            "synthetic_only": True,
            "archive_protection": "CREATE_ONLY_COPY_BY_SUPERVISOR_PROCESS; NTFS_PROTECTION_NOT_VERIFIED",
            "dedicated_account_enforced": False,
            "scientific_execution": False,
        }
        receipt_digest, _ = write_receipt(evidence_root, metadata)
        issues = verify_attestation_receipt(evidence_root)
        if issues:
            return SyntheticAttestationResult("INFRA_ERROR", "RECEIPT_VERIFICATION_FAILED:" + ";".join(issues), run_id, str(evidence_root / "receipt.json"), receipt_digest, process_observation)
        return SyntheticAttestationResult(status, reason, run_id, str(evidence_root / "receipt.json"), receipt_digest, process_observation)
    except (OSError, ContractError) as exc:
        return SyntheticAttestationResult("INFRA_ERROR", f"ARCHIVE_FAILED:{type(exc).__name__}:{exc}", run_id, None, None, process_observation)
    finally:
        shutil.rmtree(work_parent, ignore_errors=True)
