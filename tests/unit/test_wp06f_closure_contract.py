"""Fail-closed synthetic tests for WP06-F closure preparation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts import check_wp06_closure as checker


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp06f_closure_contract.json"


def _contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _provenance(reference: bool = False) -> dict[str, str]:
    value = {
        "repository": "emptiesvoid-cloud/QF_solver",
        "branch": "0.2.9-governing-integrated",
        "source_sha": "f" * 40,
        "contract_revision": "WP06F-R0",
        "contract_digest": "c" * 64,
        "case_definition_digest": "d" * 64,
        "solver_policy_digest": "p" * 64,
        "element_formulation_identity": "TET4-TL-STVK",
    }
    if reference:
        value["reference_implementation_digest"] = "r" * 64
    return value


def _refinement(names: list[str]) -> dict[str, dict[str, float]]:
    return {name: {"m2": 1.0, "m3": 1.001, "scale_floor": 1.0e-14} for name in names}


def _raw(benchmark: str, *, alpha: float | None = None) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "benchmark_id": benchmark,
        "refinement": _refinement([
            "u_monitor",
            "lambda_at_limit",
            "post_limit_monitored_displacement",
            "support_reaction",
            "strain_energy",
        ]),
        "equilibrium": {
            "support_reaction": [0.0, 0.0, 1.0],
            "external_force": [0.0, 0.0, -1.0],
            "reaction_moment": [0.0, 0.0, 0.0],
            "external_moment": [0.0, 0.0, 0.0],
            "force_scale": 1.0,
            "moment_scale": 1.0,
        },
        "reference": {
            "monitor_displacement": {"qf": 1.0, "reference": 1.001, "scale_floor": 1.0e-14},
            "lambda": {"qf": 1.0, "reference": 1.001, "scale_floor": 1.0e-14},
            "reaction": {"qf": 1.0, "reference": 1.001, "scale_floor": 1.0e-14},
            "energy": {"qf": 1.0, "reference": 1.001, "scale_floor": 1.0e-14},
        },
        "mesh_digests_match": True,
        "load_rule": "MESH_INDEPENDENT_GEOMETRIC_POINT_LOAD",
        "m4_declared": False,
        "altered_physics_retry": False,
        "result_dependent_threshold_change": False,
        "envelope_pass": True,
        "replay_pass": True,
        "required_observables_complete": True,
        "reference_independent": True,
        "reference_production_routines_called": False,
        "reported_status": "PASS",
    }
    if alpha is not None:
        raw.update({"alpha_over_l": alpha, "mode_based_substitution": False, "branch_switch_claim": False, "bifurcation_detection_claim": False})
    return raw


def _payload() -> dict[str, Any]:
    contract = _contract()
    artifacts: dict[str, Any] = {}
    for item in contract["required_artifact_manifest"]:
        artifacts[item["id"]] = {"present": True, "provenance": _provenance(item["id"].endswith("REFERENCE"))}
    return {
        "phase1_binding": _provenance(),
        "artifacts": artifacts,
        "d_raw": _raw("WP06D-TET4-MINIMAL-SNAP-THROUGH-001"),
        "e_raw": _raw("WP06E-TET4-IMPERFECT-COLUMN-001", alpha=0.005),
        "replay_a": {"lambda": [0.0, 1.0], "terminal": "PASS"},
        "replay_b": {"lambda": [0.0, 1.0], "terminal": "PASS"},
        "reported_status": "PASS",
    }


def test_wp06f_phase0_guard_and_manifest() -> None:
    checker.assert_preparation_only()
    contract = _contract()
    assert contract["phase"] == "PHASE_0_PREPARATION"
    assert len(contract["required_artifact_manifest"]) == 13
    assert contract["execution_guard"]["structural_solve_run"] is False


def test_valid_raw_evidence_derives_bounded_pass() -> None:
    result = checker.evaluate_closure(_payload())
    assert result["status"] == "WP06_PASS_BOUNDED"


def test_missing_artifact_fails_closed() -> None:
    payload = _payload()
    payload["artifacts"]["WP06-E-REPLAY"]["present"] = False
    assert checker.evaluate_closure(payload)["status"] == "WP06_INCOMPLETE_EVIDENCE"


def test_provenance_digest_mismatch_is_invalid() -> None:
    payload = _payload()
    payload["artifacts"]["WP06-D-RAW"]["provenance"]["contract_digest"] = "x" * 64
    assert checker.evaluate_closure(payload)["status"] == "WP06_INVALID_EVIDENCE"


def test_wrong_benchmark_amplitude_mesh_load_and_policy_are_rejected() -> None:
    cases = []
    payload = _payload()
    payload["d_raw"]["benchmark_id"] = "WRONG"
    cases.append(payload)
    payload = _payload()
    payload["e_raw"]["alpha_over_l"] = 0.01
    cases.append(payload)
    payload = _payload()
    payload["d_raw"]["mesh_digests_match"] = False
    cases.append(payload)
    payload = _payload()
    payload["d_raw"]["load_rule"] = "EQUAL_NODE_LOAD"
    cases.append(payload)
    payload = _payload()
    payload["artifacts"]["WP06-E-RAW"]["provenance"]["solver_policy_digest"] = "x" * 64
    cases.append(payload)
    assert all(checker.evaluate_closure(case)["status"] == "WP06_INVALID_EVIDENCE" for case in cases)


def test_refinement_failure_is_held_even_when_report_says_pass() -> None:
    payload = _payload()
    payload["d_raw"]["refinement"]["u_monitor"]["m3"] = 1.2
    assert checker.evaluate_closure(payload)["status"] == "WP06_HOLD_STRUCTURAL"


def test_equilibrium_failure_is_not_hidden_by_summary_pass() -> None:
    payload = _payload()
    payload["e_raw"]["equilibrium"]["external_force"] = [0.0, 0.0, -0.8]
    assert checker.evaluate_closure(payload)["status"] == "WP06_FAIL_EQUILIBRIUM"


def test_reference_missing_or_mismatch_is_held() -> None:
    payload = _payload()
    payload["e_raw"]["reference"]["lambda"]["reference"] = 2.0
    assert checker.evaluate_closure(payload)["status"] == "WP06_HOLD_REFERENCE"


def test_replay_mismatch_is_held() -> None:
    payload = _payload()
    payload["replay_b"]["lambda"] = [0.0, 1.1]
    assert checker.evaluate_closure(payload)["status"] == "WP06_HOLD_REPLAY"


def test_unsupported_claims_and_undeclared_m4_are_invalid() -> None:
    payload = _payload()
    payload["e_raw"]["branch_switch_claim"] = True
    assert checker.evaluate_closure(payload)["status"] == "WP06_INVALID_EVIDENCE"
    payload = _payload()
    payload["d_raw"]["m4_declared"] = True
    assert checker.evaluate_closure(payload)["status"] == "WP06_INVALID_EVIDENCE"


def test_nonfinite_and_unexpected_mechanics_change_fail_closed() -> None:
    payload = _payload()
    payload["e_raw"]["reference"]["energy"]["qf"] = float("nan")
    assert checker.evaluate_closure(payload)["status"] == "WP06_INCOMPLETE_EVIDENCE"
    payload = _payload()
    payload["production_mechanics_changed"] = True
    assert checker.evaluate_closure(payload)["status"] == "WP06_INVALID_EVIDENCE"


def test_reported_pass_cannot_override_derived_failure() -> None:
    payload = _payload()
    payload["d_raw"]["refinement"]["strain_energy"]["m3"] = 1.2
    payload["reported_status"] = "PASS"
    assert checker.evaluate_closure(payload)["status"] == "WP06_HOLD_STRUCTURAL"


def test_contract_preserves_claim_boundary_and_point_policy() -> None:
    contract = _contract()
    assert "bifurcation detection" in contract["claim_boundary"]["excluded"]
    assert "branch switching" in contract["claim_boundary"]["excluded"]
    assert contract["formal_point_award"]["phase0_award"] == "0/8"
