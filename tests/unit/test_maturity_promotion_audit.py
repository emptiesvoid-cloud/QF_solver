"""Tests for the evidence-driven maturity-promotion audit."""

from __future__ import annotations

import pytest
import json
from pathlib import Path

from solveur.verification.maturity_promotion import (
    MaturityPromotionAuditor,
    _family_evidence,
    _review_state,
    _signed_promotion_target,
    _stable_error_violations,
)


ROOT = Path(__file__).resolve().parents[2]


def test_maturity_promotion_audit_covers_plan_and_current_evidence() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()

    assert report["status"] == "WARNING"
    assert report["policy"]["automatic_maturity_promotion"] is False
    assert report["policy"]["final_relative_error_limit"] == 0.01
    assert report["policy"]["engineering_primary_observable_limit"] == 0.01
    assert report["policy"]["primary_engineering_error_limit"] == 0.01
    assert "<= 1 percent" in report["policy"]["primary_engineering_error_policy"]
    assert "1 percent" in report["policy"]["final_relative_error_policy"]
    assert report["summary"]["scope_count"] == 37
    assert report["summary"]["path_integrity_pass_count"] == 37
    assert report["summary"]["owner_decision_pending_scope_count"] == 3
    assert all(not row["missing_evidence"] for row in report["scopes"])


def test_promotion_registry_exposes_one_percent_engineering_error_policy() -> None:
    registry = json.loads(
        (ROOT / "qualification" / "maturity_promotion_0_2_1.json").read_text(encoding="utf-8")
    )
    policy = registry["policy"]
    assert policy["primary_engineering_error_limit"] == 0.01
    assert "<= 1 percent" in policy["primary_engineering_error_policy"]


def test_one_percent_gate_covers_energy_stress_strain_and_reaction_errors() -> None:
    criteria = [
        {
            "id": "CHECK",
            "required": True,
            "assertions": [
                {"path": "energy_error", "actual": 0.0101},
                {"path": "stress_error", "actual": 0.0101},
                {"path": "strain_error", "actual": 0.0101},
                {"path": "reaction_error", "actual": 0.0101},
                {"path": "residual", "actual": 1.0},
            ],
        }
    ]
    violations = _stable_error_violations(criteria, 0.01)
    assert {item["path"] for item in violations} == {
        "energy_error",
        "stress_error",
        "strain_error",
        "reaction_error",
    }


def test_maturity_promotion_audit_does_not_change_matrix_statuses() -> None:
    matrix_before = json.loads(
        (ROOT / "qualification" / "element_analysis_matrix.json").read_text(encoding="utf-8")
    )
    report = MaturityPromotionAuditor(ROOT).audit()
    matrix_after = json.loads(
        (ROOT / "qualification" / "element_analysis_matrix.json").read_text(encoding="utf-8")
    )

    assert matrix_after == matrix_before
    tet4 = next(row for row in report["scopes"] if row["scope"] == "tet4-linear-static")
    assert tet4["current_status"] == "stable"
    assert tet4["target_status"] == "stable"
    assert tet4["template_criteria_status"] == "STRUCTURED"
    assert tet4["criteria_status"] == "PASS"
    assert tet4["blocking_criteria"] == []
    assert tet4["promotion_gate"] == "NO_PROMOTION_REQUIRED"


def test_review_discovery_ignores_non_json_evidence() -> None:
    assert _review_state(
        ROOT,
        ["output/pdf/tet10_stable_refinement_owner_review.pdf"],
        "tet10-linear-static",
    ) == "MISSING"


def test_family_evidence_includes_the_scope_owner_review_record() -> None:
    matrix = json.loads(
        (ROOT / "qualification" / "element_analysis_matrix.json").read_text(encoding="utf-8")
    )

    evidence = _family_evidence("tet4-linear-static", matrix)

    assert "qualification/reviews/tet4_stable_promotion_owner_review_pending.json" in evidence


