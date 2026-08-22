"""Regression checks for the MITC4 classic stable-promotion dossier."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_mitc4_classic_review_is_owner_reviewed_and_all_evidence_exists() -> None:
    path = ROOT / "qualification/reviews/mitc4_classic_stable_owner_review_pending.json"
    review = json.loads(path.read_text(encoding="utf-8"))

    assert review["status"] == "owner_reviewed"
    assert review["decision"] == "accepted_with_recommendations"
    assert review["promotion_target"] == "stable"
    assert set(review["scope"]) == {
        "mitc4-linear-static",
        "mitc4-modal",
        "mitc4-transient-dynamic",
        "mitc4-harmonic-response",
    }
    assert review["signature"]["type"] == "declared_owner_review"
    for relative in review["evidence"]:
        assert (ROOT / relative).is_file(), relative


def test_mitc4_classic_review_questions_match_the_four_scopes() -> None:
    document = (ROOT / "docs/verification/mitc4_classic_stable_owner_review.md").read_text(encoding="utf-8")
    for scope in ("mitc4-linear-static", "mitc4-modal", "mitc4-transient-dynamic", "mitc4-harmonic-response"):
        assert scope in document
    assert "0,726108 %" in document
    assert "0,782014 %" in document
    assert "0,09867227 %" in document
    assert "0,547102 %" in document
