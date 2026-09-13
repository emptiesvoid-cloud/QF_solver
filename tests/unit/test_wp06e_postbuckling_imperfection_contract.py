"""Phase-0 contract checks for the bounded WP06-E preparation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "qualification" / "0_2_9" / "wp06e_postbuckling_imperfection_contract.json"


def _contract() -> dict[str, Any]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_wp06e_is_phase0_and_runs_no_mechanics() -> None:
    contract = _contract()
    assert contract["phase"] == "PHASE_0_PREPARATION"
    assert contract["status"] == "PREPARATION_ONLY_OWNER_CANDIDATE"
    assert contract["execution"] == {
        "structural_postbuckling_run": False,
        "buckling_eigen_solve_run": False,
        "reference_solver_run": False,
        "external_solver_run": False,
        "heavy_solve_run": False,
        "full_test_suite_run": False,
        "production_mechanics_changed": False,
        "maturity_changed": False,
    }


def test_wp06e_inventory_keeps_mode_and_branch_claims_separate() -> None:
    contract = _contract()
    separation = contract["claim_separation"]
    assert separation["bifurcation_detection_status"] == "NOT_QUALIFIED"
    assert separation["branch_switching_status"] == "NOT_QUALIFIED"
    assert separation["mode_based_imperfection_status"] == "NOT_QUALIFIED"
    capabilities = {item["capability"]: item["status"] for item in contract["capability_inventory"]}
    assert capabilities["explicit_coordinate_imperfection"] == "IMPLEMENTED_RESEARCH"
    assert capabilities["eigenmode_scaled_imperfection"] == "DISCONNECTED"
    assert capabilities["bifurcation_detection"] == "MISSING_NOT_QUALIFIED"
    assert capabilities["branch_switching"] == "MISSING_NOT_QUALIFIED"


def test_wp06e_benchmark_freezes_one_explicit_coordinate_amplitude() -> None:
    benchmark = _contract()["benchmark"]
    imperfection = benchmark["imperfection"]
    assert benchmark["id"] == "WP06E-TET4-IMPERFECT-COLUMN-001"
    assert imperfection["input_route"] == "EXPLICIT_MODIFIED_REFERENCE_COORDINATES"
    assert imperfection["formula"] == "Z_imperfect = Z0 + alpha*(1-cos(0.5*pi*X/L))"
    assert imperfection["primary_alpha_over_L"] == 0.005
    assert imperfection["primary_alpha"] == 0.02
    assert imperfection["amplitude_sweep"] is False
    assert imperfection["mode_based"] == "NOT_QUALIFIED"


def test_wp06e_envelope_and_thresholds_are_predeclared() -> None:
    contract = _contract()
    assert contract["physics_contract"]["geometric_envelope"] == {
        "minimum_det_f": 0.2,
        "principal_stretches": [0.75, 1.3],
        "maximum_green_lagrange_norm": 0.3,
    }
    thresholds = contract["thresholds"]
    assert thresholds["reference_monitor_displacement"] == 0.05
    assert thresholds["reference_load_factor"] == 0.05
    assert thresholds["reference_reaction"] == 0.05
    assert thresholds["reference_strain_energy"] == 0.07
    assert thresholds["replay_relative"] == 1.0e-12
    assert thresholds["force_equilibrium_relative"] == 1.0e-8
    assert thresholds["moment_equilibrium_relative"] == 1.0e-8


def test_wp06e_reference_is_independent_and_not_a_phase0_result() -> None:
    reference = _contract()["reference_plan"]
    assert reference["independent_implementation"] is True
    assert reference["production_continuation_routines_called"] is False
    assert reference["production_mechanics_routines_called"] is False
    assert reference["formulation_match_required"] is True
    assert reference["status_before_phase_1"] == "PLAN_ONLY_NO_REFERENCE_RESULT"
    assert reference["no_cherry_picking"] is True


def test_wp06e_requires_governing_policy_and_wp06d_before_phase1() -> None:
    contract = _contract()
    assert contract["execution_policy"]["status"] == "PENDING_GOVERNING_BRANCH_INTEGRATION"
    assert "governing policy identity/SHA" in contract["execution_policy"]["required_binding"]
    governance = contract["governance"]
    assert "WP06-E structural execution" in governance["work_blocked_until_wp06d"]
    assert "structural continuation" in governance["work_blocked_until_wp04"]


def test_wp06e_negative_controls_are_fail_closed_and_not_qualification() -> None:
    negative = {item["case"]: item["expected"] for item in _contract()["negative_controls"]}
    assert negative["unsupported_branch_switch"] == "BRANCH_SWITCHING_UNSUPPORTED"
    assert negative["unsupported_bifurcation_detection"] == "BIFURCATION_DETECTION_UNSUPPORTED"
    assert negative["nonfinite_continuation_state"] == "NONFINITE_STATE"
    assert negative["replay_mismatch"] == "REPLAY_MISMATCH"
    assert len(negative) == 11


@pytest.mark.parametrize(
    "required_observable",
    [
        "accepted_load_factor_history",
        "arc_length_radius",
        "mechanical_residual",
        "minimum_det_F",
        "terminal_classification",
    ],
)
def test_wp06e_required_observables_include_path_and_finiteness_guards(required_observable: str) -> None:
    assert required_observable in _contract()["required_observables"]
