"""Audit exact prebuilt release files against a prospective authorization contract."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, cast

if __package__:
    from scripts.git_tools import git_run
    from scripts.verify_public_package import (
        digest,
        frozen_inputs,
        installed_probe_command,
        run_command,
        verify_archives,
        write_record,
    )
else:
    from git_tools import git_run
    from verify_public_package import (
        digest,
        frozen_inputs,
        installed_probe_command,
        run_command,
        verify_archives,
        write_record,
    )

_scope_policy = cast(
    Callable[[str, str, bool], str],
    getattr(
        importlib.import_module(
            "scripts.public_release_scope" if __package__ else "public_release_scope"
        ),
        "publication_scope_decision",
    ),
)


SUPPORTED_RELEASE_CONTRACT_SCHEMA_VERSIONS = {1, 2, 3}
BOUNDED_PROFILE = "PYPI_0212_BOUNDED"
BOUNDED_SOURCE_SHA = "f6f63eb8701e38b41aae0d735850e8cf50b07fa5"
BOUNDED_TAG_OBJECT_SHA = "dbf8314b861ac7f3a963d6036080e7a96ca4b17e"
BOUNDED_DOC_SCOPE_SHA256 = "2545399b23658145f0b6f91309d8d358db41d7ebd6face8dfba703a9e3a93eef"
BOUNDED_STAGING_RUN_ID = 42465518619
BOUNDED_STAGING_ARTIFACT_ID = 13611258554
BOUNDED_QUALITY_RUN_ID = 42394326907
BOUNDED_ARTIFACTS = {
    "wheel": {"filename": "qf_solver-0.2.12-py3-none-any.whl", "bytes": 1709716,
              "sha256": "a09368d4d1d79f5b7fc10ff5c4c3a96dfa5d245a20bd9984704b8ab472d4c719"},
    "sdist": {"filename": "qf_solver-0.2.12.tar.gz", "bytes": 1344948,
              "sha256": "1b6a980c4ecb3dce1ed5a885a69c9cc66d1efd62af85fba20bb0ed13daac1cd1"},
}
BOUNDED_CHECKSUM_MANIFEST = {
    "filename": "qf_solver-0.2.12-f6f63eb-SHA256SUMS.txt", "bytes": 190,
    "sha256": "bc20da5094e4d250dc33be7aa379e07a654e20b8ba787ad596cac9801c62c634",
}
STANDARD_QUALITY_JOBS = {
    "ubuntu_python_3_10", "ubuntu_python_3_13",
    "windows_python_3_10", "windows_python_3_13",
}
BOUNDED_SMOKE_CASES = {
    "static_tet4_single_free_dof": "PASS",
    "modal_tet4_three_modes": "PASS",
    "rotating_modal_beam2_disk_one_speed": "PASS_EXPERIMENTAL",
    "campbell_beam2_disk_three_speeds": "PASS_EXPERIMENTAL",
}


def _validate_bounded_candidate_audit(audit: dict[str, Any], contract: dict[str, Any], source_sha: str) -> None:
    """Validate evidence accepted by the narrowly scoped 0.2.12 PyPI profile."""
    ci = audit.get("ci")
    if not isinstance(ci, dict) or not isinstance(ci.get("quality_jobs"), dict):
        raise ValueError("The bounded candidate audit has no standard Quality matrix.")
    if (
        ci.get("quality_head_sha") != source_sha
        or ci.get("quality_run_id") != BOUNDED_QUALITY_RUN_ID
        or ci.get("quality_conclusion") != "SUCCESS"
        or ci.get("ci_sha_exact_match") is not True
        or ci["quality_jobs"] != {name: "PASS" for name in STANDARD_QUALITY_JOBS}
    ):
        raise ValueError("Bounded profile requires exactly the four passing standard Quality cells on the source SHA.")

    evidence = audit.get("bounded_profile_evidence")
    approved = contract.get("bounded_profile_evidence")
    if not isinstance(evidence, dict) or not isinstance(approved, dict) or evidence != approved:
        raise ValueError("Bounded profile evidence must exactly match its frozen contract bindings.")
    documentation = evidence.get("documentation")
    if not isinstance(documentation, dict) or (
        documentation.get("status") != "PASS_STRICT_TAG_RENDER"
        or documentation.get("source_sha") != source_sha
        or documentation.get("rendered_html_pages") != 526
        or documentation.get("scope_audit_status") != "PASS_BOUNDED_PUBLIC_SURFACES"
        or documentation.get("scope_audit_sha256") != BOUNDED_DOC_SCOPE_SHA256
        or not isinstance(documentation.get("scope_audit_sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", documentation["scope_audit_sha256"])
    ):
        raise ValueError("Bounded profile documentation render or selected-scope audit is incomplete.")
    smokes = evidence.get("installed_smokes")
    if not isinstance(smokes, dict) or (
        smokes.get("status") != "PASS"
        or smokes.get("manifest_sha256") != contract.get("smoke_manifest_sha256")
        or not isinstance(smokes.get("manifest_sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", smokes["manifest_sha256"])
        or smokes.get("cases") != BOUNDED_SMOKE_CASES
    ):
        raise ValueError("Bounded profile requires all four installed smokes from the exact approved manifest.")
    receipts = smokes.get("receipts")
    if not isinstance(receipts, dict) or set(receipts) != set(BOUNDED_SMOKE_CASES):
        raise ValueError("Bounded profile must bind one exact execution receipt for each approved installed smoke.")
    for case_id, expected_status in BOUNDED_SMOKE_CASES.items():
        receipt = receipts[case_id]
        if not isinstance(receipt, dict) or (
            receipt.get("status") != expected_status
            or receipt.get("attempts") != 1
            or receipt.get("case_id") != case_id
            or any(not isinstance(receipt.get(key), str)
                   or not re.fullmatch(r"[0-9a-f]{64}", receipt[key])
                   for key in ("evidence_sha256", "raw_result_sha256", "authorization_sha256"))
            or not isinstance(receipt.get("evidence_path"), str)
            or not isinstance(receipt.get("evidence_commit_sha"), str)
        ):
            raise ValueError(f"The installed smoke receipt is incomplete or invalid: {case_id}")
    if evidence.get("extended_validation") != "NOT_RUN" or evidence.get("wp14") != "NOT_RUN":
        raise ValueError("Bounded profile must preserve extended validation and WP14 as NOT_RUN.")


def _validate_bounded_quality_run(source_sha: str) -> None:
    """Recheck the four standard Quality jobs against the exact Actions run."""
    run_id = BOUNDED_QUALITY_RUN_ID
    run = json.loads(_github_release_evidence(f"actions/runs/{run_id}"))
    if (
        run.get("id") != run_id
        or run.get("run_attempt") != 1
        or run.get("path") != ".github/workflows/quality.yml"
        or run.get("head_sha") != source_sha
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
        or (run.get("repository") or {}).get("id") != 1329797607
    ):
        raise ValueError("The bounded profile Quality run is not the exact successful source run.")
    response = json.loads(_github_release_evidence(f"actions/runs/{run_id}/jobs?per_page=100"))
    jobs = response.get("jobs") if isinstance(response, dict) else None
    if not isinstance(jobs, list):
        raise ValueError("The bounded profile Quality run has no readable job matrix.")
    expected = {
        "ubuntu-latest / Python 3.10", "ubuntu-latest / Python 3.13",
        "windows-latest / Python 3.10", "windows-latest / Python 3.13",
    }
    passed = {
        job.get("name") for job in jobs
        if isinstance(job, dict) and job.get("status") == "completed" and job.get("conclusion") == "success"
    }
    if passed != expected:
        raise ValueError("The exact-source Quality run does not have exactly the four passing standard matrix cells.")


def _validate_bounded_smoke_receipts(
    root: Path, head: str, source_sha: str, contract: dict[str, Any],
) -> None:
    """Verify smoke receipt digests against the committed case result records."""
    evidence = contract.get("bounded_profile_evidence", {})
    smokes = evidence.get("installed_smokes", {}) if isinstance(evidence, dict) else {}
    receipts = smokes.get("receipts", {}) if isinstance(smokes, dict) else {}
    wheel_sha = contract.get("audited_artifacts", {}).get("wheel", {}).get("sha256")
    for case_id, expected_status in BOUNDED_SMOKE_CASES.items():
        receipt = receipts[case_id]
        path = _relative_path(receipt.get("evidence_path", ""))
        commit = receipt.get("evidence_commit_sha")
        if (
            not isinstance(commit, str)
            or not re.fullmatch(r"[0-9a-f]{40}", commit)
            or git_run(["merge-base", "--is-ancestor", source_sha, commit], cwd=root).returncode
            or git_run(["merge-base", "--is-ancestor", commit, head], cwd=root).returncode
        ):
            raise ValueError(f"Smoke evidence is not committed in the exact release lineage: {case_id}")
        payload = _committed_bytes(root, head, path)
        recorded_payload = git_run(["show", f"{commit}:{path}"], cwd=root, check=True).stdout
        if (
            hashlib.sha256(payload).hexdigest() != receipt.get("evidence_sha256")
            or hashlib.sha256(recorded_payload).hexdigest() != receipt.get("evidence_sha256")
        ):
            raise ValueError(f"Smoke evidence bytes differ from the committed receipt: {case_id}")
        record = json.loads(payload)
        if not isinstance(record, dict) or (
            record.get("case_id") != case_id
            or record.get("status") != expected_status
            or record.get("attempts") != 1
            or record.get("manifest_sha256") != contract.get("smoke_manifest_sha256")
            or record.get("plan_sha256") != contract.get("smoke_plan_sha256")
            or record.get("source_sha") != source_sha
            or record.get("wheel_sha256") != wheel_sha
            or record.get("raw_result_sha256") != receipt.get("raw_result_sha256")
            or record.get("authorization_sha256") != receipt.get("authorization_sha256")
        ):
            raise ValueError(f"Committed smoke result does not match the approved case identity: {case_id}")


def _validate_bounded_documentation_record(root: Path, head: str, contract: dict[str, Any]) -> None:
    evidence = contract.get("bounded_profile_evidence", {})
    documentation = evidence.get("documentation", {}) if isinstance(evidence, dict) else {}
    path = _relative_path(documentation.get("record_path", ""))
    commit = documentation.get("record_commit_sha")
    expected_sha = documentation.get("record_sha256")
    source_sha = contract.get("source_sha")
    if (
        not isinstance(commit, str)
        or not re.fullmatch(r"[0-9a-f]{40}", commit)
        or git_run(["merge-base", "--is-ancestor", source_sha, commit], cwd=root).returncode
        or git_run(["merge-base", "--is-ancestor", commit, head], cwd=root).returncode
    ):
        raise ValueError("The strict documentation proof is not committed in the exact release lineage.")
    payload = _committed_bytes(root, head, path)
    recorded = git_run(["show", f"{commit}:{path}"], cwd=root, check=True).stdout
    if hashlib.sha256(payload).hexdigest() != expected_sha or hashlib.sha256(recorded).hexdigest() != expected_sha:
        raise ValueError("The committed strict documentation proof differs from its frozen digest.")
    record = json.loads(payload)
    if not isinstance(record, dict) or any(
        record.get(key) != documentation.get(key)
        for key in ("status", "source_sha", "rendered_html_pages", "scope_audit_status", "scope_audit_sha256")
    ):
        raise ValueError("The committed documentation proof does not match the bounded profile evidence.")


def _release_channel_permissions(contract: dict[str, Any]) -> tuple[bool, bool]:
    if "release_channels" not in contract:
        return True, True
    if contract["release_channels"] == ["pypi"]:
        return False, False
    raise ValueError("The release contract names an unsupported or malformed release channel set.")


def _relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("Contract paths must use non-empty canonical POSIX paths.")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts) or value.startswith("/"):
        raise ValueError("Contract paths must not contain aliases or traversal.")
    return value


def _committed_bytes(root: Path, head: str, relative: str) -> bytes:
    path = root / _relative_path(relative)
    committed = git_run(["show", f"{head}:{relative}"], cwd=root, check=True).stdout
    current = path.read_bytes()
    if current != committed and current.replace(b"\r\n", b"\n") != committed:
        raise ValueError(f"Committed contract input differs from its worktree bytes: {relative}")
    return committed


def _check_tool_bindings(root: Path, commit: str, bindings: Any) -> None:
    if not isinstance(bindings, dict) or not bindings:
        raise ValueError("The release contract must bind its release verification tools.")
    for relative, expected in bindings.items():
        path = _relative_path(relative)
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError(f"Release tool binding is malformed: {relative}")
        observed = hashlib.sha256(git_run(["show", f"{commit}:{path}"], cwd=root, check=True).stdout).hexdigest()
        if observed != expected:
            raise ValueError(f"Release tool binding mismatch: {relative}")


def _github_release_evidence(endpoint: str) -> bytes:
    result = subprocess.run(
        ["gh", "api", "--hostname", "github.com", f"repos/emptiesvoid-cloud/QF_solver/{endpoint}"],
        check=False,
        capture_output=True,
        timeout=45,
    )
    if result.returncode != 0:
        raise ValueError("Could not read the exact release evidence from the GitHub API.")
    return result.stdout


def validate_pypi_staging_transport(root: Path, head: str, contract: dict[str, Any]) -> None:
    """Verify the v0.2.12 Actions transport before downloading the package ZIP."""
    if contract.get("package_version") != "0.2.12":
        return
    source = contract.get("pypi_artifact_source")
    if (
        contract.get("release_channels") != ["pypi"]
        or not isinstance(source, dict)
        or set(source) != {"run_id", "artifact_id"}
        or any(type(value) is not int or not 1 <= value < 2**53 for value in source.values())
    ):
        raise ValueError("Bind one exact Actions staging run and artifact for the v0.2.12 PyPI-only release.")
    if contract.get("validation_profile") == BOUNDED_PROFILE and source != {
        "run_id": BOUNDED_STAGING_RUN_ID,
        "artifact_id": BOUNDED_STAGING_ARTIFACT_ID,
    }:
        raise ValueError("The bounded profile must use the exact preverified PyPI staging run and artifact.")
    run_id, artifact_id = source["run_id"], source["artifact_id"]
    workflow_path = ".github/workflows/stage-pypi-0212.yml"
    repository_id = 1329797607
    run = json.loads(_github_release_evidence(f"actions/runs/{run_id}"))
    workflow_sha = run.get("head_sha")
    branch = run.get("head_branch")
    source_sha = contract.get("source_sha")
    if (
        run.get("id") != run_id
        or run.get("run_attempt") != 1
        or run.get("event") != "workflow_dispatch"
        or run.get("path") != workflow_path
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
        or branch != "main"
        or (run.get("repository") or {}).get("id") != repository_id
        or (run.get("head_repository") or {}).get("id") != repository_id
        or not isinstance(source_sha, str)
        or not re.fullmatch(r"[0-9a-f]{40}", source_sha)
        or not isinstance(workflow_sha, str)
        or not re.fullmatch(r"[0-9a-f]{40}", workflow_sha)
        or workflow_sha == source_sha
        or git_run(["merge-base", "--is-ancestor", source_sha, workflow_sha], cwd=root).returncode
        or git_run(["merge-base", "--is-ancestor", workflow_sha, head], cwd=root).returncode
    ):
        raise ValueError("The selected staging run is outside the exact successful release lineage.")
    for path in (workflow_path, "scripts/stage_pypi_0212.py"):
        staged = git_run(["show", f"{workflow_sha}:{path}"], cwd=root)
        current = _committed_bytes(root, head, path)
        if staged.returncode != 0 or staged.stdout != current:
            raise ValueError("The selected staging run used different staging tool bytes.")

    jobs = json.loads(_github_release_evidence(f"actions/runs/{run_id}/attempts/1/jobs?per_page=100"))
    stage_jobs = jobs.get("jobs")
    if not isinstance(stage_jobs, list) or jobs.get("total_count") != 1 or len(stage_jobs) != 1:
        raise ValueError("The selected staging run must contain exactly one bounded staging job.")
    stage_job = stage_jobs[0]
    if (
        stage_job.get("name") != "Stage exact selected PyPI inputs"
        or stage_job.get("run_id") != run_id
        or stage_job.get("status") != "completed"
        or stage_job.get("conclusion") != "success"
    ):
        raise ValueError("The exact selected staging job did not succeed.")

    artifact = json.loads(_github_release_evidence(f"actions/artifacts/{artifact_id}"))
    if (
        artifact.get("id") != artifact_id
        or artifact.get("name") != "qf0212-selected-pypi-inputs"
        or artifact.get("expired") is not False
        or type(artifact.get("size_in_bytes")) is not int
        or not 0 < artifact["size_in_bytes"] <= 4 * 1024 * 1024
        or not isinstance(artifact.get("digest"), str)
        or not re.fullmatch(r"sha256:[0-9a-f]{64}", artifact["digest"])
        or artifact.get("workflow_run") != {
            "id": run_id, "repository_id": repository_id, "head_repository_id": repository_id,
            "head_branch": branch, "head_sha": workflow_sha,
        }
    ):
        raise ValueError("The exact selected staging artifact is missing, expired or from another run.")


def _validate_tagged_engineering_ci(
    root: Path, head: str, source_sha: str, contract: dict[str, Any], ci: dict[str, Any],
) -> None:
    if __package__:
        from scripts.verify_release_engineering_0212 import validate_release_engineering_attestation
    else:
        from verify_release_engineering_0212 import validate_release_engineering_attestation

    evidence = contract.get("tagged_engineering_ci")
    keys = {
        "workflow_sha", "workflow_sha256", "scope_manifest_sha256",
        "run_id", "run_attempt", "artifact_id", "artifact_sha256",
    }
    if not isinstance(evidence, dict) or set(evidence) != keys or evidence != ci.get("tagged_engineering_ci"):
        raise ValueError("The candidate audit and release contract must bind the same tagged engineering run.")
    workflow_sha = evidence["workflow_sha"]
    if (
        not isinstance(workflow_sha, str)
        or not re.fullmatch(r"[0-9a-f]{40}", workflow_sha)
        or workflow_sha == source_sha
        or git_run(["merge-base", "--is-ancestor", source_sha, workflow_sha], cwd=root).returncode
        or git_run(["merge-base", "--is-ancestor", workflow_sha, head], cwd=root).returncode
    ):
        raise ValueError("The exact tagged engineering workflow commit must belong to the release lineage.")
    _check_tool_bindings(root, workflow_sha, {
        ".github/workflows/release-engineering-0212.yml": evidence["workflow_sha256"],
    })
    run_id, attempt, artifact_id = (evidence[key] for key in ("run_id", "run_attempt", "artifact_id"))
    if (
        any(type(value) is not int or not 1 <= value < 2**53 for value in (run_id, attempt, artifact_id))
        or attempt != 1
        or any(
            not isinstance(evidence[key], str) or not re.fullmatch(r"[0-9a-f]{64}", evidence[key])
            for key in ("artifact_sha256", "scope_manifest_sha256")
        )
    ):
        raise ValueError("The tagged engineering run, first attempt or artifact binding is invalid.")
    run = json.loads(_github_release_evidence(f"actions/runs/{run_id}"))
    jobs = json.loads(_github_release_evidence(f"actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100"))
    artifact = json.loads(_github_release_evidence(f"actions/artifacts/{artifact_id}"))
    if (
        not isinstance(artifact, dict)
        or artifact.get("id") != artifact_id
        or type(artifact.get("size_in_bytes")) is not int
        or not 0 < artifact["size_in_bytes"] <= 65536
    ):
        raise ValueError("The GitHub engineering artifact identity or size differs from its allowed binding.")
    if (
        not isinstance(jobs, dict)
        or not isinstance(jobs.get("jobs"), list)
        or jobs.get("total_count") != len(jobs["jobs"])
    ):
        raise ValueError("The GitHub engineering job list is incomplete.")
    archive = _github_release_evidence(f"actions/artifacts/{artifact_id}/zip")
    if hashlib.sha256(archive).hexdigest() != evidence["artifact_sha256"]:
        raise ValueError("The GitHub engineering artifact differs from the exact authorized bytes.")
    tree = git_run(["rev-parse", f"{source_sha}^{{tree}}"], cwd=root, check=True, text=True).stdout.strip()
    validate_release_engineering_attestation(
        expected_workflow_sha=workflow_sha,
        expected_run_id=run_id,
        expected_run_attempt=attempt,
        expected_source_sha=source_sha,
        expected_source_tree_sha=tree,
        expected_tag_object_sha=contract["tag_object_sha"],
        expected_scope_manifest_sha256=evidence["scope_manifest_sha256"],
        github_run=run,
        github_jobs=jobs["jobs"],
        artifact_api_record=artifact,
        artifact_bytes=archive,
    )


def _validate_candidate_audit(
    root: Path, head: str, source_sha: str, contract: dict[str, Any],
) -> None:
    reference = contract.get("candidate_audit")
    if not isinstance(reference, dict):
        raise ValueError("The selected-release contract must bind the exact final candidate audit record.")
    path = _relative_path(reference.get("path", ""))
    commit = reference.get("commit_sha")
    expected_hash = reference.get("sha256")
    if (
        not isinstance(commit, str)
        or not re.fullmatch(r"[0-9a-f]{40}", commit)
        or not isinstance(expected_hash, str)
        or not re.fullmatch(r"[0-9a-f]{64}", expected_hash)
        or git_run(["merge-base", "--is-ancestor", source_sha, commit], cwd=root).returncode
        or git_run(["merge-base", "--is-ancestor", commit, head], cwd=root).returncode
    ):
        raise ValueError("The final candidate audit is not an exact descendant audit of the authorized source.")
    committed = _committed_bytes(root, head, path)
    at_commit = git_run(["show", f"{commit}:{path}"], cwd=root, check=True).stdout
    if hashlib.sha256(committed).hexdigest() != expected_hash or hashlib.sha256(at_commit).hexdigest() != expected_hash:
        raise ValueError("The final candidate audit record bytes differ from their frozen hash.")
    audit = json.loads(committed)
    candidate = audit.get("candidate")
    if not isinstance(candidate, dict):
        raise ValueError("The candidate audit record is malformed.")
    github_allowed, zenodo_allowed = _release_channel_permissions(contract)
    pypi_only = not github_allowed and not zenodo_allowed
    bounded_profile = contract.get("validation_profile") == BOUNDED_PROFILE
    if pypi_only:
        tag_object = contract.get("tag_object_sha")
        tag_ref = f"refs/tags/{contract.get('release_tag')}"
        observed_tag = git_run(["rev-parse", "--verify", tag_ref], cwd=root, text=True)
        tag_type = git_run(["cat-file", "-t", tag_ref], cwd=root, text=True)
        tag_target = git_run(["rev-parse", f"{tag_ref}^{{commit}}"], cwd=root, text=True)
        if (
            not isinstance(tag_object, str)
            or not re.fullmatch(r"[0-9a-f]{40}", tag_object)
            or observed_tag.returncode != 0
            or observed_tag.stdout.strip() != tag_object
            or tag_type.returncode != 0
            or tag_type.stdout.strip() != "tag"
            or tag_target.returncode != 0
            or tag_target.stdout.strip() != source_sha
            or candidate.get("tag_object_sha") != tag_object
        ):
            raise ValueError("The PyPI-only release does not bind its exact annotated tag object and source target.")
    if (
        audit.get("record_id") != reference.get("record_id")
        or audit.get("status") != "READY_FOR_OWNER_RELEASE_AUTHORIZATION"
        or not isinstance(candidate, dict)
        or candidate.get("package_version") != contract.get("package_version")
        or candidate.get("package_source_sha") != source_sha
        or candidate.get("expected_tag") != contract.get("release_tag")
        or candidate.get("expected_tag_target_sha") != source_sha
        or candidate.get("tag_created") is not pypi_only
        or not isinstance(audit.get("release_gates"), dict)
        or audit.get("release_gates", {}).get("ready_for_owner_release_authorization") is not True
    ):
        raise ValueError("The candidate audit does not describe this exact frozen, untagged release candidate.")

    if bounded_profile:
        _validate_bounded_candidate_audit(audit, contract, source_sha)
        _validate_bounded_documentation_record(root, head, contract)
        _validate_bounded_smoke_receipts(root, head, source_sha, contract)
        _validate_bounded_quality_run(source_sha)
    else:
        expected_gate_keys = {f"QF0211_G0{number}" for number in range(1, 9)}
        audit_gates = audit.get("release_gates", {})
        contract_gates = contract.get("release_gates", {})
        if any(audit_gates.get(key) != contract_gates.get(key) for key in expected_gate_keys):
            raise ValueError("The final candidate audit and selected-release contract gate results differ.")

    ci = audit.get("ci", {})
    if not isinstance(ci, dict):
        raise ValueError("The candidate audit CI record is malformed.")
    jobs = ci.get("quality_jobs", {})
    if not isinstance(jobs, dict):
        raise ValueError("The candidate audit CI job matrix is malformed.")
    if not bounded_profile and (
        ci.get("quality_head_sha") != source_sha
        or ci.get("quality_conclusion") != "SUCCESS"
        or ci.get("documentation_head_sha") != source_sha
        or ci.get("documentation_conclusion") != "SUCCESS"
        or ci.get("ci_sha_exact_match") is not True
        or any(jobs.get(name) != "PASS" for name in (
            "ubuntu_python_3_10",
            "ubuntu_python_3_13",
            "windows_python_3_10",
            "windows_python_3_13",
            "wp14_recovered_evidence_targeted",
            "documentation_evidence",
            "full_engineering_campaign",
        ))
    ):
        raise ValueError("The candidate audit does not contain successful exact-source Quality and Documentation CI.")
    if contract.get("package_version") == "0.2.12" and not bounded_profile:
        if not pypi_only:
            raise ValueError("The v0.2.12 workflow requires an explicitly bounded PyPI-only contract.")
        _validate_tagged_engineering_ci(root, head, source_sha, contract, ci)

    built = audit.get("build_and_artifacts", {})
    if not isinstance(built, dict):
        raise ValueError("The candidate audit build record is malformed.")
    expected_artifacts = contract.get("audited_artifacts", {})
    expected_manifest = contract.get("sha256_manifest", {})
    if not isinstance(expected_artifacts, dict) or not isinstance(expected_manifest, dict):
        raise ValueError("The selected-release artifact bindings are malformed.")
    wheel = built.get("wheel", {})
    sdist = built.get("sdist", {})
    manifest = built.get("manifest", {})
    if (
        wheel.get("filename") != expected_artifacts.get("wheel", {}).get("filename")
        or wheel.get("sha256") != expected_artifacts.get("wheel", {}).get("sha256")
        or wheel.get("size_bytes") != expected_artifacts.get("wheel", {}).get("bytes")
        or wheel.get("independent_builds_byte_identical") is not True
        or sdist.get("filename") != expected_artifacts.get("sdist", {}).get("filename")
        or sdist.get("sha256") != expected_artifacts.get("sdist", {}).get("sha256")
        or sdist.get("size_bytes") != expected_artifacts.get("sdist", {}).get("bytes")
        or sdist.get("normalized_builds_byte_identical") is not True
        or manifest.get("filename") != expected_manifest.get("filename")
        or manifest.get("sha256") != expected_manifest.get("sha256")
        or manifest.get("size_bytes") != expected_manifest.get("bytes")
        or audit.get("build_and_artifacts", {}).get("twine_check") != "PASS"
    ):
        raise ValueError("The candidate audit artifact bytes or reproducibility results differ from the Owner contract.")
    probes = built.get("installed_package_probes", {})
    if not isinstance(probes, dict):
        raise ValueError("The candidate audit installation-probe record is malformed.")
    if (
        probes.get("isolated_no_index_no_deps_install") != "PASS"
        or probes.get("imports_outside_checkout_and_safe_path") != "PASS"
        or probes.get("installed_import_origins") != "PASS"
        or probes.get("version_and_cli_probes") != "PASS"
        or (not bounded_profile and probes.get("static_smoke") != "PASS")
        or (not bounded_profile and probes.get("modal_smoke") != "PASS")
        or (not bounded_profile and probes.get("rotating_modal_smoke") != "PASS_EXPERIMENTAL")
        or (not bounded_profile and probes.get("campbell_smoke") != "PASS_EXPERIMENTAL")
    ):
        raise ValueError("The candidate audit installed-package probes are incomplete or failing.")

    scan = audit.get("selected_scope_audit", {})
    if not isinstance(scan, dict):
        raise ValueError("The candidate audit selected-scope scan record is malformed.")
    selected_scope = contract.get("selected_scope")
    if not isinstance(selected_scope, dict):
        raise ValueError("The selected-release contract has no bounded selected-scope counts.")
    if (
        scan.get("status") != "PASS_BOUNDED_PUBLIC_SURFACES"
        or scan.get("selected_package_files") != selected_scope.get("package_source_files")
        or scan.get("selected_package_findings") != 0
        or scan.get("served_document_files") != selected_scope.get("served_document_files")
        or scan.get("served_document_findings") != 0
        or scan.get("whole_repository_scanned") is not False
        or scan.get("whole_repository_g03") != "FAIL_PRESERVED"
    ):
        raise ValueError("The candidate audit selected-scope scans do not match the frozen release contract.")


def verify_artifact_set(dist: Path, contract: dict[str, Any]) -> dict[str, Any]:
    """Require exactly the two frozen packages and their exact SHA-256 manifest."""
    artifacts = contract.get("audited_artifacts")
    manifest = contract.get("sha256_manifest")
    if not isinstance(artifacts, dict) or set(artifacts) != {"wheel", "sdist"}:
        raise ValueError("The release contract must bind exactly one wheel and one sdist.")
    if not isinstance(manifest, dict) or set(manifest) != {"filename", "bytes", "sha256"}:
        raise ValueError("The release contract must bind one SHA-256 manifest.")

    expected: dict[str, dict[str, Any]] = {}
    for kind in ("wheel", "sdist"):
        binding = artifacts[kind]
        if not isinstance(binding, dict) or set(binding) != {"filename", "bytes", "sha256"}:
            raise ValueError(f"The frozen {kind} artifact binding is malformed.")
        filename = binding["filename"]
        _relative_path(filename)
        if Path(filename).name != filename or not filename.endswith(".whl" if kind == "wheel" else ".tar.gz"):
            raise ValueError(f"The frozen {kind} artifact filename is invalid.")
        if (
            not isinstance(binding["bytes"], int)
            or isinstance(binding["bytes"], bool)
            or binding["bytes"] <= 0
            or not isinstance(binding["sha256"], str)
            or len(binding["sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in binding["sha256"])
        ):
            raise ValueError(f"The frozen {kind} artifact binding is malformed.")
        expected[filename] = binding

    manifest_name = manifest["filename"]
    _relative_path(manifest_name)
    if Path(manifest_name).name != manifest_name or not manifest_name.endswith("-SHA256SUMS.txt"):
        raise ValueError("The frozen SHA-256 manifest filename is invalid.")
    if (
        not isinstance(manifest["bytes"], int)
        or isinstance(manifest["bytes"], bool)
        or manifest["bytes"] <= 0
        or not isinstance(manifest["sha256"], str)
        or len(manifest["sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in manifest["sha256"])
    ):
        raise ValueError("The frozen SHA-256 manifest binding is malformed.")
    expected[manifest_name] = manifest

    entries = list(dist.iterdir())
    if any(entry.is_symlink() or not entry.is_file() for entry in entries):
        raise ValueError("Release assets must be regular files without symlinks.")
    if {entry.name for entry in entries} != set(expected) or len(entries) != len(expected):
        raise ValueError("Release assets must contain only the two selected packages and SHA-256 manifest.")

    observed: dict[str, dict[str, Any]] = {}
    for name, binding in expected.items():
        path = dist / name
        payload = path.read_bytes()
        current = {"filename": name, "bytes": len(payload), "sha256": digest(payload)}
        if current != binding:
            raise ValueError(f"Release asset differs from the authorized contract: {name}")
        observed[name] = current

    wheel = artifacts["wheel"]
    sdist = artifacts["sdist"]
    manifest_text = (
        f"{wheel['sha256']}  {wheel['filename']}\n"
        f"{sdist['sha256']}  {sdist['filename']}\n"
    ).encode("ascii")
    if (dist / manifest_name).read_bytes() != manifest_text:
        raise ValueError("The SHA-256 manifest does not exactly describe the selected package bytes.")
    return {"status": "PASS_EXACT_RELEASE_ASSETS", "files": list(observed.values())}


def validate_owner_artifact_scope(contract: dict[str, Any], owner_record: dict[str, Any]) -> None:
    """Require the contract and prospective Owner record to agree on exact release identity and bytes."""
    schema_version = contract.get("schema_version")
    if schema_version not in SUPPORTED_RELEASE_CONTRACT_SCHEMA_VERSIONS:
        raise ValueError("Unknown selected-release contract schema; refusing implicit fallback.")

    version = contract.get("package_version")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("The selected-release contract has no stable package version.")
    if contract.get("status") != "OWNER_AUTHORIZED_SELECTED_PACKAGE_RELEASE":
        raise ValueError("The selected-release contract is not explicitly Owner-authorized.")
    bounded_profile = contract.get("validation_profile") == BOUNDED_PROFILE
    if schema_version == 3 or bounded_profile:
        if not bounded_profile or schema_version != 3:
            raise ValueError("The bounded profile requires its dedicated schema version and explicit opt-in.")
        if (
            version != "0.2.12"
            or contract.get("source_sha") != BOUNDED_SOURCE_SHA
            or contract.get("release_tag") != "v0.2.12"
            or contract.get("tag_object_sha") != BOUNDED_TAG_OBJECT_SHA
            or not isinstance(contract.get("smoke_manifest_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", contract["smoke_manifest_sha256"])
            or not isinstance(contract.get("smoke_plan_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", contract["smoke_plan_sha256"])
            or contract.get("documentation_scope_audit_sha256") != BOUNDED_DOC_SCOPE_SHA256
            or contract.get("audited_artifacts") != BOUNDED_ARTIFACTS
            or contract.get("sha256_manifest") != BOUNDED_CHECKSUM_MANIFEST
            or contract.get("legal_review_status") != "NOT_ACQUIRED"
            or owner_record.get("validation_profile") != BOUNDED_PROFILE
            or owner_record.get("bounded_profile_approved") is not True
            or owner_record.get("approved_smoke_manifest_sha256") != contract.get("smoke_manifest_sha256")
            or owner_record.get("approved_smoke_plan_sha256") != contract.get("smoke_plan_sha256")
            or owner_record.get("legal_review_status") != "NOT_ACQUIRED"
        ):
            raise ValueError("The bounded profile lacks explicit matching Owner approval for exact v0.2.12 inputs.")
    expected_decisions = {
        f"AUTHORIZE_V{version.replace('.', '_')}_PUBLICATION",
        "AUTHORIZE_SELECTED_PACKAGE_RELEASE",
    }
    approved_source = owner_record.get("authorized_source_sha")
    if (
        owner_record.get("decision") not in expected_decisions
        or owner_record.get("version") != version
        or owner_record.get("status") not in {
            "OWNER_AUTHORIZED_SELECTED_PACKAGE_RELEASE",
            "OWNER_REAUTHORIZED_LATER_AUDITED_RELEASE_CANDIDATE",
        }
        or not isinstance(approved_source, str)
        or not re.fullmatch(r"[0-9a-f]{40}", approved_source)
        or contract.get("source_sha") != approved_source
        or contract.get("tag_target_sha") != approved_source
        or owner_record.get("authorized_tag_target_sha") != approved_source
        or owner_record.get("authorized_tag") != f"v{version}"
        or contract.get("release_tag") != f"v{version}"
    ):
        raise ValueError("The candidate source differs from the exact source accepted by the Owner.")

    artifacts = contract.get("audited_artifacts")
    approved_artifacts = owner_record.get("authorized_artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != {"wheel", "sdist"}:
        raise ValueError("The selected-release contract must bind exactly one wheel and one sdist.")
    if not isinstance(approved_artifacts, dict) or set(approved_artifacts) != {"wheel", "sdist", "manifest"}:
        raise ValueError("The Owner record must bind exactly the selected wheel, sdist and manifest.")
    manifest = contract.get("sha256_manifest")
    if not isinstance(manifest, dict):
        raise ValueError("The selected-release contract has no checksum manifest binding.")
    candidate_bindings = {"wheel": artifacts["wheel"], "sdist": artifacts["sdist"], "manifest": manifest}
    for kind, candidate in candidate_bindings.items():
        approved = approved_artifacts.get(kind)
        if not isinstance(approved, dict) or set(approved) != {"filename", "bytes", "sha256"}:
            raise ValueError(f"The Owner authorization lacks a complete {kind} artifact binding.")
        if not isinstance(candidate, dict) or set(candidate) != {"filename", "bytes", "sha256"}:
            raise ValueError(f"The selected-release contract has a malformed {kind} binding.")
        candidate_size = candidate.get("bytes")
        if (
            not isinstance(candidate.get("filename"), str)
            or not isinstance(candidate_size, int)
            or isinstance(candidate_size, bool)
            or candidate_size <= 0
            or not isinstance(candidate.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", candidate["sha256"])
        ):
            raise ValueError(f"The selected-release contract has an invalid {kind} binding.")
        if candidate != approved:
            raise ValueError(f"The candidate {kind} bytes differ from the exact artifact accepted by the Owner.")

    if (
        not artifacts["wheel"]["filename"].startswith(f"qf_solver-{version}-")
        or not artifacts["wheel"]["filename"].endswith(".whl")
        or artifacts["sdist"]["filename"] != f"qf_solver-{version}.tar.gz"
        or not manifest["filename"].startswith(f"qf_solver-{version}-")
        or not manifest["filename"].endswith("-SHA256SUMS.txt")
    ):
        raise ValueError("Selected artifact filenames do not identify the authorized package version.")

    github_allowed, zenodo_allowed = _release_channel_permissions(contract)
    if "release_channels" in contract:
        if owner_record.get("release_channels") != contract["release_channels"]:
            raise ValueError("The Owner record and release contract must name the same release channels.")

    required_authorization = {
        "selected_package_publication_allowed": True,
        "tag_creation_allowed": True,
        "pypi_publication_allowed": True,
        "github_release_allowed": github_allowed,
        "zenodo_selected_artifact_publication_allowed": zenodo_allowed,
        "whole_repository_archive_cleared": False,
        "whole_repository_archive_publication_allowed": False,
        "ledger_update_allowed": False,
        "wp14_promotion_allowed": False,
        "numeric_maturity_promotion_allowed": False,
        "historical_result_reclassification_allowed": False,
        "certification_or_universal_validation_claims_allowed": False,
    }
    if owner_record.get("authorization") != required_authorization:
        raise ValueError("The Owner authorization permissions broaden or weaken the selected-release boundary.")
    if "release_channels" in contract and contract.get("authorization") != required_authorization:
        raise ValueError("The release contract permissions do not match its explicit release channels.")
    required_top_level_flags = {
        "selected_package_publication_allowed": True,
        "tag_creation_allowed": True,
        "pypi_publication_allowed": True,
        "github_release_allowed": github_allowed,
        "zenodo_selected_artifact_publication_allowed": zenodo_allowed,
        "whole_repository_archive_cleared": False,
        "whole_repository_archive_publication_allowed": False,
        "wp14_promotion_allowed": False,
        "numeric_maturity_promotion_allowed": False,
        "historical_result_reclassification_allowed": False,
        "ledger_update_allowed": False,
        "certification_or_universal_validation_claims_allowed": False,
    }
    if any(owner_record.get(key) is not expected for key, expected in required_top_level_flags.items()):
        raise ValueError("The Owner record's direct permissions broaden or weaken the selected-release boundary.")
    required_hashes = {
        "authorized_wheel_sha256": approved_artifacts["wheel"].get("sha256"),
        "authorized_sdist_sha256": approved_artifacts["sdist"].get("sha256"),
        "authorized_manifest_sha256": approved_artifacts["manifest"].get("sha256"),
    }
    if any(owner_record.get(key) != expected for key, expected in required_hashes.items()):
        raise ValueError("The Owner record's direct artifact hashes differ from its exact artifact bindings.")
    required_preserved = {
        "g03_status": "FAIL_PRESERVED",
        "whole_repository_archive_cleared": False,
        "wp14_status": "HOLD_NOT_PROMOTED",
        "numeric_maturity_promotion_allowed": False,
        "historical_result_reclassification_allowed": False,
        "ledger_update_allowed": False,
    }
    if any(owner_record.get(key) != expected for key, expected in required_preserved.items()):
        raise ValueError("The Owner record changes the preserved release boundary.")
    if owner_record.get("whole_repository_archive_publication_allowed") is not False:
        raise ValueError("The Owner record permits whole-repository archive publication despite G03.")
    if any(contract.get(key) != expected for key, expected in required_preserved.items() if key != "numeric_maturity_promotion_allowed" and key != "historical_result_reclassification_allowed" and key != "ledger_update_allowed"):
        raise ValueError("The release contract does not preserve G03 and WP14 archive boundaries.")
    if contract.get("whole_repository_archive_publication_allowed") is not False:
        raise ValueError("The release contract permits a whole-repository archive despite G03.")
    expected_gate_summary = {
        "g03_status": "FAIL_PRESERVED",
        "whole_repository_archive_cleared": False,
        "wp14_status": "HOLD_NOT_PROMOTED",
    }
    if owner_record.get("preserved_gates") != expected_gate_summary:
        raise ValueError("The Owner record's preserved gate summary is inconsistent.")

    scope = contract.get("publication_scope")
    if schema_version == 1 and scope is None:
        # Explicit adapter for the unchanged 0.2.10 contract shape.
        scope = "SELECTED_DISTRIBUTION"
    if scope != "SELECTED_DISTRIBUTION":
        raise ValueError("This verifier authorizes only an explicit selected-distribution scope.")
    if schema_version >= 2 and owner_record.get("publication_scope") != scope:
        raise ValueError("The Owner record and release contract must name the same selected scope.")
    g03_status = contract.get("g03_status")
    archive_cleared = contract.get("whole_repository_archive_cleared")
    if not isinstance(scope, str) or not isinstance(g03_status, str) or not isinstance(archive_cleared, bool):
        raise ValueError("The selected-release scope and preserved G03 state are malformed.")
    if _scope_policy(scope, g03_status, archive_cleared) != "ALLOWED":
        raise ValueError("The selected-release policy does not clear the declared publication scope.")

    release_gates = contract.get("release_gates")
    owner_gates = owner_record.get("release_gates")
    if schema_version == 3:
        if contract.get("extended_validation") != "NOT_RUN" or contract.get("wp14_validation") != "NOT_RUN":
            raise ValueError("The bounded profile must record extended validation and WP14 as NOT_RUN.")
    elif schema_version == 2 or release_gates is not None or owner_gates is not None:
        if not isinstance(release_gates, dict) or not isinstance(owner_gates, dict) or release_gates != owner_gates:
            raise ValueError("Owner and release-contract gate decisions differ.")
        required = {f"QF0211_G0{number}" for number in range(1, 9)}
        if set(release_gates) != required:
            raise ValueError("A 0.2.11 release contract must bind exactly QF0211 gates G01 through G08.")
        if any(release_gates[f"QF0211_G0{number}"] not in {"PASS", "INHERITED_PASS"} for number in range(1, 9)):
            raise ValueError("A required QF0211 release gate is not passing.")
    if version == "0.2.11":
        expected_maturity = {
            "rotating_modal": "EXPERIMENTAL",
            "campbell": "EXPERIMENTAL",
            "campbell_100_rad_s_ambiguity": "PRESERVED",
            "gyro_06_evidence": "INTERNAL_MESH_CONVERGENCE_ONLY",
        }
        if contract.get("maturities") != expected_maturity or owner_record.get("maturities") != expected_maturity:
            raise ValueError("The 0.2.11 contract must preserve the bounded experimental maturity and evidence claims.")
        expected_phase = {
            "current_phase": "PRE_PUBLICATION",
            "version_doi": "NOT_ASSIGNED",
            "release_date": "NOT_SET",
            "concept_doi": "10.5281/zenodo.22697897",
        }
        if (
            contract.get("publication_phase") != expected_phase
            or owner_record.get("publication_phase") != expected_phase
        ):
            raise ValueError("The 0.2.11 authorization must explicitly remain in the no-DOI prepublication phase.")


def _validate_superseded_owner_record(
    root: Path, head: str, owner_record: dict[str, Any], contract: dict[str, Any],
) -> None:
    previous = owner_record.get("superseded_record")
    previous_contract = contract.get("superseded_owner_authorization")
    if previous is None and previous_contract is None:
        if owner_record.get("supersedes_for_release") is not None:
            raise ValueError("Owner record names a superseded decision without binding its exact record.")
        return
    if not isinstance(previous, dict) or not isinstance(previous_contract, dict):
        raise ValueError("Superseded Owner decisions must be bound on both records or neither.")
    path = _relative_path(previous.get("path", ""))
    if previous != previous_contract:
        raise ValueError("The superseded Owner record reference differs from the prospective contract.")
    commit = previous.get("commit_sha")
    if (
        not isinstance(commit, str)
        or not re.fullmatch(r"[0-9a-f]{40}", commit)
        or not isinstance(previous.get("sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", previous["sha256"])
        or previous.get("historical_record_preserved") is not True
        or not isinstance(owner_record.get("supersedes_for_release"), str)
        or git_run(["merge-base", "--is-ancestor", commit, contract["source_sha"]], cwd=root).returncode
    ):
        raise ValueError("The reauthorization does not bind an exact prior decision in source history.")
    historical_bytes = git_run(["show", f"{commit}:{path}"], cwd=root, check=True).stdout
    current_bytes = _committed_bytes(root, head, path)
    if (
        hashlib.sha256(historical_bytes).hexdigest() != previous.get("sha256")
        or hashlib.sha256(current_bytes).hexdigest() != previous.get("sha256")
    ):
        raise ValueError("The historical Owner record was changed or does not match its recorded hash.")
    historical = json.loads(historical_bytes)
    if historical.get("record_id") != owner_record.get("supersedes_for_release"):
        raise ValueError("The historical Owner record identity does not match the superseded decision.")
    old_source = historical.get("authorized_source_sha") or historical.get("provenance", {}).get(
        "audited_package_source_sha"
    )
    if old_source == contract.get("source_sha"):
        raise ValueError("The prospective record must bind a distinct later candidate, not rewrite the prior decision.")


def _validate_contract(root: Path, contract_path: Path, candidate_path: Path) -> tuple[
    dict[str, Any], dict[str, Any], dict[str, bytes], list[dict[str, Any]], str
]:
    root = root.resolve(strict=True)
    contract_path = contract_path.resolve(strict=True)
    candidate_path = candidate_path.resolve(strict=True)
    if not contract_path.is_relative_to(root) or not candidate_path.is_relative_to(root):
        raise ValueError("Release contracts must be committed inside the repository.")
    head = git_run(["rev-parse", "HEAD"], cwd=root, check=True, text=True).stdout.strip()
    if git_run(["status", "--porcelain", "--untracked-files=all"], cwd=root, check=True).stdout.strip():
        raise ValueError("The release verification checkout must be clean.")

    relative_contract = contract_path.relative_to(root).as_posix()
    relative_candidate = candidate_path.relative_to(root).as_posix()
    release_contract = json.loads(_committed_bytes(root, head, relative_contract))
    schema_version = release_contract.get("schema_version")
    if schema_version not in SUPPORTED_RELEASE_CONTRACT_SCHEMA_VERSIONS:
        raise ValueError("Unknown selected-release contract schema; refusing implicit fallback.")
    source_contract = release_contract.get("source_contract", {})
    if source_contract.get("path") != relative_candidate:
        raise ValueError("The supplied frozen package contract path differs from the authorized release contract.")
    candidate_contract, payloads, mapping, execution_head = frozen_inputs(root, candidate_path)
    if execution_head != head:
        raise ValueError("Release contract validation observed inconsistent execution commits.")
    if release_contract.get("status") != "OWNER_AUTHORIZED_SELECTED_PACKAGE_RELEASE":
        raise ValueError("The release contract does not record an Owner-authorized selected release.")
    source_sha = release_contract.get("source_sha")
    if source_sha != candidate_contract.get("source_sha") or source_sha != release_contract.get("tag_target_sha"):
        raise ValueError("The authorized release source, frozen package source and tag target must be identical.")
    if git_run(["merge-base", "--is-ancestor", source_sha, head], cwd=root).returncode:
        raise ValueError("The audited package source is not an ancestor of the release-contract commit.")
    if candidate_contract.get("publication_allowed") is not False:
        raise ValueError("The prior candidate contract must remain unchanged and non-authorizing.")
    if candidate_contract.get("source_sha") != source_sha:
        raise ValueError("The selected package contract and authorization source differ.")

    candidate_commit = release_contract.get("source_contract", {}).get("commit_sha")
    candidate_digest = hashlib.sha256(_committed_bytes(root, head, relative_candidate)).hexdigest()
    if (
        not isinstance(candidate_commit, str)
        or candidate_digest != source_contract.get("sha256")
        or git_run(["merge-base", "--is-ancestor", candidate_commit, head], cwd=root).returncode
        or git_run(["merge-base", "--is-ancestor", source_sha, candidate_commit], cwd=root).returncode
        or hashlib.sha256(git_run(["show", f"{candidate_commit}:{relative_candidate}"], cwd=root, check=True).stdout).hexdigest()
        != candidate_digest
    ):
        raise ValueError("The prospective source contract commit or bytes do not match the release contract.")

    owner = release_contract.get("owner_authorization", {})
    owner_path = _relative_path(owner.get("path", ""))
    owner_commit = owner.get("commit_sha")
    if (
        not isinstance(owner_commit, str)
        or not re.fullmatch(r"[0-9a-f]{40}", owner_commit)
        or not isinstance(owner.get("sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", owner["sha256"])
        or not isinstance(owner.get("record_id"), str)
    ):
        raise ValueError("The release contract does not bind an exact prospective Owner authorization.")
    owner_bytes = _committed_bytes(root, head, owner_path)
    owner_record = json.loads(owner_bytes)
    recorded_owner_bytes = git_run(["show", f"{owner_commit}:{owner_path}"], cwd=root, check=True).stdout
    if (
        hashlib.sha256(owner_bytes).hexdigest() != owner.get("sha256")
        or hashlib.sha256(recorded_owner_bytes).hexdigest() != owner.get("sha256")
        or git_run(["merge-base", "--is-ancestor", owner_commit, head], cwd=root).returncode
        or git_run(["merge-base", "--is-ancestor", source_sha, owner_commit], cwd=root).returncode
    ):
        raise ValueError("The prospective Owner reauthorization is missing, changed, or out of source/governance order.")
    if (
        owner.get("record_id") != owner_record.get("record_id")
        or owner.get("supersedes_for_release") != owner_record.get("supersedes_for_release")
        or owner_record.get("status") not in {
            "OWNER_AUTHORIZED_SELECTED_PACKAGE_RELEASE",
            "OWNER_REAUTHORIZED_LATER_AUDITED_RELEASE_CANDIDATE",
        }
    ):
        raise ValueError("The contract does not identify the exact prospective Owner authorization.")
    _validate_superseded_owner_record(root, head, owner_record, release_contract)
    validate_owner_artifact_scope(release_contract, owner_record)
    if release_contract.get("package_version") == "0.2.12":
        if release_contract.get("validation_profile") == BOUNDED_PROFILE:
            if owner_record.get("pypi_artifact_source") != release_contract.get("pypi_artifact_source"):
                raise ValueError("The Owner record must bind the same exact PyPI staging run and artifact.")
        elif (
            owner_record.get("tagged_engineering_ci") != release_contract.get("tagged_engineering_ci")
            or owner_record.get("pypi_artifact_source") != release_contract.get("pypi_artifact_source")
        ):
            raise ValueError("The Owner record must bind the same engineering evidence and PyPI artifact transport.")
    _validate_candidate_audit(root, head, source_sha, release_contract)
    resolution = release_contract.get("authorization_resolution", {})
    resolution_hashes = {
        "owner_approved_wheel_sha256": release_contract["audited_artifacts"]["wheel"]["sha256"],
        "candidate_wheel_sha256": release_contract["audited_artifacts"]["wheel"]["sha256"],
        "owner_approved_sdist_sha256": release_contract["audited_artifacts"]["sdist"]["sha256"],
        "candidate_sdist_sha256": release_contract["audited_artifacts"]["sdist"]["sha256"],
        "owner_approved_manifest_sha256": release_contract["sha256_manifest"]["sha256"],
        "candidate_manifest_sha256": release_contract["sha256_manifest"]["sha256"],
    }
    if (
        resolution.get("status") not in {
            "RESOLVED_BY_OWNER_REAUTHORIZATION",
            "RESOLVED_BY_EXACT_OWNER_AUTHORIZATION",
        }
        or resolution.get("owner_approved_source_sha") != source_sha
        or resolution.get("candidate_source_sha") != source_sha
        or any(resolution.get(key) != value for key, value in resolution_hashes.items())
    ):
        raise ValueError("The release contract's Owner reauthorization resolution is stale or inconsistent.")

    github_allowed, zenodo_allowed = _release_channel_permissions(release_contract)
    required_authority = {
        "selected_package_publication_allowed": True,
        "tag_creation_allowed": True,
        "pypi_publication_allowed": True,
        "github_release_allowed": github_allowed,
        "zenodo_selected_artifact_publication_allowed": zenodo_allowed,
        "whole_repository_archive_cleared": False,
        "whole_repository_archive_publication_allowed": False,
        "ledger_update_allowed": False,
        "wp14_promotion_allowed": False,
        "numeric_maturity_promotion_allowed": False,
        "historical_result_reclassification_allowed": False,
        "certification_or_universal_validation_claims_allowed": False,
    }
    if release_contract.get("authorization") != required_authority:
        raise ValueError("The prospective release contract broadens or weakens the Owner's bounded authority.")
    if (
        release_contract.get("g03_status") != "FAIL_PRESERVED"
        or release_contract.get("whole_repository_archive_cleared") is not False
        or release_contract.get("wp14_status") != "HOLD_NOT_PROMOTED"
    ):
        raise ValueError("G03 and WP14 must remain explicitly uncleared and unpromoted.")

    bindings = release_contract.get("tool_bindings")
    if schema_version == 1:
        # Version 1 was frozen with its tools in the last commit that changed
        # that historical contract. Verify those historical Git blobs rather
        # than silently comparing them with today's release tooling.
        frozen_contract_commit = git_run(
            ["log", "-1", "--format=%H", head, "--", relative_contract],
            cwd=root,
            check=True,
            text=True,
        ).stdout.strip()
        _check_tool_bindings(root, frozen_contract_commit, bindings)
    else:
        _check_tool_bindings(root, head, bindings)
    manifest_path = _relative_path(release_contract.get("manifest_repository_path", ""))
    manifest_bytes = _committed_bytes(root, head, manifest_path)
    manifest_binding = release_contract["sha256_manifest"]
    if (
        len(manifest_bytes) != manifest_binding.get("bytes")
        or hashlib.sha256(manifest_bytes).hexdigest() != manifest_binding.get("sha256")
    ):
        raise ValueError("Committed SHA-256 manifest bytes do not match the release contract.")
    selected_scope = release_contract.get("selected_scope")
    if not isinstance(selected_scope, dict) or len(payloads) != selected_scope.get("package_source_files"):
        raise ValueError("The selected package file count differs from the prospective release contract.")
    if release_contract.get("package_version") != candidate_contract.get("package_version"):
        raise ValueError("The authorized package version differs from the frozen package contract.")
    return release_contract, candidate_contract, payloads, mapping, head


def verify_authorized_release(
    root: Path, contract_path: Path, candidate_path: Path, dist: Path, output: Path,
) -> dict[str, Any]:
    root = root.resolve(strict=True)
    dist = dist.resolve(strict=True)
    output = output.resolve()
    if output.is_relative_to(root) or root.is_relative_to(output) or output.exists():
        raise ValueError("Use a new external evidence directory; existing outputs are never overwritten.")
    if dist.is_relative_to(root) or root.is_relative_to(dist):
        raise ValueError("The release asset directory must be external to the repository.")

    contract, candidate, payloads, mapping, head = _validate_contract(root, contract_path, candidate_path)
    assets = verify_artifact_set(dist, contract)
    output.mkdir(parents=True, exist_ok=False)
    neutral = output / "outside_checkout"
    logs = output / "logs"
    published_dist = output / "dist"
    for path in (neutral, logs, published_dist):
        path.mkdir()
    for kind in ("wheel", "sdist"):
        name = contract["audited_artifacts"][kind]["filename"]
        shutil.copyfile(dist / name, published_dist / name)

    package_check = verify_archives(published_dist, payloads, contract["package_version"])
    observed = {item["path"]: item for item in package_check["binaries"]}
    for kind in ("wheel", "sdist"):
        actual = observed.get(contract["audited_artifacts"][kind]["filename"])
        expected = contract["audited_artifacts"][kind]
        if actual != {
            "path": expected["filename"],
            "bytes": expected["bytes"],
            "sha256": expected["sha256"],
        }:
            raise ValueError(f"Exact {kind} bytes differ from the authorized artifact binding.")
    write_record(output / "source_mapping.json", mapping)
    write_record(output / "package_check.json", package_check)
    write_record(output / "asset_check.json", assets)

    records: list[dict[str, Any]] = []
    run_command(
        [sys.executable, "-m", "twine", "check",
         str(published_dist / package_check["wheel"]), str(published_dist / package_check["sdist"])],
        neutral, logs, records,
    )
    run_command(
        [sys.executable, str(root / "scripts" / "check_distribution.py"),
         str(published_dist / package_check["wheel"]), str(published_dist / package_check["sdist"])],
        neutral, logs, records,
    )
    environment = output / "installed_env"
    run_command([sys.executable, "-m", "venv", "--system-site-packages", str(environment)], neutral, logs, records)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    run_command(
        [str(python), "-I", "-m", "pip", "install", "--no-deps", "--no-index",
         str(published_dist / package_check["wheel"])],
        neutral, logs, records,
    )
    console = environment / ("Scripts" if os.name == "nt" else "bin")
    for name in ("qf-solver", "solveur-ef", "mitc4-solver"):
        launcher = console / (name + ".exe" if os.name == "nt" else name)
        run_command([str(launcher), "--version"], neutral, logs, records)
    qf = console / ("qf-solver.exe" if os.name == "nt" else "qf-solver")
    run_command([str(qf), "--help"], neutral, logs, records)
    probe = root / "scripts" / "probe_installed_package.py"
    probes = []
    for label, cwd in (("outside_checkout", neutral), ("inside_checkout", root)):
        report = output / f"{label}_probe.json"
        run_command(
            installed_probe_command(python, probe, output / "source_mapping.json",
                                    contract["package_version"], report),
            cwd, logs, records,
        )
        probes.append(json.loads(report.read_text(encoding="utf-8")))

    result = {
        "status": "PASS_AUTHORIZED_SELECTED_ARTIFACTS_ONLY",
        "release_tag": contract["release_tag"],
        "package_version": contract["package_version"],
        "source_sha": contract["source_sha"],
        "execution_sha": head,
        "release_contract_commit_sha": git_run(
            ["log", "-1", "--format=%H", head, "--", contract_path.resolve().relative_to(root).as_posix()],
            cwd=root, check=True, text=True,
        ).stdout.strip(),
        "release_contract_sha256": hashlib.sha256(
            git_run(["show", f"{head}:{contract_path.resolve().relative_to(root).as_posix()}"], cwd=root, check=True).stdout
        ).hexdigest(),
        "source_contract_sha256": candidate["contract_sha256"],
        "owner_authorization_commit_sha": contract["owner_authorization"]["commit_sha"],
        "package_check": package_check,
        "release_asset_check": assets,
        "installed_probes": probes,
        "artifact_audit_runtime": {
            "python": sys.version,
            "executable": sys.executable,
            "setuptools": importlib.metadata.version("setuptools"),
            "twine": importlib.metadata.version("twine"),
        },
        "build_policy": contract["build_provenance"],
        "publication_performed": False,
        "g03_status": "FAIL_PRESERVED",
        "whole_repository_archive_cleared": False,
        "wp14_status": "HOLD_NOT_PROMOTED",
        "ledger_changed": False,
        "structural_solves_run": False,
        "numeric_maturity_changed": False,
    }
    write_record(output / "commands.json", records)
    write_record(output / "result.json", result)
    files = sorted(path for path in output.rglob("*") if path.is_file())
    write_record(output / "manifest.json", {
        "files": [
            {"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size,
             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in files
        ],
        "includes_prebuilt_selected_artifacts_and_install_logs": True,
        "rebuild_performed": False,
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--source-contract", type=Path, required=True)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(
            verify_authorized_release(args.root, args.contract, args.source_contract, args.dist, args.output),
            indent=2,
        ))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"FAIL_CLOSED: {type(exc).__name__}: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
