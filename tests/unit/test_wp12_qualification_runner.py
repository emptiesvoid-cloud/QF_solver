"""Synthetic-only tests for the WP12 qualification runner; no solver imports."""

from __future__ import annotations

import ast
import base64
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from types import SimpleNamespace
from typing import Any

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
    git_commit_is_ancestor,
    git_commit_tree_matches,
    git_identity_issues,
    load_json,
    owner_decision_binding_errors,
    overlay_errors,
    remote_identity_issues,
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
    reserve_pilot_evidence_directory,
    verify_receipt,
    write_receipt,
)
from scripts.wp12_runner.environment import collect_environment_provenance
from scripts.wp12_runner.git_remote import sync_remote_identity, write_sync_receipt
from scripts.wp12_runner.import_probe import probe_solver_import
from scripts.wp12_runner.ledger import AttemptLedger
from scripts.wp12_runner.owner_trust import (
    TRUST_STORE_PATH_VALUE,
    TRUST_STORE_SHA_VALUE,
    TrustedOwnerKey,
    canonical_payload,
    load_machine_trust_store,
    verify_owner_decision,
)
from scripts.wp12_runner.process import (
    ProcessOutcome,
    ResourceSample,
    classify_process_result,
    classify_pytest_junit,
    run_fake_process,
    run_approved_pilot_process,
    validate_approved_pilot_command,
)
from scripts.wp12_runner.cli import main as runner_main
import scripts.wp12_runner.cli as runner_cli
import scripts.wp12_runner.synthetic_orchestrator as synthetic_orchestrator
from scripts.wp12_owner_canonicalization import CanonicalizationError, PROFILE, canonical_owner_payload
from scripts.build_wp12_owner_trust_store import build_public_trust_store


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
        "schema": "qf-solver-wp12-owner-decision-v4",
        "canonicalization": PROFILE,
        "decision_id": "OWNER-SYNTHETIC-01",
        "unit_id": "SYNTH-UNIT-01",
        "run_id": "run-001",
        "attempt_number": 1,
        "launch_confirmation": "RUN_EXACT_APPROVED_UNIT",
        "isolation_assessment_sha256": "9" * 64,
        "remote_identity": {
            "remote_name": "origin",
            "remote_url": "https://github.com/emptiesvoid-cloud/QF_solver.git",
            "remote_ref": "refs/heads/emptiesvoids-cloud/0.2.12",
            "commit": COMMIT,
            "git_tree": TREE,
        },
        "status": "APPROVED",
        "campaign_id": "WP12-SYNTHETIC",
        "manifest_sha256": digest,
        "target": {"branch": "emptiesvoids-cloud/0.2.12", "commit": COMMIT, "git_tree": TREE},
        "scientific_identity": {"commit": COMMIT, "git_tree": TREE},
        "runner_identity": {"commit": COMMIT, "git_tree": TREE},
        "operations": ["EXECUTE_ONE_TEST_NODE"],
        "nodeids": [NODEID],
        "environment": {
            "platform": "synthetic",
            "python_implementation": "CPython",
            "architecture": "64bit",
            "python_version": "3.13.0",
            "venv_executable_sha256": "d" * 64,
            "packages": {"pytest": "8.4.1"},
            "native_libraries": {},
            "thread_environment": {},
            "python_executable_path": "C:\\synthetic\\venv\\Scripts\\python.exe",
            "python_executable_sha256": "d" * 64,
            "virtual_environment": {"kind": "venv", "path": "C:\\synthetic\\venv"},
            "solver_import_origin": "src/solveur/__init__.py",
            "temporary_directory": "qualification/0_2_12/wp12_evidence/WP12-SYNTHETIC/run-001/tmp",
            "junit_relative_path_from_science_checkout": "../runner/qualification/0_2_12/wp12_evidence/WP12-SYNTHETIC/run-001",
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
            "enforcement": {
                "wall": "hard",
                "cpu": "hard",
                "memory": "hard",
                "process_tree": "hard",
                "storage": "hard",
                "logs": "hard",
                "threads": "soft",
            },
        },
        "maximum_attempts": 1,
        "destination": "qualification/0_2_12/wp12_evidence/WP12-SYNTHETIC/run-001",
        "owner": {"principal": "synthetic-owner", "display_name": "Synthetic Owner"},
        "owner_key_id": "synthetic-key",
        "decided_utc": datetime.now(timezone.utc).isoformat(),
        "not_before_utc": "2026-01-01T00:00:00Z",
        "expires_utc": "2027-01-01T00:00:00Z",
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
        "schema": "qf-solver-wp12-execution-manifest-v2",
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
        "scientific_identity": {"commit": COMMIT, "git_tree": TREE},
        "runner_identity": {"commit": COMMIT, "git_tree": TREE},
        "scope": {
            "operation": "EXECUTE_ONE_TEST_NODE",
            "capability_ids": ["SYNTH-01"],
            "scientific_boundary": "synthetic schema validation only",
        },
        "code_identity": {
            "source_files_sha256": {"src/example.py": "1" * 64},
            "test_files_sha256": {"tests/unit/test_synthetic.py": "2" * 64},
            "fixture_files_sha256": {"tests/fixtures/synthetic.json": "3" * 64},
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


def _execution_manifest_v3() -> dict[str, object]:
    nodeid = "tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form"
    destination = "qualification/0_2_12/wp12_evidence/WP12-1-PILOT-001/attempt-001"
    junit_relative = "../checkout-0.2.12/" + destination
    test_sha = "2" * 64
    return {
        "schema": "qf-solver-wp12-execution-manifest-v3",
        "campaign_id": "WP12-1-PILOT-001",
        "unit_id": "WP12-1-PILOT-001-UNIT-01",
        "status": "FROZEN_NOT_AUTHORIZED",
        "repository": "emptiesvoid-cloud/QF_solver",
        "target": {
            "branch": "emptiesvoids-cloud/0.2.12",
            "commit": COMMIT,
            "git_tree": TREE,
            "require_clean_checkout": True,
            "allow_detached_at_exact_commit": True,
            "remote_name": "origin",
            "remote_url": "https://github.com/emptiesvoid-cloud/QF_solver.git",
            "remote_ref": "refs/heads/emptiesvoids-cloud/0.2.12",
        },
        "scientific_identity": {"commit": "c" * 40, "git_tree": "d" * 40},
        "runner_identity": {"commit": COMMIT, "git_tree": TREE},
        "scope": {
            "operation": "EXECUTE_ONE_TEST_NODE",
            "capability_ids": ["WP12-1-MODAL-SYMMETRIC-PROJECTION"],
            "scientific_boundary": "one structured symmetric projection identity only",
        },
        "code_identity": {
            "source_files_sha256": {
                "src/solveur/core/analyses/modal_basis_numerics.py": "1" * 64,
                "pyproject.toml": "3" * 64,
            },
            "test_files_sha256": {"tests/unit/test_modal_symmetric_projection.py": test_sha},
            "fixture_files_sha256": {"tests/unit/test_modal_symmetric_projection.py": test_sha},
        },
        "tests": {
            "nodeid": nodeid,
            "command_profile": "qf-wp12-single-node-pytest-v1",
            "argv": [
                "C:\\synthetic\\venv\\Scripts\\python.exe",
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "-p",
                "scripts.wp12_runner.pytest_provenance_plugin",
                f"--junitxml={junit_relative}/junit.xml",
                nodeid,
            ],
        },
        "fixtures": {
            "overlays": [],
            "inline": [
                {
                    "id": "WP12-1-PILOT-001-projection-matrices",
                    "nodeid": nodeid,
                    "source_file": "tests/unit/test_modal_symmetric_projection.py",
                    "source_file_sha256": test_sha,
                    "canonicalization": "qf-wp12-inline-fixture-v1",
                    "sha256": "4" * 64,
                }
            ],
        },
        "environment": {
            "platform": "synthetic-platform",
            "python_implementation": "CPython",
            "architecture": "64bit",
            "python_version": "3.13.1",
            "venv_executable_sha256": "5" * 64,
            "packages": {"pytest": "8.4.1"},
            "native_libraries": {},
            "thread_environment": {
                "OMP_NUM_THREADS": "1",
                "OPENBLAS_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1",
                "BLIS_NUM_THREADS": "1",
                "VECLIB_MAXIMUM_THREADS": "1",
                "NUMEXPR_NUM_THREADS": "1",
            },
            "python_executable_path": "C:\\synthetic\\venv\\Scripts\\python.exe",
            "python_executable_sha256": "5" * 64,
            "virtual_environment": {"kind": "venv", "path": "C:\\synthetic\\venv"},
            "solver_import_origin": "src/solveur/__init__.py",
            "temporary_directory": f"{destination}/tmp",
            "junit_relative_path_from_science_checkout": junit_relative,
        },
        "resource_limits": {
            "wall_seconds": 60,
            "cpu_seconds": 30,
            "memory_bytes": 536870912,
            "process_count": 2,
            "thread_count": 1,
            "temporary_storage_bytes": 10485760,
            "stdout_bytes": 1048576,
            "stderr_bytes": 1048576,
            "enforcement": {
                "wall": "hard",
                "cpu": "hard",
                "memory": "hard",
                "process_tree": "hard",
                "storage": "hard",
                "logs": "hard",
                "threads": "soft",
            },
        },
        "attempt_policy": {"maximum_attempts": 1, "automatic_retry": False},
        "destination": destination,
        "oracle": {
            "reference": "existing assertions in the selected nodeid",
            "classification": "algebraic projection identity",
            "frozen_acceptance": {"source": "test assertions; no new threshold"},
        },
        "prepared_at": "2026-10-25",
        "authorization_reference": {"status": "OWNER_DECISION_REQUIRED"},
        "isolation_assessment": {
            "status": "NOT_VERIFIED",
            "profile": "wp12-pilot-isolated-windows-v1",
            "attestation_path": "qualification/0_2_12/wp12_preparation/wp12_a_isolation_attestation.json",
            "sha256": "6" * 64,
            "evidence_anchor_status": "NOT_CONFIGURED",
            "review_status": "NOT_REVIEWED",
            "read_only_roots": ["science/src", "science/tests", "qualification/0_2_11"],
            "exclusive_write_root": destination,
            "limitations": ["synthetic test manifest only"],
        },
    }


def test_wp12_prepared_manifests_remain_blocked_and_incomplete_inventories_are_visible() -> None:
    paths = sorted(WP12_PREPARATION.glob("wp12_[1-6]_execution_manifest.json"))
    assert len(paths) == 6
    for index, path in enumerate(paths, start=1):
        manifest, digest = load_json(path)
        assessment = assess_prepared_manifest(manifest, digest)
        assert not assessment.execution_eligible
        assert "MANIFEST_PREPARED_NOT_AUTHORIZED" in assessment.execution_blockers
        assert "SEPARATE_OWNER_DECISION_REQUIRED" in assessment.execution_blockers
        schema_errors = validate_manifest_schema(manifest)
        if index in {1, 2, 4}:
            assert assessment.structurally_valid, (path.name, assessment.structural_errors)
            assert schema_errors == (), (path.name, schema_errors)
        else:
            assert not assessment.structurally_valid, (path.name, assessment.structural_errors)
            assert schema_errors, path.name
        identity_errors, _records = verify_manifest_input_identities(ROOT, manifest)
        assert identity_errors, path.name


def test_wp12_r2_manifest_revisions_preserve_originals_and_remain_unapproved() -> None:
    revision_root = WP12_PREPARATION / "revisions"
    index = json.loads((revision_root / "manifest_revision_index.json").read_text(encoding="utf-8"))
    assert len(index["revisions"]) == 6
    for entry in index["revisions"]:
        original_path = ROOT / entry["original_path"]
        revision_path = ROOT / entry["revision_path"]
        assert hashlib.sha256(original_path.read_bytes()).hexdigest() == entry["original_sha256"]
        assert hashlib.sha256(revision_path.read_bytes()).hexdigest() == entry["revision_sha256"]
        revision = json.loads(revision_path.read_text(encoding="utf-8"))
        assert revision["status"] == "PREPARED_NOT_AUTHORIZED"
        assert revision["authorization"]["execution_authorized"] is False
        assert validate_manifest_schema(revision) == ()
        if revision["campaign_id"].startswith(("WP12-1", "WP12-2", "WP12-3", "WP12-4")):
            identity = revision["source_and_test_identity"]
            paths = set(identity["tracked_source_files"] + identity["tracked_test_files"])
            assert set(identity["git_blob_oids"]) == paths
            assert set(identity["sha256_by_file"]) == paths
        if revision["campaign_id"].startswith("WP12-3"):
            nodeids = revision["tests"]["exact_nodeids"]
            assert len(nodeids) == len(set(nodeids))


def test_frozen_execution_and_owner_schemas_are_strict_and_valid() -> None:
    execution_manifest = _execution_manifest()
    assert validate_manifest_schema(execution_manifest) == ()
    assert assess_manifest(execution_manifest, "6" * 64).structurally_valid
    execution_manifest["unexpected"] = "not allowed"
    assert any("Additional properties" in error for error in validate_manifest_schema(execution_manifest))
    assert validate_manifest_schema(execution_manifest)[0].startswith("schema violation")
    decision = _decision(_manifest(), "7" * 64)
    assert validate_manifest_schema(decision) == ()


def test_execution_manifest_binds_science_and_runner_identities_separately() -> None:
    manifest = _execution_manifest()
    manifest["scientific_identity"] = {"commit": "c" * 40, "git_tree": "d" * 40}
    assert manifest["runner_identity"] == {"commit": COMMIT, "git_tree": TREE}
    assert manifest["target"]["commit"] == manifest["runner_identity"]["commit"]
    assert assess_manifest(manifest, "8" * 64).structurally_valid
    decision = _decision(_manifest(), "8" * 64)
    errors = owner_decision_binding_errors(decision, manifest, "8" * 64)
    assert "Owner decision scientific_identity does not match manifest" in errors

    mismatch = dict(manifest)
    mismatch["runner_identity"] = {"commit": "e" * 40, "git_tree": TREE}
    assessment = assess_manifest(mismatch, "8" * 64)
    assert "target commit/tree must equal runner_identity commit/tree" in assessment.structural_errors


def test_invalid_or_duplicate_json_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"a":1,"a":2}', encoding="utf-8")
    with pytest.raises(ContractError, match="duplicate JSON key"):
        load_json(path)
    path.write_text('{"a": NaN}', encoding="utf-8")
    with pytest.raises(ContractError, match="invalid JSON constant"):
        load_json(path)


