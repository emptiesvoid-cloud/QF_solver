"""Contract for the reviewed MITC4 laminate stable Owner record."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_mitc4_laminate_static_owner_packet_is_reviewed_and_under_one_percent() -> None:
    path = ROOT / "qualification/reviews/mitc4_laminate_static_stable_owner_review_pending.json"
    review = json.loads(path.read_text(encoding="utf-8"))
    assert review["status"] == "owner_reviewed"
    assert review["decision"] == "accepted_with_recommendations"
    assert review["promotion_target"] == "stable"
    assert review["technical_snapshot"]["stable_one_percent_gate"] == "PASS"
    assert review["technical_snapshot"]["maximum_primary_error"] <= 0.01
    assert review["technical_snapshot"]["qf_code_aster_error"] <= 0.01
    for relative in review["evidence"]:
        assert (ROOT / relative).is_file(), relative
