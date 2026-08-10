from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PENDING_REVIEW = ROOT / "qualification" / "reviews" / "orthotropic_solids_pending.json"
SIGNED_REVIEW = ROOT / "qualification" / "reviews" / "orthotropic_solids_2026-07-22.json"
SPECIFICATION = ROOT / "qualification" / "specifications" / "composite_solids.json"


def test_orthotropic_solids_pending_record_is_superseded_by_signed_review() -> None:
    review = json.loads(PENDING_REVIEW.read_text(encoding="utf-8"))

    assert review["scope"] == "orthotropic-solid-tet4-tet10"
    assert review["decision"] == "superseded_by_signed_review"
    assert review["technical_status"] == "review_closed_with_recommendations"
    assert review["successor_review"] == "qualification/reviews/orthotropic_solids_2026-07-22.json"
    assert review["validator"]["name"] == "Quentin Farinazzo"
    assert review["review_mode"] == "self_review"
    assert review["independence"] == "not_independent"
    assert review["certification_claim"] == "none"
    assert review["review_document"] == "docs/verification/revue_solides_orthotropes.md"
    assert review["proposed_decision"] == "accepted_with_recommendations"
    assert review["signature"] is None


def test_orthotropic_solids_review_covers_all_automated_evidence() -> None:
    review = json.loads(PENDING_REVIEW.read_text(encoding="utf-8"))

    assert set(review["evidence"]) == {
        "VNV-ORTHOTROPIC-SOLID-KERNEL-001",
        "VNV-ORTHOTROPIC-SOLID-EXTERNAL-002",
        "VNV-ORTHOTROPIC-SOLID-CONVERGENCE-003",
        "VNV-ORTHOTROPIC-ISOTROPIC-NONREGRESSION-004",
    }
    assert any("TET4 orthotrope converge" in item for item in review["known_limitations"])
    recommendations = {item["id"]: item for item in review["proposed_recommendations"]}
    assert recommendations["REC-ORTHO-001"]["blocking_current_internal_acceptance"] is False
    assert recommendations["REC-ORTHO-002"]["blocking_total_or_external_acceptance"] is True
    assert recommendations["REC-ORTHO-003"]["blocking_total_or_external_acceptance"] is True


def test_orthotropic_solids_review_records_partial_human_decisions() -> None:
    review = json.loads(PENDING_REVIEW.read_text(encoding="utf-8"))

    decisions = {item["item"]: item["decision"] for item in review["recorded_decisions"]}
    assert decisions["engineering_constants"] == "accepted"
    assert decisions["voigt_transformation"] == "accepted"
    assert decisions["external_correlation"] == "accepted"
    assert decisions["homogenized_composite_scope"] == "accepted"
    assert decisions["tet10_linear_static"] == "accepted"
    assert decisions["tet4_flexural_refinement"] == "accepted_with_recommendation"
    assert decisions["point_stress_singularities"] == "not_accepted_as_exclusion"
    assert any("geometries courbes" in item for item in review["open_actions"])
    assert any("modales et dynamiques" in item for item in review["open_actions"])


def test_orthotropic_solids_extension_maturity_is_explicit() -> None:
    specification = json.loads(SPECIFICATION.read_text(encoding="utf-8"))

    scopes = {item["scope"]: item for item in specification["planned_extensions"]}
    assert scopes["orthotropic-solid-modal"]["status"] == "technical_verification"
    assert scopes["orthotropic-solid-transient-dynamic"]["status"] == "technical_verification"
    assert scopes["orthotropic-solid-large-static"]["status"] == "technical_verification"
    assert scopes["orthotropic-solid-curvilinear-orientation"]["status"] == "planned"
    assert scopes["orthotropic-solid-singular-stress-assessment"]["status"] == "ready_for_owner_review"
    excluded = set(specification["out_of_scope_v1"])
    assert "delaminage et elements cohesifs" in excluded
    assert "endommagement progressif" in excluded
    assert "grandes deformations" in excluded


def test_orthotropic_solids_signed_review_records_internal_acceptance() -> None:
    review = json.loads(SIGNED_REVIEW.read_text(encoding="utf-8"))

    assert review["decision"] == "accepted_with_recommendations"
    assert review["validation_status"] == "engineering_internal_validated_with_recommendations"
    assert review["certification_claim"] == "none"
    assert review["signature"]["name"] == "Quentin Farinazzo"
    assert review["signature"]["date"] == "2026-07-22"
    assert any("champ d'orientation continu" in item for item in review["excluded_domain"])
    assert any(item["id"] == "REC-ORTHO-005" for item in review["recommendations"])


def test_singular_stress_interim_review_has_completed_added_evidence() -> None:
    review_path = (
        ROOT
        / "qualification"
        / "reviews"
        / "orthotropic_singular_stress_pending.json"
    )
    review = json.loads(review_path.read_text(encoding="utf-8"))

    assert review["decision"] == "more_evidence_required"
    assert review["decision_date"] == "2026-07-29"
    assert review["status"] == "additional_evidence_complete_pending_human_recheck"
    assert review["additional_evidence"]["status"] == "PASS_STRESS_ACCEPTANCE"
    assert review["additional_evidence"]["stress_fields_published"] is True


def test_singular_stress_final_review_records_acceptance_with_recommendations() -> None:
    review_path = (
        ROOT
        / "qualification"
        / "reviews"
        / "orthotropic_singular_stress_2026-07-29.json"
    )
    review = json.loads(review_path.read_text(encoding="utf-8"))

    assert review["decision"] == "accepted_with_recommendations"
    assert (
        review["validation_status"]
        == "engineering_internal_validated_with_recommendations"
    )
    assert all(review["accepted_answers"].values())
    assert review["signature"]["name"] == "Quentin Farinazzo"
    assert review["signature"]["date"] == "2026-07-29"
    assert review["certification_claim"] == "none"
