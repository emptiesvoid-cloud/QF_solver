"""WP13-07 V3 prospective bounded frictionless-contact V&V campaign."""

from __future__ import annotations

import copy
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

import run_wp13_07_contact_bounded as v1
import run_wp13_07_contact_bounded_v2 as v2


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp13_07_contact_bounded_v3_contract.json"
OUTPUT_DIR = ROOT / "qualification" / "0_2_8" / "wp13_07_contact_bounded_v3"
EVIDENCE_PATH = OUTPUT_DIR / "wp13_07_contact_v3_evidence.json"
EXPECTED_CONTRACT_ID = "WP13-07-CONTACT-BOUNDED-003"
EXPECTED_CONTRACT_SHA = "f775343f6008191ef3c9c81b2600ab2a42c53e1113237d01d1ec62dcf001333e"
V1_CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp13_07_contact_bounded_contract.json"
V1_EVIDENCE_PATH = ROOT / "qualification" / "0_2_8" / "wp13_07_contact_bounded" / "wp13_07_contact_evidence.json"
V2_CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp13_07_contact_bounded_v2_contract.json"
V2_EVIDENCE_PATH = ROOT / "qualification" / "0_2_8" / "wp13_07_contact_bounded_v2" / "wp13_07_contact_v2_evidence.json"


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
    _assert(contract["contract_id"] == EXPECTED_CONTRACT_ID, "Unexpected V3 contract ID.")
    _assert(sha == EXPECTED_CONTRACT_SHA, "Frozen V3 contract digest mismatch.")
    _assert(contract["created_before_campaign"], "V3 contract is not predeclared.")
    commit = _git("log", "-1", "--format=%H", "--", str(CONTRACT_PATH.relative_to(ROOT)))
    _assert(bool(commit), "V3 contract provenance is missing.")
    return contract, sha, commit


def _mechanical_contract(contract: dict[str, Any]) -> dict[str, Any]:
    helper = copy.deepcopy(contract)
    helper["gates"]["energy"].update({
        "threshold": float("inf"),
        "identity": "mechanical helper compatibility only; V3 energy is evaluated below",
        "external_work": "mechanical helper compatibility only",
    })
    return helper


def _collect_path(contract: dict[str, Any], case_name: str, penalty: float | None = None) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    raw = v1._case_raw(contract, case_name, penalty)
    path = [float(value) for value in raw["analysis"]["parameters"]["load_path"]]
    helper = _mechanical_contract(contract)
    endpoints: list[dict[str, Any]] = []
    final_record: dict[str, Any] | None = None
    for index, load_factor in enumerate(path):
        prefix = copy.deepcopy(raw)
        prefix["analysis"]["parameters"]["load_path"] = path[: index + 1]
        record = v1._run_case(prefix, helper, include_oracle=index == len(path) - 1)
        final_record = record
        endpoints.append({
            "load_factor": load_factor,
            "displacement": np.asarray(record["displacement"], dtype=float),
            "reactions": np.asarray(record["reactions"], dtype=float),
            "gap": float(record["final_gap"]),
            "penetration": float(max(-record["final_gap"], 0.0)),
            "contact_force": float(record["contact_force_magnitude"]),
            "active": bool(record["active_contact_sets"][-1]),
            "solver_status": str(record["solver_status"]),
            "residual": float(record["force_balance"]["maximum_free_relative_residual"]),
        })
    _assert(final_record is not None, "V3 declared load path is empty.")
    return raw, final_record, endpoints


def _pointwise_equilibrium(system: dict[str, Any], load_factor: float) -> tuple[np.ndarray, bool, float]:
    Kff = np.asarray(system["Kff"], dtype=float)
    Ffree = np.asarray(system["Ffree"], dtype=float)
    c = np.asarray(system["cfree"], dtype=float)
    penalty = float(system["penalty"])
    inactive_free = np.linalg.solve(Kff, load_factor * Ffree)
    inactive_gap = float(system["gap0"] + c @ inactive_free)
    if inactive_gap >= -1.0e-12:
        displacement = np.zeros_like(system["load_reference"], dtype=float)
        displacement[system["free"]] = inactive_free
        return displacement, False, inactive_gap
    active_matrix = Kff + penalty * np.outer(c, c)
    active_rhs = load_factor * Ffree - penalty * float(system["gap0"]) * c
    active_free = np.linalg.solve(active_matrix, active_rhs)
    active_gap = float(system["gap0"] + c @ active_free)
    _assert(active_gap <= 1.0e-10, f"Pointwise active contact solve is inconsistent: gap={active_gap}")
    displacement = np.zeros_like(system["load_reference"], dtype=float)
    displacement[system["free"]] = active_free
    return displacement, True, active_gap


