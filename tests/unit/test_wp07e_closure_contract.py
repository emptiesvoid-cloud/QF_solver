"""Synthetic fail-closed tests for the prospective WP07-E closure evaluator."""

from __future__ import annotations

import copy
from typing import Any

from scripts.build_wp07e_closure import (
    ACTIVE_SET_ID,
    CONTRACT_PATH,
    PENALTY_ID,
    evaluate_closure,
    load_contract,
    validate_contract,
)


RUNTIME_ID = "QF-029-WP07-D-STRUCTURAL-EVIDENCE-001"
ACTIVE_REFERENCE_ID = "QF-029-WP07-D-REFERENCE-ACTIVE-SET-001"
PENALTY_REFERENCE_ID = "QF-029-WP07-D-REFERENCE-PENALTY-001"


def _required_defaults(spec: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": 1,
        "gate": "WP07",
        "work_package": "WP07-D" if spec["role"] != "contract" else "WP07-A",
        "revision": "test",
        "status": "EXECUTED" if spec["role"] == "runtime" else "COMPLETE",
        "source_sha": "test-source-sha",
        "qualification_campaign_executed": spec["role"] == "runtime",
    }
    if spec["role"] == "contract":
        record["status"] = "PREPARATION_ONLY"
        record["qualification_campaign_executed"] = False
    if spec["id"] == "WP07A-CONTACT-FORMULATION-001":
        record["contract_id"] = spec["id"]
        record["work_package"] = "WP07-A"
    else:
        record["artifact_id"] = spec["id"]
    for field in spec["required_fields"]:
        record.setdefault(field, {})
    if spec["role"] in {"runtime", "independent_reference"}:
        record["provenance"] = {
            "source_sha": "test-source-sha",
            "case_definition_digest": "test-case-digest",
            "command": "synthetic",
            "environment": {"python": "test"},
        }
    if spec["role"] == "runtime":
        record["execution_policy"] = {
            "governing_policy_sha": "governing-policy-sha",
            "newton_convergence_contract": "owner-policy",
            "floor_aware_convergence_if_approved": "not-approved-in-preparation",
            "linear_backend": "DIRECT",
            "line_search_policy": "governing-policy",
            "load_step_retry_policy": "governing-policy",
        }
        record["negative_cases"] = [
            {"case": "reversed_orientation", "classification": "VALIDATION_FAILURE"},
            {"case": "open_no_contact", "classification": "PASS_OPEN_NO_CONTACT"},
            {"case": "excessive_penetration", "classification": "CONTACT_PENETRATION_EXCESSIVE"},
            {"case": "unsupported_combination", "classification": "UNSUPPORTED_EXPLICIT"},
            {"case": "nonfinite_observable", "classification": "EVIDENCE_VALIDATION_FAILURE"},
            {"case": "incompatible_restart_metadata", "classification": "RESTART_METADATA_MISMATCH"},
        ]
    if spec["role"] == "independent_reference":
        record["independent_implementation"] = True
        record["production_contact_routines_called"] = False
        record["formulation_match"] = True
        record["track"] = ACTIVE_SET_ID if spec["id"] == ACTIVE_REFERENCE_ID else PENALTY_ID
        record["results"] = {"reference_check": "PASS"}
    return record


def _complete_evidence() -> dict[str, dict[str, Any]]:
    contract = load_contract(CONTRACT_PATH)
    evidence: dict[str, dict[str, Any]] = {}
    for spec in contract["required_evidence"]["artifacts"]:
        evidence[spec["id"]] = _required_defaults(spec)
    evidence[RUNTIME_ID]["track_evidence"] = {}
    for track_id in (ACTIVE_SET_ID, PENALTY_ID):
        track = contract["track_separation"][track_id]
        evidence[RUNTIME_ID]["track_evidence"][track_id] = {
            "formulation": track["formulation"],
            "governing_execution_policy_match": True,
            "checks": {check: "PASS" for check in track["required_checks"]},
            "results": {"representative_metric": 1.0},
        }
    return evidence


def _set_check(evidence: dict[str, dict[str, Any]], track_id: str, check: str, status: str) -> None:
    evidence[RUNTIME_ID]["track_evidence"][track_id]["checks"][check] = status


