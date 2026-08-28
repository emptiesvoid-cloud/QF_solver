"""Runner for the deterministic nonlinear failure campaign."""

from __future__ import annotations

import numpy as np

from solveur.core.nonlinear_contracts import NonlinearFailureReason
from solveur.verification.nonlinear_failure_campaign import (
    _Assembly,
    _raising_internal,
    _run_arc_length_failure_case,
    _run_buckling_failure_case,
    _run_contact_penetration_cutback_case,
    _run_contact_penetration_limit_case,
    _run_contact_retry_rollback_case,
    _run_case,
    _run_linear_backend_failure_case,
    _run_min_increment_case,
    _run_multistep_retry_rollback_case,
    _run_nonfinite_correction_case,
    _run_state_corruption_case,
)
from solveur.verification.nonlinear_checkpoint_failure import run_checkpoint_failure_cases


def run_failure_campaign() -> dict[str, object]:
    """Run intentional failures and return a non-release evidence report."""
    cases = [
        _run_case(
            "max_iterations",
            NonlinearFailureReason.MAX_ITERATIONS,
            _Assembly(lambda displacement: displacement, np.eye(2)),
            max_iterations=1,
        ),
        _run_case(
            "singular_tangent",
            NonlinearFailureReason.SINGULAR_TANGENT,
            _Assembly(lambda displacement: np.zeros(2), np.zeros((2, 2))),
        ),
        _run_case(
            "nan_detected",
            NonlinearFailureReason.NAN_DETECTED,
            _Assembly(lambda displacement: np.array([np.nan, 0.0]), np.eye(2)),
        ),
        _run_case(
            "inf_detected",
            NonlinearFailureReason.INF_DETECTED,
            _Assembly(lambda displacement: np.array([np.inf, 0.0]), np.eye(2)),
        ),
        _run_case(
            "line_search_failure",
            NonlinearFailureReason.LINE_SEARCH_FAILURE,
            _Assembly(lambda displacement: np.zeros(2), np.eye(2)),
        ),
        _run_case(
            "invalid_element",
            NonlinearFailureReason.INVALID_ELEMENT,
            _Assembly(_raising_internal("Invalid HEX8 orientation"), np.eye(2)),
        ),
        _run_case(
            "material_update_failure",
            NonlinearFailureReason.MATERIAL_UPDATE_FAILURE,
            _Assembly(_raising_internal("material constitutive update failed"), np.eye(2)),
        ),
        _run_case(
            "contact_update_failure",
            NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
            _Assembly(_raising_internal("contact projection produced a non-finite gap"), np.eye(2)),
        ),
        _run_min_increment_case(),
    ]
    nonfinite_correction_cases = [
        _run_nonfinite_correction_case(np.nan, NonlinearFailureReason.NAN_DETECTED),
        _run_nonfinite_correction_case(np.inf, NonlinearFailureReason.INF_DETECTED),
        _run_nonfinite_correction_case(-np.inf, NonlinearFailureReason.INF_DETECTED),
    ]
    retry_cases = [_run_contact_retry_rollback_case(), _run_linear_backend_failure_case()]
    contact_failure_cases = [
        _run_contact_penetration_limit_case(),
        _run_contact_penetration_cutback_case(),
    ]
    multi_step_cases = [_run_multistep_retry_rollback_case()]
    path_failure_cases = [_run_arc_length_failure_case(), _run_buckling_failure_case()]
    state_failure_cases = [_run_state_corruption_case()]
    checkpoint_failure_cases = run_checkpoint_failure_cases()
    return {
        "campaign": "qf-solver-nonlinear-failure-contract-0.2.5a0",
        "status": (
            "PASS_INTERNAL_FAILURE_CONTRACT"
            if all(case.passed for case in cases)
            and all(case["passed"] for case in retry_cases)
            and all(case["passed"] for case in nonfinite_correction_cases)
            and all(case["passed"] for case in contact_failure_cases)
            and all(case["passed"] for case in multi_step_cases)
            and all(case["passed"] for case in path_failure_cases)
            and all(case["passed"] for case in state_failure_cases)
            and all(case["passed"] for case in checkpoint_failure_cases)
            else "FAIL"
        ),
        "release_claim": False,
        "cases": [case.to_dict() for case in cases],
        "nonfinite_correction_cases": nonfinite_correction_cases,
        "retry_cases": retry_cases,
        "contact_failure_cases": contact_failure_cases,
        "multi_step_cases": multi_step_cases,
        "path_failure_cases": path_failure_cases,
        "state_failure_cases": state_failure_cases,
        "checkpoint_failure_cases": checkpoint_failure_cases,
    }
