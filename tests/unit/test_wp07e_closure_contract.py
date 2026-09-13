"""R1 synthetic raw-evidence tests for the fail-closed WP07-E builder."""

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
CASE_DIGEST = "case-digest"
CONTRACT_DIGEST = "WP07E_CONTRACT_DIGEST_PENDING_INTEGRATION"


def _required_defaults(spec: dict[str, Any]) -> dict[str, Any]:
    role = spec["role"]
    record: dict[str, Any] = {
        "schema_version": 1,
        "gate": "WP07",
        "work_package": "WP07-D" if role != "contract" else "WP07-A",
        "revision": "test",
        "status": "EXECUTED" if role == "runtime" else "COMPLETE",
        "source_sha": f"{spec['id']}-source-sha",
        "qualification_campaign_executed": role == "runtime",
    }
    if role == "contract":
        record["status"] = "PREPARATION_ONLY"
    if spec["id"] == "WP07A-CONTACT-FORMULATION-001":
        record["contract_id"] = spec["id"]
        record["work_package"] = "WP07-A"
    else:
        record["artifact_id"] = spec["id"]
    for field in spec["required_fields"]:
        record.setdefault(field, {})
    if role in {"runtime", "independent_reference"}:
        record["provenance"] = {
            "integrated_source_sha": "integrated-sha",
            "case_definition_digest": CASE_DIGEST,
            "contract_revision": "R1",
            "contract_digest": CONTRACT_DIGEST,
            "environment": {"python": "test"},
        }
    if role == "runtime":
        record["execution_policy"] = {}
        record["negative_cases"] = []
    if role == "independent_reference":
        record["independent_implementation"] = True
        record["production_contact_routines_called"] = False
        record["formulation_match"] = True
        record["track"] = ACTIVE_SET_ID if spec["id"] == ACTIVE_REFERENCE_ID else PENALTY_ID
        record["provenance"]["reference_implementation_sha"] = f"{spec['id']}-implementation-sha"
        record["reported_status"] = "PASS"
        record["raw_comparisons"] = {}
    return record


def _structural_levels(track_id: str) -> dict[str, dict[str, Any]]:
    common = {
        "case_definition_digest": CASE_DIGEST,
        "support_reaction_vector": [0.0, 0.0, 10.0],
        "reaction_moment_vector": [0.0, 0.0, 2.0],
        "contact_resultant_vector": [0.0, 0.0, 5.0],
        "scales": {
            "U_char": 1.0,
            "F_char": 10.0,
            "M_char": 2.0,
            "penetration_scale": 1.0,
            "E_char": 10.0,
        },
    }
    m2 = {**copy.deepcopy(common), "selected_displacement": 1.0}
    m3 = {**copy.deepcopy(common), "selected_displacement": 1.005}
    if track_id == ACTIVE_SET_ID:
        m2["contact_region_measure"] = 1.0
        m3["contact_region_measure"] = 1.005
    else:
        m2.update(
            {
                "maximum_penetration": 0.01,
                "contact_energy": 1.0,
                "contact_energy_applicable": True,
            }
        )
        m3.update(
            {
                "maximum_penetration": 0.0101,
                "contact_energy": 1.005,
                "contact_energy_applicable": True,
            }
        )
    return {"M2": m2, "M3": m3}


def _replay_run() -> dict[str, Any]:
    return {
        "final_displacement": 0.5,
        "reaction_vector": [0.0, 0.0, 10.0],
        "moment_vector": [0.0, 0.0, 2.0],
        "contact_resultant": [0.0, 0.0, 5.0],
        "active_contact_qualitative_status": "CLOSED",
        "active_contact_count": 2,
        "load_factor_history": [0.5, 1.0],
        "terminal_classification": "CONVERGED",
        "newton_iteration_counts": [2, 3],
    }


