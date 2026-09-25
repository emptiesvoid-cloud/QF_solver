"""No-solve tests for sequential WP07/WP08 contact requalification evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from scripts import run_wp08d_contact_requalification as wp08_campaign
from scripts import run_wp07d_contact_requalification_r2 as wp07_campaign
from scripts import run_wp07d_structural as wp07_structural
from scripts import wp07d_execution_binding as wp07_binding
from scripts import wp08d_phase1_common as wp08_common


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _wp08_process_records(root: Path) -> list[dict[str, Any]]:
    meshes = ("M1", "M2", "M3")
    labels = [
        *(f"WP08D-{mesh}-PRIMARY_PRODUCTION" for mesh in meshes),
        *(f"WP08D-{mesh}-INDEPENDENT_REFERENCE" for mesh in meshes),
        "WP08D-M1-REPLAY",
    ]
    start = datetime(2026, 9, 25, tzinfo=timezone.utc)
    records: list[dict[str, Any]] = []
    for index, label in enumerate(labels):
        folder = root / "qualification" / "campaign" / f"case-{index}"
        folder.mkdir(parents=True)
        stdout = folder / "runner.stdout.log"
        stderr = folder / "runner.stderr.log"
        stdout.write_text(f"stdout-{index}\n", encoding="utf-8")
        stderr.write_text(f"stderr-{index}\n", encoding="utf-8")
        process = {
            "case": label,
            "command": ["python", "runner.py", "--case", label],
            "started_utc": (start + timedelta(seconds=index * 3)).isoformat().replace("+00:00", "Z"),
            "ended_utc": (start + timedelta(seconds=index * 3 + 2)).isoformat().replace("+00:00", "Z"),
            "pid": 5000 + index,
            "exit_code": 0,
            "invocation_error": None,
            "stdout_sha256": _sha256(stdout),
            "stderr_sha256": _sha256(stderr),
        }
        manifest = folder / "process.json"
        manifest.write_text(json.dumps(process, sort_keys=True) + "\n", encoding="utf-8")
        records.append(
            {
                "case": label,
                "process_manifest": manifest.relative_to(root).as_posix(),
                "sha256": _sha256(manifest),
                "pid": process["pid"],
                "exit_code": 0,
            }
        )
    return records


def test_wp08_campaign_process_audit_accepts_complete_serial_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp08_campaign, "ROOT", tmp_path)
    records = _wp08_process_records(tmp_path)

    audit = wp08_campaign._audit_process_sequence(records)

    assert audit["status"] == "PASS"
    assert audit["invocation_count"] == 7
    assert audit["sequential"] is True
    assert audit["errors"] == []


def test_wp08_campaign_process_audit_rejects_wrong_order_and_overlap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp08_campaign, "ROOT", tmp_path)
    records = _wp08_process_records(tmp_path)

    wrong_order = list(records)
    wrong_order[0], wrong_order[1] = wrong_order[1], wrong_order[0]
    assert wp08_campaign._audit_process_sequence(wrong_order)["status"] == "FAIL_CLOSED"

    second_manifest = tmp_path / records[1]["process_manifest"]
    second = json.loads(second_manifest.read_text(encoding="utf-8"))
    first = json.loads((tmp_path / records[0]["process_manifest"]).read_text(encoding="utf-8"))
    second["started_utc"] = first["started_utc"]
    second_manifest.write_text(json.dumps(second, sort_keys=True) + "\n", encoding="utf-8")
    records[1]["sha256"] = _sha256(second_manifest)

    audit = wp08_campaign._audit_process_sequence(records)

    assert audit["status"] == "FAIL_CLOSED"
    assert any("overlap" in error for error in audit["errors"])


def test_wp08_authorization_paths_use_linked_worktree_git_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    metadata_dir = tmp_path / "common-git-dir" / "worktrees" / "campaign"
    metadata_dir.mkdir(parents=True)
    monkeypatch.setattr(wp08_campaign, "_git", lambda *args: str(metadata_dir))

    owner_path = wp08_campaign._owner_authorization_path("a" * 40)
    case_path = wp08_campaign._case_authorization_path("a" * 40, "M1", "REPLAY")

    assert owner_path.parent == metadata_dir.resolve()
    assert case_path.parent == metadata_dir.resolve()
    assert ".git" not in owner_path.parts
    assert owner_path.name.endswith("a" * 40 + ".json")
    assert "_m1_replay_authorization.json" in case_path.name


def test_wp08_source_requalification_auth_uses_its_frozen_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = {
        **wp08_common.git_state(),
        "branch": wp08_common.CONTACT_REQUALIFICATION_REQUIRED_BRANCH,
        "dirty": False,
    }
    assert state["branch"] != wp08_common.REQUIRED_BRANCH
    payload = {
        "authorization": wp08_common.CONTACT_REQUALIFICATION_OWNER_TOKEN,
        "owner_authorized": True,
        "work_package": "WP08-D",
        "scope": "WP08-D_CONTACT_MECHANICS_REQUALIFICATION",
        "branch": wp08_common.CONTACT_REQUALIFICATION_REQUIRED_BRANCH,
        "execution_sha": state["head"],
        "requalification_contract_sha256": wp08_common.CONTACT_REQUALIFICATION_CONTRACT_SHA256,
        "parent_contract_digest": wp08_common.CONTRACT_DIGEST,
        "policy_digest": wp08_common.POLICY_DIGEST,
        "governing_base_sha": "b2485f98260c7ca9892997eefa3a327637d83cd3",
        "working_tree_clean": True,
        "execution_kind": "PRIMARY_PRODUCTION",
        "structural_solves_allowed": True,
        "independent_references_allowed": False,
        "replay_allowed": False,
    }
    authorization_path = tmp_path / "wp08-owner-authorization.json"
    authorization_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(wp08_common, "git_state", lambda: state)

    assert wp08_common._authorization_payload(authorization_path) == payload


def _wp07_gate(root: Path) -> dict[str, Any]:
    run_root = wp07_binding.CONTACT_REQUAL_R2_RUN_ROOT
    routes = wp07_binding.EXPECTED_ROUTES
    levels = wp07_binding.EXPECTED_LEVELS
    expected_order = [
        f"{route}/{level}/PRIMARY_PRODUCTION" for route in routes for level in levels
    ] + [f"{route}/{level}/INDEPENDENT_REFERENCE" for route in routes for level in levels]
    gate: dict[str, Any] = {
        "execution_sha": "e" * 40,
        "sequential_process_order": expected_order,
        "production_process_manifests": {},
        "reference_process_manifests": {},
    }
    start = datetime(2026, 9, 25, tzinfo=timezone.utc)
    sequence = 0
    for role, kind, folder in (
        ("production", "PRIMARY_PRODUCTION", "primary"),
        ("reference", "INDEPENDENT_REFERENCE", "reference"),
    ):
        for route in routes:
            for level in levels:
                case_dir = root / run_root / route / level / folder
                case_dir.mkdir(parents=True)
                stdout = case_dir / "runner.stdout.log"
                stderr = case_dir / "runner.stderr.log"
                stdout.write_text(f"out-{sequence}\n", encoding="utf-8")
                stderr.write_text(f"err-{sequence}\n", encoding="utf-8")
                label = f"{route}/{level}/{kind}"
                process = {
                    "case": label,
                    "route": route,
                    "mesh": level,
                    "execution_kind": kind,
                    "execution_sha": gate["execution_sha"],
                    "command": ["python", "runner.py", "--case", label],
                    "started_utc": (start + timedelta(seconds=sequence * 3)).isoformat().replace("+00:00", "Z"),
                    "ended_utc": (start + timedelta(seconds=sequence * 3 + 2)).isoformat().replace("+00:00", "Z"),
                    "pid": 7000 + sequence,
                    "exit_code": 0,
                    "invocation_error": None,
                    "stdout_sha256": _sha256(stdout),
                    "stderr_sha256": _sha256(stderr),
                }
                manifest_path = case_dir / "runner_process.json"
                manifest_path.write_text(json.dumps(process, sort_keys=True) + "\n", encoding="utf-8")
                key = f"{route}/{level}"
                gate[f"{role}_process_manifests"][key] = {
                    "path": (run_root / route / level / folder / "runner_process.json").as_posix(),
                    "sha256": _sha256(manifest_path),
                    "pid": process["pid"],
                    "exit_code": 0,
                }
                sequence += 1
    return gate


def test_wp07_replay_gate_requires_hash_bound_serial_process_manifests(tmp_path: Path) -> None:
    gate = _wp07_gate(tmp_path)
    run_root = wp07_binding.CONTACT_REQUAL_R2_RUN_ROOT

    wp07_binding._validate_contact_r2_process_evidence(gate, root=tmp_path, run_root=run_root)

    gate["sequential_process_order"].reverse()
    with pytest.raises(PermissionError, match="process order"):
        wp07_binding._validate_contact_r2_process_evidence(gate, root=tmp_path, run_root=run_root)


def test_wp07_contact_r2_1_binding_discloses_inherited_wp07_source_changes() -> None:
    binding = wp07_binding.load_binding(wp07_binding.CONTACT_REQUAL_R2_BINDING_PATH)

    wp07_binding.validate_binding(binding)

    assert (
        binding["source_lineage_disclosure"]["source_contains_wp07_candidate_changes_since_governing_base"]
        is True
    )


def test_wp07_contact_r2_2_replay_gate_path_is_relative_and_uses_fresh_roots() -> None:
    expected_gate = wp07_binding.CONTACT_REQUAL_R2_REPLAY_GATE_PATH.relative_to(wp07_binding.ROOT)

    assert wp07_campaign.REPLAY_GATE == expected_gate
    assert wp07_campaign.RUN_ROOT == wp07_binding.CONTACT_REQUAL_R2_RUN_ROOT
    assert wp07_campaign.AUTH_ROOT == wp07_binding.CONTACT_REQUAL_R2_AUTH_ROOT
    assert expected_gate.as_posix().endswith("replay_authorization_gate_r2_2.json")


def test_wp07_penalty_summary_telemetry_is_explicitly_post_solve() -> None:
    class RecordingMonitor:
        def __init__(self) -> None:
            self.events: list[tuple[dict[str, object], str]] = []

        def observe_nonlinear(self, event: dict[str, object], *, source: str) -> None:
            self.events.append((event, source))

    monitor = RecordingMonitor()
    summary = wp07_structural._emit_post_solve_nonlinear_summary(
        monitor,
        {
            "increments": [
                {"increment": 1, "iterations": 3, "load_factor": 0.5, "relative_residual": 1.0e-11},
                {"increment": 2, "iterations": 4, "load_factor": 1.0, "relative_residual": 2.0e-12},
            ]
        },
    )

    assert summary == {
        "mode": "POST_SOLVE_INCREMENT_SUMMARY",
        "increment_count": 2,
        "newton_iterations": 7,
    }
    assert len(monitor.events) == 4
    assert {source for _, source in monitor.events} == {"runner_post_solve_summary"}
    assert [event["event"] for event, _ in monitor.events] == [
        "ITERATION",
        "STEP_ACCEPTED",
        "ITERATION",
        "STEP_ACCEPTED",
    ]


def test_wp07_penalty_summary_reports_missing_increment_diagnostics() -> None:
    class RecordingMonitor:
        def observe_nonlinear(self, event: dict[str, object], *, source: str) -> None:
            raise AssertionError("No summary event is expected without increment diagnostics.")

    summary = wp07_structural._emit_post_solve_nonlinear_summary(RecordingMonitor(), {})

    assert summary == {
        "mode": "POST_SOLVE_SUMMARY_UNAVAILABLE",
        "increment_count": 0,
        "newton_iterations": 0,
    }
