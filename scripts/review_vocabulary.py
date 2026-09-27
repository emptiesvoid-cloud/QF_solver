"""Audit review terms in current sources and migrated historical records."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence


TEXT_SUFFIXES = {
    ".cff", ".css", ".html", ".json", ".js", ".md", ".py", ".rst",
    ".tex", ".toml", ".txt", ".yaml", ".yml",
}
FORBIDDEN_TERMS = ("h" + "uman", "h" + "umain")


def review_vocabulary_audit(
    root: Path, paths: Sequence[str], *, excluded_prefixes: Sequence[str] = (),
) -> dict[str, Any]:
    """Fail on prohibited terms, missing listed inputs, or invalid UTF-8.

    Historical records have no vocabulary exemption. Their terminology-only
    migration is verified separately, against the original Git objects.
    """
    offenders: list[str] = []
    integrity_errors: list[str] = []
    for relative in sorted(set(paths)):
        path = root / relative
        if path.suffix.lower() not in TEXT_SUFFIXES or relative.startswith(tuple(excluded_prefixes)):
            continue
        if not path.is_file():
            integrity_errors.append(relative)
            continue
        try:
            content = path.read_text(encoding="utf-8").casefold()
        except (OSError, UnicodeError):
            integrity_errors.append(relative)
            continue
        if any(term in content for term in FORBIDDEN_TERMS):
            offenders.append(relative)
    return {
        "status": "FAIL" if offenders or integrity_errors else "PASS",
        "offenders": offenders,
        "integrity_errors": integrity_errors,
    }