def test_maturity_promotion_reports_are_reproducible(tmp_path: Path) -> None:
    auditor = MaturityPromotionAuditor(ROOT)
    report = auditor.audit()
    paths = auditor.write_reports(tmp_path / "promotion", report)

    assert paths["json"].is_file()
    assert paths["markdown"].is_file()
    assert paths["owner_packet_json"].is_file()
    assert paths["owner_packet_markdown"].is_file()
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert payload["audit_id"] == report["audit_id"]
    markdown = paths["markdown"].read_text(encoding="utf-8")
    assert "BLOCKED_CRITERIA_FAILED" in markdown


def test_owner_review_packet_contains_no_decisions_and_excludes_technical_failures(tmp_path: Path) -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    packet = MaturityPromotionAuditor(ROOT).write_reports(tmp_path / "owner_packet", report)
    payload = json.loads(packet["owner_packet_json"].read_text(encoding="utf-8"))

    assert payload["status"] == "PENDING_OWNER_REVIEW"
    assert payload["policy"]["automatic_maturity_promotion"] is False
    assert payload["scopes"]
    assert all(item["decision"] is None for item in payload["scopes"])
    assert all(item["signature"] is None for item in payload["scopes"])
    assert all(item["promotion_target"] is None for item in payload["scopes"])
    assert all(item["technical_status"] in {"PASS", "BLOCKED"} for item in payload["scopes"])
    assert all(
        item["technical_status"] == "PASS" or item["blocking_criteria"]
        for item in payload["scopes"]
    )
    assert payload["summary"]["owner_decision_pending_count"] == 3


def test_promotion_audit_classifies_pending_decisions_separately() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    rows = {item["scope"]: item for item in report["scopes"]}

    assert rows["mitc3-laminate-dynamic"]["blocking_classification"] == "technical_criteria_failed"
    assert rows["mitc3-laminate-dynamic"]["promotion_gate"] == "BLOCKED_CRITERIA_FAILED"
    assert rows["orthotropic-solid-modal"]["blocking_classification"] == "none"
    assert rows["orthotropic-solid-modal"]["promotion_gate"] == "READY_FOR_OWNER_REVIEW"
    assert rows["mitc3-laminate-static-curved"]["blocking_classification"] == "technical_criteria_failed"
    assert rows["mitc3-laminate-static-curved"]["promotion_gate"] == "BLOCKED_CRITERIA_FAILED"


def test_promotion_report_separates_technical_owner_and_release_states() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    rows = {item["scope"]: item for item in report["scopes"]}

    ready = rows["contact-frictional-static"]
    assert ready["technical_status"] == "PASS"
    assert ready["owner_decision"] == "ACCEPTED"
    assert ready["maturity_target"] == "owner_accepted"
    assert ready["release_readiness"] == "READY_FOR_RELEASE_ACTION"

    technical_block = rows["mitc3-laminate-dynamic"]
    assert technical_block["technical_status"] == "BLOCKED"
    assert technical_block["release_readiness"] == "NOT_READY_TECHNICAL"

    promoted = rows["mitc4-laminate-dynamic-refined-three-layups"]
    assert promoted["technical_status"] == "PASS"
    assert promoted["owner_decision"] == "ACCEPTED"
    assert promoted["maturity_target"] == "stable"
    assert promoted["release_readiness"] == "NO_PROMOTION_REQUIRED"


def test_bounded_mitc3_subscopes_are_ready_only_for_owner_review() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    rows = {item["scope"]: item for item in report["scopes"]}

    for scope in (
        "mitc3-laminate-dynamic-thin-planar",
        "mitc3-laminate-static-curved-mixed-transverse",
    ):
        row = rows[scope]
        assert row["criteria_status"] == "BLOCKED"
        assert row["blocking_classification"] == "owner_decision_pending"
        assert row["promotion_gate"] == "BLOCKED_OWNER_REVIEW"
        assert row["path_integrity"] == "PASS"
        assert row["missing_evidence"] == []


