"""Deterministic guards for the PP04 public-documentation cleanup."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
REGISTRY = DOCS / "document_registry.json"
CONSOLIDATED = ROOT / "qualification" / "0_2_8" / "consolidated_registry.json"

CURRENT_STATUS_PAGES = (
    DOCS / "analyses" / "index.md",
    DOCS / "elements" / "index.md",
    DOCS / "etat" / "capacites.md",
    DOCS / "solveurs" / "index.md",
    DOCS / "getting-started" / "when-to-use-qf-solver.md",
)

HISTORICAL_PAGES = (
    DOCS / "verification" / "0_2_7" / "README.md",
    DOCS / "benchmarks" / "index.md",
    DOCS / "comparisons" / "index.md",
    DOCS / "comparisons" / "python-fem-solvers.md",
    DOCS / "comparisons" / "qf-vs-calculix.md",
    DOCS / "comparisons" / "qf-vs-code-aster.md",
    DOCS / "comparisons" / "qf-vs-scikit-fem.md",
    DOCS / "comparisons" / "qf-vs-sfepy.md",
    DOCS / "verification" / "0_2_8" / "README.md",
)

# The 0.2.7 verification README is a frozen public view.  Its historical
# context is supplied by the surrounding navigation and front matter, so the
# guard must not require a post-freeze content edit.  Other historical pages
# remain editable and must retain their explicit banner.
IMMUTABLE_HISTORICAL_PAGES = (
    DOCS / "verification" / "0_2_7" / "README.md",
)
EDITABLE_HISTORICAL_PAGES = tuple(path for path in HISTORICAL_PAGES if path not in IMMUTABLE_HISTORICAL_PAGES)

SUPERSEDED_PAGES = (
    DOCS / "demarrage" / "installation.md",
    DOCS / "demarrage" / "premier_calcul.md",
    DOCS / "creer_cas.md",
    DOCS / "grand_modele.md",
    DOCS / "manuel_theorique_elements_finis.md",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _front_matter(path: Path) -> str:
    content = _text(path)
    assert content.startswith("---\n")
    end = content.find("\n---\n", 4)
    assert end != -1
    return content[4:end]


def test_current_document_metadata_and_registry_are_coherent() -> None:
    registry = json.loads(_text(REGISTRY))
    assert registry["language"] == "en"
    entries = {entry["id"]: entry for entry in registry["documents"]}

    expected = {
        "DOC-STATE-001": ("index.md", "QF Solver 0.2.8"),
        "DOC-ARCH-001": ("architecture.md", "QF Solver architecture"),
        "DOC-REF-002": ("reference/registre_documentaire.md", "Documentation registry"),
    }
    for document_id, (path, title) in expected.items():
        entry = entries[document_id]
        assert entry["path"] == path
        assert entry["title"] == title
        assert (DOCS / path).is_file()

    for path in ("index.md", "architecture.md", "reference/registre_documentaire.md"):
        assert "applicable_version: 0.2.8-development" in _front_matter(DOCS / path)

    assert re.search(r"^# QF Solver 0\.2\.8$", _text(DOCS / "index.md"), re.MULTILINE)
    assert re.search(r"^# QF Solver architecture$", _text(DOCS / "architecture.md"), re.MULTILINE)
    assert re.search(r"^# Documentation registry$", _text(DOCS / "reference" / "registre_documentaire.md"), re.MULTILINE)
    generated = _text(DOCS / "generated" / "document_registry.md")
    assert "| DOC-STATE-001 | QF Solver 0.2.8 |" in generated
    assert "| DOC-ARCH-001 | QF Solver architecture |" in generated
    assert "| DOC-REF-002 | Documentation registry |" in generated


def test_generated_status_avoids_fragile_test_count() -> None:
    status = _text(DOCS / "generated" / "status.md")
    assert "Test inventory" not in status
    assert re.search(r"full-suite test\s+inventory is recorded by the final Gate-E evidence", status)
    assert "0.2.8-development" in status
    assert "Mixed distributed PETSc/MPI" in status
    assert "not validated" in status


def test_current_public_pages_use_canonical_maturity_vocabulary() -> None:
    for path in CURRENT_STATUS_PAGES:
        content = _text(path)
        assert "SUPPORTED_WITH_LIMITATIONS" not in content
    assert "`ROUTE_DEPENDENT — see capability index`" in _text(DOCS / "analyses" / "index.md")
    assert "`EXPERIMENTAL_BOUNDED`" in _text(DOCS / "getting-started" / "when-to-use-qf-solver.md")


def test_historical_pages_are_explicitly_labeled() -> None:
    for path in HISTORICAL_PAGES:
        content = _text(path)
        assert "historical" in content.lower() or "intermediate" in content.lower()
    for path in EDITABLE_HISTORICAL_PAGES:
        assert "NOT CURRENT STATUS" in _text(path)

    frozen_readme = DOCS / "verification" / "0_2_7" / "README.md"
    assert frozen_readme in IMMUTABLE_HISTORICAL_PAGES
    assert "applicable_version: 0.2.7" in _front_matter(frozen_readme)
    nav = _text(ROOT / ".github" / "pages" / "mkdocs.yml")
    historical_nav = re.search(r"Historical Evidence:\s*(?:\n|.)*?verification/0_2_7/README\.md", nav)
    assert historical_nav is not None


def test_superseded_pages_have_canonical_targets() -> None:
    for path in SUPERSEDED_PAGES:
        content = _text(path)
        assert "status: superseded" in content
        assert "canonical" in content.lower() or "guide maintenu" in content.lower()
    nav = _text(ROOT / ".github" / "pages" / "mkdocs.yml")
    for path in SUPERSEDED_PAGES:
        assert path.relative_to(DOCS).as_posix() not in nav


def test_registry_counts_and_distributed_boundary_are_preserved() -> None:
    registry = json.loads(_text(CONSOLIDATED))
    counts = registry["combination_registry"]["state_counts"]
    assert counts == {
        "QUALIFIED_BOUNDED": 32,
        "EXPERIMENTAL": 14,
        "NOT_QUALIFIED": 0,
    }
    assert sum(counts.values()) == 46
    capabilities = _text(DOCS / "capabilities" / "index.md")
    assert "Distributed mixed PETSc/MPI runtime" in capabilities
    assert "`NOT_VALIDATED`" in capabilities


def test_public_navigation_is_english() -> None:
    nav = _text(ROOT / ".github" / "pages" / "mkdocs.yml")
    assert "Getting Started:" in nav
    assert "Verification & Validation:" in nav
    assert "Project:" in nav
    assert "Demarrage:" not in nav
    assert "Verification et validation:" not in nav
