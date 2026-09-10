"""Regression guards for Git-backed verification under campaign environments."""

from pathlib import Path

from scripts.git_tools import git_blob, git_command, git_object_exists


ROOT = Path(__file__).resolve().parents[2]


def test_git_history_helper_survives_path_and_cwd_changes(monkeypatch, tmp_path: Path) -> None:
    """The engineering campaign must not make Git lookup depend on PATH."""
    executable = Path(git_command())
    assert executable.is_file()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", "")

    blob, content = git_blob("HEAD", "pyproject.toml", cwd=ROOT)

    assert blob
    assert b"[project]" in content
    assert git_object_exists("HEAD:pyproject.toml", cwd=ROOT)
