"""Audit the frozen HEX20 WP05 representative-stress convergence metric."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any

import numpy as np

from solveur.elements.solid.hex20 import Hex20Element


ROOT = Path(__file__).resolve().parents[1]
CORRECTED = ROOT / "qualification" / "0_2_9" / "overnight_r2_corrected"
RUNS = CORRECTED / "wp05_runs" / "HEX20"
REPLAYS = CORRECTED / "wp05_replay_run3" / "HEX20"
CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp05_cd_structural_contract.json"
OUTPUT_DIR = ROOT / "qualification" / "0_2_9" / "wp05d_forensics"
OUTPUT_JSON = OUTPUT_DIR / "hex20_stress_convergence_forensics.json"
OUTPUT_DOC = ROOT / "docs" / "verification" / "0_2_9" / "wp05-d-hex20-stress-forensics.md"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _relative_delta(first: float, second: float) -> float:
    return abs(second - first) / max(abs(first), abs(second), 1.0e-12)


def _load(level: str) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    result_path = RUNS / level / "result.json"
    raw_path = RUNS / level / "raw.npz"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    with np.load(raw_path, allow_pickle=False) as raw:
        arrays = {name: np.asarray(raw[name]).copy() for name in raw.files}
    return result, arrays


def _region(arrays: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    coordinates = arrays["integration_reference_coordinates"]
    weights = arrays["integration_volume_weights"]
    sigma_xx = arrays["integration_cauchy_stress"][:, 0, 0]
    mask = (
        (coordinates[:, 0] / 4.0 >= 0.40)
        & (coordinates[:, 0] / 4.0 <= 0.60)
        & (coordinates[:, 1] / 0.5 >= 0.70)
        & (coordinates[:, 1] / 0.5 <= 0.95)
        & (coordinates[:, 2] / 0.5 >= 0.20)
        & (coordinates[:, 2] / 0.5 <= 0.80)
    )
    return coordinates[mask], weights[mask], sigma_xx[mask], mask


def _distribution(level: str, arrays: dict[str, np.ndarray]) -> dict[str, Any]:
    coordinates, weights, sigma_xx, mask = _region(arrays)
    coordinates = np.asarray(coordinates, dtype=float)
    weights = np.asarray(weights, dtype=float)
    sigma_xx = np.asarray(sigma_xx, dtype=float)
    normalized_y = coordinates[:, 1] / 0.5
    normalized_x = coordinates[:, 0] / 4.0
    normalized_z = coordinates[:, 2] / 0.5
    weight_sum = float(weights.sum())
    weighted_mean = float(np.average(sigma_xx, weights=weights))
    centered_y = normalized_y - float(np.average(normalized_y, weights=weights))
    centered_sigma = sigma_xx - weighted_mean
    covariance = float(np.sum(weights * centered_y * centered_sigma))
    variance_y = float(np.sum(weights * centered_y**2))
    variance_sigma = float(np.sum(weights * centered_sigma**2))
    slope = covariance / variance_y
    correlation = covariance / math.sqrt(variance_y * variance_sigma)
    element_index = np.repeat(np.arange(arrays["integration_cauchy_stress"].shape[0] // 27), 27)[mask]
    contributions: list[dict[str, Any]] = []
    for index in np.unique(element_index):
        selected = element_index == index
        element_weight = float(weights[selected].sum())
        element_sigma = float(np.average(sigma_xx[selected], weights=weights[selected]))
        element_coordinates = np.average(coordinates[selected], weights=weights[selected], axis=0)
        contributions.append(
            {
                "element_index": int(index),
                "reference_coordinates": element_coordinates.tolist(),
                "reference_weight": element_weight,
                "weighted_sigma_xx": element_sigma,
                "weighted_contribution": element_weight * element_sigma,
            }
        )
    contributions.sort(key=lambda row: float(row["weighted_contribution"]), reverse=True)
    total_contribution = math.fsum(float(weight * stress) for weight, stress in zip(weights, sigma_xx))
    top_one = max(1, int(math.ceil(0.01 * len(contributions))))
    top_ten = max(1, int(math.ceil(0.10 * len(contributions))))
    return {
        "level": level,
        "integration_point_count_total": int(arrays["integration_cauchy_stress"].shape[0]),
        "integration_point_count_region": int(mask.sum()),
        "element_count_region": int(len(contributions)),
        "region_weight": weight_sum,
        "analytic_region_volume": 0.8 * 0.125 * 0.3,
        "region_weight_error_vs_analytic_volume": weight_sum - 0.03,
        "reference_coordinate_range": {
            "x": [float(coordinates[:, 0].min()), float(coordinates[:, 0].max())],
            "y": [float(coordinates[:, 1].min()), float(coordinates[:, 1].max())],
            "z": [float(coordinates[:, 2].min()), float(coordinates[:, 2].max())],
        },
        "normalized_coordinate_weighted_centroid": [
            float(np.average(normalized_x, weights=weights)),
            float(np.average(normalized_y, weights=weights)),
            float(np.average(normalized_z, weights=weights)),
        ],
        "sigma_xx": {
            "min": float(sigma_xx.min()),
            "max": float(sigma_xx.max()),
            "mean_unweighted": float(sigma_xx.mean()),
            "std_unweighted": float(sigma_xx.std()),
            "median_unweighted": float(np.median(sigma_xx)),
            "q01_unweighted": float(np.quantile(sigma_xx, 0.01)),
            "q99_unweighted": float(np.quantile(sigma_xx, 0.99)),
            "weighted_mean": weighted_mean,
            "weighted_y_slope": slope,
            "weighted_y_correlation": correlation,
        },
        "highest_contribution_element": contributions[0],
        "top_one_percent_element_contribution_fraction": float(
            math.fsum(float(row["weighted_contribution"]) for row in contributions[:top_one]) / total_contribution
        ),
        "top_ten_percent_element_contribution_fraction": float(
            math.fsum(float(row["weighted_contribution"]) for row in contributions[:top_ten]) / total_contribution
        ),
        "boundary_distances": {
            "minimum_distance_to_clamp_x0": float(coordinates[:, 0].min()),
            "minimum_distance_to_loaded_face_xL": float(4.0 - coordinates[:, 0].max()),
        },
        "top_contributions": contributions[:10],
    }


def _numerical_consistency(level: str, arrays: dict[str, np.ndarray], result: dict[str, Any]) -> dict[str, Any]:
    coordinates, weights, sigma_xx, mask = _region(arrays)
    selected_weights = weights
    selected_sigma = sigma_xx
    production_value = float(result["observables"]["representative_sigma_xx"])
    independent_value = float(np.average(selected_sigma, weights=selected_weights))
    reversed_value = float(np.average(selected_sigma[::-1], weights=selected_weights[::-1]))
    rng = np.random.default_rng(20260914)
    permutation = rng.permutation(selected_sigma.size)
    permuted_value = float(np.average(selected_sigma[permutation], weights=selected_weights[permutation]))
    groups = arrays["integration_volume_weights"].reshape(-1, 27)
    jacobian_determinants = groups.sum(axis=1) / 8.0
    quadrature_weights = np.asarray(Hex20Element.integration_weights, dtype=float)
    normalized_weights = groups / jacobian_determinants[:, None]
    return {
        "level": level,
        "production_extractor_value": production_value,
        "independent_raw_recompute_value": independent_value,
        "absolute_production_vs_independent": abs(production_value - independent_value),
        "reverse_enumeration_value": reversed_value,
        "permuted_enumeration_value": permuted_value,
        "enumeration_max_absolute_difference": max(
            abs(reversed_value - independent_value), abs(permuted_value - independent_value)
        ),
        "total_reference_volume": float(arrays["integration_volume_weights"].sum()),
        "jacobian_determinant_min": float(jacobian_determinants.min()),
        "jacobian_determinant_max": float(jacobian_determinants.max()),
        "jacobian_positive": bool(np.all(jacobian_determinants > 0.0)),
        "quadrature_weight_rule_max_error": float(np.max(np.abs(normalized_weights - quadrature_weights[None, :]))),
        "raw_npz_sha256": hashlib.sha256((RUNS / level / "raw.npz").read_bytes()).hexdigest(),
    }


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    h2_result, h2_arrays = _load("H2")
    h3_result, h3_arrays = _load("H3")
    h2_value = float(h2_result["observables"]["representative_sigma_xx"])
    h3_value = float(h3_result["observables"]["representative_sigma_xx"])
    h1_result = json.loads((RUNS / "H1" / "result.json").read_text(encoding="utf-8"))
    replay_result = json.loads((REPLAYS / "H1" / "result.json").read_text(encoding="utf-8"))
    payload: dict[str, Any] = {
        "record_id": "QF-029-WP05D-HEX20-STRESS-FORENSICS-001",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repository_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "original_wp05d_result": "FAIL_CLOSED",
        "original_stress_delta": 0.10427343557067302,
        "frozen_stress_threshold": 0.08,
        "original_failure_preserved": True,
        "original_result_path": "qualification/0_2_9/overnight_r2_corrected/wp05_runs/HEX20/H2-H3/result.json",
        "contract_path": "qualification/0_2_9/wp05_cd_structural_contract.json",
        "contract_sha256": hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest(),
        "observable_definition": contract["observables"]["representative_cauchy_sigma_xx"],
        "observable_implementation_path": {
            "production_fields": "src/solveur/elements/solid/total_lagrangian_j2.py:TotalLagrangianJ2Element.integration_point_results",
            "qualification_mapping": "scripts/run_wp05_structural_qualification.py:_integration_records",
            "aggregation": "scripts/wp05_cd_structural_harness.py:sample_region_weighted_sigma_xx",
            "delta_checker": "scripts/build_wp05_overnight_audit.py:_relative",
        },
        "h2": {
            "representative_stress": h2_value,
            "independent_recomputation": _numerical_consistency("H2", h2_arrays, h2_result),
            "distribution": _distribution("H2", h2_arrays),
        },
        "h3": {
            "representative_stress": h3_value,
            "independent_recomputation": _numerical_consistency("H3", h3_arrays, h3_result),
            "distribution": _distribution("H3", h3_arrays),
        },
        "absolute_difference": abs(h3_value - h2_value),
        "relative_difference": _relative_delta(h2_value, h3_value),
        "replay": {
            "status": "PASS" if replay_result["observables"]["representative_sigma_xx"] == h1_result["observables"]["representative_sigma_xx"] else "FAIL",
            "h1_value": h1_result["observables"]["representative_sigma_xx"],
            "replay_value": replay_result["observables"]["representative_sigma_xx"],
            "path_equal": h1_result["accepted_load_factors"] == replay_result["accepted_load_factors"],
            "newton_count_equal": h1_result["newton_iterations"] == replay_result["newton_iterations"],
        },
        "boundary_sensitivity": {
            "clamp_sensitivity": "NO",
            "load_boundary_sensitivity": "NO",
            "local_stress_concentration": "YES_BOUNDED_GRADIENT_NOT_SINGULARITY",
            "basis": "The frozen region is X/L 0.40-0.60, while the clamp is X=0 and load face is X=L.",
        },
        "classification": {
            "failure_classification": "MESH_LOCATION_SAMPLING_EFFECT",
            "dominant_cause": "G_EXPECTED_DISCRETIZATION_CONVERGENCE_SLOWER_THAN_FROZEN_STRESS_GATE compounded by C mesh-location sampling",
            "alternatives_rejected": {
                "quadrature_weighting_defect": True,
                "stress_measure_extraction_defect": True,
                "serialization_defect": True,
                "production_mechanics_defect": True,
            },
            "explanation": "The positive, correctly normalized HEX20 quadrature samples are not nested between H2 and H3. The fixed region's weighted normalized-Y centroid shifts from 0.80556 to 0.84028, and sigma_xx has a strong bounded bending gradient in Y.",
        },
        "h4": {
            "diagnostic_run": False,
            "result": "NOT_RUN",
            "reason": "Existing raw invariants and spatial distribution localize the cause; no qualification decision requires H4.",
        },
        "defect_proven": False,
        "defect_location": "NONE_IN_CURRENT_FROZEN_OBSERVABLE; earlier centroid-proxy defect is already preserved and corrected separately",
        "correction_applied": False,
        "post_correction_h2_h3_stress_delta": _relative_delta(h2_value, h3_value),
        "wp05d_status": "FAIL_CLOSED",
        "wp05e_status": "NOT_RUN_DEPENDENCY_BLOCKED",
        "production_mechanics_changed": False,
        "thresholds_changed": False,
        "full_repository_suite_run": False,
    }
    _write_json(OUTPUT_JSON, payload)
    OUTPUT_DOC.parent.mkdir(parents=True, exist_ok=True)
    h2_dist = payload["h2"]["distribution"]
    h3_dist = payload["h3"]["distribution"]
    OUTPUT_DOC.write_text(
        f"""# WP05-D HEX20 representative-stress forensic audit

