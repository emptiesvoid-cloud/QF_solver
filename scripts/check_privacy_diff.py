"""Reject new employer-name and personal-profile references in staged changes."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys


def privacy_findings(diff_text: str) -> list[str]:
    """Return forbidden added diff lines, ignoring generic test fixture names."""
    employer_names = ("saf" + "ran", "snec" + "ma")
    profile_path = re.compile(
        r"(?i)[A-Z]:\\Users\\(?!private(?:\\|$)|example(?:\\|$)|"
        r"username(?:\\|$)|user(?:\\|$))[^\\/\s\"'<>]+"
    )
    posix_profile = re.compile(r"(?i)/(?:home|root)/(?!runner(?:/|$))[^/\s\"'<>]+")
    findings = []
    for line in diff_text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        added = line[1:]
        lower = added.casefold()
        if any(name in lower for name in employer_names) or profile_path.search(added) or posix_profile.search(added):
            findings.append(added.strip()[:240])
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cached", action="store_true", help="inspect staged changes (pre-commit mode)")
    parser.add_argument("--base", help="inspect changes from this base commit (CI mode)")
    args = parser.parse_args()
    if args.cached and args.base:
        parser.error("choose either --cached or --base")
    command = ["git", "diff", "--no-ext-diff", "--no-color", "--unified=0"]
    if args.cached:
        command.append("--cached")
    elif args.base:
        command.append(f"{args.base}...HEAD")
    else:
        parser.error("use --cached or --base")
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode:
        print(completed.stderr, file=sys.stderr, end="")
        return completed.returncode
    findings = privacy_findings(completed.stdout)
    if findings:
        print("Privacy check rejected newly added employer or personal-profile references:", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        return 1
    print("Privacy diff check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
