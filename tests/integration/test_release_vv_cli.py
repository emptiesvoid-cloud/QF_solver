from __future__ import annotations

import pytest
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_release_vv_cli_writes_owner_and_machine_reports(tmp_path: Path) -> None:
    output = tmp_path / "release_vv"
    completed = subprocess.run(
        [sys.executable, "qf_solver.py", "release-vv", "--output", str(output)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 4, completed.stdout + completed.stderr
    assert "RELEASE V&V STATUS: FAIL" in completed.stdout
    summary = json.loads((output / "release_vv_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "release_vv_manifest.json").read_text(encoding="utf-8"))
    assert summary["release"]["version"] == "0.2.1a0"
    assert summary["manifest"] == "release_vv_manifest.json"
    evidence = next(
        check for check in summary["checks"] if check["id"] == "EVIDENCE-BUNDLE-CODE-ASTER-CORRELATION-2026-08-14"
    )
    assert evidence["status"] == "PASS"
    assert {entry["role"] for entry in manifest["files"]} == {"summary", "report"}


def test_release_vv_cli_can_fail_on_warning(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "qf_solver.py",
            "release-vv",
            "--output",
            str(tmp_path / "release_vv"),
            "--fail-on-warning",
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 4
    assert "RELEASE V&V STATUS: FAIL" in completed.stdout

pytestmark = pytest.mark.evidence
