"""Archive complete WP13-02B Newmark evidence without changing the solver."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
import sys
import time
import types
from pathlib import Path
from typing import Any

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
try:
    import resource as _resource  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - Windows
    _resource = types.ModuleType("resource")
    _resource.RUSAGE_SELF = 0
    _resource.getrusage = lambda _who: types.SimpleNamespace(ru_maxrss=0)
    sys.modules["resource"] = _resource
sys.path.insert(0, str(ROOT / "scripts"))

from run_wp13_01k_mvp import build  # noqa: E402
from solveur.api.public import solve_model  # noqa: E402
from solveur.compatibility import check_compatibility  # noqa: E402
from solveur.core.analyses import dynamic as dynamic_module  # noqa: E402
from solveur.core.model import FiniteElementModel  # noqa: E402
from solveur.elements.registry import ElementRegistry  # noqa: E402
from solveur.materials.factory import MaterialFactory  # noqa: E402

CONTRACT_PATH = ROOT / "qualification/0_2_8/wp13_02a_newmark_contract.json"
OUTPUT_DIR = ROOT / "qualification/0_2_8/wp13_02b2_raw"
ARCHIVE_PATH = OUTPUT_DIR / "wp13_02b2_raw_arrays.npz"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
FAMILIES = ("TET4", "WEDGE6", "HEX8")
DT_LEVELS = (20, 40, 80, 160)
PROBE_NODE = 13
PROBE_DOF = "UZ"


def git_hash(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def clone(base: FiniteElementModel, reference: dict[str, Any], dt: float, steps: int, **overrides: Any) -> FiniteElementModel:
    analysis: dict[str, Any] = {
        "type": "transient_dynamic",
        "method": "newmark",
        "time_step": dt,
        "steps": steps,
        "newmark_beta": 0.25,
        "newmark_gamma": 0.5,
        "initial_displacements": reference["initial_entries"],
        "initial_velocities": [],
        "rayleigh_alpha": 0.0,
        "rayleigh_beta": 0.0,
        "postprocess_mode": "summary",
        "history_probes": [{"node": PROBE_NODE, "dof": PROBE_DOF, "label": "mixed_probe_13_UZ"}],
        "mass_formulation": "consistent",
        "linear_method": "direct",
        "dynamic_residual_failure_tolerance": 1.0e-7,
    }
    analysis.update(overrides.pop("analysis", {}))
    kwargs = {
        "nodes": base.nodes.tolist(),
        "elements": [{"type": e.type, "nodes": list(e.nodes), "material": e.material} for e in base.elements],
        "materials": base.materials,
        "fixed_dofs": [{"node": c.node, "dofs": list(c.dofs)} for c in base.fixed_dofs],
        "loads": [],
        "analysis": analysis,
        "units": base.units,
    }
    kwargs.update(overrides)
    return FiniteElementModel.from_raw(**kwargs)


def local_matrices(base: FiniteElementModel) -> tuple[np.ndarray, np.ndarray, Any, list[tuple[Any, Any, np.ndarray, np.ndarray, list[int]]]]:
    dofs = base.dof_manager()
    stiffness = np.zeros((dofs.ndof, dofs.ndof))
    mass = np.zeros((dofs.ndof, dofs.ndof))
    records = []
    for item in base.elements:
        spec = ElementRegistry.get(item.type)
        coords = base.nodes[list(item.nodes)]
        material = MaterialFactory.create(base.materials[item.material], coordinates=coords)
        element = spec.factory(material)
        k = np.asarray(element.stiffness(coords), dtype=float)
        m = np.asarray(element.mass(coords), dtype=float)
        ids = [index for node in item.nodes for index in dofs.node_indices(node, spec.dofs)]
        stiffness[np.ix_(ids, ids)] += k
        mass[np.ix_(ids, ids)] += m
        records.append((item, spec, k, m, ids))
    return stiffness, mass, dofs, records


def reference(base: FiniteElementModel) -> dict[str, Any]:
    stiffness, mass, dofs, records = local_matrices(base)
    fixed = np.asarray(sorted({dofs.index(c.node, name) for c in base.fixed_dofs for name in c.dofs}), dtype=int)
    free = np.setdiff1d(np.arange(dofs.ndof), fixed)
    values, vectors = eigh(stiffness[np.ix_(free, free)], mass[np.ix_(free, free)])
    first = int(np.flatnonzero(values > 1.0e-10)[0])
    omega = math.sqrt(float(values[first]))
    mode = np.zeros(dofs.ndof)
    mode[free] = vectors[:, first]
    mode *= 1.0e-5 / max(float(np.max(np.abs(mode))), 1.0e-30)
    initial_acceleration = np.zeros(dofs.ndof)
    initial_acceleration[free] = np.linalg.solve(
        mass[np.ix_(free, free)], -(stiffness @ mode)[free]
    )
    initial_entries = [
        {"node": node, "dof": name, "value": float(mode[dofs.index(node, name)])}
        for node in range(base.node_count)
        for name in ("UX", "UY", "UZ")
        if dofs.has(node, name) and mode[dofs.index(node, name)] != 0.0
    ]
    return {
        "base": base,
        "stiffness": stiffness,
        "mass": mass,
        "dofs": dofs,
        "records": records,
        "fixed": fixed,
        "free": free,
        "mode": mode,
        "omega": omega,
        "frequency_hz": omega / (2.0 * math.pi),
        "period": 2.0 * math.pi / omega,
        "initial_acceleration": initial_acceleration,
        "initial_entries": initial_entries,
        "probe": dofs.index(PROBE_NODE, PROBE_DOF),
    }


def relative_rms(actual: np.ndarray, expected: np.ndarray) -> float:
    return float(np.linalg.norm(actual - expected) / max(np.linalg.norm(expected), 1.0e-30))


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


def estimate_frequency(signal: np.ndarray, time_vector: np.ndarray, omega: float) -> float:
    result = minimize_scalar(
        lambda candidate: fit(signal, time_vector, candidate)[2],
        bounds=(0.75 * omega, 1.25 * omega),
        method="bounded",
        options={"xatol": 1.0e-10},
    )
    return float(result.x)


def interface_energy(
    ref: dict[str, Any],
    time_vector: np.ndarray,
    displacement: np.ndarray,
    velocity: np.ndarray,
    acceleration: np.ndarray,
) -> dict[str, Any]:
    base, dofs = ref["base"], ref["dofs"]
    family_nodes = {
        family: {node for e in base.elements if e.type == family for node in e.nodes}
        for family in FAMILIES
    }
    pairs = {
        "TET4_WEDGE6": ("TET4", "WEDGE6", sorted(family_nodes["TET4"] & family_nodes["WEDGE6"])),
        "WEDGE6_HEX8": ("WEDGE6", "HEX8", sorted(family_nodes["WEDGE6"] & family_nodes["HEX8"])),
    }
    powers = {key: {"left": [], "right": []} for key in pairs}
    for index in range(time_vector.size):
        family_forces = {family: np.zeros(dofs.ndof) for family in FAMILIES}
        for item, _spec, k, m, ids in ref["records"]:
            family_forces[item.type][ids] += k @ displacement[index, ids] + m @ acceleration[index, ids]
        for key, (left, right, nodes) in pairs.items():
            ids = [j for node in nodes for j in dofs.node_indices(node, ("UX", "UY", "UZ"))]
            powers[key]["left"].append(float(family_forces[left][ids] @ velocity[index, ids]))
            powers[key]["right"].append(float(family_forces[right][ids] @ velocity[index, ids]))
    result = {}
    for key, values in powers.items():
        left_power = np.asarray(values["left"])
        right_power = np.asarray(values["right"])
        closure = left_power + right_power
        left_energy = float(np.trapz(left_power, time_vector))
        right_energy = float(np.trapz(right_power, time_vector))
        closure_energy = float(np.trapz(closure, time_vector))
        result[key] = {
            "power_left_W": left_power,
            "power_right_W": right_power,
            "power_closure_W": closure,
            "energy_transfer_left_J": left_energy,
            "energy_transfer_right_J": right_energy,
            "energy_closure_error_J": abs(closure_energy),
            "energy_closure_error_relative": abs(closure_energy) / max(abs(left_energy) + abs(right_energy), 1.0e-30),
            "maximum_power_closure_W": float(np.max(np.abs(closure))),
        }
    return result


def capture(base: FiniteElementModel, ref: dict[str, Any], points: int) -> dict[str, Any]:
    dt, steps = ref["period"] / points, 4 * points
    states = []
    original = dynamic_module.history_row

    def recorder(*args: Any, **kwargs: Any) -> dict[str, Any]:
        states.append((np.array(args[3], copy=True), np.array(args[4], copy=True), np.array(args[5], copy=True)))
        return original(*args, **kwargs)

    dynamic_module.history_row = recorder
    started = time.perf_counter()
    try:
        result = solve_model(clone(base, ref, dt, steps), enforce_policy=False)
    finally:
        dynamic_module.history_row = original
    elapsed = time.perf_counter() - started
    time_vector = np.r_[0.0, np.arange(1, steps + 1) * dt]
    displacement = np.vstack((ref["mode"], [state[0] for state in states]))
    velocity = np.vstack((np.zeros_like(ref["mode"]), [state[1] for state in states]))
    acceleration = np.vstack((ref["initial_acceleration"], [state[2] for state in states]))
    k, m, free, fixed = ref["stiffness"], ref["mass"], ref["free"], ref["fixed"]
    # The modal coordinate uses the generalized-mass-normalized vector
    # defined by the independent oracle, with no change to the production
    # Newmark implementation.
    mode_unit = ref["mode"] / max(float(np.sqrt(ref["mode"] @ m @ ref["mode"])), 1.0e-30)
    q = np.asarray([mode_unit @ m @ u for u in displacement])
    qv = np.asarray([mode_unit @ m @ v for v in velocity])
    qa = np.asarray([mode_unit @ m @ a for a in acceleration])
    q0 = float(q[0])
    omega = ref["omega"]
    q_ref = q0 * np.cos(omega * time_vector)
    qv_ref = -q0 * omega * np.sin(omega * time_vector)
    qa_ref = -q0 * omega**2 * np.cos(omega * time_vector)
    probe = ref["probe"]
    probe_values = displacement[:, probe]
    probe_ref = ref["mode"][probe] * np.cos(omega * time_vector)
    amplitude, phase, _ = fit(probe_values, time_vector, omega)
    phase_ref = 0.0 if ref["mode"][probe] >= 0.0 else math.pi
    strain = np.asarray([0.5 * u @ k @ u for u in displacement])
    kinetic = np.asarray([0.5 * v @ m @ v for v in velocity])
    total = strain + kinetic
    residual_vector = np.asarray([m @ a + k @ u for u, a in zip(displacement, acceleration, strict=True)])
    residual_norm = np.linalg.norm(residual_vector[:, free], axis=1)
    residual_reference = np.maximum.reduce([
        np.linalg.norm((m @ acceleration.T).T[:, free], axis=1),
        np.linalg.norm((k @ displacement.T).T[:, free], axis=1),
        np.ones(time_vector.size),
    ])
    raw_interface = interface_energy(ref, time_vector, displacement, velocity, acceleration)
    return {
        "points_per_period": points,
        "dt_s": dt,
        "steps": steps,
        "runtime_s": elapsed,
        "solver_status": result.status,
        "time": time_vector,
        "displacement": displacement,
        "velocity": velocity,
        "acceleration": acceleration,
        "residual_vector": residual_vector,
        "residual_norm": residual_norm,
        "residual_relative": residual_norm / residual_reference,
        "reactions": residual_vector[:, fixed],
        "energy_strain": strain,
        "energy_kinetic": kinetic,
        "energy_total": total,
        "energy_relative_drift": (total - total[0]) / max(abs(float(total[0])), 1.0e-30),
        "modal_q": q,
        "modal_q_reference": q_ref,
        "modal_v": qv,
        "modal_v_reference": qv_ref,
        "modal_a": qa,
        "modal_a_reference": qa_ref,
        "probe_displacement": probe_values,
        "probe_reference": probe_ref,
        "probe_amplitude_error": abs(amplitude / max(abs(ref["mode"][probe]), 1.0e-30) - 1.0),
        "probe_phase_error_rad": abs(wrap_phase(phase - phase_ref)),
        "frequency_estimate_hz": estimate_frequency(q, time_vector, omega) / (2.0 * math.pi),
        "frequency_error_relative": abs(estimate_frequency(q, time_vector, omega) - omega) / omega,
        "q_error": relative_rms(q, q_ref),
        "v_error": relative_rms(qv, qv_ref),
        "a_error": relative_rms(qa, qa_ref),
        "interface_energy": raw_interface,
        "dynamic_residual_norm_max": float(np.max(residual_norm)),
        "dynamic_residual_relative_max": float(np.max(residual_norm / residual_reference)),
        "energy_drift_max": float(np.max(np.abs((total - total[0]) / max(abs(float(total[0])), 1.0e-30)))),
        "iterations_per_step": int(result.solver["linear_execution"]["iteration_count_total"] // steps),
        "iterations_total": int(result.solver["linear_execution"]["iteration_count_total"]),
    }


def digest(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array, dtype=np.float64).tobytes()).hexdigest()


def failure(factory: Any) -> dict[str, Any]:
    try:
        factory()
    except Exception as exc:  # noqa: BLE001 - record the explicit contract failure
        return {"status": "REJECTED", "exception": type(exc).__name__, "message": str(exc)[:300]}
    return {"status": "NOT_REJECTED"}


def run_failure_contract(base: FiniteElementModel, ref: dict[str, Any]) -> dict[str, Any]:
    dt, steps = ref["period"] / 20.0, 80
    bad_elements = [
        {"type": e.type, "nodes": list(e.nodes), "material": e.material}
        if index != 1
        else {"type": e.type, "nodes": [*e.nodes[:-1], 999], "material": e.material}
        for index, e in enumerate(base.elements)
    ]
    return {
        "invalid_dt": failure(lambda: solve_model(clone(base, ref, 0.0, steps), enforce_policy=False)),
        "missing_mass": failure(lambda: solve_model(clone(base, ref, dt, steps, materials={"solid": {**copy.deepcopy(base.materials["solid"]), "density": 0.0}}), enforce_policy=False)),
        "unsupported_damping": failure(lambda: solve_model(clone(base, ref, dt, steps, analysis={"rayleigh_alpha": -1.0}), enforce_policy=False)),
        "unsupported_time_load": failure(lambda: solve_model(clone(base, ref, dt, steps, analysis={"load_function": "not_a_supported_function"}), enforce_policy=False)),
        "invalid_initial_conditions": failure(lambda: solve_model(clone(base, ref, dt, steps, analysis={"initial_displacements": ref["initial_entries"] + [{"node": PROBE_NODE, "dof": "NOT_A_DOF", "value": 1.0}]}), enforce_policy=False)),
        "invalid_mixed_interface": failure(lambda: solve_model(clone(base, ref, dt, steps, elements=bad_elements), enforce_policy=False)),
        "unsupported_family": {
            "status": check_compatibility("PYRAMID5", "transient_dynamic", "isotropic_3d").status,
            "reason": check_compatibility("PYRAMID5", "transient_dynamic", "isotropic_3d").reason,
        },
    }


def json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def main() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    base = build(1)
    ref = reference(base)
    runs = {level: capture(base, ref, level) for level in DT_LEVELS}
    replay_1, replay_2 = capture(base, ref, 160), capture(base, ref, 160)
    failure_contract = run_failure_contract(base, ref)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    arrays: dict[str, np.ndarray] = {}
    array_manifest: dict[str, Any] = {}
    raw_fields = (
        "time", "displacement", "velocity", "acceleration", "residual_vector",
        "residual_norm", "residual_relative", "reactions", "energy_strain",
        "energy_kinetic", "energy_total", "energy_relative_drift", "modal_q",
        "modal_q_reference", "modal_v", "modal_v_reference", "modal_a",
        "modal_a_reference", "probe_displacement", "probe_reference",
    )

    def add(name: str, array: np.ndarray) -> None:
        arrays[name] = np.asarray(array, dtype=np.float64)
        array_manifest[name] = {"shape": list(arrays[name].shape), "dtype": "float64", "sha256": digest(arrays[name])}

    for level, run in runs.items():
        for field in raw_fields:
            add(f"dt_t1_{level}_{field}", run[field])
        for interface, values in run["interface_energy"].items():
            for field in ("power_left_W", "power_right_W", "power_closure_W"):
                add(f"dt_t1_{level}_{interface}_{field}", values[field])
    for index, run in enumerate((replay_1, replay_2), start=1):
        for field in raw_fields:
            add(f"replay_{index}_t1_160_{field}", run[field])
    np.savez_compressed(ARCHIVE_PATH, **arrays)

    replay = {
        "displacement_relative_l2": relative_rms(replay_1["displacement"], replay_2["displacement"]),
        "velocity_relative_l2": relative_rms(replay_1["velocity"], replay_2["velocity"]),
        "acceleration_relative_l2": relative_rms(replay_1["acceleration"], replay_2["acceleration"]),
        "reaction_relative_l2": relative_rms(replay_1["reactions"], replay_2["reactions"]),
        "residual_relative_l2": relative_rms(replay_1["residual_norm"], replay_2["residual_norm"]),
        "energy_relative_l2": relative_rms(replay_1["energy_total"], replay_2["energy_total"]),
        "iterations_identical": replay_1["iterations_total"] == replay_2["iterations_total"],
        "status_identical": replay_1["solver_status"] == replay_2["solver_status"],
        "digests_identical": all(digest(replay_1[field]) == digest(replay_2[field]) for field in ("displacement", "velocity", "acceleration", "reactions", "energy_total", "residual_norm")),
    }
    contract_sha = git_hash(CONTRACT_PATH)
    manifest = {
        "schema_version": 1,
        "record_id": "QF-028-WP13-02B2-EVIDENCE-CLOSURE",
        "work_package": "WP13-02B2",
        "baseline_sha": "7adedc27d983a5511fca11684427d51e73bd6628",
        "contract_id": contract["contract_id"],
        "contract_blob_sha": contract_sha,
        "contract_unchanged": contract_sha == "7e5af8374e33e8d45a61d4a60b01127802bfca64",
        "contract_interpretation": {
            "contract_ambiguity": True,
            "basis": "The frozen contract fixes four dt levels and numeric values but does not explicitly define coarse/fine applicability for RMS and phase gates, nor a replay level. The 02A2 report records a fine-level interpretation; it is not inserted into the original contract.",
            "gates": {
                "dt_levels": "ALL_DT_LEVELS",
                "dt_convergence_relative_rms": "CONTRACT_AMBIGUITY; proposed FINE_LEVELS_ONLY",
                "oracle_displacement_relative_rms": "CONTRACT_AMBIGUITY; proposed FINE_LEVELS_ONLY",
                "oracle_phase_absolute_rad": "CONTRACT_AMBIGUITY; proposed FINE_LEVELS_ONLY",
                "first_frequency_relative": "ALL_DT_LEVELS",
                "newmark_dynamic_residual_relative": "ALL_DT_LEVELS",
                "undamped_energy_relative_drift": "ALL_DT_LEVELS",
                "interface_displacement_continuity": "ALL_DT_LEVELS",
                "interface_force_transfer_relative": "ALL_DT_LEVELS",
                "replay_requirements": "CONTRACT_AMBIGUITY; proposed FINE_LEVELS_ONLY at T1/160",
                "pure_control": "CHARACTERIZATION_ONLY_WHEN_COMPARABLE",
            },
        },
        "scope": {
            "connected_components": 1,
            "families": FAMILIES,
            "family_counts": {family: sum(e.type == family for e in base.elements) for family in FAMILIES},
            "ndof": base.dof_manager().ndof,
            "probe": {"node": PROBE_NODE, "dof": PROBE_DOF, "index": ref["probe"]},
        },
        "raw_archive": {
            "path": str(ARCHIVE_PATH.relative_to(ROOT)).replace("\\", "/"),
            "sha256": hashlib.sha256(ARCHIVE_PATH.read_bytes()).hexdigest(),
            "format": "NumPy NPZ compressed; float64 arrays; t=0 and every Newmark step are included",
            "array_manifest": array_manifest,
        },
        "reference": {
            "method": "independent local-element K/M scatter + scipy generalized eigensolve + closed-form first-mode oscillator",
            "production_newmark_or_router_reused": False,
            "omega_rad_s": ref["omega"],
            "frequency_hz": ref["frequency_hz"],
            "period_s": ref["period"],
            "modal_coordinate": "q=phi_unit.T @ M @ u; qv=phi_unit.T @ M @ v; qa=phi_unit.T @ M @ a",
            "frequency_estimator": "bounded least-squares cosine/sine fit on q over [0.75,1.25]*omega_reference; probe amplitude/phase uses fixed omega_reference",
        },
        "runs": {str(level): {key: json_safe(value) for key, value in run.items() if isinstance(value, (str, int, float, bool)) or key == "interface_energy"} for level, run in runs.items()},
        "modal_analytical_controls": {str(level): {"q_error": run["q_error"], "v_error": run["v_error"], "a_error": run["a_error"], "gate_application": "CONTRACT_AMBIGUITY for q; CHARACTERIZATION_ONLY for v/a"} for level, run in runs.items()},
        "replays": {"level": "T1/160", "comparison": replay},
        "failure_contract": failure_contract,
        "integrity": {
            "numerical_source_changed": False,
            "formulation_changed": False,
            "gates_changed": False,
            "maturity_changed": False,
            "evidence_0_2_7_changed": False,
            "original_contract_rewritten": False,
            "prior_02b_results_rewritten": False,
        },
        "decision": {
            "status": "CONTRACT_AMBIGUITY_BLOCKING",
            "raw_evidence_status": "CLOSED_FOR_ARCHIVAL_DATA",
            "claim_auto_promotion": False,
            "owner_gate_required": True,
            "blockers": ["coarse/fine gate applicability is not explicit in the frozen contract"],
        },
    }
    MANIFEST_PATH.write_text(json.dumps(json_safe(manifest), indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"archive": str(ARCHIVE_PATH), "manifest": str(MANIFEST_PATH), "replay": replay, "failure_contract": failure_contract}, indent=2))


if __name__ == "__main__":
    main()
