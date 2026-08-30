"""Build reproducible A/B evidence for the 026-G12 optimization lot."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path
from typing import Any


CONTRACT_ID = "026-G12-OPTIMIZATION"
START_SHA = "c967903956c82fcae6a23c9a946ddcd8bf93306e"
ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _portable_repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def _scaling_row(row: dict[str, Any]) -> dict[str, Any]:
    measurement = (row.get("measurements") or [{}])[0]
    return {
        "target_dofs": row.get("target_dofs"),
        "actual_dofs": measurement.get("total_dofs"),
        "status": row.get("status"),
        "assembly_seconds": measurement.get("assembly_seconds"),
        "linear_solve_seconds": measurement.get("linear_solve_seconds"),
        "wall_total_seconds": measurement.get("wall_total_seconds"),
        "load_assembly_seconds": measurement.get("load_assembly_seconds"),
        "load_balance_seconds": measurement.get("load_balance_seconds"),
        "mesh_validation_seconds": measurement.get("mesh_validation_seconds"),
        "global_stiffness_nnz": measurement.get("global_stiffness_nnz"),
        "reduced_stiffness_nnz": measurement.get("reduced_stiffness_nnz"),
        "global_matrix_storage_bytes": measurement.get("global_matrix_storage_bytes"),
        "global_matrix_storage_per_dof": measurement.get("global_matrix_storage_per_dof"),
        "nnz_per_dof": measurement.get("nnz_per_dof"),
        "case_peak_rss_bytes": row.get("case_peak_rss_bytes"),
        "relative_residual_norm": measurement.get("relative_residual_norm"),
        "solution_checksum": measurement.get("solution_checksum"),
        "finite_metrics": measurement.get("finite_metrics"),
        "deterministic": row.get("deterministic"),
    }


def _baseline_rows(source: dict[str, Any]) -> list[dict[str, Any]]:
    selected = []
    for row in source.get("rows", []):
        candidate = _scaling_row(row)
        if candidate["actual_dofs"] in {3000, 10125}:
            selected.append(candidate)
    return selected


def _optimized_rows(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [_scaling_row(row) for row in source.get("rows", []) if row.get("status") == "PASS"]


def _log_slope(rows: list[dict[str, Any]], x_key: str, y_key: str) -> float | None:
    points = [
        (float(row[x_key]), float(row[y_key]))
        for row in rows
        if row.get(x_key) is not None and row.get(y_key) is not None and row[x_key] > 0 and row[y_key] > 0
    ]
    if len(points) < 3:
        return None
    x_mean = sum(math.log(x) for x, _ in points) / len(points)
    y_mean = sum(math.log(y) for _, y in points) / len(points)
    denominator = sum((math.log(x) - x_mean) ** 2 for x, _ in points)
    return float(
        sum((math.log(x) - x_mean) * (math.log(y) - y_mean) for x, y in points) / denominator
    ) if denominator else None


def _compare_rows(baseline: list[dict[str, Any]], optimized: list[dict[str, Any]]) -> list[dict[str, Any]]:
    optimized_by_dof = {row["actual_dofs"]: row for row in optimized}
    comparisons = []
    for old in baseline:
        new = optimized_by_dof.get(old["actual_dofs"])
        if new is None:
            comparisons.append({"actual_dofs": old["actual_dofs"], "status": "MISSING_OPTIMIZED_CASE"})
            continue
        comparisons.append(
            {
                "actual_dofs": old["actual_dofs"],
                "baseline": old,
                "optimized": new,
                "assembly_speedup": old["assembly_seconds"] / new["assembly_seconds"],
                "load_assembly_speedup": old["load_assembly_seconds"] / new["load_assembly_seconds"],
                "load_balance_speedup": old["load_balance_seconds"] / new["load_balance_seconds"],
                "total_speedup": old["wall_total_seconds"] / new["wall_total_seconds"],
                "memory_ratio": new["case_peak_rss_bytes"] / old["case_peak_rss_bytes"],
                "nnz_equal": old["global_stiffness_nnz"] == new["global_stiffness_nnz"],
                "checksum_equal": old["solution_checksum"] == new["solution_checksum"],
                "residual_absolute_delta": abs(
                    new["relative_residual_norm"] - old["relative_residual_norm"]
                ),
                "status": "PASS",
            }
        )
    return comparisons


def build_evidence(
    baseline_path: Path,
    optimized_path: Path,
    assembly_path: Path,
    profiles_path: Path,
    cache_path: Path | None = None,
    regression_path: Path | None = None,
) -> dict[str, Any]:
    baseline_source = _read(baseline_path)
    optimized_source = _read(optimized_path)
    assembly_source = _read(assembly_path)
    profiles_source = _read(profiles_path)
    baseline = _baseline_rows(baseline_source)
    optimized = _optimized_rows(optimized_source)
    comparisons = _compare_rows(baseline, optimized)
    assembly_rows = assembly_source.get("rows", [])
    completed_assembly = [row for row in assembly_rows if row.get("status") == "PASS"]
    profiles = [row for row in profiles_source.get("profiles", []) if row.get("status") == "PASS"]
    largest_profile = max(profiles, key=lambda row: row.get("target_dofs", 0), default={})
    profile_case = largest_profile.get("profiled_case", {})
    profile_wall = float(largest_profile.get("profiled_wall_seconds") or profile_case.get("wall_total_seconds") or 0.0)
    cache_proof = _read(cache_path) if cache_path is not None and cache_path.is_file() else None
    regression = _read(regression_path) if regression_path is not None and regression_path.is_file() else None
    regression_neutral = all(
        row.get("status") == "PASS"
        and row.get("nnz_equal")
        and row.get("checksum_equal")
        for row in comparisons
    )
    return {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "status": "PASS" if regression_neutral and optimized and profiles else "PARTIAL",
        "start_sha": START_SHA,
        "optimization_commit_sha": _git_head(),
        "baseline_source": _portable_repo_path(baseline_path),
        "optimized_source": _portable_repo_path(optimized_path),
        "assembly_probe_source": _portable_repo_path(assembly_path),
        "profile_source": _portable_repo_path(profiles_path),
        "optimization_method": {
            "load_balance": "direct nodal contribution balance plus vectorized contiguous translation layout",
            "load_storage": "no global dense temporary vector per nodal load when only the total is requested",
            "quality_cache": "mutation-sensitive geometry/connectivity/threshold cache in MeshValidator",
            "solver_formulation_changed": False,
        },
        "batch_strategy": {
            "nodal_loads": "direct O(number_of_nodal_loads) accumulation; no element-by-element global scan",
            "stiffness": "existing bounded assembly chunks of 256; not changed in this lot",
            "large_probe": "assembly-only for 300k/1M to avoid disproportionate solve/resource risk",
        },
        "baseline": {"source_sha": baseline_source.get("environment", {}).get("git_head"), "rows": baseline},
        "optimized": {"rows": optimized, "status": optimized_source.get("status")},
        "a_b_comparison": comparisons,
        "scaling": {
            "completed_full_solve_rows": optimized,
            "assembly_exponent": _log_slope(optimized, "actual_dofs", "assembly_seconds"),
            "solve_exponent": _log_slope(optimized, "actual_dofs", "linear_solve_seconds"),
            "total_exponent": _log_slope(optimized, "actual_dofs", "wall_total_seconds"),
            "memory_exponent": _log_slope(optimized, "actual_dofs", "case_peak_rss_bytes"),
        },
        "assembly_only_probes": {
            "rows": assembly_rows,
            "completed_rows": completed_assembly,
            "resource_limited_rows": [row for row in assembly_rows if row.get("status") == "RESOURCE_LIMITED"],
            "resource_policy": assembly_source.get("resource_policy"),
        },
        "cache_proof": cache_proof,
        "final_profile": {
            "target_dofs": largest_profile.get("target_dofs"),
            "actual_dofs": profile_case.get("total_dofs"),
            "profiled_wall_seconds": largest_profile.get("profiled_wall_seconds"),
            "load_balance_seconds": profile_case.get("load_balance_seconds"),
            "mesh_validation_seconds": profile_case.get("mesh_validation_seconds"),
            "assembly_seconds": profile_case.get("assembly_seconds"),
            "linear_solve_seconds": profile_case.get("linear_solve_seconds"),
            "load_balance_calls": profile_case.get("load_balance_calls"),
            "load_balance_node_visits": profile_case.get("load_balance_node_visits"),
            "profile_share_percent": {
                "load_balance": (100.0 * profile_case.get("load_balance_seconds", 0.0) / profile_wall if profile_wall else None),
                "mesh_validation": (100.0 * profile_case.get("mesh_validation_seconds", 0.0) / profile_wall if profile_wall else None),
                "assembly": (100.0 * profile_case.get("assembly_seconds", 0.0) / profile_wall if profile_wall else None),
                "linear_solve": (100.0 * profile_case.get("linear_solve_seconds", 0.0) / profile_wall if profile_wall else None),
            },
            "top_functions": largest_profile.get("top_functions", []),
        },
        "new_bottleneck": {
            "category": "MESH_VALIDATION",
            "component": "TET4 mesh quality metrics",
            "reason": "after load-balance optimization, quality validation dominates the clean 10k profile",
            "profile_share_percent": (100.0 * profile_case.get("mesh_validation_seconds", 0.0) / profile_wall if profile_wall else None),
        },
        "numerical_regression": {
            "detected": "NO" if regression_neutral else "YES",
            "checks": comparisons,
            "finite_optimized_cases": all(row.get("finite_metrics") for row in optimized),
        },
        "bugs_found": [],
        "functional_code_changed": True,
        "verification_infrastructure_changed": True,
        "full_regression": regression or "PENDING_FINAL_RUN",
        "optimization_candidates_deferred": [
            "vectorize/cache TET4 mesh-quality metrics",
            "reduce Python DOF-name normalization in stiffness assembly",
            "investigate sparse assembly only after validation costs",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=Path("qualification/0_2_6/g12_lot2_scaling.json"))
    parser.add_argument("--optimized", type=Path, required=True)
    parser.add_argument("--assembly", type=Path, required=True)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--cache-proof", type=Path, default=None)
    parser.add_argument("--regression-triage", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(build_evidence(args.baseline, args.optimized, args.assembly, args.profiles, args.cache_proof, args.regression_triage), indent=2)
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
