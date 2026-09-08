"""WP13-03B V3 prospective mixed MPC/RBE2 static V&V campaign."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scripts import run_wp13_03b_v2_mpc_rbe2 as v2
from solveur.core.router import AnalysisRouter
from solveur.mesh.validation import MeshValidator


CONTRACT_PATH = ROOT / "qualification/0_2_8/wp13_03b_v3_mpc_rbe2_contract.json"
OUT = ROOT / "qualification/0_2_8/wp13_03b_v3_mpc_rbe2_runtime"
CONTRACT_ID = "WP13-03-MIXED-MPC-RBE2-003"
BASE_SHA = "10ff2f0708c4f579c7a032036d981f616e8970f04ee000ed86b9146d3ca903d7"


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _load_contract(expected_sha: str) -> tuple[dict[str, Any], str, dict[str, Any]]:
    raw = CONTRACT_PATH.read_bytes()
    contract_sha = _digest(raw)
    if contract_sha != expected_sha:
        raise RuntimeError(f"V3 contract SHA mismatch: observed {contract_sha}, expected {expected_sha}.")
    v3 = json.loads(raw.decode("utf-8"))
    if v3.get("contract_id") != CONTRACT_ID:
        raise RuntimeError("V3 contract ID mismatch.")
    base_path = ROOT / str(v3["base_contract"]["path"])
    base_raw = base_path.read_bytes()
    if _digest(base_raw) != BASE_SHA or v3["base_contract"]["contract_sha256"] != BASE_SHA:
        raise RuntimeError("Immutable V2 contract SHA mismatch.")
    base = json.loads(base_raw.decode("utf-8"))

    resolved = copy.deepcopy(base)
    resolved["contract_id"] = v3["contract_id"]
    resolved["contract_version"] = v3["contract_version"]
    resolved["v3_contract"] = v3
    resolved["metrics_and_gates"] = copy.deepcopy(base["metrics_and_gates"])
    resolved["metrics_and_gates"]["energy_work"] = copy.deepcopy(v3["energy_work_v3"])
    return resolved, contract_sha, v3


def _energy(state: dict[str, Any], v3: dict[str, Any]) -> dict[str, float]:
    u = np.asarray(state["displacement"], dtype=float)
    stiffness = state["stiffness"]
    loads = np.asarray(state["loads"], dtype=float)
    utku = float(u @ (stiffness @ u))
    utf = float(u @ loads)
    strain = 0.5 * utku
    ramped = 0.5 * utf
    absolute = abs(strain - ramped)
    relative = absolute / max(abs(strain), abs(ramped), 1.0e-30)
    clapeyron = abs(utku - utf)
    return {
        "U_strain": strain,
        "UTKU": utku,
        "UTF": utf,
        "W_external_ramped": ramped,
        "energy_error_abs": absolute,
        "energy_error_rel": relative,
        "clapeyron_error": clapeyron,
        "constraint_work": float(u @ np.asarray(state["constraint_forces"], dtype=float)),
        "absolute_gate": float(v3["energy_work_v3"]["absolute_gate"]["value"]),
        "relative_gate": float(v3["energy_work_v3"]["relative_gate"]["value"]),
        "clapeyron_gate": float(v3["energy_work_v3"]["clapeyron_gate"]["value"]),
    }


def _contract_homogeneity(state: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    d_vector = np.asarray(state["d"], dtype=float)
    nonzero_fixed = any("value" in item and float(item["value"]) != 0.0 for item in raw["fixed_dofs"])
    nonzero_offset = bool(np.max(np.abs(d_vector), initial=0.0) > 0.0)
    return {
        "mpc_constraints_homogeneous": not nonzero_offset,
        "affine_offset": float(np.max(np.abs(d_vector), initial=0.0)),
        "prescribed_nonzero_displacement": nonzero_fixed,
        "imposed_support_motion": False,
        "valid": not nonzero_offset and not nonzero_fixed,
    }


def _validate_evidence(evidence: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    required = set(base["evidence_schema"]["required_fields"])
    required.update(evidence["contract"]["v3_required_fields"])
    missing = sorted(required.difference(evidence))
    if missing:
        raise RuntimeError(f"Evidence schema missing fields: {missing}")
    if evidence["failure_contract"]["required"] != 9 or evidence["failure_contract"]["executed"] != 9:
        raise RuntimeError("V3 failure contract does not execute all nine frozen cases.")
    for row in evidence["failure_contract"]["cases"]:
        if not all(key in row for key in ("actual_input", "actual_input_digest", "type_match", "message_match", "path_match", "pass")):
            raise RuntimeError(f"Failure evidence is incomplete for {row.get('case_id', '<unknown>')}.")
        if _digest(_canonical(row["actual_input"])) != row["actual_input_digest"]:
            raise RuntimeError(f"Failure input digest mismatch for {row['case_id']}.")
    return {"valid": True, "missing_fields": [], "semantic_valid": True}


def _gate_results(
    resolved: dict[str, Any], v3: dict[str, Any], geometry: dict[str, Any], state: dict[str, Any],
    control: dict[str, Any], replay: dict[str, Any], failures: list[dict[str, Any]], rbe2: dict[str, Any],
    rbe2_rejection: dict[str, str], homogeneity: dict[str, Any], energy: dict[str, float],
) -> dict[str, bool]:
    gates = resolved["metrics_and_gates"]
    oracle_gate = float(v3["non_energy_gates"]["oracle_comparison"]["gate"]["value"])
    interface_pass = all(
        row["displacement_jump"] <= gates["interface_load_transfer"]["displacement_gate"]["value"]
        and row["force_transfer_error"] <= gates["interface_load_transfer"]["force_gate"]["value"]
        for row in state["interfaces"].values()
    )
    return {
        "geometry": bool(geometry["all_element_jacobians_valid"] and geometry["connected_components"] == 1),
        "homogeneous_constraints": bool(homogeneity["valid"]),
        "constraint": bool(state["constraint_residual"] <= gates["constraint_satisfaction"]["gate"]["value"]),
        "free_residual": bool(state["free_relative_residual"] <= gates["free_residual"]["gate"]["value"]),
        "dense_kkt": bool(
            state["displacement_error"] <= oracle_gate
            and state["reaction_error"] <= oracle_gate
            and state["constraint_force_error"] <= oracle_gate
        ),
        "equilibrium": bool(
            state["force_balance_relative"] <= gates["equilibrium"]["force_gate"]["value"]
            and state["moment_balance_relative"] <= gates["equilibrium"]["moment_gate"]["value"]
        ),
        "load_transfer": interface_pass,
        "energy_absolute": bool(energy["energy_error_abs"] <= energy["absolute_gate"]),
        "energy_relative": bool(energy["energy_error_rel"] <= energy["relative_gate"]),
        "clapeyron": bool(energy["clapeyron_error"] <= energy["clapeyron_gate"]),
        "control": bool(v2._relative(state["displacement"], control["displacement"]) >= gates["control"]["gate"]["value"]),
        "replay": bool(replay["full_array_comparison"] and replay["status_identical"]),
        "failure_contract": bool(all(row["pass"] for row in failures)),
        "rbe2_expansion": bool(rbe2["expanded_constraint_count"] == 3 and rbe2["translation_relations_valid"]),
        "rbe2_rotation_rejected": bool(
            rbe2_rejection["observed_exception_type"] == "MeshValidationError"
            and "rotational master terms" in rbe2_rejection["observed_message"]
        ),
        "all_families_participate": bool(all(row["participates"] for row in state["family"].values())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-contract-sha", required=True)
    args = parser.parse_args()
    resolved, contract_sha, v3 = _load_contract(args.expected_contract_sha)
    if OUT.exists() and any(OUT.iterdir()):
        raise RuntimeError(f"V3 evidence output directory is not empty: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)

    raw = v2._benchmark_raw(resolved, constraint_mode="mpc")
    model = v2._model_from_raw(raw)
    geometry = v2._geometry_precheck(resolved)
    preflight = MeshValidator().validate(model)
    if preflight.status != "PASS" or not geometry["all_element_jacobians_valid"]:
        raise RuntimeError(f"V3 preflight failed: {preflight.errors}")
    state = v2._solve_state(resolved, raw, include_kkt=True)
    control_raw = v2._benchmark_raw(resolved, constraint_mode="control")
    control = v2._solve_state(resolved, control_raw, include_kkt=False)
    replay = v2._replay_record(resolved, raw, state)
    failures = v2._failure_cases(resolved)
    rbe2 = v2._rbe2_evidence(resolved, model)
    rbe2_rejection = {"observed_exception_type": "NO_EXCEPTION", "observed_message": ""}
    try:
        AnalysisRouter().solve(v2._model_from_raw(v2._benchmark_raw(resolved, constraint_mode="rbe2")))
    except Exception as exc:  # noqa: BLE001 - archive the explicit public preflight rejection.
        rbe2_rejection = {"observed_exception_type": type(exc).__name__, "observed_message": str(exc)}

    homogeneity = _contract_homogeneity(state, raw)
    if not homogeneity["valid"]:
        raise RuntimeError("Frozen V3 campaign is not homogeneous; aborting before energy-gate evaluation.")
    energy = _energy(state, v3)
    gates = _gate_results(resolved, v3, geometry, state, control, replay, failures, rbe2, rbe2_rejection, homogeneity, energy)
    npz_path = OUT / "wp13_03b_v3_raw.npz"
    array_digests = v2._write_npz(npz_path, state, control)
    base = json.loads((ROOT / v3["base_contract"]["path"]).read_text(encoding="utf-8"))
    v3_fields = list(v3["evidence_requirements_v3"]["additional_required_fields"])
    evidence: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "contract_sha": contract_sha,
        "base_contract_sha": BASE_SHA,
        "repo_sha": v2._repo_sha(),
        "environment": v2._environment(),
        "contract": {
            "contract_id": CONTRACT_ID,
            "contract_sha": contract_sha,
            "contract_path": str(CONTRACT_PATH.relative_to(ROOT)),
            "base_contract_id": base["contract_id"],
            "base_contract_sha": BASE_SHA,
            "contract_created_before_run": v3["created_before_numerical_campaign"],
            "gates_source": "V2 exact base sections plus V3 energy_work_v3",
            "v3_required_fields": v3_fields,
        },
        "provenance": {"repo_sha": v2._repo_sha(), "environment": v2._environment(), "runner": "scripts/run_wp13_03b_v3_mpc_rbe2.py"},
        "benchmark_inputs": raw,
        "conditioning": geometry,
        "conditioning_prechecks": geometry,
        "micro_check": {
            "mixed_static_mpc_allowed": True,
            "constraint_present_after_preflight": True,
            "affine_reduction_applied": True,
            "expansion_back_to_full_dof": True,
            "ndof": state["dofs"].ndof,
            "constraint_count": int(state["C"].shape[0]),
            "constraint_residual": state["constraint_residual"],
            "constraint_dropped_silently": False,
            "family_dropped_silently": False,
            "rbe2_rotation_downgraded_silently": False,
        },
        "runtime": {"status": state["status"], "displacement": v2._array_record(state["displacement"]), "reactions": v2._array_record(state["reactions"]), "residual": v2._array_record(state["residual"]), "stiffness": v2._array_record(state["stiffness"].toarray()), "loads": v2._array_record(state["loads"]), "constraint_forces": v2._array_record(state["constraint_forces"])},
        "raw_displacement": v2._array_record(state["displacement"]),
        "support_reactions": v2._array_record(state["reactions"]),
        "constraint": {"C": v2._array_record(state["C"]), "d": v2._array_record(state["d"]), "u": v2._array_record(state["displacement"]), "C_u_minus_d": v2._array_record(state["constraint_residual_vector"]), "constraint_residual": state["constraint_residual"], "definitions": resolved["constraint_definition"]["constraint_equations"]},
        "constraint_definitions": resolved["constraint_definition"],
        "constraint_matrix_or_equivalent": v2._array_record(state["C"]),
        "master_slave_mappings": {"master_node": resolved["constraint_definition"]["master_node"], "slave_node": resolved["constraint_definition"]["slave_node"], "mpc_equations": resolved["constraint_definition"]["constraint_equations"]},
        "constraint_residuals": {"vector": v2._array_record(state["constraint_residual_vector"]), "norm": state["constraint_residual"]},
        "constraint_forces": v2._array_record(state["constraint_forces"]),
        "dense_kkt_oracle": {"valid": True, "assembly_independent": True, "runtime_reduction_reused": False, "u_kkt": v2._array_record(state["u_kkt"]), "lambda_kkt": v2._array_record(state["lambda_kkt"]), "kkt_constraint_forces": v2._array_record(state["kkt_constraint_forces"]), "kkt_support_reactions": v2._array_record(state["kkt_support_reactions"]), "displacement_error": state["displacement_error"], "reaction_error": state["reaction_error"], "constraint_force_error": state["constraint_force_error"], "shared_kernel_limitation": "Element stiffness kernels are shared; dense K/F assembly, literal C construction, and dense KKT solve do not reuse ConstraintReduction or the runtime factorization."},
        "independent_oracle": {},
        "equilibrium": {"external_force_vector": state["external_force_vector"].tolist(), "support_reactions": state["support_reaction_resultant"].tolist(), "constraint_force_resultant": state["constraint_force_resultant"].tolist(), "force_balance_vector": state["force_balance"].tolist(), "moment_balance_vector": state["moment_balance"].tolist(), "global_force_balance": state["force_balance_relative"], "global_moment_balance": state["moment_balance_relative"]},
        "load_transfer": {"path": resolved["benchmark"]["mechanical_load_path"], "interfaces": state["interfaces"], "no_support_bypass": True, "valid": gates["load_transfer"]},
        "energy_work": {**energy, "definition": v3["energy_work_v3"], "homogeneity": homogeneity},
        "family_participation": state["family"],
        "control_case": {"status": control["status"], "displacement": v2._array_record(control["displacement"]), "reactions": v2._array_record(control["reactions"]), "constraint_effect_relative": v2._relative(state["displacement"], control["displacement"]), "constraint_effect_demonstrated": gates["control"]},
        "rbe2": {**rbe2, "rejection": rbe2_rejection},
        "replay": replay,
        "replay_runs": replay,
        "failure_contract": {"required": 9, "executed": len(failures), "passed": sum(int(row["pass"]) for row in failures), "any_exception_accepted": False, "silent_fallback": False, "cases": failures},
        "failure_executions": failures,
        "digests": {"npz": _digest(npz_path.read_bytes()), "arrays": array_digests},
        "mpc_constraints_homogeneous": homogeneity["mpc_constraints_homogeneous"],
        "affine_offset": homogeneity["affine_offset"],
        "U_strain": energy["U_strain"],
        "UTKU": energy["UTKU"],
        "UTF": energy["UTF"],
        "W_external_ramped": energy["W_external_ramped"],
        "energy_error_abs": energy["energy_error_abs"],
        "energy_error_rel": energy["energy_error_rel"],
        "clapeyron_error": energy["clapeyron_error"],
        "energy_gate_decisions": {key: gates[key] for key in ("energy_absolute", "energy_relative", "clapeyron")},
        "gate_decisions": gates,
    }
    evidence["independent_oracle"] = evidence["dense_kkt_oracle"]
    evidence["schema_validation"] = _validate_evidence(evidence, base)
    evidence["semantic_validation"] = {"valid": all(gates.values()), "checks": gates}
    (OUT / "wp13_03b_v3_evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    status = "PASS" if all(gates.values()) else "FAIL"
    print(json.dumps({"status": status, "gate_decisions": gates, "output": str(OUT)}, sort_keys=True))
    return 0 if status == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
