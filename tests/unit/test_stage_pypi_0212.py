"""Synthetic checks for the exact 0.2.12 package asset staging utility."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from scripts.stage_pypi_0212 import _download_https, _write_selected_assets, checksum_manifest


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
    assert {path.name for path in output.iterdir()} == {
        "qf_solver-0.2.12-py3-none-any.whl",
        "qf_solver-0.2.12.tar.gz",
        "qf_solver-0.2.12-69d0718-normalized-SHA256SUMS.txt",
    }
    assert hashlib.sha256((output / "qf_solver-0.2.12-py3-none-any.whl").read_bytes()).hexdigest() == wheel_sha
    assert hashlib.sha256((output / "qf_solver-0.2.12.tar.gz").read_bytes()).hexdigest() == sdist_sha
    assert hashlib.sha256(
        (output / "qf_solver-0.2.12-69d0718-normalized-SHA256SUMS.txt").read_bytes()
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
    upload = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/upload-artifact@"))
    assert upload["with"]["name"] == "qf0212-selected-pypi-inputs"
    assert upload["with"]["retention-days"] == 3
    assert len(upload["with"]["path"].splitlines()) == 3
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert "verify-all" not in commands
    assert "pytest" not in commands
    assert "--confirm-stage-exact-assets" in commands
