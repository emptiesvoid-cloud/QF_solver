"""Contracts for the explicit public-release readiness gate."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from scripts.release_readiness import release_readiness
from scripts.git_tools import git_command


ROOT = Path(__file__).resolve().parents[2]
_RELEASE_AUDIT_SUBPROCESS_TIMEOUT = 180


def _read_subprocess_report(output: Path, completed: subprocess.CompletedProcess[str]) -> dict[str, object]:
    """Fail with child diagnostics when a release audit cannot write its report."""
    assert output.is_file(), (
        f"release audit did not write {output}; returncode={completed.returncode}; "
        f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
    )
    return json.loads(output.read_text(encoding="utf-8"))


def _audit_subprocess_environment() -> dict[str, str]:
    """Pass the already-resolved Git executable into nested audit processes."""
    environment = os.environ.copy()
    environment["QF_SOLVER_GIT"] = git_command()
    return environment


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
        env=_audit_subprocess_environment(),
        # The direct readiness audit scans the complete public tree and is
        # noticeably slower on Windows runners, especially on Python 3.13.
        # The audit scans the full public tree and Git archive.  On a loaded
        # Windows CI worker the subprocess can exceed 90 seconds without
        # being hung; keep a finite, documented guard with room for that
        # bounded workload.
        timeout=_RELEASE_AUDIT_SUBPROCESS_TIMEOUT,
    )

    report = _read_subprocess_report(output, completed)
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
            env=_audit_subprocess_environment(),
            timeout=_RELEASE_AUDIT_SUBPROCESS_TIMEOUT,
        )

        status = _read_subprocess_report(output, completed)["status"]
        assert status in returncodes
        assert completed.returncode == returncodes[status], completed.stderr
