"""Keep maintained publication sources on the controlled review vocabulary."""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.git_tools import git_command
from scripts.review_vocabulary import review_vocabulary_audit


ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_PREFIXES = (
    "." + "co" + "dex/",
    ".graphifyignore",
    "A" + "GENTS.md",
    "graphify-out/",
)


def test_published_sources_use_controlled_review_vocabulary() -> None:
    completed = subprocess.run(
        [git_command(), "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    report = review_vocabulary_audit(
        ROOT, completed.stdout.splitlines(), excluded_prefixes=EXCLUDED_PREFIXES,
    )
    assert not report["integrity_errors"], report["integrity_errors"]
    assert not report["offenders"], "generic review vocabulary remains in: " + ", ".join(report["offenders"])
