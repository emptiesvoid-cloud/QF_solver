"""Validate an externally approved CI execution identity; does not authorize execution."""
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

    event_name = runtime.get("event")
    if event_name not in {"pull_request", "push", "workflow_dispatch"} or manifest.get("event") != event_name:
        raise ValueError("event is not covered by the approved manifest")
    for field in ("run_id", "run_attempt"):
        approved = manifest[field]
        if type(approved) is not int or approved <= 0 or runtime.get(field) != str(approved):
            raise ValueError(f"GitHub {field} mismatch")
    merge = git("rev-parse", "HEAD")
    if event["repository"]["full_name"] != manifest["repository"] or runtime.get("repository") != manifest["repository"]:
        raise ValueError("repository mismatch")
    if runtime.get("ref") != manifest.get("ref") or runtime.get("sha") != manifest.get("sha"):
        raise ValueError("ref or commit SHA mismatch")
    if merge != manifest["sha"]:
        raise ValueError("checked out commit differs from approved SHA")
    expected_parents = manifest.get("parents")
    if not isinstance(expected_parents, list) or not all(isinstance(parent, str) for parent in expected_parents):
        raise ValueError("manifest parents must be a list of commit SHAs")
    if git("show", "-s", "--format=%P", merge).split() != expected_parents:
        raise ValueError("commit parents differ from the approved manifest")

    if event_name == "pull_request":
        pr = event["pull_request"]
        head, base = pr["head"]["sha"], pr["base"]["sha"]
        pr_number = event.get("number")
        if type(pr_number) is not int or pr_number != manifest.get("pr"):
            raise ValueError("PR number mismatch")
        if pr["base"].get("ref") != "main" or pr["head"].get("repo", {}).get("full_name") != manifest["repository"]:
            raise ValueError("only same-repository PRs targeting main are permitted")
        if head != manifest.get("head") or base != manifest.get("base"):
            raise ValueError("head/base mismatch")
        if runtime.get("ref") != f"refs/pull/{pr_number}/merge":
            raise ValueError("PR merge ref mismatch")
        if expected_parents != [base, head]:
            raise ValueError("merge parents mismatch")
        if git("rev-parse", "HEAD^{tree}") != manifest.get("merge_tree"):
            raise ValueError("merge tree mismatch")
    elif event_name == "push":
        before, after = event.get("before"), event.get("after")
        if (event.get("ref") != "refs/heads/main" or runtime.get("ref") != event.get("ref")
                or manifest.get("before") != before):
            raise ValueError("push is outside the approved main update")
        if after != manifest.get("sha") or after != runtime.get("sha"):
            raise ValueError("push tip differs from approved SHA")
        if not before or before == "0" * 40:
            raise ValueError("main push has no verifiable prior commit")
        try:
            git("merge-base", "--is-ancestor", before, after)
        except subprocess.CalledProcessError as exc:
            raise ValueError("approved main base is not an ancestor of the push tip") from exc
        if git("rev-parse", "HEAD^{tree}") != manifest.get("tree"):
            raise ValueError("push tree mismatch")
    else:
        if runtime.get("ref") != "refs/heads/main" or git("rev-parse", "HEAD^{tree}") != manifest.get("tree"):
            raise ValueError("manual CI dispatch is limited to the approved main tree")

    status = git("status", "--porcelain=v1", "-z", "--untracked-files=all")
    permitted = {f"?? {path}" for path in allowed_untracked}
    if any(entry and entry not in permitted for entry in status.split("\0")):
        raise ValueError("checkout contains unexpected changes")
    workflow_hashes = manifest.get("workflow_sha256")
    if not isinstance(workflow_hashes, dict) or set(workflow_hashes) != set(WORKFLOWS):
        raise ValueError("manifest must bind the complete CI workflow set")
    for path in WORKFLOWS:
        committed = subprocess.check_output(["git", "--no-replace-objects", "show", f"{merge}:{path}"], cwd=root)
        digest = hashlib.sha256(committed).hexdigest()
        if digest != workflow_hashes[path]:
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
    print("CI identity matches manifest; environment approval and resource supervision remain separate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
