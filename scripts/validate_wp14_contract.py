"""Validate the declarative WP14 large-scale execution contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_7" / "wp14_execution_contract.json"


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("WP14 contract root must be an object")
    return value


def _expected_counts(nx: int, ny: int, nz: int) -> tuple[int, int, int]:
    nodes = (nx + 1) * (ny + 1) * (nz + 1)
    elements = 6 * nx * ny * nz
    return nodes, elements, 3 * nodes


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "contract_id",
        "work_package",
        "gate",
        "start_sha",
        "reference_model",
        "subscale_cases",
        "execution_environment",
        "solver_contract",
        "spd_cg_contract",
        "acceptance_metrics",
        "replay_policy",
        "resource_safety",
        "three_million_ladder",
        "evidence_schema",
    }
    errors.extend(f"missing root field: {key}" for key in sorted(required - contract.keys()))
    reference = contract.get("reference_model", {})
    mesh = reference.get("mesh", {}) if isinstance(reference, dict) else {}
    dims = tuple(mesh.get(key, 0) for key in ("nx", "ny", "nz"))
    if dims != (69, 69, 69):
        errors.append(f"reference dimensions must be 69^3, got {dims}")
    expected = _expected_counts(*dims)
    actual = tuple(mesh.get(key) for key in ("node_count", "element_count", "true_dof"))
    if actual != expected:
        errors.append(f"reference counts mismatch: expected {expected}, got {actual}")
    if mesh.get("true_dof", 0) < 1_000_000:
        errors.append("reference model is below the 1M true-DOF minimum")
    if mesh.get("decomposition") != "six" or mesh.get("tetrahedra_per_brick") != 6:
        errors.append("reference model must use the six-TET structured decomposition")

    subscale = contract.get("subscale_cases", [])
    ids = [case.get("case_id") for case in subscale]
    if len(ids) < 3 or len(ids) != len(set(ids)):
        errors.append("at least three unique subscale cases are required")
    for case in subscale:
        expected_case = _expected_counts(case["nx"], case["ny"], case["nz"])
        actual_case = tuple(case.get(key) for key in ("node_count", "element_count", "true_dof"))
        if actual_case != expected_case:
            errors.append(f"subscale count mismatch for {case.get('case_id')}: {actual_case} != {expected_case}")

    environment = contract.get("execution_environment", {})
    for key in ("os", "cpu", "python", "numpy", "scipy", "blas", "threads"):
        if key not in environment:
            errors.append(f"missing frozen environment field: {key}")
    if environment.get("threads") != 1:
        errors.append("execution must freeze one numerical thread")
    if any(value != "1" for value in environment.get("thread_environment", {}).values()):
        errors.append("thread environment variables must all be set to one")

    solver = contract.get("solver_contract", {})
    for key in ("reference_backend", "reference_solver", "reference_preconditioner", "rtol", "atol", "max_iterations", "random_seed", "seed_policy", "fallback_policy"):
        if key not in solver:
            errors.append(f"missing solver contract field: {key}")
    if solver.get("backend_selection") != "explicit_only" or solver.get("fallback_policy", "").startswith("none") is False:
        errors.append("backend selection must be explicit and fallback-free")

    metrics = contract.get("acceptance_metrics", {})
    if metrics.get("tolerances_status") != "FROZEN_BEFORE_WP15_WP16":
        errors.append("WP14 tolerances are not marked frozen before execution")
    if metrics.get("post_result_retuning") is not False:
        errors.append("post-result tolerance retuning must be forbidden")
    replay = contract.get("replay_policy", {})
    if replay.get("required_replays_for_1m") != 2 or replay.get("mismatch_verdict") != "INVALID_EVIDENCE":
        errors.append("1M replay policy is incomplete")

    resource = contract.get("resource_safety", {})
    for key in ("preflight_required", "memory_rule", "disk_rule", "timeout_seconds_1m", "oom_policy", "timeout_policy", "no_claim_on_resource_limited"):
        if key not in resource:
            errors.append(f"missing resource safety field: {key}")
    if resource.get("preflight_required") is not True or resource.get("no_claim_on_resource_limited") is not True:
        errors.append("resource preflight and no-claim rule are mandatory")

    ladder = contract.get("three_million_ladder", {})
    for tier in ("bronze", "silver", "gold"):
        if ladder.get(tier, {}).get("status") != "DEFINED":
            errors.append(f"3M {tier} tier is not defined")
    if ladder.get("bronze", {}).get("solve_required") is not False:
        errors.append("Bronze must not require a solve or create a solve claim")

    evidence = contract.get("evidence_schema", {})
    fields = evidence.get("required_fields", [])
    for key in ("source_sha", "input_digest", "hardware", "backend", "true_dof", "residual_relative", "equilibrium_relative", "strain_energy", "verdict"):
        if key not in fields:
            errors.append(f"evidence schema missing required field: {key}")
    if evidence.get("resource_limited_is_not_pass") is not True:
        errors.append("resource-limited evidence must not be PASS")
    return errors


def main() -> int:
    try:
        errors = validate_contract(load_contract())
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"WP14 contract FAIL: {exc}")
        return 1
    if errors:
        print("WP14 contract FAIL:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("WP14 contract PASS: reference model, environment, solver, SPD/CG, replay, resource and 3M contracts are frozen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
