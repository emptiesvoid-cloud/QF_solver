from pathlib import Path

from scripts.release_readiness import release_readiness


def test_release_readiness_remains_dry_run_and_reports_uncommitted_worktree() -> None:
    report = release_readiness(Path(__file__).resolve().parents[2])

    assert report["status"] == "NOT_READY"
    assert any(item["id"] == "git_clean_worktree" and item["status"] == "FAIL" for item in report["checks"])
    assert any("tag" in action.lower() for action in report["manual_actions"])
