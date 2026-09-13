"""Freeze and execute the prospective WP04-C2R6 policy controls.

This script deliberately runs before the real C2R6 nonlinear campaign.  It
uses the immutable C2R5 captured tangent only to calibrate a state-resolution
diagnostic; it does not alter or rewrite that evidence.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "qualification" / "0_2_9" / "c2r6"
CAPTURE = (
    Path(tempfile.gettempdir())
    / "qf_solver_029_c2r5_forensics"
    / "c2_m2_canonical_step4_failure.npz"
)
RESULT = OUTPUT / "floor_aware_policy.json"


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and not np.isfinite(value):
            return None
        return value
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _control_inputs(matrix: csr_matrix, displacement: np.ndarray) -> dict[str, Any]:
    from solveur.core.nonlinear.robustness import FLOOR_AWARE_LINEAR_BACKWARD_ERROR_TOLERANCE

    correction = np.zeros_like(displacement)
    correction[0] = 1.4295467474352116e-16 * max(float(np.linalg.norm(displacement)), 1.0e-300)
    return {
        "residual_history": [1.0411047989090212e-10] * 4,
        "relative_residual": 1.0411047989090212e-10,
        "convergence_tolerance": 1.0e-10,
        "correction": correction,
        "displacement": displacement,
        "tangent": matrix,
        "residual_scale": 1.0,
        "linear_backward_error": min(FLOOR_AWARE_LINEAR_BACKWARD_ERROR_TOLERANCE, 1.0e-12),
        "line_search_improvement_available": False,
        "force_equilibrium": 3.299667940206007e-14,
        "moment_equilibrium": 8.554221404645066e-16,
        "state_valid": True,
    }


def _decision(controller: Any, values: Mapping[str, Any], **updates: Any) -> dict[str, Any]:
    candidate = dict(values)
    candidate.update(updates)
    return controller.floor_aware_decision(**candidate).to_dict()


def main() -> int:
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    from solveur.core.nonlinear.robustness import (
        FLOOR_AWARE_COMPONENT_ULP_MULTIPLIER,
        FLOOR_AWARE_CORRECTION_EPS_MULTIPLIER,
        FLOOR_AWARE_EQUILIBRIUM_TOLERANCE,
        FLOOR_AWARE_LINEAR_BACKWARD_ERROR_TOLERANCE,
        FLOOR_AWARE_PLATEAU_WINDOW,
        FLOOR_AWARE_POLICY_ID,
        FLOOR_AWARE_POLICY_VERSION,
        NonlinearRobustnessOptions,
        UnifiedNonlinearRobustnessController,
    )

    if not CAPTURE.exists():
        raise FileNotFoundError(f"C2R5 capture required for controls: {CAPTURE}")
    with np.load(CAPTURE, allow_pickle=False) as data:
        matrix = csr_matrix(
            (data["data"], data["indices"], data["indptr"]),
            shape=tuple(int(item) for item in data["shape"]),
        )
        displacement = np.asarray(data["trial_displacement"], dtype=float)[
            np.asarray(data["free"], dtype=int)
        ]

    options = NonlinearRobustnessOptions(floor_aware_termination=True)
    options.validate()
    controller = UnifiedNonlinearRobustnessController.from_options(options)
    positive_inputs = _control_inputs(matrix, displacement)
    positives = {
        "P1_C2R5_canonical_step4": _decision(controller, positive_inputs),
        "P2_C2R4_off_route_plateau": _decision(
            controller,
            positive_inputs,
            residual_history=[1.1303927985055497e-10] * 4,
            relative_residual=1.1303927985055497e-10,
            correction=np.array(positive_inputs["correction"], copy=True)
            * (3.24802865160447e-16 / 1.4295467474352116e-16),
            force_equilibrium=3.299667940206007e-14,
            moment_equilibrium=8.554221404645066e-16,
        ),
        "P3_R2B_M1_primary": _decision(
            controller,
            positive_inputs,
            residual_history=[1.0e-1, 1.0e-3, 5.0e-11, 5.0e-11],
            relative_residual=5.0e-11,
        ),
    }
    negatives = {
        "N1_early_large_residual": _decision(
            controller,
            positive_inputs,
            residual_history=[1.0e-1] * 4,
            relative_residual=1.0e-1,
        ),
        "N2_poor_force_equilibrium": _decision(controller, positive_inputs, force_equilibrium=1.0e-3),
        "N3_true_failure_away_from_floor": _decision(
            controller,
            positive_inputs,
            residual_history=[1.0e-3] * 4,
            relative_residual=1.0e-3,
        ),
        "N4_correction_not_at_resolution": _decision(
            controller,
            positive_inputs,
            correction=np.full(displacement.shape, 1.0e3),
        ),
        "N5_invalid_or_nonfinite_state": _decision(controller, positive_inputs, state_valid=False),
        "N6_invalid_cg_correction": _decision(controller, positive_inputs, linear_backward_error=1.0895e-5),
    }

    if positives["P1_C2R5_canonical_step4"]["decision"] != "FLOOR_CONVERGED":
        raise AssertionError(f"P1 did not pass: {positives['P1_C2R5_canonical_step4']}")
    if positives["P2_C2R4_off_route_plateau"]["decision"] != "FLOOR_CONVERGED":
        raise AssertionError(f"P2 did not pass: {positives['P2_C2R4_off_route_plateau']}")
    if positives["P3_R2B_M1_primary"]["decision"] != "PRIMARY_CONVERGED":
        raise AssertionError(f"P3 did not remain primary: {positives['P3_R2B_M1_primary']}")
    if any(value["decision"] != "REJECT" for value in negatives.values()):
        raise AssertionError(f"A negative control was accepted: {negatives}")

    result = {
        "schema_version": 1,
        "record_id": "QF-SOLVER-0.2.9-WP04-C2R6-FLOOR-AWARE-POLICY",
        "status": "FROZEN_BEFORE_M2",
        "start_sha": "2c52bf8196a7d47d14ce1784290580160de26590",
        "policy": {
            "policy_id": FLOOR_AWARE_POLICY_ID,
            "policy_version": FLOOR_AWARE_POLICY_VERSION,
            "enabled_only_by_explicit_option": True,
            "default_enabled": False,
            "plateau_window": FLOOR_AWARE_PLATEAU_WINDOW,
            "correction_eps_multiplier": FLOOR_AWARE_CORRECTION_EPS_MULTIPLIER,
            "component_ulp_multiplier": FLOOR_AWARE_COMPONENT_ULP_MULTIPLIER,
            "equilibrium_tolerance": FLOOR_AWARE_EQUILIBRIUM_TOLERANCE,
            "linear_backward_error_tolerance": FLOOR_AWARE_LINEAR_BACKWARD_ERROR_TOLERANCE,
            "relative_correction_definition": "norm(du)/max(norm(u), displacement_scale, tiny)",
            "state_resolution_definition": "max(||K||inf*eps*||u||2/scale, ||K*abs(spacing(u))||2/scale, 8*eps)",
            "threshold_derivation": (
                "8*eps bounds a small fixed sequence of norm/update roundings; "
                "4*component-ulp bounds componentwise displacement resolution. "
                "These constants were frozen from operation-count reasoning, not fitted to a residual multiplier."
            ),
            "acceptance_conjunction": [
                "finite residual and state",
                "relative residual is above primary tolerance but no larger than computed state-resolution estimate",
                "four normalized residual samples with spread no larger than the same estimate",
                "relative correction is at machine resolution",
                "linear backward error is within the existing R2 contract",
                "no line-search merit improvement exists",
                "caller supplies bounded force and moment equilibrium evidence",
                "caller supplies valid deformation/state evidence",
            ],
        },
        "source_capture": {
            "path": str(CAPTURE),
            "sha256": _sha256(CAPTURE),
            "size_bytes": CAPTURE.stat().st_size,
            "matrix_shape": [int(item) for item in matrix.shape],
            "matrix_nnz": int(matrix.nnz),
        },
        "state_resolution_diagnostic": {
            "displacement_norm_2": float(np.linalg.norm(displacement)),
            "displacement_norm_inf": float(np.max(np.abs(displacement), initial=0.0)),
            "machine_epsilon": float(np.finfo(float).eps),
            "matrix_inf_norm": float(np.max(np.asarray(np.abs(matrix).sum(axis=1)).ravel(), initial=0.0)),
            "matrix_inf_eps_u2_over_scale": positive_inputs["tangent"].shape[0],
            "policy_computed": positives["P1_C2R5_canonical_step4"],
        },
        "positive_controls": positives,
        "negative_controls": negatives,
        "controls_status": "PASS_ALL_POSITIVE_AND_NEGATIVE_CONTROLS",
        "production_policy_changed": False,
        "m3_run": False,
        "full_test_suite_run": False,
    }
    # Replace the placeholder with a real scalar without retaining matrix data.
    result["state_resolution_diagnostic"]["matrix_inf_eps_u2_over_scale"] = positives[
        "P1_C2R5_canonical_step4"
    ]["state_resolution_residual_estimate"]
    _write_json(RESULT, result)
    print(json.dumps(_jsonable(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
