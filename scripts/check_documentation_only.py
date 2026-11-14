"""Fail closed unless a PR changes only the two pilot documentation files.

The Git objects are inspected as data. No files from the candidate commit are
imported, checked out or executed. This diagnostic is not a merge approval.
"""
from __future__ import annotations

import re
import subprocess
import sys

ALLOWED = frozenset({"README.md", "CITATION_REPORTS.bib"})
MAX_FILE_BYTES = 2_000_000
SHA = re.compile(r"[0-9a-f]{40}")


def run_git(*args: str) -> bytes:
    return subprocess.run(
        ["git", "--no-replace-objects", *args], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout


def validate(base: str, head: str) -> list[str]:
    if not SHA.fullmatch(base) or not SHA.fullmatch(head):
        raise ValueError("base and head must be full lowercase commit SHAs")
    run_git("merge-base", "--is-ancestor", base, head)
    raw = run_git("diff", "--name-status", "-z", "--no-renames", "--no-ext-diff", base, head, "--")
    parts = raw.split(b"\0")
    if parts[-1] != b"":
        raise ValueError("invalid diff output")
    parts.pop()
    if not parts or len(parts) % 2:
        raise ValueError("empty or malformed diff")
    changed: list[str] = []
    for i in range(0, len(parts), 2):
        status = parts[i].decode("ascii")
        path = parts[i + 1].decode("utf-8", "strict")
        if status not in {"A", "M"} or path not in ALLOWED or path in changed:
            raise ValueError(f"change outside documentation pilot: {status} {path!r}")
        entry = run_git("ls-tree", "-z", head, "--", path)
        header, found_path = entry.rstrip(b"\0").split(b"\t", 1)
        mode, kind, _ = header.split(b" ", 2)
        if mode != b"100644" or kind != b"blob" or found_path.decode("utf-8") != path:
            raise ValueError(f"not a regular file: {path}")
        size = int(run_git("cat-file", "-s", f"{head}:{path}"))
        if size > MAX_FILE_BYTES:
            raise ValueError(f"file too large: {path}")
        data = run_git("show", f"{head}:{path}")
        if b"\0" in data:
            raise ValueError(f"binary content: {path}")
        data.decode("utf-8", "strict")
        changed.append(path)
    run_git("diff", "--check", "--no-ext-diff", base, head, "--")
    return changed


def main() -> int:
    try:
        if len(sys.argv) != 3:
            raise ValueError("usage: check_documentation_only.py BASE_SHA HEAD_SHA")
        changed = validate(sys.argv[1], sys.argv[2])
    except (ValueError, UnicodeError, subprocess.CalledProcessError) as exc:
        print(f"Documentation diagnostic refused: {exc}", file=sys.stderr)
        return 1
    print("Documentation diagnostic: " + ", ".join(changed))
    print("Informational only. Existing required checks and Owner gates still apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