def _track_entry(track_id: str) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "formulation": (
            "LINEAR_ACTIVE_SET_INITIAL_SEARCH"
            if track_id == ACTIVE_SET_ID
            else "NONLINEAR_PENALTY_INITIAL_SEARCH"
        ),
        "reported_status": "PASS",
        "structural_levels": _structural_levels(track_id),
        "equilibrium": {
            "support_reaction_vector": [0.0, 0.0, 10.0],
            "external_force_vector": [0.0, 0.0, -10.0],
            "reaction_moment_vector": [0.0, 0.0, 2.0],
            "external_moment_vector": [0.0, 0.0, -2.0],
            "F_char": 10.0,
            "M_char": 2.0,
        },
        "replay": {"run_a": _replay_run(), "run_b": _replay_run()},
    }
    if track_id == ACTIVE_SET_ID:
        entry["identity"] = {
            "open_contact_force_vector": [0.0, 0.0, 0.0],
            "closed_gap": 1.0e-12,
            "pressure": 1.0,
            "L_char": 1.0,
            "F_char": 10.0,
            "P_char": 1.0,
        }
    else:
        entry["identity"] = {
            "energy_gradient_error": 1.0e-10,
            "tangent_frobenius_error": 1.0e-10,
            "tangent_max_column_error": 1.0e-10,
            "tangent_symmetry_error": 0.0,
            "open_contact_force_vector": [0.0, 0.0, 0.0],
            "open_force_scale": 10.0,
            "reopen_ghost_force_vector": [0.0, 0.0, 0.0],
            "reopen_force_scale": 10.0,
        }
        entry["rollback"] = {
            "state_before_digest": "state-0",
            "trial_state_digest": "state-1",
            "state_after_reject_digest": "state-0",
        }
        entry["load_path"] = {"step_statuses": ["ACCEPTED", "ACCEPTED"]}
        entry["replay"]["run_a"].update(
            {
                "contact_topology_digest": "contact-digest",
                "model_signature": "model-signature",
                "accepted_state_digest": "accepted-digest",
            }
        )
        entry["replay"]["run_b"].update(
            {
                "contact_topology_digest": "contact-digest",
                "model_signature": "model-signature",
                "accepted_state_digest": "accepted-digest",
            }
        )
    return entry


def _reference_record(track_id: str, record: dict[str, Any]) -> None:
    record["track"] = track_id
    record["raw_comparisons"] = {
        "selected_displacement": {"qf": 0.5, "reference": 0.501, "scale": 1.0},
        "reaction_resultant": {"qf": [0.0, 0.0, 10.0], "reference": [0.0, 0.0, 10.1], "scale": 10.0},
        "reaction_moment": {"qf": [0.0, 0.0, 2.0], "reference": [0.0, 0.0, 2.01], "scale": 2.0},
        "contact_resultant": {"qf": [0.0, 0.0, 5.0], "reference": [0.0, 0.0, 5.1], "scale": 5.0},
    }
    if track_id == ACTIVE_SET_ID:
        record["raw_comparisons"]["contact_region_measure"] = {
            "qf": 1.0,
            "reference": 1.01,
            "scale": 1.0,
        }
    else:
        record["raw_comparisons"]["penetration"] = {
            "qf": 0.1,
            "reference": 0.101,
            "scale": 1.0,
        }


