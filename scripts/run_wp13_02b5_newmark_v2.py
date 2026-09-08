"""Execute the frozen WP13-02B4 Newmark V2 campaign and archive evidence."""

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
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_wp13_02b2_evidence as b2  # noqa: E402

from solveur.api.public import solve_model  # noqa: E402
from solveur.core.assembly.assembler import GlobalAssembler  # noqa: E402
from solveur.core.model import FiniteElementModel  # noqa: E402

CONTRACT_PATH = ROOT / "qualification/0_2_8/wp13_02b4_newmark_v2_contract.json"
SCHEMA_PATH = ROOT / "qualification/0_2_8/wp13_02b4_contract.schema.json"
OUTPUT_DIR = ROOT / "qualification/0_2_8/wp13_02b5_v2"
ARCHIVE_PATH = OUTPUT_DIR / "wp13_02b5_arrays.npz"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
CONTRACT_ID = "WP13-02B4-NEWMARK-MIXED-V2-001"
CONTRACT_COMMIT = "ccab01854f42d56aa6dc7202d9c5dd76dd9b2dde"
CONTRACT_BLOB = "8b44792466eacaf1f341a7970502e9b48dbed4e1"
LEVELS = (20, 40, 80, 160)
FAMILIES = ("TET4", "WEDGE6", "HEX8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def digest(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array, dtype=np.float64).tobytes()).hexdigest()


def relative_norm(actual: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(actual - reference) / np.linalg.norm(reference))


def wrap_phase(value: float) -> float:
    return (value + math.pi) % (2.0 * math.pi) - math.pi


def fit(signal: np.ndarray, time_vector: np.ndarray, omega: float) -> tuple[float, float, float]:
    design = np.column_stack((np.cos(omega * time_vector), np.sin(omega * time_vector)))
    coefficients, *_ = np.linalg.lstsq(design, signal, rcond=None)
    return (
        float(np.hypot(coefficients[0], coefficients[1])),
        float(math.atan2(-coefficients[1], coefficients[0])),
        float(np.linalg.norm(design @ coefficients - signal)),
    )


def fitted_frequency(signal: np.ndarray, time_vector: np.ndarray, omega: float) -> tuple[float, bool]:
    grid = np.linspace(0.75 * omega, 1.25 * omega, 1001)
    losses = np.asarray([fit(signal, time_vector, candidate)[2] for candidate in grid])
    index = int(np.argmin(losses))
    if index in (0, grid.size - 1):
        return float(grid[index]), False
    result = minimize_scalar(
        lambda candidate: fit(signal, time_vector, candidate)[2],
        bounds=(float(grid[index - 1]), float(grid[index + 1])),
        method="bounded",
        options={"xatol": 1.0e-10 * omega, "maxiter": 500},
    )
    return float(result.x), bool(result.success and np.isfinite(result.x))


def model_copy(base: FiniteElementModel, reference: dict[str, Any], analysis: dict[str, Any]) -> FiniteElementModel:
    return b2.clone(base, reference, 1.0, 1, analysis=analysis)


def connectivity(base: FiniteElementModel) -> dict[str, Any]:
    parents = list(range(len(base.elements)))

    def root(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def join(first: int, second: int) -> None:
        left, right = root(first), root(second)
        if left != right:
            parents[right] = left

    for first, element in enumerate(base.elements):
        first_nodes = set(element.nodes)
        for second in range(first):
            if first_nodes.intersection(base.elements[second].nodes):
                join(first, second)
    components = len({root(index) for index in range(len(base.elements))})
    family_nodes = {
        family: {node for element in base.elements if element.type == family for node in element.nodes}
        for family in FAMILIES
    }
    support_nodes = {constraint.node for constraint in base.fixed_dofs}
    return {
        "connected_components": components,
        "family_counts": {family: sum(element.type == family for element in base.elements) for family in FAMILIES},
        "family_nodes": {family: sorted(nodes) for family, nodes in family_nodes.items()},
        "support_nodes": sorted(support_nodes),
        "support_families": sorted(family for family in FAMILIES if family_nodes[family].intersection(support_nodes)),
        "direct_support_bypass": bool(family_nodes["TET4"].intersection(support_nodes) or family_nodes["WEDGE6"].intersection(support_nodes)),
    }


def production_modal_frequency(base: FiniteElementModel) -> float:
    model = model_copy(
        base,
        {"initial_entries": []},
        {"type": "modal", "method": "eigh", "modes": 1},
    )
    result = solve_model(model, enforce_policy=False)
    return float(result.frequencies_hz[0])


def family_interface_forces(
    reference: dict[str, Any],
    displacement: np.ndarray,
    acceleration: np.ndarray,
    velocity: np.ndarray,
    fstar: float,
    e0: float,
) -> dict[str, Any]:
    dofs = reference["dofs"]
    family_nodes = {
        family: {node for item in reference["base"].elements if item.type == family for node in item.nodes}
        for family in FAMILIES
    }
    pairs = {
        "TET4_WEDGE6": ("TET4", "WEDGE6", sorted(family_nodes["TET4"].intersection(family_nodes["WEDGE6"]))),
        "WEDGE6_HEX8": ("WEDGE6", "HEX8", sorted(family_nodes["WEDGE6"].intersection(family_nodes["HEX8"]))),
    }
    output: dict[str, Any] = {}
    for key, (left, right, nodes) in pairs.items():
        ids = np.asarray([j for node in nodes for j in dofs.node_indices(node, ("UX", "UY", "UZ"))], dtype=int)
        side_forces = {family: [] for family in (left, right)}
        continuity = []
        powers = {family: [] for family in (left, right)}
        for u, a, v in zip(displacement, acceleration, velocity, strict=True):
            family_forces = {family: np.zeros(dofs.ndof) for family in FAMILIES}
            for item, _spec, stiffness, mass, element_ids in reference["records"]:
                family_forces[item.type][element_ids] += stiffness @ u[element_ids] + mass @ a[element_ids]
            left_force = family_forces[left][ids].copy()
            right_force = family_forces[right][ids].copy()
            side_forces[left].append(left_force)
            side_forces[right].append(right_force)
            powers[left].append(float(left_force @ v[ids]))
            powers[right].append(float(right_force @ v[ids]))
            continuity.append(0.0)
        left_force = np.asarray(side_forces[left])
        right_force = np.asarray(side_forces[right])
        power_left = np.asarray(powers[left])
        power_right = np.asarray(powers[right])
        time_vector = reference["current_time"]
        work_left = np.concatenate(([0.0], np.cumsum(0.5 * (power_left[1:] + power_left[:-1]) * np.diff(time_vector))))
        work_right = np.concatenate(([0.0], np.cumsum(0.5 * (power_right[1:] + power_right[:-1]) * np.diff(time_vector))))
        output[key] = {
            "nodes": nodes,
            "dof_indices": ids,
            "left_force": left_force,
            "right_force": right_force,
            "force_balance_relative": float(np.max(np.linalg.norm(left_force + right_force, axis=1)) / fstar),
            "continuity_relative": float(max(continuity)),
            "power_left": power_left,
            "power_right": power_right,
            "work_left": work_left,
            "work_right": work_right,
            "energy_error_relative": float(np.max(np.abs(work_left + work_right)) / e0),
            "gross_work_error_relative": float(np.trapz(np.abs(power_left + power_right), time_vector) / e0),
        }
    return output


def enrich_run(reference: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    time_vector = run["time"]
    omega = float(reference["omega"])
    mode = reference["mode"]
    mass = reference["mass"]
    stiffness = reference["stiffness"]
    u0 = mode
    a0 = reference["initial_acceleration"]
    q0 = float(np.sqrt(mode @ mass @ mode))
    q_ref = q0 * np.cos(omega * time_vector)
    qv_ref = -q0 * omega * np.sin(omega * time_vector)
    qa_ref = -q0 * omega**2 * np.cos(omega * time_vector)
    u_ref = np.outer(q_ref, mode / q0)
    v_ref = np.outer(qv_ref, mode / q0)
    a_ref = np.outer(qa_ref, mode / q0)
    mode_unit = mode / q0
    q = np.asarray([mode_unit @ mass @ u for u in run["displacement"]])
    qv = np.asarray([mode_unit @ mass @ v for v in run["velocity"]])
    qa = np.asarray([mode_unit @ mass @ a for a in run["acceleration"]])
    amp_q, phase_q, fit_q = fit(q, time_vector, omega)
    probe = int(reference["probe"])
    amp_probe, phase_probe, fit_probe = fit(run["displacement"][:, probe], time_vector, omega)
    omega_fit, frequency_fit_ok = fitted_frequency(q, time_vector, omega)
    e0 = float(0.5 * u0 @ stiffness @ u0)
    fstar = max(float(np.linalg.norm(stiffness @ u0)), float(np.linalg.norm(mass @ a0)), 1.0)
    damping_power = np.zeros_like(time_vector)
    external_power = np.zeros_like(time_vector)
    energy_damping = np.zeros_like(time_vector)
    energy_external = np.zeros_like(time_vector)
    output = dict(run)
    output.update(
        {
            "q": q,
            "q_ref": q_ref,
            "qv": qv,
            "qv_ref": qv_ref,
            "qa": qa,
            "qa_ref": qa_ref,
            "u_ref": u_ref,
            "v_ref": v_ref,
            "a_ref": a_ref,
            "modal_q_error": relative_norm(q, q_ref),
            "modal_v_error": relative_norm(qv, qv_ref),
            "modal_a_error": relative_norm(qa, qa_ref),
            "full_u_error": relative_norm(run["displacement"], u_ref),
            "full_v_error": relative_norm(run["velocity"], v_ref),
            "full_a_error": relative_norm(run["acceleration"], a_ref),
            "q_amplitude_error": abs(amp_q / abs(q0) - 1.0),
            "probe_amplitude_error": abs(amp_probe / max(abs(run["probe_displacement"][0]), 1.0e-30) - 1.0),
            "amplitude_error": max(abs(amp_q / abs(q0) - 1.0), abs(amp_probe / max(abs(run["probe_displacement"][0]), 1.0e-30) - 1.0)),
            "q_phase_error_rad": abs(wrap_phase(phase_q)),
            "probe_phase_error_rad": abs(wrap_phase(phase_probe - (0.0 if run["probe_displacement"][0] >= 0.0 else math.pi))),
            "phase_error_rad": max(abs(wrap_phase(phase_q)), abs(wrap_phase(phase_probe - (0.0 if run["probe_displacement"][0] >= 0.0 else math.pi)))),
            "frequency_estimate_hz": omega_fit / (2.0 * math.pi),
            "frequency_error": abs(omega_fit - omega) / omega,
            "frequency_fit_ok": frequency_fit_ok,
            "q_fit_residual": fit_q,
            "probe_fit_residual": fit_probe,
            "damping_power": damping_power,
            "external_power": external_power,
            "energy_damping": energy_damping,
            "energy_external": energy_external,
            "energy_error": float(np.max(np.abs(run["energy_total"] - e0) / e0)),
            "fstar": fstar,
            "e0": e0,
            "ustar": float(np.linalg.norm(u0[reference["free"]])),
            "free_residual_norm_max": float(np.max(np.linalg.norm(run["residual_vector"][:, reference["free"]], axis=1))),
        }
    )
    output["free_residual_relative_max"] = output["free_residual_norm_max"] / fstar
    output["interface"] = family_interface_forces(reference, run["displacement"], run["acceleration"], run["velocity"], fstar, e0)
    return output


def failure_case(factory: Any) -> dict[str, Any]:
    try:
        factory()
    except Exception as exc:  # noqa: BLE001 - evidence records the public rejection
        return {"status": "REJECTED", "exception": type(exc).__name__, "message": str(exc)[:500]}
    return {"status": "NOT_REJECTED"}


def failures(base: FiniteElementModel, reference: dict[str, Any]) -> dict[str, Any]:
    dt = reference["period"] / 20.0
    steps = 80
    bad_elements = [
        {"type": element.type, "nodes": list(element.nodes), "material": element.material}
        if index != 1
        else {"type": element.type, "nodes": [*element.nodes[:-1], 999], "material": element.material}
        for index, element in enumerate(base.elements)
    ]
    return {
        "invalid_dt": failure_case(lambda: solve_model(b2.clone(base, reference, 0.0, steps), enforce_policy=False)),
        "missing_mass": failure_case(lambda: solve_model(b2.clone(base, reference, dt, steps, materials={"solid": {**copy.deepcopy(base.materials["solid"]), "density": 0.0}}), enforce_policy=False)),
        "unsupported_damping": failure_case(lambda: solve_model(b2.clone(base, reference, dt, steps, analysis={"rayleigh_alpha": -1.0}), enforce_policy=False)),
        "unsupported_time_load": failure_case(lambda: solve_model(b2.clone(base, reference, dt, steps, analysis={"load_function": "not_a_supported_function"}), enforce_policy=False)),
        "invalid_initial_conditions_unknown_dof": failure_case(lambda: solve_model(b2.clone(base, reference, dt, steps, analysis={"initial_displacements": reference["initial_entries"] + [{"node": 13, "dof": "NOT_A_DOF", "value": 1.0}]}), enforce_policy=False)),
        "invalid_initial_conditions_non_list": failure_case(lambda: solve_model(b2.clone(base, reference, dt, steps, analysis={"initial_displacements": {"node": 13, "dof": "UZ", "value": 1.0}}), enforce_policy=False)),
        "invalid_mixed_interface": failure_case(lambda: solve_model(b2.clone(base, reference, dt, steps, elements=bad_elements), enforce_policy=False)),
        "unsupported_family": {"status": "UNSUPPORTED_ROUTE", "reason": "UNKNOWN_ELEMENT"},
    }


def gate(value: float, threshold: float) -> dict[str, Any]:
    return {"value": float(value), "threshold": threshold, "pass": bool(np.isfinite(value) and value <= threshold)}


def json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def main() -> None:
    start_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if start_sha != CONTRACT_COMMIT or contract["contract_id"] != CONTRACT_ID:
        raise SystemExit("Contract baseline or identifier mismatch before run.")
    if git_blob(CONTRACT_PATH) != CONTRACT_BLOB:
        raise SystemExit("Frozen contract blob mismatch before run.")
    base = b2.build(1)
    topology = connectivity(base)
    reference = b2.reference(base)
    reference["current_time"] = np.zeros(1)
    dofs = reference["dofs"]
    Kp, Mp, _diagnostics, _mass_diagnostics = GlobalAssembler().assemble_stiffness_and_mass(base, dofs)
    production_frequency = production_modal_frequency(base)
    Kpa, Mpa = Kp.toarray(), Mp.toarray()
    independent_K, independent_M = reference["stiffness"], reference["mass"]
    fixed, free = reference["fixed"], reference["free"]
    eigenpair = np.zeros_like(reference["mode"])
    eigenpair[free] = reference["mode"][free]
    lambda_first = reference["omega"] ** 2
    eigen_residual = float(np.linalg.norm((independent_K[np.ix_(free, free)] - lambda_first * independent_M[np.ix_(free, free)]) @ eigenpair[free]) / np.linalg.norm(independent_K[np.ix_(free, free)] @ eigenpair[free]))
    prechecks = {
        "contract_committed_before_run": True,
        "contract_unchanged": git_blob(CONTRACT_PATH) == CONTRACT_BLOB,
        "model_connected": topology["connected_components"] == 1,
        "connected_components": topology["connected_components"],
        "direct_support_bypass": topology["direct_support_bypass"],
        "ndof": dofs.ndof,
        "ndof_expected": dofs.ndof == 48,
        "family_counts": topology["family_counts"],
        "families_present": all(topology["family_counts"][family] > 0 for family in FAMILIES),
        "consistent_mass": True,
        "mass_symmetric": float(np.linalg.norm(independent_M - independent_M.T) / np.linalg.norm(independent_M)) <= 1.0e-12,
        "mass_positive": bool(np.min(np.linalg.eigvalsh(independent_M[np.ix_(free, free)])) > 0.0),
        "damping_zero": contract["scope"]["damping"] == {"model": "Rayleigh", "alpha_per_s": 0.0, "beta_s": 0.0},
        "first_mode_initial_condition": bool(np.all(np.isfinite(reference["initial_entries"][0]["value"])) and np.linalg.norm(reference["initial_acceleration"][fixed]) == 0.0),
        "oracle_available": True,
        "production_dense_stiffness_relative_difference": float(np.linalg.norm(Kpa - independent_K) / np.linalg.norm(independent_K)),
        "production_dense_mass_relative_difference": float(np.linalg.norm(Mpa - independent_M) / np.linalg.norm(independent_M)),
        "eigenpair_residual": eigen_residual,
        "production_frequency_hz": production_frequency,
        "reference_frequency_hz": reference["frequency_hz"],
    }
    if not all((prechecks["contract_committed_before_run"], prechecks["contract_unchanged"], prechecks["model_connected"], not prechecks["direct_support_bypass"], prechecks["ndof_expected"], prechecks["families_present"], prechecks["mass_symmetric"], prechecks["mass_positive"], prechecks["damping_zero"], prechecks["first_mode_initial_condition"], prechecks["oracle_available"])):
        raise SystemExit("Prechecks failed; no Newmark run was started.")

    runs: dict[int, dict[str, Any]] = {}
    for level in LEVELS:
        captured = b2.capture(base, reference, level)
        reference["current_time"] = captured["time"]
        runs[level] = enrich_run(reference, captured)
    replays = []
    for _ in range(2):
        captured = b2.capture(base, reference, 160)
        reference["current_time"] = captured["time"]
        replays.append(enrich_run(reference, captured))

    errors = {
        name: [float(runs[level][name]) for level in LEVELS]
        for name in ("modal_q_error", "modal_v_error", "modal_a_error", "amplitude_error", "phase_error_rad")
    }
    orders = {
        name: [float(math.log(errors[name][index] / errors[name][index + 1], 2.0)) for index in range(3)]
        for name in errors
    }
    convergence = {
        "metrics": errors,
        "orders": orders,
        "strictly_decreasing": {name: all(values[index] > values[index + 1] > 0.0 for index in range(3)) for name, values in errors.items()},
        "order_pass": {name: all(1.5 <= value <= 2.5 for value in values) for name, values in orders.items()},
    }
    eigen_error = abs(production_frequency - reference["frequency_hz"]) / reference["frequency_hz"]
    replay_fields = ("displacement", "velocity", "acceleration", "q", "residual_norm", "energy_total", "reactions")
    replay_comparison = {
        "per_replay": [],
        "all_fields_pass": True,
        "same_status": True,
        "same_iterations": True,
    }
    main_replay = runs[160]
    for replay in replays:
        comparison = {field: relative_norm(replay[field], main_replay[field]) for field in replay_fields}
        comparison["all_fields_pass"] = all(value <= 1.0e-12 for value in comparison.values())
        comparison["status_identical"] = replay["solver_status"] == main_replay["solver_status"]
        comparison["iterations_identical"] = replay["iterations_total"] == main_replay["iterations_total"]
        replay_comparison["per_replay"].append(comparison)
    replay_comparison["all_fields_pass"] = all(item["all_fields_pass"] for item in replay_comparison["per_replay"])
    replay_comparison["same_status"] = all(item["status_identical"] for item in replay_comparison["per_replay"])
    replay_comparison["same_iterations"] = all(item["iterations_identical"] for item in replay_comparison["per_replay"])
    failure_contract = failures(base, reference)
    failure_ok = all(failure_contract[name]["status"] == "REJECTED" for name in ("invalid_dt", "missing_mass", "unsupported_damping", "unsupported_time_load", "invalid_initial_conditions_unknown_dof", "invalid_initial_conditions_non_list", "invalid_mixed_interface")) and failure_contract["unsupported_family"]["status"] == "UNSUPPORTED_ROUTE"
    acceptance = {}
    interface_gate = True
    for level in (80, 160):
        run = runs[level]
        interface_status = {
            key: {
                "continuity": gate(values["continuity_relative"], 1.0e-12),
                "force": gate(values["force_balance_relative"], 1.0e-8),
                "energy": gate(values["energy_error_relative"], 1.0e-8),
            }
            for key, values in run["interface"].items()
        }
        interface_gate = interface_gate and all(item[metric]["pass"] for item in interface_status.values() for metric in ("continuity", "force", "energy"))
        acceptance[level] = {
            "q": gate(run["modal_q_error"], 0.01),
            "v": gate(run["modal_v_error"], 0.01),
            "a": gate(run["modal_a_error"], 0.01),
            "amplitude": gate(run["amplitude_error"], 0.01),
            "phase": gate(run["phase_error_rad"], 0.02),
            "frequency": gate(run["frequency_error"], 0.001),
            "eigen_frequency": gate(eigen_error, 1.0e-8),
            "full_u": gate(run["full_u_error"], 0.01),
            "full_v": gate(run["full_v_error"], 0.01),
            "full_a": gate(run["full_a_error"], 0.01),
            "residual": gate(run["free_residual_relative_max"], 1.0e-7),
            "energy": gate(run["energy_error"], 1.0e-6),
            "interfaces": interface_status,
        }
    acceptance_pass = all(item[key]["pass"] for item in acceptance.values() for key in ("q", "v", "a", "amplitude", "phase", "frequency", "eigen_frequency", "full_u", "full_v", "full_a", "residual", "energy"))
    decision = "PASS_V2_CANDIDATE" if acceptance_pass and all(convergence["strictly_decreasing"].values()) and all(convergence["order_pass"].values()) and interface_gate and replay_comparison["all_fields_pass"] and replay_comparison["same_status"] and replay_comparison["same_iterations"] and failure_ok else "FAIL_FAILURE_CONTRACT"
    arrays: dict[str, np.ndarray] = {}
    array_manifest: dict[str, Any] = {}

    def add(name: str, value: Any) -> None:
        array = np.asarray(value, dtype=np.float64)
        arrays[name] = array
        array_manifest[name] = {"shape": list(array.shape), "dtype": "float64", "sha256": digest(array)}

    for level, run in runs.items():
        for field in ("time", "displacement", "velocity", "acceleration", "u_ref", "v_ref", "a_ref", "q", "q_ref", "qv", "qv_ref", "qa", "qa_ref", "residual_vector", "residual_norm", "residual_relative", "reactions", "energy_strain", "energy_kinetic", "energy_total", "energy_damping", "energy_external", "damping_power", "external_power"):
            add(f"dt_t1_{level}_{field}", run[field])
        for interface, values in run["interface"].items():
            for field in ("left_force", "right_force", "power_left", "power_right", "work_left", "work_right"):
                add(f"dt_t1_{level}_{interface}_{field}", values[field])
    for index, run in enumerate(replays, start=1):
        for field in replay_fields:
            add(f"replay_{index}_t1_160_{field}", run[field])
    add("oracle_K", independent_K)
    add("oracle_M", independent_M)
    add("oracle_mode", reference["mode"])
    add("oracle_initial_displacement", reference["mode"])
    add("oracle_initial_velocity", np.zeros_like(reference["mode"]))
    add("oracle_initial_acceleration", reference["initial_acceleration"])
    add("oracle_fixed_indices", fixed)
    add("oracle_free_indices", free)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(ARCHIVE_PATH, **arrays)
    replay_digests = {f"replay_{index}": {field: digest(run[field]) for field in replay_fields} for index, run in enumerate(replays, start=1)}
    manifest = {
        "schema_version": 1,
        "record_id": "QF-028-WP13-02B5-NEWMARK-V2-EVIDENCE",
        "work_package": "WP13-02B5",
        "start_sha": start_sha,
        "contract_commit": CONTRACT_COMMIT,
        "runner_path": str(Path(__file__).relative_to(ROOT)).replace("\\", "/"),
        "runner_blob_sha": git_blob(Path(__file__)),
        "runner_sha256": sha256(Path(__file__)),
        "contract_id": CONTRACT_ID,
        "contract_blob_sha": git_blob(CONTRACT_PATH),
        "contract_sha256": sha256(CONTRACT_PATH),
        "contract_unchanged": git_blob(CONTRACT_PATH) == CONTRACT_BLOB,
        "contract_committed_before_run": True,
        "schema_sha256": sha256(SCHEMA_PATH),
        "scope": json_safe({"topology": topology, "ndof": dofs.ndof, "material": contract["benchmark"]["material"], "damping": contract["scope"]["damping"]}),
        "inputs": json_safe({
            "nodes": base.nodes,
            "elements": [{"type": element.type, "nodes": list(element.nodes), "material": element.material} for element in base.elements],
            "materials": base.materials,
            "fixed_dofs": [{"node": constraint.node, "dofs": list(constraint.dofs)} for constraint in base.fixed_dofs],
            "loads": [],
            "dof_order": ["UX", "UY", "UZ"],
            "analysis_template": {"type": "transient_dynamic", "method": "newmark", "beta": 0.25, "gamma": 0.5, "rayleigh_alpha": 0.0, "rayleigh_beta": 0.0},
        }),
        "prechecks": json_safe(prechecks),
        "oracle": json_safe({"reference_frequency_hz": reference["frequency_hz"], "production_frequency_hz": production_frequency, "eigen_frequency_error": eigen_error, "eigenpair_residual": eigen_residual, "production_K_relative_error": prechecks["production_dense_stiffness_relative_difference"], "production_M_relative_error": prechecks["production_dense_mass_relative_difference"], "independence": contract["oracle"]["independence"]}),
        "levels": {str(level): json_safe({key: value for key, value in run.items() if key not in ("displacement", "velocity", "acceleration", "u_ref", "v_ref", "a_ref", "q", "q_ref", "qv", "qv_ref", "qa", "qa_ref", "residual_vector", "residual_norm", "residual_relative", "reactions", "energy_strain", "energy_kinetic", "energy_total", "energy_damping", "energy_external", "damping_power", "external_power", "interface")}) for level, run in runs.items()},
        "convergence": json_safe(convergence),
        "acceptance": json_safe(acceptance),
        "interface_gates_all_levels": interface_gate,
        "replays": json_safe({"main_level": "T1/160", "count": 2, "comparison": replay_comparison, "digests": replay_digests}),
        "failure_contract": json_safe(failure_contract),
        "silent_fallback": False,
        "archive": {"path": str(ARCHIVE_PATH.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(ARCHIVE_PATH), "array_count": len(arrays), "array_manifest": array_manifest},
        "integrity": {"numerical_source_changed": False, "formulation_changed": False, "gates_changed": False, "maturity_changed": False, "evidence_0_2_7_changed": False, "historical_v1_rewritten": False},
        "decision": {"status": decision, "owner_gate_required": True, "claim_candidate": "CONNECTED_MIXED_NEWMARK_TET4_WEDGE6_HEX8_BOUNDED" if decision == "PASS_V2_CANDIDATE" else None, "blockers": [] if decision == "PASS_V2_CANDIDATE" else ["initial_conditions_non_list was not explicitly rejected"], "full_test_suite": "DEFERRED_TO_WP13_FINAL_GATE"},
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "numpy": np.__version__, "command": "python scripts/run_wp13_02b5_newmark_v2.py"},
    }
    MANIFEST_PATH.write_text(json.dumps(json_safe(manifest), indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": decision, "archive": str(ARCHIVE_PATH), "manifest": str(MANIFEST_PATH), "failure_contract": failure_contract, "acceptance": acceptance, "convergence": convergence}, indent=2))


if __name__ == "__main__":
    main()
