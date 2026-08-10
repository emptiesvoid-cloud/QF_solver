"""Contracts for the explicit public-release readiness gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.release_readiness import release_readiness


ROOT = Path(__file__).resolve().parents[2]


def test_current_open_source_tree_reports_its_actual_release_state() -> None:
    report = release_readiness(ROOT)
    statuses = {item["id"]: item["status"] for item in report["checks"]}

    assert report["source_audit"]["status"] == "PASS"
    assert report["archive_audit"]["status"] == "PASS"
    assert statuses["license_selected"] == "PASS"
    expected = "READY" if all(status == "PASS" for status in statuses.values()) else "NOT_READY"
    assert report["status"] == expected


def test_readiness_report_lists_only_machine_checkable_blocking_gate_ids() -> None:
    report = release_readiness(ROOT)

    assert all(isinstance(identifier, str) and identifier for identifier in report["blocking_gates"])
    assert "license_selected" not in report["blocking_gates"]
    assert ("git_history_audit" in report["blocking_gates"]) == (
        report["history_audit"]["status"] != "PASS"
    )
    assert report["manual_actions"]


def test_release_readiness_supports_direct_script_execution(tmp_path) -> None:
    output = tmp_path / "readiness.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "release_readiness.py"),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    expected_returncode = 0 if report["status"] == "READY" else 4
    assert completed.returncode == expected_returncode
    assert f"RELEASE READINESS: {report['status']}" in completed.stdout


def test_release_audit_commands_create_nested_output_directories(tmp_path) -> None:
    cases = (
        ("audit_public_release.py", {"PASS": 0}),
        ("audit_release_archive.py", {"PASS": 0}),
        ("audit_git_history.py", {"PASS": 0, "WARNING": 1}),
        ("release_readiness.py", {"READY": 0, "NOT_READY": 4}),
    )

    for script, returncodes in cases:
        output = tmp_path / "new" / "release" / f"{script}.json"
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script), "--output", str(output)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        status = json.loads(output.read_text(encoding="utf-8"))["status"]
        assert status in returncodes
        assert completed.returncode == returncodes[status], completed.stderr
