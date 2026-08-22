"""Checks for the consolidated element-family Owner review PDF."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_owner_review_element_pack_pdf.py"
PACK = ROOT / "output" / "pdf" / "qf_solver_owner_review_elements_20260821.pdf"


def _load_builder():
    specification = importlib.util.spec_from_file_location("owner_review_element_pack", SCRIPT)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_element_owner_review_pack_contains_all_requested_families() -> None:
    _load_builder().main()
    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(PACK)).pages)

    assert len(PdfReader(str(PACK)).pages) >= 7
    for label in ("MITC3 isotrope classique", "MITC4 isotrope classique", "MITC4 multicouche dynamique", "TET4 isotrope", "TET10 isotrope"):
        assert label in text
    assert "Quentin Farinazzo" in text
    assert "aucune certification externe" in text
