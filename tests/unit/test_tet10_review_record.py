from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_tet10_review_records_internal_acceptance_with_recommendations() -> None:
    path = ROOT / "qualification" / "reviews" / "tet10_linear_2026-07-18.json"
    review = json.loads(path.read_text(encoding="utf-8"))

    assert review["scope"] == "tet10-linear-static"
    assert review["decision"] == "accepted_with_recommendations"
    assert review["decision_date"] == "2026-07-18"
    assert review["validator"]["name"] == "Quentin Farinazzo"
    assert review["review_mode"] == "self_review"
    assert review["independence"] == "not_independent"
    assert review["signature"]["type"] == "declared_electronic_self_review"
    assert len(review["evidence"]) == 5
    assert "VNV-TET10-CALCULIX-C3D10-014" in review["evidence"]
    assert "VNV-TET10-NEAR-INCOMPRESSIBLE-015" in review["evidence"]
    recommendation = next(item for item in review["recommendations"] if item["id"] == "REC-TET10-001")
    assert recommendation["status"] == "deferred_final_validation_campaign"
    assert recommendation["blocking_current_internal_acceptance"] is False
    assert recommendation["blocking_total_or_external_acceptance"] is True


def test_tet10_scope_is_candidate_after_signed_self_review() -> None:
    scope = json.loads(
        (ROOT / "qualification" / "vnv" / "tet10_validation_scope.json").read_text(
            encoding="utf-8"
        )
    )

    assert scope["current_status"] == "candidate"
    assert scope["remaining_blockers"] == []
    assert scope["internal_validation"]["status"] == "accepted_with_recommendations"
    assert scope["deferred_final_recommendation"]["blocking_total_or_external_acceptance"] is True
