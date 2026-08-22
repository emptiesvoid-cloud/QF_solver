"""Regression checks for the first stable-promotion Owner-review pack."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_beam2_discrete_stable_review_is_owner_reviewed_and_traceable() -> None:
    review_path = ROOT / "qualification/reviews/beam2_discrete_dynamics_stable_owner_review_pending.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))

    assert review["status"] == "owner_reviewed"
    assert review["decision"] == "accepted_with_recommendations"
    assert review["promotion_target"] == "stable"
    assert set(review["scope"]) == {"beam2-linear-dynamics", "discrete-linear-dynamics"}
    assert review["signature"]["type"] == "declared_owner_review"
    for relative in review["evidence"]:
        assert (ROOT / relative).is_file(), relative


def test_dynamic_stable_review_pdf_is_rebuilt() -> None:
    pdf = ROOT / "output/pdf/owner_review_dynamique_lineaire.pdf"
    assert pdf.is_file()
    assert pdf.stat().st_size > 10_000