def test_contract_is_machine_readable_and_preparation_only() -> None:
    contract = load_contract()

    assert validate_contract(contract) == []
    assert contract["status"] == "PREPARATION_ONLY"
    assert contract["qualification_campaign_executed"] is False
    assert contract["integration_train_required"] is True
    assert contract["decision_matrix"]["precedence_high_to_low"][0] == "WP07_INCOMPLETE_EVIDENCE"


def test_all_supplied_gates_close_only_with_complete_evidence() -> None:
    report = evaluate_closure(_complete_evidence())

    assert report["status"] == "WP07_PASS_BOUNDED"
    assert report["fabricated_data"] is False
    assert report["missing_artifacts"] == []


def test_missing_artifact_is_incomplete_not_pass() -> None:
    evidence = _complete_evidence()
    del evidence[PENALTY_REFERENCE_ID]

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_INCOMPLETE_EVIDENCE"
    assert PENALTY_REFERENCE_ID in report["missing_artifacts"]


def test_identity_failure_has_fail_closed_precedence() -> None:
    evidence = _complete_evidence()
    _set_check(evidence, ACTIVE_SET_ID, "complementarity", "FAIL")
    _set_check(evidence, PENALTY_ID, "equilibrium_force", "FAIL")

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_FAIL_IDENTITY"


def test_equilibrium_failure_is_not_downgraded_to_limitation() -> None:
    evidence = _complete_evidence()
    _set_check(evidence, PENALTY_ID, "equilibrium_moment", "FAIL")

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_FAIL_EQUILIBRIUM"


def test_replay_failure_holds_closure() -> None:
    evidence = _complete_evidence()
    _set_check(evidence, ACTIVE_SET_ID, "replay", "FAIL")

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_HOLD_REPLAY"


def test_refinement_failure_holds_structural_closure() -> None:
    evidence = _complete_evidence()
    _set_check(evidence, PENALTY_ID, "refinement", "FAIL")

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_HOLD_STRUCTURAL_CONVERGENCE"


def test_incompatible_reference_holds_reference_gate() -> None:
    evidence = _complete_evidence()
    evidence[ACTIVE_REFERENCE_ID]["formulation_match"] = False

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_HOLD_REFERENCE"


def test_explicitly_not_covered_track_produces_bounded_partial_status() -> None:
    evidence = _complete_evidence()
    evidence[RUNTIME_ID]["track_evidence"][PENALTY_ID] = {
        "track_status": "NOT_COVERED",
        "reason": "Penalty structural campaign is outside this bounded claim.",
    }

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_PARTIAL_ACTIVE_SET_ONLY"


def test_nonfinite_evidence_is_rejected_before_any_pass() -> None:
    evidence = _complete_evidence()
    evidence[RUNTIME_ID]["track_evidence"][PENALTY_ID]["results"]["bad"] = float("nan")

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_INCOMPLETE_EVIDENCE"
    assert report["malformed_evidence"]


def test_updated_search_is_excluded_from_closure() -> None:
    evidence = _complete_evidence()
    evidence[RUNTIME_ID]["track_evidence"][PENALTY_ID]["updated_search"] = True

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_INCOMPLETE_EVIDENCE"


def test_missing_and_identity_failure_keep_incomplete_precedence() -> None:
    evidence = _complete_evidence()
    del evidence[ACTIVE_REFERENCE_ID]
    _set_check(evidence, PENALTY_ID, "tangent_fd", "FAIL")

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_INCOMPLETE_EVIDENCE"


def test_invalid_not_applicable_without_reason_is_incomplete() -> None:
    evidence = _complete_evidence()
    _set_check(evidence, ACTIVE_SET_ID, "open_zero_force", {"status": "NOT_APPLICABLE"})  # type: ignore[arg-type]

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_INCOMPLETE_EVIDENCE"


def test_report_is_deterministic_for_same_evidence() -> None:
    evidence = _complete_evidence()

    first = evaluate_closure(copy.deepcopy(evidence))
    second = evaluate_closure(copy.deepcopy(evidence))

    assert first == second
