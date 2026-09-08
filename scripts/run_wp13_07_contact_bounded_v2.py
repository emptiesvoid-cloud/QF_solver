"""Prospective WP13-07 V2 bounded frictionless-contact evidence campaign.

V1 remains immutable.  V2 evaluates the same frozen cases but replaces the
inapplicable final-load energy identity with the predeclared, active-set-aware
incremental external-work integral.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

import run_wp13_07_contact_bounded as v1
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp13_07_contact_bounded_v2_contract.json"
OUTPUT_DIR = ROOT / "qualification" / "0_2_8" / "wp13_07_contact_bounded_v2"
EVIDENCE_PATH = OUTPUT_DIR / "wp13_07_contact_v2_evidence.json"
EXPECTED_CONTRACT_ID = "WP13-07-CONTACT-BOUNDED-002"
EXPECTED_CONTRACT_SHA = "d7f9105fcad22d9df164692d9bbc0a483ca77ded5f18395bd647403790d0bf2c"
V1_CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp13_07_contact_bounded_contract.json"
V1_EVIDENCE_PATH = ROOT / "qualification" / "0_2_8" / "wp13_07_contact_bounded" / "wp13_07_contact_evidence.json"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _digest(value: Any) -> str:
    return hashlib.sha256(v1._canonical(v1._jsonable(value)).encode("utf-8")).hexdigest()


def _environment() -> dict[str, str]:
    import numpy
    import scipy

    return {"python": sys.version, "platform": platform.platform(), "numpy": numpy.__version__, "scipy": scipy.__version__}


def _load_contract() -> tuple[dict[str, Any], str, str]:
    raw = CONTRACT_PATH.read_bytes()
    contract = json.loads(raw.decode("utf-8"))
    sha = hashlib.sha256(raw).hexdigest()
    _assert(contract["contract_id"] == EXPECTED_CONTRACT_ID, "Unexpected V2 contract ID.")
    _assert(sha == EXPECTED_CONTRACT_SHA, "Frozen V2 contract digest mismatch.")
    _assert(contract["created_before_campaign"], "V2 contract is not predeclared.")
    commit = _git("log", "-1", "--format=%H", "--", str(CONTRACT_PATH.relative_to(ROOT)))
    _assert(bool(commit), "V2 contract has no Git provenance.")
    return contract, sha, commit


def _mechanical_contract(contract: dict[str, Any]) -> dict[str, Any]:
    """Adapt V1 mechanical helpers without reusing its obsolete energy gate."""
    helper_contract = copy.deepcopy(contract)
    helper_contract["gates"]["energy"].update({
        "threshold": float("inf"),
        "identity": "V1 helper compatibility only; V2 replaces this calculation.",
        "external_work": "not evaluated by V1 helper",
    })
    return helper_contract


def _assemble_energy_system(raw: dict[str, Any]) -> dict[str, Any]:
    model = FiniteElementModel.from_raw(**copy.deepcopy(raw))
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    stiffness = np.asarray(assembler.assemble_stiffness(model, dofs).toarray(), dtype=float)
    load_reference = np.asarray(assembler.assemble_loads(model, dofs), dtype=float)
    fixed = np.asarray(assembler.fixed_indices(model, dofs), dtype=int)
    free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
    row, gap0, geometry = v1._contact_row(raw, model)
    return {
        "stiffness": stiffness,
        "load_reference": load_reference,
        "fixed": fixed,
        "free": free,
        "Kff": stiffness[np.ix_(free, free)],
        "Ffree": load_reference[free],
        "cfull": row,
        "cfree": row[free],
        "gap0": gap0,
        "penalty": float(raw["analysis"]["parameters"]["contact_penalty"]),
        "geometry": geometry,
    }


def _branch(system: dict[str, Any], active: bool) -> dict[str, np.ndarray]:
    matrix = np.asarray(system["Kff"], dtype=float).copy()
    rhs_offset = np.zeros_like(system["Ffree"], dtype=float)
    if active:
        c = np.asarray(system["cfree"], dtype=float)
        penalty = float(system["penalty"])
        matrix += penalty * np.outer(c, c)
        rhs_offset = -penalty * float(system["gap0"]) * c
    return {"A": np.linalg.solve(matrix, system["Ffree"]), "b": np.linalg.solve(matrix, rhs_offset)}


def _branch_displacement(system: dict[str, Any], branch: dict[str, np.ndarray], load_factor: float) -> np.ndarray:
    displacement = np.zeros_like(system["load_reference"], dtype=float)
    displacement[system["free"]] = branch["A"] * load_factor + branch["b"]
    return displacement


def _branch_root(system: dict[str, Any], branch: dict[str, np.ndarray]) -> float:
    denominator = float(np.asarray(system["cfree"]) @ branch["A"])
    numerator = float(system["gap0"] + np.asarray(system["cfree"]) @ branch["b"])
    _assert(abs(denominator) > 1.0e-15, "Contact transition root is indeterminate.")
    return -numerator / denominator


def _branch_work(system: dict[str, Any], branch: dict[str, np.ndarray], start: float, end: float) -> float:
    increment = branch["A"] * 0.5 * (end * end - start * start) + branch["b"] * (end - start)
    return float(np.asarray(system["Ffree"]) @ increment)


def _potential(system: dict[str, Any], displacement: np.ndarray) -> tuple[float, float, float, float]:
    strain = float(0.5 * displacement @ (system["stiffness"] @ displacement))
    gap = float(system["gap0"] + system["cfull"] @ displacement)
    contact = float(0.5 * system["penalty"] * max(-gap, 0.0) ** 2)
    return strain, contact, strain + contact, gap


def _run_path(contract: dict[str, Any], case_name: str, *, penalty: float | None = None) -> dict[str, Any]:
    raw_full = v1._case_raw(contract, case_name, penalty)
    load_path = [float(item) for item in raw_full["analysis"]["parameters"]["load_path"]]
    helper_contract = _mechanical_contract(contract)
    endpoints: list[dict[str, Any]] = []
    final_record: dict[str, Any] | None = None
    for index in range(len(load_path)):
        raw_prefix = copy.deepcopy(raw_full)
        raw_prefix["analysis"]["parameters"]["load_path"] = load_path[: index + 1]
        record = v1._run_case(raw_prefix, helper_contract, include_oracle=index == len(load_path) - 1)
        endpoints.append({
            "load_factor": load_path[index],
            "displacement": np.asarray(record["displacement"], dtype=float),
            "reactions": np.asarray(record["reactions"], dtype=float),
            "gap": float(record["final_gap"]),
            "penetration": float(max(-record["final_gap"], 0.0)),
            "contact_force": float(record["contact_force_magnitude"]),
            "active": bool(record["active_contact_sets"][-1]),
            "solver_status": record["solver_status"],
            "free_residual": float(record["force_balance"]["maximum_free_relative_residual"]),
        })
        final_record = record
    _assert(final_record is not None, "Declared load path is empty.")
    system = _assemble_energy_system(raw_full)
    inactive = _branch(system, False)
    active = _branch(system, True)
    absolute_tol = float(contract["gates"]["energy"]["absolute_tolerance"])
    relative_tol = float(contract["gates"]["energy"]["relative_tolerance"])
    local_tol = float(contract["gates"]["energy"]["incremental_local_absolute_tolerance"])
    all_points = [{"load_factor": 0.0, "displacement": np.zeros_like(system["load_reference"]), "active": False, "gap": float(system["gap0"]), "penetration": 0.0, "contact_force": 0.0, "solver_status": "INITIAL"}] + endpoints
    increments: list[dict[str, Any]] = []
    cumulative_work = 0.0
    cumulative_trapezoid = 0.0
    endpoint_errors: list[float] = []
    transition_root_errors: list[float] = []
    for step, (previous, current) in enumerate(zip(all_points, all_points[1:]), start=1):
        lambda_a = float(previous["load_factor"])
        lambda_b = float(current["load_factor"])
        state_a = bool(previous["active"])
        state_b = bool(current["active"])
        before = active if state_a else inactive
        after = active if state_b else inactive
        expected_current = _branch_displacement(system, after, lambda_b)
        endpoint_error = float(np.linalg.norm(current["displacement"] - expected_current) / max(np.linalg.norm(expected_current), 1.0))
        endpoint_errors.append(endpoint_error)
        transition = ("active_to_active" if state_a else "inactive_to_inactive") if state_a == state_b else ("inactive_to_active" if state_b else "active_to_inactive")
        roots: list[float] = []
        segments: list[tuple[dict[str, np.ndarray], float, float]]
        if state_a == state_b:
            segments = [(before, lambda_a, lambda_b)]
        else:
            root_before = _branch_root(system, before)
            root_after = _branch_root(system, after)
            transition_root_errors.append(abs(root_before - root_after))
            root = 0.5 * (root_before + root_after)
            lower, upper = min(lambda_a, lambda_b), max(lambda_a, lambda_b)
            _assert(lower - 1e-12 <= root <= upper + 1e-12, f"Transition root {root} lies outside declared load interval.")
            roots = [root]
            segments = [(before, lambda_a, root), (after, root, lambda_b)]
        exact_work = float(sum(_branch_work(system, branch, start, end) for branch, start, end in segments))
        trapezoid_work = float(0.5 * (lambda_a + lambda_b) * system["load_reference"] @ (current["displacement"] - previous["displacement"]))
        strain_a, contact_a, potential_a, _ = _potential(system, previous["displacement"])
        strain_b, contact_b, potential_b, _ = _potential(system, current["displacement"])
        local_error = float(potential_b - potential_a - exact_work)
        cumulative_work += exact_work
        cumulative_trapezoid += trapezoid_work
        increments.append({
            "step": step,
            "load_factor_start": lambda_a,
            "load_factor_end": lambda_b,
            "active_set_transition": transition,
            "transition_load_factors": roots,
            "runtime_active_set_start": "active" if state_a else "inactive",
            "runtime_active_set_end": "active" if state_b else "inactive",
            "gap_start": float(previous["gap"]),
            "gap_end": float(current["gap"]),
            "penetration_start": float(previous["penetration"]),
            "penetration_end": float(current["penetration"]),
            "contact_force_end": float(current["contact_force"]),
            "U_strain_start": strain_a,
            "U_contact_start": contact_a,
            "U_strain_end": strain_b,
            "U_contact_end": contact_b,
            "external_incremental_work_exact": exact_work,
            "external_incremental_work_endpoint_trapezoid_characterization": trapezoid_work,
            "cumulative_external_work_exact": cumulative_work,
            "cumulative_endpoint_trapezoid_characterization": cumulative_trapezoid,
            "local_energy_balance_error": local_error,
            "local_energy_gate_pass": bool(abs(local_error) <= local_tol),
            "runtime_endpoint_oracle_relative_error": endpoint_error,
        })
    final_displacement = np.asarray(endpoints[-1]["displacement"], dtype=float)
    strain, contact, total, final_gap = _potential(system, final_displacement)
    balance = float(total - cumulative_work)
    relative = float(abs(balance) / max(abs(cumulative_work), 1.0))
    ghost_values = [item["U_contact_end"] for item in increments if item["runtime_active_set_end"] == "inactive"]
    ghost_max = max(ghost_values, default=0.0)
    energy_pass = bool(abs(balance) <= absolute_tol and relative <= relative_tol and all(item["local_energy_gate_pass"] for item in increments) and contact >= 0.0 and ghost_max <= float(contract["gates"]["energy"]["ghost_energy_tolerance"]))
    final_record["energy"] = {
        "definition": contract["gates"]["energy"],
        "U_strain_final": strain,
        "U_contact_final": contact,
        "U_total_final": total,
        "W_external_incremental": cumulative_work,
        "W_external_endpoint_trapezoid_characterization_only": cumulative_trapezoid,
        "prescribed_displacement_work": 0.0,
        "other_external_work": 0.0,
        "energy_balance": balance,
        "energy_error_abs": abs(balance),
        "energy_error_rel": relative,
        "contact_energy_nonnegative": bool(contact >= 0.0),
        "ghost_contact_energy_max": ghost_max,
        "incremental_records": increments,
        "maximum_runtime_endpoint_oracle_relative_error": max(endpoint_errors, default=0.0),
        "maximum_transition_root_disagreement": max(transition_root_errors, default=0.0),
    }
    final_record["gates"]["energy"] = {"absolute_error": abs(balance), "relative_error": relative, "absolute_tolerance": absolute_tol, "relative_tolerance": relative_tol, "pass": energy_pass}
    final_record["status"] = "PASS" if all(bool(gate["pass"]) for gate in final_record["gates"].values()) else "FAIL"
    final_record["_bundle"] = {
        "displacement": final_displacement,
        "reactions": final_record["reactions"],
        "contact_forces": final_record["contact_internal_force"],
        "gaps": [float(item["gap"]) for item in endpoints],
        "penetration": [float(item["penetration"]) for item in endpoints],
        "active_contact_set": [bool(item["active"]) for item in endpoints],
        "strain_energy": [float(item["U_strain_end"]) for item in increments],
        "contact_penalty_energy": [float(item["U_contact_end"]) for item in increments],
        "incremental_external_work": [float(item["external_incremental_work_exact"]) for item in increments],
        "cumulative_energy": [float(item["cumulative_external_work_exact"]) for item in increments],
        "solver_status": [str(item["solver_status"]) for item in endpoints],
    }
    return final_record


def _replay(contract: dict[str, Any], case_name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    replays = [_run_path(contract, case_name) for _ in range(int(contract["gates"]["replay"]["replay_count"]))]
    main_digest = _digest(replays[0]["_bundle"])
    rows = [{"replay": index + 1, "status": item["status"], "semantic_digest": _digest(item["_bundle"]), "exact_match_main": bool(v1._jsonable(item["_bundle"]) == v1._jsonable(replays[0]["_bundle"]))} for index, item in enumerate(replays)]
    return {"fields": contract["gates"]["replay"]["fields"], "count": len(replays), "replays": rows, "all_fields_exact": all(item["exact_match_main"] for item in rows), "semantic_digest_equal": all(item["semantic_digest"] == main_digest for item in rows)}, replays


def _schema_validate(evidence: dict[str, Any]) -> list[str]:
    required = ["schema_version", "contract", "provenance", "v1_preservation", "case_inputs", "cases", "penalty_sensitivity", "mesh_refinement_characterization", "search_evidence", "failure_cases", "replays", "registry_audit", "gate_decisions", "validation"]
    missing = [item for item in required if item not in evidence]
    if evidence.get("contract", {}).get("contract_id") != EXPECTED_CONTRACT_ID:
        missing.append("contract.contract_id")
    if evidence.get("contract", {}).get("contract_sha256") != EXPECTED_CONTRACT_SHA:
        missing.append("contract.contract_sha256")
    if set(evidence.get("cases", {})) != {"case_a", "case_b"}:
        missing.append("cases")
    if len(evidence.get("failure_cases", [])) != 8:
        missing.append("failure_cases")
    for case in evidence.get("cases", {}).values():
        for field in ("U_strain_final", "U_contact_final", "W_external_incremental", "incremental_records"):
            if field not in case.get("energy", {}):
                missing.append(f"energy.{field}")
    return missing


def main() -> None:
    _assert(not OUTPUT_DIR.exists(), f"V2 output already exists: {OUTPUT_DIR}")
    _assert(V1_CONTRACT_PATH.exists() and V1_EVIDENCE_PATH.exists(), "Immutable V1 contract/evidence is missing.")
    contract, contract_sha, contract_commit = _load_contract()
    repo_sha = _git("rev-parse", "HEAD")
    raw_cases = {"case_a": v1._case_raw(contract, "case_a"), "case_b": v1._case_raw(contract, "case_b")}
    case_a = _run_path(contract, "case_a")
    case_b = _run_path(contract, "case_b")
    expected_sequence = list(contract["benchmark"]["case_b"]["expected_state_sequence"])
    observed_sequence = ["active" if state else "inactive" for state in case_b["_bundle"]["active_contact_set"]]
    _assert(observed_sequence == expected_sequence, f"Unexpected Case B active-set sequence: {observed_sequence}")
    sensitivity: list[dict[str, Any]] = []
    for penalty in contract["benchmark"]["penalty_sensitivity_values"]:
        result = _run_path(contract, "case_a", penalty=float(penalty))
        sensitivity.append({"penalty": float(penalty), "status": result["status"], "penetration": result["max_penetration"], "energy_error_abs": result["energy"]["energy_error_abs"], "energy_error_rel": result["energy"]["energy_error_rel"], "solver_status": result["solver_status"]})
    penetrations = [float(row["penetration"]) for row in sensitivity]
    sensitivity_pass = bool(all(left >= right for left, right in zip(penetrations, penetrations[1:])) and all(row["status"] == "PASS" for row in sensitivity))
    helper_contract = _mechanical_contract(contract)
    mesh = v1._mesh_characterization(helper_contract)
    search = v1._search_evidence(contract, raw_cases)
    failures = v1._failure_cases(contract, raw_cases["case_a"])
    replay, replay_runs = _replay(contract, "case_a")
    registry = v1._registry_counts()
    oracle_pass = all(item["oracle"]["comparison_status"] == "PASS" for item in (case_a, case_b))
    nonenergy_pass = all(case["gates"][name]["pass"] for case in (case_a, case_b) for name in ("max_penetration", "final_gap", "active_contact_count", "normal_force", "force_balance"))
    gate_status = bool(case_a["status"] == "PASS" and case_b["status"] == "PASS" and sensitivity_pass and mesh["status"] == "PASS_CHARACTERIZATION" and search["status"] == "PASS" and oracle_pass and all(row["pass"] for row in failures) and replay["all_fields_exact"] and replay["semantic_digest_equal"] and nonenergy_pass)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "contract": {"contract_id": contract["contract_id"], "contract_sha256": contract_sha, "contract_commit_sha": contract_commit, "created_before_campaign": contract["created_before_campaign"], "scope": contract["scope"], "gates": contract["gates"], "oracle": contract["oracle"], "limitations": contract["limitations"], "claim_policy": contract["claim_policy"]},
        "provenance": {"repo_sha": repo_sha, "environment": _environment(), "contract_source": str(CONTRACT_PATH.relative_to(ROOT)), "output_path": str(EVIDENCE_PATH.relative_to(ROOT)), "output_directory_new_before_run": True},
        "v1_preservation": {"contract_id": "WP13-07-CONTACT-BOUNDED-001", "status": "FAIL_ENERGY_GATE", "energy_error": 0.5775705775705774, "contract_sha256": hashlib.sha256(V1_CONTRACT_PATH.read_bytes()).hexdigest(), "evidence_sha256": hashlib.sha256(V1_EVIDENCE_PATH.read_bytes()).hexdigest(), "modified": False},
        "case_inputs": v1._strip_internal(raw_cases),
        "cases": {"case_a": v1._strip_internal(case_a), "case_b": v1._strip_internal(case_b)},
        "case_b_active_set_sequence": {"expected": expected_sequence, "observed": observed_sequence, "pass": observed_sequence == expected_sequence},
        "penalty_sensitivity": {"rows": sensitivity, "penetration_non_increasing": all(left >= right for left, right in zip(penetrations, penetrations[1:])), "status": "PASS" if sensitivity_pass else "FAIL", "universal_penalty_claim": False},
        "mesh_refinement_characterization": mesh,
        "search_evidence": search,
        "failure_cases": v1._strip_internal(failures),
        "replays": v1._strip_internal(replay),
        "registry_audit": registry,
        "historical_integrity": contract["historical_integrity"],
        "gate_decisions": {"case_a": case_a["status"], "case_b": case_b["status"], "case_b_active_set": observed_sequence == expected_sequence, "nonenergy": nonenergy_pass, "energy_case_a": case_a["gates"]["energy"]["pass"], "energy_case_b": case_b["gates"]["energy"]["pass"], "penalty_sensitivity": sensitivity_pass, "mesh_refinement": mesh["status"], "search": search["status"], "oracle": oracle_pass, "failure_contract": all(row["pass"] for row in failures), "replay": replay["all_fields_exact"] and replay["semantic_digest_equal"], "overall_targeted_status": "PASS_CONTACT_BOUNDED_OWNER_READY" if gate_status else "FAIL_CONTACT_BOUNDED_CAMPAIGN"},
        "validation": {},
    }
    missing = _schema_validate(payload)
    payload["validation"] = {"evidence_schema_valid": not missing, "schema_missing_fields": missing, "semantic_validator_valid": not missing, "evidence_integrity": "PASS" if not missing else "FAIL"}
    if missing:
        payload["gate_decisions"]["overall_targeted_status"] = "FAIL_EVIDENCE"
    digest_payload = copy.deepcopy(payload)
    digest_payload["semantic_digest"] = None
    payload["semantic_digest"] = _digest(digest_payload)
    payload["evidence_integrity_sha256"] = _digest(payload)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    EVIDENCE_PATH.write_text(json.dumps(v1._strip_internal(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["gate_decisions"]["overall_targeted_status"], "contract_sha": contract_sha, "repo_sha": repo_sha, "evidence": str(EVIDENCE_PATH), "case_a_energy": case_a["energy"]["energy_error_rel"], "case_b_energy": case_b["energy"]["energy_error_rel"], "failure_cases": sum(bool(item["pass"]) for item in failures), "replay": replay["all_fields_exact"] and replay["semantic_digest_equal"]}, indent=2))


if __name__ == "__main__":
    main()
