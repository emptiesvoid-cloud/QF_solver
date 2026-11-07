"""Fail-closed verification of QF Solver 0.2.12 extended CI evidence.

This module validates a release attestation against GitHub API records and the
bytes of the artifact downloaded for that run attempt. It does *not* authenticate
caller-supplied JSON. Callers must obtain ``github_run``, ``github_jobs`` and
``artifact_api_record`` from GitHub over the authenticated API (for example via
``gh api``), and ``artifact_bytes`` from that exact run's artifact download.
An offline attestation file alone is never sufficient evidence.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from typing import Any


EXPECTED_REPOSITORY = "emptiesvoid-cloud/QF_solver"
EXPECTED_REPOSITORY_ID = 1329797607
EXPECTED_WORKFLOW_PATH = ".github/workflows/release-engineering-0212.yml"
EXPECTED_EVENT = "workflow_dispatch"
EXPECTED_REF = "refs/heads/emptiesvoids-cloud/qf0212-pypi-qualification"
EXPECTED_TAG = "v0.2.12"
ARTIFACT_NAME_PREFIX = "release-engineering-0212-attestation"
REQUIRED_JOB_IDS = frozenset({"wp14-targeted", "engineering", "documentation"})
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha(value: Any, label: str, length: int = 40) -> str:
    pattern = _SHA40 if length == 40 else _SHA64
    _require(isinstance(value, str) and pattern.fullmatch(value) is not None,
             f"Malformed {label}.")
    return value


def _positive_int(value: Any, label: str) -> int:
    _require(type(value) is int and value > 0, f"Malformed {label}.")
    return value


def _exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    _require(isinstance(value, dict) and set(value) == keys,
             f"Malformed {label}: required fields differ.")
    return value


def _api_repository(value: Any) -> str:
    _require(isinstance(value, dict), "GitHub API run repository is missing.")
    full_name = value.get("full_name")
    _require(full_name == EXPECTED_REPOSITORY,
             "GitHub API run belongs to a different repository.")
    _require(value.get("id") == EXPECTED_REPOSITORY_ID,
             "GitHub API repository id mismatch.")
    return full_name


def _read_attestation_artifact(payload: bytes) -> dict[str, Any]:
    _require(isinstance(payload, bytes) and bool(payload),
             "Downloaded attestation artifact bytes are missing.")
    _require(len(payload) <= 65_536,
             "Downloaded attestation artifact exceeds the 64 KiB limit.")
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = archive.infolist()
            _require(len(members) == 1
                     and members[0].filename == "release_engineering_attestation.json"
                     and not members[0].is_dir()
                     and members[0].file_size <= 65_536
                     and members[0].compress_size <= 65_536,
                     "Artifact ZIP must contain exactly one bounded attestation JSON.")
            mode = (members[0].external_attr >> 16) & 0o170000
            _require(mode != 0o120000, "Attestation artifact member must not be a symlink.")
            raw = archive.read(members[0])
            value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Downloaded artifact is not a valid attestation ZIP.") from exc
    _require(isinstance(value, dict), "Attestation JSON root must be an object.")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in result, "Attestation JSON contains a duplicate key.")
        result[key] = value
    return result


def validate_release_engineering_attestation(
    *,
    expected_workflow_sha: str,
    expected_run_id: int,
    expected_run_attempt: int,
    expected_source_sha: str,
    expected_source_tree_sha: str,
    expected_tag_object_sha: str,
    expected_scope_manifest_sha256: str,
    github_run: dict[str, Any],
    github_jobs: list[dict[str, Any]],
    artifact_api_record: dict[str, Any],
    artifact_bytes: bytes,
) -> dict[str, Any]:
    """Validate one extended-CI result, preserving workflow/source identities.

    ``expected_*`` values must come from the prospectively approved release
    contract and a verified annotated tag. ``github_*`` records and the
    artifact bytes must be fetched live from GitHub. In particular, the Actions
    run's ``head_sha`` identifies the workflow commit; the tag's source commit
    is a separate identity and is checked independently in every required job
    attestation.

    The function is intentionally strict: all three extended jobs must be
    present once and successful. Skipped or absent jobs never satisfy it.
    """
    _positive_int(expected_run_id, "expected run id")
    _positive_int(expected_run_attempt, "expected run attempt")
    expected_workflow_sha = _sha(expected_workflow_sha, "expected workflow SHA")
    expected_source_sha = _sha(expected_source_sha, "expected tagged source SHA")
    expected_source_tree_sha = _sha(expected_source_tree_sha, "expected source tree SHA")
    expected_tag_object_sha = _sha(expected_tag_object_sha, "expected annotated tag object SHA")
    expected_scope_manifest_sha256 = _sha(
        expected_scope_manifest_sha256, "expected execution-scope manifest SHA-256", 64
    )
    _require(expected_source_sha != expected_workflow_sha,
             "Workflow and tagged source identities must remain distinct.")
    # Parse the payload from the authenticated GitHub artifact itself. Do not
    # accept a second caller-provided JSON value which could diverge from bytes.
    attestation = _read_attestation_artifact(artifact_bytes)

    _exact_keys(attestation, {
        "schema_version", "repository", "workflow_path", "workflow_sha", "run_id",
        "run_attempt", "event", "ref", "run_status", "conclusion", "scope_manifest_sha256",
        "source", "jobs", "artifacts", "limitations",
    }, "attestation")
    _require(attestation["schema_version"] == 1, "Unsupported attestation schema.")
    _require(attestation["repository"] == EXPECTED_REPOSITORY,
             "Attestation repository mismatch.")
    _require(attestation["workflow_path"] == EXPECTED_WORKFLOW_PATH,
             "Attestation workflow path mismatch.")
    _require(attestation["workflow_sha"] == expected_workflow_sha,
             "Attestation workflow SHA mismatch.")
    _require(attestation["run_id"] == expected_run_id
             and type(attestation["run_id"]) is int, "Attestation run id mismatch.")
    _require(attestation["run_attempt"] == expected_run_attempt
             and type(attestation["run_attempt"]) is int, "Attestation run attempt mismatch.")
    _require(attestation["event"] == EXPECTED_EVENT, "Attestation event mismatch.")
    _require(attestation["ref"] == EXPECTED_REF, "Attestation ref mismatch.")
    _require(attestation["scope_manifest_sha256"] == expected_scope_manifest_sha256,
             "Execution-scope manifest SHA-256 mismatch.")
    # The artifact is uploaded while the attestation job is still running, so
    # a self-reported final run result is circular and untrustworthy. The
    # schema requires explicit nulls here; final status comes only from API.
    _require(attestation["run_status"] is None and attestation["conclusion"] is None,
             "Final run status must be bound from GitHub API, not self-reported.")
    _require(isinstance(attestation["limitations"], list)
             and all(isinstance(item, str) and item for item in attestation["limitations"]),
             "Attestation limitations must be explicit text entries.")

    source = _exact_keys(attestation["source"], {
        "tag", "tag_object_sha", "source_sha", "source_tree_sha",
    }, "source identity")
    _require(source["tag"] == EXPECTED_TAG, "Attestation tag mismatch.")
    _require(source["tag_object_sha"] == expected_tag_object_sha,
             "Attestation annotated tag object mismatch.")
    _require(source["source_sha"] == expected_source_sha,
             "Attestation tagged source commit mismatch.")
    _require(source["source_tree_sha"] == expected_source_tree_sha,
             "Attestation source tree mismatch.")

    # The API run record authenticates the workflow execution only when fetched
    # live by the caller. It must agree with the approved repository/workflow
    # and run identity; head_sha is deliberately the workflow commit.
    _require(isinstance(github_run, dict), "GitHub API run record is missing.")
    _api_repository(github_run.get("head_repository"))
    _require(github_run.get("path") == EXPECTED_WORKFLOW_PATH,
             "GitHub API run workflow path mismatch.")
    _require(github_run.get("id") == expected_run_id
             and type(github_run.get("id")) is int, "GitHub API run id mismatch.")
    _require(github_run.get("run_attempt") == expected_run_attempt
             and type(github_run.get("run_attempt")) is int,
             "GitHub API run attempt mismatch.")
    _require(github_run.get("event") == EXPECTED_EVENT,
             "GitHub API run event mismatch.")
    _require(github_run.get("head_branch") == "emptiesvoids-cloud/qf0212-pypi-qualification"
             and github_run.get("head_sha") == expected_workflow_sha,
             "GitHub API run is not on the approved workflow commit on main.")
    _require(github_run.get("status") == "completed"
             and github_run.get("conclusion") == "success",
             "GitHub API run did not succeed.")
    _api_repository(github_run.get("repository"))

    job_attestations = attestation["jobs"]
    _require(isinstance(job_attestations, dict) and set(job_attestations) == REQUIRED_JOB_IDS,
             "Attestation must contain exactly the three required extended jobs.")
    _require(isinstance(github_jobs, list), "GitHub API job list is malformed.")
    api_by_name: dict[str, dict[str, Any]] = {}
    for job in github_jobs:
        _require(isinstance(job, dict), "GitHub API job record is malformed.")
        name = job.get("name")
        _require(isinstance(name, str) and name not in api_by_name,
                 "GitHub API job names must be present and unique.")
        _require(job.get("run_id") == expected_run_id,
                 "GitHub API job belongs to another run.")
        api_by_name[name] = job

    for job_id in sorted(REQUIRED_JOB_IDS):
        record = _exact_keys(job_attestations[job_id], {
            "job_id", "github_job_id", "name", "status", "conclusion",
            "tested_source_sha", "workflow_sha", "run_id", "run_attempt",
        }, f"{job_id} job attestation")
        _require(record["job_id"] == job_id and record["name"] == job_id,
                 f"{job_id} attestation job id/name mismatch.")
        _positive_int(record["github_job_id"], f"{job_id} GitHub job id")
        _require(record["status"] == "completed" and record["conclusion"] == "success",
                 f"{job_id} did not succeed.")
        _require(record["tested_source_sha"] == expected_source_sha,
                 f"{job_id} tested a different source commit.")
        _require(record["workflow_sha"] == expected_workflow_sha,
                 f"{job_id} used a different workflow commit.")
        _require(record["run_id"] == expected_run_id and type(record["run_id"]) is int,
                 f"{job_id} run id mismatch.")
        _require(record["run_attempt"] == expected_run_attempt
                 and type(record["run_attempt"]) is int,
                 f"{job_id} run attempt mismatch.")
        name = record["name"]
        _require(isinstance(name, str) and name in api_by_name,
                 f"{job_id} has no corresponding live GitHub job.")
        api_job = api_by_name[name]
        _require(api_job.get("id") == record["github_job_id"]
                 and api_job.get("status") == "completed"
                 and api_job.get("conclusion") == "success",
                 f"Live GitHub job {name} did not succeed.")
        _require(api_job.get("run_id") == expected_run_id,
                 f"Live GitHub job {name} belongs to another run.")

    artifacts = attestation["artifacts"]
    _require(isinstance(artifacts, list) and len(artifacts) == 1,
             "Attestation must bind exactly one metadata artifact.")
    claimed_artifact = _exact_keys(artifacts[0], {
        "name", "content_manifest", "contains_raw_science_or_docs_data", "retention_days",
    },
                                   "attestation artifact claim")
    expected_artifact_name = (
        f"{ARTIFACT_NAME_PREFIX}-{expected_run_id}-attempt-{expected_run_attempt}"
    )
    _require(claimed_artifact["name"] == expected_artifact_name,
             "Attestation artifact name mismatch.")
    content_manifest = claimed_artifact["content_manifest"]
    _require(isinstance(content_manifest, list) and len(content_manifest) == 1,
             "Artifact content manifest must contain only the attestation JSON.")
    entry = _exact_keys(content_manifest[0], {"path"},
                        "artifact content manifest entry")
    _require(entry["path"] == "release_engineering_attestation.json",
             "Unexpected file in the attestation artifact.")
    _require(claimed_artifact["contains_raw_science_or_docs_data"] is False
             and claimed_artifact["retention_days"] == 7
             and type(claimed_artifact["retention_days"]) is int,
             "Attestation artifact must be metadata-only with seven-day retention.")

    _require(isinstance(artifact_api_record, dict),
             "Live GitHub artifact API record is missing.")
    _require(artifact_api_record.get("name") == expected_artifact_name,
             "Live GitHub artifact name mismatch.")
    artifact_id = _positive_int(artifact_api_record.get("id"), "artifact id")
    _require(artifact_api_record.get("expired") is False,
             "GitHub artifact is expired.")
    workflow_run = artifact_api_record.get("workflow_run")
    _require(isinstance(workflow_run, dict)
             and workflow_run.get("id") == expected_run_id
             and workflow_run.get("head_sha") == expected_workflow_sha
             and workflow_run.get("head_branch") == "emptiesvoids-cloud/qf0212-pypi-qualification",
             "GitHub artifact is not attached to the expected workflow run.")
    _require(workflow_run.get("repository_id") == EXPECTED_REPOSITORY_ID
             and workflow_run.get("head_repository_id") == EXPECTED_REPOSITORY_ID,
             "GitHub artifact repository identity mismatch.")
    actual_artifact_sha = hashlib.sha256(artifact_bytes).hexdigest()
    api_digest = artifact_api_record.get("digest")
    _require(isinstance(api_digest, str) and api_digest == f"sha256:{actual_artifact_sha}",
             "Downloaded artifact bytes do not match the GitHub API digest.")
    api_size = artifact_api_record.get("size_in_bytes")
    _require(type(api_size) is int and api_size == len(artifact_bytes),
             "Downloaded artifact size does not match the GitHub API record.")
    return {
        "status": "PASS_GITHUB_EVIDENCE_CONSISTENT",
        "repository": EXPECTED_REPOSITORY,
        "workflow_path": EXPECTED_WORKFLOW_PATH,
        "workflow_sha": expected_workflow_sha,
        "source_sha": expected_source_sha,
        "source_tree_sha": expected_source_tree_sha,
        "tag": EXPECTED_TAG,
        "tag_object_sha": expected_tag_object_sha,
        "scope_manifest_sha256": expected_scope_manifest_sha256,
        "run_id": expected_run_id,
        "run_attempt": expected_run_attempt,
        "event": EXPECTED_EVENT,
        "required_jobs": sorted(REQUIRED_JOB_IDS),
        "artifact_id": artifact_id,
        "artifact_name": expected_artifact_name,
        "artifact_sha256": actual_artifact_sha,
        "artifact_size_bytes": len(artifact_bytes),
        "authentication_note": "This result is only as authentic as caller-fetched GitHub API records and artifact bytes; offline JSON alone is not authenticated.",
    }
