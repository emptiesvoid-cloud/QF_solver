"""Unit checks for the fail-closed standard CI identity verifier."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from scripts.ci_verify_pr_identity import check


REPOSITORY = "emptiesvoid-cloud/QF_solver"
WORKFLOWS = (".github/workflows/quality.yml", ".github/workflows/docs-tests.yml")


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def _commit(root: Path, message: str) -> str:
    _git(root, "add", ".")
    _git(root, "-c", "user.name=CI test", "-c", "user.email=ci@example.invalid", "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _workflow_hashes(root: Path, sha: str) -> dict[str, str]:
    return {
        path: hashlib.sha256(subprocess.check_output(["git", "show", f"{sha}:{path}"], cwd=root)).hexdigest()
        for path in WORKFLOWS
    }


def _repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "CI test")
    _git(root, "config", "user.email", "ci@example.invalid")
    for workflow in WORKFLOWS:
        path = root / workflow
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"name: {Path(workflow).stem}\n", encoding="utf-8")
    (root / "source.txt").write_text("base\n", encoding="utf-8")
    return root, _commit(root, "base")


def _runtime(event: str, ref: str, sha: str) -> dict[str, str]:
    return {
        "event": event,
        "repository": REPOSITORY,
        "ref": ref,
        "sha": sha,
        "run_id": "500",
        "run_attempt": "2",
    }


def test_check_accepts_approved_same_repository_pull_request(tmp_path: Path) -> None:
    root, base = _repo(tmp_path)
    _git(root, "checkout", "-b", "feature")
    (root / "source.txt").write_text("head\n", encoding="utf-8")
    head = _commit(root, "feature")
    _git(root, "checkout", "main")
    _git(root, "merge", "--no-ff", "--no-edit", "feature")
    merge = _git(root, "rev-parse", "HEAD")
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    event = {
        "repository": {"full_name": REPOSITORY},
        "number": 42,
        "pull_request": {
            "head": {"sha": head, "ref": "feature", "repo": {"full_name": REPOSITORY}},
            "base": {"sha": base, "ref": "main"},
        },
    }
    manifest = {
        "event": "pull_request", "repository": REPOSITORY, "pr": 42,
        "ref": "refs/pull/42/merge", "sha": merge, "head": head, "base": base,
        "merge_tree": tree, "parents": [base, head], "run_id": 500, "run_attempt": 2,
        "workflow_sha256": _workflow_hashes(root, merge),
    }
    check(root, event, manifest, _runtime("pull_request", "refs/pull/42/merge", merge))


def test_check_accepts_approved_main_push(tmp_path: Path) -> None:
    root, before = _repo(tmp_path)
    (root / "source.txt").write_text("updated\n", encoding="utf-8")
    after = _commit(root, "main update")
    event = {"repository": {"full_name": REPOSITORY}, "ref": "refs/heads/main", "before": before, "after": after}
    manifest = {
        "event": "push", "repository": REPOSITORY, "ref": "refs/heads/main",
        "sha": after, "before": before, "tree": _git(root, "rev-parse", "HEAD^{tree}"),
        "parents": [before], "run_id": 500, "run_attempt": 2,
        "workflow_sha256": _workflow_hashes(root, after),
    }
    check(root, event, manifest, _runtime("push", "refs/heads/main", after))


def test_check_rejects_push_outside_main(tmp_path: Path) -> None:
    root, before = _repo(tmp_path)
    (root / "source.txt").write_text("updated\n", encoding="utf-8")
    after = _commit(root, "branch update")
    event = {"repository": {"full_name": REPOSITORY}, "ref": "refs/heads/feature", "before": before, "after": after}
    manifest = {
        "event": "push", "repository": REPOSITORY, "ref": "refs/heads/feature",
        "sha": after, "before": before, "tree": _git(root, "rev-parse", "HEAD^{tree}"),
        "parents": [before], "run_id": 500, "run_attempt": 2,
        "workflow_sha256": _workflow_hashes(root, after),
    }
    with pytest.raises(ValueError, match="outside the approved main update"):
        check(root, event, manifest, _runtime("push", "refs/heads/feature", after))