def test_owner_canonicalization_profile_v1_matches_fixed_synthetic_vector() -> None:
    decision = {
        "schema": "qf-solver-wp12-owner-decision-v4",
        "canonicalization": PROFILE,
        "launch_confirmation": "RUN_EXACT_APPROVED_UNIT",
        "attempt_number": 1,
        "owner": {"principal": "synthetic-owner", "display_name": "Quentin Farinazzo – synthétique"},
        "signature": {"signature_base64": "ignored-envelope"},
    }
    expected = (
        '{"attempt_number":1,"canonicalization":"qf-owner-json-v1",'
        '"launch_confirmation":"RUN_EXACT_APPROVED_UNIT",'
        '"owner":{"display_name":"Quentin Farinazzo – synthétique","principal":"synthetic-owner"},'
        '"schema":"qf-solver-wp12-owner-decision-v4"}'
    ).encode("utf-8")
    assert canonical_owner_payload(decision) == expected
    assert canonical_payload(decision) == expected
    with pytest.raises(CanonicalizationError, match="floating-point"):
        canonical_owner_payload({**decision, "attempt_number": 1.0})
    with pytest.raises(CanonicalizationError, match="ASCII"):
        canonical_owner_payload({**decision, "clÉ": "rejected"})


def test_invalid_manifest_schema_is_rejected() -> None:
    manifest = _manifest()
    manifest["schema"] = "unknown"
    assessment = assess_manifest(manifest, "1" * 64)
    assert not assessment.structurally_valid
    assert "unsupported manifest schema" in assessment.structural_errors


def test_pilot_v3_manifest_binds_exact_instrumented_command_and_stays_unauthorized() -> None:
    manifest = _execution_manifest_v3()
    assert validate_manifest_schema(manifest) == ()
    assessment = assess_manifest(manifest, "7" * 64)
    assert assessment.structural_errors == ()
    assert assessment.execution_blockers == (
        "SEPARATE_OWNER_DECISION_REQUIRED",
        "REAL_EXECUTION_DISABLED_IN_WP12_A",
    )

    altered = _execution_manifest_v3()
    altered["tests"]["argv"] = [*altered["tests"]["argv"][:-1], "-k", "modal"]
    assert validate_manifest_schema(altered)
    assert assess_manifest(altered, "7" * 64).structural_errors


def test_pilot_v4_manifest_binds_separate_checkouts_and_stays_blocked(tmp_path: Path) -> None:
    manifest = _execution_manifest_v3()
    manifest["schema"] = "qf-solver-wp12-execution-manifest-v4"
    manifest["isolation_assessment"]["runner_account"] = "QF_WP12_RUNNER"
    manifest["isolation_assessment"]["runner_account_sid"] = "S-1-5-21-1000-1000-1000-1001"
    science_path = str(tmp_path / "science")
    runner_path = str(tmp_path / "runner")
    venv_path = str(tmp_path / "venv")
    python_executable = str(Path(venv_path) / "Scripts" / "python.exe")
    evidence_path = str(tmp_path / "evidence" / "WP12-1-PILOT-001" / "attempt-001")
    nodeid = manifest["tests"]["nodeid"]
    manifest["tests"]["command_profile"] = "qf-wp12-single-node-pytest-v3"
    manifest["tests"]["argv"] = [
        python_executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "-p",
        "scripts.wp12_runner.pytest_provenance_plugin",
        "-o",
        "addopts=",
        "--noconftest",
        f"--junitxml={evidence_path}\\junit.xml",
        nodeid,
    ]
    manifest["environment"]["python_executable_path"] = manifest["tests"]["argv"][0]
    manifest["environment"]["virtual_environment"]["path"] = venv_path
    manifest["execution_context"] = {
        "science_checkout": {"path": science_path, **manifest["scientific_identity"]},
        "runner_checkout": {"path": runner_path, **manifest["runner_identity"]},
        "python_executable": manifest["tests"]["argv"][0],
        "venv_root": venv_path,
        "python_base_root": str(tmp_path / "python-base"),
        "working_directory": science_path,
        "plugin_path": str(Path(runner_path) / "scripts" / "wp12_runner" / "pytest_provenance_plugin.py"),
        "solver_import_root": str(Path(science_path) / "src"),
        "pythonpath": [runner_path, str(Path(science_path) / "src")],
        "requirements_lock_sha256": "9" * 64,
        "inline_fixture": {
            "schema": "qf-wp12-inline-fixture-v1",
            "fixture_id": "WP12-1-PILOT-001-projection-matrices",
            "canonicalization": "qf-wp12-inline-fixture-v1",
            "sha256": "4" * 64,
        },
        "expected_packages": {"pytest": "8.4.1"},
        "expected_native_libraries_sha256": {"numpy/sample.pyd": "a" * 64},
        "thread_environment": manifest["environment"]["thread_environment"],
        "evidence_root": str(tmp_path / "evidence"),
        "destination_path": evidence_path,
        "temporary_root": str(tmp_path / "temporary"),
        "archive": {
            "status": "NOT_CONFIGURED",
            "method": "ADMINISTRATOR_SEALED_COPY_V1",
            "destination": str(tmp_path / "sealed-archive"),
            "request_root": str(tmp_path / "archive-requests"),
            "owner_decision_root": str(tmp_path / "owner-decisions"),
            "manifest_path": str(tmp_path / "owner-decisions" / "WP12-1-PILOT-001" / "manifest-v2.json"),
            "python_executable": python_executable,
            "python_executable_sha256": "5" * 64,
            "decision_verifier_script_path": str(
                Path(runner_path) / "scripts" / "wp12_runner" / "owner_decision_verifier.py"
            ),
            "decision_verifier_script_sha256": "9" * 64,
            "contracts_script_sha256": "a" * 64,
            "owner_trust_script_sha256": "b" * 64,
            "canonicalization_script_sha256": "c" * 64,
            "execution_attestation": "NONE",
            "worker_task_name": r"\QFSolverWP12\ArchiveWorker",
            "worker_script_path": str(
                Path(runner_path) / "scripts" / "wp12_runner" / "windows" / "Invoke-WP12EvidenceArchiveWorker.ps1"
            ),
            "worker_script_sha256": "c" * 64,
            "ack_timeout_seconds": 60,
        },
        "isolation_attestation": {
            "path": str(tmp_path / "isolation.json"),
            "sha256": "6" * 64,
            "status": "NOT_VERIFIED",
        },
        "security_review": {
            "status": "NOT_REVIEWED",
            "review_record_path": str(tmp_path / "review.json"),
            "sha256": "7" * 64,
        },
        "attempt_id": "attempt-001",
        "runner_files_sha256": {"scripts/wp12_runner/pytest_provenance_plugin.py": "8" * 64},
    }
    errors = validate_manifest_schema(manifest)
    assert errors == ()
    assessment = assess_manifest(manifest, "b" * 64)
    assert assessment.structural_errors == ()
    assert "SEPARATE_OWNER_DECISION_REQUIRED" in assessment.execution_blockers
    assert "WINDOWS_ISOLATION_NOT_VERIFIED" in assessment.execution_blockers
    assert "INDEPENDENT_EVIDENCE_ARCHIVE_NOT_CONFIGURED" in assessment.execution_blockers
    fabricated_attestation = json.loads(json.dumps(manifest))
    fabricated_attestation["execution_context"]["archive"]["execution_attestation"] = "SYSTEM_OBSERVED_CHILD_V1"
    assert validate_manifest_schema(fabricated_attestation)


