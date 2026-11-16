"""Recover diagnostics from persisted method vectors without repeating any solve."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from research.j8_hex8.diagnostics import (
    CASE_FILES,
    _state_metrics,
    _write_json_atomic,
    backward_error_inf,
    canonical_sha256,
    partitioned_residuals,
    sha256,
)


ROOT = Path(__file__).resolve().parents[2]
INPUT_ROOT = ROOT / "research/j8_hex8/inputs"
CASE_IDS = {
    "regular": "j8_hex8_regular_nu04999_nx16",
    "near_degenerate": "j8_hex8_near_degenerate_nu0495_nx4",
}
COMMON_METHODS = {
    "numpy_direct",
    "scipy_positive_definite",
    "symmetric_diagonal_scaling",
    "scalar_equation_scale_1e-6",
    "scalar_equation_scale_1e6",
    "physical_length_unit_m_to_mm",
    "iterative_refinement",
}


def recompute_one_method(
    stiffness: np.ndarray,
    force: np.ndarray,
    fixed_mask: np.ndarray,
    coordinates: np.ndarray,
    displacement: np.ndarray,
    archived_displacement: np.ndarray,
    reference_length_m: float,
) -> dict[str, Any]:
    """Recompute residual, reaction, balance, and energy metrics from one saved vector."""
    metrics = _state_metrics(
        np.asarray(stiffness, dtype=np.float64),
        np.asarray(force, dtype=np.float64),
        np.asarray(displacement, dtype=np.float64),
        np.asarray(fixed_mask, dtype=bool),
        np.asarray(coordinates, dtype=np.float64),
        reference_length_m,
    )
    partition = partitioned_residuals(stiffness, force, displacement, fixed_mask)
    backward = backward_error_inf(
        partition["free_matrix"], partition["free_displacement"], partition["effective_free_rhs"]
    )
    reference_free = np.asarray(archived_displacement, dtype=np.float64)[~np.asarray(fixed_mask, dtype=bool)]
    method_free = np.asarray(displacement, dtype=np.float64)[~np.asarray(fixed_mask, dtype=bool)]
    return {
        "relative_displacement_change_from_archived": float(
            np.linalg.norm(method_free - reference_free)
            / max(float(np.linalg.norm(reference_free)), np.finfo(float).tiny)
        ),
        "free_residual_norm_n": metrics["free_residual_norm_n"],
        "backward_error": backward,
        "force_closure_n": metrics["balances"]["force_closure_n"],
        "force_closure_norm_n": metrics["balances"]["force_closure_norm_n"],
        "moment_closure_origin_nm": metrics["balances"]["moment_closure_origin_nm"],
        "moment_closure_origin_norm_nm": metrics["balances"]["moment_closure_origin_norm_nm"],
        "moment_contribution_scaled_indicator": metrics["balances"]["moment_contribution_scaled_indicator"],
        "energy": metrics["energy"],
    }


def recover_method_archive(
    case_key: str,
    diagnostic_result_path: Path,
    method_solutions_path: Path,
    frozen_manifest_path: Path,
    frozen_contract_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Recompute all metrics from saved vectors; this function never solves a system."""
    if case_key not in CASE_FILES:
        raise ValueError(f"unknown J8 case: {case_key}")
    original = json.loads(diagnostic_result_path.read_text(encoding="utf-8"))
    manifest = json.loads(frozen_manifest_path.read_text(encoding="utf-8"))
    case_contract = json.loads(frozen_contract_path.read_text(encoding="utf-8"))
    result_name, state_name = CASE_FILES[case_key]
    j7_result_path = INPUT_ROOT / result_name
    j7_state_path = INPUT_ROOT / state_name
    if canonical_sha256(frozen_contract_path) != original["source"]["contract_canonical_lf_sha256"]:
        raise RuntimeError("recovery contract does not match the original J8 execution hash")
    if manifest["analysis_source_commit"] != original["source"]["analysis_source_commit"]:
        raise RuntimeError("recovery manifest source commit differs from the original J8 run")
    if manifest["contract_canonical_lf_sha256"] != original["source"]["contract_canonical_lf_sha256"]:
        raise RuntimeError("recovery manifest contract digest differs from the original J8 run")
    if sha256(j7_result_path) != original["source"]["result_sha256"]:
        raise RuntimeError("recovery input J7 result digest differs from the original J8 run")
    if sha256(j7_state_path) != original["source"]["state_npz_sha256"]:
        raise RuntimeError("recovery input J7 state digest differs from the original J8 run")
    expected_solution_hash = original["output"]["method_solutions_sha256"]
    if sha256(method_solutions_path) != expected_solution_hash:
        raise RuntimeError("saved method-solution archive differs from the original J8 result hash")
    manifest_case = manifest["cases"][case_key]
    if (
        manifest_case["result_sha256"] != sha256(j7_result_path)
        or manifest_case["state_npz_sha256"] != sha256(j7_state_path)
    ):
        raise RuntimeError("frozen execution manifest does not bind the J7 result and matrix state")
    if original["case_id"] != CASE_IDS[case_key]:
        raise RuntimeError("incomplete J8 result belongs to a different case")
    with np.load(j7_state_path, allow_pickle=False) as archive:
        state = {key: archive[key] for key in archive.files}
    with np.load(method_solutions_path, allow_pickle=False) as archive:
        vectors = {key: archive[key] for key in archive.files}
    expected_methods = set(COMMON_METHODS)
    if case_key == "near_degenerate":
        expected_methods.add("mpmath_80_decimal_digits")
    observed_methods = {
        name.removesuffix("_displacement_m")
        for name in vectors
        if name.endswith("_displacement_m") and name != "archived_displacement_m"
    }
    if observed_methods != expected_methods:
        raise RuntimeError(f"saved solution vector inventory is incomplete: {sorted(observed_methods)}")

    recovered: dict[str, Any] = {}
    for method_name in sorted(expected_methods):
        vector_name = method_name + "_displacement_m"
        result = recompute_one_method(
            state["stiffness_n_per_m"],
            state["force_n"],
            state["fixed_dof_mask"],
            state["coordinates_m"],
            vectors[vector_name],
            state["displacement_m"],
            float(case_contract["model_scope"][case_key]["length_m"]),
        )
        original_method = original.get("methods", {}).get(method_name)
        result["status"] = "METRICS_RECOVERED_FROM_SAVED_VECTOR"
        result["elapsed_seconds"] = (
            original_method.get("elapsed_seconds") if original_method is not None else None
        )
        result["elapsed_time_provenance"] = (
            "ORIGINAL_RUN_CHECKPOINT" if original_method is not None else "NOT_PERSISTED_BY_ORIGINAL_CHECKPOINT"
        )
        if original_method:
            base_fields = {
                "status", "elapsed_seconds", "relative_displacement_change_from_archived",
                "free_residual_norm_n", "backward_error", "force_closure_n", "force_closure_norm_n",
                "moment_closure_origin_nm", "moment_closure_origin_norm_nm", "energy",
                "backward_error_status", "solution_archive_sha256",
            }
            result["original_checkpoint_metadata"] = {
                key: value for key, value in original_method.items() if key not in base_fields
            }
        recovered[method_name] = result

    output = {
        "schema": "qf-j8-hex8-recovered-method-metrics-v1",
        "classification": "POSTPROCESSING_OF_COMPLETED_RUN_NOT_A_NEW_SOLVE",
        "original_execution_status": original["execution_status"],
        "case_key": case_key,
        "case_id": original["case_id"],
        "source": {
            "original_j8_source_commit": original["source"]["analysis_source_commit"],
            "original_j8_repository_head": original["source"]["repository_head"],
            "original_contract_canonical_lf_sha256": original["source"]["contract_canonical_lf_sha256"],
            "frozen_manifest_sha256": sha256(frozen_manifest_path),
            "j7_result_sha256": sha256(j7_result_path),
            "j7_state_sha256": sha256(j7_state_path),
            "method_solutions_sha256": sha256(method_solutions_path),
            "incomplete_diagnostic_result_sha256": sha256(diagnostic_result_path),
            "recovery_source_sha256": sha256(Path(__file__).resolve()),
        },
        "method_inventory_complete": sorted(observed_methods) == sorted(expected_methods),
        "metrics_source": "saved full displacement vectors from the original J8 run; K, f, mask, coordinates, and contract-bound J7 state",
        "timing_limit": "per-method elapsed time is retained only where present in the original checkpoint; recovered metrics do not infer or invent timings",
        "archived_state_reconstruction": original["independent_reconstruction"],
        "original_checkpoint_method_inventory": sorted(original.get("methods", {})),
        "methods": recovered,
        "limits": [
            "no matrix solve or finite-element assembly was repeated during this recovery",
            "historical J7 criteria and verdicts are unchanged",
            "recovery confirms arithmetic from saved vectors, not physical accuracy of the common HEX8-SRI model",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(output_path, output)
    return output
