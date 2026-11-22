"""Double-precision, matrix-only G08 first-mode screening (not a certificate)."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from scipy.linalg import cholesky, eigh, solve_triangular

from research.g08_compare.capture import read_matrix_archive, sha256_file
from research.g08_compare.controlled import scope_for, validate_archive

HERE = Path(__file__).resolve().parent


class SpectralInputError(ValueError):
    """Captured data are malformed or not bound to the registered G08 scope."""


def _symmetry_defect(matrix: np.ndarray) -> float:
    return float(
        np.linalg.norm(matrix - matrix.T, ord=np.inf)
        / max(np.linalg.norm(matrix, ord=np.inf), np.finfo(float).tiny)
    )


def _inertia_screen(matrix: np.ndarray) -> dict[str, Any]:
    values = eigh((matrix + matrix.T) / 2.0, eigvals_only=True, check_finite=True, driver="evd")
    tolerance = 100.0 * np.finfo(float).eps * max(float(np.max(np.abs(values))), np.finfo(float).tiny)
    return {
        "negative": int(np.count_nonzero(values < -tolerance)),
        "near_zero": int(np.count_nonzero(np.abs(values) <= tolerance)),
        "positive": int(np.count_nonzero(values > tolerance)),
        "scale_aware_double_precision_tolerance": tolerance,
        "minimum_eigenvalue": float(values[0]),
        "maximum_eigenvalue": float(values[-1]),
    }


def screen_matrices(
    k0: Any,
    kg: Any,
    *,
    candidate_factor: float,
    candidate_bracket: Mapping[str, Any],
    candidate_mode: Any,
    free_dof_indices: Any,
    full_dof_count: int,
) -> dict[str, Any]:
    """Compute dense symmetric screens and retain an explicitly non-proof status."""
    initial = np.asarray(k0.toarray() if hasattr(k0, "toarray") else k0, dtype=np.float64)
    geometric = np.asarray(kg.toarray() if hasattr(kg, "toarray") else kg, dtype=np.float64)
    mode = np.asarray(candidate_mode, dtype=np.float64)
    free = np.asarray(free_dof_indices, dtype=np.int64)
    dimension = initial.shape[0] if initial.ndim == 2 else 0
    try:
        lower_bracket = float(candidate_bracket["lower"])
        upper_bracket = float(candidate_bracket["upper"])
        bracket_valid = (
            np.isfinite(lower_bracket)
            and np.isfinite(upper_bracket)
            and 0.0 < lower_bracket <= float(candidate_factor) <= upper_bracket
            and lower_bracket < upper_bracket
        )
    except (KeyError, TypeError, ValueError):
        bracket_valid = False
        lower_bracket, upper_bracket = 0.0, 0.0
    if (
        initial.ndim != 2
        or dimension == 0
        or initial.shape[1] != dimension
        or geometric.shape != initial.shape
        or mode.shape != (int(full_dof_count),)
        or free.shape != (dimension,)
        or np.unique(free).size != free.size
        or np.any(free < 0)
        or np.any(free >= int(full_dof_count))
        or not bracket_valid
        or not np.isfinite(initial).all()
        or not np.isfinite(geometric).all()
        or not np.isfinite(mode).all()
        or not np.isfinite(float(candidate_factor))
        or float(candidate_factor) <= 0
        or (free.size == dimension and np.linalg.norm(mode[free]) <= np.finfo(float).tiny)
    ):
        raise SpectralInputError("matrix, mode, or free-DOF dimensions and values are invalid")
    k0_defect, kg_defect = _symmetry_defect(initial), _symmetry_defect(geometric)
    symmetry_limit = 1e-12
    result: dict[str, Any] = {
        "classification": "NUMERICAL_OBSERVATION_ONLY",
        "method": "Dense binary64 symmetric eigenscreens; Cholesky K0 = L L.T, then eigensolve L^-1(-Kg)L^-T.",
        "dimension": dimension,
        "K0_symmetry_defect_inf_relative": k0_defect,
        "Kg_symmetry_defect_inf_relative": kg_defect,
        "symmetry_tolerance_predeclared": symmetry_limit,
        "candidate_factor": float(candidate_factor),
        "candidate_bracket": {"lower": lower_bracket, "upper": upper_bracket},
        "first_mode_status": "FIRST_MODE_NOT_ESTABLISHED",
        "error_controlled_inertia": "NOT_PERFORMED",
    }
    if max(k0_defect, kg_defect) > symmetry_limit:
        result["K0_status"] = "K0_SYMMETRY_OUTSIDE_SCREEN"
        result["root_rank_status"] = "NOT_EVALUATED"
        return result

    initial_symmetric = (initial + initial.T) / 2.0
    geometric_symmetric = (geometric + geometric.T) / 2.0
    k0_values = eigh(initial_symmetric, eigvals_only=True, check_finite=True, driver="evd")
    k0_tolerance = 100.0 * np.finfo(float).eps * max(float(np.max(np.abs(k0_values))), np.finfo(float).tiny)
    result.update(
        {
            "K0_status": "POSITIVE_DOUBLE_PRECISION_SCREEN" if k0_values[0] > k0_tolerance else "K0_POSITIVITY_INDETERMINATE",
            "K0_minimum_eigenvalue": float(k0_values[0]),
            "K0_maximum_eigenvalue": float(k0_values[-1]),
            "K0_condition_2_estimate": float(k0_values[-1] / k0_values[0]) if k0_values[0] > 0 else None,
            "K0_eigenvalue_screen_tolerance": k0_tolerance,
            "K0_eigenvalues_at_or_below_tolerance": int(np.count_nonzero(k0_values <= k0_tolerance)),
        }
    )
    if k0_values[0] <= k0_tolerance:
        result["root_rank_status"] = "NOT_EVALUATED_K0_POSITIVITY_INDETERMINATE"
        return result

    try:
        lower_factor = cholesky(initial_symmetric, lower=True, check_finite=True)
    except np.linalg.LinAlgError:
        result["K0_status"] = "K0_CHOLESKY_FAILED"
        result["root_rank_status"] = "NOT_EVALUATED"
        return result
    left = solve_triangular(lower_factor, -geometric_symmetric, lower=True, check_finite=True)
    transformed = solve_triangular(lower_factor, left.T, lower=True, check_finite=True).T
    transformed_defect = _symmetry_defect(transformed)
    transformed = (transformed + transformed.T) / 2.0
    transformed_values = eigh(transformed, eigvals_only=True, check_finite=True, driver="evd")
    positive_values = transformed_values[transformed_values > 0.0]
    positive_roots = np.sort(1.0 / positive_values)
    factor = float(candidate_factor)
    candidate_rank = int(np.argmin(np.abs(positive_roots - factor))) + 1 if positive_roots.size else None
    candidate_mode_reduced = mode[free]
    residual = initial_symmetric @ candidate_mode_reduced + factor * (geometric_symmetric @ candidate_mode_reduced)
    residual_scale = np.linalg.norm(initial_symmetric @ candidate_mode_reduced) + abs(factor) * np.linalg.norm(
        geometric_symmetric @ candidate_mode_reduced
    )
    bracket_lower, bracket_upper = float(candidate_bracket["lower"]), float(candidate_bracket["upper"])
    q_candidate = initial_symmetric + factor * geometric_symmetric
    q_lower = initial_symmetric + bracket_lower * geometric_symmetric
    q_upper = initial_symmetric + bracket_upper * geometric_symmetric
    result.update(
        {
            "transformed_S_symmetry_defect_inf_relative": transformed_defect,
            "positive_roots_numeric_count": int(positive_roots.size),
            "smallest_positive_roots_numeric": positive_roots[:5].tolist(),
            "candidate_root_rank_numeric": candidate_rank,
            "candidate_nearest_numeric_root_delta": (
                float(positive_roots[candidate_rank - 1] - factor) if candidate_rank is not None else None
            ),
            "candidate_next_root_relative_gap_numeric": (
                float((positive_roots[candidate_rank] - positive_roots[candidate_rank - 1]) / factor)
                if candidate_rank is not None and candidate_rank < positive_roots.size
                else None
            ),
            "candidate_generalized_residual": float(np.linalg.norm(residual) / max(residual_scale, np.finfo(float).tiny)),
            "candidate_solver_style_residual_recomputed": float(
                np.linalg.norm(residual) / max(np.linalg.norm(initial_symmetric @ candidate_mode_reduced), 1.0)
            ),
            "candidate_Q_inertia_numeric": _inertia_screen(q_candidate),
            "candidate_bracket_inertia_numeric": {
                "lower": _inertia_screen(q_lower),
                "upper": _inertia_screen(q_upper),
            },
            "root_rank_status": "RANK_1_NUMERICAL_SCREEN" if candidate_rank == 1 else "NOT_RANK_1_NUMERICAL_SCREEN",
            "positivity_and_inertia_certified": False,
            "first_mode_status": "FIRST_MODE_NOT_ESTABLISHED",
        }
    )
    return result


def analyze_capture(archive: Path, case_name: str) -> dict[str, Any]:
    """Verify one capture bundle and screen its stored binary64 matrices."""
    archive = Path(archive).resolve(strict=True)
    metadata = json.loads((archive / "capture.json").read_text(encoding="utf-8"))
    result = json.loads((archive / "result.json").read_text(encoding="utf-8"))
    scope = scope_for(str(metadata.get("scope")))
    receipt = {
        "scope": scope["id"],
        "source": scope["source"],
        "inputs_sha256": scope["inputs"],
        "resultant_ux": -1.0,
    }
    verdict = validate_archive(archive, scope=scope, receipt=receipt, pytest_status="PASSED")
    if verdict.get("archive_validation") != "VALID" or verdict.get("capture_validation") != "VALID":
        raise SpectralInputError("capture bundle did not pass the registered offline archive validator")
    arrays = read_matrix_archive(archive / "matrices.npz")
    capture_metadata = metadata
    run_evidence = _runner_evidence(archive, scope, result, capture_metadata)
    screen = screen_matrices(
        arrays["K0"],
        arrays["Kg"],
        candidate_factor=float(result["factor"]),
        candidate_bracket=result["diagnostics"]["critical_bracket"],
        candidate_mode=np.load(archive / "mode.npy", allow_pickle=False),
        free_dof_indices=arrays["free_dof_indices"],
        full_dof_count=int(metadata["full_dof_count"]),
    )
    summary = json.loads((HERE / "results" / "controlled-ab-retry-2026-11-22.json").read_text(encoding="utf-8"))
    summary_key = "before_retry" if case_name == "before" else "after"
    historical = summary[summary_key]
    historical_match = {
        "source": historical["source_commit"] == scope["source"],
        "inputs": historical["inputs_sha256"] == scope["inputs"],
        "mesh": historical["mesh_sha256"] == scope["mesh"],
        "candidate_factor_exact": float(historical["factor"]) == float(result["factor"]),
        "candidate_residual_exact": float(historical["eigenpair_residual_relative"]) == float(result["residual"]),
        "candidate_mode_sha256": historical["mode_sha256"] == capture_metadata["candidate"]["mode_sha256"],
        "first_mode_status_preserved": historical["first_mode_status"] == "FIRST_MODE_NOT_ESTABLISHED",
    }
    if not all(historical_match.values()):
        raise SpectralInputError("captured result differs from its historical A/B identity or candidate")
    dof_digest = hashlib.sha256(
        json.dumps(
            {
                "fixed": arrays["fixed_dof_indices"].tolist(),
                "free": arrays["free_dof_indices"].tolist(),
                "labels": arrays["dof_labels"].tolist(),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "case": case_name,
        "scope_id": scope["id"],
        "source_commit": scope["source"],
        "source_tree": scope["source_tree"],
        "solver_tree": scope["solver_tree"],
        "generator_blob": scope["generator_blob"],
        "capture_contract_sha256": scope["capture_contract_sha256"],
        "inputs_sha256": scope["inputs"],
        "mesh_sha256": scope["mesh"],
        "capture_json_sha256": sha256_file(archive / "capture.json"),
        "matrices_npz_sha256": sha256_file(archive / "matrices.npz"),
        "result_json_sha256": sha256_file(archive / "result.json"),
        "dof_map_sha256": dof_digest,
        "archive_validation": verdict["archive_validation"],
        "capture_validation": verdict["capture_validation"],
        "free_dofs": int(scope["free_dofs"]),
        "fixed_dofs": int(metadata["fixed_dof_count"]),
        "full_dofs": int(metadata["full_dof_count"]),
        "node_count": int(scope["nodes"]),
        "element_count": int(scope["elements"]),
        "matrix_fingerprints": {
            name: {
                "sha256_canonical_csr": capture_metadata["matrices"][name]["sha256_canonical_csr"],
                "shape": capture_metadata["matrices"][name]["shape"],
                "nnz": capture_metadata["matrices"][name]["nnz"],
                "symmetry_defect_relative_max_entry": capture_metadata["matrices"][name][
                    "symmetry_defect_relative_max_entry"
                ],
            }
            for name in ("K0", "Kg")
        },
        "u_pre_sha256": capture_metadata["preload"]["u_pre_sha256"],
        "candidate_mode_sha256": capture_metadata["candidate"]["mode_sha256"],
        "units": capture_metadata["units"],
        "pencil_sign_convention": capture_metadata["sign_convention"],
        "runtime_versions": {
            key: capture_metadata["runtime"][key] for key in ("python", "numpy", "scipy")
        },
        "historical_ab_scope_id": historical["scope_id"],
        "preload_status": verdict["preload_status"],
        "preload_final_relative_residual": float(result["diagnostics"]["preload_diagnostics"]["increments"][-1]["relative_residual"]),
        "candidate_factor": float(result["factor"]),
        "signed_critical_load": float(result["signed_load"]),
        "solver_candidate_residual_relative": float(result["residual"]),
        "historical_ab_result_match": historical_match,
        "solver_backend": result["diagnostics"]["backend"],
        "solver_eigen_formulation": result["diagnostics"]["eigen_formulation"],
        "runner_evidence": run_evidence,
        "screen": screen,
    }


def _runner_evidence(
    archive: Path,
    scope: Mapping[str, Any],
    result: Mapping[str, Any],
    capture_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Read and redact the neighboring run, preflight, and one-shot ledger records."""
    run_path = archive.parents[1] / "run.json"
    if not run_path.is_file():
        return {"status": "RUN_RECORD_NOT_INCLUDED"}
    try:
        run = json.loads(run_path.read_text(encoding="utf-8"))
        receipt_ref = run["preflight_receipt"]
        receipt_path = Path(receipt_ref["path"])
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        ledger_ref = run["attempt_ledger"]
        ledger_path = Path(ledger_ref["path"])
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise SpectralInputError("runner, preflight, or ledger evidence is unreadable") from exc
    nodeid = str(scope["nodeid"])
    ledger_entries = ledger.get("entries")
    one_shot_entries = ledger_entries.get(ledger_ref.get("key")) if isinstance(ledger_entries, dict) else None
    if (
        run.get("g08_scope_id") != scope["id"]
        or run.get("g08_source", {}).get("commit") != scope["source"]
        or run.get("runner_status") != "PASS"
        or run.get("state") != "G08_RESULT_ARCHIVED"
        or run.get("preload_status") != "CONVERGED"
        or run.get("spectral_status") != "COMPUTED"
        or run.get("archive_validation") != "VALID"
        or run.get("capture_validation") != "VALID"
        or run.get("return_code") != 0
        or run.get("attempt") != 1
        or run.get("contract_sha256") != scope.get("capture_contract_sha256")
        or run.get("mode_sha256") != capture_metadata.get("candidate", {}).get("mode_sha256")
        or run.get("captured_k0_sha256")
        != capture_metadata.get("matrices", {}).get("K0", {}).get("sha256_canonical_csr")
        or run.get("captured_kg_sha256")
        != capture_metadata.get("matrices", {}).get("Kg", {}).get("sha256_canonical_csr")
        or run.get("captured_u_pre_sha256") != capture_metadata.get("preload", {}).get("u_pre_sha256")
        or float(run.get("critical_factor")) != float(result.get("factor"))
        or float(run.get("critical_mode_residual_relative")) != float(result.get("residual"))
        or receipt_ref.get("sha256") != sha256_file(receipt_path)
        or receipt.get("state") != "PREFLIGHT_PASS"
        or receipt.get("scope_id") != scope["id"]
        or receipt.get("attempt_reserved") is not False
        or receipt.get("collected_nodeids") != [nodeid]
        or receipt.get("preflight_id") is None
        or ledger_ref.get("attempt") != 1
        or ledger.get("mandate_id") != run.get("mandate_id")
        or not isinstance(one_shot_entries, list)
        or len(one_shot_entries) != 1
        or not str(ledger_ref.get("key", "")).endswith(nodeid)
    ):
        raise SpectralInputError("runner/preflight/ledger identity or one-shot status differs from the capture scope")
    return {
        "status": "VERIFIED",
        "runner_state": run["state"],
        "runner_status": run["runner_status"],
        "return_code": run["return_code"],
        "attempt": run["attempt"],
        "scope_id": scope["id"],
        "nodeid": nodeid,
        "contract_sha256": run["contract_sha256"],
        "source_inventory_sha256": run["source_inventory_sha256"],
        "run_record_sha256": sha256_file(run_path),
        "preflight": {
            "id": receipt["preflight_id"],
            "status": receipt["state"],
            "sha256": receipt_ref["sha256"],
            "attempt_reserved": receipt["attempt_reserved"],
        },
        "ledger": {
            "filename": ledger_path.name,
            "sha256": sha256_file(ledger_path),
            "entries": len(one_shot_entries),
        },
        "preload_status": run["preload_status"],
        "spectral_status": run["spectral_status"],
        "archive_validation": run["archive_validation"],
        "capture_validation": run["capture_validation"],
        "elapsed_seconds": float(run["elapsed_seconds"]),
        "peak_rss_bytes": int(run["peak_rss_bytes"]),
        "peak_process_count": int(run["peak_process_count"]),
        "archive_bytes": int(run["archive_bytes"]),
        "stdout_bytes": int(run["stdout_bytes"]),
        "stderr_bytes": int(run["stderr_bytes"]),
    }


