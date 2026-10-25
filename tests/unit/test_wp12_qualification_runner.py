"""Synthetic-only tests for the WP12 qualification runner; no solver imports."""

from __future__ import annotations

import ast
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading

import pytest

from scripts.wp12_runner.contracts import (
    ContractError,
    GitSnapshot,
    approved_command,
    approved_nodeid,
    assess_manifest,
    assess_prepared_manifest,
    attempt_allowed,
    execution_gate_blockers,
    git_identity_issues,
    load_json,
    owner_decision_binding_errors,
    overlay_errors,
    sha256_bytes,
    safe_repo_relative_path,
    validate_owner_decision_structure,
    validate_manifest_schema,
    verify_file_hashes,
    verify_manifest_input_identities,
)
from scripts.wp12_runner.evidence import (
    JsonlJournal,
    create_evidence_directory,
    record_refusal,
    verify_receipt,
    write_receipt,
)
from scripts.wp12_runner.process import (
    ProcessOutcome,
    ResourceSample,
    classify_process_result,
    classify_pytest_junit,
    run_fake_process,
)
from scripts.wp12_runner.cli import main as runner_main
import scripts.wp12_runner.cli as runner_cli


ROOT = Path(__file__).resolve().parents[2]
WP12_PREPARATION = ROOT / "qualification" / "0_2_12" / "wp12_preparation"
NODEID = "tests/unit/test_synthetic.py::test_case"
COMMIT = "a" * 40
TREE = "b" * 40


def _manifest() -> dict[str, object]:
    return {
        "schema": "qf-solver-wp12-prepared-manifest-v1",
        "campaign_id": "WP12-SYNTHETIC",
        "repository": "emptiesvoid-cloud/QF_solver",
        "status": "PREPARED_NOT_AUTHORIZED",
        "mode": "PREPARATION_ONLY",
        "numerical_execution_performed": False,
        "wp12_status": "OPEN",
        "execution_status_label": "NUMERICAL_EXECUTION_NOT_PERFORMED",
        "preparation_status_label": "PREPARATION_ONLY",
        "wp12_status_label": "WP12_STATUS=OPEN",
        "authorization": {"execution_authorized": False},
        "target": {
            "branch": "emptiesvoids-cloud/0.2.12",
            "commit": COMMIT,
            "git_tree": TREE,
            "worktree_must_be_clean": True,
        },
        "scope": {"capability_matrix_ids": ["SYNTH-01"]},
        "source_and_test_identity": {
            "tracked_source_files": ["src/example.py"],
            "tracked_test_files": ["tests/unit/test_synthetic.py"],
            "git_blob_oids": {"tests/unit/test_synthetic.py": "c" * 40},
        },
        "fixtures": {"entries": []},
        "tests": {"exact_nodeids": [NODEID], "commands": []},
        "oracles_and_acceptance": {"no_new_thresholds": True},
        "environment": {"python": "PROPOSED — OWNER_APPROVAL_REQUIRED"},
        "resource_limits": {"timeout_seconds_per_node": {"value": None}},
        "attempt_policy": {"maximum_attempts_per_node": {"value": 1}},
        "evidence": {"exclusive_destination_template": "qualification/0_2_12/wp12_evidence/WP12-SYNTHETIC/<run_id>"},
    }


def _decision(manifest: dict[str, object], digest: str) -> dict[str, object]:
    return {
        "schema": "qf-solver-wp12-owner-decision-v1",
        "decision_id": "OWNER-SYNTHETIC-01",
        "status": "APPROVED",
        "campaign_id": "WP12-SYNTHETIC",
        "manifest_sha256": digest,
        "target": {"branch": "emptiesvoids-cloud/0.2.12", "commit": COMMIT, "git_tree": TREE},
        "operations": ["EXECUTE_ONE_TEST_NODE"],
        "nodeids": [NODEID],
        "environment": {
            "platform": "synthetic",
            "python_version": "3.13.0",
            "venv_executable_sha256": "d" * 64,
            "packages": {"pytest": "8.4.1"},
            "native_libraries": {},
            "thread_environment": {},
        },
        "budgets": {
            "wall_seconds": 10,
            "cpu_seconds": 10,
            "memory_bytes": 1024 * 1024,
            "process_count": 1,
            "thread_count": 1,
            "temporary_storage_bytes": 4096,
            "stdout_bytes": 1024,
            "stderr_bytes": 1024,
        },
        "maximum_attempts": 1,
        "destination": "qualification/0_2_12/wp12_evidence/WP12-SYNTHETIC/run-001",
        "owner": {"principal": "synthetic-owner", "display_name": "Synthetic Owner"},
        "decided_utc": datetime.now(timezone.utc).isoformat(),
        "signature": {
            "algorithm": "ed25519",
            "key_id": "synthetic-key",
            "public_key_sha256": "e" * 64,
            "payload_sha256": "f" * 64,
            "signature_base64": base64.b64encode(b"x" * 64).decode("ascii"),
        },
    }


