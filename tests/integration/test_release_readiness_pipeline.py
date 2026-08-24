import subprocess
from pathlib import Path

from scripts.release_readiness import release_readiness


def test_release_readiness_remains_dry_run_and_reports_worktree_state() -> None:
    root = Path(__file__).resolve().parents[2]
    report = release_readiness(root)

    assert report["status"] == "NOT_READY"
    git_status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    expected_status = "FAIL" if git_status.stdout.strip() else "PASS"
    assert any(
        item["id"] == "git_clean_worktree" and item["status"] == expected_status
        for item in report["checks"]
    )
    assert any("tag" in action.lower() for action in report["manual_actions"])