def test_validate_v4_manifest_uses_separate_science_and_runner_checkouts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.wp12_runner.cli import _validate_mode

    manifest_path = WP12_PREPARATION / "wp12_b_pilot_manifest_v2.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    science = tmp_path / "science"
    runner = tmp_path / "runner"

    def make_repository(root: Path, paths: set[str], branch: str) -> tuple[str, str, dict[str, str]]:
        root.mkdir(parents=True)

        def git(*args: str) -> str:
            result = subprocess.run(
                ["git", *args], cwd=root, check=True, capture_output=True, text=True, timeout=20, shell=False
            )
            return result.stdout.strip()

        git("init", "--initial-branch=" + branch)
        git("config", "user.name", "Synthetic Owner")
        git("config", "user.email", "synthetic@example.invalid")
        hashes: dict[str, str] = {}
        for relative in sorted(paths):
            content = f"synthetic fixture for {relative}\n".encode("utf-8")
            path = root.joinpath(*relative.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            hashes[relative] = hashlib.sha256(content).hexdigest()
        git("add", "--all")
        git("commit", "-m", "synthetic split-checkout fixture")
        return git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}"), hashes

    science_paths = set().union(
        *(
            set(manifest["code_identity"][group])
            for group in ("source_files_sha256", "test_files_sha256", "fixture_files_sha256")
        )
    )
    runner_paths = set(manifest["execution_context"]["runner_files_sha256"])
    science_commit, science_tree, science_hashes = make_repository(science, science_paths, "science-fixture")
    runner_commit, runner_tree, runner_hashes = make_repository(runner, runner_paths, "emptiesvoids-cloud/0.2.12")

    for group in ("source_files_sha256", "test_files_sha256", "fixture_files_sha256"):
        manifest["code_identity"][group] = {path: science_hashes[path] for path in manifest["code_identity"][group]}
    manifest["scientific_identity"] = {"commit": science_commit, "git_tree": science_tree}
    manifest["runner_identity"] = {"commit": runner_commit, "git_tree": runner_tree}
    manifest["target"]["commit"] = runner_commit
    manifest["target"]["git_tree"] = runner_tree
    manifest["execution_context"]["science_checkout"] = {
        "path": str(science),
        "commit": science_commit,
        "git_tree": science_tree,
    }
    manifest["execution_context"]["runner_checkout"] = {
        "path": str(runner),
        "commit": runner_commit,
        "git_tree": runner_tree,
    }
    manifest["execution_context"]["working_directory"] = str(science)
    python_executable = str(tmp_path / "venv" / "Scripts" / "python.exe")
    venv_root = str(tmp_path / "venv")
    evidence_root = str(tmp_path / "evidence")
    destination_path = str(Path(evidence_root) / manifest["campaign_id"] / "attempt-001")
    manifest["tests"]["argv"][0] = python_executable
    for index, argument in enumerate(manifest["tests"]["argv"]):
        if isinstance(argument, str) and argument.startswith("--junitxml="):
            manifest["tests"]["argv"][index] = f"--junitxml={Path(destination_path) / 'junit.xml'}"
    manifest["environment"]["python_executable_path"] = python_executable
    manifest["environment"]["virtual_environment"]["path"] = venv_root
    manifest["execution_context"]["python_executable"] = python_executable
    manifest["execution_context"]["venv_root"] = venv_root
    manifest["execution_context"]["python_base_root"] = str(tmp_path / "python-base")
    manifest["execution_context"]["evidence_root"] = evidence_root
    manifest["execution_context"]["destination_path"] = destination_path
    manifest["execution_context"]["temporary_root"] = str(tmp_path / "temporary")
    manifest["execution_context"]["archive"]["destination"] = str(tmp_path / "sealed-archive")
    manifest["execution_context"]["archive"]["request_root"] = str(tmp_path / "archive-requests")
    owner_decision_root = tmp_path / "owner-decisions"
    manifest["execution_context"]["archive"]["owner_decision_root"] = str(owner_decision_root)
    manifest["execution_context"]["archive"]["manifest_path"] = str(
        owner_decision_root / manifest["campaign_id"] / "manifest-v2.json"
    )
    manifest["execution_context"]["archive"]["python_executable"] = python_executable
    manifest["execution_context"]["archive"]["decision_verifier_script_path"] = str(
        runner / "scripts" / "wp12_runner" / "owner_decision_verifier.py"
    )
    manifest["execution_context"]["archive"]["worker_script_path"] = str(
        runner / "scripts" / "wp12_runner" / "windows" / "Invoke-WP12EvidenceArchiveWorker.ps1"
    )
    manifest["execution_context"]["isolation_attestation"]["path"] = str(tmp_path / "isolation.json")
    manifest["execution_context"]["security_review"]["review_record_path"] = str(tmp_path / "review.json")
    manifest["execution_context"]["plugin_path"] = str(
        runner / "scripts" / "wp12_runner" / "pytest_provenance_plugin.py"
    )
    manifest["execution_context"]["solver_import_root"] = str(science / "src")
    manifest["execution_context"]["pythonpath"] = [str(runner), str(science / "src")]
    manifest["execution_context"]["runner_files_sha256"] = runner_hashes
    temp_manifest = tmp_path / "manifest-v4.json"
    temp_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(
        runner_cli,
        "collect_environment_provenance",
        lambda **kwargs: {"root": str(kwargs["repository_root"]), "declared": kwargs.get("declared", {})},
    )

    assert _validate_mode(temp_manifest, runner) == 0
    valid = json.loads(capsys.readouterr().out)
    assert valid["state"] == "STRUCTURALLY_VALID_NOT_AUTHORIZED"
    assert valid["execution_started"] is False
    assert valid["input_identity_errors"] == []
    assert valid["git"]["commit"] == runner_commit
    assert valid["science_git"]["commit"] == science_commit
    expected_science_records = sum(
        len(manifest["code_identity"][group])
        for group in ("source_files_sha256", "test_files_sha256", "fixture_files_sha256")
    )
    assert len(valid["input_identity_records"]) == expected_science_records + len(runner_hashes)

    altered = science / "src" / "solveur" / "contact" / "entities.py"
    altered.write_text("tampered synthetic source\n", encoding="utf-8")
    assert _validate_mode(temp_manifest, runner) == 2
    blocked = json.loads(capsys.readouterr().out)
    assert blocked["state"] == "BLOCKED"
    assert "SCIENTIFIC_CHECKOUT_IDENTITY_OR_CLEANLINESS_MISMATCH" in blocked["input_identity_errors"]
    assert "SHA256_MISMATCH:src/solveur/contact/entities.py" in blocked["input_identity_errors"]


def test_owner_signature_profile_round_trips_with_ephemeral_synthetic_key() -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from scripts.sign_wp12_owner_decision import sign_owner_decision

    manifest = _execution_manifest_v3()
    manifest_sha = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    now = datetime.now(timezone.utc)
    target = manifest["target"]
    remote = {key: target[key] for key in ("remote_name", "remote_url", "remote_ref")}
    remote.update({"commit": "e" * 40, "git_tree": "f" * 40})
    decision = {
        "schema": "qf-solver-wp12-owner-decision-v4",
        "canonicalization": PROFILE,
        "decision_id": "SYNTHETIC-OWNER-DECISION-01",
        "unit_id": manifest["unit_id"],
        "run_id": "attempt-001",
        "attempt_number": 1,
        "launch_confirmation": "RUN_EXACT_APPROVED_UNIT",
        "isolation_assessment_sha256": manifest["isolation_assessment"]["sha256"],
        "remote_identity": remote,
        "status": "APPROVED",
        "campaign_id": manifest["campaign_id"],
        "manifest_sha256": manifest_sha,
        "target": {key: target[key] for key in ("branch", "commit", "git_tree")},
        "scientific_identity": manifest["scientific_identity"],
        "runner_identity": manifest["runner_identity"],
        "operations": ["EXECUTE_ONE_TEST_NODE"],
        "nodeids": [manifest["tests"]["nodeid"]],
        "environment": manifest["environment"],
        "budgets": {**manifest["resource_limits"]},
        "maximum_attempts": 1,
        "destination": manifest["destination"],
        "owner": {"principal": "synthetic-owner", "display_name": "Synthetic Owner"},
        "owner_key_id": "synthetic-key",
        "decided_utc": now.isoformat(),
        "not_before_utc": (now - timedelta(minutes=1)).isoformat(),
        "expires_utc": (now + timedelta(hours=1)).isoformat(),
        "signature": {"key_id": "synthetic-key"},
    }
    private_key = Ed25519PrivateKey.generate()
    signed = sign_owner_decision(decision, private_key)
    assert validate_owner_decision_structure(signed) == ()
    assert owner_decision_binding_errors(signed, manifest, manifest_sha) == ()

    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    trusted = TrustedOwnerKey(
        "synthetic-key",
        "synthetic-owner",
        base64.b64encode(public_raw).decode("ascii"),
    )
    verified = verify_owner_decision(
        signed,
        trusted_keys={trusted.key_id: trusted},
        manifest_sha256=manifest_sha,
        expected_campaign_id=manifest["campaign_id"],
        expected_scientific_identity=manifest["scientific_identity"],
        expected_runner_identity=manifest["runner_identity"],
        now=now,
    )
    assert verified.authenticated