def test_pending_criteria_are_traceable_to_undecided_review_files() -> None:
    matrix = json.loads(
        (ROOT / "qualification" / "maturity_criteria_0_2_1.json").read_text(encoding="utf-8")
    )
    pending = [
        criterion
        for scope in matrix["scopes"]
        for criterion in scope["criteria"]
        if criterion.get("kind") == "pending"
    ]

    assert pending
    for criterion in pending:
        source = criterion.get("source")
        assert source, criterion["id"]
        review_path = ROOT / source
        assert review_path.is_file(), criterion["id"]
        review = json.loads(review_path.read_text(encoding="utf-8"))
        assert review.get("status", "pending") in {"pending", "pending_owner_review", "ready_for_owner_review"}
        assert review.get("decision") is None
        assert review.get("signature") is None


def test_signed_promotion_target_is_detected_without_matrix_mutation(tmp_path: Path) -> None:
    review = tmp_path / "signed_stable.json"
    review.write_text(
        json.dumps(
            {
                "scope": "tet4-linear-static",
                "decision": "accepted_with_recommendations",
                "promotion_target": "stable",
                "signature": {"name": "Owner", "date": "2026-08-20"},
            }
        ),
        encoding="utf-8",
    )

    assert _signed_promotion_target(tmp_path, [review.name], "tet4-linear-static") == "stable"


def test_stable_scopes_within_one_percent_have_structured_passing_criteria() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    expected = {
        "tet4-modal",
        "tet4-transient-dynamic",
        "tet4-harmonic-response",
        "tet10-modal",
        "tet10-transient-dynamic",
        "tet10-harmonic-response",
    }
    rows = {row["scope"]: row for row in report["scopes"]}

    for scope in expected:
        row = rows[scope]
        assert row["template_criteria_status"] == "STRUCTURED"
        assert row["criteria_status"] == "PASS"
        assert row["blocking_criteria"] == []
        assert row["current_status"] == "stable"
        assert row["promotion_gate"] == "NO_PROMOTION_REQUIRED"
        assert all(
            criterion["status"] in {"PASS", "NOT_APPLICABLE"}
            for criterion in row["criteria"]
        )

    tet4_static = rows["tet4-linear-static"]
    assert tet4_static["criteria_status"] == "PASS"
    assert tet4_static["blocking_criteria"] == []
    assert tet4_static["current_status"] == "stable"
    assert tet4_static["promotion_gate"] == "NO_PROMOTION_REQUIRED"


def test_optional_out_of_scope_probe_does_not_block_stable_subscope() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    rows = {row["scope"]: row for row in report["scopes"]}

    for scope in ("mitc4-laminate-static",):
        row = rows[scope]
        assert row["criteria_status"] == "PASS"
        assert row["blocking_criteria"] == []
        assert row["stable_error_violations"] == []
        assert row["current_status"] == "stable"
        assert row["promotion_gate"] == "NO_PROMOTION_REQUIRED"


def test_mitc4_transient_uses_temporal_primary_observable() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    row = next(item for item in report["scopes"] if item["scope"] == "mitc4-transient-dynamic")

    assert row["criteria_status"] == "PASS"
    assert row["blocking_criteria"] == []
    assert row["stable_error_violations"] == []
    assert row["current_status"] == "stable"
    assert row["promotion_gate"] == "NO_PROMOTION_REQUIRED"


def test_mitc4_modal_is_ready_after_modal_refinement() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    row = next(item for item in report["scopes"] if item["scope"] == "mitc4-modal")

    assert row["criteria_status"] == "PASS"
    assert row["blocking_criteria"] == []
    assert row["stable_error_violations"] == []
    assert row["current_status"] == "stable"
    assert row["promotion_gate"] == "NO_PROMOTION_REQUIRED"


