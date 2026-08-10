from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
REVIEWS = ROOT / "docs" / "assets" / "reviews"


def test_mitc3_owner_review_pdf_pack_is_complete() -> None:
    expected = {
        "owner_review_mitc3_statique.pdf": (6, "Questions de decision Owner"),
        "vnv_mitc3_scordelis_h20k.pdf": (3, "20,000"),
        "vnv_mitc3_cylindre_pince_h20k.pdf": (3, "19,600"),
        "vnv_mitc3_hemisphere_code_aster.pdf": (5, "0.0927 %"),
    }
    for filename, (minimum_pages, marker) in expected.items():
        path = REVIEWS / filename
        assert path.is_file()
        assert path.stat().st_size > 80_000
        reader = PdfReader(str(path))
        assert len(reader.pages) >= minimum_pages
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        assert "QF_solver" in text
        assert "MITC3" in text
        assert marker in text