def test_protected_worker_verifier_binds_synthetic_signature_manifest_and_attempt(tmp_path: Path) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from scripts.sign_wp12_owner_decision import sign_owner_decision
    from scripts.wp12_runner.owner_decision_verifier import verify_authorized_decision

    manifest = _execution_manifest_v3()
    manifest["schema"] = "qf-solver-wp12-execution-manifest-v4"
    science = tmp_path / "science"
    runner = tmp_path / "runner"
    evidence = tmp_path / "evidence" / "WP12-1-PILOT-001" / "attempt-001"
    owner_decisions = tmp_path / "owner-decisions"
    python_path = Path(sys.executable).resolve()
    python_sha = sha256_bytes(python_path.read_bytes())
    science_identity = manifest["scientific_identity"]
    runner_identity = manifest["runner_identity"]
    nodeid = manifest["tests"]["nodeid"]
    destination = "qualification/0_2_12/wp12_evidence/WP12-1-PILOT-001/attempt-001"
    manifest["isolation_assessment"]["runner_account"] = "QF_WP12_RUNNER"
    manifest["isolation_assessment"]["runner_account_sid"] = "S-1-5-21-1-2-3-1001"
    manifest["tests"]["command_profile"] = "qf-wp12-single-node-pytest-v3"
    manifest["tests"]["argv"] = [
        str(python_path),
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "-p",
        "scripts.wp12_runner.pytest_provenance_plugin",
        "-o",
        "addopts=",
        "--noconftest",
        f"--junitxml={evidence / 'junit.xml'}",
        nodeid,
    ]
    manifest["tests"]["argv"][0] = str(python_path)
    manifest["environment"]["platform"] = "synthetic-Windows"
    manifest["environment"]["python_executable_path"] = str(python_path)
    manifest["environment"]["python_executable_sha256"] = python_sha
    manifest["environment"]["venv_executable_sha256"] = python_sha
    manifest["environment"]["virtual_environment"] = {"kind": "venv", "path": str(Path(sys.prefix).resolve())}
    manifest["environment"]["python_version"] = ".".join(map(str, sys.version_info[:3]))
    manifest["execution_context"] = {
        "science_checkout": {"path": str(science), **science_identity},
        "runner_checkout": {"path": str(runner), **runner_identity},
        "python_executable": str(python_path),
        "venv_root": str(Path(sys.prefix).resolve()),
        "python_base_root": str(Path(sys.base_prefix).resolve()),
        "working_directory": str(science),
        "plugin_path": str(runner / "scripts" / "wp12_runner" / "pytest_provenance_plugin.py"),
        "solver_import_root": str(science / "src"),
        "pythonpath": [str(runner), str(science / "src")],
        "requirements_lock_sha256": "9" * 64,
        "inline_fixture": {
            "schema": "qf-wp12-inline-fixture-v1",
            "fixture_id": "WP12-1-PILOT-001-projection-matrices",
            "canonicalization": "qf-wp12-inline-fixture-v1",
            "sha256": "4" * 64,
        },
        "expected_packages": {"pytest": "8.4.1"},
        "expected_native_libraries_sha256": {"numpy/sample.pyd": "a" * 64},
        "thread_environment": manifest["environment"]["thread_environment"],
        "evidence_root": str(evidence.parents[1]),
        "destination_path": str(evidence),
        "temporary_root": str(tmp_path / "temporary"),
        "archive": {
            "status": "NOT_CONFIGURED",
            "method": "ADMINISTRATOR_SEALED_COPY_V1",
            "destination": str(tmp_path / "sealed-archive"),
            "request_root": str(tmp_path / "archive-requests"),
            "owner_decision_root": str(owner_decisions),
            "manifest_path": str(owner_decisions / "WP12-1-PILOT-001" / "manifest-v2.json"),
            "python_executable": str(python_path),
            "python_executable_sha256": python_sha,
            "decision_verifier_script_path": str(runner / "scripts" / "wp12_runner" / "owner_decision_verifier.py"),
            "decision_verifier_script_sha256": "9" * 64,
            "contracts_script_sha256": "a" * 64,
            "owner_trust_script_sha256": "b" * 64,
            "canonicalization_script_sha256": "c" * 64,
            "execution_attestation": "NONE",
            "worker_task_name": r"\QFSolverWP12\ArchiveWorker",
            "worker_script_path": str(
                runner / "scripts" / "wp12_runner" / "windows" / "Invoke-WP12EvidenceArchiveWorker.ps1"
            ),
            "worker_script_sha256": "c" * 64,
            "ack_timeout_seconds": 60,
        },
        "isolation_attestation": {
            "path": str(tmp_path / "isolation.json"),
            "sha256": "6" * 64,
            "status": "NOT_VERIFIED",
        },
        "security_review": {
            "status": "NOT_REVIEWED",
            "review_record_path": str(tmp_path / "review.json"),
            "sha256": "7" * 64,
        },
        "attempt_id": "attempt-001",
        "runner_files_sha256": {"scripts/wp12_runner/pytest_provenance_plugin.py": "8" * 64},
    }
    manifest["destination"] = destination
    manifest["unit_id"] = "WP12-1-PILOT-001-UNIT-01"
    manifest_path = owner_decisions / "WP12-1-PILOT-001" / "manifest-v2.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2), encoding="utf-8")
    manifest_sha = sha256_bytes(manifest_path.read_bytes())
    assert validate_manifest_schema(manifest) == ()

    now = datetime.now(timezone.utc)
    target = manifest["target"]
    decision: dict[str, Any] = {
        "schema": "qf-solver-wp12-owner-decision-v4",
        "canonicalization": PROFILE,
        "decision_id": "SYNTHETIC-OWNER-01",
        "unit_id": manifest["unit_id"],
        "run_id": "attempt-001",
        "attempt_number": 1,
        "launch_confirmation": "RUN_EXACT_APPROVED_UNIT",
        "isolation_assessment_sha256": manifest["isolation_assessment"]["sha256"],
        "remote_identity": {
            "remote_name": "origin",
            "remote_url": "https://github.com/emptiesvoid-cloud/QF_solver.git",
            "remote_ref": "refs/heads/emptiesvoids-cloud/0.2.12",
            "commit": target["commit"],
            "git_tree": target["git_tree"],
        },
        "status": "APPROVED",
        "campaign_id": manifest["campaign_id"],
        "manifest_sha256": manifest_sha,
        "target": {key: target[key] for key in ("branch", "commit", "git_tree")},
        "scientific_identity": science_identity,
        "runner_identity": runner_identity,
        "operations": ["EXECUTE_ONE_TEST_NODE"],
        "nodeids": [nodeid],
        "environment": manifest["environment"],
        "budgets": manifest["resource_limits"],
        "maximum_attempts": 1,
        "destination": destination,
        "owner": {"principal": "synthetic-owner", "display_name": "Synthetic Owner"},
        "owner_key_id": "synthetic-owner-key",
        "decided_utc": now.isoformat(),
        "not_before_utc": (now - timedelta(minutes=1)).isoformat(),
        "expires_utc": (now + timedelta(hours=1)).isoformat(),
        "signature": {"key_id": "synthetic-owner-key"},
    }
    private_key = Ed25519PrivateKey.generate()
    signed = sign_owner_decision(decision, private_key)
    decision_path = owner_decisions / manifest["campaign_id"] / f"{signed['decision_id']}.json"
    decision_path.parent.mkdir(parents=True, exist_ok=True)
    decision_path.write_text(json.dumps(signed, sort_keys=True, indent=2), encoding="utf-8")
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    trusted = TrustedOwnerKey("synthetic-owner-key", "synthetic-owner", base64.b64encode(public_raw).decode("ascii"))
    report = verify_authorized_decision(
        runner_root=runner,
        decision_path=decision_path,
        manifest_path=manifest_path,
        campaign_id=manifest["campaign_id"],
        decision_id=signed["decision_id"],
        unit_id=manifest["unit_id"],
        run_id="attempt-001",
        manifest_sha256=manifest_sha,
        nodeid=nodeid,
        attempt_number=1,
        destination=destination,
        scientific_identity=science_identity,
        runner_identity=runner_identity,
        trusted_keys={trusted.key_id: trusted},
    )
    assert report["authenticated"] is True, report["errors"]
    mismatched_run = verify_authorized_decision(
        runner_root=runner,
        decision_path=decision_path,
        manifest_path=manifest_path,
        campaign_id=manifest["campaign_id"],
        decision_id=signed["decision_id"],
        unit_id=manifest["unit_id"],
        run_id="attempt-002",
        manifest_sha256=manifest_sha,
        nodeid=nodeid,
        attempt_number=1,
        destination=destination,
        scientific_identity=science_identity,
        runner_identity=runner_identity,
        trusted_keys={trusted.key_id: trusted},
    )
    assert mismatched_run["authenticated"] is False
    assert any("run ID" in error for error in mismatched_run["errors"])


def test_approved_command_builder_rejects_arbitrary_pytest_flags(tmp_path: Path) -> None:
    from scripts.wp12_runner.inline_fixtures import PILOT_NODEID

    science_root = tmp_path / "science"
    evidence_dir = tmp_path / "evidence" / "attempt-001"
    science_root.mkdir()
    evidence_dir.mkdir(parents=True)
    relative_junit = os.path.relpath(evidence_dir / "junit.xml", science_root).replace("\\", "/")
    exact = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "-p",
        "scripts.wp12_runner.pytest_provenance_plugin",
        "-o",
        "addopts=",
        "--noconftest",
        f"--junitxml={relative_junit}",
        PILOT_NODEID,
    ]
    validate_approved_pilot_command(
        exact,
        cwd=science_root,
        run_directory=evidence_dir,
        python_executable=sys.executable,
        expected_nodeid=PILOT_NODEID,
    )
    with pytest.raises(ContractError, match="exact WP12-1 pilot"):
        validate_approved_pilot_command(
            [*exact[:-1], "-k", "modal"],
            cwd=science_root,
            run_directory=evidence_dir,
            python_executable=sys.executable,
            expected_nodeid=PILOT_NODEID,
        )