def test_tet10_dynamic_scopes_expose_complete_external_proof() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    rows = {row["scope"]: row for row in report["scopes"]}

    for scope in ("tet10-modal", "tet10-transient-dynamic", "tet10-harmonic-response"):
        assert rows[scope]["criteria_status"] == "PASS"
        assert rows[scope]["blocking_criteria"] == []
        assert rows[scope]["current_status"] == "stable"
        assert rows[scope]["promotion_gate"] == "NO_PROMOTION_REQUIRED"


def test_mitc4_static_is_ready_after_external_correlation() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    row = next(item for item in report["scopes"] if item["scope"] == "mitc4-linear-static")

    assert row["template_criteria_status"] == "STRUCTURED"
    assert row["criteria_status"] == "PASS"
    assert row["blocking_criteria"] == []
    assert row["current_status"] == "stable"
    assert row["promotion_gate"] == "NO_PROMOTION_REQUIRED"


def test_mitc4_laminate_dynamic_refined_scope_is_ready_without_hiding_reservation() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    row = next(
        item
        for item in report["scopes"]
        if item["scope"] == "mitc4-laminate-dynamic-refined-three-layups"
    )
    criteria = {criterion["id"]: criterion for criterion in row["criteria"]}

    assert row["template_criteria_status"] == "STRUCTURED"
    assert row["criteria_status"] == "PASS"
    assert row["blocking_criteria"] == []
    assert row["promotion_gate"] == "NO_PROMOTION_REQUIRED"
    assert row["maturity_target"] == "stable"
    assert criteria["MITC4-LAM-DYN-REF-C01"]["status"] == "PASS"


def test_nonstable_promotion_is_blocked_when_required_criteria_fail() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    rows = {item["scope"]: item for item in report["scopes"]}

    assert rows["mitc3-laminate-static-curved"]["promotion_gate"] == "BLOCKED_CRITERIA_FAILED"
    assert rows["mitc3-laminate-static-curved"]["blocking_criteria"]
    assert rows["mitc3-laminate-dynamic"]["promotion_gate"] == "BLOCKED_CRITERIA_FAILED"
    assert rows["mitc3-laminate-dynamic"]["blocking_criteria"]


def test_mitc3_curved_load_family_campaign_is_complete() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    row = next(item for item in report["scopes"] if item["scope"] == "mitc3-laminate-static-curved")
    criteria = {criterion["id"]: criterion for criterion in row["criteria"]}

    assert criteria["MITC3-LAM-STAT-C03"]["status"] == "FAIL"
    assert row["path_integrity"] == "PASS"


def test_mitc3_curved_three_load_campaign_is_traceable_and_blocks_only_convergence() -> None:
    evidence = json.loads(
        (ROOT / "qualification" / "maturity_evidence_0_2_1" / "mitc3_laminate.json").read_text(encoding="utf-8")
    )["scopes"]["mitc3-laminate-static-curved"]["strict_extended_campaign_3loads"]

    assert evidence["load_family_count"] == 3
    assert max(
        evidence["mixed_fine_vector_difference"],
        evidence["transverse_fine_vector_difference"],
        evidence["axial_fine_vector_difference"],
    ) <= 0.01
    assert evidence["axial_final_mesh_increment_max"] > 0.05


def test_supplementary_scopes_report_their_criteria_evidence_paths() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    row = next(item for item in report["scopes"] if item["scope"] == "orthotropic-solid-modal")

    assert row["evidence_paths"]
    assert row["path_integrity"] == "PASS"


def test_orthotropic_promotion_keeps_static_technical_pass_and_dynamic_owner_gates() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    rows = {item["scope"]: item for item in report["scopes"]}

    static = rows["orthotropic-solid-tet4-tet10"]
    assert static["criteria_status"] == "PASS"
    assert static["blocking_criteria"] == []
    assert static["promotion_gate"] == "READY_FOR_OWNER_REVIEW"

    modal = rows["orthotropic-solid-modal"]
    assert modal["criteria_status"] == "PASS"
    assert modal["blocking_criteria"] == []
    assert modal["promotion_gate"] == "READY_FOR_OWNER_REVIEW"

    transient = rows["orthotropic-solid-transient-dynamic"]
    assert transient["criteria_status"] == "PASS"
    assert transient["blocking_criteria"] == []
    assert transient["promotion_gate"] == "READY_FOR_OWNER_REVIEW"