def _execution_manifest() -> dict[str, object]:
    return {
        "schema": "qf-solver-wp12-execution-manifest-v1",
        "campaign_id": "WP12-SYNTHETIC",
        "unit_id": "SYNTH-UNIT-01",
        "status": "FROZEN_NOT_AUTHORIZED",
        "repository": "emptiesvoid-cloud/QF_solver",
        "target": {
            "branch": "emptiesvoids-cloud/0.2.12",
            "commit": COMMIT,
            "git_tree": TREE,
            "require_clean_checkout": True,
            "allow_detached_at_exact_commit": False,
        },
        "scope": {
            "operation": "EXECUTE_ONE_TEST_NODE",
            "capability_ids": ["SYNTH-01"],
            "scientific_boundary": "synthetic schema validation only",
        },
        "code_identity": {
            "source_files_sha256": {"src/example.py": "1" * 64},
            "test_files_sha256": {"tests/unit/test_synthetic.py": "2" * 64},
            "fixture_files_sha256": {"tests/fixtures/synthetic.json": "3" * 64},
            "runner_commit": COMMIT,
        },
        "tests": {"nodeid": NODEID, "argv": ["python", "-m", "pytest", "-q", NODEID]},
        "fixtures": {"overlays": []},
        "environment": {
            "platform": "synthetic",
            "python_version": "3.13.0",
            "venv_executable_sha256": "4" * 64,
            "packages": {"pytest": "8.4.1"},
            "native_libraries": {},
            "thread_environment": {},
        },
        "resource_limits": {
            "wall_seconds": 10,
            "cpu_seconds": 10,
            "memory_bytes": 1024 * 1024,
            "process_count": 1,
            "thread_count": 1,
            "temporary_storage_bytes": 4096,
            "stdout_bytes": 1024,
            "stderr_bytes": 1024,
            "enforcement": {
                "wall": "hard",
                "cpu": "soft",
                "memory": "soft",
                "process_tree": "soft",
                "storage": "soft",
                "logs": "hard",
            },
        },
        "attempt_policy": {"maximum_attempts": 1, "automatic_retry": False},
        "destination": "qualification/0_2_12/wp12_evidence/WP12-SYNTHETIC/run-001",
        "oracle": {"reference": "synthetic", "classification": "test harness", "frozen_acceptance": {}},
        "prepared_at": "2026-10-25",
        "authorization_reference": {"decision_id": "OWNER-SYNTHETIC-01", "decision_sha256": "5" * 64},
    }


def test_wp12_prepared_manifests_remain_blocked_and_incomplete_inventories_are_visible() -> None:
    paths = sorted(WP12_PREPARATION.glob("wp12_[1-6]_execution_manifest.json"))
    assert len(paths) == 6
    for index, path in enumerate(paths, start=1):
        manifest, digest = load_json(path)
        assessment = assess_prepared_manifest(manifest, digest)
        assert not assessment.execution_eligible
        assert "MANIFEST_PREPARED_NOT_AUTHORIZED" in assessment.execution_blockers
        assert "REAL_EXECUTION_DISABLED_IN_WP12_R" in assessment.execution_blockers
        schema_errors = validate_manifest_schema(manifest)
        if index in {1, 2, 4}:
            assert assessment.structurally_valid, (path.name, assessment.structural_errors)
            assert schema_errors == (), (path.name, schema_errors)
        else:
            assert not assessment.structurally_valid, (path.name, assessment.structural_errors)
            assert schema_errors, path.name
        identity_errors, _records = verify_manifest_input_identities(ROOT, manifest)
        assert identity_errors, path.name