def compare_captures(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    before_factor, after_factor = float(before["candidate_factor"]), float(after["candidate_factor"])
    difference = after_factor - before_factor
    return {
        "classification": "MESH_AND_CONNECTIVITY_CHANGE_NUMERICAL_OBSERVATION",
        "before_source": before["source_commit"],
        "after_source": after["source_commit"],
        "free_dofs_before_after": [before["free_dofs"], after["free_dofs"]],
        "elements_before_after": [before["element_count"], after["element_count"]],
        "nodes_before_after": [before["node_count"], after["node_count"]],
        "candidate_factor_before_after": [before_factor, after_factor],
        "candidate_factor_difference_after_minus_before": difference,
        "candidate_factor_relative_difference": difference / before_factor,
        "signed_critical_load_before_after": [before["signed_critical_load"], after["signed_critical_load"]],
        "solver_residual_before_after": [before["solver_candidate_residual_relative"], after["solver_candidate_residual_relative"]],
        "first_mode_status": "FIRST_MODE_NOT_ESTABLISHED",
        "interpretation_limit": "The change combines connectivity and discretization; no isolated connectivity effect or physical buckling qualification is inferred.",
    }


def analyze_pair(before_archive: Path, after_archive: Path) -> dict[str, Any]:
    before = analyze_capture(before_archive, "before")
    after = analyze_capture(after_archive, "after")
    history = json.loads((HERE / "results" / "controlled-ab-retry-2026-11-22.json").read_text(encoding="utf-8"))
    historical_verdicts = {}
    for name, key in (
        ("initial_before_failure", "historical_before_attempt"),
        ("before_ab", "before_retry"),
        ("after_ab", "after"),
    ):
        item = history[key]
        historical_verdicts[name] = {
            "scope_id": item["scope_id"],
            "runner_status": item["runner_status"],
            "preload_status": item["preload_status"],
            "spectral_status": item["spectral_status"],
            "archive_validation": item["archive_validation"],
            "first_mode_status": item.get("first_mode_status", "NOT_ESTABLISHED"),
        }
    return {
        "schema": "qf-g08-first-mode-matrix-screen-v1",
        "classification": "DEVELOPMENT_ONLY_NUMERICAL_OBSERVATION",
        "interval_backend": {
            "python_flint_available": importlib.util.find_spec("flint") is not None,
            "gmpy2_available": importlib.util.find_spec("gmpy2") is not None,
            "mpmath_available_but_not_used_as_interval_certificate": importlib.util.find_spec("mpmath") is not None,
            "error_controlled_inertia": "NOT_PERFORMED",
        },
        "historical_verdicts_preserved": historical_verdicts,
        "cases": {"before": before, "after": after},
        "comparison": compare_captures(before, after),
        "mode_comparison": "NOT_PERFORMED; no common physical interpolation/projection was defined and tested.",
        "first_mode_status": "FIRST_MODE_NOT_ESTABLISHED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before_archive", type=Path)
    parser.add_argument("after_archive", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = analyze_pair(args.before_archive, args.after_archive)
    rendered = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