def test_frictional_contact_keeps_owner_gate_after_internal_campaign() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    row = next(item for item in report["scopes"] if item["scope"] == "contact-frictional-static")
    criteria = {criterion["id"]: criterion for criterion in row["criteria"]}

    assert row["criteria_status"] == "PASS"
    assert row["blocking_criteria"] == []
    assert row["promotion_gate"] == "READY_FOR_RELEASE_ACTION"
    assert criteria["CONTACT-FRIC-C01"]["status"] == "PASS"
    assert any(
        assertion.get("path") == "campaign.case_count"
        and assertion.get("expected") == 3
        for assertion in criteria["CONTACT-FRIC-C01"]["assertions"]
    )
    assert criteria["CONTACT-FRIC-C02"]["status"] == "PASS"
    assert criteria["CONTACT-FRIC-C03"]["status"] == "PASS"
    assert criteria["CONTACT-FRIC-C04"]["status"] == "PASS"


def test_bounded_contact_scope_is_structured_without_changing_its_status() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    row = next(
        item for item in report["scopes"] if item["scope"] == "contact-v1-linear-static-bounded"
    )

    assert row["template_criteria_status"] == "STRUCTURED"
    assert row["criteria_status"] == "PASS"
    assert row["current_status"] == "owner_accepted"
    assert row["target_status"] == "owner_accepted"
    assert row["promotion_gate"] == "NO_PROMOTION_REQUIRED"
    assert row["path_integrity"] == "PASS"


def test_mitc3_laminate_static_exposes_missing_dedicated_ledger() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    row = next(item for item in report["scopes"] if item["scope"] == "mitc3-laminate-static")

    assert row["template_criteria_status"] == "STRUCTURED"
    assert row["criteria_status"] == "PASS"
    assert row["blocking_criteria"] == []
    assert row["promotion_gate"] == "READY_FOR_RELEASE_ACTION"
    assert row["path_integrity"] == "PASS"
    criteria = {criterion["id"]: criterion for criterion in row["criteria"]}
    assert criteria["MITC3-LAM-STAT-C01"]["status"] == "PASS"
    assert criteria["MITC3-LAM-STAT-C02"]["status"] == "PASS"


def test_large_tet4_promotion_preserves_scaling_warning_and_owner_gate() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    row = next(item for item in report["scopes"] if item["scope"] == "large-tet4-linear-static")
    criteria = {criterion["id"]: criterion for criterion in row["criteria"]}

    assert row["criteria_status"] == "PASS"
    assert row["blocking_criteria"] == []
    assert row["promotion_gate"] == "READY_FOR_RELEASE_ACTION"
    assert row["path_integrity"] == "PASS"
    assert all(criteria[key]["status"] == "PASS" for key in (
        "LARGE-TET4-C01",
        "LARGE-TET4-C02",
        "LARGE-TET4-C03",
        "LARGE-TET4-C04",
    ))


def test_p1_dynamic_scopes_keep_archived_mitc3_refinement_after_promotion() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    rows = {item["scope"]: item for item in report["scopes"]}

    assert rows["mitc3-linear-static"]["current_status"] == "stable"
    assert rows["mitc3-linear-static"]["promotion_gate"] == "NO_PROMOTION_REQUIRED"
    for scope, criterion_id in (
        ("mitc3-modal", "MITC3-MOD-C04"),
        ("mitc3-transient-dynamic", "MITC3-NEW-C04"),
        ("mitc3-harmonic-response", "MITC3-HAR-C04"),
    ):
        assert rows[scope]["criteria_status"] == "PASS"
        assert rows[scope]["blocking_criteria"] == []
        assert rows[scope]["current_status"] == "stable"
        assert rows[scope]["promotion_gate"] == "NO_PROMOTION_REQUIRED"
        assert rows[scope]["owner_review"] == "ACCEPTED"
        assert rows[scope]["criteria"][0]["status"] == "PASS"

    assert rows["beam2-linear-dynamics"]["criteria_status"] == "PASS"
    assert rows["discrete-linear-dynamics"]["criteria_status"] == "PASS"


