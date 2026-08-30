"""Checks for the active, non-historical G08 Owner review record."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "qualification" / "0_2_6"
DOCS = ROOT / "docs" / "verification" / "0_2_6"


def test_active_g08_owner_review_preserves_family_boundaries() -> None:
    review = json.loads(
        (DATA / "g08_owner_final_review.json").read_text(encoding="utf-8")
    )
    assert review["status"] == "PASS_WITH_LIMITATIONS"
    assert review["contract_lowered"] is False
    decisions = review["family_decisions"]
    assert decisions["TET4"]["decision"] == "QUALIFIED_BOUNDED"
    assert decisions["TET10"]["decision"] == "PASS_WITH_LIMITATIONS"
    assert decisions["HEX8"]["decision"] == "MORE_EVIDENCE_REQUIRED"
    assert decisions["HEX20"]["decision"] == "PASS_WITH_LIMITATIONS"
    assert review["superseded_evidence_excluded"]


def test_active_g08_review_is_registered_and_documented() -> None:
    gates = json.loads((DATA / "gates.json").read_text(encoding="utf-8"))
    gate = next(row for row in gates["gates"] if row["id"] == "026-G08")
    assert gate["status"] == "PASS_WITH_LIMITATIONS"
    assert "g08_owner_final_review.json" in gate["evidence_ids"]
    document = (DOCS / "0_2_6_g08_owner_final_review.md").read_text(
        encoding="utf-8"
    )
    assert "APPROVED_BOUNDED_WITH_FAMILY_LIMITATIONS" in document
    assert "HEX8" in document