def test_frozen_execution_and_owner_schemas_are_strict_and_valid() -> None:
    execution_manifest = _execution_manifest()
    assert validate_manifest_schema(execution_manifest) == ()
    assert assess_manifest(execution_manifest, "6" * 64).structurally_valid
    execution_manifest["unexpected"] = "not allowed"
    assert any("Additional properties" in error for error in validate_manifest_schema(execution_manifest))
    assert validate_manifest_schema(execution_manifest)[0].startswith("schema violation")
    decision = _decision(_manifest(), "7" * 64)
    assert validate_manifest_schema(decision) == ()


def test_invalid_or_duplicate_json_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"a":1,"a":2}', encoding="utf-8")
    with pytest.raises(ContractError, match="duplicate JSON key"):
        load_json(path)
    path.write_text('{"a": NaN}', encoding="utf-8")
    with pytest.raises(ContractError, match="invalid JSON constant"):
        load_json(path)


def test_invalid_manifest_schema_is_rejected() -> None:
    manifest = _manifest()
    manifest["schema"] = "unknown"
    assessment = assess_manifest(manifest, "1" * 64)
    assert not assessment.structurally_valid
    assert "unsupported manifest schema" in assessment.structural_errors


def test_malformed_nodeid_inventory_does_not_crash_validator() -> None:
    manifest = _manifest()
    manifest["tests"] = {"exact_nodeids": [{"not": "a nodeid"}]}
    assessment = assess_prepared_manifest(manifest, "1" * 64)
    assert not assessment.structurally_valid
    assert validate_manifest_schema(manifest)


def test_owner_decision_absence_and_manifest_hash_mismatch_deny() -> None:
    manifest = _manifest()
    digest = "1" * 64
    assessment = assess_prepared_manifest(manifest, digest)
    snapshot = GitSnapshot(Path.cwd(), "emptiesvoids-cloud/0.2.12", COMMIT, TREE, True, "")
    absent = execution_gate_blockers(
        assessment=assessment,
        manifest=manifest,
        supplied_manifest_sha256=digest,
        owner_decision=None,
        git_snapshot=snapshot,
        nodeid=NODEID,
        argv=None,
        previous_attempts=0,
        attempt_number=1,
        destination_exists=False,
    )
    assert "OWNER_DECISION_ABSENT" in absent
    mismatch = execution_gate_blockers(
        assessment=assessment,
        manifest=manifest,
        supplied_manifest_sha256="2" * 64,
        owner_decision=None,
        git_snapshot=snapshot,
        nodeid=NODEID,
        argv=None,
        previous_attempts=0,
        attempt_number=1,
        destination_exists=False,
    )
    assert "MANIFEST_SHA256_NOT_APPROVED" in mismatch
    assert "REAL_EXECUTION_DISABLED_IN_WP12_R" in mismatch


def test_existing_evidence_destination_is_an_explicit_gate_blocker() -> None:
    manifest = _execution_manifest()
    assessment = assess_manifest(manifest, "1" * 64)
    snapshot = GitSnapshot(Path.cwd(), "emptiesvoids-cloud/0.2.12", COMMIT, TREE, True, "")
    blockers = execution_gate_blockers(
        assessment=assessment,
        manifest=manifest,
        supplied_manifest_sha256="1" * 64,
        owner_decision=None,
        git_snapshot=snapshot,
        nodeid=NODEID,
        argv=["python", "-m", "pytest", "-q", NODEID],
        previous_attempts=0,
        attempt_number=1,
        destination_exists=True,
    )
    assert "DESTINATION_ALREADY_EXISTS" in blockers


def test_owner_json_status_does_not_authenticate_authority() -> None:
    manifest = _manifest()
    digest = "1" * 64
    decision = _decision(manifest, digest)
    assert validate_owner_decision_structure(decision) == ()
    assert owner_decision_binding_errors(decision, manifest, digest) == ()
    assessment = assess_prepared_manifest(manifest, digest)
    snapshot = GitSnapshot(Path.cwd(), "emptiesvoids-cloud/0.2.12", COMMIT, TREE, True, "")
    blockers = execution_gate_blockers(
        assessment=assessment,
        manifest=manifest,
        supplied_manifest_sha256=digest,
        owner_decision=decision,
        git_snapshot=snapshot,
        nodeid=NODEID,
        argv=None,
        previous_attempts=0,
        attempt_number=1,
        destination_exists=False,
    )
    assert "OWNER_SIGNATURE_UNVERIFIED_NO_TRUST_ROOT" in blockers
    assert "REAL_EXECUTION_DISABLED_IN_WP12_R" in blockers


