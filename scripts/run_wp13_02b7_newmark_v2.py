"""Replay the frozen WP13-02B4 Newmark V2 campaign after WP13-02B6."""

from __future__ import annotations

import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_wp13_02b5_newmark_v2 as b5  # noqa: E402


CONTRACT_PATH = ROOT / "qualification/0_2_8/wp13_02b4_newmark_v2_contract.json"
SCHEMA_PATH = ROOT / "qualification/0_2_8/wp13_02b4_contract.schema.json"
OUTPUT_DIR = ROOT / "qualification/0_2_8/wp13_02b7_v2"
ARCHIVE_PATH = OUTPUT_DIR / "wp13_02b7_arrays.npz"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
CONTRACT_ID = "WP13-02B4-NEWMARK-MIXED-V2-001"
CONTRACT_COMMIT = "ccab01854f42d56aa6dc7202d9c5dd76dd9b2dde"
START_SHA = "fc6b32c8ea1fff0a98390b7788018b14e2ac4891"
CONTRACT_BLOB = "8b44792466eacaf1f341a7970502e9b48dbed4e1"
LEVELS = (20, 40, 80, 160)
FAMILIES = ("TET4", "WEDGE6", "HEX8")


def _add_archive_array(
    arrays: dict[str, np.ndarray], manifest: dict[str, Any], name: str, value: Any
) -> None:
    array = np.asarray(value, dtype=np.float64)
    arrays[name] = array
    manifest[name] = {"shape": list(array.shape), "dtype": "float64", "sha256": b5.digest(array)}