def test_production_process_launcher_refuses_before_starting_any_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scripts.wp12_runner.process as process_module
    from scripts.wp12_runner.evidence import reserve_pilot_evidence_directory

    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    run_directory = reserve_pilot_evidence_directory(evidence_root, "WP12-1-PILOT-001", "attempt-001", "a" * 64)
    cwd = tmp_path / "science"
    cwd.mkdir()
    nodeid = "tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form"
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "-p",
        "scripts.wp12_runner.pytest_provenance_plugin",
        "-o",
        "addopts=",
        "--noconftest",
        f"--junitxml={run_directory}\\junit.xml",
        nodeid,
    ]
    limits = {
        "wall_seconds": 60,
        "cpu_seconds": 30,
        "memory_bytes": 1024 * 1024,
        "process_count": 2,
        "thread_count": 1,
        "temporary_storage_bytes": 1024,
        "stdout_bytes": 1024,
        "stderr_bytes": 1024,
        "enforcement": {
            "wall": "hard",
            "cpu": "hard",
            "memory": "hard",
            "process_tree": "hard",
            "storage": "hard",
            "logs": "hard",
            "threads": "hard",
        },
    }
    threads = {
        name: "1"
        for name in (
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
            "BLIS_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS",
            "NUMEXPR_NUM_THREADS",
        )
    }
    monkeypatch.setattr(
        process_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail("production launcher started a process before child attestation"),
    )
    with pytest.raises(ContractError, match="SYSTEM_CHILD_PROCESS_ATTESTATION_NOT_IMPLEMENTED"):
        run_approved_pilot_process(
            command,
            campaign_id="WP12-1-PILOT-001",
            run_id="attempt-001",
            nodeid=nodeid,
            manifest_sha256="a" * 64,
            cwd=cwd,
            run_directory=run_directory,
            environment=threads,
            resource_limits=limits,
        )
    assert (run_directory / ".reservation.json").is_file()


def test_pilot_inline_fixture_identity_is_extracted_without_importing_solver() -> None:
    from scripts.wp12_runner.inline_fixtures import fixture_sha256, projection_pilot_fixture

    source_path = ROOT / "tests" / "unit" / "test_modal_symmetric_projection.py"
    loaded_solver_modules = {name for name in sys.modules if name == "solveur" or name.startswith("solveur.")}
    fixture = projection_pilot_fixture(source_path.read_bytes())
    assert fixture["nodeid"].endswith("test_structured_symmetric_projection_matches_dense_bilinear_form")
    assert len(fixture_sha256(fixture)) == 64
    loaded_solver_modules_after = {name for name in sys.modules if name == "solveur" or name.startswith("solveur.")}
    assert loaded_solver_modules_after <= loaded_solver_modules


def test_execute_pilot_denies_without_owner_decision_before_manifest_access(tmp_path: Path) -> None:
    from scripts.wp12_runner.scientific_execution import execute_pilot

    event = execute_pilot(
        runner_root=ROOT,
        manifest_path=tmp_path / "absent-manifest.json",
        owner_decision_path=None,
        supplied_manifest_sha256=None,
    )
    assert event["status"] == "DENY_EXECUTION"
    assert event["execution_started"] is False
    assert event["blockers"] == ["OWNER_DECISION_ABSENT"]


