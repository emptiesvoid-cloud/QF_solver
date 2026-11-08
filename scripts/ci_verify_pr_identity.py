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


def check(root: Path, event: dict, manifest: dict, runtime: dict) -> None:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=root, text=True).strip()

    if runtime.get("event") != "pull_request":
        raise ValueError("only pull_request is permitted")
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
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("checkout is not clean")
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


def main() -> int:
    try:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        manifest = authenticate_manifest(
            Path(os.environ["QF_APPROVED_IDENTITY_MANIFEST"]).read_bytes(),
            os.environ["QF_MANIFEST_AUTH_SECRET"], os.environ["QF_MANIFEST_SIGNATURE"],
        )
        runtime = {"event": os.environ.get("GITHUB_EVENT_NAME"), "repository": os.environ.get("GITHUB_REPOSITORY"),
                   "ref": os.environ.get("GITHUB_REF"), "sha": os.environ.get("GITHUB_SHA")}
        check(Path.cwd(), event, manifest, runtime)
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"CI identity rejected: {exc}", file=sys.stderr)
        return 1
    print("CI identity matches manifest; authorization and resource supervision remain separate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
