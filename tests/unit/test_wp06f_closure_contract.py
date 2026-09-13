"""R1 fail-closed synthetic tests for WP06-F closure preparation."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from scripts import check_wp06_closure as checker


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp06f_closure_contract.json"


def _contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _phase1_binding(anchors: dict[str, Any]) -> dict[str, Any]:
    return {
        "repository": "emptiesvoid-cloud/QF_solver",
        "branch": "0.2.9-governing-integrated",
        "source_sha": "f" * 40,
        "solver_policy_digest": "s" * 64,
        "governing_policy_identity": {
            "governing_policy_sha": "f" * 40,
            "formulation_label": anchors["formulation_label"],
            "residual_form": anchors["residual_form"],
            "orientation_policy": anchors["d_orientation_policy"],
            "newton_convergence_contract": "governing-newton-contract",
            "floor_aware_convergence_policy": "governing-floor-aware-policy",
            "load_step_retry_policy": anchors["d_retry_policy"],
            "linear_backend": anchors["d_linear_backend"],
            "line_search_policy": "governing-line-search-policy",
            "arc_length_termination_policy": anchors["d_termination_policy"],
            "policy_digest": "s" * 64,
        },
    }


def _provenance(
    anchors: dict[str, Any],
    *,
    track: str | None = None,
    reference: bool = False,
    binding: dict[str, Any] | None = None,
) -> dict[str, str]:
    binding = binding or _phase1_binding(anchors)
    value = {
        "repository": binding["repository"],
        "branch": binding["branch"],
        "source_sha": binding["source_sha"],
        "contract_revision": "WP06D-R1" if track == "d" else "WP06E-R0" if track == "e" else "historical",
        "contract_digest": anchors[f"{track}_contract_digest"] if track else "h" * 64,
        "case_definition_digest": anchors[f"{track}_case_definition_digest"] if track else "k" * 64,
        "solver_policy_digest": binding["solver_policy_digest"],
        "element_formulation_identity": anchors["element_formulation"],
    }
    if reference:
        value["reference_implementation_digest"] = "r" * 64
    return value


def _replay() -> dict[str, Any]:
    run = {
        "accepted_displacement_path": [[0.0, 0.0], [0.1, 0.2]],
        "lambda_path": [0.0, 1.0],
        "radius_history": [0.02, 0.02],
        "orientation_history": ["positive", "positive"],
        "accepted_rejected_steps": ["accepted", "accepted"],
        "newton_counts": [2, 3],
        "terminal_classification": "PASS",
    }
    return {"run_a": copy.deepcopy(run), "run_b": copy.deepcopy(run)}


def _refinement() -> dict[str, dict[str, float]]:
    return {
        name: {"m2": 1.0, "m3": 1.001, "scale_floor": 1.0e-14}
        for name in (
            "u_monitor",
            "lambda_at_limit",
            "post_limit_monitored_displacement",
            "support_reaction",
            "strain_energy",
        )
    }


def _equilibrium() -> dict[str, Any]:
    return {
        "support_reaction": [0.0, 0.0, 1.0],
        "external_force": [0.0, 0.0, -1.0],
        "reaction_moment": [0.0, 0.0, 0.0],
        "external_moment": [0.0, 0.0, 0.0],
        "force_scale": 1.0,
        "moment_scale": 1.0,
    }


def _raw_d(anchors: dict[str, Any]) -> dict[str, Any]:
    return {
        "benchmark_id": anchors["d_benchmark_id"],
        "element_formulation": anchors["element_formulation"],
        "formulation_label": anchors["formulation_label"],
        "residual_form": anchors["residual_form"],
        "constraint_form": anchors["constraint_form"],
        "orientation_policy": anchors["d_orientation_policy"],
        "load_rule": anchors["d_load_rule"],
        "mesh_digests": {"M1": "1" * 64, "M2": "2" * 64, "M3": "3" * 64},
        "case_definition_digest": anchors["d_case_definition_digest"],
        "state_owner": anchors["state_owner"],
        "state_schema_digest": anchors["state_schema_digest"],
        "rollback_contract_digest": anchors["rollback_contract_digest"],
        "continuation_formulation": anchors["d_continuation_formulation"],
        "retry_policy": anchors["d_retry_policy"],
        "linear_backend": anchors["d_linear_backend"],
        "termination_policy": anchors["d_termination_policy"],
        "refinement": _refinement(),
        "limit_point_observed": True,
        "path_continues_beyond_limit": True,
        "equilibrium": _equilibrium(),
        "envelope_pass": True,
        "required_observables_complete": True,
        "altered_physics_retry": False,
        "undeclared_m4": False,
        "result_dependent_threshold_change": False,
    }


def _raw_e(anchors: dict[str, Any]) -> dict[str, Any]:
    return {
        "benchmark_id": anchors["e_benchmark_id"],
        "route": anchors["e_route"],
        "element_formulation": anchors["element_formulation"],
        "formulation_label": anchors["formulation_label"],
        "residual_form": anchors["residual_form"],
        "constraint_form": anchors["constraint_form"],
        "orientation_policy": anchors["d_orientation_policy"],
        "imperfection_formula": anchors["e_imperfection_formula"],
        "alpha_over_l": anchors["e_alpha_over_l"],
        "mode_based_substitution": False,
        "branch_switch_claim": False,
        "bifurcation_detection_claim": False,
        "claim_exclusions": list(anchors["e_excluded_claims"]),
        "state_owner": anchors["state_owner"],
        "state_schema_digest": anchors["state_schema_digest"],
        "rollback_contract_digest": anchors["rollback_contract_digest"],
        "linear_backend": anchors["d_linear_backend"],
        "termination_policy": anchors["d_termination_policy"],
        "case_definition_digest": anchors["e_case_definition_digest"],
        "equilibrium": _equilibrium(),
        "envelope_pass": True,
        "required_observables_complete": True,
    }


def _reference(anchors: dict[str, Any], track: str) -> dict[str, Any]:
    value: dict[str, Any] = {
        "benchmark_id": anchors[f"{track}_benchmark_id"],
        "formulation_match": True,
        "independent_implementation": True,
        "element_formulation": anchors["element_formulation"],
        "formulation_label": anchors["formulation_label"],
        "observations": {
            "monitor_displacement": {"qf": 1.0, "reference": 1.001, "scale_floor": 1.0e-14},
            "lambda": {"qf": 1.0, "reference": 1.001, "scale_floor": 1.0e-14},
            "reaction": {"qf": 1.0, "reference": 1.001, "scale_floor": 1.0e-14},
            "energy": {"qf": 1.0, "reference": 1.001, "scale_floor": 1.0e-14},
        },
        "production_arclength_routines_called": False,
        "production_continuation_kernels_called": False,
        "production_residual_tangent_helpers_called": False,
        "production_tet4_geometric_helpers_called": False,
    }
    if track == "d":
        value["mesh_digests"] = {"M1": "1" * 64, "M2": "2" * 64, "M3": "3" * 64}
    return value


def _payload() -> dict[str, Any]:
    anchors = checker.controlled_anchors()
    binding = _phase1_binding(anchors)
    artifacts: dict[str, Any] = {}
    for item in _contract()["required_artifact_manifest"]:
        artifact_id = item["id"]
        track = "d" if artifact_id.startswith("WP06-D-") and artifact_id in checker.PHASE1_IDS else "e" if artifact_id in checker.PHASE1_IDS else None
        raw: dict[str, Any] | None = None
        reference = False
        if artifact_id == "WP06-D-RAW":
            raw = _raw_d(anchors)
        elif artifact_id == "WP06-E-RAW":
            raw = _raw_e(anchors)
        elif artifact_id == "WP06-D-REFERENCE":
            raw, reference = _reference(anchors, "d"), True
        elif artifact_id == "WP06-E-REFERENCE":
            raw, reference = _reference(anchors, "e"), True
        elif artifact_id == "WP06-D-REPLAY":
            raw = {"mesh_digests": {"M1": "1" * 64, "M2": "2" * 64, "M3": "3" * 64}, **_replay()}
        elif artifact_id == "WP06-E-REPLAY":
            raw = _replay()
        artifacts[artifact_id] = {
            "present": True,
            "provenance": _provenance(anchors, track=track, reference=reference, binding=binding),
        }
        if raw is not None:
            artifacts[artifact_id]["raw"] = raw
    return {
        "phase1_binding": binding,
        "artifacts": artifacts,
    }


def test_wp06f_phase0_guard_and_manifest() -> None:
    checker.assert_preparation_only()
    contract = _contract()
    assert contract["phase"] == "PHASE_0_PREPARATION"
    assert len(contract["required_artifact_manifest"]) == 13
    assert contract["execution_guard"]["structural_solve_run"] is False


def test_valid_raw_evidence_derives_bounded_pass() -> None:
    assert checker.evaluate_closure(_payload())["status"] == "WP06_PASS_BOUNDED"


def test_e_does_not_require_fake_d_refinement_schema() -> None:
    payload = _payload()
    assert "refinement" not in payload["artifacts"]["WP06-E-RAW"]["raw"]
    assert checker.evaluate_closure(payload)["status"] == "WP06_PASS_BOUNDED"


def test_e_fake_refinement_is_not_an_e_gate() -> None:
    payload = _payload()
    payload["artifacts"]["WP06-E-RAW"]["raw"]["refinement"] = {
        "u_monitor": {"m2": 1.0, "m3": 2.0, "scale_floor": 1.0e-14},
    }
    assert checker.evaluate_closure(payload)["status"] == "WP06_PASS_BOUNDED"


def test_missing_artifact_fails_closed() -> None:
    payload = _payload()
    payload["artifacts"]["WP06-E-REPLAY"]["present"] = False
    assert checker.evaluate_closure(payload)["status"] == "WP06_INCOMPLETE_EVIDENCE"


def test_provenance_digest_mismatch_is_invalid() -> None:
    payload = _payload()
    payload["artifacts"]["WP06-D-RAW"]["provenance"]["contract_digest"] = "x" * 64
    assert checker.evaluate_closure(payload)["status"] == "WP06_INVALID_EVIDENCE"


@pytest.mark.parametrize(
    ("track", "field", "value"),
    [
        ("d", "benchmark_id", "WRONG_D_BENCHMARK"),
        ("d", "load_rule", "EQUAL_NODE_LOAD"),
        ("d", "mesh_digests", {"M1": "1" * 64, "M2": "2" * 64, "M3": "a" * 64}),
        ("d", "retry_policy", "ALTERED_PHYSICS_RETRY"),
    ],
)
def test_r0_d_identity_guards_remain_fail_closed(track: str, field: str, value: Any) -> None:
    payload = _payload()
    payload["artifacts"][f"WP06-{track.upper()}-RAW"]["raw"][field] = value
    assert checker.evaluate_closure(payload)["status"] == "WP06_INVALID_EVIDENCE"


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("governing_policy_sha", "g" * 40, "WP06_INVALID_EVIDENCE"),
        ("arc_length_termination_policy", "wrong-termination", "WP06_INVALID_EVIDENCE"),
        ("line_search_policy", None, "WP06_INCOMPLETE_EVIDENCE"),
    ],
)
def test_governing_policy_identity_is_bound_and_not_self_asserted(
    field: str, value: Any, expected: str
) -> None:
    payload = _payload()
    payload["phase1_binding"]["governing_policy_identity"][field] = value
    assert checker.evaluate_closure(payload)["status"] == expected


def test_track_specific_reference_threshold_table_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _payload()
    payload["artifacts"]["WP06-D-REFERENCE"]["raw"]["observations"]["reaction"]["reference"] = 1.02
    payload["artifacts"]["WP06-E-REFERENCE"]["raw"]["observations"]["reaction"]["reference"] = 1.02
    altered = copy.deepcopy(_contract())
    altered["thresholds"]["d_reference"]["reaction"] = 0.05
    altered["thresholds"]["e_reference"]["reaction"] = 0.01
    monkeypatch.setattr(checker, "load_contract", lambda: altered)
    assert checker.evaluate_closure(payload)["status"] == "WP06_HOLD_REFERENCE"


def test_d_reference_uses_d_table_not_e_table(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _payload()
    payload["artifacts"]["WP06-D-REFERENCE"]["raw"]["observations"]["reaction"]["reference"] = 1.02
    altered = copy.deepcopy(_contract())
    altered["thresholds"]["d_reference"]["reaction"] = 0.01
    altered["thresholds"]["e_reference"]["reaction"] = 0.05
    monkeypatch.setattr(checker, "load_contract", lambda: altered)
    assert checker.evaluate_closure(payload)["status"] == "WP06_HOLD_REFERENCE"


def test_e_reference_uses_e_table_not_d_table(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _payload()
    payload["artifacts"]["WP06-E-REFERENCE"]["raw"]["observations"]["reaction"]["reference"] = 1.02
    altered = copy.deepcopy(_contract())
    altered["thresholds"]["d_reference"]["reaction"] = 0.05
    altered["thresholds"]["e_reference"]["reaction"] = 0.01
    monkeypatch.setattr(checker, "load_contract", lambda: altered)
    assert checker.evaluate_closure(payload)["status"] == "WP06_HOLD_REFERENCE"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("route", "modal/arc_length"),
        ("element_formulation", "HEX8 Total-Lagrangian StVK"),
        ("imperfection_formula", "wrong"),
        ("alpha_over_l", 0.01),
    ],
)
def test_wrong_e_identity_is_rejected(field: str, value: Any) -> None:
    payload = _payload()
    payload["artifacts"]["WP06-E-RAW"]["raw"][field] = value
    assert checker.evaluate_closure(payload)["status"] == "WP06_INVALID_EVIDENCE"


def test_consistent_but_wrong_cross_wp_formulation_is_rejected() -> None:
    payload = _payload()
    payload["artifacts"]["WP06-D-RAW"]["raw"]["formulation_label"] = "WRONG_FORMULATION"
    payload["artifacts"]["WP06-E-RAW"]["raw"]["formulation_label"] = "WRONG_FORMULATION"
    assert checker.evaluate_closure(payload)["status"] == "WP06_INVALID_EVIDENCE"


def test_payload_level_raw_duplicates_cannot_override_manifest_artifacts() -> None:
    payload = _payload()
    payload["d_raw"] = {"benchmark_id": "WRONG"}
    payload["e_raw"] = {"route": "wrong"}
    assert checker.evaluate_closure(payload)["status"] == "WP06_PASS_BOUNDED"


def test_d_mesh_digests_must_match_all_d_artifacts() -> None:
    payload = _payload()
    payload["artifacts"]["WP06-D-REPLAY"]["raw"]["mesh_digests"]["M3"] = "other-mesh"
    assert checker.evaluate_closure(payload)["status"] == "WP06_INVALID_EVIDENCE"


@pytest.mark.parametrize(
    ("artifact_id", "field", "value"),
    [
        ("WP06-D-REPLAY", "lambda_path", [0.0, 1.1]),
        ("WP06-E-REPLAY", "radius_history", [0.02, 0.03]),
        ("WP06-E-REPLAY", "orientation_history", ["positive", "negative"]),
        ("WP06-D-REPLAY", "accepted_rejected_steps", ["accepted", "rejected"]),
        ("WP06-E-REPLAY", "newton_counts", [2, 4]),
        ("WP06-D-REPLAY", "terminal_classification", "FAIL"),
    ],
)
def test_dedicated_replay_artifact_mismatch_is_held(artifact_id: str, field: str, value: Any) -> None:
    payload = _payload()
    payload["artifacts"][artifact_id]["raw"]["run_b"][field] = value
    assert checker.evaluate_closure(payload)["status"] == "WP06_HOLD_REPLAY"


def test_replay_boolean_alone_is_not_sufficient() -> None:
    payload = _payload()
    payload["artifacts"]["WP06-D-REPLAY"]["raw"] = {
        "replay_pass": True,
        "mesh_digests": {"M1": "1" * 64, "M2": "2" * 64, "M3": "3" * 64},
    }
    assert checker.evaluate_closure(payload)["status"] == "WP06_INCOMPLETE_EVIDENCE"


def test_missing_nested_refinement_value_is_incomplete() -> None:
    payload = _payload()
    del payload["artifacts"]["WP06-D-RAW"]["raw"]["refinement"]["u_monitor"]
    assert checker.evaluate_closure(payload)["status"] == "WP06_INCOMPLETE_EVIDENCE"


def test_refinement_failure_is_reported_as_status_mismatch_if_summary_says_pass() -> None:
    payload = _payload()
    payload["artifacts"]["WP06-D-RAW"]["raw"]["refinement"]["u_monitor"]["m3"] = 1.2
    payload["reported_status"] = "PASS"
    assert checker.evaluate_closure(payload)["status"] == "WP06_STATUS_MISMATCH"


def test_equilibrium_failure_is_not_hidden_by_summary_pass() -> None:
    payload = _payload()
    payload["artifacts"]["WP06-E-RAW"]["raw"]["equilibrium"]["external_force"] = [0.0, 0.0, -0.8]
    payload["reported_status"] = "PASS"
    assert checker.evaluate_closure(payload)["status"] == "WP06_STATUS_MISMATCH"


def test_reference_missing_raw_is_held() -> None:
    payload = _payload()
    payload["artifacts"]["WP06-E-REFERENCE"]["raw"] = None
    assert checker.evaluate_closure(payload)["status"] == "WP06_HOLD_REFERENCE"


def test_unsupported_claims_and_undeclared_m4_are_invalid() -> None:
    payload = _payload()
    payload["artifacts"]["WP06-E-RAW"]["raw"]["branch_switch_claim"] = True
    assert checker.evaluate_closure(payload)["status"] == "WP06_INVALID_EVIDENCE"
    payload = _payload()
    payload["artifacts"]["WP06-D-RAW"]["raw"]["undeclared_m4"] = True
    assert checker.evaluate_closure(payload)["status"] == "WP06_INVALID_EVIDENCE"


def test_nonfinite_and_unexpected_mechanics_change_fail_closed() -> None:
    payload = _payload()
    payload["artifacts"]["WP06-E-RAW"]["raw"]["equilibrium"]["external_force"][0] = float("nan")
    assert checker.evaluate_closure(payload)["status"] == "WP06_INCOMPLETE_EVIDENCE"
    payload = _payload()
    payload["production_mechanics_changed"] = True
    assert checker.evaluate_closure(payload)["status"] == "WP06_INVALID_EVIDENCE"


def test_contract_preserves_claim_boundary_and_point_policy() -> None:
    contract = _contract()
    assert "bifurcation detection" in contract["claim_boundary"]["excluded"]
    assert "branch switching" in contract["claim_boundary"]["excluded"]
    assert contract["formal_point_award"]["phase0_award"] == "0/8"
