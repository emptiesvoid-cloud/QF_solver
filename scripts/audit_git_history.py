"""Audit reachable Git-history paths before preparing a public repository."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Sequence, TypedDict

try:
    from scripts.git_tools import git_command
except ModuleNotFoundError:
    from git_tools import git_command  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
_PRIVATE_TOOL_DIRECTORY = "." + "co" + "dex"
_WINDOWS_PROFILE_DIRECTORY = "app" + "data"
_INTERNAL_INSTRUCTIONS = "a" + "gents.md"
_SENSITIVE_PARTS = (
    "results/",
    "results_large/",
    "site/",
    "qualification/vnv/",
    "vnv-",
    _PRIVATE_TOOL_DIRECTORY,
    _WINDOWS_PROFILE_DIRECTORY,
    _INTERNAL_INSTRUCTIONS,
    "qf_solver_manual.tex",
    "qf_solver_manual_candidate_",
    ".env",
)
_REVIEWED_PUBLIC_HISTORY_PATHS = (
    "qualification/vnv/mitc4_stable_package_2026-08-21/study.json",
    "qualification/vnv/external/rqg08_j2_common_024/reference/summary.json",
)


class GitHistoryFinding(TypedDict):
    """A reachable path that must be examined before a public release."""

    revision: str
    path: str
    kind: str


class GitHistoryReport(TypedDict):
    """Portable result of the reachable-history path prefilter."""

    status: str
    commit_count: int
    findings: list[GitHistoryFinding | str]
    limitation: str


def audit_git_history_paths(root: str | Path = ROOT) -> GitHistoryReport:
    """List reachable-history filenames that require public-history review."""
    base = Path(root).resolve()
    try:
        completed = subprocess.run(
            [git_command(), "log", "--all", "--format=%H", "--name-only"], cwd=base, text=True, capture_output=True, check=False, timeout=30
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "FAIL",
            "findings": [f"git history unavailable: {exc}"],
            "commit_count": 0,
            "limitation": "History could not be inspected.",
        }
    if completed.returncode != 0:
        return {
            "status": "FAIL",
            "findings": [completed.stderr.strip() or "git log failed"],
            "commit_count": 0,
            "limitation": "History could not be inspected.",
        }
    revision = ""
    findings: list[GitHistoryFinding | str] = []
    commits: set[str] = set()
    for line in completed.stdout.splitlines():
        value = line.strip()
        if not value:
            continue
        if len(value) == 40 and all(character in "0123456789abcdef" for character in value):
            revision = value
            commits.add(value)
            continue
        if _is_sensitive_path(value):
            findings.append({"revision": revision, "path": value, "kind": "sensitive_history_path"})
    findings.extend(_author_email_findings(base))
    return {
        "status": "PASS" if not findings else "WARNING",
        "commit_count": len(commits),
        "findings": findings,
        "limitation": "Path-index prefilter only; manually review reachable file contents before publication.",
    }


def _is_sensitive_path(path: str) -> bool:
    """Flag private artifacts while allowing reviewed documentation snapshots."""
    normalized = path.replace("\\", "/").lower()
    if normalized in _REVIEWED_PUBLIC_HISTORY_PATHS:
        return False
    if normalized.startswith(("docs/generated/", "docs/assets/generated/")):
        return False
    return any(part in normalized for part in _SENSITIVE_PARTS)


def _author_email_findings(root: Path) -> list[GitHistoryFinding]:
    """Report reachable commit emails other than GitHub's public no-reply form."""
    try:
        completed = subprocess.run(
            [git_command(), "log", "--all", "--format=%H%x00%ae"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    findings: list[GitHistoryFinding] = []
    seen: set[tuple[str, str]] = set()
    for line in completed.stdout.splitlines():
        if "\x00" not in line:
            continue
        revision, email = line.split("\x00", 1)
        normalized = email.strip().lower()
        if normalized and not normalized.endswith("@users.noreply.github.com"):
            key = (revision, normalized)
            if key not in seen:
                seen.add(key)
                findings.append(
                    {
                        "revision": revision,
                        "path": "<commit-author-email>",
                        "kind": "private_history_identity",
                    }
                )
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("git_history_audit.json"))
    args = parser.parse_args(argv)
    report = audit_git_history_paths(ROOT)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"GIT HISTORY AUDIT: {report['status']} ({report['commit_count']} commits, {len(report['findings'])} findings)")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
