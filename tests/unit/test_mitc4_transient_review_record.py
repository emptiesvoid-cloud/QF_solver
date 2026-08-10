from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_mitc4_transient_review_records_bounded_internal_acceptance() -> None:
    path = ROOT / "qualification" / "reviews" / "mitc4_transient_dynamic_2026-07-16.json"
    review = json.loads(path.read_text(encoding="utf-8"))

    assert review["scope"] == "mitc4-transient-dynamic"
    assert review["decision"] == "accepted_with_recommendations"
    assert review["decision_date"] == "2026-07-16"
    assert review["validator"]["name"] == "Quentin Farinazzo"
    assert review["review_mode"] == "self_review"
    assert review["independence"] == "not_independent"
    assert review["certification_claim"] == "none"
    assert review["use_class"] == "engineering_internal"
    assert review["source_worktree_state"] == "dirty_at_review"
    assert len(review["evidence"]) == 4
    assert any(item["status"] == "active" for item in review["recommendations"])
    assert review["signature"]["declaration"] == "je valide l'etude"


def test_mitc4_transient_scope_points_to_final_review() -> None:
    scope = json.loads(
        (ROOT / "qualification" / "vnv" / "mitc4_validation_scope.json").read_text(
            encoding="utf-8"
        )
    )

    readiness = scope["transient_technical_readiness"]
    assert readiness["status"] == "accepted_with_recommendations"
    assert readiness["blocking_item"] is None
    assert readiness["review_record"].endswith("mitc4_transient_dynamic_2026-07-16.json")
    assert scope["transient_internal_validation_status"] == "validated_with_recommendations"
