"""Regression checks for controlled Owner-review PDFs."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_open_owner_review_pdfs.py"


def _load_builder():
    specification = importlib.util.spec_from_file_location("open_owner_review_pdf_builder", SCRIPT)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_owner_review_pdfs_are_complete() -> None:
    builder = _load_builder()
    correlation, status = builder.build()

    correlation_text = "\n".join(page.extract_text() or "" for page in PdfReader(str(correlation)).pages)
    status_text = "\n".join(page.extract_text() or "" for page in PdfReader(str(status)).pages)

    assert "Q10" in correlation_text
    assert "MITC3 hemisphere pince" in correlation_text
    assert "DECISION ENREGISTREE" in status_text
    assert "NE PAS VALIDER ENCORE" in status_text
