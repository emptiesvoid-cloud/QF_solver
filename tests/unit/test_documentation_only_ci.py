from pathlib import Path
import subprocess

import pytest

from scripts.check_documentation_only import validate


def test_classifier_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    def git(*args: str, data: bytes | None = None) -> str:
        result = subprocess.run(["git", *args], input=data, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, check=True)
        return result.stdout.decode().strip()

    git("init", "-q")
    git("config", "user.name", "CI diagnostic test")
    git("config", "user.email", "ci-test@example.invalid")
    (tmp_path / "README.md").write_text("# Baseline\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    (tmp_path / "README.md").write_text("# Baseline\n\nReport.\n", encoding="utf-8")
    (tmp_path / "CITATION_REPORTS.bib").write_text("@techreport{x, title={Report}}\n", encoding="utf-8")
    git("add", "README.md", "CITATION_REPORTS.bib")
    git("commit", "-qm", "documentation")
    docs = git("rev-parse", "HEAD")
    assert set(validate(base, docs)) == {"README.md", "CITATION_REPORTS.bib"}

    (tmp_path / "solver.py").write_text("pass\n", encoding="utf-8")
    git("add", "solver.py")
    git("commit", "-qm", "non documentation")
    with pytest.raises(ValueError, match="outside documentation pilot"):
        validate(base, git("rev-parse", "HEAD"))
    with pytest.raises(ValueError, match="empty or malformed"):
        validate(base, base)
    with pytest.raises(ValueError, match="full lowercase"):
        validate("--help", docs)

    git("reset", "--hard", docs)
    blob = git("hash-object", "-w", "--stdin", data=b"target")
    git("update-index", "--add", "--cacheinfo", f"120000,{blob},README.md")
    git("commit", "-qm", "symlink")
    with pytest.raises(ValueError, match="outside documentation pilot|not a regular file"):
        validate(base, git("rev-parse", "HEAD"))