def test_execute_requires_machine_trust_before_opening_manifest(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    refusal_records: list[dict[str, object]] = []

    def record(_directory: Path, event: dict[str, object], *, allowed_root: Path) -> Path:
        refusal_records.append(dict(event))
        return tmp_path / "refusal.json"

    monkeypatch.setattr(runner_cli, "record_refusal", record)
    result = runner_cli._execute_mode(
        tmp_path / "manifest.json",
        tmp_path / "owner.json",
        "f" * 64,
        None,
        ROOT,
    )
    output = json.loads(capsys.readouterr().err)
    assert result == 3
    assert output["status"] == "DENY_EXECUTION"
    assert output["execution_started"] is False
    assert output["attempt_reserved"] is False
    assert output["blockers"] == ["OWNER_TRUST_STORE_NOT_CONFIGURED_OR_INVALID"]
    assert len(refusal_records) == 1


def test_scientific_execution_rejects_untrusted_decision_before_manifest_access(tmp_path: Path) -> None:
    from scripts.wp12_runner.scientific_execution import execute_pilot

    event = execute_pilot(
        runner_root=ROOT,
        manifest_path=tmp_path / "manifest.json",
        owner_decision_path=tmp_path / "decision.json",
        supplied_manifest_sha256="f" * 64,
    )
    assert event["status"] == "DENY_EXECUTION"
    assert event["execution_started"] is False
    assert event["attempt_reserved"] is False
    assert event["blockers"] == ["OWNER_TRUST_STORE_NOT_CONFIGURED_OR_INVALID"]


def test_trust_status_reports_only_public_metadata(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    public_bytes = b"p" * 32
    key = TrustedOwnerKey("synthetic-key", "synthetic-owner", base64.b64encode(public_bytes).decode("ascii"))
    monkeypatch.setattr(
        "scripts.wp12_runner.owner_trust.load_machine_trust_store",
        lambda _root: ({key.key_id: key}, "a" * 64),
    )
    assert runner_cli._trust_status_mode(ROOT) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["state"] == "VERIFIED_READ_ONLY"
    assert output["keys"][0]["key_id"] == "synthetic-key"
    assert "public_key_base64" not in output["keys"][0]
    assert output["private_key_accessed"] is False


def test_remote_identity_requires_signed_advertisement_and_does_not_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.wp12_runner.contracts as contracts

    remote_commit = "c" * 40
    remote_tree = "d" * 40
    target = {
        "branch": "emptiesvoids-cloud/0.2.12",
        "commit": COMMIT,
        "git_tree": TREE,
        "remote_name": "origin",
        "remote_url": "https://github.com/emptiesvoid-cloud/QF_solver.git",
        "remote_ref": "refs/heads/emptiesvoids-cloud/0.2.12",
    }
    owner = {
        "remote_identity": {
            "remote_name": "origin",
            "remote_url": target["remote_url"],
            "remote_ref": target["remote_ref"],
            "commit": remote_commit,
            "git_tree": remote_tree,
        }
    }
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        calls.append(command)
        if command[1:3] == ["config", "--get"]:
            return SimpleNamespace(returncode=0, stdout=target["remote_url"], stderr="")
        if command[1] == "ls-remote":
            return SimpleNamespace(returncode=0, stdout=f"{remote_commit}\t{target['remote_ref']}\n", stderr="")
        if command[1:3] == ["rev-parse", f"{remote_commit}^{{tree}}"]:
            return SimpleNamespace(returncode=0, stdout=remote_tree, stderr="")
        if command[1:3] == ["merge-base", "--is-ancestor"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected git call: {command}")

    monkeypatch.setattr(contracts.subprocess, "run", fake_run)
    assert remote_identity_issues(ROOT, target, owner) == ()
    assert all(command[1] != "fetch" for command in calls)
    owner["remote_identity"]["commit"] = "e" * 40
    assert remote_identity_issues(ROOT, target, owner) == ("REMOTE_COMMIT_MISMATCH",)


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
    assert "OWNER_DECISION_ABSENT" in mismatch


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
    assert "OWNER_DECISION_UNAUTHENTICATED" in blockers
    assert "MANIFEST_PREPARED_NOT_AUTHORIZED" in blockers


def test_owner_decision_binding_rejects_changed_nodeid_and_commit() -> None:
    manifest = _manifest()
    digest = "1" * 64
    decision = _decision(manifest, digest)
    decision["nodeids"] = ["tests/unit/test_other.py::test_case"]
    decision["target"] = {"branch": "emptiesvoids-cloud/0.2.12", "commit": "9" * 40, "git_tree": TREE}
    errors = owner_decision_binding_errors(decision, manifest, digest)
    assert any("nodeids" in error for error in errors)
    assert any("commit" in error for error in errors)


def _signed_synthetic_decision(
    manifest: dict[str, object], digest: str
) -> tuple[dict[str, object], dict[str, TrustedOwnerKey]]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.generate()
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    decision = _decision(manifest, digest)
    payload = canonical_payload(decision)
    decision["signature"] = {
        "algorithm": "ed25519",
        "key_id": "synthetic-key",
        "public_key_sha256": hashlib.sha256(public_bytes).hexdigest(),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "signature_base64": base64.b64encode(private_key.sign(payload)).decode("ascii"),
    }
    return decision, {
        "synthetic-key": TrustedOwnerKey(
            "synthetic-key", "synthetic-owner", base64.b64encode(public_bytes).decode("ascii")
        )
    }


def test_ed25519_owner_decision_authentication_and_fail_closed_bindings() -> None:
    manifest = _manifest()
    digest = "a" * 64
    decision, keys = _signed_synthetic_decision(manifest, digest)
    expected = {"commit": COMMIT, "git_tree": TREE}
    common = {
        "trusted_keys": keys,
        "manifest_sha256": digest,
        "expected_campaign_id": "WP12-SYNTHETIC",
        "expected_scientific_identity": expected,
        "expected_runner_identity": expected,
        "now": datetime(2026, 10, 25, tzinfo=timezone.utc),
    }
    assert verify_owner_decision(decision, **common).authenticated
    assert not verify_owner_decision({**decision, "manifest_sha256": "b" * 64}, **common).authenticated
    assert not verify_owner_decision(decision, **{**common, "trusted_keys": {}}).authenticated
    revoked = {
        "synthetic-key": TrustedOwnerKey(
            "synthetic-key", "synthetic-owner", keys["synthetic-key"].public_key_base64, revoked=True
        )
    }
    assert not verify_owner_decision(decision, **{**common, "trusted_keys": revoked}).authenticated
    assert not verify_owner_decision(
        decision,
        **{**common, "expected_runner_identity": {"commit": "c" * 40, "git_tree": TREE}},
    ).authenticated
    assert not verify_owner_decision(
        decision,
        **{**common, "now": datetime(2028, 1, 1, tzinfo=timezone.utc)},
    ).authenticated
    tampered_signature = json.loads(json.dumps(decision))
    tampered_signature["signature"]["signature_base64"] = base64.b64encode(b"x" * 64).decode("ascii")
    assert not verify_owner_decision(tampered_signature, **common).authenticated


@pytest.mark.skipif(os.name != "nt", reason="machine-scoped trust store is Windows-specific")
def test_machine_trust_store_requires_hklm_sha256_pin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    public_key = base64.b64encode(b"p" * 32).decode("ascii")
    trust_bytes = (
        json.dumps(
            {
                "schema": "qf-wp12-owner-trust-store-v1",
                "keys": [
                    {
                        "key_id": "synthetic-machine-key",
                        "principal": "synthetic-owner",
                        "public_key_base64": public_key,
                        "revoked": False,
                    }
                ],
            },
            sort_keys=True,
        )
    ).encode("utf-8")
    trust_path = tmp_path / "owner-trust.json"
    trust_path.write_bytes(trust_bytes)

    class RegistryKey:
        def __enter__(self) -> "RegistryKey":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    values = {
        TRUST_STORE_PATH_VALUE: str(trust_path),
        TRUST_STORE_SHA_VALUE: hashlib.sha256(trust_bytes).hexdigest(),
    }

    def open_key(_hive: object, _path: str, _reserved: int, access: int) -> RegistryKey:
        if access == 2:
            raise PermissionError("synthetic read-only machine key")
        return RegistryKey()

    fake_registry = SimpleNamespace(
        HKEY_LOCAL_MACHINE=object(),
        KEY_READ=1,
        KEY_SET_VALUE=2,
        OpenKey=open_key,
        QueryValueEx=lambda _key, name: (values[name], 1),
    )
    monkeypatch.setitem(sys.modules, "winreg", fake_registry)
    import scripts.wp12_runner.owner_trust as owner_trust_module

    real_open = owner_trust_module.os.open

    def read_only_open(path: str | Path, flags: int, *args: object, **kwargs: object) -> int:
        if Path(path) == trust_path and flags & os.O_WRONLY:
            raise PermissionError("synthetic read-only trust file")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(owner_trust_module.os, "open", read_only_open)
    monkeypatch.setattr(owner_trust_module.os, "access", lambda *_args: False)
    keys, digest = load_machine_trust_store(ROOT)
    assert digest == values[TRUST_STORE_SHA_VALUE]
    assert keys["synthetic-machine-key"].principal == "synthetic-owner"
    values[TRUST_STORE_SHA_VALUE] = "0" * 64
    with pytest.raises(ContractError, match="do not match"):
        load_machine_trust_store(ROOT)


def test_attempt_ledger_preserves_failures_and_rejects_reuse_or_partial_lines(tmp_path: Path) -> None:
    ledger = AttemptLedger(tmp_path / "attempts.jsonl", allowed_root=tmp_path)

    def start(run_id: str, attempt: int) -> None:
        ledger.start_attempt(
            campaign_id="WP12-SYNTHETIC",
            manifest_sha256="a" * 64,
            run_id=run_id,
            nodeid=NODEID,
            attempt=attempt,
            maximum_attempts=2,
            git_identity={"commit": COMMIT, "git_tree": TREE},
            started_utc="2026-10-25T10:00:00Z",
        )

    start("run-001", 1)
    with pytest.raises(ContractError, match="still open"):
        start("run-002", 2)
    ledger.finish_attempt(
        run_id="run-001",
        status="FAIL",
        finished_utc="2026-10-25T10:00:01Z",
        reason="synthetic failure preserved",
        stdout_sha256="b" * 64,
        stderr_sha256="c" * 64,
        evidence_sha256={"synthetic.json": "d" * 64},
    )
    with pytest.raises(ContractError, match="already appeared"):
        start("run-001", 2)
    start("run-002", 2)
    records = ledger.verify()
    assert [record["event"] for record in records] == ["ATTEMPT_STARTED", "ATTEMPT_FINISHED", "ATTEMPT_STARTED"]
    with pytest.raises(ContractError, match="already has a terminal"):
        ledger.finish_attempt(
            run_id="run-001",
            status="PASS",
            finished_utc="2026-10-25T10:00:02Z",
            reason=None,
            stdout_sha256=None,
            stderr_sha256=None,
            evidence_sha256={},
        )
    with (tmp_path / "attempts.jsonl").open("ab") as stream:
        stream.write(b'{"partial":')
    with pytest.raises(ContractError, match="incomplete record"):
        ledger.verify()


def test_attempt_ledger_serializes_concurrent_campaign_appends(tmp_path: Path) -> None:
    ledger = AttemptLedger(tmp_path / "concurrent.jsonl", allowed_root=tmp_path)

    def append_for_campaign(index: int) -> None:
        ledger.start_attempt(
            campaign_id=f"WP12-SYNTH-{index}",
            manifest_sha256=f"{index:064x}",
            run_id=f"run-{index}",
            nodeid=NODEID,
            attempt=1,
            maximum_attempts=1,
            git_identity={"commit": COMMIT, "git_tree": TREE},
            started_utc="2026-10-25T10:00:00Z",
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(append_for_campaign, range(8)))
    records = ledger.verify()
    assert len(records) == 8
    assert [record["sequence"] for record in records] == list(range(1, 9))


def test_interrupted_attempt_requires_reconciliation_and_a_new_run_id(tmp_path: Path) -> None:
    ledger = AttemptLedger(tmp_path / "interrupted.jsonl", allowed_root=tmp_path)
    ledger.start_attempt(
        campaign_id="WP12-SYNTH-INTERRUPT",
        manifest_sha256="a" * 64,
        run_id="run-before-interrupt",
        nodeid=NODEID,
        attempt=1,
        maximum_attempts=2,
        git_identity={"commit": COMMIT, "git_tree": TREE},
        started_utc="2026-10-25T10:00:00Z",
    )
    with pytest.raises(ContractError, match="still open"):
        ledger.start_attempt(
            campaign_id="WP12-SYNTH-INTERRUPT",
            manifest_sha256="a" * 64,
            run_id="run-after-interrupt",
            nodeid=NODEID,
            attempt=2,
            maximum_attempts=2,
            git_identity={"commit": COMMIT, "git_tree": TREE},
            started_utc="2026-10-25T10:01:00Z",
        )
    ledger.finish_attempt(
        run_id="run-before-interrupt",
        status="INTERRUPTED",
        finished_utc="2026-10-25T10:00:30Z",
        reason="synthetic process interrupted",
        stdout_sha256=None,
        stderr_sha256=None,
        evidence_sha256={},
    )
    ledger.start_attempt(
        campaign_id="WP12-SYNTH-INTERRUPT",
        manifest_sha256="a" * 64,
        run_id="run-after-interrupt",
        nodeid=NODEID,
        attempt=2,
        maximum_attempts=2,
        git_identity={"commit": COMMIT, "git_tree": TREE},
        started_utc="2026-10-25T10:01:00Z",
    )
    assert ledger.verify()[-2]["status"] == "INTERRUPTED"
    assert ledger.verify()[-1]["run_id"] == "run-after-interrupt"


def test_environment_provenance_is_static_and_marks_child_import_unverifiable() -> None:
    provenance = collect_environment_provenance(
        repository_root=ROOT,
        source_files=("scripts/wp12_runner/environment.py",),
        test_files=("tests/unit/test_wp12_qualification_runner.py",),
        fixture_files=("tests/fixtures/wp12_runner/fake_child.py",),
    )
    assert provenance["observed"]["python"]["sha256"]
    assert provenance["observed"]["inputs"]["sources"][0]["state"] == "OBSERVED_FILE"
    assert provenance["observed"]["solver_origin"]["actual_child_import_origin"] is None
    assert any("BLAS/LAPACK" in item for item in provenance["unverifiable"])


def test_explicit_remote_sync_uses_exact_non_force_refspec(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.wp12_runner.git_remote as git_remote

    bare = tmp_path / "origin.git"
    repository = tmp_path / "repo"
    bare.mkdir()
    repository.mkdir()

    def git(cwd: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=cwd, check=True, capture_output=True, text=True, timeout=20, shell=False
        )
        return result.stdout.strip()

    git(bare, "init", "--bare")
    git(repository, "init", "--initial-branch=emptiesvoids-cloud/0.2.12")
    git(repository, "config", "user.name", "Synthetic Owner")
    git(repository, "config", "user.email", "synthetic@example.invalid")
    (repository / "README.synthetic").write_text("synthetic git identity fixture\n", encoding="utf-8")
    git(repository, "add", "README.synthetic")
    git(repository, "commit", "-m", "synthetic identity fixture")
    git(repository, "remote", "add", "origin", str(bare))
    git(repository, "push", "-u", "origin", "emptiesvoids-cloud/0.2.12")
    monkeypatch.setattr(
        git_remote, "_assert_expected_origin", lambda _root: "https://github.com/emptiesvoid-cloud/QF_solver.git"
    )
    identity = sync_remote_identity(repository)
    assert identity.local_commit == identity.remote_commit
    assert identity.local_tree == identity.remote_tree
    assert identity.local_is_ancestor
    receipt = write_sync_receipt(repository, identity, repository / ".codex" / "wp12_runner_audit")
    assert receipt.is_file()


def test_scientific_commit_ancestry_is_checked_without_fetch(tmp_path: Path) -> None:
    repository = tmp_path / "ancestry"
    repository.mkdir()

    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=repository, check=True, capture_output=True, text=True, timeout=20, shell=False
        )
        return result.stdout.strip()

    git("init", "--initial-branch=synthetic")
    git("config", "user.name", "Synthetic Owner")
    git("config", "user.email", "synthetic@example.invalid")
    document = repository / "candidate.txt"
    document.write_text("scientific source identity\n", encoding="utf-8")
    git("add", "candidate.txt")
    git("commit", "-m", "synthetic scientific base")
    science_commit = git("rev-parse", "HEAD")
    science_tree = git("rev-parse", "HEAD^{tree}")
    document.write_text("runner infrastructure only\n", encoding="utf-8")
    git("commit", "-am", "synthetic runner descendant")
    runner_commit = git("rev-parse", "HEAD")
    runner_tree = git("rev-parse", "HEAD^{tree}")
    assert git_commit_is_ancestor(repository, science_commit, runner_commit)
    assert not git_commit_is_ancestor(repository, runner_commit, science_commit)
    assert git_commit_tree_matches(repository, science_commit, science_tree)
    assert not git_commit_tree_matches(repository, science_commit, runner_tree)


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


def test_static_manifest_identity_check_preserves_c02_overlay_and_c01_mismatch(tmp_path: Path) -> None:
    source_manifest, _digest = load_json(WP12_PREPARATION / "wp12_3_execution_manifest.json")
    source_entries = source_manifest["fixtures"]["entries"]
    source_c01 = next(entry for entry in source_entries if entry.get("id") == "C01 R19 model fixture")
    source_overlay = next(entry for entry in source_entries if entry.get("id") == "Frozen AJ mesh/load helper")
    assert source_c01["status"] == "CONFLICT_REQUIRES_OWNER_RESOLUTION"
    assert source_c01["expected_sha256_in_test"] == "b74c57cae86d94b4cbfdae0c298ea98aa660f70159c72eb4b72f0ee4b5eee3e5"
    assert source_c01["byte_sha256"] == "a732254d59268aace44e44e2a21f5619d4c267531c388eed1aab0bb09fb2def0"
    assert source_overlay["availability"].startswith("MISSING;")
    assert not (ROOT / source_overlay["path"]).exists()

    repository = tmp_path / "synthetic"
    repository.mkdir()

    def git(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args], cwd=repository, check=True, capture_output=True, text=True
        )
        return completed.stdout.strip()

    git("init", "--initial-branch=synthetic")
    git("config", "user.name", "Synthetic Owner")
    git("config", "user.email", "synthetic@users.noreply.github.com")
    c01_relative = "examples/c01_fixture.json"
    overlay_relative = "tests/unit/frozen_overlay.py"
    c01_path = repository / c01_relative
    overlay_path = repository / overlay_relative
    c01_path.parent.mkdir(parents=True)
    overlay_path.parent.mkdir(parents=True)
    c01_bytes = b"synthetic C01 fixture\n"
    overlay_bytes = b"synthetic historical overlay\n"
    c01_path.write_bytes(c01_bytes)
    overlay_path.write_bytes(overlay_bytes)
    git("add", "--all")
    git("commit", "--quiet", "-m", "synthetic fixture source")
    source_commit = git("rev-parse", "HEAD")
    overlay_oid = git("rev-parse", f"{source_commit}:{overlay_relative}")
    overlay_path.unlink()
    git("add", "--all")
    git("commit", "--quiet", "-m", "synthetic overlay omitted")
    target_commit = git("rev-parse", "HEAD")
    c01_oid = git("rev-parse", f"{target_commit}:{c01_relative}")
    c01_sha = hashlib.sha256(c01_bytes).hexdigest()
    manifest = {
        "target": {"commit": target_commit},
        "fixtures": {
            "entries": [
                {
                    "id": "synthetic-C01",
                    "path": c01_relative,
                    "source_commit": target_commit,
                    "git_blob_oid": c01_oid,
                    "byte_sha256": c01_sha,
                    "expected_sha256_in_test": "0" * 64,
                },
                {
                    "id": "synthetic-overlay",
                    "path": overlay_relative,
                    "source_commit": source_commit,
                    "git_blob_oid": overlay_oid,
                    "byte_sha256": hashlib.sha256(overlay_bytes).hexdigest(),
                },
            ]
        },
    }
    errors, records = verify_manifest_input_identities(repository, manifest)

    assert errors == (f"FIXTURE_CONTRACT_DIGEST_MISMATCH:{c01_relative}",)
    overlay_records = [record for record in records if record.get("state") == "OVERLAY_IDENTIFIED_NOT_MATERIALIZED"]
    assert len(overlay_records) == 1
    assert overlay_records[0]["path"] == overlay_relative


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


def test_execution_safe_path_rejects_symlinked_ancestor(tmp_path: Path) -> None:
    from scripts.wp12_runner.scientific_execution import _safe_path

    actual_root = tmp_path / "actual"
    actual_root.mkdir()
    target = actual_root / "probe.txt"
    target.write_text("synthetic path probe", encoding="utf-8")
    link = tmp_path / "alias"
    try:
        link.symlink_to(actual_root, target_is_directory=True)
    except OSError:
        pytest.skip("this Windows account cannot create a synthetic directory symlink")

    assert _safe_path(str(link / "probe.txt")) is None


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
    assert refusal["blockers"] == ["OWNER_DECISION_ABSENT"]


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
    if os.name == "nt":
        assert outcome.hard_job_enforced


def test_self_test_cli_runs_only_the_fixed_synthetic_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    reports: list[dict[str, object]] = []
    monkeypatch.setattr(runner_cli, "_json_print", lambda value, **_kwargs: reports.append(dict(value)))
    assert runner_main(["--mode", "SELF_TEST", "--case", "all"]) == 0
    assert len(reports) == 1
    report = reports[0]
    assert report["scientific_execution"] is False
    expected_state = "PASS_WITH_NOT_APPLICABLE" if os.name != "nt" else "PASS"
    assert report["state"] == expected_state
    assert report["campaign_id"] == "WP12-X-SYNTHETIC-ORCHESTRATOR"
    assert report["result_kind"] == "SYNTHETIC_RUNNER_SELF_TEST"
    assert report["journal_chain_verified"] is True
    assert report["journal_record_count"] == 16
    assert report["temporary_evidence_discarded_after_report"] is True
    assert len(report["plan_sha256"]) == 64
    assert {item["case"] for item in report["results"]} == {
        "success",
        "exit",
        "sleep",
        "tree",
        "flood",
        "memory",
        "cpu",
    }
    assert all(item["self_test"] in {"PASS", "NOT_APPLICABLE"} for item in report["results"])
    assert len({item["run_id"] for item in report["results"]}) == len(report["results"])
    assert all(item["attempt"] == item["maximum_attempts"] == 1 for item in report["results"])
    assert all(item["scientific_result"] is False for item in report["results"])
    assert all("nodeid" not in item for item in report["results"])
    assert all(item["self_test"] == "NOT_APPLICABLE" or len(item["receipt_sha256"]) == 64 for item in report["results"])


def test_synthetic_orchestrator_rejects_unknown_cases_and_real_execute_enablement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ContractError, match="fixed synthetic case IDs"):
        synthetic_orchestrator.run_synthetic_orchestration("tests/unit/test_anything.py::test_case")

    monkeypatch.setattr(synthetic_orchestrator, "REAL_EXECUTION_ENABLED", True)
    with pytest.raises(ContractError, match="scientific EXECUTE is enabled"):
        synthetic_orchestrator.run_synthetic_orchestration("success")


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object memory enforcement is platform-specific")
def test_hard_job_memory_limit_terminates_synthetic_allocator(tmp_path: Path) -> None:
    outcome = run_fake_process(
        "memory",
        tmp_path / "memory-limit",
        timeout_seconds=8,
        output_byte_limit=4096,
        process_count_limit=4,
        memory_hard_limit_bytes=64 * 1024 * 1024,
    )
    assert outcome.hard_job_enforced
    assert outcome.return_code not in (None, 0)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object CPU-time enforcement is platform-specific")
def test_hard_job_cpu_time_limit_terminates_synthetic_spinner(tmp_path: Path) -> None:
    outcome = run_fake_process(
        "cpu",
        tmp_path / "cpu-limit",
        timeout_seconds=8,
        output_byte_limit=4096,
        process_count_limit=4,
        cpu_hard_limit_seconds=1,
    )
    assert outcome.hard_job_enforced
    assert outcome.cpu_limit_exceeded
    assert outcome.state == "RESOURCE_LIMIT"


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
    passed = b'<testsuite tests="1" failures="0" errors="0" skipped="0"><testcase classname="tests.unit.test_synthetic" name="test_case" /></testsuite>'
    failed = b'<testsuite tests="1" failures="1" errors="0" skipped="0"><testcase classname="test_synthetic" name="test_case"><failure /></testcase></testsuite>'
    skipped = b'<testsuite tests="1" failures="0" errors="0" skipped="1"><testcase classname="test_synthetic" name="test_case"><skipped /></testcase></testsuite>'
    assert classify_pytest_junit(passed, NODEID) == "PASS"
    assert classify_pytest_junit(failed, NODEID) == "FAIL"
    assert classify_pytest_junit(skipped, NODEID) == "INCONCLUSIVE"
    process = ProcessOutcome("PROCESS_EXITED", 1, None, 0.1, 0, 0, 10, 1, ())
    assert classify_process_result(process, failed, NODEID) == "FAIL"
    assert classify_process_result(process, None, NODEID) == "INFRA_ERROR"
    assert (
        classify_process_result(ProcessOutcome("PROCESS_EXITED", 0, None, 0.1, 0, 0, 10, 1, ()), failed, NODEID)
        == "INFRA_ERROR"
    )
    wrapped_pass = b'<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"><testcase classname="tests.unit.test_synthetic" name="test_case" /></testsuite></testsuites>'
    evil_wrapper = b'<evil><testsuite tests="1" failures="0" errors="0" skipped="0"><testcase classname="tests.unit.test_synthetic" name="test_case" /></testsuite></evil>'
    multiple_suites = b'<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"><testcase classname="tests.unit.test_synthetic" name="test_case" /></testsuite><testsuite tests="0" failures="0" errors="0" skipped="0" /></testsuites>'
    multiple_cases = b'<testsuite tests="2" failures="0" errors="0" skipped="0"><testcase classname="tests.unit.test_synthetic" name="test_case" /><testcase classname="tests.unit.test_synthetic" name="test_case" /></testsuite>'
    assert classify_pytest_junit(wrapped_pass, NODEID) == "PASS"
    assert classify_pytest_junit(evil_wrapper, NODEID) == "INFRA_ERROR"
    assert classify_pytest_junit(multiple_suites, NODEID) == "INFRA_ERROR"
    assert classify_pytest_junit(multiple_cases, NODEID) == "INFRA_ERROR"
    assert (
        classify_process_result(ProcessOutcome("PROCESS_EXITED", 2, None, 0.1, 0, 0, 10, 1, ()), failed, NODEID)
        == "INFRA_ERROR"
    )
    contradictory = b'<testsuite tests="1" failures="0" errors="0" skipped="0"><testcase classname="tests.unit.test_synthetic" name="test_case"><failure /></testcase></testsuite>'
    assert classify_pytest_junit(contradictory, NODEID) == "INFRA_ERROR"


def test_pilot_evidence_destination_is_reserved_once_and_bound_to_the_manifest(tmp_path: Path) -> None:
    from scripts.wp12_runner.evidence import verify_pilot_evidence_reservation

    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    run = reserve_pilot_evidence_directory(evidence_root, "WP12-1-PILOT-001", "attempt-001", "a" * 64)
    assert (
        verify_pilot_evidence_reservation(
            run,
            campaign_id="WP12-1-PILOT-001",
            run_id="attempt-001",
            manifest_sha256="a" * 64,
        )
        == ()
    )
    assert verify_pilot_evidence_reservation(
        run,
        campaign_id="WP12-1-PILOT-001",
        run_id="attempt-001",
        manifest_sha256="b" * 64,
    )
    with pytest.raises(FileExistsError):
        reserve_pilot_evidence_directory(evidence_root, "WP12-1-PILOT-001", "attempt-001", "a" * 64)


def test_pilot_evidence_reservation_rejects_a_prepopulated_destination(tmp_path: Path) -> None:
    from scripts.wp12_runner.evidence import verify_pilot_evidence_reservation

    root = tmp_path / "evidence"
    root.mkdir()
    run = reserve_pilot_evidence_directory(root, "WP12-1-PILOT-001", "attempt-001", "a" * 64)
    (run / "unexpected.txt").write_text("synthetic", encoding="utf-8")
    errors = verify_pilot_evidence_reservation(
        run,
        campaign_id="WP12-1-PILOT-001",
        run_id="attempt-001",
        manifest_sha256="a" * 64,
    )
    assert errors == ("reserved evidence directory is not empty",)


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


def test_import_probe_child_resolves_only_the_declared_synthetic_source(tmp_path: Path) -> None:
    package = tmp_path / "src" / "solveur"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("from importlib import import_module\n", encoding="utf-8")
    (package / "version.py").write_text('__version__ = "synthetic"\n', encoding="utf-8")

    report = probe_solver_import(Path(sys.executable), tmp_path)

    assert report["state"] == "SOURCE_IMPORT_VERIFIED"
    assert report["scientific_source_root"] == str(tmp_path.resolve())
    assert report["solveur_file"] == str((package / "__init__.py").resolve())
    assert report["version"] == "synthetic"
    assert report["fem_or_analysis_api_called"] is False


def test_provenance_plugin_accepts_pinned_inventory_superset_with_only_fake_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.wp12_runner.pytest_provenance_plugin import WP12ProvenancePlugin
    import types

    science = tmp_path / "science"
    source = science / "src" / "solveur" / "__init__.py"
    evidence = tmp_path / "evidence"
    source.parent.mkdir(parents=True)
    evidence.mkdir()
    source.write_text("# synthetic package marker\n", encoding="utf-8")
    not_imported_source = source.parent / "not_imported.py"
    not_imported_source.write_text("# declared but not imported\n", encoding="utf-8")
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    not_imported_digest = hashlib.sha256(not_imported_source.read_bytes()).hexdigest()
    monkeypatch.setenv("QF_WP12_EXPECTED_NODEID", NODEID)
    plugin_path = Path(__file__).resolve().parents[2] / "scripts" / "wp12_runner" / "pytest_provenance_plugin.py"
    monkeypatch.setenv("QF_WP12_EXPECTED_PLUGIN_PATH", str(plugin_path))
    monkeypatch.setenv("QF_WP12_EXPECTED_PLUGIN_SHA256", hashlib.sha256(plugin_path.read_bytes()).hexdigest())
    monkeypatch.setenv("QF_WP12_SOLVER_ROOT", str(science / "src"))
    monkeypatch.setenv("QF_WP12_EVIDENCE_ROOT", str(evidence))
    monkeypatch.setenv(
        "QF_WP12_EXPECTED_SOURCE_HASHES",
        json.dumps(
            {
                "src/solveur/__init__.py": source_digest,
                "src/solveur/not_imported.py": not_imported_digest,
            }
        ),
    )
    fake = types.ModuleType("solveur")
    fake.__file__ = str(source)
    monkeypatch.setitem(sys.modules, "solveur", fake)
    plugin = WP12ProvenancePlugin()
    item = SimpleNamespace(nodeid=NODEID)
    plugin.pytest_collection_modifyitems(SimpleNamespace(), SimpleNamespace(), [item])
    report = json.loads((evidence / "collection.json").read_text(encoding="utf-8"))
    assert report["collection_valid"] is True
    assert report["plugin_verified"] is True
    assert report["declared_source_hashes_verified"] is True
    assert report["selected_nodeids"] == [NODEID]


def test_owner_trust_store_builder_exports_only_a_synthetic_public_key(tmp_path: Path) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    private_path = tmp_path / "synthetic-owner.pem"
    private_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    document, digest = build_public_trust_store(
        private_path,
        key_id="synthetic-owner-key",
        principal="synthetic-owner",
        passphrase="",
        repository_root=ROOT,
    )

    assert document["schema"] == "qf-wp12-owner-trust-store-v1"
    assert document["keys"][0]["key_id"] == "synthetic-owner-key"
    assert len(base64.b64decode(document["keys"][0]["public_key_base64"])) == 32
    assert len(digest) == 64
    assert base64.b64encode(
        key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
    ).decode("ascii") not in json.dumps(document)


def test_system_archive_worker_refuses_forged_reservation_without_protected_owner_decision(
    tmp_path: Path,
) -> None:
    import shutil
    import subprocess

    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("Windows PowerShell is unavailable for the synthetic archive-worker check")
    from scripts.wp12_runner.archive_protocol import create_attempt_reservation_request
    from scripts.wp12_runner.contracts import sha256_file

    request_root = tmp_path / "requests"
    archive_root = tmp_path / "archive"
    evidence_root = tmp_path / "evidence"
    owner_decision_root = tmp_path / "owner-decisions"
    for directory in (request_root, archive_root, evidence_root, owner_decision_root):
        directory.mkdir()
    worker = ROOT / "scripts" / "wp12_runner" / "windows" / "Invoke-WP12EvidenceArchiveWorker.ps1"
    verifier = ROOT / "scripts" / "wp12_runner" / "owner_decision_verifier.py"
    identities = {
        "scientific_commit": "1" * 40,
        "scientific_tree": "2" * 40,
        "runner_commit": "3" * 40,
        "runner_tree": "4" * 40,
    }
    campaign_id = "WP12-1-PILOT-001"
    nodeid = "tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form"
    request_path, _digest, request_id, reservation_key_value = create_attempt_reservation_request(
        request_root=request_root,
        campaign_id=campaign_id,
        decision_id="OWNER-SYNTHETIC-01",
        unit_id="WP12-1-PILOT-001-UNIT-01",
        run_id="attempt-001",
        nodeid=nodeid,
        destination="qualification/0_2_12/wp12_evidence/WP12-1-PILOT-001/attempt-001",
        manifest_sha256="a" * 64,
        owner_decision_sha256="b" * 64,
        identities=identities,
    )
    campaign_owner_root = owner_decision_root / campaign_id
    campaign_owner_root.mkdir()
    manifest_path = campaign_owner_root / "manifest-v2.json"
    manifest_path.write_text(
        json.dumps(
            {
                "campaign_id": campaign_id,
                "status": "FROZEN_NOT_AUTHORIZED",
                "execution_context": {
                    "archive": {
                        "manifest_path": str(manifest_path),
                        "execution_attestation": "NONE",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    manifest_hash = sha256_file(manifest_path)
    worker_hash = sha256_file(worker)
    verifier_hash = sha256_file(verifier)
    contracts_hash = sha256_file(ROOT / "scripts" / "wp12_runner" / "contracts.py")
    owner_trust_hash = sha256_file(ROOT / "scripts" / "wp12_runner" / "owner_trust.py")
    canonicalization_hash = sha256_file(ROOT / "scripts" / "wp12_owner_canonicalization.py")
    python_hash = sha256_file(Path(sys.executable).resolve())
    argv = [
        powershell,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(worker),
        "-RequestRoot",
        str(request_root),
        "-EvidenceRoot",
        str(evidence_root),
        "-ArchiveRoot",
        str(archive_root),
        "-OwnerDecisionRoot",
        str(owner_decision_root),
        "-PythonExecutable",
        str(Path(sys.executable).resolve()),
        "-PythonExecutableSha256",
        python_hash,
        "-VerifierScriptSha256",
        verifier_hash,
        "-ContractsScriptSha256",
        contracts_hash,
        "-OwnerTrustScriptSha256",
        owner_trust_hash,
        "-CanonicalizationScriptSha256",
        canonicalization_hash,
        "-WorkerScriptSha256",
        worker_hash,
        "-ManifestPath",
        str(manifest_path),
        "-ManifestSha256",
        manifest_hash,
        "-RunnerSid",
        "S-1-5-21-1-2-3-1001",
    ]
    result = subprocess.run(argv, capture_output=True, text=True, timeout=20, check=False)
    assert result.returncode == 0, result.stderr
    assert request_path.is_file()
    reservations = archive_root / "_wp12_ledger" / "reservations"
    assert not reservations.exists() or list(reservations.iterdir()) == []
    ack_path = archive_root / "_wp12_ledger" / "reservation-acks" / f"{request_id}.json"
    assert not ack_path.exists()
    assert reservation_key_value


def test_production_pilot_entrypoint_is_unconditionally_fail_closed() -> None:
    from scripts.wp12_runner.pilot_execution import execute_authenticated_pilot_unit

    result = execute_authenticated_pilot_unit(
        manifest={"campaign_id": "synthetic", "unit_id": "synthetic", "tests": {"nodeid": "x"}},
        manifest_sha256="0" * 64,
        owner_decision_sha256="1" * 64,
        owner_decision_id="synthetic",
        context={"attempt_id": "synthetic"},
        environment_report={},
    )

    assert result["status"] == "DENY_EXECUTION"
    assert result["reason"] == "SYSTEM_CHILD_PROCESS_ATTESTATION_NOT_IMPLEMENTED"
    assert result["execution_started"] is False


def test_pilot_preflight_recomputes_inline_fixture_from_exact_test_source(tmp_path: Path) -> None:
    from scripts.wp12_runner.inline_fixtures import PILOT_NODEID, fixture_sha256, projection_pilot_fixture
    from scripts.wp12_runner.scientific_execution import _pilot_inline_fixture_errors

    source_relative = "tests/unit/test_modal_symmetric_projection.py"
    source_bytes = (ROOT / source_relative).read_bytes()
    source_path = tmp_path / source_relative
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(source_bytes)
    source_digest = hashlib.sha256(source_bytes).hexdigest()
    fixture = projection_pilot_fixture(source_bytes)
    canonical_digest = fixture_sha256(fixture)
    fixture_id = fixture["fixture_id"]
    manifest: dict[str, Any] = {
        "code_identity": {
            "test_files_sha256": {source_relative: source_digest},
            "fixture_files_sha256": {source_relative: source_digest},
        },
        "fixtures": {
            "inline": [
                {
                    "id": fixture_id,
                    "nodeid": PILOT_NODEID,
                    "source_file": source_relative,
                    "source_file_sha256": source_digest,
                    "canonicalization": "qf-wp12-inline-fixture-v1",
                    "sha256": canonical_digest,
                }
            ]
        },
    }
    context = {
        "inline_fixture": {
            "schema": "qf-wp12-inline-fixture-v1",
            "fixture_id": fixture_id,
            "canonicalization": "qf-wp12-inline-fixture-v1",
            "sha256": canonical_digest,
        }
    }

    assert _pilot_inline_fixture_errors(tmp_path, manifest, context, PILOT_NODEID) == ()
    manifest["fixtures"]["inline"][0]["sha256"] = "0" * 64
    assert _pilot_inline_fixture_errors(tmp_path, manifest, context, PILOT_NODEID) == (
        "PILOT_INLINE_FIXTURE_CANONICAL_HASH_MISMATCH",
    )
