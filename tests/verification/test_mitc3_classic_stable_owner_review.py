"""Regression checks for the bounded MITC3 classic promotion dossier."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_mitc3_classic_stable_review_is_owner_reviewed_and_separate_from_laminates() -> None:
    path = ROOT / "qualification/reviews/mitc3_classic_stable_owner_review_pending.json"
    review = json.loads(path.read_text(encoding="utf-8"))

    assert review["status"] == "owner_reviewed"
    assert review["decision"] == "accepted_with_recommendations"
    assert review["promotion_target"] == "stable"
    assert set(review["scope"]) == {
        "mitc3-modal",
        "mitc3-transient-dynamic",
        "mitc3-harmonic-response",
    }
    assert review["signature"]["type"] == "declared_owner_review"
    assert all((ROOT / item).is_file() for item in review["evidence"])


def test_mitc3_classic_review_records_final_error_gate() -> None:
    document = (ROOT / "docs/verification/mitc3_classic_stable_owner_review.md").read_text(encoding="utf-8")
    assert "0,673329 %" in document
    assert "0,174158 %" in document
    assert "0,096638 %" in document
    assert "MITC3 stratifié" in document
    assert "MITC3 courbe" in document
