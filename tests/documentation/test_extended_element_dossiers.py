from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "qualification" / "documentation_review_pages.json"
PRIMARY = {
    "DOC-ELEM-001": "TET4-FW",
    "DOC-ELEM-002": "TET10-FW",
    "DOC-ELEM-003": "MITC4-FW",
    "DOC-ELEM-BEAM2-001": "BEAM2-",
}


def _entry(identifier: str) -> dict:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return next(page for page in payload["pages"] if page["id"] == identifier)


@pytest.mark.parametrize("identifier", PRIMARY)
def test_primary_element_has_a_ten_page_pdf_contract(identifier: str) -> None:
    entry = _entry(identifier)
    assert entry["minimum_pdf_pages"] >= 10
    assert len(entry["appendices"]) >= 3
    assert all((ROOT / path).is_file() for path in entry["appendices"])


@pytest.mark.parametrize(("identifier", "test_prefix"), PRIMARY.items())
def test_primary_element_documents_strong_weak_forms_and_ten_tests(
    identifier: str,
    test_prefix: str,
) -> None:
    entry = _entry(identifier)
    paths = [ROOT / entry["path"], *(ROOT / path for path in entry["appendices"])]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    lowered = text.lower()
    assert "formulation forte" in lowered
    assert "formulation faible" in lowered
    assert "exemple" in lowered
    assert "convergence" in lowered
    assert "references" in lowered
    identifiers = set(re.findall(rf"{re.escape(test_prefix)}[A-Z]*-?\d{{2}}", text))
    assert len(identifiers) >= 10, (identifier, sorted(identifiers))


def test_generated_pdf_page_counts_meet_the_controlled_minimum() -> None:
    report = ROOT / "output" / "pdf" / "dossier_technique_page_counts.json"
    if not report.is_file():
        pytest.skip("Build scripts/build_technical_pages_pdf.py before PDF checks.")
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["elements"]
    assert all(row["status"] == "PASS" for row in payload["elements"])
    assert all(row["pages"] >= row["minimum"] >= 10 for row in payload["elements"])
