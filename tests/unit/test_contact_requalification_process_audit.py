"""No-solve tests for sequential WP07/WP08 contact requalification evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from scripts import run_wp08d_contact_requalification as wp08_campaign
from scripts import wp07d_execution_binding as wp07_binding


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


def _wp07_gate(root: Path) -> dict[str, Any]:
    run_root = Path("qualification/0_2_9/wp07d_contact_requalification_r2/runs")
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
    run_root = Path("qualification/0_2_9/wp07d_contact_requalification_r2/runs")

    wp07_binding._validate_contact_r2_process_evidence(gate, root=tmp_path, run_root=run_root)

    gate["sequential_process_order"].reverse()
    with pytest.raises(PermissionError, match="process order"):
        wp07_binding._validate_contact_r2_process_evidence(gate, root=tmp_path, run_root=run_root)
