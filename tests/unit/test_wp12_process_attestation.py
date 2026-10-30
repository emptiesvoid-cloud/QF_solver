"""Synthetic-only end-to-end tests for the WP12 child attestor.

These tests sign ephemeral decisions and execute only the fixed fake child.
They do not import QF Solver or launch pytest from a child process.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

import pytest

from scripts.wp12_owner_canonicalization import PROFILE
from scripts.wp12_runner.contracts import sha256_bytes
from scripts.wp12_runner.evidence import verify_receipt
from scripts.wp12_runner.owner_trust import TrustedOwnerKey, canonical_payload
from scripts.wp12_runner.process_attestation import (
    SYNTHETIC_CAMPAIGN_ID,
    SYNTHETIC_NODEIDS,
    run_synthetic_attested_child,
    verify_attestation_receipt,
)
import scripts.wp12_runner.process_attestation as process_attestation


ROOT = Path(__file__).resolve().parents[2]
FAKE_CHILD = ROOT / "tests" / "fixtures" / "wp12_runner" / "attestation_fake_child.py"
RUNNER_IDENTITY = {"commit": "1" * 40, "git_tree": "2" * 40}
SCIENCE_IDENTITY = {"commit": "0" * 40, "git_tree": "0" * 40}
SUCCESS_NODEID = "tests/unit/test_wp12_process_attestation.py::test_success"


def _signed_decision(nodeid: str, manifest_sha256: str) -> tuple[dict[str, Any], dict[str, TrustedOwnerKey]]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.generate()
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    now = datetime.now(timezone.utc)
    destination = "qualification/0_2_12/wp12_evidence/WP12-C-ATTESTATION-SYNTHETIC/run-001"
    decision: dict[str, Any] = {
        "schema": "qf-solver-wp12-owner-decision-v4",
        "canonicalization": PROFILE,
        "decision_id": "OWNER-SYNTHETIC-C-001",
        "unit_id": "WP12-C-ATTESTATION-UNIT-001",
        "run_id": "run-001",
        "attempt_number": 1,
        "launch_confirmation": "RUN_EXACT_APPROVED_UNIT",
        "isolation_assessment_sha256": "3" * 64,
        "remote_identity": {
            "remote_name": "origin",
            "remote_url": "https://github.com/emptiesvoid-cloud/QF_solver.git",
            "remote_ref": "refs/heads/emptiesvoids-cloud/0.2.12",
            "commit": "0" * 40,
            "git_tree": "0" * 40,
        },
        "status": "APPROVED",
        "campaign_id": SYNTHETIC_CAMPAIGN_ID,
        "manifest_sha256": manifest_sha256,
        "target": {
            "branch": "emptiesvoids-cloud/0.2.12",
            "commit": "0" * 40,
            "git_tree": "0" * 40,
        },
        "scientific_identity": SCIENCE_IDENTITY,
        "runner_identity": RUNNER_IDENTITY,
        "operations": ["EXECUTE_ONE_TEST_NODE"],
        "nodeids": [nodeid],
        "environment": {
            "platform": "synthetic",
            "python_implementation": "CPython",
            "architecture": "64bit",
            "python_version": sys.version.split()[0],
            "venv_executable_sha256": "4" * 64,
            "packages": {"pytest": "synthetic-unused"},
            "native_libraries": {},
            "thread_environment": {},
            "python_executable_path": str(Path(sys.executable).resolve()),
            "python_executable_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
            "virtual_environment": {"kind": "system-python", "path": str(Path(sys.executable).parent)},
            "solver_import_origin": "NOT_IMPORTED",
            "temporary_directory": "synthetic-only",
            "junit_relative_path_from_science_checkout": "synthetic-only",
        },
        "budgets": {
            "wall_seconds": 5,
            "cpu_seconds": 5,
            "memory_bytes": 1024 * 1024 * 1024,
            "process_count": 2,
            "thread_count": 4,
            "temporary_storage_bytes": 1024 * 1024,
            "stdout_bytes": 65536,
            "stderr_bytes": 65536,
            "enforcement": {
                "wall": "hard",
                "cpu": "hard",
                "memory": "hard",
                "process_tree": "hard",
                "storage": "soft",
                "logs": "hard",
                "threads": "soft",
            },
        },
        "maximum_attempts": 1,
        "destination": destination,
        "owner": {"principal": "synthetic-owner", "display_name": "Synthetic Owner"},
        "owner_key_id": "ephemeral-test-key",
        "decided_utc": now.isoformat(),
        "not_before_utc": (now - timedelta(minutes=1)).isoformat(),
        "expires_utc": (now + timedelta(minutes=10)).isoformat(),
        "signature": {},
    }
    payload = canonical_payload(decision)
    decision["signature"] = {
        "algorithm": "ed25519",
        "key_id": "ephemeral-test-key",
        "public_key_sha256": hashlib.sha256(public_bytes).hexdigest(),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "signature_base64": base64.b64encode(private_key.sign(payload)).decode("ascii"),
    }
    return decision, {
        "ephemeral-test-key": TrustedOwnerKey(
            "ephemeral-test-key", "synthetic-owner", base64.b64encode(public_bytes).decode("ascii")
        )
    }


def _manifest(evidence_parent: Path, nodeid: str = SUCCESS_NODEID) -> bytes:
    document = {
        "schema": "qf-wp12-synthetic-attestation-plan-v1",
        "campaign_id": SYNTHETIC_CAMPAIGN_ID,
        "nodeid": nodeid,
        "run_id": "run-001",
        "destination": "qualification/0_2_12/wp12_evidence/WP12-C-ATTESTATION-SYNTHETIC/run-001",
        "materialized_evidence_parent": str(evidence_parent.resolve()),
        "scientific_execution": False,
        "owner_decision_required": True,
        "inputs": {"fake_child_sha256": hashlib.sha256(process_attestation._FIXTURE.read_bytes()).hexdigest()},
        "environment": {
            "python_executable_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        },
    }
    return (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _run(tmp_path: Path, nodeid: str = SUCCESS_NODEID):
    evidence_root = tmp_path / "archive" / "run-001"
    evidence_root.parent.mkdir(parents=True, exist_ok=True)
    manifest_bytes = _manifest(evidence_root.parent, nodeid)
    digest = sha256_bytes(manifest_bytes)
    decision, keys = _signed_decision(nodeid, digest)
    return run_synthetic_attested_child(
        decision=decision,
        trusted_keys=keys,
        manifest_bytes=manifest_bytes,
        expected_manifest_sha256=digest,
        nodeid=nodeid,
        runner_identity=RUNNER_IDENTITY,
        evidence_root=evidence_root,
        now=datetime.now(timezone.utc),
    )


def test_valid_ephemeral_owner_decision_attests_only_fixed_fake_child(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.status == "PASS"
    assert result.process_attestation is not None
    assert result.process_attestation["pid"] > 0
    assert result.process_attestation["parent_pid"] > 0
    assert result.process_attestation["image_sha256"] == hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
    assert result.process_attestation["command_line"][-1] == SUCCESS_NODEID
    assert result.receipt_path is not None
    run_directory = Path(result.receipt_path).parent
    assert not verify_receipt(run_directory)
    assert not verify_attestation_receipt(run_directory)
    receipt = json.loads(Path(result.receipt_path).read_text(encoding="utf-8"))
    assert receipt["metadata"]["process_attestation_verified"] is True
    assert receipt["metadata"]["dedicated_account_enforced"] is False
    assert receipt["metadata"]["scientific_execution"] is False


@pytest.mark.parametrize(
    ("nodeid", "expected_status"),
    [
        ("tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form", "DENY_EXECUTION"),
        ("tests/unit/test_wp12_process_attestation.py::test_no_junit", "INFRA_ERROR"),
        ("tests/unit/test_wp12_process_attestation.py::test_contradictory_junit", "INFRA_ERROR"),
        ("tests/unit/test_wp12_process_attestation.py::test_junit_substitution", "INFRA_ERROR"),
        ("tests/unit/test_wp12_process_attestation.py::test_nonzero", "FAIL"),
    ],
)
def test_scientific_nodeid_refused_and_synthetic_reports_classified(
    tmp_path: Path, nodeid: str, expected_status: str
) -> None:
    if nodeid not in SYNTHETIC_NODEIDS:
        result = _run(tmp_path, nodeid)
        assert result.status == expected_status
        assert result.process_attestation is None
        assert not (tmp_path / "archive" / "run-001").exists()
        return
    result = _run(tmp_path, nodeid)
    assert result.status == expected_status
    assert result.process_attestation is not None
    assert result.receipt_path is not None
    assert not verify_attestation_receipt(Path(result.receipt_path).parent)


def test_invalid_signature_manifest_and_destination_are_denied_before_launch(tmp_path: Path) -> None:
    evidence_parent = tmp_path / "archive"
    evidence_parent.mkdir(parents=True)
    manifest_bytes = _manifest(evidence_parent)
    digest = sha256_bytes(manifest_bytes)
    decision, keys = _signed_decision(SUCCESS_NODEID, digest)
    decision["signature"]["signature_base64"] = base64.b64encode(b"x" * 64).decode("ascii")
    result = run_synthetic_attested_child(
        decision=decision,
        trusted_keys=keys,
        manifest_bytes=manifest_bytes,
        expected_manifest_sha256=digest,
        nodeid=SUCCESS_NODEID,
        runner_identity=RUNNER_IDENTITY,
        evidence_root=tmp_path / "archive" / "bad-signature",
        now=datetime.now(timezone.utc),
    )
    assert result.status == "DENY_EXECUTION"
    assert result.process_attestation is None
    assert "signature" in (result.reason or "").lower()

    decision, keys = _signed_decision(SUCCESS_NODEID, digest)
    mismatch = run_synthetic_attested_child(
        decision=decision,
        trusted_keys=keys,
        manifest_bytes=manifest_bytes,
        expected_manifest_sha256="f" * 64,
        nodeid=SUCCESS_NODEID,
        runner_identity=RUNNER_IDENTITY,
        evidence_root=tmp_path / "archive" / "bad-manifest",
        now=datetime.now(timezone.utc),
    )
    assert mismatch.status == "DENY_EXECUTION"
    assert mismatch.reason == "MANIFEST_SHA256_MISMATCH"
    assert mismatch.process_attestation is None


def test_existing_archive_destination_is_never_overwritten(tmp_path: Path) -> None:
    destination = tmp_path / "archive" / "run-001"
    destination.mkdir(parents=True)
    sentinel = destination / "preserve.txt"
    sentinel.write_text("keep", encoding="utf-8")
    manifest_bytes = _manifest(destination.parent)
    digest = sha256_bytes(manifest_bytes)
    decision, keys = _signed_decision(SUCCESS_NODEID, digest)
    result = run_synthetic_attested_child(
        decision=decision,
        trusted_keys=keys,
        manifest_bytes=manifest_bytes,
        expected_manifest_sha256=digest,
        nodeid=SUCCESS_NODEID,
        runner_identity=RUNNER_IDENTITY,
        evidence_root=destination,
        now=datetime.now(timezone.utc),
    )
    assert result.status == "DENY_EXECUTION"
    assert result.reason == "EVIDENCE_DESTINATION_ALREADY_EXISTS_OR_UNSAFE"
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_receipt_tampering_is_detected_and_attempt_collision_is_refused(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.status == "PASS"
    assert result.receipt_path is not None
    receipt_path = Path(result.receipt_path)
    receipt_path.write_text(receipt_path.read_text(encoding="utf-8").replace('"status": "PASS"', '"status": "FAIL"'), encoding="utf-8")
    assert verify_attestation_receipt(receipt_path.parent)
    shutil.rmtree(receipt_path.parent)

    duplicate = _run(tmp_path)
    assert duplicate.status == "DENY_EXECUTION"
    assert duplicate.reason is not None and duplicate.reason.startswith("ATTEMPT_RESERVATION_REFUSED:")
    assert duplicate.process_attestation is None


def test_declared_interpreter_mismatch_is_denied_before_process_creation(tmp_path: Path) -> None:
    evidence_root = tmp_path / "archive" / "run-001"
    evidence_root.parent.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(_manifest(evidence_root.parent).decode("utf-8"))
    manifest["environment"]["python_executable_sha256"] = "f" * 64
    manifest_bytes = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    digest = sha256_bytes(manifest_bytes)
    decision, keys = _signed_decision(SUCCESS_NODEID, digest)
    result = run_synthetic_attested_child(
        decision=decision,
        trusted_keys=keys,
        manifest_bytes=manifest_bytes,
        expected_manifest_sha256=digest,
        nodeid=SUCCESS_NODEID,
        runner_identity=RUNNER_IDENTITY,
        evidence_root=evidence_root,
        now=datetime.now(timezone.utc),
    )
    assert result.status == "DENY_EXECUTION"
    assert result.reason == "SYNTHETIC_INPUT_IDENTITY_MISMATCH"
    assert result.process_attestation is None


def test_system_identity_observation_is_rejected_before_child_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observe = process_attestation._process_user_identity

    def report_system(process):
        identity = observe(process)
        identity["windows_user_sid"] = "S-1-5-18"
        return identity

    monkeypatch.setattr(process_attestation, "_process_user_identity", report_system)
    result = _run(tmp_path)
    assert result.status == "INFRA_ERROR"
    assert "LocalSystem" in (result.reason or "")
    assert result.receipt_path is not None


def test_input_change_after_prelaunch_check_is_recorded_as_infrastructure_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    copied_fixture = tmp_path / "attestation_fake_child.py"
    copied_fixture.write_bytes(FAKE_CHILD.read_bytes())
    monkeypatch.setattr(process_attestation, "_FIXTURE", copied_fixture)
    observe = process_attestation._process_user_identity

    def observe_then_mutate(process):
        identity = observe(process)
        copied_fixture.write_bytes(copied_fixture.read_bytes() + b"\n# changed after process creation\n")
        return identity

    monkeypatch.setattr(process_attestation, "_process_user_identity", observe_then_mutate)
    result = _run(tmp_path / "run")
    assert result.status == "INFRA_ERROR"
    assert "pinned input changed" in (result.reason or "")
    assert result.receipt_path is not None


def test_process_launch_error_is_archived_as_infrastructure_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_launch(*args, **kwargs):
        raise OSError("synthetic launch failure")

    monkeypatch.setattr(process_attestation.subprocess, "Popen", fail_launch)
    result = _run(tmp_path)
    assert result.status == "INFRA_ERROR"
    assert result.process_attestation is None
    assert result.receipt_path is not None


def test_supervisor_interruption_is_not_reclassified_as_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original_popen = subprocess.Popen

    def interrupt_communication(*args, **kwargs):
        process = original_popen(*args, **kwargs)

        def interrupt(*_args, **_kwargs):
            raise KeyboardInterrupt

        process.communicate = interrupt
        return process

    monkeypatch.setattr(process_attestation.subprocess, "Popen", interrupt_communication)
    result = _run(tmp_path)
    assert result.status == "INTERRUPTED"
    assert result.receipt_path is not None
    assert result.process_attestation is not None


def test_public_synthetic_api_has_no_command_or_executable_override() -> None:
    import inspect

    parameters = set(inspect.signature(run_synthetic_attested_child).parameters)
    assert not {"command", "argv", "executable", "cwd", "environment"}.intersection(parameters)


def test_non_windows_backend_is_refused_before_reservation_or_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        process_attestation,
        "os",
        type("SyntheticOS", (), {"name": "posix", "path": os.path})(),
    )
    result = _run(tmp_path)
    assert result.status == "DENY_EXECUTION"
    assert result.reason == "SUSPENDED_WINDOWS_PROCESS_REQUIRED_FOR_ATTESTATION"
    assert result.process_attestation is None
    assert not (tmp_path / "archive" / ".wp12-c-attempt-ledger.jsonl").exists()


def test_job_assignment_failure_terminates_the_suspended_process_handle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import psutil
    import scripts.wp12_runner.windows_job as windows_job

    process_ids: list[int] = []

    class FailingJob:
        def __init__(self, **_kwargs):
            self.active = False

        def __enter__(self):
            self.active = True
            return self

        def assign_suspended_process(self, process, *, resume=False):
            assert resume is False
            process_ids.append(process.pid)
            raise OSError("synthetic Job Object assignment failure")

        def terminate(self):
            self.active = False

        def close(self):
            self.active = False

        def active_process_count(self):
            return 0

    monkeypatch.setattr(windows_job, "WindowsJob", FailingJob)
    result = _run(tmp_path)
    assert result.status == "INFRA_ERROR"
    assert result.receipt_path is not None
    assert process_ids
    assert not psutil.pid_exists(process_ids[0])


def test_timeout_and_descendant_scenarios_are_not_reported_as_pass(tmp_path: Path) -> None:
    timeout = _run(tmp_path / "timeout", "tests/unit/test_wp12_process_attestation.py::test_timeout")
    assert timeout.status == "TIMEOUT"
    assert timeout.receipt_path is not None
    descendant = _run(tmp_path / "descendant", "tests/unit/test_wp12_process_attestation.py::test_descendant")
    assert descendant.status in {"TIMEOUT", "INFRA_ERROR"}
    assert descendant.status != "PASS"
    assert descendant.receipt_path is not None