def test_owner_decision_binding_rejects_changed_nodeid_and_commit() -> None:
    manifest = _manifest()
    digest = "1" * 64
    decision = _decision(manifest, digest)
    decision["nodeids"] = ["tests/unit/test_other.py::test_case"]
    decision["target"] = {"branch": "emptiesvoids-cloud/0.2.12", "commit": "9" * 40, "git_tree": TREE}
    errors = owner_decision_binding_errors(decision, manifest, digest)
    assert any("nodeids" in error for error in errors)
    assert any("commit" in error for error in errors)


def test_wrong_commit_tree_or_dirty_checkout_is_rejected() -> None:
    target = {"branch": "emptiesvoids-cloud/0.2.12", "commit": COMMIT, "git_tree": TREE, "worktree_must_be_clean": True}
    wrong = GitSnapshot(Path.cwd(), target["branch"], "9" * 40, "8" * 40, True, "")
    assert git_identity_issues(target, wrong) == ("GIT_COMMIT_MISMATCH", "GIT_TREE_MISMATCH")
    dirty = GitSnapshot(Path.cwd(), target["branch"], COMMIT, TREE, False, " M tests/fake.py")
    assert git_identity_issues(target, dirty) == ("GIT_CHECKOUT_DIRTY",)


def test_modified_fixture_hash_is_detected(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.json"
    fixture.write_bytes(b"approved fixture")
    expected = hashlib.sha256(fixture.read_bytes()).hexdigest()
    assert verify_file_hashes(tmp_path, {"fixture.json": expected}) == ()
    fixture.write_bytes(b"changed fixture")
    assert verify_file_hashes(tmp_path, {"fixture.json": expected}) == ("SHA256_MISMATCH:fixture.json",)


def test_static_manifest_identity_check_preserves_c02_overlay_and_c01_mismatch() -> None:
    manifest, _digest = load_json(WP12_PREPARATION / "wp12_3_execution_manifest.json")
    errors, records = verify_manifest_input_identities(ROOT, manifest)
    assert any(error.startswith("FIXTURE_CONTRACT_DIGEST_MISMATCH:") for error in errors)
    overlay = [record for record in records if record.get("state") == "OVERLAY_IDENTIFIED_NOT_MATERIALIZED"]
    assert len(overlay) == 1
    assert overlay[0]["path"] == "tests/unit/test_wpc02_aj_partial_active_contact.py"
    assert not (ROOT / overlay[0]["path"]).exists()


def test_nodeid_and_command_must_be_exactly_approved() -> None:
    assert approved_nodeid(NODEID, [NODEID])
    assert not approved_nodeid("tests/unit/test_synthetic.py::*", [NODEID])
    assert not approved_nodeid("tests/unit", [NODEID])
    unit = {"nodeid": NODEID, "argv": ["python", "-m", "pytest", "-q", NODEID]}
    assert approved_command(NODEID, unit["argv"], [unit])
    assert not approved_command(NODEID, ["python", "-m", "pytest", "-q", "tests/unit"], [unit])


def test_attempt_budget_is_one_shot() -> None:
    assert attempt_allowed(1, 0, 1)
    assert not attempt_allowed(2, 1, 1)
    assert not attempt_allowed(1, 0, 0)
    assert not attempt_allowed(True, 0, 1)


def test_existing_destination_and_traversal_are_refused(tmp_path: Path) -> None:
    destination = create_evidence_directory(tmp_path, "WP12-SYNTHETIC", "run-001")
    assert destination.is_dir()
    with pytest.raises(FileExistsError):
        create_evidence_directory(tmp_path, "WP12-SYNTHETIC", "run-001")
    with pytest.raises(ContractError):
        create_evidence_directory(tmp_path, "..", "escape")
    assert not safe_repo_relative_path("qualification/0_2_12/../wp12_evidence/run")
    assert not safe_repo_relative_path("qualification/0_2_12/./wp12_evidence/run")
    assert not safe_repo_relative_path("qualification//wp12_evidence/run")


def test_undeclared_overlay_and_mutated_overlay_are_refused() -> None:
    data = b"historical helper bytes"
    path = "tests/unit/frozen_helper.py"
    source_commit = "a" * 40
    blob_oid = "b" * 40
    assert overlay_errors(None, path, source_commit, blob_oid, data) == ("OVERLAY_NOT_DECLARED",)
    declaration = {
        "path": path,
        "source_commit": source_commit,
        "git_blob_oid": blob_oid,
        "sha256": sha256_bytes(data),
    }
    assert overlay_errors(declaration, path, source_commit, blob_oid, data) == ()
    assert overlay_errors(declaration, path, source_commit, blob_oid, b"altered")


def test_incomplete_or_malformed_journal_is_rejected(tmp_path: Path) -> None:
    incomplete = tmp_path / "incomplete.jsonl"
    incomplete.write_bytes(b'{"event":"RUNNING"}')
    with pytest.raises(ContractError, match="incomplete record"):
        JsonlJournal.read(incomplete)
    malformed = tmp_path / "malformed.jsonl"
    malformed.write_bytes(b"not-json\n")
    with pytest.raises(ContractError, match="record 1 is invalid"):
        JsonlJournal.read(malformed)


def test_receipt_inventory_hashes_and_refuses_overwrite(tmp_path: Path) -> None:
    run_directory = tmp_path / "run"
    run_directory.mkdir()
    (run_directory / "stdout.bin").write_bytes(b"synthetic output")
    digest, receipt = write_receipt(run_directory, {"mode": "SELF_TEST", "scientific_result": False})
    assert receipt.is_file()
    assert len(digest) == 64
    assert verify_receipt(run_directory) == ()
    with pytest.raises(FileExistsError, match="overwrite"):
        write_receipt(run_directory, {"mode": "SELF_TEST"})
    (run_directory / "stdout.bin").write_bytes(b"tampered")
    assert "evidence artifact inventory differs from receipt" in verify_receipt(run_directory)


def test_refusal_is_durably_recorded_without_touching_evidence(tmp_path: Path) -> None:
    audit = tmp_path / "audit"
    refusal = record_refusal(audit, {"event": "DENY_EXECUTION", "execution_started": False}, allowed_root=tmp_path)
    payload = json.loads(refusal.read_text(encoding="utf-8"))
    assert payload["event"] == "DENY_EXECUTION"
    assert payload["execution_started"] is False
    assert not (tmp_path / "qualification" / "0_2_12" / "wp12_evidence").exists()
    with pytest.raises(ContractError, match="inside the configured repository"):
        record_refusal(tmp_path.parent / "escape", {"event": "DENY_EXECUTION"}, allowed_root=tmp_path)


def test_execute_mode_logs_refusal_for_prepared_manifest_and_never_launches_tests(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = WP12_PREPARATION / "wp12_1_execution_manifest.json"
    _manifest_doc, digest = load_json(manifest_path)
    audit = tmp_path / "audit"
    monkeypatch.setattr(runner_cli, "DEFAULT_AUDIT_DIRECTORY", audit)
    monkeypatch.setattr(runner_cli, "REPOSITORY_ROOT", tmp_path)
    result = runner_main(
        [
            "--mode",
            "EXECUTE",
            "--root",
            str(ROOT),
            "--manifest",
            str(manifest_path),
            "--manifest-sha256",
            digest,
            "--nodeid",
            "tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form",
        ]
    )
    output = capsys.readouterr().err
    assert result == 3
    assert '"event": "DENY_EXECUTION"' in output
    assert '"execution_started": false' in output
    refusal_files = list(audit.glob("refusal-*.json"))
    assert len(refusal_files) == 1
    refusal = json.loads(refusal_files[0].read_text(encoding="utf-8"))
    assert "REAL_EXECUTION_DISABLED_IN_WP12_R" in refusal["blockers"]
    assert "MANIFEST_PREPARED_NOT_AUTHORIZED" in refusal["blockers"]


def test_execute_argument_rejection_is_logged_and_force_flag_is_not_supported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner_cli, "DEFAULT_AUDIT_DIRECTORY", tmp_path / "audit")
    monkeypatch.setattr(runner_cli, "REPOSITORY_ROOT", tmp_path)
    with pytest.raises(SystemExit):
        runner_main(["--mode", "EXECUTE", "--manifest", "manifest.json", "--force"])
    output = capsys.readouterr().err
    assert '"event": "DENY_EXECUTION"' in output
    refusal_files = list((tmp_path / "audit").glob("refusal-*.json"))
    assert len(refusal_files) == 1
    refusal = json.loads(refusal_files[0].read_text(encoding="utf-8"))
    assert refusal["blockers"] == ["EXECUTE_ARGUMENT_VALIDATION_FAILED"]
    assert refusal["execution_started"] is False


def test_synthetic_child_success_nonzero_timeout_and_output_cap(tmp_path: Path) -> None:
    success = run_fake_process("success", tmp_path / "success")
    assert success.state == "PROCESS_EXITED"
    assert success.return_code == 0
    nonzero = run_fake_process("exit", tmp_path / "nonzero")
    assert nonzero.state == "PROCESS_EXITED"
    assert nonzero.return_code == 17
    timeout = run_fake_process("sleep", tmp_path / "timeout", timeout_seconds=0.2)
    assert timeout.state == "TIMEOUT"
    capped = run_fake_process("flood", tmp_path / "flood", output_byte_limit=128)
    assert capped.state == "RESOURCE_LIMIT"
    assert (tmp_path / "flood" / "stdout.bin").stat().st_size <= 128
    with pytest.raises(ContractError, match="fixed synthetic child cases"):
        run_fake_process("arbitrary-command", tmp_path / "arbitrary")


def test_descendant_process_is_terminated_and_reported(tmp_path: Path) -> None:
    outcome = run_fake_process("tree", tmp_path / "tree", timeout_seconds=0.3)
    assert outcome.state == "TIMEOUT"
    assert outcome.child_pids_remaining == ()


def test_interruption_is_not_reclassified_as_success(tmp_path: Path) -> None:
    interrupt = threading.Event()
    timer = threading.Timer(0.12, interrupt.set)
    timer.start()
    outcome = run_fake_process("sleep", tmp_path / "interrupt", timeout_seconds=2, interrupt_event=interrupt)
    timer.join()
    assert outcome.state == "INTERRUPTED"


def test_simulated_resource_sample_causes_resource_limit(tmp_path: Path) -> None:
    calls = 0

    def high_memory_sample(_pid: int) -> ResourceSample:
        nonlocal calls
        calls += 1
        return ResourceSample(process_count=1, rss_bytes=4096)

    outcome = run_fake_process(
        "sleep",
        tmp_path / "memory-limit",
        timeout_seconds=2,
        memory_soft_limit_bytes=1024,
        sample_provider=high_memory_sample,
    )
    assert calls >= 1
    assert outcome.state == "RESOURCE_LIMIT"
    assert "not a hard memory cap" in (outcome.stop_reason or "")


def test_pytest_result_classification_keeps_fail_separate_from_infrastructure() -> None:
    passed = b'<testsuite><testcase classname="tests.unit.test_synthetic" name="test_case" /></testsuite>'
    failed = b'<testsuite><testcase classname="test_synthetic" name="test_case"><failure /></testcase></testsuite>'
    skipped = b'<testsuite><testcase classname="test_synthetic" name="test_case"><skipped /></testcase></testsuite>'
    assert classify_pytest_junit(passed, NODEID) == "PASS"
    assert classify_pytest_junit(failed, NODEID) == "FAIL"
    assert classify_pytest_junit(skipped, NODEID) == "INCONCLUSIVE"
    process = ProcessOutcome("PROCESS_EXITED", 1, None, 0.1, 0, 0, 10, 1, ())
    assert classify_process_result(process, failed, NODEID) == "FAIL"
    assert classify_process_result(process, None, NODEID) == "INFRA_ERROR"


def test_runner_sources_and_fixture_import_no_scientific_package() -> None:
    paths = [
        *Path(__file__).resolve().parents[2].joinpath("scripts/wp12_runner").glob("*.py"),
        Path(__file__).resolve().parents[2] / "scripts" / "run_wp12_qualification.py",
        Path(__file__).resolve().parents[1] / "fixtures" / "wp12_runner" / "fake_child.py",
    ]
    forbidden = {"solveur", "qf_solver"}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module.split(".", 1)[0])
        assert not forbidden.intersection(imports), path
