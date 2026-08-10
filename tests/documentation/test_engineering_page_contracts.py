from __future__ import annotations

import json
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "qualification" / "documentation_review_pages.json"


def _plain(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def test_documentation_review_registry_is_safe_and_complete() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert payload["policy"]["review_name"] == "Owner review"
    assert payload["policy"]["maturity_change_requires_recorded_owner_decision"] is True
    assert payload["policy"]["documented_demonstration_is_qualification"] is False
    assert payload["policy"]["latest_review_decision"] == "accepted_with_recommendations"
    assert payload["policy"]["qualification_effect"] == "none"

    pages = payload["pages"]
    assert len(pages) >= 21
    assert len({page["id"] for page in pages}) == len(pages)
    assert {page["kind"] for page in pages} == {"element", "method"}
    for page in pages:
        assert page["review_status"] == "owner_reviewed"
        assert page["reviewer"] == "Quentin Farinazzo"
        assert page["review_date"] == "2026-08-01"
        assert page["decision"] == "accepted_with_recommendations"
        assert (ROOT / page["review_record"]).is_file()
        assert page["qualification_effect"] == "none"


def test_every_registered_page_contains_the_engineering_contract() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    required_groups = (
        ("geometrie", "ddl"),
        ("formulation mathematique",),
        ("integration", "algorithme"),
        ("exemple executable",),
        ("maillage",),
        ("chargement", "conditions limites"),
        ("tableau", "resultat"),
        ("figure", "deform"),
        ("invariant",),
        ("convergence",),
        ("limite", "reference"),
        ("owner review",),
    )
    for entry in payload["pages"]:
        path = ROOT / entry["path"]
        assert path.is_file(), entry["path"]
        text = _plain(path.read_text(encoding="utf-8"))
        for group in required_groups:
            assert all(token in text for token in group), f"{entry['id']}: {group}"
        assert "python .\\qf_solver.py" in text or "python .\\mitc4_solver.py" in text, entry["id"]


def test_owner_review_page_records_the_explicit_decision_without_qualification() -> None:
    page = ROOT / "docs" / "verification" / "owner_review_pages_techniques.md"
    text = page.read_text(encoding="utf-8")
    assert "owner_reviewed" in text
    assert "Decision finale : **accepted_with_recommendations**" in text
    assert "DECISION accepted | accepted_with_recommendations | changes_required" in text
    assert "Une demonstration documentee" in text


def test_final_owner_review_pins_the_accepted_pdf() -> None:
    path = ROOT / "qualification" / "reviews" / "technical_manual_owner_review_final_2026-08-01.json"
    review = json.loads(path.read_text(encoding="utf-8"))
    assert review["owner"] == "Quentin Farinazzo"
    assert review["owner_declaration"] == "Je valide le document."
    assert review["decision"] == "accepted_with_recommendations"
    assert review["review_status"] == "closed"
    assert review["document_acceptance"] is True
    assert review["qualification_effect"] == "none"
    assert review["maturity_effect"] == "none"
    assert review["document"]["sha256"] == (
        "35a33ac588917568b1cf411bbe331193f4b409b7c32966f3002db29198e6c1e7"
    )
