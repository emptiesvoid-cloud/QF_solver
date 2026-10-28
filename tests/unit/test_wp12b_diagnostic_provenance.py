"""Synthetic checks for prospective WP12-B diagnostic provenance; no FEM execution."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "development_autonomous.py"
SPEC = importlib.util.spec_from_file_location("development_autonomous_provenance_test", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


ATTEMPT_ID = "dev-0123456789ab-attempt-1"
NODEID = MODULE.WP12B_HEX20_DIAGNOSTIC_NODEID
WORKTREE_ID = MODULE.WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID
MANIFEST = {"authorization_id": "WP12B-HEX20-AFFINE-DIAG-R1", "sha256": "a" * 64}


def test_child_environment_carries_run_manifest_and_attempt_id(tmp_path: Path) -> None:
    run_json = tmp_path / "run.json"
    environment = MODULE.build_child_environment(
        tmp_path / "tmp",
        base={},
        source_root=tmp_path / "src",
        wp12_entry={
            "worktree_id": WORKTREE_ID,
            "execution_scope_id": WORKTREE_ID,
            "max_fem_cases_per_attempt": 1,
            "evidence_root": str(tmp_path / "evidence"),
            "target_max_dofs": 60,
        },
        wp12_selection={"selected_dofs": 60},
        wp12_attempt_id=ATTEMPT_ID,
        wp12_manifest_receipt=MANIFEST,
        wp12_run_json_path=run_json,
    )

    assert environment["QF_DEV_WORKTREE_ID"] == WORKTREE_ID
    assert environment["QF_DEV_SELECTED_DOFS"] == "60"
    assert environment["QF_DEV_ATTEMPT_ID"] == ATTEMPT_ID
    assert environment["QF_DEV_MANIFEST_ID"] == MANIFEST["authorization_id"]
    assert environment["QF_DEV_MANIFEST_SHA256"] == MANIFEST["sha256"]
    assert environment["QF_DEV_RUN_JSON_PATH"] == str(run_json.resolve())


def test_child_environment_rejects_partial_or_malformed_binding(tmp_path: Path) -> None:
    with pytest.raises(MODULE.PolicyError, match="identities together"):
        MODULE.build_child_environment(
            tmp_path,
            base={},
            wp12_attempt_id=ATTEMPT_ID,
        )
    with pytest.raises(MODULE.PolicyError, match="malformed"):
        MODULE.build_child_environment(
            tmp_path,
            base={},
            wp12_attempt_id="not-an-attempt-id",
            wp12_manifest_receipt=MANIFEST,
            wp12_run_json_path=tmp_path / "run.json",
        )


def test_run_json_sidecar_link_verifies_all_shared_identities(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    attempt_dir = evidence_root / "wp12b_hex20_affine_diagnostic"
    attempt_dir.mkdir(parents=True)
    run_json_path = tmp_path / "run.json"
    run_json_path.write_text(
        json.dumps(
            {
                "controller_attempt_id": ATTEMPT_ID,
                "worktree_id": WORKTREE_ID,
                "series_id": "dev-0123456789ab",
                "attempt": 1,
                "target": [NODEID],
                "execution_manifest": MANIFEST,
                "wp12_case_selection": {"selected_dofs": 60},
            }
        ),
        encoding="utf-8",
    )
    sidecar_path = attempt_dir / f"{ATTEMPT_ID}.json"
    sidecar = {
        "schema": "qfsolver-wp12b-hex20-affine-diagnostic-v1",
        "identity": {"nodeid": NODEID},
        "controller": {
            "worktree_id": WORKTREE_ID,
            "selected_dofs": 60,
            "controller_attempt_id": ATTEMPT_ID,
            "manifest_id": MANIFEST["authorization_id"],
            "manifest_sha256": MANIFEST["sha256"],
            "run_json_path": str(run_json_path.resolve()),
        },
    }
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")

    result = MODULE._wp12b_hex20_diagnostic_sidecar(
        worktree_id=WORKTREE_ID,
        target=NODEID,
        evidence_root=str(evidence_root),
        attempt_id=ATTEMPT_ID,
        manifest_receipt=MANIFEST,
        selected_dofs=60,
        run_json_path=run_json_path,
        sidecar_limit_bytes=256 * 1024 * 1024,
    )

    assert result is not None
    assert result["status"] == "VERIFIED"
    assert result["sha256"] == MODULE._sha256(sidecar_path)

    sidecar["controller"]["manifest_sha256"] = "b" * 64
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
    mismatch = MODULE._wp12b_hex20_diagnostic_sidecar(
        worktree_id=WORKTREE_ID,
        target=NODEID,
        evidence_root=str(evidence_root),
        attempt_id=ATTEMPT_ID,
        manifest_receipt=MANIFEST,
        selected_dofs=60,
        run_json_path=run_json_path,
        sidecar_limit_bytes=256 * 1024 * 1024,
    )
    assert mismatch is not None
    assert mismatch["status"] == "PROVENANCE_MISMATCH"

    expected_controller = {
        "worktree_id": WORKTREE_ID,
        "selected_dofs": 60,
        "controller_attempt_id": ATTEMPT_ID,
        "manifest_id": MANIFEST["authorization_id"],
        "manifest_sha256": MANIFEST["sha256"],
        "run_json_path": str(run_json_path.resolve()),
    }
    for field, wrong_value in {
        "worktree_id": "wp12_elements_loads",
        "selected_dofs": 30,
        "controller_attempt_id": "dev-fedcba987654-attempt-1",
        "manifest_id": "WP12B-OTHER-MANDATE-R1",
        "manifest_sha256": "b" * 64,
        "run_json_path": str(tmp_path / "other-run.json"),
    }.items():
        sidecar["controller"] = {**expected_controller, field: wrong_value}
        sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
        mismatch = MODULE._wp12b_hex20_diagnostic_sidecar(
            worktree_id=WORKTREE_ID,
            target=NODEID,
            evidence_root=str(evidence_root),
            attempt_id=ATTEMPT_ID,
            manifest_receipt=MANIFEST,
            selected_dofs=60,
            run_json_path=run_json_path,
            sidecar_limit_bytes=256 * 1024 * 1024,
        )
        assert mismatch is not None and mismatch["status"] == "PROVENANCE_MISMATCH"
