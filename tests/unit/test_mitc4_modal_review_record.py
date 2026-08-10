from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "qualification" / "reviews" / "mitc4_modal_2026-07-16.json"


def test_mitc4_modal_review_records_provisional_consistent_mass_acceptance() -> None:
    review = json.loads(REVIEW.read_text(encoding="utf-8"))

    assert review["scope"] == "mitc4-modal"
    assert review["validation_status"] == "provisional_internal_validation"
    assert review["decision"] == "accepted_with_recommendations"
    assert review["validator"]["name"] == "Quentin Farinazzo"
    assert review["review_mode"] == "self_review"
    assert review["independence"] == "not_independent"
    assert review["certification_claim"] == "none"
    assert review["use_class"] == "engineering_internal_provisional"
    assert any("masse coherente" in item for item in review["accepted_domain"])
    assert any("masse concentree" in item for item in review["excluded_domain"])
    recommendations = {item["id"]: item["status"] for item in review["recommendations"]}
    assert recommendations["REC-MOD-004"] == "scope_exclusion_active"
    assert recommendations["REC-MOD-005"] == "open_external_qualification_blocker"
    assert review["signature"]["declaration"].endswith("tentative de validation")


def test_mitc4_modal_scope_points_to_provisional_review() -> None:
    scope = json.loads(
        (ROOT / "qualification" / "vnv" / "mitc4_validation_scope.json").read_text(
            encoding="utf-8"
        )
    )
    readiness = scope["modal_technical_readiness"]
    assert readiness["status"] == "provisionally_accepted_with_recommendations"
    assert readiness["blocking_item"] is None
    assert readiness["review_record"].endswith("mitc4_modal_2026-07-16.json")
    assert scope["modal_internal_validation_status"] == "tentatively_validated"
    assert scope["modal_mass_policy"]["accepted_formulation"] == "consistent"
