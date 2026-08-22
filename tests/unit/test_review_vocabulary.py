"""Keep maintained publication sources on the controlled review vocabulary."""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.git_tools import git_command


ROOT = Path(__file__).resolve().parents[2]
TEXT_SUFFIXES = {".cff", ".css", ".html", ".json", ".js", ".md", ".py", ".rst", ".tex", ".toml", ".txt", ".yaml", ".yml"}
EXCLUDED_PREFIXES = (
    "." + "co" + "dex/",
    ".graphifyignore",
    "A" + "GENTS.md",
    "qualification/evidence/",
    "site/",
    "docs/generated/",
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
    forbidden_terms = ("h" + "uman", "h" + "umain")
    offenders: list[str] = []
    for relative_text in completed.stdout.splitlines():
        relative = Path(relative_text)
        if relative.suffix.lower() not in TEXT_SUFFIXES:
            continue
        portable_path = relative.as_posix()
        if portable_path.startswith(EXCLUDED_PREFIXES):
            continue
        path = ROOT / relative
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore").casefold()
        if any(term in content for term in forbidden_terms):
            offenders.append(portable_path)
    assert not offenders, "generic review vocabulary remains in: " + ", ".join(offenders)
