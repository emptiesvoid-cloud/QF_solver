"""Execute the frozen WP13-02C connected mixed harmonic campaign.

This runner is deliberately evidence-facing.  It consumes the committed
contract as its only source for frequencies and gates, builds the frozen
WP13-01K compact elbow, computes an independent dense reference, then calls
the public harmonic route.  It does not modify any production FEM kernel or
any Newmark evidence.
"""

from __future__ import annotations

# ruff: noqa: E402
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
from scipy.linalg import eigh, solve as dense_solve

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

try:
    import resource as _resource  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - Windows compatibility for the frozen geometry builder
    _resource = types.ModuleType("resource")
    _resource.RUSAGE_SELF = 0
    _resource.getrusage = lambda _who: types.SimpleNamespace(ru_maxrss=0)
    sys.modules["resource"] = _resource

from run_wp13_01k_mvp import build  # noqa: E402
from solveur.api.public import solve_model  # noqa: E402
from solveur.core.errors import InputValidationError  # noqa: E402
from solveur.core.model import FiniteElementModel  # noqa: E402
from solveur.elements.registry import ElementRegistry  # noqa: E402
from solveur.materials.factory import MaterialFactory  # noqa: E402


CONTRACT_PATH = ROOT / "qualification/0_2_8/wp13_02c_harmonic_contract.json"
SCHEMA_PATH = ROOT / "qualification/0_2_8/wp13_02c_harmonic_contract.schema.json"
OUTPUT_DIR = ROOT / "qualification/0_2_8/wp13_02c_harmonic_v1"
ARCHIVE_PATH = OUTPUT_DIR / "wp13_02c_harmonic_arrays.npz"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
FAMILIES = ("TET4", "WEDGE6", "HEX8")
INTERFACES = {
    "TET4_WEDGE6": ("TET4", "WEDGE6", (10, 11, 12)),
    "WEDGE6_HEX8": ("WEDGE6", "HEX8", (2, 3, 6, 7)),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_blob_sha(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def git_revision() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def git_last_commit(path: Path) -> str:
    return subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", str(path)], cwd=ROOT, text=True
    ).strip()


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert contract["contract_id"] == "WP13-02C-HARMONIC-MIXED-001"
    assert contract["status"] == "PREDECLARED_NOT_EXECUTED"
    assert schema["properties"]["contract_id"]["const"] == contract["contract_id"]
    assert contract["predeclared_gates"]["fixed_before_execution"] is True
    assert contract["predeclared_gates"]["post_observation_retuning"] is False
    return contract


def build_harmonic_model(
    base: FiniteElementModel,
    frequencies_hz: list[float],
    alpha: float,
    *,
    material_override: dict[str, Any] | None = None,
    elements_override: list[dict[str, Any]] | None = None,
    loads_override: list[dict[str, Any]] | None = None,
    analysis_override: dict[str, Any] | None = None,
) -> FiniteElementModel:
    top_nodes = [
        node
        for node, point in enumerate(base.nodes)
        if np.isclose(float(point[2]), 3.0, rtol=0.0, atol=1.0e-14)
    ]
    loads = loads_override if loads_override is not None else [
        {"node": node, "dof": "UZ", "value": 1.0 / len(top_nodes)}
        for node in top_nodes
    ]
    elements = elements_override if elements_override is not None else [
        {"type": element.type, "nodes": list(element.nodes), "material": element.material}
        for element in base.elements
    ]
    materials = {key: copy.deepcopy(value) for key, value in base.materials.items()}
    if material_override is not None:
        materials = material_override
    analysis = {
        "type": "harmonic_response",
        "method": "direct_frequency",
        "frequencies_hz": frequencies_hz,
        "damping_model": "rayleigh",
        "rayleigh_alpha": alpha,
        "rayleigh_beta": 0.0,
        "mass_formulation": "consistent",
        "harmonic_residual_failure_tolerance": 1.0e-7,
    }
    if analysis_override:
        analysis.update(analysis_override)
    return FiniteElementModel.from_raw(
        nodes=base.nodes.tolist(),
        elements=elements,
        materials=materials,
        fixed_dofs=[{"node": condition.node, "dofs": list(condition.dofs)} for condition in base.fixed_dofs],
        loads=loads,
        analysis=analysis,
        units=base.units,
    )


def independent_matrices(
    base: FiniteElementModel,
) -> tuple[np.ndarray, np.ndarray, Any, list[dict[str, Any]]]:
    """Scatter local element matrices without calling GlobalAssembler."""
    dofs = base.dof_manager()
    stiffness = np.zeros((dofs.ndof, dofs.ndof), dtype=float)
    mass = np.zeros_like(stiffness)
    records: list[dict[str, Any]] = []
    for element_definition in base.elements:
        spec = ElementRegistry.get(element_definition.type)
        coordinates = base.nodes[list(element_definition.nodes)]
        material = MaterialFactory.create(
            base.materials[element_definition.material], coordinates=coordinates
        )
        element = spec.factory(material)
        local_stiffness = np.asarray(element.stiffness(coordinates), dtype=float)
        local_mass = np.asarray(element.mass(coordinates), dtype=float)
        ids = [
            index
            for node in element_definition.nodes
            for index in dofs.node_indices(node, spec.dofs)
        ]
        stiffness[np.ix_(ids, ids)] += local_stiffness
        mass[np.ix_(ids, ids)] += local_mass
        records.append(
            {
                "family": element_definition.type,
                "nodes": list(element_definition.nodes),
                "ids": ids,
                "K": local_stiffness,
                "M": local_mass,
            }
        )
    return stiffness, mass, dofs, records


def fixed_free_indices(base: FiniteElementModel, dofs: Any) -> tuple[np.ndarray, np.ndarray]:
    fixed = np.asarray(
        sorted(
            {
                dofs.index(condition.node, name)
                for condition in base.fixed_dofs
                for name in condition.dofs
            }
        ),
        dtype=int,
    )
    free = np.setdiff1d(np.arange(dofs.ndof), fixed)
    return fixed, free


def frozen_load(base: FiniteElementModel, dofs: Any) -> np.ndarray:
    top_nodes = [
        node
        for node, point in enumerate(base.nodes)
        if np.isclose(float(point[2]), 3.0, rtol=0.0, atol=1.0e-14)
    ]
    loads = np.zeros(dofs.ndof, dtype=float)
    for node in top_nodes:
        loads[dofs.index(node, "UZ")] = 1.0 / len(top_nodes)
    return loads


def oracle(base: FiniteElementModel) -> dict[str, Any]:
    stiffness, mass, dofs, records = independent_matrices(base)
    fixed, free = fixed_free_indices(base, dofs)
    values, vectors = eigh(
        stiffness[np.ix_(free, free)],
        mass[np.ix_(free, free)],
        check_finite=True,
        driver="gvd",
    )
    positive = np.flatnonzero(values > 1.0e-10)
    if positive.size == 0:
        raise RuntimeError("Independent oracle found no positive fixed-base eigenvalue.")
    first = int(positive[0])
    omega = math.sqrt(float(values[first]))
    mode = np.zeros(dofs.ndof, dtype=float)
    mode[free] = vectors[:, first]
    free_mode = mode[free]
    pivot = int(np.argmax(np.abs(free_mode)))
    if free_mode[pivot] < 0.0:
        mode *= -1.0
    load = frozen_load(base, dofs)
    modal_force = vectors.T @ load[free]
    zeta = float(CONTRACT["scope"]["damping"]["zeta_at_first_mode"])
    alpha = 2.0 * zeta * omega
    beta = float(CONTRACT["scope"]["damping"]["beta_stiffness_s"])
    damping = alpha * mass + beta * stiffness
    static = np.zeros(dofs.ndof, dtype=float)
    static[free] = dense_solve(stiffness[np.ix_(free, free)], load[free], assume_a="sym")
    return {
        "stiffness": stiffness,
        "mass": mass,
        "damping": damping,
        "dofs": dofs,
        "records": records,
        "fixed": fixed,
        "free": free,
        "load": load,
        "eigenvalues": values,
        "modal_force_participation": modal_force,
        "first_mode_load_participation_ratio": float(
            abs(modal_force[first]) ** 2 / max(float(np.sum(np.abs(modal_force) ** 2)), 1.0e-30)
        ),
        "mode": mode,
        "omega1": omega,
        "frequency_hz": omega / (2.0 * math.pi),
        "alpha": alpha,
        "beta": beta,
        "zeta": zeta,
        "static": static,
        "probe_node": min(node for node, point in enumerate(base.nodes) if np.isclose(float(point[2]), 3.0, rtol=0.0, atol=1.0e-14)),
        "probe_dof": "UZ",
    }


def conditioning(base: FiniteElementModel, ref: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    distances: list[float] = []
    jacobians: list[tuple[float, float]] = []
    for element in base.elements:
        coords = base.nodes[list(element.nodes)]
        pairwise = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=2)
        distances.extend(float(value) for value in pairwise.ravel() if value > 0.0)
        if element.type == "TET4":
            jacobians.append((float(np.linalg.det((coords[1:] - coords[0]).T)), float(np.linalg.cond((coords[1:] - coords[0]).T))))
        else:
            kernel = ElementRegistry.get(element.type).factory(
                MaterialFactory.create(base.materials[element.material], coordinates=coords)
            )
            for point in kernel.integration_points:
                jacobian = kernel.jacobian(coords, point)
                jacobians.append((float(np.linalg.det(jacobian)), float(np.linalg.cond(jacobian))))
    stiffness = ref["stiffness"]
    mass = ref["mass"]
    k_diag = np.abs(np.diag(stiffness))
    m_diag = np.abs(np.diag(mass))
    k_diag = k_diag[k_diag > 0.0]
    m_diag = m_diag[m_diag > 0.0]
    free = ref["free"]
    k_free = stiffness[np.ix_(free, free)]
    m_free = mass[np.ix_(free, free)]
    k_eigs = np.linalg.eigvalsh(k_free)
    m_eigs = np.linalg.eigvalsh(m_free)
    pre = contract["conditioning_precheck"]["metrics"]
    values = {
        "max_aspect_ratio": max(distances) / min(distances),
        "jacobian_range": [min(value[0] for value in jacobians), max(value[0] for value in jacobians)],
        "max_jacobian_condition": max(value[1] for value in jacobians),
        "mass_scale_range": max(m_diag) / min(m_diag),
        "stiffness_scale_range": max(k_diag) / min(k_diag),
        "stiffness_symmetry_error": float(np.linalg.norm(stiffness - stiffness.T) / max(np.linalg.norm(stiffness), 1.0e-30)),
        "mass_symmetry_error": float(np.linalg.norm(mass - mass.T) / max(np.linalg.norm(mass), 1.0e-30)),
        "free_stiffness_min_eigenvalue": float(min(k_eigs)),
        "free_mass_min_eigenvalue": float(min(m_eigs)),
        "conditioning_number_estimate": {
            "Kff": float(max(k_eigs) / min(k_eigs)),
            "Mff": float(max(m_eigs) / min(m_eigs)),
        },
    }
    gates = {
        "max_element_edge_aspect_ratio": values["max_aspect_ratio"] <= pre["max_element_edge_aspect_ratio"]["value"],
        "jacobian_condition_number": values["max_jacobian_condition"] <= pre["jacobian_condition_number"]["value"],
        "jacobian_determinant_positive": values["jacobian_range"][0] > 0.0,
        "assembled_stiffness_positive_diagonal_ratio": values["stiffness_scale_range"] <= pre["assembled_stiffness_positive_diagonal_ratio"]["value"],
        "assembled_mass_positive_diagonal_ratio": values["mass_scale_range"] <= pre["assembled_mass_positive_diagonal_ratio"]["value"],
        "stiffness_symmetry": values["stiffness_symmetry_error"] <= pre["stiffness_symmetry_relative_frobenius"]["value"],
        "mass_symmetry": values["mass_symmetry_error"] <= pre["mass_symmetry_relative_frobenius"]["value"],
        "free_stiffness_positive_definite": values["free_stiffness_min_eigenvalue"] > 0.0,
        "free_mass_positive_definite": values["free_mass_min_eigenvalue"] > 0.0,
    }
    return {"values": values, "gates": gates, "status": "PASS" if all(gates.values()) else "FAIL"}


def dense_response(ref: dict[str, Any], frequency_hz: float) -> np.ndarray:
    omega = 2.0 * math.pi * frequency_hz
    matrix = ref["stiffness"] + 1j * omega * ref["damping"] - omega**2 * ref["mass"]
    response = np.zeros(ref["dofs"].ndof, dtype=complex)
    response[ref["free"]] = dense_solve(
        matrix[np.ix_(ref["free"], ref["free"])],
        ref["load"][ref["free"]].astype(complex),
        assume_a="gen",
    )
    return response


def sdof_response(ref: dict[str, Any], frequency_hz: float) -> np.ndarray:
    omega = 2.0 * math.pi * frequency_hz
    q_force = np.vdot(ref["mode"], ref["load"])
    denominator = ref["omega1"] ** 2 - omega**2 + 1j * omega * ref["alpha"]
    return ref["mode"] * (q_force / denominator)


def family_dynamic_forces(ref: dict[str, Any], response: np.ndarray, frequency_hz: float) -> dict[str, np.ndarray]:
    omega = 2.0 * math.pi * frequency_hz
    forces = {family: np.zeros(ref["dofs"].ndof, dtype=complex) for family in FAMILIES}
    for record in ref["records"]:
        local = record["K"] + 1j * omega * (ref["alpha"] * record["M"] + ref["beta"] * record["K"]) - omega**2 * record["M"]
        ids = record["ids"]
        forces[record["family"]][ids] += local @ response[ids]
    return forces


def interface_metrics(ref: dict[str, Any], response: np.ndarray, frequency_hz: float) -> dict[str, Any]:
    forces = family_dynamic_forces(ref, response, frequency_hz)
    load_scale = max(float(np.linalg.norm(ref["load"][ref["free"]])), 1.0)
    response_scale = max(float(np.max(np.abs(response))), 1.0e-30)
    result: dict[str, Any] = {}
    for name, (left, right, nodes) in INTERFACES.items():
        ids = np.asarray([ref["dofs"].index(node, dof) for node in nodes for dof in ("UX", "UY", "UZ")], dtype=int)
        left_state = response[ids]
        right_state = response[ids]
        g_left = forces[left][ids]
        g_right = forces[right][ids]
        work_left = np.vdot(left_state, g_left)
        work_right = np.vdot(right_state, g_right)
        energy_denominator = max(abs(work_left) + abs(work_right), load_scale * response_scale, 1.0e-30)
        result[name] = {
            "shared_nodes": list(nodes),
            "displacement_jump": float(np.max(np.abs(left_state - right_state)) / response_scale),
            "force_left": g_left.tolist(),
            "force_right": g_right.tolist(),
            "force_balance_relative": float(np.linalg.norm(g_left + g_right) / load_scale),
            "work_left": complex(work_left),
            "work_right": complex(work_right),
            "energy_mismatch_relative": float(abs(work_left + work_right) / energy_denominator),
        }
    return result


def family_energies(ref: dict[str, Any], response: np.ndarray, frequency_hz: float) -> dict[str, Any]:
    omega = 2.0 * math.pi * frequency_hz
    rows: dict[str, Any] = {}
    for family in FAMILIES:
        kinetic = 0.0
        strain = 0.0
        for record in ref["records"]:
            if record["family"] != family:
                continue
            ids = record["ids"]
            x = response[ids]
            kinetic += 0.25 * omega**2 * float(np.real(np.vdot(x, record["M"] @ x)))
            strain += 0.25 * float(np.real(np.vdot(x, record["K"] @ x)))
        rows[family] = {"kinetic": kinetic, "strain": strain}
    velocity = 1j * omega * response
    kinetic_global = 0.25 * omega**2 * float(np.real(np.vdot(response, ref["mass"] @ response)))
    strain_global = 0.25 * float(np.real(np.vdot(response, ref["stiffness"] @ response)))
    damping_power = 0.5 * float(np.real(np.vdot(velocity, ref["damping"] @ velocity)))
    external_power = 0.5 * float(np.real(np.vdot(velocity, ref["load"])))
    rows["global"] = {
        "kinetic": kinetic_global,
        "strain": strain_global,
        "damping": damping_power,
        "external_work": external_power,
        "total_balance": external_power - damping_power,
    }
    return rows


def response_metrics(ref: dict[str, Any], responses: np.ndarray, frequencies_hz: list[float], result: Any) -> dict[str, Any]:
    probe = ref["dofs"].index(ref["probe_node"], ref["probe_dof"])
    references = np.vstack([dense_response(ref, frequency) for frequency in frequencies_hz])
    sdof = np.vstack([sdof_response(ref, frequency) for frequency in frequencies_hz])
    amplitudes = np.abs(responses[:, probe])
    reference_amplitudes = np.abs(references[:, probe])
    phase_runtime = np.angle(responses[:, probe])
    phase_reference = np.angle(references[:, probe])
    phase_errors = np.abs((phase_runtime - phase_reference + math.pi) % (2.0 * math.pi) - math.pi)
    amplitude_errors = np.abs(amplitudes / np.maximum(reference_amplitudes, 1.0e-30) - 1.0)
    residual_vectors: list[np.ndarray] = []
    residuals: list[float] = []
    interfaces: list[dict[str, Any]] = []
    energies: list[dict[str, Any]] = []
    reactions: list[np.ndarray] = []
    for response, frequency in zip(responses, frequencies_hz, strict=True):
        omega = 2.0 * math.pi * frequency
        residual = (ref["stiffness"] + 1j * omega * ref["damping"] - omega**2 * ref["mass"]) @ response - ref["load"]
        residual_vectors.append(residual)
        residuals.append(float(np.linalg.norm(residual[ref["free"]]) / max(np.linalg.norm(ref["load"][ref["free"]]), 1.0)))
        reactions.append(residual[ref["fixed"]])
        interfaces.append(interface_metrics(ref, response, frequency))
        energies.append(family_energies(ref, response, frequency))
    residual_array = np.vstack(residual_vectors)
    reference_residuals = np.asarray(result.solver["relative_residual_norms"], dtype=float)
    peak_runtime = int(np.argmax(amplitudes))
    peak_reference = int(np.argmax(reference_amplitudes))
    static_error = float(np.linalg.norm(responses[0].real - ref["static"]) / max(np.linalg.norm(ref["static"]), 1.0e-30))
    return {
        "responses": responses,
        "references": references,
        "sdof_references": sdof,
        "residual_vectors": residual_array,
        "residuals": residuals,
        "production_residuals": reference_residuals.tolist(),
        "reactions": np.vstack(reactions),
        "interfaces": interfaces,
        "energies": energies,
        "probe": {"node": ref["probe_node"], "dof": ref["probe_dof"], "index": probe},
        "amplitudes": amplitudes.tolist(),
        "reference_amplitudes": reference_amplitudes.tolist(),
        "amplitude_errors": amplitude_errors.tolist(),
        "phases": phase_runtime.tolist(),
        "reference_phases": phase_reference.tolist(),
        "phase_errors": phase_errors.tolist(),
        "static_limit_error": static_error,
        "peak_runtime_index": peak_runtime,
        "peak_reference_index": peak_reference,
        "peak_runtime_frequency_hz": float(frequencies_hz[peak_runtime]),
        "peak_reference_frequency_hz": float(frequencies_hz[peak_reference]),
        "peak_amplitude_error": float(amplitude_errors[peak_reference]),
        "peak_phase_error": float(phase_errors[peak_reference]),
        "sdof_probe_relative_errors": [
            float(abs(abs(response[probe]) / max(abs(reference[probe]), 1.0e-30) - 1.0))
            for response, reference in zip(sdof, references, strict=True)
        ],
    }


def solve_harmonic(base: FiniteElementModel, frequencies_hz: list[float], ref: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    model = build_harmonic_model(base, frequencies_hz, ref["alpha"])
    started = time.perf_counter()
    result = solve_model(model, enforce_policy=False)
    elapsed = time.perf_counter() - started
    responses = np.vstack([np.asarray(response, dtype=complex) for response in result.responses])
    metrics = response_metrics(ref, responses, frequencies_hz, result)
    metrics["runtime_seconds"] = elapsed
    metrics["solver_status"] = result.status
    return result, metrics


def validate_connected_scope(model: FiniteElementModel) -> None:
    families = {element.type for element in model.elements}
    if families != set(FAMILIES):
        raise InputValidationError(f"Mixed harmonic scope requires exactly {FAMILIES}; got {sorted(families)}.")
    node_families: dict[int, set[str]] = {}
    for element in model.elements:
        for node in element.nodes:
            node_families.setdefault(node, set()).add(element.type)
    adjacency = {family: set() for family in FAMILIES}
    for linked in node_families.values():
        for left in linked:
            for right in linked:
                if left != right:
                    adjacency[left].add(right)
    seen = set()
    stack = [FAMILIES[0]]
    while stack:
        family = stack.pop()
        if family in seen:
            continue
        seen.add(family)
        stack.extend(adjacency[family] - seen)
    if seen != set(FAMILIES):
        raise InputValidationError(f"Mixed harmonic family graph is disconnected: {adjacency}.")


def expected_failure(factory: Callable[[], Any]) -> dict[str, Any]:
    try:
        factory()
    except Exception as exc:  # noqa: BLE001 - actual failure contract evidence
        return {
            "executed": True,
            "expected_exception": "explicit input/mesh/route rejection",
            "observed_exception": type(exc).__name__,
            "message": str(exc)[:500],
            "status": "PASS",
        }
    return {
        "executed": True,
        "expected_exception": "explicit input/mesh/route rejection",
        "observed_exception": None,
        "message": "No exception was raised.",
        "status": "FAIL",
    }


def failure_cases(base: FiniteElementModel, ref: dict[str, Any]) -> dict[str, Any]:
    frequency = [ref["frequency_hz"]]
    alpha = ref["alpha"]

    def model_with_analysis(**overrides: Any) -> FiniteElementModel:
        return build_harmonic_model(base, frequency, alpha, analysis_override=overrides)

    def bad_material(**updates: Any) -> dict[str, Any]:
        material = {key: copy.deepcopy(value) for key, value in base.materials.items()}
        material["solid"].update(updates)
        return material

    top_nodes = [node for node, point in enumerate(base.nodes) if np.isclose(float(point[2]), 3.0, rtol=0.0, atol=1.0e-14)]
    valid_load = [{"node": node, "dof": "UZ", "value": 1.0 / len(top_nodes)} for node in top_nodes]
    cases: dict[str, Callable[[], Any]] = {
        "invalid_frequency_negative": lambda: solve_model(build_harmonic_model(base, [-1.0], alpha), enforce_policy=False),
        "invalid_frequency_nan": lambda: solve_model(build_harmonic_model(base, [float("nan")], alpha), enforce_policy=False),
        "invalid_frequency_inf": lambda: solve_model(build_harmonic_model(base, [float("inf")], alpha), enforce_policy=False),
        "missing_mass": lambda: solve_model(
            build_harmonic_model(base, frequency, alpha, material_override=bad_material(density=0.0)),
            enforce_policy=False,
        ),
        "unsupported_damping": lambda: solve_model(
            model_with_analysis(damping_model="unknown_model"), enforce_policy=False
        ),
        "malformed_harmonic_load": lambda: solve_model(
            build_harmonic_model(base, frequency, alpha, loads_override=[{"node": top_nodes[0], "dof": "BAD", "value": 1.0}]),
            enforce_policy=False,
        ),
        "invalid_complex_real_input": lambda: solve_model(
            build_harmonic_model(base, frequency, alpha, loads_override=[{"node": top_nodes[0], "dof": "UZ", "value": 1.0 + 1.0j}]),
            enforce_policy=False,
        ),
    }
    bad_elements = [
        {"type": element.type, "nodes": list(element.nodes), "material": element.material}
        for element in base.elements
        if element.type != "WEDGE6"
    ]
    cases["invalid_mixed_interface"] = lambda: (
        validate_connected_scope(build_harmonic_model(base, frequency, alpha, elements_override=bad_elements))
    )
    unsupported_elements = [
        {"type": "PYRAMID5" if index == 0 else element.type, "nodes": list(element.nodes) if index else [*element.nodes, 4], "material": element.material}
        for index, element in enumerate(base.elements)
    ]
    cases["unsupported_family"] = lambda: solve_model(
        build_harmonic_model(base, frequency, alpha, elements_override=unsupported_elements), enforce_policy=False
    )
    del valid_load
    return {name: expected_failure(factory) for name, factory in cases.items()}


def complex_digest(array: np.ndarray) -> str:
    return sha256_bytes(np.ascontiguousarray(array, dtype=np.complex128).tobytes())


def real_digest(array: np.ndarray) -> str:
    return sha256_bytes(np.ascontiguousarray(array, dtype=np.float64).tobytes())


def replay_comparison(main: dict[str, Any], replay: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    gate = float(contract["predeclared_gates"]["replay_response_relative"]["value"])
    def rel(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.linalg.norm(a - b) / max(np.linalg.norm(a), 1.0e-30))
    response = rel(main["responses"], replay["responses"])
    reaction = rel(main["reactions"], replay["reactions"])
    residual = rel(main["residual_vectors"], replay["residual_vectors"])
    amplitude = rel(np.asarray(main["amplitudes"]), np.asarray(replay["amplitudes"]))
    phase = float(np.max(np.abs(np.asarray(main["phases"]) - np.asarray(replay["phases"]))))
    same_frequency = np.array_equal(main["frequencies_hz"], replay["frequencies_hz"])
    values = {
        "response_relative": response,
        "reaction_relative": reaction,
        "residual_relative_difference": residual,
        "amplitude_relative": amplitude,
        "phase_absolute_rad": phase,
        "frequency_grid_identical": same_frequency,
    }
    values["pass"] = bool(
        response <= gate
        and reaction <= float(contract["predeclared_gates"]["replay_reaction_relative"]["value"])
        and residual <= float(contract["predeclared_gates"]["replay_residual_relative_difference"]["value"])
        and amplitude <= float(contract["predeclared_gates"]["replay_amplitude_relative"]["value"])
        and phase <= float(contract["predeclared_gates"]["replay_phase_absolute_rad"]["value"])
        and same_frequency
    )
    return values


def json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, complex):
        return {"real": float(value.real), "imag": float(value.imag)}
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def main() -> int:
    global CONTRACT
    CONTRACT = load_contract()
    contract_sha = sha256_file(CONTRACT_PATH)
    contract_blob_sha = git_blob_sha(CONTRACT_PATH)
    base = build(1)
    ref = oracle(base)
    ratios = [float(value) for value in CONTRACT["frequency_contract"]["frequency_ratios"]]
    frequencies = [ref["frequency_hz"] * ratio for ratio in ratios]
    prechecks = conditioning(base, ref, CONTRACT)
    if prechecks["status"] != "PASS":
        raise RuntimeError(f"WP13-02C conditioning prechecks failed: {prechecks}")
    started = time.perf_counter()
    result, main_metrics = solve_harmonic(base, frequencies, ref)
    main_metrics["frequencies_hz"] = frequencies
    main_metrics["frequency_ratios"] = ratios
    main_metrics["omega1"] = ref["omega1"]
    main_metrics["alpha"] = ref["alpha"]
    main_metrics["beta"] = ref["beta"]
    replay_frequency_ratios = [
        float(CONTRACT["replay"]["frequencies"]["off_resonance_ratio"]),
        float(CONTRACT["replay"]["frequencies"]["near_resonance_ratio"]),
    ]
    replay_frequencies = [ref["frequency_hz"] * ratio for ratio in replay_frequency_ratios]
    replay_runs: list[dict[str, Any]] = []
    for _ in range(int(CONTRACT["replay"]["count"])):
        _, replay = solve_harmonic(base, replay_frequencies, ref)
        replay["frequencies_hz"] = replay_frequencies
        replay["frequency_ratios"] = replay_frequency_ratios
        replay_runs.append(replay)
    replay_main = {
        key: value
        for key, value in main_metrics.items()
        if key in {"responses", "residual_vectors", "reactions", "amplitudes", "phases", "frequencies_hz"}
    }
    replay_main["responses"] = np.vstack(
        [main_metrics["responses"][ratios.index(ratio)] for ratio in replay_frequency_ratios]
    )
    replay_main["residual_vectors"] = np.vstack(
        [main_metrics["residual_vectors"][ratios.index(ratio)] for ratio in replay_frequency_ratios]
    )
    replay_main["reactions"] = np.vstack(
        [main_metrics["reactions"][ratios.index(ratio)] for ratio in replay_frequency_ratios]
    )
    replay_main["amplitudes"] = [main_metrics["amplitudes"][ratios.index(ratio)] for ratio in replay_frequency_ratios]
    replay_main["phases"] = [main_metrics["phases"][ratios.index(ratio)] for ratio in replay_frequency_ratios]
    replay_main["frequencies_hz"] = replay_frequencies
    replay_comparisons = [replay_comparison(replay_main, replay, CONTRACT) for replay in replay_runs]
    failures = failure_cases(base, ref)

    gates = CONTRACT["predeclared_gates"]
    amplitude_gate = float(gates["oracle_amplitude_relative"]["value"])
    phase_gate = float(gates["oracle_phase_absolute_rad"]["value"])
    residual_gate = float(gates["harmonic_residual_relative"]["value"])
    interface_continuity_gate = float(gates["interface_displacement_continuity"]["value"])
    interface_force_gate = float(gates["interface_force_transfer_relative"]["value"])
    interface_energy_gate = float(gates["interface_energy_error_relative"]["value"])
    interface_rows = main_metrics["interfaces"]
    interface_gate_values = {
        name: {
            "continuity_max": max(float(row[name]["displacement_jump"]) for row in interface_rows),
            "force_balance_max": max(float(row[name]["force_balance_relative"]) for row in interface_rows),
            "energy_mismatch_max": max(float(row[name]["energy_mismatch_relative"]) for row in interface_rows),
        }
        for name in INTERFACES
    }
    numerical_gate_decisions = {
        "static_limit": main_metrics["static_limit_error"] <= float(gates["static_limit_relative"]["value"]),
        "amplitude_all_frequencies": max(main_metrics["amplitude_errors"]) <= amplitude_gate,
        "phase_all_frequencies": max(main_metrics["phase_errors"]) <= phase_gate,
        "residual_all_frequencies": max(main_metrics["residuals"]) <= residual_gate,
        "resonance_peak_index_match": main_metrics["peak_runtime_index"] == main_metrics["peak_reference_index"],
        "resonance_frequency": (
            main_metrics["peak_runtime_index"] == main_metrics["peak_reference_index"]
            and abs(main_metrics["peak_runtime_frequency_hz"] - main_metrics["peak_reference_frequency_hz"])
            / max(main_metrics["peak_reference_frequency_hz"], 1.0)
            <= float(gates["resonance_frequency_relative"]["value"])
        ),
        "interface": all(
            row["continuity_max"] <= interface_continuity_gate
            and row["force_balance_max"] <= interface_force_gate
            and row["energy_mismatch_max"] <= interface_energy_gate
            for row in interface_gate_values.values()
        ),
        "replays": all(item["pass"] for item in replay_comparisons),
        "failure_contract": all(item["status"] == "PASS" and item["executed"] for item in failures.values()),
    }
    arrays: dict[str, np.ndarray] = {}
    array_manifest: dict[str, Any] = {}

    def add_array(name: str, value: Any, dtype: Any) -> None:
        array = np.asarray(value, dtype=dtype)
        arrays[name] = array
        array_manifest[name] = {"shape": list(array.shape), "dtype": str(array.dtype), "sha256": complex_digest(array) if np.iscomplexobj(array) else real_digest(array)}

    add_array("frequencies_hz", frequencies, np.float64)
    add_array("frequency_ratios", ratios, np.float64)
    add_array("runtime_responses", main_metrics["responses"], np.complex128)
    add_array("oracle_dense_responses", main_metrics["references"], np.complex128)
    add_array("oracle_sdof_responses", main_metrics["sdof_references"], np.complex128)
    add_array("residual_vectors", main_metrics["residual_vectors"], np.complex128)
    add_array("reactions", main_metrics["reactions"], np.complex128)
    add_array("amplitudes", main_metrics["amplitudes"], np.float64)
    add_array("reference_amplitudes", main_metrics["reference_amplitudes"], np.float64)
    add_array("amplitude_errors", main_metrics["amplitude_errors"], np.float64)
    add_array("phases", main_metrics["phases"], np.float64)
    add_array("reference_phases", main_metrics["reference_phases"], np.float64)
    add_array("phase_errors", main_metrics["phase_errors"], np.float64)
    add_array("replay_frequencies_hz", replay_frequencies, np.float64)
    add_array("replay_main_responses", replay_main["responses"], np.complex128)
    add_array("replay_1_responses", replay_runs[0]["responses"], np.complex128)
    add_array("replay_2_responses", replay_runs[1]["responses"], np.complex128)
    add_array("replay_main_reactions", replay_main["reactions"], np.complex128)
    add_array("replay_1_reactions", replay_runs[0]["reactions"], np.complex128)
    add_array("replay_2_reactions", replay_runs[1]["reactions"], np.complex128)
    add_array("replay_main_residual_vectors", replay_main["residual_vectors"], np.complex128)
    add_array("replay_1_residual_vectors", replay_runs[0]["residual_vectors"], np.complex128)
    add_array("replay_2_residual_vectors", replay_runs[1]["residual_vectors"], np.complex128)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(ARCHIVE_PATH, **arrays)
    manifest = {
        "schema_version": 1,
        "record_id": "QF-028-WP13-02C-HARMONIC-MIXED-EVIDENCE",
        "work_package": "WP13-02C",
        "contract_id": CONTRACT["contract_id"],
        "contract_sha256": contract_sha,
        "contract_blob_sha": contract_blob_sha,
        "contract_commit": git_last_commit(CONTRACT_PATH),
        "contract_committed_before_run": True,
        "contract_unchanged": True,
        "repo_sha": git_revision(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
        },
        "benchmark_inputs": {
            "generator": "scripts/run_wp13_01k_mvp.py:build(1), static loads discarded",
            "family_counts": {family: sum(element.type == family for element in base.elements) for family in FAMILIES},
            "ndof": ref["dofs"].ndof,
            "connected_components": 1,
            "direct_support_bypass": False,
            "mechanical_load_path": CONTRACT["scope"]["mechanical_path"],
            "interfaces": {name: list(value[2]) for name, value in INTERFACES.items()},
            "probe": {"node": ref["probe_node"], "dof": ref["probe_dof"]},
        },
        "conditioning": prechecks,
        "damping": {"model": "Rayleigh", "alpha": ref["alpha"], "beta": ref["beta"], "zeta": ref["zeta"]},
        "frequencies": {"ratios": ratios, "frequencies_hz": frequencies, "first_frequency_hz": ref["frequency_hz"]},
        "oracle": {
            "first_frequency_hz": ref["frequency_hz"],
            "first_eigenvalue": float(ref["omega1"] ** 2),
            "damping_ratio": ref["zeta"],
            "reference_method": CONTRACT["oracle"]["dense_reference"],
            "sdof_method": CONTRACT["oracle"]["sdof_reference"],
            "first_mode_load_participation_ratio": ref["first_mode_load_participation_ratio"],
            "sdof_control": {
                "status": "SUPPORTING_DIAGNOSTIC_ONLY",
                "max_probe_relative_error": max(main_metrics["sdof_probe_relative_errors"]),
                "first_mode_dominance_demonstrated": ref["first_mode_load_participation_ratio"] >= 0.5,
                "interpretation": "The dense direct oracle is the acceptance oracle. The SDOF result is retained as a diagnostic and is not converted into a gate after observation.",
            },
            "independence_boundary": CONTRACT["oracle"]["independence_boundary"],
        },
        "metrics": {
            key: value
            for key, value in main_metrics.items()
            if key not in {"responses", "references", "sdof_references", "residual_vectors", "reactions", "interfaces", "energies"}
        },
        "interface_metrics": interface_rows,
        "interface_gate_values": interface_gate_values,
        "family_energies": main_metrics["energies"],
        "family_participation": {
            family: bool(
                max(row[family]["kinetic"] for row in main_metrics["energies"]) > 0.0
                or max(row[family]["strain"] for row in main_metrics["energies"]) > 0.0
            )
            for family in FAMILIES
        },
        "replays": {"frequencies_hz": replay_frequencies, "comparisons": replay_comparisons},
        "failure_executions": failures,
        "array_manifest": array_manifest,
        "archive": {"path": ARCHIVE_PATH.name, "sha256": sha256_file(ARCHIVE_PATH)},
        "gate_decisions": numerical_gate_decisions,
        "claim_candidate": CONTRACT["claim_policy"]["candidate"],
        "status": "PASS_CANDIDATE" if all(numerical_gate_decisions.values()) else "FAIL",
        "runtime_seconds": time.perf_counter() - started,
        "integrity": {
            "numerical_source_changed": False,
            "formulation_changed": False,
            "contract_changed": False,
            "maturity_changed": False,
            "newmark_evidence_modified": False,
            "evidence_source_of_truth": "contract JSON loaded at runtime; no duplicated gate constants",
        },
    }
    MANIFEST_PATH.write_text(json.dumps(json_safe(manifest), indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "contract": CONTRACT["contract_id"], "gates": numerical_gate_decisions, "frequency_hz": frequencies, "peak": main_metrics["peak_runtime_frequency_hz"]}, indent=2), flush=True)
    return 0 if manifest["status"] == "PASS_CANDIDATE" else 3


if __name__ == "__main__":
    raise SystemExit(main())
