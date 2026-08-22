"""Tests for review-record validation used by maturity promotion."""

from __future__ import annotations

import json
from pathlib import Path

from solveur.verification.owner_review import validate_owner_review


ROOT = Path(__file__).resolve().parents[2]


def test_pending_review_is_valid_but_requires_a_decision_for_release() -> None:
    path = ROOT / "qualification" / "reviews" / "contact_frictional_static_owner_review_pending.json"

    pending = validate_owner_review(path, scope="contact-frictional-static")
    gated = validate_owner_review(path, scope="contact-frictional-static", require_decision=True)

    assert pending.status == "PENDING"
    assert pending.errors == ()
    assert gated.status == "FAIL"
    assert "decision is required" in gated.errors[0]


def test_mitc4_orthotropic_one_ply_remains_gated_until_owner_signature() -> None:
    path = ROOT / "qualification" / "reviews" / "mitc4_orthotropic_one_ply_stable_pending.json"

    signed = validate_owner_review(
        path,
        scope="mitc4-orthotropic-homogeneous-ply",
        require_decision=True,
        target_maturity="stable",
    )

    assert signed.status == "PASS"
    assert signed.decision == "accepted_with_recommendations"
    assert signed.promotion_target == "stable"
    assert signed.errors == ()


def test_signed_owner_review_passes_structural_validation() -> None:
    path = ROOT / "qualification" / "reviews" / "orthotropic_solids_2026-07-22.json"

    report = validate_owner_review(path, scope="orthotropic-solid-tet4-tet10", require_decision=True)

    assert report.status == "PASS"
    assert report.decision == "accepted_with_recommendations"
    assert report.errors == ()


def test_invalid_decision_and_missing_signature_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "invalid_review.json"
    path.write_text(
        json.dumps(
            {
                "review_id": "INVALID-001",
                "scope": ["tet4-linear-static"],
                "decision": "accepted",
                "signature": None,
            }
        ),
        encoding="utf-8",
    )

    report = validate_owner_review(path, scope="tet4-linear-static", require_decision=True)

    assert report.status == "FAIL"
    assert any("unsupported decision" in error for error in report.errors)
    assert any("signature object" in error for error in report.errors)


def test_signed_review_can_explicitly_target_stable_without_changing_the_matrix(
    tmp_path: Path,
) -> None:
    path = tmp_path / "stable_review.json"
    path.write_text(
        json.dumps(
            {
                "review_id": "STABLE-001",
                "scope": "tet4-linear-static",
                "decision": "accepted_with_recommendations",
                "promotion_target": "stable",
                "signature": {"name": "Owner", "date": "2026-08-20"},
            }
        ),
        encoding="utf-8",
    )

    report = validate_owner_review(
        path,
        scope="tet4-linear-static",
        require_decision=True,
        target_maturity="stable",
    )

    assert report.status == "PASS"
    assert report.promotion_target == "stable"


def test_stable_target_rejects_more_evidence_required(tmp_path: Path) -> None:
    path = tmp_path / "incomplete_review.json"
    path.write_text(
        json.dumps(
            {
                "review_id": "STABLE-002",
                "scope": "tet4-linear-static",
                "decision": "more_evidence_required",
                "promotion_target": "stable",
                "signature": {"name": "Owner", "date": "2026-08-20"},
            }
        ),
        encoding="utf-8",
    )

    report = validate_owner_review(path, require_decision=True)

    assert report.status == "FAIL"
    assert any("incompatible" in error for error in report.errors)
