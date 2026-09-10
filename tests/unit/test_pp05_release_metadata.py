"""Targeted guards for the 0.2.8 release metadata and trust surface."""

from __future__ import annotations

import json
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[2]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _markdown_section(text: str, heading: str) -> str:
    match = re.search(rf"(?ms)^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)", text)
    assert match, f"missing Markdown section: {heading}"
    return match.group(0)


def test_028_changelog_is_structured_unreleased_and_bounded() -> None:
    section = _markdown_section(_text("CHANGELOG.md"), "0.2.8 - Unreleased")
    for heading in (
        "### Added",
        "### Improved",
        "### Verification and qualification",
        "### API and packaging",
        "### Documentation",
        "### Known limitations",
    ):
        assert heading in section
    assert "NOT_PUBLISHED_YET" in section
    assert "NOT_AVAILABLE_YET" in section
    assert "NOT_VALIDATED" in section
    assert "RESEARCH_ONLY" in section
    assert "No distributed mixed" in section
    assert not re.search(r"(?im)^## 0\.2\.8\s+-\s*(?:\d|Released)", section)


def test_security_policy_is_durable_across_published_and_candidate_channels() -> None:
    security = _text("SECURITY.md")
    assert "Latest published release" in security
    assert "Current `0.2.8` pre-publication candidate" in security
    assert "Older releases" in security
    assert "0.2.7 = supported" not in security
    assert "best-effort basis" in security


def test_candidate_metadata_and_citation_are_coherent() -> None:
    project = tomllib.loads(_text("pyproject.toml"))["project"]
    runtime = _text("src/solveur/version.py")
    citation = _text("CITATION.cff")
    assert project["version"] == "0.2.8"
    assert '__version__ = "0.2.8"' in runtime
    assert 'version: "0.2.8"' in citation
    assert "Publication status: NOT_PUBLISHED_YET" in citation
    assert "DOI status: NOT_AVAILABLE_YET" in citation

    for relative in (
        "README.md",
        "CHANGELOG.md",
        "OPEN_SOURCE_READINESS.md",
        "PUBLIC_RELEASE_POLICY.md",
    ):
        text = _text(relative)
        assert "0.2.8" in text, relative
        if relative == "README.md":
            assert "Release availability is authoritative" in text
            assert "NOT_PUBLISHED_YET" not in text
            assert "NOT_AVAILABLE_YET" not in text
        else:
            assert "NOT_PUBLISHED_YET" in text, relative
            assert "NOT_AVAILABLE_YET" in text, relative

    for relative in ("SECURITY.md", "SUPPORT.md"):
        assert "0.2.8" in _text(relative), relative
        assert "NOT_PUBLISHED_YET" in _text(relative), relative


def test_public_release_policy_classifies_reviewed_evidence_and_exclusions() -> None:
    policy = " ".join(_text("PUBLIC_RELEASE_POLICY.md").split())
    for phrase in (
        "controlled V&V contracts",
        "selected qualification records",
        "Owner/delivery decisions",
        "evidence manifests",
        "Large raw arrays",
        "temporary runtime outputs",
        "credentials and secrets",
    ):
        assert phrase in policy


def test_release_registry_and_public_boundaries_remain_unchanged() -> None:
    registry = json.loads(_text("qualification/0_2_8/consolidated_registry.json"))
    assert registry["combination_registry"]["state_counts"] == {
        "QUALIFIED_BOUNDED": 32,
        "EXPERIMENTAL": 14,
        "NOT_QUALIFIED": 0,
    }
    assert "Mixed distributed PETSc/MPI" in _text("README.md")
    assert "`NOT_VALIDATED`" in _text("README.md")
    assert "0.2.8" in _text("CONTRIBUTING.md")
    assert "haven't had the time to put everything on GitHub" not in _text("CONTRIBUTING.md")
