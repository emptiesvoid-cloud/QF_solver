"""Scope checks for the bounded WP14 public package/document scanner."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.audit_wp14_public_scope import (
    SCANNABLE_SUFFIXES,
    changed_bound_paths,
    select_document_paths,
    validate_documentation_publication_policy,
)


def test_document_scope_selects_only_frozen_docs_prefix_and_scannable_suffixes() -> None:
    tree = {
        "docs/index.md": ("100644", "a"),
        "docs/generated/report.json": ("100644", "b"),
        "docs/verification/0_2_9/owner-decisions.md": ("100644", "private"),
        "docs/assets/plot.png": ("100644", "c"),
        "scripts/private.md": ("100644", "d"),
    }
    report = select_document_paths(
        tree,
        {
            "include_prefixes": ["docs/"],
            "exclude_prefixes": ["docs/verification/0_2_9/"],
            "suffixes": [".md", ".json"],
        },
    )
    assert report == ["docs/generated/report.json", "docs/index.md"]


@pytest.mark.parametrize(
    "selection",
    [
        {"include_prefixes": ["scripts/"], "suffixes": [".md"]},
        {"include_prefixes": ["docs/", "docs/"], "suffixes": [".md"]},
        {"include_prefixes": ["docs/"], "suffixes": [".png"]},
        {"include_prefixes": ["docs/"], "suffixes": [".md", ".MD"]},
    ],
)
def test_document_scope_rejects_invalid_or_ambiguous_rules(selection: dict[str, list[str]]) -> None:
    with pytest.raises(ValueError):
        select_document_paths({"docs/index.md": ("100644", "a")}, selection)


def test_document_scope_rejects_non_regular_selected_paths() -> None:
    with pytest.raises(ValueError, match="non-regular"):
        select_document_paths(
            {"docs/index.md": ("120000", "a")},
            {"include_prefixes": ["docs/"], "suffixes": [".md"]},
        )


def test_documentation_exclusion_must_match_the_mkdocs_publication_policy() -> None:
    selection = {"exclude_prefixes": ["docs/verification/0_2_9/"]}
    policy = {
        "config_path": ".github/pages/mkdocs.yml",
        "excluded_source_prefix": "docs/verification/0_2_9/",
        "mkdocs_exclude_pattern": "verification/0_2_9/**",
    }
    validate_documentation_publication_policy(
        selection,
        policy,
        b"exclude_docs: |\n  verification/0_2_9/**\n",
    )
    with pytest.raises(ValueError, match="not bound"):
        validate_documentation_publication_policy(
            selection,
            policy,
            b"not_in_nav: |\n  verification/0_2_9/**\n",
        )


def test_public_mkdocs_configuration_excludes_controlled_029_archive() -> None:
    config = Path(".github/pages/mkdocs.yml")
    text = config.read_text(encoding="utf-8")
    assert "exclude_docs: |\n  verification/0_2_9/**" in text


def test_frozen_supported_suffix_set_includes_pdf_and_markdown() -> None:
    assert ".md" in SCANNABLE_SUFFIXES
    assert ".pdf" in SCANNABLE_SUFFIXES


def test_frozen_path_comparison_detects_content_mode_addition_and_removal_only_in_scope() -> None:
    source = {
        "src/solveur/api.py": ("100644", "blob-a"),
        "docs/guide.md": ("100644", "blob-b"),
        "docs/removed.md": ("100644", "blob-remove"),
        "scripts/internal.py": ("100644", "blob-c"),
    }
    execution = {
        "src/solveur/api.py": ("100755", "blob-a"),
        "docs/guide.md": ("100644", "blob-new"),
        "docs/added.md": ("100644", "blob-d"),
        "scripts/internal.py": ("100644", "blob-changed"),
    }

    assert changed_bound_paths(
        source,
        execution,
        ["src/solveur/api.py", "docs/guide.md", "docs/removed.md", "docs/added.md"],
    ) == ["docs/added.md", "docs/guide.md", "docs/removed.md", "src/solveur/api.py"]