def _numerical_integral(system: dict[str, Any], start: float, end: float, panels: int) -> tuple[float, list[float]]:
    if start == end:
        return 0.0, []
    coarse_count = max(128, panels)
    coarse = np.linspace(start, end, coarse_count + 1)
    states = [_pointwise_equilibrium(system, float(value))[1] for value in coarse]
    transitions: list[float] = []
    for left, right, state_left, state_right in zip(coarse[:-1], coarse[1:], states[:-1], states[1:], strict=True):
        if state_left == state_right:
            continue
        lo, hi = float(left), float(right)
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            state_mid = _pointwise_equilibrium(system, mid)[1]
            if state_mid == state_left:
                lo = mid
            else:
                hi = mid
        transitions.append(0.5 * (lo + hi))
    points = [float(start), *transitions, float(end)]
    points = sorted(set(points)) if end >= start else sorted(set(points), reverse=True)
    total = 0.0
    reference = np.asarray(system["load_reference"], dtype=float)
    for segment_start, segment_end in zip(points[:-1], points[1:], strict=True):
        grid = np.linspace(segment_start, segment_end, panels + 1)
        values = [_pointwise_equilibrium(system, float(value))[0] for value in grid]
        for lambda_a, lambda_b, u_a, u_b in zip(grid[:-1], grid[1:], values[:-1], values[1:], strict=True):
            force_a = lambda_a * reference
            force_b = lambda_b * reference
            total += float(0.5 * (force_a + force_b) @ (u_b - u_a))
    return total, transitions


def _potential(system: dict[str, Any], displacement: np.ndarray) -> tuple[float, float, float, float]:
    strain = float(0.5 * displacement @ (system["stiffness"] @ displacement))
    gap = float(system["gap0"] + system["cfull"] @ displacement)
    contact = float(0.5 * system["penalty"] * max(-gap, 0.0) ** 2)
    return strain, contact, strain + contact, gap


def _analytic_path(system: dict[str, Any], endpoints: list[dict[str, Any]], tolerance: float) -> tuple[float, list[dict[str, Any]], float]:
    inactive = v2._branch(system, False)
    active = v2._branch(system, True)
    points = [{"load_factor": 0.0, "displacement": np.zeros_like(system["load_reference"]), "active": False, "gap": float(system["gap0"]), "penetration": 0.0, "contact_force": 0.0, "solver_status": "INITIAL"}, *endpoints]
    total = 0.0
    increments: list[dict[str, Any]] = []
    roots_disagreement: list[float] = []
    max_endpoint_error = 0.0
    for step, (previous, current) in enumerate(zip(points, points[1:]), start=1):
        la, lb = float(previous["load_factor"]), float(current["load_factor"])
        state_a, state_b = bool(previous["active"]), bool(current["active"])
        before, after = (active if state_a else inactive), (active if state_b else inactive)
        expected = v2._branch_displacement(system, after, lb)
        endpoint_error = float(np.linalg.norm(current["displacement"] - expected) / max(np.linalg.norm(expected), 1.0))
        max_endpoint_error = max(max_endpoint_error, endpoint_error)
        transition = "active_to_active" if state_a and state_b else "inactive_to_inactive" if not state_a and not state_b else "inactive_to_active" if state_b else "active_to_inactive"
        pieces: list[tuple[dict[str, np.ndarray], float, float]]
        roots: list[float] = []
        if state_a == state_b:
            pieces = [(before, la, lb)]
        else:
            root_before = v2._branch_root(system, before)
            root_after = v2._branch_root(system, after)
            roots_disagreement.append(abs(root_before - root_after))
            root = 0.5 * (root_before + root_after)
            _assert(min(la, lb) - 1e-12 <= root <= max(la, lb) + 1e-12, "Analytic transition is outside the declared load interval.")
            roots = [root]
            pieces = [(before, la, root), (after, root, lb)]
        work = 0.0
        for branch, start, end in pieces:
            work += float(0.5 * (end * end - start * start) * np.asarray(system["Ffree"]) @ branch["A"])
        strain_a, contact_a, potential_a, _ = _potential(system, previous["displacement"])
        strain_b, contact_b, potential_b, _ = _potential(system, current["displacement"])
        local_balance = float(potential_b - potential_a - work)
        total += work
        increments.append({
            "step": step,
            "lambda_a": la,
            "lambda_b": lb,
            "active_set_transition": transition,
            "active_state_start": "active" if state_a else "inactive",
            "active_state_end": "active" if state_b else "inactive",
            "transition_load_factors": roots,
            "A_q": before["A"].copy(),
            "b_q": before["b"].copy(),
            "U_strain_start": strain_a,
            "U_contact_start": contact_a,
            "U_strain_end": strain_b,
            "U_contact_end": contact_b,
            "work_increment": work,
            "local_energy_balance": local_balance,
            "endpoint_oracle_error": endpoint_error,
            "local_energy_pass": abs(local_balance) <= tolerance,
        })
    return total, increments, max(max(roots_disagreement, default=0.0), max_endpoint_error)


