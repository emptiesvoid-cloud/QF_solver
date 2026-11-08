"""Validate an externally approved PR execution identity; does not authorize execution."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
import sys
from pathlib import Path

WORKFLOWS = (".github/workflows/quality.yml", ".github/workflows/docs-tests.yml")


def check(
    root: Path, event: dict, manifest: dict, runtime: dict, *, allowed_untracked: tuple[str, ...] = (),
) -> None:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", "--no-replace-objects", *args], cwd=root, text=True).strip()

    if runtime.get("event") != "pull_request":
        raise ValueError("only pull_request is permitted")
    for field in ("run_id", "run_attempt"):
        approved = manifest[field]
        if type(approved) is not int or approved <= 0 or runtime.get(field) != str(approved):
            raise ValueError(f"GitHub {field} mismatch")
    pr = event["pull_request"]
    head, base = pr["head"]["sha"], pr["base"]["sha"]
    merge = git("rev-parse", "HEAD")
    if event["repository"]["full_name"] != manifest["repository"] or runtime.get("repository") != manifest["repository"]:
        raise ValueError("repository mismatch")
    if event["number"] != manifest["pr"] or runtime.get("ref") != f"refs/pull/{manifest['pr']}/merge":
        raise ValueError("PR identity mismatch")
    if head != manifest["head"] or base != manifest["base"]:
        raise ValueError("head/base mismatch")
    if runtime.get("sha") != merge:
        raise ValueError("checked out commit differs from GitHub context")
    if git("show", "-s", "--format=%P", merge).split() != [base, head]:
        raise ValueError("merge parents mismatch")
    if git("rev-parse", "HEAD^{tree}") != manifest["merge_tree"]:
        raise ValueError("merge tree mismatch")
    status = git("status", "--porcelain=v1", "-z", "--untracked-files=all")
    permitted = {f"?? {path}" for path in allowed_untracked}
    if any(entry and entry not in permitted for entry in status.split("\0")):
        raise ValueError("checkout contains unexpected changes")
    for path in WORKFLOWS:
        digest = hashlib.sha256((root / path).read_bytes()).hexdigest()
        if digest != manifest["workflow_sha256"][path]:
            raise ValueError(f"workflow mismatch: {path}")


def authenticate_manifest(raw: bytes, secret: str, signature: str) -> dict:
    """Authenticate exact manifest bytes using a separately provisioned secret."""
    if len(secret) < 32:
        raise ValueError("manifest authentication secret is missing or too short")
    expected = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("manifest authentication failed")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("manifest must be a JSON object")
    return result


def load_approved_manifest(root: Path, *, allowed_untracked: tuple[str, ...] = ()) -> dict:
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    inline = os.environ.get("QF_APPROVED_IDENTITY_MANIFEST_JSON")
    path = os.environ.get("QF_APPROVED_IDENTITY_MANIFEST")
    if bool(inline) == bool(path):
        raise ValueError("supply exactly one approved manifest source")
    raw = inline.encode("utf-8") if inline else Path(path).read_bytes()
    manifest = authenticate_manifest(raw, os.environ["QF_MANIFEST_AUTH_SECRET"], os.environ["QF_MANIFEST_SIGNATURE"])
    runtime = {"event": os.environ.get("GITHUB_EVENT_NAME"), "repository": os.environ.get("GITHUB_REPOSITORY"),
               "ref": os.environ.get("GITHUB_REF"), "sha": os.environ.get("GITHUB_SHA"),
               "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT")}
    check(root, event, manifest, runtime, allowed_untracked=allowed_untracked)
    return manifest


def main() -> int:
    try:
        load_approved_manifest(Path.cwd())
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"CI identity rejected: {exc}", file=sys.stderr)
        return 1
    print("CI identity matches manifest; authorization and resource supervision remain separate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
