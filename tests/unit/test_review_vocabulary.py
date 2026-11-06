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
    "docs/development/",
    "docs/verification/0_2_9/",
    "docs/elements/rbe2_rbe3_audit_vv.md",
    "docs/verification/wp12_b_elements_loads_audit.md",
)


def test_published_sources_use_controlled_review_vocabulary() -> None:
    completed = subprocess.run(
        [git_command(), "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    public_sources = [
        path for path in completed.stdout.splitlines()
        if path == "README.md" or path.startswith("docs/")
    ]
    report = review_vocabulary_audit(ROOT, public_sources, excluded_prefixes=EXCLUDED_PREFIXES)
    assert not report["integrity_errors"], report["integrity_errors"]
    assert not report["offenders"], "generic review vocabulary remains in: " + ", ".join(report["offenders"])