def _complete_evidence() -> dict[str, dict[str, Any]]:
    contract = load_contract(CONTRACT_PATH)
    evidence: dict[str, dict[str, Any]] = {
        spec["id"]: _required_defaults(spec)
        for spec in contract["required_evidence"]["artifacts"]
    }
    evidence[RUNTIME_ID].update(
        {
            "provenance": {
                "integrated_source_sha": "integrated-sha",
                "case_definition_digest": CASE_DIGEST,
                "contract_revision": "R1",
                "contract_digest": CONTRACT_DIGEST,
                "environment": {"python": "test"},
            },
            "execution_policy": copy.deepcopy(contract["governing_execution_policy"]["expected"]),
            "governing_execution_policy_match": True,
            "negative_cases": [
                {"case": "reversed_orientation", "observed_classification": "VALIDATION_FAILURE"},
                {"case": "open_no_contact", "observed_classification": "PASS_OPEN_NO_CONTACT"},
                {"case": "excessive_penetration", "observed_classification": "CONTACT_PENETRATION_EXCESSIVE"},
                {"case": "unsupported_combination", "observed_classification": "UNSUPPORTED_EXPLICIT"},
                {"case": "nonfinite_observable", "observed_classification": "EVIDENCE_VALIDATION_FAILURE"},
                {"case": "incompatible_restart_metadata", "observed_classification": "RESTART_METADATA_MISMATCH"},
            ],
            "track_evidence": {
                ACTIVE_SET_ID: _track_entry(ACTIVE_SET_ID),
                PENALTY_ID: _track_entry(PENALTY_ID),
            },
        }
    )
    evidence["QF-029-WP07-C-CONTACT-IDENTITIES-001"]["observed_results"] = {
        "penalty_energy_gradient_relative_error": 1.5192447540399686e-10,
        "penalty_tangent_frobenius_relative_error": 1.5743360213643872e-11,
        "penalty_tangent_max_column_relative_error": 3.274180926489745e-11,
        "penalty_tangent_symmetry_relative_error": 0.0,
        "penalty_open_force_normalized": 0.0,
    }
    for track_id, reference_id in (
        (ACTIVE_SET_ID, ACTIVE_REFERENCE_ID),
        (PENALTY_ID, PENALTY_REFERENCE_ID),
    ):
        _reference_record(track_id, evidence[reference_id])
        evidence[reference_id]["provenance"] = {
            "integrated_source_sha": "integrated-sha",
            "case_definition_digest": CASE_DIGEST,
            "contract_revision": "R1",
            "contract_digest": CONTRACT_DIGEST,
            "environment": {"python": "test"},
            "reference_implementation_sha": f"{track_id}-reference-sha",
        }
    return evidence


def test_r1_contract_is_machine_readable_and_preparation_only() -> None:
    contract = load_contract()

    assert validate_contract(contract) == []
    assert contract["owner_correction"] == "OWNER_CORRECTION_R1"
    assert contract["status"] == "PREPARATION_ONLY"
    assert contract["qualification_campaign_executed"] is False
    assert contract["identity_thresholds"][PENALTY_ID]["tangent_max_column"] == 5.0e-6


def test_r1_01_valid_raw_values_close_bounded() -> None:
    report = evaluate_closure(_complete_evidence())

    assert report["status"] == "WP07_PASS_BOUNDED"
    assert report["fabricated_data"] is False
    assert report["missing_artifacts"] == []
    assert report["status_mismatches"] == []
    assert report["tracks"][ACTIVE_SET_ID]["gates"]["refinement"]["derived_status"] == "PASS"
    assert report["tracks"][PENALTY_ID]["gates"]["tangent_fd"]["derived_status"] == "PASS"


def test_r1_02_reported_pass_cannot_hide_refinement_failure() -> None:
    evidence = _complete_evidence()
    evidence[RUNTIME_ID]["track_evidence"][ACTIVE_SET_ID]["structural_levels"]["M3"]["selected_displacement"] = 2.0

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_HOLD_STRUCTURAL_CONVERGENCE"
    assert report["tracks"][ACTIVE_SET_ID]["reported_status"] == "PASS"
    assert report["tracks"][ACTIVE_SET_ID]["gates"]["selected_displacement"]["derived_status"] == "FAIL"


def test_r1_03_reported_pass_cannot_hide_vector_equilibrium_failure() -> None:
    evidence = _complete_evidence()
    evidence[RUNTIME_ID]["track_evidence"][PENALTY_ID]["equilibrium"]["external_force_vector"] = [1.0, 0.0, -10.0]

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_FAIL_EQUILIBRIUM"
    assert report["tracks"][PENALTY_ID]["gates"]["equilibrium_force"]["derived_status"] == "FAIL"


def test_r1_04_reported_pass_cannot_hide_replay_mismatch() -> None:
    evidence = _complete_evidence()
    evidence[RUNTIME_ID]["track_evidence"][ACTIVE_SET_ID]["replay"]["run_b"]["final_displacement"] = 0.6

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_HOLD_REPLAY"
    assert report["tracks"][ACTIVE_SET_ID]["gates"]["replay"]["derived_status"] == "FAIL"