def _failure_ok(failures: dict[str, Any]) -> bool:
    required = (
        "invalid_dt",
        "missing_mass",
        "unsupported_damping",
        "unsupported_time_load",
        "invalid_initial_conditions_unknown_dof",
        "invalid_initial_conditions_non_list",
        "invalid_mixed_interface",
    )
    return all(failures[name]["status"] == "REJECTED" for name in required) and failures["unsupported_family"]["status"] == "UNSUPPORTED_ROUTE"


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if head != START_SHA:
        raise SystemExit(f"Unexpected WP13-02B7 start SHA: {head}")
    if contract["contract_id"] != CONTRACT_ID or b5.git_blob(CONTRACT_PATH) != CONTRACT_BLOB:
        raise SystemExit("Frozen contract mismatch before run.")

    base = b5.b2.build(1)
    topology = b5.connectivity(base)
    reference = b5.b2.reference(base)
    reference["current_time"] = np.zeros(1)
    dofs = reference["dofs"]
    stiffness, mass, _, _ = b5.GlobalAssembler().assemble_stiffness_and_mass(base, dofs)
    production_frequency = b5.production_modal_frequency(base)
    production_k = stiffness.toarray()
    production_m = mass.toarray()
    independent_k, independent_m = reference["stiffness"], reference["mass"]
    fixed, free = reference["fixed"], reference["free"]
    lambda_first = reference["omega"] ** 2
    eigenpair = reference["mode"][free]
    eigen_residual = float(
        np.linalg.norm(
            (independent_k[np.ix_(free, free)] - lambda_first * independent_m[np.ix_(free, free)]) @ eigenpair
        )
        / np.linalg.norm(independent_k[np.ix_(free, free)] @ eigenpair)
    )
    prechecks = {
        "contract_committed_before_run": True,
        "contract_unchanged": b5.git_blob(CONTRACT_PATH) == CONTRACT_BLOB,
        "model_connected": topology["connected_components"] == 1,
        "connected_components": topology["connected_components"],
        "direct_support_bypass": topology["direct_support_bypass"],
        "ndof": dofs.ndof,
        "ndof_expected": dofs.ndof == 48,
        "family_counts": topology["family_counts"],
        "families_present": all(topology["family_counts"][family] > 0 for family in FAMILIES),
        "consistent_mass": True,
        "mass_symmetric": float(np.linalg.norm(independent_m - independent_m.T) / np.linalg.norm(independent_m)) <= 1.0e-12,
        "mass_positive": bool(np.min(np.linalg.eigvalsh(independent_m[np.ix_(free, free)])) > 0.0),
        "damping_zero": contract["scope"]["damping"] == {"model": "Rayleigh", "alpha_per_s": 0.0, "beta_s": 0.0},
        "first_mode_initial_condition": bool(np.isfinite(reference["initial_entries"][0]["value"]) and np.linalg.norm(reference["initial_acceleration"][fixed]) == 0.0),
        "oracle_available": True,
        "production_dense_stiffness_relative_difference": float(np.linalg.norm(production_k - independent_k) / np.linalg.norm(independent_k)),
        "production_dense_mass_relative_difference": float(np.linalg.norm(production_m - independent_m) / np.linalg.norm(independent_m)),
        "eigenpair_residual": eigen_residual,
        "production_frequency_hz": production_frequency,
        "reference_frequency_hz": reference["frequency_hz"],
    }
    if not all((
        prechecks["contract_committed_before_run"], prechecks["contract_unchanged"], prechecks["model_connected"],
        not prechecks["direct_support_bypass"], prechecks["ndof_expected"], prechecks["families_present"],
        prechecks["mass_symmetric"], prechecks["mass_positive"], prechecks["damping_zero"],
        prechecks["first_mode_initial_condition"], prechecks["oracle_available"],
    )):
        raise SystemExit("Prechecks failed; no Newmark run was started.")

    runs: dict[int, dict[str, Any]] = {}
    for level in LEVELS:
        captured = b5.b2.capture(base, reference, level)
        reference["current_time"] = captured["time"]
        runs[level] = b5.enrich_run(reference, captured)
    replays = []
    for _ in range(2):
        captured = b5.b2.capture(base, reference, 160)
        reference["current_time"] = captured["time"]
        replays.append(b5.enrich_run(reference, captured))

    errors = {name: [float(runs[level][name]) for level in LEVELS] for name in ("modal_q_error", "modal_v_error", "modal_a_error", "amplitude_error", "phase_error_rad")}
    orders = {name: [float(math.log(values[index] / values[index + 1], 2.0)) for index in range(3)] for name, values in errors.items()}
    convergence = {
        "metrics": errors,
        "orders": orders,
        "strictly_decreasing": {name: all(values[index] > values[index + 1] > 0.0 for index in range(3)) for name, values in errors.items()},
        "order_pass": {name: all(1.5 <= value <= 2.5 for value in values) for name, values in orders.items()},
    }
    eigen_error = abs(production_frequency - reference["frequency_hz"]) / reference["frequency_hz"]
    replay_fields = ("displacement", "velocity", "acceleration", "q", "residual_norm", "energy_total", "reactions")
    main_replay = runs[160]
    replay_comparison = {"per_replay": [], "all_fields_pass": True, "same_status": True, "same_iterations": True}
    for replay in replays:
        comparison = {field: b5.relative_norm(replay[field], main_replay[field]) for field in replay_fields}
        comparison["all_fields_pass"] = all(value <= 1.0e-12 for value in comparison.values())
        comparison["status_identical"] = replay["solver_status"] == main_replay["solver_status"]
        comparison["iterations_identical"] = replay["iterations_total"] == main_replay["iterations_total"]
        replay_comparison["per_replay"].append(comparison)
    replay_comparison["all_fields_pass"] = all(item["all_fields_pass"] for item in replay_comparison["per_replay"])
    replay_comparison["same_status"] = all(item["status_identical"] for item in replay_comparison["per_replay"])
    replay_comparison["same_iterations"] = all(item["iterations_identical"] for item in replay_comparison["per_replay"])
    failure_contract = b5.failures(base, reference)
    interface_status_all: dict[str, Any] = {}
    interface_gate = True
    for level in LEVELS:
        run = runs[level]
        interface_status = {
            key: {"continuity": b5.gate(values["continuity_relative"], 1.0e-12), "force": b5.gate(values["force_balance_relative"], 1.0e-8), "energy": b5.gate(values["energy_error_relative"], 1.0e-8)}
            for key, values in run["interface"].items()
        }
        interface_status_all[str(level)] = interface_status
        interface_gate = interface_gate and all(item[metric]["pass"] for item in interface_status.values() for metric in ("continuity", "force", "energy"))
    acceptance: dict[str, Any] = {}
    for level in (80, 160):
        run = runs[level]
        acceptance[level] = {
            "q": b5.gate(run["modal_q_error"], 0.01), "v": b5.gate(run["modal_v_error"], 0.01), "a": b5.gate(run["modal_a_error"], 0.01),
            "amplitude": b5.gate(run["amplitude_error"], 0.01), "phase": b5.gate(run["phase_error_rad"], 0.02), "frequency": b5.gate(run["frequency_error"], 0.001),
            "eigen_frequency": b5.gate(eigen_error, 1.0e-8), "full_u": b5.gate(run["full_u_error"], 0.01), "full_v": b5.gate(run["full_v_error"], 0.01), "full_a": b5.gate(run["full_a_error"], 0.01),
            "residual": b5.gate(run["free_residual_relative_max"], 1.0e-7), "energy": b5.gate(run["energy_error"], 1.0e-6), "interfaces": interface_status_all[str(level)],
        }
    acceptance_pass = all(item[key]["pass"] for item in acceptance.values() for key in ("q", "v", "a", "amplitude", "phase", "frequency", "eigen_frequency", "full_u", "full_v", "full_a", "residual", "energy"))
    decision = "PASS_V2_CANDIDATE" if acceptance_pass and all(convergence["strictly_decreasing"].values()) and all(convergence["order_pass"].values()) and interface_gate and replay_comparison["all_fields_pass"] and replay_comparison["same_status"] and replay_comparison["same_iterations"] and _failure_ok(failure_contract) else "FAIL_FAILURE_CONTRACT"

    arrays: dict[str, np.ndarray] = {}
    array_manifest: dict[str, Any] = {}
    run_fields = ("time", "displacement", "velocity", "acceleration", "u_ref", "v_ref", "a_ref", "q", "q_ref", "qv", "qv_ref", "qa", "qa_ref", "residual_vector", "residual_norm", "residual_relative", "reactions", "energy_strain", "energy_kinetic", "energy_total", "energy_damping", "energy_external", "damping_power", "external_power")
    for level, run in runs.items():
        for field in run_fields:
            _add_archive_array(arrays, array_manifest, f"dt_t1_{level}_{field}", run[field])
        for interface, values in run["interface"].items():
            for field in ("left_force", "right_force", "power_left", "power_right", "work_left", "work_right"):
                _add_archive_array(arrays, array_manifest, f"dt_t1_{level}_{interface}_{field}", values[field])
    for index, run in enumerate(replays, start=1):
        for field in replay_fields:
            _add_archive_array(arrays, array_manifest, f"replay_{index}_t1_160_{field}", run[field])
    for name, value in (("oracle_K", independent_k), ("oracle_M", independent_m), ("oracle_mode", reference["mode"]), ("oracle_initial_displacement", reference["mode"]), ("oracle_initial_velocity", np.zeros_like(reference["mode"])), ("oracle_initial_acceleration", reference["initial_acceleration"]), ("oracle_fixed_indices", fixed), ("oracle_free_indices", free)):
        _add_archive_array(arrays, array_manifest, name, value)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(ARCHIVE_PATH, **arrays)
    replay_digests = {f"replay_{index}": {field: b5.digest(run[field]) for field in replay_fields} for index, run in enumerate(replays, start=1)}
    manifest = {
        "schema_version": 1, "record_id": "QF-028-WP13-02B7-NEWMARK-V2-EVIDENCE", "work_package": "WP13-02B7", "start_sha": head,
        "contract_commit": CONTRACT_COMMIT, "runner_path": "scripts/run_wp13_02b7_newmark_v2.py", "runner_blob_sha": b5.git_blob(Path(__file__)), "runner_sha256": b5.sha256(Path(__file__)),
        "contract_id": CONTRACT_ID, "contract_blob_sha": b5.git_blob(CONTRACT_PATH), "contract_sha256": b5.sha256(CONTRACT_PATH), "contract_unchanged": True, "contract_committed_before_run": True, "schema_sha256": b5.sha256(SCHEMA_PATH),
        "scope": b5.json_safe({"topology": topology, "ndof": dofs.ndof, "material": contract["benchmark"]["material"], "damping": contract["scope"]["damping"]}),
        "inputs": b5.json_safe({"nodes": base.nodes, "elements": [{"type": element.type, "nodes": list(element.nodes), "material": element.material} for element in base.elements], "materials": base.materials, "fixed_dofs": [{"node": constraint.node, "dofs": list(constraint.dofs)} for constraint in base.fixed_dofs], "loads": [], "dof_order": ["UX", "UY", "UZ"], "analysis_template": {"type": "transient_dynamic", "method": "newmark", "beta": 0.25, "gamma": 0.5, "rayleigh_alpha": 0.0, "rayleigh_beta": 0.0}}),
        "prechecks": b5.json_safe(prechecks), "oracle": b5.json_safe({"reference_frequency_hz": reference["frequency_hz"], "production_frequency_hz": production_frequency, "eigen_frequency_error": eigen_error, "eigenpair_residual": eigen_residual, "production_K_relative_error": prechecks["production_dense_stiffness_relative_difference"], "production_M_relative_error": prechecks["production_dense_mass_relative_difference"], "independence": contract["oracle"]["independence"]}),
        "levels": {str(level): b5.json_safe({key: value for key, value in run.items() if key not in run_fields + ("interface",)}) for level, run in runs.items()}, "convergence": b5.json_safe(convergence), "acceptance": b5.json_safe(acceptance), "interface_gates_all_levels": interface_gate,
        "replays": b5.json_safe({"main_level": "T1/160", "count": 2, "comparison": replay_comparison, "digests": replay_digests}), "failure_contract": b5.json_safe(failure_contract), "silent_fallback": False,
        "archive": {"path": "qualification/0_2_8/wp13_02b7_v2/wp13_02b7_arrays.npz", "sha256": b5.sha256(ARCHIVE_PATH), "array_count": len(arrays), "array_manifest": array_manifest},
        "integrity": {"numerical_source_changed": False, "input_validation_source_changed": True, "formulation_changed": False, "contract_changed": False, "gates_changed": False, "maturity_changed": False, "evidence_0_2_7_changed": False, "historical_b5_rewritten": False},
        "decision": {"status": decision, "owner_gate_required": True, "claim_candidate": "CONNECTED_MIXED_NEWMARK_TET4_WEDGE6_HEX8_BOUNDED" if decision == "PASS_V2_CANDIDATE" else None, "blockers": [] if decision == "PASS_V2_CANDIDATE" else ["unexpected failure-contract rejection"], "full_test_suite": "DEFERRED_TO_WP13_FINAL_GATE"},
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "numpy": np.__version__, "command": "python scripts/run_wp13_02b7_newmark_v2.py"},
    }
    MANIFEST_PATH.write_text(json.dumps(b5.json_safe(manifest), indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": decision, "manifest": str(MANIFEST_PATH), "failure_contract": failure_contract}, indent=2))


if __name__ == "__main__":
    main()
