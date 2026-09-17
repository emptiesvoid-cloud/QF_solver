"""Focused fail-closed policy tests for the WP07-E R2 closure checker."""

from __future__ import annotations

import math

from scripts.verify_wp07e_closure_r2 import (
    _expected_negative_cases,
    _finite,
    _production_case_pass,
    _reference_case_pass,
    _status_from_checks,
)


def test_wp07e_missing_evidence_holds() -> None:
    status, gate = _status_from_checks(
        missing=["case"],
        hash_mismatches=[],
        provenance_failures=[],
        negative_failures=[],
    )
    assert (status, gate) == ("HOLD", "WP07_INCOMPLETE_EVIDENCE")


def test_wp07e_hash_or_provenance_mismatch_fails_closed() -> None:
    for kwargs in (
        {"hash_mismatches": ["artifact"]},
        {"provenance_failures": ["source SHA"]},
    ):
        status, gate = _status_from_checks(
            missing=[],
            hash_mismatches=kwargs.get("hash_mismatches", []),
            provenance_failures=kwargs.get("provenance_failures", []),
            negative_failures=[],
        )
        assert (status, gate) == ("FAIL_CLOSED", "WP07_INCOMPLETE_EVIDENCE")


def test_wp07e_wrong_negative_outcome_fails() -> None:
    status, gate = _status_from_checks(
        missing=[],
        hash_mismatches=[],
        provenance_failures=[],
        negative_failures=["reversed_orientation"],
    )
    assert (status, gate) == ("FAIL", "WP07_FAIL_IDENTITY")


def test_wp07e_pass_is_candidate_only() -> None:
    assert _status_from_checks(
        missing=[],
        hash_mismatches=[],
        provenance_failures=[],
        negative_failures=[],
    ) == ("PASS_CANDIDATE", "WP07_PASS_BOUNDED")


def test_wp07e_nonfinite_values_are_rejected_recursively() -> None:
    assert not _finite({"nested": [1.0, {"observable": math.nan}]})
    assert not _finite({"observable": math.inf})
    assert _finite({"observable": 0.0, "note": "finite"})


def test_wp07e_contract_requires_exact_six_negative_cases() -> None:
    cases = _expected_negative_cases(
        {
            "negative_case_policy": [
                {"case": "reversed_orientation", "accepted_classifications": ["VALIDATION_FAILURE"]},
                {"case": "open_no_contact", "accepted_classifications": ["PASS_OPEN_NO_CONTACT"]},
                {"case": "excessive_penetration", "accepted_classifications": ["CONTACT_PENETRATION_EXCESSIVE", "ROUTE_NATIVE_FAILURE"]},
                {"case": "unsupported_combination", "accepted_classifications": ["UNSUPPORTED_EXPLICIT"]},
                {"case": "nonfinite_observable", "accepted_classifications": ["EVIDENCE_VALIDATION_FAILURE"]},
                {"case": "incompatible_restart_metadata", "accepted_classifications": ["RESTART_METADATA_MISMATCH"]},
            ]
        }
    )
    assert set(cases) == {
        "reversed_orientation",
        "open_no_contact",
        "excessive_penetration",
        "unsupported_combination",
        "nonfinite_observable",
        "incompatible_restart_metadata",
    }


def test_wp07d_accepted_penalty_status_encoding_is_not_misclassified() -> None:
    case = {
        "status": "PASS",
        "production_status": "success",
        "production_run_status": "COMPLETED",
        "reference_status": "PASS",
        "reference_run_status": "COMPLETED",
    }
    assert _production_case_pass(case)
    assert _reference_case_pass(case)
    assert not _production_case_pass({**case, "production_status": "failed"})
