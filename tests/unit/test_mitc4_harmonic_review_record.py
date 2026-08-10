import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "qualification" / "reviews" / "mitc4_harmonic_response_pending.json"
ACCEPTED_REVIEW = (
    ROOT / "qualification" / "reviews" / "mitc4_harmonic_response_2026-07-15.json"
)


def test_mitc4_harmonic_pending_review_points_to_signed_record() -> None:
    data = json.loads(REVIEW.read_text(encoding="utf-8"))

    assert data["scope"] == "mitc4-harmonic-response"
    assert data["technical_status"] == "superseded_by_signed_review"
    assert data["decision"] == "superseded_by_signed_review"
    assert data["decision_date"] is None
    assert data["signature"] is None
    assert data["superseded_by"].endswith("mitc4_harmonic_response_2026-07-15.json")
    assert data["review_mode"] == "self_review"
    assert data["independence"] == "not_independent"
    assert set(data["evidence"]) == {
        "VNV-MITC4-HARMONIC-MODAL-001",
        "VNV-MITC4-HARMONIC-CONDENSATION-002",
        "VNV-MITC4-HARMONIC-BROADBAND-003",
        "VNV-MITC4-HARMONIC-NAFEMS13H-004",
    }


def test_mitc4_harmonic_review_evidence_has_executable_tests() -> None:
    expected_tests = (
        "test_mitc4_harmonic_vnv.py",
        "test_mitc4_harmonic_condensation_vnv.py",
        "test_mitc4_harmonic_broadband_vnv.py",
        "test_mitc4_harmonic_nafems_vnv.py",
    )
    for name in expected_tests:
        assert (ROOT / "tests" / "verification" / name).is_file()


def test_mitc4_harmonic_review_records_acceptance_with_recommendations() -> None:
    data = json.loads(ACCEPTED_REVIEW.read_text(encoding="utf-8"))

    assert data["scope"] == "mitc4-harmonic-response"
    assert data["decision"] == "accepted_with_recommendations"
    assert data["decision_date"] == "2026-07-15"
    assert data["validator"]["name"] == "Quentin Farinazzo"
    assert data["review_mode"] == "self_review"
    assert data["independence"] == "not_independent"
    assert data["certification_claim"] == "none"
    recommendations = {item["id"]: item["status"] for item in data["recommendations"]}
    assert recommendations["REC-MITC4-HAR-001"] == "implemented_pending_mechanical_recheck"
    assert (
        recommendations["REC-MITC4-HAR-002"]
        == "completed_calculix_warning_code_aster_pass"
    )
