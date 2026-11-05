import subprocess
from pathlib import Path

from scripts.git_tools import git_command
import scripts.release_readiness as release_readiness_module
from scripts.release_readiness import release_readiness


def test_release_readiness_remains_dry_run_and_reports_worktree_state(monkeypatch) -> None:
    root = Path(__file__).resolve().parents[2]
    monkeypatch.setattr(
        release_readiness_module,
        "audit_public_release",
        lambda _root: {"status": "PASS", "findings": [], "scanned_files": 1},
    )
    monkeypatch.setattr(
        release_readiness_module,
        "audit_release_archive",
        lambda _root: {"status": "PASS", "findings": [], "paths": ["README.md"]},
    )
    monkeypatch.setattr(
        release_readiness_module,
        "audit_git_history_paths",
        lambda _root: {
            "status": "PASS",
            "commit_count": 1,
            "findings": [],
            "limitation": "synthetic report",
        },
    )
    report = release_readiness(root)

    git_status = subprocess.run(
        [git_command(), "status", "--porcelain"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    expected_status = "FAIL" if git_status.stdout.strip() else "PASS"
    expected_readiness = (
        "READY"
        if all(item["status"] == "PASS" for item in report["checks"])
        else "NOT_READY"
    )
    assert report["status"] == expected_readiness
    assert any(
        item["id"] == "git_clean_worktree" and item["status"] == expected_status
        for item in report["checks"]
    )
    assert any("tag" in action.lower() for action in report["manual_actions"])