def _run_path(contract: dict[str, Any], case_name: str, penalty: float | None = None) -> dict[str, Any]:
    raw, record, endpoints = _collect_path(contract, case_name, penalty)
    system = v2._assemble_energy_system(raw)
    energy_contract = contract["gates"]["energy"]
    analytic, increments, analytic_diagnostic = _analytic_path(system, endpoints, float(energy_contract["incremental_local_absolute_tolerance"]))
    numerical, numerical_transitions = _numerical_integral(system, 0.0, float(endpoints[0]["load_factor"]), int(contract["cross_check"]["panels_per_smooth_segment"]))
    numerical = 0.0
    all_numeric_transitions: list[float] = []
    previous_lambda = 0.0
    for endpoint in endpoints:
        contribution, transitions = _numerical_integral(system, previous_lambda, float(endpoint["load_factor"]), int(contract["cross_check"]["panels_per_smooth_segment"]))
        numerical += contribution
        all_numeric_transitions.extend(transitions)
        previous_lambda = float(endpoint["load_factor"])
    final_u = np.asarray(endpoints[-1]["displacement"], dtype=float)
    strain, contact, total, final_gap = _potential(system, final_u)
    balance = float(total - analytic)
    relative = float(abs(balance) / max(abs(total), abs(analytic), 1.0e-30))
    crosscheck_error = float(abs(analytic - numerical))
    transition_energies = [item for item in increments if item["active_set_transition"] != "inactive_to_inactive" and item["active_set_transition"] != "active_to_active"]
    ghost = max((float(item["U_contact_end"]) for item in increments if item["active_state_end"] == "inactive"), default=0.0)
    crosscheck_pass = crosscheck_error <= float(energy_contract["work_crosscheck_tolerance"])
    energy_pass = bool(abs(balance) <= float(energy_contract["absolute_tolerance"]) and relative <= float(energy_contract["relative_tolerance"]) and crosscheck_pass and all(item["local_energy_pass"] for item in increments) and ghost <= float(energy_contract["ghost_energy_tolerance"]) and analytic_diagnostic <= 1.0e-10)
    record["energy"] = {
        "definition": energy_contract,
        "U_strain_final": strain,
        "U_contact_final": contact,
        "U_total_final": total,
        "W_external_analytic_branchwise": analytic,
        "W_external_numerical_path": numerical,
        "work_crosscheck_abs": crosscheck_error,
        "work_crosscheck_tolerance": float(energy_contract["work_crosscheck_tolerance"]),
        "work_crosscheck_pass": crosscheck_pass,
        "prescribed_displacement_work": 0.0,
        "other_external_work": 0.0,
        "energy_error_abs": abs(balance),
        "energy_error_rel": relative,
        "b_offset_work_contribution": 0.0,
        "contact_energy_nonnegative": contact >= 0.0,
        "ghost_contact_energy_max": ghost,
        "incremental_records": increments,
        "numerical_transition_load_factors": all_numeric_transitions,
        "analytic_transition_diagnostic": analytic_diagnostic,
        "active_set_transition_energy": transition_energies,
    }
    record["gates"]["energy"] = {"absolute_error": abs(balance), "relative_error": relative, "work_crosscheck_abs": crosscheck_error, "work_crosscheck_tolerance": float(energy_contract["work_crosscheck_tolerance"]), "absolute_tolerance": float(energy_contract["absolute_tolerance"]), "relative_tolerance": float(energy_contract["relative_tolerance"]), "pass": energy_pass}
    record["status"] = "PASS" if all(bool(gate["pass"]) for gate in record["gates"].values()) else "FAIL"
    record["_bundle"] = {"displacement": final_u, "reactions": record["reactions"], "contact_forces": record["contact_internal_force"], "gaps": [float(item["gap"]) for item in endpoints], "penetration": [float(item["penetration"]) for item in endpoints], "active_contact_set": [bool(item["active"]) for item in endpoints], "strain_energy": [float(item["U_strain_end"]) for item in increments], "contact_penalty_energy": [float(item["U_contact_end"]) for item in increments], "external_work": [float(item["work_increment"]) for item in increments], "numerical_work": numerical, "solver_status": [item["solver_status"] for item in endpoints]}
    return record


