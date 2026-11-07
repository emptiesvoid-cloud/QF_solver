"""Synthetic fail-closed tests for 0.2.12 extended-CI release evidence."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import zipfile

import pytest

from scripts.verify_release_engineering_0212 import (
    REQUIRED_JOB_IDS,
    validate_release_engineering_attestation,
)


def _fixture() -> tuple[dict, dict, list[dict], dict, bytes, dict[str, str]]:
    workflow_sha = "a" * 40
    source_sha = "b" * 40
    source_tree_sha = "c" * 40
    tag_object_sha = "d" * 40
    scope_sha = "e" * 64
    run_id = 42123456789
    attempt = 1
    artifact_name = f"release-engineering-0212-attestation-{run_id}-attempt-{attempt}"
    jobs = {
        job_id: {
            "job_id": job_id,
            "github_job_id": 1000 + index,
            "name": job_id,
            "status": "completed",
            "conclusion": "success",
            "tested_source_sha": source_sha,
            "workflow_sha": workflow_sha,
            "run_id": run_id,
            "run_attempt": attempt,
        }
        for index, job_id in enumerate(sorted(REQUIRED_JOB_IDS))
    }
    attestation = {
        "schema_version": 1,
        "repository": "emptiesvoid-cloud/QF_solver",
        "workflow_path": ".github/workflows/release-engineering-0212.yml",
        "workflow_sha": workflow_sha,
        "run_id": run_id,
        "run_attempt": attempt,
        "event": "workflow_dispatch",
        "ref": "refs/heads/emptiesvoids-cloud/qf0212-pypi-qualification",
        "run_status": None,
        "conclusion": None,
        "scope_manifest_sha256": scope_sha,
        "limitations": ["synthetic fixture only"],
        "source": {
            "tag": "v0.2.12",
            "tag_object_sha": tag_object_sha,
            "source_sha": source_sha,
            "source_tree_sha": source_tree_sha,
        },
        "jobs": jobs,
        "artifacts": [{
            "name": artifact_name,
            "content_manifest": [{"path": "release_engineering_attestation.json"}],
            "contains_raw_science_or_docs_data": False,
            "retention_days": 7,
        }],
    }
    payload = json.dumps(attestation, sort_keys=True, separators=(",", ":")).encode()
    artifact_stream = io.BytesIO()
    with zipfile.ZipFile(artifact_stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("release_engineering_attestation.json", payload)
    artifact_bytes = artifact_stream.getvalue()
    github_run = {
        "id": run_id,
        "run_attempt": attempt,
        "event": "workflow_dispatch",
        "head_branch": "emptiesvoids-cloud/qf0212-pypi-qualification",
        "head_sha": workflow_sha,
        "path": ".github/workflows/release-engineering-0212.yml",
        "status": "completed",
        "conclusion": "success",
        "head_repository": {"full_name": "emptiesvoid-cloud/QF_solver", "id": 1329797607},
        "repository": {"full_name": "emptiesvoid-cloud/QF_solver", "id": 1329797607},
    }
    github_jobs = [
        {
            "id": 1000 + index,
            "run_id": run_id,
            "name": job_id,
            "status": "completed",
            "conclusion": "success",
        }
        for index, job_id in enumerate(sorted(REQUIRED_JOB_IDS))
    ]
    artifact_api_record = {
        "id": 99887766,
        "name": artifact_name,
        "expired": False,
        "size_in_bytes": len(artifact_bytes),
        "digest": f"sha256:{hashlib.sha256(artifact_bytes).hexdigest()}",
        "workflow_run": {
            "id": run_id,
            "head_sha": workflow_sha,
            "head_branch": "emptiesvoids-cloud/qf0212-pypi-qualification",
            "repository_id": 1329797607,
            "head_repository_id": 1329797607,
        },
    }
    expected = {
        "expected_workflow_sha": workflow_sha,
        "expected_run_id": run_id,
        "expected_run_attempt": attempt,
        "expected_source_sha": source_sha,
        "expected_source_tree_sha": source_tree_sha,
        "expected_tag_object_sha": tag_object_sha,
        "expected_scope_manifest_sha256": scope_sha,
    }
    return attestation, github_run, github_jobs, artifact_api_record, artifact_bytes, expected


def _artifact(attestation: dict) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "release_engineering_attestation.json",
            json.dumps(attestation, sort_keys=True, separators=(",", ":")).encode(),
        )
    return stream.getvalue()


def _validate(fixture: tuple, **overrides):
    attestation, github_run, github_jobs, artifact_record, artifact_bytes, expected = fixture
    attestation = overrides.get("attestation", attestation)
    if "attestation" in overrides:
        artifact_bytes = _artifact(attestation)
        artifact_record = copy.deepcopy(artifact_record)
        artifact_record["size_in_bytes"] = len(artifact_bytes)
        artifact_record["digest"] = f"sha256:{hashlib.sha256(artifact_bytes).hexdigest()}"
    return validate_release_engineering_attestation(
        github_run=overrides.get("github_run", github_run),
        github_jobs=overrides.get("github_jobs", github_jobs),
        artifact_api_record=overrides.get("artifact_api_record", artifact_record),
        artifact_bytes=overrides.get("artifact_bytes", artifact_bytes),
        **expected,
    )


def test_dual_identity_attestation_matches_api_records_and_exact_artifact() -> None:
    result = _validate(_fixture())
    assert result["status"] == "PASS_GITHUB_EVIDENCE_CONSISTENT"
    assert result["workflow_sha"] == "a" * 40
    assert result["source_sha"] == "b" * 40
    assert result["workflow_sha"] != result["source_sha"]
    assert set(result["required_jobs"]) == REQUIRED_JOB_IDS


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda a: a.update(repository="attacker/other"), "repository mismatch"),
        (lambda a: a.update(workflow_path=".github/workflows/quality.yml"), "workflow path mismatch"),
        (lambda a: a.update(workflow_sha="e" * 40), "workflow SHA mismatch"),
        (lambda a: a.update(run_attempt=2), "run attempt mismatch"),
        (lambda a: a["source"].update(source_tree_sha="f" * 40), "source tree mismatch"),
        (lambda a: a["jobs"]["engineering"].update(tested_source_sha="e" * 40), "different source"),
        (lambda a: a["jobs"]["documentation"].update(conclusion="skipped"), "did not succeed"),
    ],
)
def test_malformed_or_mismatched_attestation_fails_closed(change, message: str) -> None:
    fixture = _fixture()
    attestation = copy.deepcopy(fixture[0])
    change(attestation)
    with pytest.raises(ValueError, match=message):
        _validate(fixture, attestation=attestation)


def test_live_api_failure_or_missing_job_never_becomes_pass() -> None:
    fixture = _fixture()
    run = copy.deepcopy(fixture[1])
    run["conclusion"] = "failure"
    with pytest.raises(ValueError, match="did not succeed"):
        _validate(fixture, github_run=run)

    jobs = copy.deepcopy(fixture[2])
    jobs.pop()
    with pytest.raises(ValueError, match="no corresponding live GitHub job"):
        _validate(fixture, github_jobs=jobs)


def test_artifact_digest_run_and_payload_are_bound() -> None:
    fixture = _fixture()
    record = copy.deepcopy(fixture[3])
    record["digest"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="do not match the GitHub API digest"):
        _validate(fixture, artifact_api_record=record)

    record = copy.deepcopy(fixture[3])
    record["workflow_run"]["id"] += 1
    with pytest.raises(ValueError, match="not attached to the expected workflow run"):
        _validate(fixture, artifact_api_record=record)


def test_artifact_with_extra_file_is_rejected() -> None:
    fixture = _fixture()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("release_engineering_attestation.json", b"{}")
        archive.writestr("extra.txt", b"not permitted")
    payload = stream.getvalue()
    record = copy.deepcopy(fixture[3])
    record["size_in_bytes"] = len(payload)
    record["digest"] = f"sha256:{hashlib.sha256(payload).hexdigest()}"
    with pytest.raises(ValueError, match="exactly one bounded attestation JSON"):
        _validate(fixture, artifact_api_record=record, artifact_bytes=payload)


def test_offline_attestation_without_live_api_records_is_not_accepted() -> None:
    fixture = _fixture()
    record = copy.deepcopy(fixture[1])
    record["head_repository"] = {"full_name": "evil/repo", "id": -1}
    with pytest.raises(ValueError, match="different repository"):
        validate_release_engineering_attestation(
            **fixture[5],
            github_run=record,
            github_jobs=[],
            artifact_api_record=fixture[3],
            artifact_bytes=fixture[4],
        )
