"""Fail-closed policy for selected distributions versus whole-repository archives."""

from __future__ import annotations

from typing import Literal


def publication_scope_decision(
    scope: str,
    g03_status: str,
    whole_repository_archive_cleared: bool,
) -> Literal["ALLOWED", "DENIED"]:
    """Decide one explicitly named scope without conflating its clearance gates."""
    if scope == "SELECTED_DISTRIBUTION":
        if g03_status == "FAIL_PRESERVED" and whole_repository_archive_cleared is False:
            return "ALLOWED"
        if g03_status == "PASS" and whole_repository_archive_cleared is True:
            return "ALLOWED"
        return "DENIED"
    if scope == "WHOLE_REPOSITORY_ARCHIVE":
        if g03_status == "PASS" and whole_repository_archive_cleared is True:
            return "ALLOWED"
        return "DENIED"
    return "DENIED"
