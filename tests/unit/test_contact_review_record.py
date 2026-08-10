"""Contracts for the interim and final Owner review records of contact V1."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "qualification" / "reviews" / "contact_v1_linear_static_bounded_pending.json"
FINAL_REVIEW = (
    ROOT
    / "qualification"
    / "reviews"
    / "contact_v1_linear_static_bounded_2026-07-29.json"
)
REGISTER = ROOT / "qualification" / "reviews" / "owner_review_register_2026-07-26.json"


def test_contact_v1_interim_review_requests_and_receives_more_evidence() -> None:
    review = json.loads(REVIEW.read_text(encoding="utf-8"))

    assert review["scope"] == "contact-v1-linear-static-bounded"
    assert (
        review["technical_status"]
        == "external_correlation_complete_with_warning_pending_human_recheck"
    )
    assert review["decision"] == "more_evidence_required"
    assert review["decision_date"] == "2026-07-29"
    assert review["signature"]["applies_to"] == "interim more_evidence_required decision only"
    assert review["certification_claim"] == "none"
    assert review["review_mode"] == "self_review"
    assert "VNV-CONTACT-CODEASTER-FOLDED-SEARCH-007" in review["evidence"]
    assert "VNV-CONTACT-ADDITIONAL-MODELS-008" in review["evidence"]
    assert "VNV-CONTACT-CODEASTER-ADDITIONAL-009" in review["evidence"]
    assert review["additional_evidence"]["status"] == "PASS_INTERNAL"
    assert review["external_correlation_extension"]["status"] == "PASS_WITH_EXTERNAL_WARNING"
    assert review["superseded_by"].endswith(
        "contact_v1_linear_static_bounded_2026-07-29.json"
    )
    assert any("grand glissement" in item for item in review["known_limitations"])


def test_contact_v1_final_owner_review_records_the_refined_acceptance() -> None:
    review = json.loads(FINAL_REVIEW.read_text(encoding="utf-8"))

    condition = review["acceptance_condition"]
    assert review["review_type"] == "owner_review"
    assert review["validation_status"] == "engineering_ready_bounded"
    assert review["decision"] == "accepted_for_bounded_engineering_use"
    assert review["owner"]["name"] == "Quentin Farinazzo"
    assert review["decision_date"] == "2026-07-29"
    assert condition["refined_elements"] == 768
    assert condition["refined_code_aster_curve_error"] < condition["limit"]
    assert condition["confirmation_elements"] == 9984
    assert condition["confirmation_code_aster_curve_error"] < 1.0e-10
    assert condition["status"] == "PASS"
    assert review["certification_claim"] == "none"


def test_contact_v1_owner_review_is_visible_in_the_register() -> None:
    register = json.loads(REGISTER.read_text(encoding="utf-8"))

    record = next(
        item
        for item in register["accepted_internal_with_recommendations"]
        if item["scope"] == "contact-v1-linear-static-bounded"
    )
    assert record["review"].endswith(
        "contact_v1_linear_static_bounded_2026-07-29.json"
    )
    assert record["decision_date"] == "2026-07-29"
    assert "contact-v1-linear-static-bounded" in register["accepted_internal"]
