from __future__ import annotations

from solveur.verification.nonlinear_failure_campaign import run_failure_campaign


def test_adversarial_failure_campaign_preserves_typed_reasons() -> None:
    report = run_failure_campaign()

    assert report["status"] == "PASS_INTERNAL_FAILURE_CONTRACT"
    assert report["release_claim"] is False
    assert all(case["passed"] for case in report["cases"])
    assert all(case["converged"] is False for case in report["cases"])
    assert all(case["diagnostics"]["solver"] == "full_newton" for case in report["cases"])
    assert len(report["nonfinite_correction_cases"]) == 3
    assert all(case["passed"] for case in report["nonfinite_correction_cases"])
    assert [case["failure_reason"] for case in report["nonfinite_correction_cases"]] == [
        "NAN_DETECTED",
        "INF_DETECTED",
        "INF_DETECTED",
    ]
    assert report["retry_cases"][0]["passed"] is True
    assert report["retry_cases"][0]["diagnostics"]["committed_steps"] == [0.5, 1.0]
    assert report["retry_cases"][1]["name"] == "linear_solver_failure"
    assert report["retry_cases"][1]["passed"] is True
    assert report["retry_cases"][1]["failure_reason"] == "LINEAR_SOLVER_FAILURE"
    assert report["contact_failure_cases"][0]["name"] == "contact_penetration_limit"
    assert report["contact_failure_cases"][0]["passed"] is True
    assert report["contact_failure_cases"][0]["failure_reason"] == "CONTACT_PENETRATION_EXCESSIVE"
    contact_cutback = next(
        case for case in report["contact_failure_cases"] if case["name"] == "contact_penetration_cutback"
    )
    assert contact_cutback["passed"] is True
    assert contact_cutback["diagnostics"]["committed_steps"] == [0.5, 0.75, 1.0]
    assert contact_cutback["diagnostics"]["rollback_before_retry"] is True
    assert contact_cutback["diagnostics"]["displacement_relative_difference"] < 1.0e-10
    assert report["multi_step_cases"][0]["name"] == "multistep_retry_rollback"
    assert report["multi_step_cases"][0]["passed"] is True
    assert report["multi_step_cases"][0]["diagnostics"]["committed_steps"] == [0.5, 0.75, 1.0]
    assert {case["name"] for case in report["path_failure_cases"]} == {
        "arc_length_failure",
        "buckling_failure",
    }
    assert all(case["passed"] for case in report["path_failure_cases"])
    assert all(case["converged"] is False for case in report["path_failure_cases"])
    assert {case["failure_reason"] for case in report["path_failure_cases"]} == {
        "ARC_LENGTH_FAILURE",
        "BUCKLING_FAILURE",
    }
    assert report["state_failure_cases"][0]["name"] == "state_corruption"
    assert report["state_failure_cases"][0]["passed"] is True
    assert report["state_failure_cases"][0]["converged"] is False
    assert report["state_failure_cases"][0]["failure_reason"] == "STATE_CORRUPTION"
    assert report["state_failure_cases"][0]["diagnostics"]["transaction"] == "generic"
    assert {case["name"] for case in report["checkpoint_failure_cases"]} == {
        "checkpoint_corruption",
        "checkpoint_model_mismatch",
    }
    assert all(case["passed"] for case in report["checkpoint_failure_cases"])
    assert all(case["converged"] is False for case in report["checkpoint_failure_cases"])
    assert all(
        case["failure_reason"] == "CHECKPOINT_FAILURE"
        for case in report["checkpoint_failure_cases"]
    )
