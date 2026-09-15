"""Targeted tests for the fail-closed WP08-D Phase-1 runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import run_wp08d_frictional_structural as runner
from scripts import wp08d_phase1_common as common


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "qualification" / "0_2_9" / "wp08d_phase1" / "wp08d_phase1_artifact_schema.json"


@pytest.mark.parametrize(
    ("mesh", "nodes", "elements", "dofs"),
    (("M1", 16, 12, 48), ("M2", 49, 96, 147), ("M3", 229, 768, 687)),
)
def test_phase1_dry_preflight_is_frozen_and_no_solve(mesh: str, nodes: int, elements: int, dofs: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        common,
        "verify_branch_provenance",
        lambda: {
            "branch": common.REQUIRED_BRANCH,
            "head": common.REQUIRED_GOVERNING_SHA,
            "required_governing_sha": common.REQUIRED_GOVERNING_SHA,
            "governing_sha_is_ancestor": True,
            "working_tree_clean": True,
        },
    )
    report = common.dry_run(mesh, tmp_path)
    assert report["status"] == "DRY_RUN_ONLY"
    assert report["preflight"]["mesh"]["nodes"] == nodes
    assert report["preflight"]["mesh"]["elements"] == elements
    assert report["preflight"]["mesh"]["dofs"] == dofs
    assert report["structural_solves_run"] is False
    assert report["preflight"]["reference_solves_run"] is False
    assert (tmp_path / f"dry_run_{mesh}.json").is_file()


def test_default_cli_is_fail_closed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert runner.main(["--mesh", "M1", "--output-dir", str(tmp_path)]) == 2
    assert common.UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED in capsys.readouterr().err


def test_execute_cli_requires_versioned_owner_authorization(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert runner.main(["--mesh", "M1", "--execute-phase1", "--output-dir", str(tmp_path)]) == 2
    assert common.UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_jsonl_telemetry_envelope_flushes_without_solver(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.jsonl"
    telemetry = common.Phase1Telemetry(path, analysis_id="test-phase1", mesh="M1")
    telemetry.emit("RUN_START", "ANALYSIS_START", status="STARTED", elapsed=0.0)
    telemetry.emit("MESH_READY", "MESH_READY", status="COMPLETED", increment=0, elapsed=0.01)
    telemetry.close()
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [row["metrics"]["phase1_event"] for row in rows] == ["RUN_START", "MESH_READY"]
    assert all(row["metadata"]["mesh"] == "M1" for row in rows)


def test_artifact_schema_declares_all_phase1_outputs() -> None:
    payload = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert payload["status"] == "PREPARATION_ONLY"
    assert set(payload["directories"]["M1"]) == {
        "result.json", "progress.json", "telemetry.jsonl", "raw.npz", "manifest.json"
    }
    assert payload["qualification_claim"] == "NO_PHASE1_EXECUTION_IN_THIS_FREEZE"


def test_replay_checker_is_evidence_only() -> None:
    left = {
        "status": "PASS",
        "solver": {},
        "node_count": 16,
        "element_count": 12,
        "ndof": 48,
        "observables": {
            "selected_displacement": 0.1,
            "cumulative_local_dissipation": 1.0,
            "force_balance_relative_error": 1.0e-15,
            "moment_balance_relative_error": 2.0e-15,
        },
    }
    right = dict(left)
    result = common.replay_comparison(left, right)
    assert result["status"] == "PASS"
    assert result["structural_solve_performed"] is False