def test_beam2_static_owner_promotion_is_recorded() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    row = next(item for item in report["scopes"] if item["scope"] == "beam2-linear-static")

    assert row["criteria_status"] == "PASS"
    assert row["blocking_criteria"] == []
    assert row["promotion_gate"] == "NO_PROMOTION_REQUIRED"
    criteria = {criterion["id"]: criterion for criterion in row["criteria"]}
    assert criteria["BEAM2-LS-C02"]["status"] == "PASS"
    assert criteria["BEAM2-LS-C04"]["status"] == "PASS"


def test_mitc4_laminate_static_uses_tracked_external_evidence() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    row = next(item for item in report["scopes"] if item["scope"] == "mitc4-laminate-static")

    assert row["criteria_status"] == "PASS"
    assert row["blocking_criteria"] == []
    assert row["stable_error_violations"] == []
    assert row["criteria_status"] == "PASS"
    assert row["current_status"] == "stable"
    assert row["promotion_gate"] == "NO_PROMOTION_REQUIRED"
    assert row["path_integrity"] == "PASS"
    refined = next(item for item in row["criteria"] if item["id"] == "MITC4-LAM-STAT-C02B")
    assert refined["status"] == "FAIL"
    assert refined["required"] is False


def test_mitc3_laminate_dynamic_refinement_closes_only_the_mesh_gap() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    row = next(item for item in report["scopes"] if item["scope"] == "mitc3-laminate-dynamic")
    criteria = {criterion["id"]: criterion for criterion in row["criteria"]}

    assert criteria["MITC3-LAM-DYN-C03"]["status"] == "PASS"
    assert criteria["MITC3-LAM-DYN-C04"]["status"] == "PASS"
    assert row["blocking_criteria"] == ["MITC3-LAM-DYN-C01"]
    assert "MITC3-LAM-DYN-C09" not in criteria
    assert row["promotion_gate"] == "BLOCKED_CRITERIA_FAILED"
    assert row["path_integrity"] == "PASS"


def test_total_lagrangian_keeps_independent_audit_as_a_hard_gate() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    row = next(
        item for item in report["scopes"] if item["scope"] == "tet4-total-lagrangian-structural-v2"
    )
    criteria = {criterion["id"]: criterion for criterion in row["criteria"]}

    assert row["criteria_status"] == "BLOCKED"
    assert row["blocking_criteria"] == ["TET4-TL-C04"]
    assert row["promotion_gate"] == "BLOCKED_OWNER_REVIEW"
    assert all(criteria[key]["status"] == "PASS" for key in (
        "TET4-TL-C01",
        "TET4-TL-C01B",
        "TET4-TL-C02",
        "TET4-TL-C03",
    ))


def test_tet4_j2_uses_code_aster_reference_and_keeps_owner_gate() -> None:
    report = MaturityPromotionAuditor(ROOT).audit()
    row = next(item for item in report["scopes"] if item["scope"] == "tet4-material-nonlinear")
    criteria = {criterion["id"]: criterion for criterion in row["criteria"]}

    assert row["criteria_status"] == "PASS"
    assert row["blocking_criteria"] == []
    assert row["promotion_gate"] == "READY_FOR_RELEASE_ACTION"
    assert row["path_integrity"] == "PASS"
    assert criteria["TET4-J2-C01"]["status"] == "PASS"
    assert criteria["TET4-J2-C02"]["status"] == "PASS"
    assert criteria["TET4-J2-C03"]["status"] == "PASS"
    assert criteria["TET4-J2-C04"]["status"] == "PASS"

pytestmark = pytest.mark.evidence
