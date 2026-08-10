from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_mitc3_owner_review_records_bounded_acceptance_and_supersedes_pending() -> None:
    pending = json.loads(
        (ROOT / "qualification" / "reviews" / "mitc3_linear_static_pending.json").read_text(
            encoding="utf-8"
        )
    )
    record = json.loads(
        (ROOT / "qualification" / "reviews" / "mitc3_linear_static_2026-08-01.json").read_text(
            encoding="utf-8"
        )
    )
    assert pending["status"] == "superseded_by_signed_owner_review"
    assert pending["superseded_by"].endswith("mitc3_linear_static_2026-08-01.json")
    assert record["status"] == "owner_validated_bounded_scope"
    assert record["review_mode"] == "owner_review"
    assert record["independence"] == "not_independent"
    assert record["decision"] == "accepted_for_bounded_engineering_use"
    assert record["decision_date"] == "2026-08-01"
    assert [question["answer"] for question in record["questions"]] == ["yes"] * 6
    assert record["automated_evidence"]["code_aster_dkt"]["status"] == (
        "PASS_EXTERNAL_CORRELATION"
    )
    assert record["automated_evidence"]["calculix_s3"]["status"] == "WARNING"
    assert record["automated_evidence"]["explicit_bending_patch"]["status"] == "PASS"
    assert record["automated_evidence"]["pinched_hemisphere_code_aster"]["status"] == (
        "PASS_EXTERNAL_CORRELATION"
    )
    assert record["blocking_items"] == []
