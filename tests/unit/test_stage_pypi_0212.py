"""Synthetic checks for the exact 0.2.12 package asset staging utility."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from scripts.stage_pypi_0212 import (
    CHECKSUM_NAME,
    CHECKSUM_SHA256,
    SDIST_BYTES,
    SDIST_SHA256,
    SOURCE_SHA,
    WHEEL_BYTES,
    WHEEL_SHA256,
    _download_https,
    _write_selected_assets,
    checksum_manifest,
)



def test_release_stage_is_frozen_to_qualified_f6_artifacts() -> None:
    assert SOURCE_SHA == "f6f63eb8701e38b41aae0d735850e8cf50b07fa5"
    assert WHEEL_BYTES == 1_709_716
    assert WHEEL_SHA256 == "a09368d4d1d79f5b7fc10ff5c4c3a96dfa5d245a20bd9984704b8ab472d4c719"
    assert SDIST_BYTES == 1_344_948
    assert SDIST_SHA256 == "1b6a980c4ecb3dce1ed5a885a69c9cc66d1efd62af85fba20bb0ed13daac1cd1"
    assert CHECKSUM_NAME == "qf_solver-0.2.12-f6f63eb-SHA256SUMS.txt"
    assert CHECKSUM_SHA256 == "bc20da5094e4d250dc33be7aa379e07a654e20b8ba787ad596cac9801c62c634"

def test_stager_writes_exact_hash_bound_file_set_and_refuses_substitution(tmp_path: Path) -> None:
    wheel = b"wheel fixture"
    sdist = b"sdist fixture"
    wheel_sha = hashlib.sha256(wheel).hexdigest()
    sdist_sha = hashlib.sha256(sdist).hexdigest()
    expected_manifest_sha = hashlib.sha256(checksum_manifest(wheel_sha, sdist_sha)).hexdigest()

    output = tmp_path / "dist"
    result = _write_selected_assets(
        output,
        wheel,
        sdist,
        wheel_size=len(wheel),
        sdist_size=len(sdist),
        wheel_sha256=wheel_sha,
        sdist_sha256=sdist_sha,
        checksum_sha256=expected_manifest_sha,
    )
    assert result["status"] == "PASS_EXACT_SELECTED_ASSETS_STAGED"
    assert result["source_sha"] == "f6f63eb8701e38b41aae0d735850e8cf50b07fa5"
    assert {path.name for path in output.iterdir()} == {
        "qf_solver-0.2.12-py3-none-any.whl",
        "qf_solver-0.2.12.tar.gz",
        "qf_solver-0.2.12-f6f63eb-SHA256SUMS.txt",
    }
    assert hashlib.sha256((output / "qf_solver-0.2.12-py3-none-any.whl").read_bytes()).hexdigest() == wheel_sha
    assert hashlib.sha256((output / "qf_solver-0.2.12.tar.gz").read_bytes()).hexdigest() == sdist_sha
    assert hashlib.sha256(
        (output / "qf_solver-0.2.12-f6f63eb-SHA256SUMS.txt").read_bytes()
    ).hexdigest() == expected_manifest_sha

    with pytest.raises(ValueError, match="SHA-256 does not match"):
        _write_selected_assets(
            tmp_path / "wrong",
            wheel,
            sdist + b"substitution",
            wheel_size=len(wheel),
            sdist_size=len(sdist) + len(b"substitution"),
            wheel_sha256=wheel_sha,
            sdist_sha256=sdist_sha,
            checksum_sha256=expected_manifest_sha,
        )

    with pytest.raises(ValueError, match="HTTPS URL"):
        _download_https("http://example.invalid/package", 1)


def test_staging_workflow_is_manual_bounded_and_does_not_run_science() -> None:
    workflow_path = Path(__file__).resolve().parents[2] / ".github/workflows/stage-pypi-0212.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    events = workflow.get("on", workflow.get(True))
    assert set(events) == {"workflow_dispatch"}
    assert events["workflow_dispatch"]["inputs"]["confirm_exact_assets"]["default"] is False
    assert events["workflow_dispatch"]["inputs"]["expected_workflow_sha"]["required"] is True
    assert workflow["permissions"] == {"contents": "read"}

    job = workflow["jobs"]["stage"]
    assert job["name"] == "Stage exact selected PyPI inputs"
    assert job["timeout-minutes"] == 5
    assert job["environment"]["name"] == "qf0212-pypi-staging"
    checkout = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["persist-credentials"] is False
    identity = next(step for step in job["steps"] if step.get("name") == "Verify the tag, source and staging workflow context")
    assert identity["env"]["EXPECTED_SOURCE_TAG_OBJECT"] == "dbf8314b861ac7f3a963d6036080e7a96ca4b17e"
    assert identity["env"]["EXPECTED_SOURCE_SHA"] == SOURCE_SHA
    assert identity["env"]["EXPECTED_SOURCE_TREE"] == "aba6002504ce881abd9c0aed1fdb27a289e3dafd"
    upload = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/upload-artifact@"))
    assert upload["with"]["name"] == "qf0212-selected-pypi-inputs"
    assert upload["with"]["retention-days"] == 3
    assert len(upload["with"]["path"].splitlines()) == 3
    assert CHECKSUM_NAME in upload["with"]["path"]
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert "verify-all" not in commands
    assert "pytest" not in commands
    assert "--confirm-stage-exact-assets" in commands
