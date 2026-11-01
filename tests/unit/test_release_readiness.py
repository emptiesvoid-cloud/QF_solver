"""Contracts for the explicit public-release readiness gate."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.release_readiness as release_readiness_module
from scripts.release_readiness import release_readiness
from scripts.git_tools import git_command


ROOT = Path(__file__).resolve().parents[2]
_RELEASE_AUDIT_SUBPROCESS_TIMEOUT = 300


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


def _synthetic_git_root(path: Path) -> Path:
    """Create a tiny Git root for CLI wiring tests without rescanning this repository."""
    path.mkdir(parents=True, exist_ok=True)
    (path / "README.md").write_text("Synthetic release-audit fixture.\n", encoding="utf-8")
    subprocess.run([git_command(), "init", "--quiet"], cwd=path, check=True)
    subprocess.run([git_command(), "config", "user.name", "QF Solver Test"], cwd=path, check=True)
    subprocess.run(
        [git_command(), "config", "user.email", "qfsolver-test@users.noreply.github.com"],
        cwd=path,
        check=True,
    )
    subprocess.run([git_command(), "add", "README.md"], cwd=path, check=True)
    subprocess.run([git_command(), "commit", "--quiet", "-m", "synthetic audit root"], cwd=path, check=True)
    return path


def _stub_repository_scanners(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep report-composition tests from rescanning the full repository."""
    monkeypatch.setattr(
        release_readiness_module,
        "audit_public_release",
        lambda _root: {"status": "FAIL", "findings": [{"identifier": "synthetic"}], "scanned_files": 1},
    )
    monkeypatch.setattr(
        release_readiness_module,
        "audit_release_archive",
        lambda _root: {"status": "FAIL", "findings": ["synthetic"], "paths": ["README.md"]},
    )


def test_release_readiness_composes_current_scanner_and_history_statuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_repository_scanners(monkeypatch)
    report = release_readiness(ROOT)
    statuses = {item["id"]: item["status"] for item in report["checks"]}

    assert report["source_audit"]["status"] == "FAIL"
    assert report["archive_audit"]["status"] == "FAIL"
    assert statuses["public_source_audit"] == report["source_audit"]["status"]
    assert statuses["release_archive_audit"] == report["archive_audit"]["status"]
    assert statuses["git_history_audit"] == (
        "PASS" if report["history_audit"]["status"] == "PASS" else "FAIL"
    )
    expected = "READY" if all(status == "PASS" for status in statuses.values()) else "NOT_READY"
    assert report["status"] == expected


def test_readiness_report_lists_only_machine_checkable_blocking_gate_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_repository_scanners(monkeypatch)
    monkeypatch.setattr(
        release_readiness_module,
        "audit_git_history_paths",
        lambda _root: {
            "status": "WARNING",
            "commit_count": 1,
            "findings": ["synthetic finding"],
            "limitation": "synthetic report",
        },
    )
    report = release_readiness(ROOT)

    assert all(isinstance(identifier, str) and identifier for identifier in report["blocking_gates"])
    assert "license_selected" not in report["blocking_gates"]
    assert ("git_history_audit" in report["blocking_gates"]) == (
        report["history_audit"]["status"] != "PASS"
    )
    assert report["manual_actions"]


def test_release_readiness_supports_direct_script_execution(tmp_path) -> None:
    output = tmp_path / "readiness.json"
    root = _synthetic_git_root(tmp_path / "repository")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "release_readiness.py"),
            "--root",
            str(root),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=_audit_subprocess_environment(),
        timeout=_RELEASE_AUDIT_SUBPROCESS_TIMEOUT,
    )

    report = _read_subprocess_report(output, completed)
    expected_returncode = 0 if report["status"] == "READY" else 4
    assert completed.returncode == expected_returncode
    assert f"RELEASE READINESS: {report['status']}" in completed.stdout


def test_release_audit_commands_create_nested_output_directories(tmp_path) -> None:
    # This tests export and exit-code fidelity, not release acceptance; the
    # separate current-tree tests still require the scanners to return PASS.
    root = _synthetic_git_root(tmp_path / "repository")
    cases = (
        ("audit_public_release.py", {"PASS": 0, "FAIL": 1}),
        ("audit_release_archive.py", {"PASS": 0, "FAIL": 1}),
        ("audit_git_history.py", {"PASS": 0, "WARNING": 1}),
        ("release_readiness.py", {"READY": 0, "NOT_READY": 4}),
    )

    for script, returncodes in cases:
        output = tmp_path / "new" / "release" / f"{script}.json"
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script), "--root", str(root), "--output", str(output)],
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
