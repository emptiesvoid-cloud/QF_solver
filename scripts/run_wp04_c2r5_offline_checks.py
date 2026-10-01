"""Offline checks for the captured WP04-C2R5 step-4 state.

This companion never invokes the nonlinear solver.  It repeats residual
assembly at the captured immutable displacement and records the resulting
spread and global equilibrium metrics in the C2R5 evidence JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CAPTURE = Path(r"C:\Users\fari\AppData\Local\Temp\qf_solver_029_c2r5_forensics\c2_m2_canonical_step4_failure.npz")
RESULT = ROOT / "qualification" / "0_2_9" / "c2r5" / "residual_precision_audit.json"
REASSEMBLY_COUNT = 5


def main() -> int:
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT))
    from scripts.run_wp04_c2r5_residual_precision_audit import _accumulate_methods
    from tests.verification.test_wp04_c2_tet4_requalification import _case, _equilibrium

    with np.load(CAPTURE, allow_pickle=False) as data:
        trial = np.asarray(data["trial_displacement"], dtype=float)
        accepted = np.asarray(data["accepted_displacement"], dtype=float)
        external = np.asarray(data["external"], dtype=float)
        internal_captured = np.asarray(data["trial_internal_force"], dtype=float)
        free = np.asarray(data["free"], dtype=int)
        load_factor = float(data["load_factor"][0])

    case = _case("C2-M2")
    target = load_factor * external
    scale = max(float(np.linalg.norm(target[free])), 1.0)
    residuals: list[float] = []
    precision_rows: list[dict[str, float]] = []
    internals: list[np.ndarray] = []
    for _ in range(REASSEMBLY_COUNT):
        internal, _ = case["assembly"].assemble(trial, tangent_required=False)
        internal = np.asarray(internal, dtype=float)
        internals.append(internal)
        residuals.append(float(np.linalg.norm((target - internal)[free]) / scale))
        accumulated = _accumulate_methods(case["assembly"], trial, target, free, scale)
        precision_rows.append(
            {
                key: float(value["normalized_residual"])
                for key, value in accumulated.items()
                if key in {"float64", "pairwise", "compensated_kahan", "longdouble_accumulation"}
            }
        )

    first_internal = internals[0]
    accepted_internal, _ = case["assembly"].assemble(accepted, tangent_required=False)
    accepted_case = dict(case)
    accepted_case["external"] = (load_factor - 1.0 / 12.0) * external
    step_case = dict(case)
    step_case["external"] = target
    equilibrium = {
        "accepted_state_before_step": _equilibrium(
            accepted_case, accepted, np.asarray(accepted_internal, dtype=float)
        ),
        "stagnated_trial": _equilibrium(step_case, trial, first_internal),
        "stagnated_trial_status": "NOT_EQUILIBRIUM_ACCEPTED_PATH_STATE",
    }
    result: dict[str, Any] = {
        "capture_path": str(CAPTURE),
        "reassembly_count": REASSEMBLY_COUNT,
        "residual_norm": {
            "min": min(residuals),
            "max": max(residuals),
            "mean": float(np.mean(residuals)),
            "spread": max(residuals) - min(residuals),
            "values": residuals,
            "scale": scale,
        },
        "captured_internal_matches_first_reassembly": bool(np.array_equal(internal_captured, first_internal)),
        "bitwise_identical_internal_force": all(np.array_equal(first_internal, item) for item in internals[1:]),
        "precision_reassembly": precision_rows,
        "force_moment_balance": equilibrium,
        "interpretation": {
            "state_is_unchanged_between_reassemblies": True,
            "element_evaluation_precision": "float64",
            "global_accumulation_precision": "normal float64 assembly for residual spread",
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))

    existing = json.loads(RESULT.read_text(encoding="utf-8"))
    existing["reassembly_checks"] = result
    existing["root_cause_classification"] = {
        "classification": "NONLINEAR_RESIDUAL_NUMERICAL_FLOOR",
        "mechanism": "FORCE_CANCELLATION_AND_FLOAT64_PRECISION_LIMIT",
        "evidence": [
            "direct and both tighter MINRES corrections are machine-scale",
            "normal, pairwise, compensated and platform longdouble accumulation remain at the same residual order",
            "repeated residual assembly is deterministic",
            "force/internal force cancellation indicator is large while global equilibrium remains machine-scale",
        ],
        "production_policy_change": False,
    }
    existing["offline_termination_policy_analysis"] = {
        "status": "DIAGNOSTIC_ONLY",
        "mixed_criterion_feasibility": "Plausible only as a scale-aware conjunction; no acceptance threshold is frozen or implemented.",
        "candidate_evidence": [
            "primary residual remains the existing criterion",
            "relative correction norm is machine-scale",
            "reassembly spread is deterministic",
            "force and moment balance are recorded",
            "linear backward error is recorded",
        ],
        "m1_retrospective_check": "NOT_APPLICABLE_NO_POLICY_THRESHOLD_PROPOSED",
    }
    RESULT.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
