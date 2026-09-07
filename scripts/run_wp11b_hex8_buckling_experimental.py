"""Run the WP11B bounded HEX8 buckling experimental-readiness campaign."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# ruff: noqa: E402
from solveur.api import solve_model
from solveur.core.errors import MeshValidationError, NumericalConvergenceError

from scripts.run_wp06_hex8_buckling import (
    _fixed_and_free,
    _input_digest,
    _matrix_diagnostics,
    _model,
)


BASELINE_SHA = "eed9fc7cdeec07f77cccfa647cfa167031668bef"
CONTRACT = ROOT / "qualification" / "0_2_8" / "wp11b_hex8_buckling_experimental_contract.json"
EVIDENCE = ROOT / "qualification" / "0_2_8" / "wp11b_hex8_buckling_experimental_vnv.json"
MATRIX = ROOT / "qualification" / "0_2_8" / "wp11b_hex8_buckling_experimental_matrix.json"


def _json_default(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=_json_default)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _model_with_e(model: Any, youngs_modulus: float) -> Any:
    model.materials["solid"] = dict(model.materials["solid"])
    model.materials["solid"]["E"] = float(youngs_modulus)
    return model


def _mode_metrics(model: Any, mode: np.ndarray) -> dict[str, Any]:
    fixed, free = _fixed_and_free(model)
    free_mode = np.asarray(mode, dtype=float)[free]
    y = np.asarray(mode, dtype=float)[1::3]
    z = np.asarray(mode, dtype=float)[2::3]
    y_norm = float(np.linalg.norm(y))
    z_norm = float(np.linalg.norm(z))
    total = max(float(np.linalg.norm(free_mode)), 1.0e-30)
    dominant = "UZ" if z_norm >= y_norm else "UY"
    return {
        "dominant_lateral_direction": dominant,
        "lateral_fraction": float(np.hypot(y_norm, z_norm) / total),
        "uy_norm": y_norm,
        "uz_norm": z_norm,
        "free_mode_norm": float(np.linalg.norm(free_mode)),
        "mode_norm": float(np.linalg.norm(mode)),
        "free_dof_count": int(free.size),
        "fixed_dof_count": int(fixed.size),
    }


def _solve_case(
    *,
    counts: tuple[int, int, int],
    length: float = 4.0,
    load_total: float = 1.0,
    youngs_modulus: float = 1_000.0,
    perturb: bool = False,
    invalid_orientation: bool = False,
) -> dict[str, Any]:
    model = _model(
        "cantilever",
        length=length,
        counts=counts,
        load_total=load_total,
        perturb=perturb,
        invalid_orientation=invalid_orientation,
    )
    _model_with_e(model, youngs_modulus)
    row: dict[str, Any] = {
        "counts": list(counts),
        "length": float(length),
        "load_total": float(load_total),
        "youngs_modulus": float(youngs_modulus),
        "node_count": model.node_count,
        "element_count": len(model.elements),
        "input_sha256": _input_digest(model, "cantilever"),
    }
    try:
        result = solve_model(model, enforce_policy=False)
        solver = result.solver
        factor = float(solver["critical_factor"])
        mode = np.asarray(result.displacements, dtype=float)
        diagnostics = _matrix_diagnostics(model, mode, factor)
        mode_metrics = _mode_metrics(model, mode)
        finite_factor = bool(np.isfinite(factor) and factor > 0.0)
        finite_mode = bool(np.all(np.isfinite(mode)))
        row.update(
            {
                "status": "PASS",
                "critical_factor": factor,
                "mode_metrics": mode_metrics,
                "solver_reported_residual_relative": float(solver["critical_mode_residual_relative"]),
                "matrix_diagnostics": diagnostics,
                "physical_checks": {
                    "critical_factor_positive_finite": finite_factor,
                    "mode_finite": finite_mode,
                    "dominant_lateral_UZ": mode_metrics["dominant_lateral_direction"] == "UZ",
                    "preload_residual": diagnostics["preload_relative_residual"] <= 1.0e-8,
                    "geometric_stiffness_symmetry": diagnostics["geometric_stiffness_symmetry_relative"] <= 1.0e-12,
                    "eigen_residual": diagnostics["eigen_residual_relative_recomputed"] <= 1.0e-7,
                    "compression_sign": diagnostics["compression_sign_detected"],
                },
            }
        )
        row["evidence_digest"] = _digest(
            {
                "input_sha256": row["input_sha256"],
                "critical_factor": factor,
                "mode": mode,
                "solver_residual": row["solver_reported_residual_relative"],
                "matrix_diagnostics": diagnostics,
                "mode_metrics": mode_metrics,
            }
        )
    except (MeshValidationError, NumericalConvergenceError, ValueError, RuntimeError) as exc:
        row.update(
            {
                "status": "EXPECTED_FAILURE" if invalid_orientation else "FAIL",
                "failure_type": type(exc).__name__,
                "failure_message": str(exc),
            }
        )
    return row


def _primary_campaign() -> dict[str, Any]:
    rows = [_solve_case(counts=level) for level in ((2, 2, 2), (4, 4, 4), (6, 6, 6))]
    factors = [float(row["critical_factor"]) for row in rows if row["status"] == "PASS"]
    adjacent_changes = [abs(factors[i] - factors[i - 1]) / abs(factors[i]) for i in range(1, len(factors))]
    internal_pass = all(
        row["status"] == "PASS" and all(row["physical_checks"].values()) for row in rows
    )
    return {
        "benchmark": "clamped solid cantilever block under uniform end-face dead compression",
        "rows": rows,
        "critical_factors": factors,
        "adjacent_relative_changes": adjacent_changes,
        "trend": "decreasing_positive_factor_with_refinement",
        "internal_gates": "PASS" if internal_pass else "FAIL",
        "refinement_characterization": "CHARACTERIZED_ONLY; no Euler convergence gate applied",
    }


def _scaling_and_robustness(reference: dict[str, Any]) -> dict[str, Any]:
    base = float(reference["critical_factor"])
    e_double = _solve_case(counts=(4, 4, 4), youngs_modulus=2_000.0)
    preload_double = _solve_case(counts=(4, 4, 4), load_total=2.0)
    length_double = _solve_case(counts=(4, 4, 4), length=8.0)
    perturb = _solve_case(counts=(4, 4, 4), perturb=True)
    invalid = _solve_case(counts=(1, 1, 1), invalid_orientation=True)

    def ratio(row: dict[str, Any]) -> float:
        return float(row["critical_factor"]) / base if row.get("status") == "PASS" else float("nan")

    e_ratio = ratio(e_double)
    preload_ratio = ratio(preload_double)
    perturb_ratio = ratio(perturb)
    return {
        "E_scaling": {
            "result": e_double,
            "expected_ratio": 2.0,
            "observed_ratio": e_ratio,
            "relative_error": abs(e_ratio - 2.0) / 2.0,
            "pass": np.isfinite(e_ratio) and abs(e_ratio - 2.0) / 2.0 <= 0.05,
        },
        "preload_scaling": {
            "result": preload_double,
            "expected_ratio": 0.5,
            "observed_ratio": preload_ratio,
            "relative_error": abs(preload_ratio - 0.5) / 0.5,
            "pass": np.isfinite(preload_ratio) and abs(preload_ratio - 0.5) / 0.5 <= 0.05,
        },
        "length_sensitivity": {
            "result": length_double,
            "reference_factor": base,
            "pass": length_double.get("status") == "PASS" and 0.0 < float(length_double["critical_factor"]) < base,
        },
        "moderate_perturbation": {
            "result": perturb,
            "observed_ratio": perturb_ratio,
            "relative_change": abs(perturb_ratio - 1.0) if np.isfinite(perturb_ratio) else float("inf"),
            "pass": perturb.get("status") == "PASS" and np.isfinite(perturb_ratio) and abs(perturb_ratio - 1.0) <= 0.10,
        },
        "invalid_orientation": {
            "result": invalid,
            "explicit_failure": invalid.get("status") == "EXPECTED_FAILURE",
        },
        "status": "PASS"
        if all(
            item["pass"]
            for item in (
                {"pass": bool(e_ratio) and bool(np.isfinite(e_ratio)) and abs(e_ratio - 2.0) / 2.0 <= 0.05},
                {"pass": bool(np.isfinite(preload_ratio)) and abs(preload_ratio - 0.5) / 0.5 <= 0.05},
                {"pass": length_double.get("status") == "PASS" and 0.0 < float(length_double["critical_factor"]) < base},
                {"pass": perturb.get("status") == "PASS" and np.isfinite(perturb_ratio) and abs(perturb_ratio - 1.0) <= 0.10},
                {"pass": invalid.get("status") == "EXPECTED_FAILURE"},
            )
        )
        else "FAIL",
    }


def _replay() -> dict[str, Any]:
    first = _solve_case(counts=(4, 4, 4))
    second = _solve_case(counts=(4, 4, 4))
    return {
        "required": 2,
        "first": first,
        "second": second,
        "deterministic": first.get("evidence_digest") == second.get("evidence_digest"),
        "comparison": "critical_factor, mode vector, residuals, matrix diagnostics and evidence digest",
    }


def main() -> int:
    primary = _primary_campaign()
    reference = primary["rows"][1]
    scaling = _scaling_and_robustness(reference)
    replay = _replay()
    result = {
        "schema_version": 1,
        "record_id": "QF-028-WP11B-HEX8-BUCKLING-EXPERIMENTAL-VNV",
        "work_package": "WP11B",
        "source_sha": BASELINE_SHA,
        "contract": "qualification/0_2_8/wp11b_hex8_buckling_experimental_contract.json",
        "benchmark": primary,
        "scaling_and_robustness": scaling,
        "replays": replay,
        "external_oracle": {"status": "NOT_AVAILABLE", "comparable": False, "reason": "No independent current comparable solver result was available; no correlation is claimed."},
        "historical_preservation": {
            "wp06_euler_fail_preserved": True,
            "wp06_convergence_fail_preserved": True,
            "wp06_records_rewritten": False,
            "historical_0_2_7_evidence_changed": False,
        },
        "integrity": {
            "numerical_source_changed": False,
            "bugs_found": False,
            "bugs_fixed": False,
            "predeclared_gates_changed": False,
        },
    }
    result["gates"] = {
        "primary_internal_checks": primary["internal_gates"],
        "physical_scaling": scaling["status"],
        "invalid_geometry": scaling["invalid_orientation"]["explicit_failure"],
        "replay_determinism": replay["deterministic"],
        "finite_eigenvalues": all(row.get("physical_checks", {}).get("critical_factor_positive_finite", False) for row in primary["rows"]),
        "external_oracle": "NOT_REQUIRED_FOR_EXPERIMENTAL",
    }
    result["decision"] = "EXPERIMENTAL_CANDIDATE" if all(value is True or value == "PASS" or value == "NOT_REQUIRED_FOR_EXPERIMENTAL" for value in result["gates"].values()) else "NOT_QUALIFIED"
    result["proposed_public_status"] = "EXPERIMENTAL" if result["decision"] == "EXPERIMENTAL_CANDIDATE" else "NOT_QUALIFIED"
    result["owner_gate_required"] = True
    EVIDENCE.write_text(json.dumps(result, indent=2, default=_json_default), encoding="utf-8")
    MATRIX.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "record_id": "QF-028-WP11B-HEX8-BUCKLING-EXPERIMENTAL-MATRIX",
                "work_package": "WP11B",
                "source_sha": BASELINE_SHA,
                "technical_decision": result["decision"],
                "proposed_public_status": result["proposed_public_status"],
                "owner_gate_required": True,
                "scope": "HEX8 linear eigenvalue buckling; linear-elastic prestress; valid bounded cantilever solid block; first positive mode; exploratory/research use only",
                "limitations": [
                    "WP06 Euler and mesh-convergence FAIL results remain unchanged and visible.",
                    "No general Euler prediction or convergence claim.",
                    "No external correlation claim.",
                    "No production, certification, nonlinear, post-buckling, arbitrary-mesh, mixed-mesh or multi-mode claim.",
                ],
                "integrity": result["integrity"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"decision": result["decision"], "gates": result["gates"], "replay": replay["deterministic"]}, indent=2, sort_keys=True))
    return 0 if result["decision"] == "EXPERIMENTAL_CANDIDATE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
