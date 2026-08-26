import subprocess
from pathlib import Path

from scripts.git_tools import git_command
from scripts.release_readiness import release_readiness


def test_release_readiness_remains_dry_run_and_reports_worktree_state() -> None:
    root = Path(__file__).resolve().parents[2]
    report = release_readiness(root)

    git_status = subprocess.run(
        [git_command(), "status", "--porcelain"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    expected_status = "FAIL" if git_status.stdout.strip() else "PASS"
    expected_readiness = "NOT_READY" if expected_status == "FAIL" else "READY"
    assert report["status"] == expected_readiness
    assert any(
        item["id"] == "git_clean_worktree" and item["status"] == expected_status
        for item in report["checks"]
    )
    assert any("tag" in action.lower() for action in report["manual_actions"])
