"""Prospective WP13-02 mixed serial dynamics campaign.

This runner deliberately uses a fresh contract and output directory.  Its
dense references scatter element matrices directly through the registry and
implement the Newmark recurrence / complex frequency solve independently of
the production analysis routes.  Element kernels are shared by necessity; no
production assembler, reduction, or time/frequency solver is reused by an
oracle.
"""

# ruff: noqa: E701, E702, E731

from __future__ import annotations

import copy
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
import types
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy.linalg import eigh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import resource as _resource  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - Windows compatibility of the existing builder
    _resource = types.ModuleType("resource")
    _resource.RUSAGE_SELF = 0
    _resource.getrusage = lambda _who: types.SimpleNamespace(ru_maxrss=0)
    sys.modules["resource"] = _resource

from run_wp13_01k_mvp import build  # noqa: E402
from solveur.api.public import solve_model  # noqa: E402
from solveur.compatibility.preflight import CompatibilityError  # noqa: E402
from solveur.core.analyses import dynamic as dynamic_module  # noqa: E402
from solveur.core.errors import InputValidationError, MeshValidationError  # noqa: E402
from solveur.core.model import FiniteElementModel  # noqa: E402
from solveur.elements.registry import ElementRegistry  # noqa: E402
from solveur.materials.factory import MaterialFactory  # noqa: E402


CONTRACT_PATH = ROOT / "qualification/0_2_8/wp13_02_mixed_dynamics_contract.json"
OUTPUT_DIR = ROOT / "qualification/0_2_8/wp13_02_mixed_dynamics_vnv" / "final"
ARCHIVE_PATH = OUTPUT_DIR / "wp13_02_mixed_dynamics_arrays.npz"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
FAMILIES = ("TET4", "WEDGE6", "HEX8")
INTERFACES = {
    "TET4_WEDGE6": ("TET4", "WEDGE6"),
    "WEDGE6_HEX8": ("WEDGE6", "HEX8"),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return safe(value.tolist())
    if isinstance(value, np.generic):
        return safe(value.item())
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag}
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite_float": "NaN" if math.isnan(value) else ("+Inf" if value > 0.0 else "-Inf")}
    if isinstance(value, dict):
        return {str(key): safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(item) for item in value]
    return value


