"""Check the PyPI workflow's routing without dispatching it."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_pypi_transport_preflight_binds_one_artifact_and_rejects_channel_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/publish-pypi.yml").read_text(encoding="utf-8"))
    events = workflow.get("on", workflow.get(True))
    assert set(events) == {"workflow_dispatch"}
    assert events["workflow_dispatch"]["inputs"]["run_extended_validation"]["default"] is False
    jobs = workflow["jobs"]
    assert jobs["quality"]["needs"] == "build"
    assert "inputs.run_extended_validation == true" in jobs["quality"]["if"]
    assert "inputs.run_extended_validation == true" in jobs["publish"]["if"]
    download = next(step for step in jobs["build"]["steps"] if "artifact-ids" in step.get("with", {}))
    assert download["if"] == "needs.preflight.outputs.asset_transport == 'actions'"
    assert download["with"]["merge-multiple"] is True
    assert jobs["build"]["permissions"] == {"actions": "read", "contents": "read"}
    step = next(step for step in jobs["preflight"]["steps"] if step.get("id") == "release_contract")
    script = step["run"].split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    source, tag_object = "a" * 40, "b" * 40
    contract_path, output = tmp_path / "contract.json", tmp_path / "outputs.txt"
    monkeypatch.setattr(sys, "argv", ["-", str(contract_path), "v0.2.12", source, tag_object])
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    authorization = {
        "selected_package_publication_allowed": True,
        "whole_repository_archive_publication_allowed": False,
        "pypi_publication_allowed": True,
        "github_release_allowed": False,
        "zenodo_selected_artifact_publication_allowed": False,
    }
    legacy = {
        "status": "OWNER_AUTHORIZED_SELECTED_PACKAGE_RELEASE",
        "publication_scope": "SELECTED_DISTRIBUTION",
        "package_version": "0.2.12",
        "release_tag": "v0.2.12",
        "source_sha": source,
        "tag_object_sha": tag_object,
        "g03_status": "FAIL_PRESERVED",
        "whole_repository_archive_cleared": False,
        "wp14_status": "HOLD_NOT_PROMOTED",
        "authorization": authorization,
    }
    candidate = {
        **legacy,
        "release_channels": ["pypi"],
        "pypi_artifact_source": {"run_id": 10, "artifact_id": 11},
    }
    cases = [
        (legacy, {"asset_transport": "legacy-release"}),
        (candidate, {"asset_transport": "actions", "asset_run_id": "10", "asset_artifact_id": "11"}),
    ]
    for contract, expected in cases:
        contract_path.write_text(json.dumps(contract), encoding="utf-8")
        exec(compile(script, "release-preflight", "exec"), {})
        assert dict(line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines()) == expected
        output.unlink()
    for overrides in (
        {"release_channels": None},
        {"release_channels": ["pypi", "zenodo"]},
        {"pypi_artifact_source": {"run_id": 10, "artifact_id": True}},
        {"pypi_artifact_source": {"run_id": 10, "artifact_id": 2**53}},
        {"authorization": {**authorization, "github_release_allowed": True}},
        {"tag_object_sha": "c" * 40},
        {"source_sha": "d" * 40},
    ):
        contract_path.write_text(json.dumps({**candidate, **overrides}), encoding="utf-8")
        with pytest.raises(SystemExit):
            exec(compile(script, "release-preflight", "exec"), {})
        assert not output.exists()