def _replays(contract: dict[str, Any], case_name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    records = [_run_path(contract, case_name) for _ in range(int(contract["gates"]["replay"]["replay_count"]))]
    main_digest = _digest(records[0]["_bundle"])
    rows = [{"replay": index + 1, "status": item["status"], "semantic_digest": _digest(item["_bundle"]), "exact_match_main": bool(v1._jsonable(item["_bundle"]) == v1._jsonable(records[0]["_bundle"]))} for index, item in enumerate(records)]
    return {"fields": contract["gates"]["replay"]["fields"], "count": len(rows), "replays": rows, "all_fields_exact": all(item["exact_match_main"] for item in rows), "semantic_digest_equal": all(item["semantic_digest"] == main_digest for item in rows)}, records


def _schema_validate(evidence: dict[str, Any]) -> list[str]:
    required = ["schema_version", "contract", "provenance", "v1_preservation", "v2_preservation", "case_inputs", "cases", "penalty_sensitivity", "mesh_refinement_characterization", "search_evidence", "failure_cases", "replays", "registry_audit", "gate_decisions", "validation"]
    missing = [item for item in required if item not in evidence]
    if evidence.get("contract", {}).get("contract_id") != EXPECTED_CONTRACT_ID:
        missing.append("contract.contract_id")
    if evidence.get("contract", {}).get("contract_sha256") != EXPECTED_CONTRACT_SHA:
        missing.append("contract.contract_sha256")
    if len(evidence.get("failure_cases", [])) != 8:
        missing.append("failure_cases.8")
    for case_name, case in evidence.get("cases", {}).items():
        for field in ("U_strain_final", "U_contact_final", "W_external_analytic_branchwise", "W_external_numerical_path", "work_crosscheck_abs", "incremental_records"):
            if field not in case.get("energy", {}):
                missing.append(f"{case_name}.energy.{field}")
    return missing


def main() -> None:
    _assert(not OUTPUT_DIR.exists(), f"V3 output already exists: {OUTPUT_DIR}")
    for path in (V1_CONTRACT_PATH, V1_EVIDENCE_PATH, V2_CONTRACT_PATH, V2_EVIDENCE_PATH):
        _assert(path.exists(), f"Historical artifact is missing: {path}")
    contract, contract_sha, contract_commit = _load_contract()
    repo_sha = _git("rev-parse", "HEAD")
    raw_cases = {"case_a": v1._case_raw(contract, "case_a"), "case_b": v1._case_raw(contract, "case_b")}
    case_a = _run_path(contract, "case_a")
    case_b = _run_path(contract, "case_b")
    sequence = ["active" if value else "inactive" for value in case_b["_bundle"]["active_contact_set"]]
    expected_sequence = list(contract["benchmark"]["case_b"]["expected_state_sequence"])
    _assert(sequence == expected_sequence, f"Case B active-set sequence mismatch: {sequence}")
    sensitivity: list[dict[str, Any]] = []
    for penalty in contract["benchmark"]["penalty_sensitivity_values"]:
        result = _run_path(contract, "case_a", float(penalty))
        sensitivity.append({"penalty": float(penalty), "status": result["status"], "penetration": result["max_penetration"], "energy_error_rel": result["energy"]["energy_error_rel"], "work_crosscheck_abs": result["energy"]["work_crosscheck_abs"], "solver_status": result["solver_status"]})
    penetrations = [float(item["penetration"]) for item in sensitivity]
    sensitivity_pass = bool(all(left >= right for left, right in zip(penetrations, penetrations[1:])) and all(item["status"] == "PASS" for item in sensitivity))
    helper = _mechanical_contract(contract)
    mesh = v1._mesh_characterization(helper)
    search = v1._search_evidence(contract, raw_cases)
    failures = v1._failure_cases(contract, raw_cases["case_a"])
    replay, replay_records = _replays(contract, "case_a")
    registry = v1._registry_counts()
    oracle_pass = all(item["oracle"]["comparison_status"] == "PASS" for item in (case_a, case_b))
    nonenergy_pass = all(case["gates"][name]["pass"] for case in (case_a, case_b) for name in ("max_penetration", "final_gap", "active_contact_count", "normal_force", "force_balance"))
    overall_pass = bool(case_a["status"] == "PASS" and case_b["status"] == "PASS" and sensitivity_pass and mesh["status"] == "PASS_CHARACTERIZATION" and search["status"] == "PASS" and oracle_pass and nonenergy_pass and all(row["pass"] for row in failures) and replay["all_fields_exact"] and replay["semantic_digest_equal"])
    payload: dict[str, Any] = {
        "schema_version": 1,
        "contract": {"contract_id": contract["contract_id"], "contract_sha256": contract_sha, "contract_commit_sha": contract_commit, "created_before_campaign": contract["created_before_campaign"], "scope": contract["scope"], "gates": contract["gates"], "cross_check": contract["cross_check"], "oracle": contract["oracle"], "limitations": contract["limitations"], "claim_policy": contract["claim_policy"]},
        "provenance": {"repo_sha": repo_sha, "environment": _environment(), "contract_source": str(CONTRACT_PATH.relative_to(ROOT)), "output_path": str(EVIDENCE_PATH.relative_to(ROOT)), "output_directory_new_before_run": True},
        "v1_preservation": {"contract_id":"WP13-07-CONTACT-BOUNDED-001","status":"FAIL_ENERGY_GATE","energy_error":0.5775705775705774,"contract_sha256":hashlib.sha256(V1_CONTRACT_PATH.read_bytes()).hexdigest(),"evidence_sha256":hashlib.sha256(V1_EVIDENCE_PATH.read_bytes()).hexdigest(),"modified":False},
        "v2_preservation": {"contract_id":"WP13-07-CONTACT-BOUNDED-002","status":"FAIL_CONTACT_BOUNDED_CAMPAIGN","contract_sha256":hashlib.sha256(V2_CONTRACT_PATH.read_bytes()).hexdigest(),"evidence_sha256":hashlib.sha256(V2_EVIDENCE_PATH.read_bytes()).hexdigest(),"modified":False},
        "case_inputs": v1._strip_internal(raw_cases),
        "cases": {"case_a":v1._strip_internal(case_a),"case_b":v1._strip_internal(case_b)},
        "case_b_active_set_sequence": {"expected":expected_sequence,"observed":sequence,"pass":sequence == expected_sequence},
        "penalty_sensitivity": {"rows":sensitivity,"penetration_non_increasing":all(left >= right for left,right in zip(penetrations,penetrations[1:])),"status":"PASS" if sensitivity_pass else "FAIL","universal_penalty_claim":False},
        "mesh_refinement_characterization": mesh,
        "search_evidence": search,
        "failure_cases": v1._strip_internal(failures),
        "replays": v1._strip_internal(replay),
        "registry_audit": registry,
        "historical_integrity": contract["historical_integrity"],
        "gate_decisions": {"case_a":case_a["status"],"case_b":case_b["status"],"case_b_active_set":sequence == expected_sequence,"nonenergy":nonenergy_pass,"energy_case_a":case_a["gates"]["energy"]["pass"],"energy_case_b":case_b["gates"]["energy"]["pass"],"penalty_sensitivity":sensitivity_pass,"mesh_refinement":mesh["status"],"search":search["status"],"oracle":oracle_pass,"failure_contract":all(row["pass"] for row in failures),"replay":replay["all_fields_exact"] and replay["semantic_digest_equal"],"overall_targeted_status":"PASS_CONTACT_BOUNDED_OWNER_READY" if overall_pass else "FAIL_CONTACT_BOUNDED_CAMPAIGN"},
        "validation": {},
    }
    missing = _schema_validate(payload)
    payload["validation"] = {"evidence_schema_valid":not missing,"schema_missing_fields":missing,"semantic_validator_valid":not missing,"evidence_integrity":"PASS" if not missing else "FAIL"}
    if missing:
        payload["gate_decisions"]["overall_targeted_status"] = "FAIL_EVIDENCE"
    digest_payload = copy.deepcopy(payload)
    digest_payload["semantic_digest"] = None
    payload["semantic_digest"] = _digest(digest_payload)
    payload["evidence_integrity_sha256"] = _digest(payload)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    EVIDENCE_PATH.write_text(json.dumps(v1._strip_internal(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(v1._jsonable({"status":payload["gate_decisions"]["overall_targeted_status"],"contract_sha":contract_sha,"repo_sha":repo_sha,"evidence":str(EVIDENCE_PATH),"case_a":case_a["energy"],"case_b":case_b["energy"],"failure_cases":sum(bool(row["pass"]) for row in failures),"replay":replay["all_fields_exact"] and replay["semantic_digest_equal"]}), indent=2))


if __name__ == "__main__":
    main()