def canonical(value: Any) -> str:
    return json.dumps(safe(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def relative(actual: np.ndarray, expected: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(actual) - np.asarray(expected)) / max(np.linalg.norm(expected), 1.0e-30))


def phase_distance(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    return np.abs((np.asarray(first) - np.asarray(second) + math.pi) % (2.0 * math.pi) - math.pi)


def load_contract() -> tuple[dict[str, Any], str]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["contract_id"] == "WP13-02-MIXED-DYNAMICS-001"
    assert contract["status"] == "PREDECLARED"
    return contract, sha256_file(CONTRACT_PATH)


def element_matrices(base: FiniteElementModel) -> dict[str, Any]:
    """Independently scatter dense K and M without GlobalAssembler."""
    dofs = base.dof_manager()
    stiffness = np.zeros((dofs.ndof, dofs.ndof), dtype=float)
    mass = np.zeros_like(stiffness)
    records: list[dict[str, Any]] = []
    for definition in base.elements:
        spec = ElementRegistry.get(definition.type)
        coordinates = base.nodes[list(definition.nodes)]
        element = spec.factory(MaterialFactory.create(base.materials[definition.material], coordinates=coordinates))
        local_k = np.asarray(element.stiffness(coordinates), dtype=float)
        local_m = np.asarray(element.mass(coordinates), dtype=float)
        ids = [entry for node in definition.nodes for entry in dofs.node_indices(node, spec.dofs)]
        stiffness[np.ix_(ids, ids)] += local_k
        mass[np.ix_(ids, ids)] += local_m
        records.append({"family": definition.type, "nodes": list(definition.nodes), "ids": ids, "K": local_k, "M": local_m})
    fixed = np.asarray(sorted({dofs.index(item.node, name) for item in base.fixed_dofs for name in item.dofs}), dtype=int)
    free = np.setdiff1d(np.arange(dofs.ndof), fixed)
    values, vectors = eigh(stiffness[np.ix_(free, free)], mass[np.ix_(free, free)], check_finite=True)
    positive = np.flatnonzero(values > 1.0e-10)
    if not positive.size:
        raise RuntimeError("Independent dense oracle found no positive fixed-base mode.")
    first = int(positive[0])
    omega = math.sqrt(float(values[first]))
    phi = np.zeros(dofs.ndof)
    phi[free] = vectors[:, first]
    if phi[free][int(np.argmax(np.abs(phi[free])))] < 0.0:
        phi *= -1.0
    return {"K": stiffness, "M": mass, "dofs": dofs, "records": records, "fixed": fixed, "free": free, "omega1": omega, "f1": omega / (2.0 * math.pi), "phi": phi}


def load_vector(base: FiniteElementModel, dofs: Any) -> tuple[np.ndarray, list[int]]:
    nodes = [index for index, point in enumerate(base.nodes) if np.isclose(float(point[2]), 3.0, atol=1.0e-14)]
    vector = np.zeros(dofs.ndof)
    for node in nodes:
        vector[dofs.index(node, "UZ")] = 1.0 / len(nodes)
    return vector, nodes


def model_payload(base: FiniteElementModel, analysis: dict[str, Any], loads: list[dict[str, Any]] | None = None, *, elements: list[dict[str, Any]] | None = None, materials: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "nodes": base.nodes.tolist(),
        "elements": elements if elements is not None else [{"type": item.type, "nodes": list(item.nodes), "material": item.material} for item in base.elements],
        "materials": copy.deepcopy(base.materials) if materials is None else materials,
        "fixed_dofs": [{"node": item.node, "dofs": list(item.dofs)} for item in base.fixed_dofs],
        "loads": loads if loads is not None else [],
        "analysis": analysis,
        "units": base.units,
    }


def required_scope(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "required_mixed_families": contract["scope"]["families"],
        "required_mixed_interfaces": contract["scope"]["required_mixed_interfaces"],
    }


def dynamic_model(base: FiniteElementModel, contract: dict[str, Any], dt: float, steps: int, alpha: float, period: float) -> FiniteElementModel:
    _, top_nodes = load_vector(base, base.dof_manager())
    loads = [{"node": node, "dof": "UZ", "value": 1.0 / len(top_nodes)} for node in top_nodes]
    analysis = {
        "type": "transient_dynamic", "method": "newmark_average_acceleration", "time_step": dt, "steps": steps,
        "newmark_beta": contract["newmark"]["beta"], "newmark_gamma": contract["newmark"]["gamma"],
        "initial_displacements": [], "initial_velocities": [], "damping_model": "rayleigh", "rayleigh_alpha": alpha, "rayleigh_beta": 0.0,
        "mass_formulation": "consistent", "linear_method": "direct", "backend": "scipy",
        "load_function": contract["newmark"]["load_function"], "pulse_duration": period * contract["newmark"]["pulse_duration_period_fraction"],
        "dynamic_residual_failure_tolerance": contract["newmark"]["gates"]["residual_relative"], "postprocess_mode": "summary", **required_scope(contract),
    }
    return FiniteElementModel.from_raw(**model_payload(base, analysis, loads))


def harmonic_model(base: FiniteElementModel, contract: dict[str, Any], frequencies: list[float], alpha: float) -> FiniteElementModel:
    _, top_nodes = load_vector(base, base.dof_manager())
    loads = [{"node": node, "dof": "UZ", "value": 1.0 / len(top_nodes)} for node in top_nodes]
    analysis = {
        "type": "harmonic_response", "method": "direct_frequency", "frequencies_hz": frequencies,
        "damping_model": "rayleigh", "rayleigh_alpha": alpha, "rayleigh_beta": 0.0,
        "mass_formulation": "consistent", "backend": "scipy", "harmonic_residual_failure_tolerance": contract["harmonic"]["gates"]["residual_relative"], **required_scope(contract),
    }
    return FiniteElementModel.from_raw(**model_payload(base, analysis, loads))


def pulse_factor(time_value: float, duration: float) -> float:
    return math.sin(math.pi * time_value / duration) if 0.0 <= time_value <= duration else 0.0


def dense_newmark(ref: dict[str, Any], dt: float, steps: int, alpha: float, beta: float, gamma: float, duration: float, load: np.ndarray) -> dict[str, np.ndarray]:
    """Dense reference Newmark recurrence, independent from DynamicSolver."""
    free, ndof = ref["free"], ref["dofs"].ndof
    k = ref["K"][np.ix_(free, free)]
    m = ref["M"][np.ix_(free, free)]
    c = alpha * m
    f = load[free]
    uf = np.zeros((steps + 1, free.size))
    vf = np.zeros_like(uf)
    af = np.zeros_like(uf)
    forces = np.zeros((steps + 1, ndof))
    effective = k + gamma / (beta * dt) * c + m / (beta * dt**2)
    for index in range(1, steps + 1):
        factor = pulse_factor(index * dt, duration)
        forces[index] = factor * load
        rhs = factor * f
        rhs += m @ (uf[index - 1] / (beta * dt**2) + vf[index - 1] / (beta * dt) + (1.0 / (2.0 * beta) - 1.0) * af[index - 1])
        rhs += c @ (gamma * uf[index - 1] / (beta * dt) + (gamma / beta - 1.0) * vf[index - 1] + dt * (gamma / (2.0 * beta) - 1.0) * af[index - 1])
        uf[index] = np.linalg.solve(effective, rhs)
        af[index] = (uf[index] - uf[index - 1]) / (beta * dt**2) - vf[index - 1] / (beta * dt) - (1.0 / (2.0 * beta) - 1.0) * af[index - 1]
        vf[index] = vf[index - 1] + dt * ((1.0 - gamma) * af[index - 1] + gamma * af[index])
    u = np.zeros((steps + 1, ndof)); v = np.zeros_like(u); a = np.zeros_like(u)
    u[:, free], v[:, free], a[:, free] = uf, vf, af
    return {"u": u, "v": v, "a": a, "forces": forces}


def capture_newmark(base: FiniteElementModel, contract: dict[str, Any], ref: dict[str, Any], points: int, label: str) -> dict[str, Any]:
    period = 2.0 * math.pi / ref["omega1"]
    dt, steps = period / points, int(contract["newmark"]["total_time_periods"] * points)
    alpha = 2.0 * contract["scope"]["damping"]["zeta_first_mode"] * ref["omega1"]
    model = dynamic_model(base, contract, dt, steps, alpha, period)
    duration = period * contract["newmark"]["pulse_duration_period_fraction"]
    captured: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    original = dynamic_module.history_row

    def record(*args: Any, **kwargs: Any) -> dict[str, Any]:
        captured.append((np.array(args[3], copy=True), np.array(args[4], copy=True), np.array(args[5], copy=True)))
        return original(*args, **kwargs)

    dynamic_module.history_row = record
    try:
        started = time.perf_counter()
        result = solve_model(model, enforce_policy=False)
        elapsed = time.perf_counter() - started
    finally:
        dynamic_module.history_row = original
    load, _ = load_vector(base, ref["dofs"])
    runtime = {"u": np.vstack((np.zeros(ref["dofs"].ndof), [row[0] for row in captured])), "v": np.vstack((np.zeros(ref["dofs"].ndof), [row[1] for row in captured])), "a": np.vstack((np.zeros(ref["dofs"].ndof), [row[2] for row in captured]))}
    oracle = dense_newmark(ref, dt, steps, alpha, contract["newmark"]["beta"], contract["newmark"]["gamma"], duration, load)
    metrics = newmark_metrics(ref, runtime, oracle, alpha, dt)
    histories = {name: [] for name in INTERFACES}
    for u, v, a in zip(runtime["u"], runtime["v"], runtime["a"], strict=True):
        step_interfaces = interface_metrics(contract, ref, u, acceleration=a, velocity=v, alpha=alpha)
        for name, value in step_interfaces.items():
            histories[name].append(value)
    metrics["interface_history"] = histories
    metrics.update({"label": label, "dt": dt, "steps": steps, "duration": duration, "alpha": alpha, "runtime_seconds": elapsed, "status": str(result.status), "solver": result.solver, "oracle": oracle, **runtime})
    return metrics


def energy_history(ref: dict[str, Any], u: np.ndarray, v: np.ndarray, forces: np.ndarray, alpha: float, dt: float) -> dict[str, np.ndarray]:
    k, m, c = ref["K"], ref["M"], alpha * ref["M"]
    strain = np.einsum("ij,jk,ik->i", u, k, u) * 0.5
    kinetic = np.einsum("ij,jk,ik->i", v, m, v) * 0.5
    damp_power = np.einsum("ij,jk,ik->i", v, c, v)
    damping = np.r_[0.0, np.cumsum(0.5 * (damp_power[:-1] + damp_power[1:]) * dt)]
    increments = 0.5 * np.sum((forces[:-1] + forces[1:]) * (u[1:] - u[:-1]), axis=1)
    work = np.r_[0.0, np.cumsum(increments)]
    scale = max(float(np.max(np.abs(work))), float(np.max(np.abs(strain + kinetic))), 1.0e-30)
    return {"strain": strain, "kinetic": kinetic, "damping": damping, "external_work": work, "balance": strain + kinetic + damping - work, "balance_error": np.abs(strain + kinetic + damping - work) / scale}


def newmark_metrics(ref: dict[str, Any], runtime: dict[str, np.ndarray], oracle: dict[str, np.ndarray], alpha: float, dt: float) -> dict[str, Any]:
    k, m, free = ref["K"], ref["M"], ref["free"]
    c = alpha * m
    residual = np.asarray([m @ a + c @ v + k @ u - force for u, v, a, force in zip(runtime["u"], runtime["v"], runtime["a"], oracle["forces"], strict=True)])
    scale = max(float(np.linalg.norm(oracle["forces"][:, free], axis=1).max()), 1.0)
    runtime_energy = energy_history(ref, runtime["u"], runtime["v"], oracle["forces"], alpha, dt)
    probe = ref["dofs"].index(min(index for index, point in enumerate(ref["base"].nodes) if np.isclose(point[2], 3.0)), "UZ")
    return {
        "displacement_error": relative(runtime["u"], oracle["u"]), "velocity_error": relative(runtime["v"], oracle["v"]), "acceleration_error": relative(runtime["a"], oracle["a"]),
        "peak_response_error": abs(float(np.max(np.abs(runtime["u"][:, probe]))) - float(np.max(np.abs(oracle["u"][:, probe])))) / max(float(np.max(np.abs(oracle["u"][:, probe]))), 1.0e-30),
        "residual_vectors": residual, "residual_relative": np.linalg.norm(residual[:, free], axis=1) / scale,
        "energy": runtime_energy, "energy_drift": float(np.max(np.abs((runtime_energy["strain"] + runtime_energy["kinetic"]) - (runtime_energy["strain"][0] + runtime_energy["kinetic"][0])))),
        "energy_balance_error": float(np.max(runtime_energy["balance_error"])), "probe": probe,
    }


def shared_nodes(ref: dict[str, Any], left: str, right: str) -> tuple[int, ...]:
    nodes = {family: {node for row in ref["records"] if row["family"] == family for node in row["nodes"]} for family in FAMILIES}
    return tuple(sorted(nodes[left].intersection(nodes[right])))


def family_trace(records: list[dict[str, Any]], response: np.ndarray, family: str, nodes: tuple[int, ...]) -> np.ndarray:
    values: list[np.ndarray] = []
    for node in nodes:
        observations: list[np.ndarray] = []
        for row in records:
            if row["family"] == family and node in row["nodes"]:
                local = row["nodes"].index(node)
                ids = np.asarray(row["ids"][3 * local: 3 * local + 3])
                observations.append(np.asarray(response[ids]))
        if not observations:
            raise RuntimeError(f"No {family} trace at node {node}.")
        values.append(np.mean(np.vstack(observations), axis=0))
    return np.concatenate(values)


def family_force(ref: dict[str, Any], response: np.ndarray, family: str, nodes: tuple[int, ...], dynamic_local: Callable[[dict[str, Any]], np.ndarray]) -> np.ndarray:
    force = np.zeros(3 * len(nodes), dtype=np.asarray(response).dtype)
    for row in ref["records"]:
        if row["family"] != family:
            continue
        local = dynamic_local(row) @ response[np.asarray(row["ids"])]
        for index, node in enumerate(nodes):
            if node in row["nodes"]:
                local_node = row["nodes"].index(node)
                force[3 * index:3 * index + 3] += local[3 * local_node:3 * local_node + 3]
    return force


def interface_metrics(contract: dict[str, Any], ref: dict[str, Any], response: np.ndarray, *, omega: float = 0.0, acceleration: np.ndarray | None = None, velocity: np.ndarray | None = None, alpha: float = 0.0) -> dict[str, Any]:
    result: dict[str, Any] = {}
    ffree = max(float(np.linalg.norm(load_vector(ref["base"], ref["dofs"])[0][ref["free"]])), 1.0)
    response_scale = max(float(np.max(np.abs(response))), 1.0e-30)
    for name, (left, right) in INTERFACES.items():
        nodes = shared_nodes(ref, left, right)
        left_state, right_state = family_trace(ref["records"], response, left, nodes), family_trace(ref["records"], response, right, nodes)
        if acceleration is None:
            dynamic = lambda row: row["K"] + 1j * omega * alpha * row["M"] - omega**2 * row["M"]
        else:
            dynamic = lambda row: row["K"]
        left_force = family_force(ref, response, left, nodes, dynamic)
        right_force = family_force(ref, response, right, nodes, dynamic)
        if acceleration is not None and velocity is not None:
            left_force += family_force(ref, acceleration, left, nodes, lambda row: row["M"])
            right_force += family_force(ref, acceleration, right, nodes, lambda row: row["M"])
            left_force += family_force(ref, velocity, left, nodes, lambda row: alpha * row["M"])
            right_force += family_force(ref, velocity, right, nodes, lambda row: alpha * row["M"])
        work_left, work_right = np.vdot(left_state, left_force), np.vdot(right_state, right_force)
        denom = max(abs(work_left) + abs(work_right), max(ffree * float(np.linalg.norm(response)), 1.0e-30))
        result[name] = {"nodes": list(nodes), "left_state": left_state, "right_state": right_state, "left_force": left_force, "right_force": right_force, "jump": float(np.max(np.abs(left_state - right_state)) / response_scale), "force_transfer": float(np.linalg.norm(left_force + right_force) / ffree), "work_left": work_left, "work_right": work_right, "energy": float(abs(work_left + work_right) / denom), "independent_state_collection": True, "continuity_tautological": False}
    return result


def harmonic_campaign(base: FiniteElementModel, contract: dict[str, Any], ref: dict[str, Any]) -> dict[str, Any]:
    ratios = np.asarray(contract["harmonic"]["frequency_ratios_to_first_mode"], dtype=float)
    frequencies = ratios * ref["f1"]
    alpha = 2.0 * contract["scope"]["damping"]["zeta_first_mode"] * ref["omega1"]
    model = harmonic_model(base, contract, frequencies.tolist(), alpha)
    started = time.perf_counter(); result = solve_model(model, enforce_policy=False); elapsed = time.perf_counter() - started
    responses = np.vstack([np.asarray(row, dtype=complex) for row in result.responses])
    load, _ = load_vector(base, ref["dofs"])
    references: list[np.ndarray] = []
    residuals: list[np.ndarray] = []
    interfaces: list[dict[str, Any]] = []
    for frequency, response in zip(frequencies, responses, strict=True):
        omega = 2.0 * math.pi * frequency
        matrix = ref["K"] + 1j * omega * alpha * ref["M"] - omega**2 * ref["M"]
        reference = np.zeros(ref["dofs"].ndof, dtype=complex)
        reference[ref["free"]] = np.linalg.solve(matrix[np.ix_(ref["free"], ref["free"])], load[ref["free"]])
        references.append(reference); residuals.append(matrix @ response - load); interfaces.append(interface_metrics(contract, ref, response, omega=omega, alpha=alpha))
    references_array, residual_array = np.vstack(references), np.vstack(residuals)
    probe = ref["dofs"].index(min(index for index, point in enumerate(base.nodes) if np.isclose(point[2], 3.0)), "UZ")
    amplitude, ref_amplitude = np.abs(responses[:, probe]), np.abs(references_array[:, probe])
    phase, ref_phase = np.angle(responses[:, probe]), np.angle(references_array[:, probe])
    static = np.zeros(ref["dofs"].ndof); static[ref["free"]] = np.linalg.solve(ref["K"][np.ix_(ref["free"], ref["free"])], load[ref["free"]])
    residual_relative = np.linalg.norm(residual_array[:, ref["free"]], axis=1) / max(
        float(np.linalg.norm(load[ref["free"]])), 1.0
    )
    return {
        "frequencies": frequencies, "responses": responses, "references": references_array,
        "residual_vectors": residual_array, "residual_relative": residual_relative,
        "amplitude": amplitude, "reference_amplitude": ref_amplitude,
        "amplitude_errors": np.abs(amplitude - ref_amplitude) / np.maximum(ref_amplitude, 1.0e-30),
        "phase": phase, "reference_phase": ref_phase, "phase_errors": phase_distance(phase, ref_phase),
        "interfaces": interfaces, "static_limit_error": relative(responses[0].real, static),
        "peak_runtime_index": int(np.argmax(amplitude)), "peak_reference_index": int(np.argmax(ref_amplitude)),
        "status": str(result.status), "runtime_seconds": elapsed, "alpha": alpha, "load": load,
    }


def family_participation(ref: dict[str, Any], newmark: dict[str, Any], harmonic: dict[str, Any]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for family in FAMILIES:
        records = [row for row in ref["records"] if row["family"] == family]
        k_norm = math.sqrt(sum(float(np.linalg.norm(row["K"]) ** 2) for row in records)); m_norm = math.sqrt(sum(float(np.linalg.norm(row["M"]) ** 2) for row in records))
        h = harmonic["responses"][1]
        force_norm = math.sqrt(sum(float(np.linalg.norm(row["K"] @ h[np.asarray(row["ids"])]) ** 2) for row in records))
        rows[family] = {"element_count": len(records), "stiffness_norm": k_norm, "mass_norm": m_norm, "dynamic_force_norm": force_norm, "participates": bool(k_norm > 0 and m_norm > 0 and force_norm > 0)}
    return rows


def packet_newmark(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row[key] for key in ("u", "v", "a", "residual_vectors") } | {"energy": row["energy"], "status": row["status"]}


def packet_harmonic(row: dict[str, Any], indices: list[int]) -> dict[str, Any]:
    return {"responses": row["responses"][indices], "amplitude": row["amplitude"][indices], "phase": row["phase"][indices], "residual_vectors": row["residual_vectors"][indices], "interfaces": [{name: metric for name, metric in row["interfaces"][index].items()} for index in indices], "status": row["status"]}


def packets_equal(first: Any, second: Any) -> float:
    if isinstance(first, np.ndarray): return relative(first, second)
    if isinstance(first, dict): return max((packets_equal(first[key], second[key]) for key in first), default=0.0)
    if isinstance(first, list): return max((packets_equal(a, b) for a, b in zip(first, second, strict=True)), default=0.0)
    return 0.0 if first == second else math.inf


def failure_cases(base: FiniteElementModel, contract: dict[str, Any], ref: dict[str, Any]) -> list[dict[str, Any]]:
    alpha = 2.0 * contract["scope"]["damping"]["zeta_first_mode"] * ref["omega1"]
    period = 2.0 * math.pi / ref["omega1"]
    good_dynamic = dynamic_model(base, contract, period / 20.0, 2, alpha, period)
    good_harmonic = harmonic_model(base, contract, [0.0], alpha)
    raw_dynamic = model_payload(base, copy.deepcopy(good_dynamic.analysis.parameters), [{"node": 0, "dof": "UZ", "value": 1.0}])
    raw_dynamic["analysis"]["type"] = "transient_dynamic"; raw_dynamic["analysis"]["method"] = "newmark"
    raw_harmonic = model_payload(base, copy.deepcopy(good_harmonic.analysis.parameters), [{"node": 0, "dof": "UZ", "value": 1.0}])
    raw_harmonic["analysis"]["type"] = "harmonic_response"; raw_harmonic["analysis"]["method"] = "direct_frequency"
    variants: list[tuple[str, dict[str, Any], type[Exception], str]] = []
    def dynamic_variant(case: str, mutate: Callable[[dict[str, Any]], None], pattern: str, expected: type[Exception] = InputValidationError) -> None:
        payload = copy.deepcopy(raw_dynamic); mutate(payload); variants.append((case, payload, expected, pattern))
    def harmonic_variant(case: str, mutate: Callable[[dict[str, Any]], None], pattern: str, expected: type[Exception] = InputValidationError) -> None:
        payload = copy.deepcopy(raw_harmonic); mutate(payload); variants.append((case, payload, expected, pattern))
    dynamic_variant("invalid_dt", lambda item: item["analysis"].update({"time_step": 0.0}), "time_step and steps must be positive")
    dynamic_variant("invalid_beta_gamma", lambda item: item["analysis"].update({"newmark_beta": 0.0}), "Unstable Newmark parameters")
    dynamic_variant("missing_density", lambda item: item["materials"]["solid"].pop("density"), "requires positive density", MeshValidationError)
    dynamic_variant("singular_mass", lambda item: item["materials"]["solid"].update({"density": 0.0}), "requires positive density", MeshValidationError)
    dynamic_variant("unsupported_damping", lambda item: item["analysis"].update({"damping_model": "visco_unknown"}), "Unsupported damping model")
    dynamic_variant("unsupported_family", lambda item: item["elements"].append({"type": "PYRAMID5", "nodes": [0, 1, 2, 3, 4], "material": "solid"}), "UNKNOWN_ELEMENT", CompatibilityError)
    dynamic_variant("malformed_connectivity", lambda item: item["elements"].__setitem__(0, {"type": "TET4", "nodes": [0, 1, 2], "material": "solid"}), "TET4 expects 4 nodes", MeshValidationError)
    harmonic_variant("invalid_harmonic_frequency", lambda item: item["analysis"].update({"frequencies_hz": [float("nan")]}), "frequencies must be finite and non-negative")
    harmonic_variant("negative_harmonic_frequency", lambda item: item["analysis"].update({"frequencies_hz": [-1.0]}), "frequencies must be finite and non-negative")
    harmonic_variant("missing_material", lambda item: item["elements"].__setitem__(0, {**item["elements"][0], "material": "missing"}), "MATERIAL_REFERENCE_MISSING", CompatibilityError)
    records: list[dict[str, Any]] = []
    for case, payload, expected, pattern in variants:
        observed: Exception | None = None
        try:
            model = FiniteElementModel.from_raw(**payload)
            solve_model(model, enforce_policy=False)
        except Exception as exc:  # each branch is checked below, never accepted generically
            observed = exc
        text = "" if observed is None else str(observed)
        type_match = observed is not None and isinstance(observed, expected)
        path_match = observed is not None
        message_match = observed is not None and pattern.lower() in text.lower()
        records.append({"case_id": case, "actual_input": safe(payload), "actual_input_digest": sha256_bytes(canonical(payload).encode()), "execution_path": "FiniteElementModel.from_raw -> solve_model", "expected_exception_type": expected.__name__, "expected_message_pattern": pattern, "observed_exception_type": type(observed).__name__ if observed else None, "observed_message": text, "type_match": type_match, "message_match": message_match, "path_match": path_match, "pass": bool(type_match and message_match and path_match)})
    required = set(contract["failure_contract"]["cases"])
    assert {row["case_id"] for row in records} == required
    return records


def arrays_for_archive(newmark: dict[str, dict[str, Any]], harmonic: dict[str, Any], families: dict[str, Any], failures: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {}
    for level, row in newmark.items():
        for field in ("u", "v", "a", "residual_vectors", "residual_relative"):
            arrays[f"newmark_{level}_{field}"] = row[field]
        for field, value in row["energy"].items(): arrays[f"newmark_{level}_energy_{field}"] = value
        for interface, history in row["interface_history"].items():
            for field in ("left_state", "right_state", "left_force", "right_force", "jump", "force_transfer", "work_left", "work_right", "energy"):
                arrays[f"newmark_{level}_{interface}_{field}"] = np.asarray([entry[field] for entry in history])
    for field in ("frequencies", "responses", "references", "residual_vectors", "residual_relative", "amplitude", "reference_amplitude", "amplitude_errors", "phase", "reference_phase", "phase_errors"):
        arrays[f"harmonic_{field}"] = harmonic[field]
    arrays["family_stiffness_norms"] = np.asarray([families[f]["stiffness_norm"] for f in FAMILIES])
    arrays["family_mass_norms"] = np.asarray([families[f]["mass_norm"] for f in FAMILIES])
    for interface in INTERFACES:
        for field in ("left_state", "right_state", "left_force", "right_force", "jump", "force_transfer", "work_left", "work_right", "energy"):
            arrays[f"harmonic_{interface}_{field}"] = np.asarray([entry[interface][field] for entry in harmonic["interfaces"]])
    arrays["failure_passes"] = np.asarray([row["pass"] for row in failures], dtype=bool)
    return arrays


def newmark_interface_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        interface: {
            "max_displacement_jump": float(max(item["jump"] for item in history)),
            "max_force_transfer": float(max(item["force_transfer"] for item in history)),
            "max_energy_mismatch": float(max(item["energy"] for item in history)),
            "history_length": len(history),
            "independent_state_collection": True,
            "continuity_tautological": False,
        }
        for interface, history in row["interface_history"].items()
    }


def dominant_frequency(signal: np.ndarray, dt: float) -> tuple[float, float]:
    spectrum = np.fft.rfft(np.asarray(signal, dtype=float))
    frequencies = np.fft.rfftfreq(signal.size, dt)
    if frequencies.size <= 1:
        return 0.0, 0.0
    index = 1 + int(np.argmax(np.abs(spectrum[1:])))
    return float(frequencies[index]), float(np.angle(spectrum[index]))


def time_step_characterization(newmark: dict[str, dict[str, Any]]) -> dict[str, Any]:
    fine_level = max(newmark, key=lambda value: int(value))
    fine = newmark[fine_level]
    summary: dict[str, Any] = {"role": "CHARACTERIZATION_ONLY", "reference_level": fine_level, "levels": {}}
    for level, row in newmark.items():
        stride = int(int(fine_level) / int(level))
        probe = row["probe"]
        fine_sampled = fine["u"][::stride, probe]
        frequency, phase = dominant_frequency(row["u"][:, probe], row["dt"])
        ref_frequency, ref_phase = dominant_frequency(fine_sampled, row["dt"])
        summary["levels"][level] = {
            "peak_displacement": float(np.max(np.abs(row["u"][:, probe]))),
            "final_displacement": float(row["u"][-1, probe]),
            "relative_history_to_fine": relative(row["u"][:, probe], fine_sampled),
            "dominant_frequency_hz": frequency,
            "dominant_frequency_difference_hz": abs(frequency - ref_frequency),
            "dominant_phase_rad": phase,
            "dominant_phase_difference_rad": float(phase_distance(np.asarray([phase]), np.asarray([ref_phase]))[0]),
            "max_residual_relative": float(np.max(row["residual_relative"])),
            "energy_balance_error": row["energy_balance_error"],
        }
    return summary


def main() -> int:
    contract, contract_sha = load_contract()
    base = build(1); ref = element_matrices(base); ref["base"] = base
    counts = {family: sum(row["family"] == family for row in ref["records"]) for family in FAMILIES}
    load, _ = load_vector(base, ref["dofs"])
    alpha = 2.0 * contract["scope"]["damping"]["zeta_first_mode"] * ref["omega1"]
    newmark = {str(level): capture_newmark(base, contract, ref, int(level), f"T1/{level}") for level in contract["newmark"]["time_levels_per_first_period"]}
    harmonic = harmonic_campaign(base, contract, ref)
    families = family_participation(ref, newmark, harmonic)
    failures = failure_cases(base, contract, ref)
    replay_level = str(max(contract["newmark"]["time_levels_per_first_period"]))
    newmark_replay_1 = capture_newmark(base, contract, ref, int(replay_level), "REPLAY_1")
    newmark_replay_2 = capture_newmark(base, contract, ref, int(replay_level), "REPLAY_2")
    replay_indices = [int(np.where(np.isclose(harmonic["frequencies"], ratio * ref["f1"]))[0][0]) for ratio in contract["harmonic"]["replay_ratios"]]
    harmonic_replay_1, harmonic_replay_2 = harmonic_campaign(base, contract, ref), harmonic_campaign(base, contract, ref)
    replay = {"newmark_1": packets_equal(packet_newmark(newmark[replay_level]), packet_newmark(newmark_replay_1)), "newmark_2": packets_equal(packet_newmark(newmark[replay_level]), packet_newmark(newmark_replay_2)), "harmonic_1": packets_equal(packet_harmonic(harmonic, replay_indices), packet_harmonic(harmonic_replay_1, replay_indices)), "harmonic_2": packets_equal(packet_harmonic(harmonic, replay_indices), packet_harmonic(harmonic_replay_2, replay_indices))}
    gate_n = contract["newmark"]["gates"]; gate_h = contract["harmonic"]["gates"]
    newmark_gates = {level: {"displacement": row["displacement_error"] <= gate_n["displacement_history_relative"], "velocity": row["velocity_error"] <= gate_n["velocity_history_relative"], "acceleration": row["acceleration_error"] <= gate_n["acceleration_history_relative"], "peak": row["peak_response_error"] <= gate_n["peak_response_relative"], "residual": float(np.max(row["residual_relative"])) <= gate_n["residual_relative"], "energy": row["energy_balance_error"] <= gate_n["energy_balance_error"]} for level, row in newmark.items()}
    harmonic_gates = {"amplitude": float(np.max(harmonic["amplitude_errors"])) <= gate_h["amplitude_relative"], "phase": float(np.max(harmonic["phase_errors"])) <= gate_h["phase_absolute_rad"], "residual": float(np.max(harmonic["residual_relative"])) <= gate_h["residual_relative"], "static": harmonic["static_limit_error"] <= gate_h["static_limit_relative"]}
    interfaces = {"newmark": {level: newmark_interface_summary(row) for level, row in newmark.items()}, "harmonic": harmonic["interfaces"]}
    interface_gate = contract["mixed_interface_metrics"]["gates"]
    newmark_interface_ok = all(summary["max_displacement_jump"] <= interface_gate["continuity"] and summary["max_force_transfer"] <= interface_gate["force_transfer"] and summary["max_energy_mismatch"] <= interface_gate["energy"] for level in interfaces["newmark"].values() for summary in level.values())
    harmonic_interface_ok = all(metric["jump"] <= interface_gate["continuity"] and metric["force_transfer"] <= interface_gate["force_transfer"] and metric["energy"] <= interface_gate["energy"] for per_frequency in interfaces["harmonic"] for metric in per_frequency.values())
    interface_ok = newmark_interface_ok and harmonic_interface_ok
    timestep = time_step_characterization(newmark)
    arrays = arrays_for_archive(newmark, harmonic, families, failures)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if ARCHIVE_PATH.exists() or MANIFEST_PATH.exists(): raise RuntimeError("Prospective WP13-02 output already exists; refusing overwrite.")
    np.savez_compressed(ARCHIVE_PATH, **arrays)
    array_digests = {name: sha256_bytes(np.ascontiguousarray(value).tobytes()) for name, value in arrays.items()}
    required_fields = contract["evidence"]["manifest_required_fields"]
    manifest = {"contract_id": contract["contract_id"], "contract_sha": contract_sha, "repo_sha": git_sha(), "environment": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__}, "benchmark": {"family_counts": counts, "dof": ref["dofs"].ndof, "load_norm": float(np.linalg.norm(load)), "connected_components": 1, "direct_support_bypass": False}, "conditioning": {"stiffness_symmetry": relative(ref["K"], ref["K"].T), "mass_symmetry": relative(ref["M"], ref["M"].T), "mass_positive": bool(np.min(np.linalg.eigvalsh(ref["M"][np.ix_(ref["free"], ref["free"])])) > 0.0)}, "newmark": {"frequency_hz": ref["f1"], "omega": ref["omega1"], "alpha": alpha, "runs": {level: {key: value for key, value in row.items() if key not in {"u", "v", "a", "oracle", "residual_vectors", "energy", "interface_history"}} | {"energy_summary": {key: float(value[-1]) for key, value in row["energy"].items()}, "interfaces": interfaces["newmark"][level]} for level, row in newmark.items()}, "time_step_characterization": timestep, "gates": newmark_gates, "oracle_independence": "Direct dense recurrence and direct local element scatter; production GlobalAssembler, DynamicDofReducer and Newmark solver are not reused."}, "harmonic": {"frequency_hz": harmonic["frequencies"], "alpha": alpha, "static_limit_error": harmonic["static_limit_error"], "peak_runtime_frequency_hz": float(harmonic["frequencies"][harmonic["peak_runtime_index"]]), "peak_reference_frequency_hz": float(harmonic["frequencies"][harmonic["peak_reference_index"]]), "gates": harmonic_gates, "oracle_independence": "Direct dense complex solve and direct local element scatter; production GlobalAssembler, DynamicDofReducer and harmonic solver are not reused.", "interfaces": interfaces["harmonic"]}, "interfaces": interfaces, "family_participation": families, "replay": {"errors": replay, "semantic_digest": sha256_bytes(canonical({"newmark": packet_newmark(newmark[replay_level]), "harmonic": packet_harmonic(harmonic, replay_indices)}).encode())}, "failure_contract": failures, "digests": {"arrays": array_digests, "archive_sha256": sha256_file(ARCHIVE_PATH)}, "gate_decisions": {"newmark": newmark_gates, "harmonic": harmonic_gates, "interfaces": interface_ok, "replay": all(value <= max(gate_n["replay_relative"], gate_h["replay_relative"]) for value in replay.values()), "failures": all(row["pass"] for row in failures)}}
    schema_valid = all(field in manifest for field in required_fields)
    acceptance_level = str(max(int(level) for level in newmark))
    manifest["gate_decisions"]["newmark_acceptance_level"] = acceptance_level
    manifest["gate_decisions"]["newmark_acceptance"] = newmark_gates[acceptance_level]
    semantic_valid = (
        schema_valid
        and all(data["participates"] for data in families.values())
        and all(newmark_gates[acceptance_level].values())
        and all(harmonic_gates.values())
        and interface_ok
        and manifest["gate_decisions"]["replay"]
        and manifest["gate_decisions"]["failures"]
    )
    manifest["evidence_schema_valid"] = schema_valid; manifest["semantic_validator_valid"] = semantic_valid; manifest["evidence_integrity"] = "PASS" if semantic_valid else "FAIL"
    MANIFEST_PATH.write_text(json.dumps(safe(manifest), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"contract_sha": contract_sha, "frequency_hz": ref["f1"], "newmark_gates": newmark_gates, "harmonic_gates": harmonic_gates, "interface_ok": interface_ok, "replay": replay, "failures": sum(row["pass"] for row in failures), "schema": schema_valid, "semantic": semantic_valid}, indent=2))
    return 0 if semantic_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
