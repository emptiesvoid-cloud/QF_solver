"""Offline checks for the identity-only 0.2.12 engineering preflight."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github/workflows/release-engineering-0212.yml"


def _workflow() -> dict[str, object]:
    # BaseLoader keeps the YAML 1.2 `on` key as a string under PyYAML 1.1.
    loaded = yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(loaded, dict)
    return loaded


def test_workflow_is_manual_only_and_restricted_to_governance_ref() -> None:
    workflow = _workflow()
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["env"]["GOVERNANCE_REF"] == (
        "refs/heads/emptiesvoids-cloud/qf0212-pypi-qualification"
    )
    preflight = workflow["jobs"]["identity-preflight"]
    verify = next(step for step in preflight["steps"] if step.get("id") == "verify")
    script = verify["run"]
    assert 'test "$GITHUB_EVENT_NAME" = "workflow_dispatch"' in script
    assert 'test "$GITHUB_REF" = "$GOVERNANCE_REF"' in script


def test_workflow_freezes_tag_object_commit_and_tree_without_science_jobs() -> None:
    workflow = _workflow()
    env = workflow["env"]
    assert env["SOURCE_TAG"] == "v0.2.12"
    assert env["SOURCE_TAG_OBJECT"] == "7cf30876045d41af2e9f9fdf15034ff3dc3dcef5"
    assert env["SOURCE_SHA"] == "69d0718c805ea410ce5148ca0d1d39eae12736a1"
    assert env["SOURCE_TREE"] == "50cd5d2fd700a8d52485649f71181cdcd76bc722"

    jobs = workflow["jobs"]
    assert set(jobs) == {"identity-preflight", "preflight-receipt"}
    serialized = WORKFLOW_PATH.read_text(encoding="utf-8")
    forbidden_commands = (
        "qf_solver.py verify",
        "verify-all --profile engineering",
        "pytest -m benchmark",
        "tests/verification/test_wp04",
        "tests/documentation",
        "prepare_wp14_recovered_evidence.py",
    )
    assert all(command not in serialized for command in forbidden_commands)


def test_receipt_is_explicitly_non_scientific_and_contains_no_raw_artifact_upload() -> None:
    workflow = _workflow()
    receipt = workflow["jobs"]["preflight-receipt"]
    upload = next(step for step in receipt["steps"] if step.get("uses", "").startswith("actions/upload-artifact@"))
    assert upload["with"]["name"] == (
        "release-engineering-0212-preflight-${{ github.run_id }}-attempt-${{ github.run_attempt }}"
    )
    assert upload["with"]["retention-days"] == "7"
    assert "release_engineering_0212_preflight.json" in upload["with"]["path"]

    writer = next(step for step in receipt["steps"] if step.get("name") == "Write metadata-only identity receipt")
    assert '"kind": "identity_preflight_only"' in writer["run"]
    assert '"scientific_validation_performed": False' in writer["run"]
    assert "A successful preflight receipt is not a release or scientific PASS." in writer["run"]
    assert "actions/download-artifact" not in WORKFLOW_PATH.read_text(encoding="utf-8")


def test_identity_outputs_keep_workflow_and_tested_source_separate() -> None:
    workflow = _workflow()
    verify = next(
        step
        for step in workflow["jobs"]["identity-preflight"]["steps"]
        if step.get("id") == "verify"
    )
    script = verify["run"]
    assert 'printf \'workflow_sha=%s\\n\' "$GITHUB_SHA"' in script
    assert 'printf \'source_sha=%s\\n\' "$SOURCE_SHA"' in script
    assert 'printf \'source_tree=%s\\n\' "$SOURCE_TREE"' in script
    assert 'git rev-parse "refs/tags/$SOURCE_TAG^{commit}"' in script
    assert 'git rev-parse "$SOURCE_SHA^{tree}"' in script