def test_r1_05_reported_reference_pass_cannot_hide_raw_mismatch() -> None:
    evidence = _complete_evidence()
    evidence[ACTIVE_REFERENCE_ID]["raw_comparisons"]["selected_displacement"]["reference"] = 2.0

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_HOLD_REFERENCE"
    assert report["tracks"][ACTIVE_SET_ID]["gates"]["reference"]["derived_status"] == "FAIL"


def test_r1_06_wrong_negative_classification_fails_identity() -> None:
    evidence = _complete_evidence()
    evidence[RUNTIME_ID]["negative_cases"][0]["observed_classification"] = "PASS"

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_FAIL_IDENTITY"
    assert report["tracks"][ACTIVE_SET_ID]["gates"]["negative_cases"]["derived_status"] == "FAIL"


def test_r1_07_missing_raw_metric_is_incomplete() -> None:
    evidence = _complete_evidence()
    del evidence[RUNTIME_ID]["track_evidence"][PENALTY_ID]["structural_levels"]["M2"]["maximum_penetration"]

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_INCOMPLETE_EVIDENCE"
    assert report["tracks"][PENALTY_ID]["status"] == "INCOMPLETE"


def test_r1_08_nonfinite_raw_metric_is_incomplete() -> None:
    evidence = _complete_evidence()
    evidence[RUNTIME_ID]["track_evidence"][PENALTY_ID]["identity"]["energy_gradient_error"] = float("inf")

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_INCOMPLETE_EVIDENCE"
    assert report["malformed_evidence"]


def test_r1_09_policy_boolean_cannot_override_sha() -> None:
    evidence = _complete_evidence()
    evidence[RUNTIME_ID]["execution_policy"]["governing_policy_sha"] = "wrong-policy-sha"

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_INCOMPLETE_EVIDENCE"
    assert any("governing_policy_sha" in reason for reason in report["global_validation_errors"])


def test_r1_10_stale_case_digest_is_incomplete() -> None:
    evidence = _complete_evidence()
    evidence[RUNTIME_ID]["track_evidence"][ACTIVE_SET_ID]["structural_levels"]["M3"]["case_definition_digest"] = "stale"

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_INCOMPLETE_EVIDENCE"
    assert any("stale" in reason for reason in report["global_validation_errors"])


def test_r1_11_reported_pass_and_derived_fail_record_status_mismatch() -> None:
    evidence = _complete_evidence()
    evidence[RUNTIME_ID]["track_evidence"][PENALTY_ID]["identity"]["energy_gradient_error"] = 1.0

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_FAIL_IDENTITY"
    assert PENALTY_ID in report["status_mismatches"]
    assert report["tracks"][PENALTY_ID]["status_mismatch"] is True


def test_r1_12_updated_search_is_incomplete_not_bounded() -> None:
    evidence = _complete_evidence()
    evidence[RUNTIME_ID]["track_evidence"][PENALTY_ID]["updated_search"] = True

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_INCOMPLETE_EVIDENCE"


def test_r1_13_owner_authorized_not_covered_is_explicit_partial() -> None:
    evidence = _complete_evidence()
    evidence[RUNTIME_ID]["track_evidence"][PENALTY_ID] = {
        "track_status": "NOT_COVERED",
        "owner_authorized_exclusion": True,
        "reported_status": "NOT_COVERED",
        "reason": "Penalty structural execution is outside this bounded claim.",
    }

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_PARTIAL_ACTIVE_SET_ONLY"


def test_r1_14_failing_generated_track_cannot_be_removed_as_partial() -> None:
    evidence = _complete_evidence()
    evidence[RUNTIME_ID]["track_evidence"][PENALTY_ID] = {
        "track_status": "NOT_COVERED",
        "owner_authorized_exclusion": True,
        "reported_status": "NOT_COVERED",
        "reason": "This is deliberately invalid because raw evidence was generated.",
        "structural_levels": {},
    }

    report = evaluate_closure(evidence)

    assert report["status"] == "WP07_INCOMPLETE_EVIDENCE"


def test_r1_report_is_deterministic_for_same_raw_evidence() -> None:
    evidence = _complete_evidence()

    first = evaluate_closure(copy.deepcopy(evidence))
    second = evaluate_closure(copy.deepcopy(evidence))

    assert first == second
