import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ACCEPTED_REVIEW = (
    ROOT / "qualification" / "reviews" / "mitc4_harmonic_response_2026-07-15.json"
)


def test_mitc4_harmonic_stale_pending_review_is_removed() -> None:
    stale = ROOT / "qualification" / "reviews" / "mitc4_harmonic_response_pending.json"
    assert not stale.exists()
    assert ACCEPTED_REVIEW.is_file()


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