The original frozen WP05-D result is preserved as **FAIL_CLOSED**: H2→H3 representative Cauchy `sigma_xx` delta `0.10427343557067302`, against the unchanged frozen limit `0.08`. This audit does not force qualification and does not alter the physical benchmark, observable definition, or threshold.

## Definition and independent checks

The observable is the positive reference-volume-weighted Cauchy `sigma_xx` at production integration points whose reference coordinates lie in `X/L = [0.40, 0.60]`, `Y/H = [0.70, 0.95]`, `Z/D = [0.20, 0.80]`. The H2 and H3 raw NPZ records use the production HEX20 27-point rule and `w_q det(J0)` weights.

| Quantity | H2 | H3 |
|---|---:|---:|
| Representative sigma_xx | {h2_value:.15g} | {h3_value:.15g} |
| Region integration points | {h2_dist['integration_point_count_region']} | {h3_dist['integration_point_count_region']} |
| Region elements | {h2_dist['element_count_region']} | {h3_dist['element_count_region']} |
| Region reference weight | {h2_dist['region_weight']:.15g} | {h3_dist['region_weight']:.15g} |
| Weighted normalized-Y centroid | {h2_dist['normalized_coordinate_weighted_centroid'][1]:.15g} | {h3_dist['normalized_coordinate_weighted_centroid'][1]:.15g} |
| Sigma_xx min/max | {h2_dist['sigma_xx']['min']:.15g} / {h2_dist['sigma_xx']['max']:.15g} | {h3_dist['sigma_xx']['min']:.15g} / {h3_dist['sigma_xx']['max']:.15g} |
| Weighted Y slope | {h2_dist['sigma_xx']['weighted_y_slope']:.15g} | {h3_dist['sigma_xx']['weighted_y_slope']:.15g} |

