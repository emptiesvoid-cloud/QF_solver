"""Explicit remote synchronization and candidate identity checks for WP12.

VALIDATE never calls these functions. SYNC is a separate, visible operation
which updates only the configured remote-tracking ref and never force-fetches.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any

from .contracts import ContractError, REPOSITORY, TARGET_BRANCH


_ALLOWED_ORIGINS = {
    f"https://github.com/{REPOSITORY}.git",
    f"https://github.com/{REPOSITORY}",
    f"git@github.com:{REPOSITORY}.git",
}


@dataclass(frozen=True)
class RemoteIdentity:
    origin_url: str
    remote_ref: str
    remote_commit: str
    remote_tree: str
    local_commit: str
    local_tree: str
    local_is_ancestor: bool
    synchronized_utc: str


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
        shell=False,
    )
    if result.returncode:
        raise ContractError(f"git {' '.join(arguments)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _assert_expected_origin(root: Path) -> str:
    origin = _git(root, "remote", "get-url", "origin")
    if origin not in _ALLOWED_ORIGINS:
        raise ContractError("origin URL does not identify the expected GitHub repository")
    return origin


def sync_remote_identity(root: Path) -> RemoteIdentity:
    """Explicitly fetch the exact target branch without force or tag updates."""
    canonical = root.resolve(strict=True)
    top = Path(_git(canonical, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if top != canonical:
        raise ContractError("SYNC root must be the canonical Git repository root")
    origin = _assert_expected_origin(canonical)
    local_commit = _git(canonical, "rev-parse", "HEAD")
    local_tree = _git(canonical, "rev-parse", "HEAD^{tree}")
    remote_ref = f"refs/remotes/origin/{TARGET_BRANCH}"
    source_ref = f"refs/heads/{TARGET_BRANCH}"
    # No '+' refspec: a non-fast-forward remote-tracking update fails closed.
    _git(canonical, "fetch", "--no-tags", "--no-recurse-submodules", "origin", f"{source_ref}:{remote_ref}")
    remote_commit = _git(canonical, "rev-parse", remote_ref)
    remote_tree = _git(canonical, "rev-parse", f"{remote_ref}^{{tree}}")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", local_commit, remote_commit],
        cwd=canonical,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        shell=False,
    )
    if ancestor.returncode not in (0, 1):
        raise ContractError(f"git merge-base failed: {ancestor.stderr.strip()}")
    if ancestor.returncode == 1:
        raise ContractError("local HEAD is not an ancestor of the synchronized remote branch")
    return RemoteIdentity(
        origin_url=origin,
        remote_ref=remote_ref,
        remote_commit=remote_commit,
        remote_tree=remote_tree,
        local_commit=local_commit,
        local_tree=local_tree,
        local_is_ancestor=True,
        synchronized_utc=datetime.now(timezone.utc).isoformat(),
    )


def write_sync_receipt(repository_root: Path, identity: RemoteIdentity, receipt_directory: Path) -> Path:
    """Write a create-new local receipt; it is not a cryptographic Owner approval."""
    root = repository_root.resolve(strict=True)
    expected = root / ".codex" / "wp12_runner_audit"
    destination = receipt_directory.resolve(strict=False)
    if destination != expected:
        raise ContractError("remote sync receipt destination must be .codex/wp12_runner_audit")
    try:
        destination.relative_to(root)
    except ValueError as exc:
        raise ContractError("remote sync receipt must remain inside the repository audit area") from exc
    if destination.is_symlink() or bool(getattr(destination, "is_junction", lambda: False)()):
        raise ContractError("remote sync receipt directory must not be a symlink or junction")
    destination.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"schema": "qf-wp12-remote-sync-receipt-v1", **identity.__dict__}
    name = f"remote-sync-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}.json"
    path = destination / name
    with path.open("xb") as stream:
        stream.write((json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        stream.flush()
        import os

        os.fsync(stream.fileno())
    return path
