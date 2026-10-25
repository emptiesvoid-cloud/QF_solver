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
    verify_receipt,
    write_receipt,
)
from scripts.wp12_runner.environment import collect_environment_provenance
from scripts.wp12_runner.git_remote import sync_remote_identity, write_sync_receipt
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
    validate_approved_pilot_command,
)
from scripts.wp12_runner.cli import main as runner_main
import scripts.wp12_runner.cli as runner_cli
import scripts.wp12_runner.synthetic_orchestrator as synthetic_orchestrator
from scripts.wp12_owner_canonicalization import CanonicalizationError, PROFILE, canonical_owner_payload


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
        "schema": "qf-solver-wp12-owner-decision-v3",
        "canonicalization": PROFILE,
        "decision_id": "OWNER-SYNTHETIC-01",
        "unit_id": "SYNTH-UNIT-01",
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
        "schema": "qf-solver-wp12-owner-decision-v3",
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
        '"schema":"qf-solver-wp12-owner-decision-v3"}'
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
        "schema": "qf-solver-wp12-owner-decision-v3",
        "canonicalization": PROFILE,
        "decision_id": "SYNTHETIC-OWNER-DECISION-01",
        "unit_id": manifest["unit_id"],
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
        f"--junitxml={relative_junit}",
        PILOT_NODEID,
    ]
    validate_approved_pilot_command(exact, cwd=science_root, run_directory=evidence_dir, python_executable=sys.executable)
    with pytest.raises(ContractError, match="exact WP12-1 pilot"):
        validate_approved_pilot_command(
            [*exact[:-1], "-k", "modal"],
            cwd=science_root,
            run_directory=evidence_dir,
            python_executable=sys.executable,
        )


def test_pilot_inline_fixture_identity_is_extracted_without_importing_solver() -> None:
    from scripts.wp12_runner.inline_fixtures import fixture_sha256, projection_pilot_fixture

    source_path = ROOT / "tests" / "unit" / "test_modal_symmetric_projection.py"
    fixture = projection_pilot_fixture(source_path.read_bytes())
    assert fixture["nodeid"].endswith("test_structured_symmetric_projection_matches_dense_bilinear_form")
    assert len(fixture_sha256(fixture)) == 64
    assert not any(name == "solveur" or name.startswith("solveur.") for name in sys.modules)


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
    assert event["blockers"] == ["REAL_EXECUTION_DISABLED_IN_WP12_A"]


def test_execute_is_unconditionally_disabled_even_with_manifest_and_owner_inputs(
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
    assert output["blockers"] == ["REAL_EXECUTION_DISABLED_IN_WP12_A"]
    assert len(refusal_records) == 1


def test_scientific_execution_stub_ignores_all_authorization_inputs(tmp_path: Path) -> None:
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
    assert event["blockers"] == ["REAL_EXECUTION_DISABLED_IN_WP12_A"]


def test_trust_status_reports_only_public_metadata(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
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
    assert refusal["blockers"] == ["REAL_EXECUTION_DISABLED_IN_WP12_A"]


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
    assert report["journal_record_count"] == 14
    assert report["temporary_evidence_discarded_after_report"] is True
    assert len(report["plan_sha256"]) == 64
    assert {item["case"] for item in report["results"]} == {
        "success",
        "exit",
        "sleep",
        "tree",
        "flood",
        "memory",
    }
    assert all(item["self_test"] in {"PASS", "NOT_APPLICABLE"} for item in report["results"])
    assert len({item["run_id"] for item in report["results"]}) == len(report["results"])
    assert all(item["attempt"] == item["maximum_attempts"] == 1 for item in report["results"])
    assert all(item["scientific_result"] is False for item in report["results"])
    assert all("nodeid" not in item for item in report["results"])
    assert all(
        item["self_test"] == "NOT_APPLICABLE" or len(item["receipt_sha256"]) == 64 for item in report["results"]
    )


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