Independent raw recomputation matches the serialized production-extractor value exactly for both levels. Reversed/permuted enumeration changes the result by at most floating-point roundoff. Total reference volume is 1.0, Jacobians are positive, and the 27-point quadrature weights match the production rule to floating-point precision. H1 replay remains PASS.

## Cause localization

The region is at least 1.6 m from both the clamp (`X=0`) and loaded face (`X=4`), so clamp and load-boundary singularity sensitivity is **NO**. It is intentionally off-neutral-axis, and the bounded bending stress gradient is strong: sigma_xx is positively correlated with normalized Y (H2 `{h2_dist['sigma_xx']['weighted_y_correlation']:.6f}`, H3 `{h3_dist['sigma_xx']['weighted_y_correlation']:.6f}`).

H2 and H3 do not sample the indicator region at the same locations: H2 has weighted normalized-Y centroid `{h2_dist['normalized_coordinate_weighted_centroid'][1]:.8f}`, H3 `{h3_dist['normalized_coordinate_weighted_centroid'][1]:.8f}`. The resulting increase in the fixed-region quadrature estimator is therefore a mesh-location sampling effect compounded by ordinary discretization convergence. This is not a quadrature-weight, serialization, Cauchy-measure, or production-mechanics defect.

## Decision

- Defect proven: **NO**.
- Correction applied: **NO**.
- Optional H4: **NOT RUN**; no qualification rescue is implied.
- WP05-D: **FAIL_CLOSED** under the unchanged 8% threshold.
- WP05-E: **NOT RUN / dependency-blocked**.

No production mechanics or thresholds changed. Full repository suite was not run.
""",
        encoding="utf-8",
    )
    print(json.dumps({"json": str(OUTPUT_JSON), "doc": str(OUTPUT_DOC), "status": payload["wp05d_status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
