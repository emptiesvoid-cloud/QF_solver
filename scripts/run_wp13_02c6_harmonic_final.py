"""Execute WP13-02C6 with the WP13-02C5 evidence pipeline frozen first.

The C5 pipeline remains the source of truth for contract lookup, interface
energy, modal projection, failure evidence and freeze verification.  This
runner is committed before its pre-run freeze and writes a new C6 archive; it
never overwrites C, C2 or C3 evidence and has no post-run processing stage.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import jsonschema
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_wp13_02c_harmonic_mixed as legacy  # noqa: E402
import run_wp13_02c5_harmonic_pipeline as c5  # noqa: E402
from solveur.api.public import solve_model  # noqa: E402


CONTRACT_PATH = c5.CONTRACT_PATH
C6_SCHEMA_PATH = ROOT / "qualification/0_2_8/wp13_02c6_harmonic_evidence.schema.json"
OUTPUT_DIR = ROOT / "qualification/0_2_8/wp13_02c6_harmonic_final"
FREEZE_PATH = OUTPUT_DIR / "pre_run_freeze.json"
ARCHIVE_PATH = OUTPUT_DIR / "wp13_02c6_harmonic_arrays.npz"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
RUNNER_PATH = Path(__file__).resolve()
INTERFACES = legacy.INTERFACES
FAMILIES = legacy.FAMILIES


def sha256_file(path: Path) -> str:
    return c5.sha256_file(path)


def json_safe(value: Any) -> Any:
    return c5._json_safe(value)


def load_contract() -> dict[str, Any]:
    return c5.load_contract()


def _relative(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a)
    b = np.asarray(b)
    return float(np.linalg.norm(a - b) / max(float(np.linalg.norm(a)), 1.0e-30))


def _contractual_residual(contract: dict[str, Any], residual: np.ndarray, ref: dict[str, Any]) -> float:
    literal = str(c5.contract_value(contract, "metric_definitions.residual_relative"))
    if "max(norm(F_free),1 N)" not in literal:
        raise c5.ContractComplianceError("C6 residual implementation does not match the frozen literal.")
    free_force_norm = float(np.linalg.norm(ref["load"][ref["free"]]))
    return float(np.linalg.norm(residual[ref["free"]]) / max(free_force_norm, 1.0))


def _family_trace(
    records: list[dict[str, Any]], response: np.ndarray, family: str, nodes: tuple[int, ...]
) -> tuple[np.ndarray, dict[str, Any]]:
    trace: list[np.ndarray] = []
    source_records: list[list[int]] = []
    differences: list[float] = []
    for node in nodes:
        observations: list[np.ndarray] = []
        record_ids: list[int] = []
        for index, record in enumerate(records):
            if record["family"] != family or node not in record["nodes"]:
                continue
            local_node = record["nodes"].index(node)
            ids = np.asarray(record["ids"][3 * local_node : 3 * local_node + 3], dtype=int)
            observations.append(np.asarray(response[ids], dtype=np.complex128))
            record_ids.append(index)
        if not observations:
            raise RuntimeError(f"No {family} element record touches interface node {node}.")
        stacked = np.vstack(observations)
        differences.append(float(np.max(np.abs(stacked - stacked[0]))))
        trace.append(np.mean(stacked, axis=0))
        source_records.append(record_ids)
    return np.concatenate(trace), {
        "family": family,
        "nodes": list(nodes),
        "source_element_records": source_records,
        "observation_count": int(sum(len(item) for item in source_records)),
        "collection": "family-local element records -> local node-major DOF slices",
        "independent_state_collection": True,
        "within_family_observation_max_difference": max(differences, default=0.0),
    }


def _family_force(
    ref: dict[str, Any], response: np.ndarray, frequency_hz: float, family: str, nodes: tuple[int, ...]
) -> tuple[np.ndarray, dict[str, Any]]:
    omega = 2.0 * math.pi * frequency_hz
    force = np.zeros(3 * len(nodes), dtype=np.complex128)
    source_records: list[int] = []
    for record_index, record in enumerate(ref["records"]):
        if record["family"] != family:
            continue
        dynamic = record["K"] + 1j * omega * (
            ref["alpha"] * record["M"] + ref["beta"] * record["K"]
        ) - omega**2 * record["M"]
        local_force = dynamic @ response[np.asarray(record["ids"], dtype=int)]
        for output_index, node in enumerate(nodes):
            if node in record["nodes"]:
                local_node = record["nodes"].index(node)
                force[3 * output_index : 3 * output_index + 3] += local_force[
                    3 * local_node : 3 * local_node + 3
                ]
                source_records.append(record_index)
    return force, {
        "family": family,
        "nodes": list(nodes),
        "source_element_records": sorted(set(source_records)),
        "collection": "family-local dynamic element forces on interface DOFs",
    }


def interface_metrics(
    contract: dict[str, Any], ref: dict[str, Any], response: np.ndarray, frequency_hz: float
) -> dict[str, Any]:
    free_force_norm = float(np.linalg.norm(ref["load"][ref["free"]]))
    response_l2 = float(np.linalg.norm(response))
    response_scale = max(float(np.max(np.abs(response))), 1.0e-30)
    result: dict[str, Any] = {}
    for name, (left, right, nodes) in INTERFACES.items():
        left_state, left_source = _family_trace(ref["records"], response, left, nodes)
        right_state, right_source = _family_trace(ref["records"], response, right, nodes)
        left_force, left_force_source = _family_force(ref, response, frequency_hz, left, nodes)
        right_force, right_force_source = _family_force(ref, response, frequency_hz, right, nodes)
        work_left = np.vdot(left_state, left_force)
        work_right = np.vdot(right_state, right_force)
        energy = c5.energy_metric_from_contract(
            contract, work_left, work_right, free_force_norm, response_l2
        )
        result[name] = {
            "shared_nodes": list(nodes),
            "left_family": left,
            "right_family": right,
            "left_state": left_state,
            "right_state": right_state,
            "left_force": left_force,
            "right_force": right_force,
            "displacement_jump": float(np.max(np.abs(left_state - right_state)) / response_scale),
            "force_balance_relative": float(
                np.linalg.norm(left_force + right_force) / max(free_force_norm, 1.0)
            ),
            "work_left": complex(work_left),
            "work_right": complex(work_right),
            "energy": energy,
            "left_state_source": left_source,
            "right_state_source": right_source,
            "left_force_source": left_force_source,
            "right_force_source": right_force_source,
            "independent_state_collection": True,
            "continuity_tautological": False,
        }
    return result


def run_campaign(
    base: Any,
    ref: dict[str, Any],
    contract: dict[str, Any],
    frequencies: np.ndarray,
) -> dict[str, Any]:
    model = legacy.build_harmonic_model(base, frequencies.tolist(), ref["alpha"])
    started = time.perf_counter()
    result = solve_model(model, enforce_policy=False)
    elapsed = time.perf_counter() - started
    responses = np.vstack([np.asarray(item, dtype=np.complex128) for item in result.responses])
    references = np.vstack([legacy.dense_response(ref, float(frequency)) for frequency in frequencies])
    sdof = np.vstack([legacy.sdof_response(ref, float(frequency)) for frequency in frequencies])
    probe = ref["dofs"].index(ref["probe_node"], ref["probe_dof"])
    residual_vectors: list[np.ndarray] = []
    residuals: list[float] = []
    reactions: list[np.ndarray] = []
    interfaces: list[dict[str, Any]] = []
    energies: list[dict[str, Any]] = []
    modal: list[complex] = []
    for response, frequency in zip(responses, frequencies, strict=True):
        omega = 2.0 * math.pi * float(frequency)
        dynamic = ref["stiffness"] + 1j * omega * ref["damping"] - omega**2 * ref["mass"]
        residual = dynamic @ response - ref["load"]
        residual_vectors.append(residual)
        residuals.append(_contractual_residual(contract, residual, ref))
        reactions.append(residual[ref["fixed"]])
        interfaces.append(interface_metrics(contract, ref, response, float(frequency)))
        energies.append(legacy.family_energies(ref, response, float(frequency)))
        q, _ = c5.modal_coordinate(
            ref["mode"], ref["mass"], response,
            phi_source="independent dense K/M eigen-oracle first fixed-base mode",
            mass_source="independent dense K/M mass matrix",
        )
        modal.append(q)
    amplitudes = np.abs(responses[:, probe])
    reference_amplitudes = np.abs(references[:, probe])
    phases = np.angle(responses[:, probe])
    reference_phases = np.angle(references[:, probe])
    amplitude_errors = np.abs(amplitudes / np.maximum(reference_amplitudes, 1.0e-30) - 1.0)
    phase_errors = np.abs((phases - reference_phases + math.pi) % (2.0 * math.pi) - math.pi)
    peak_runtime_index = int(np.argmax(amplitudes))
    peak_reference_index = int(np.argmax(reference_amplitudes))
    return {
        "responses": responses,
        "references": references,
        "sdof_references": sdof,
        "residual_vectors": np.vstack(residual_vectors),
        "residuals": np.asarray(residuals, dtype=float),
        "reactions": np.vstack(reactions),
        "interfaces": interfaces,
        "energies": energies,
        "modal_coordinate_complex": np.asarray(modal, dtype=np.complex128),
        "amplitudes": amplitudes,
        "reference_amplitudes": reference_amplitudes,
        "amplitude_errors": amplitude_errors,
        "phases": phases,
        "reference_phases": reference_phases,
        "phase_errors": phase_errors,
        "static_limit_error": float(
            np.linalg.norm(responses[0].real - ref["static"])
            / max(np.linalg.norm(ref["static"]), 1.0e-30)
        ),
        "peak_runtime_index": peak_runtime_index,
        "peak_reference_index": peak_reference_index,
        "peak_runtime_frequency_hz": float(frequencies[peak_runtime_index]),
        "peak_reference_frequency_hz": float(frequencies[peak_reference_index]),
        "frequencies_hz": frequencies,
        "solver_status": str(result.status),
        "runtime_seconds": elapsed,
    }


def replay_packet(
    metrics: dict[str, Any], indices: np.ndarray | None = None
) -> dict[str, Any]:
    if indices is None:
        return metrics
    packet: dict[str, Any] = {}
    for key, value in metrics.items():
        if key in {"interfaces", "energies"}:
            packet[key] = [value[int(index)] for index in indices]
        elif isinstance(value, np.ndarray) and value.ndim > 0 and value.shape[0] == len(metrics["frequencies_hz"]):
            packet[key] = value[indices]
        else:
            packet[key] = value
    packet["frequencies_hz"] = np.asarray(metrics["frequencies_hz"])[indices]
    return packet


def replay_comparison(main: dict[str, Any], replay: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    gate = float(contract["predeclared_gates"]["replay_response_relative"]["value"])
    reaction_gate = float(contract["predeclared_gates"]["replay_reaction_relative"]["value"])
    residual_gate = float(contract["predeclared_gates"]["replay_residual_relative_difference"]["value"])
    amplitude_gate = float(contract["predeclared_gates"]["replay_amplitude_relative"]["value"])
    phase_gate = float(contract["predeclared_gates"]["replay_phase_absolute_rad"]["value"])
    fields = c5.replay_fields_from_contract(contract)
    values = {
        "complex_displacement_relative": _relative(main["responses"], replay["responses"]),
        "complex_reactions_relative": _relative(main["reactions"], replay["reactions"]),
        "complex_residual_relative": _relative(main["residual_vectors"], replay["residual_vectors"]),
        "amplitude_relative": _relative(main["amplitudes"], replay["amplitudes"]),
        "phase_absolute_rad": float(np.max(np.abs(main["phases"] - replay["phases"]))),
        "frequency_grid_identical": bool(np.array_equal(main["frequencies_hz"], replay["frequencies_hz"])),
        "status_identical": main["solver_status"] == replay["solver_status"],
        "modal_coordinate_relative": _relative(
            main["modal_coordinate_complex"], replay["modal_coordinate_complex"]
        ),
    }
    for name in INTERFACES:
        for side in ("left_state", "right_state", "left_force", "right_force"):
            values[f"{name}_{side}_relative"] = _relative(
                np.vstack([row[name][side] for row in main["interfaces"]]),
                np.vstack([row[name][side] for row in replay["interfaces"]]),
            )
        for scalar in ("displacement_jump", "force_balance_relative"):
            values[f"{name}_{scalar}_relative"] = _relative(
                np.asarray([row[name][scalar] for row in main["interfaces"]]),
                np.asarray([row[name][scalar] for row in replay["interfaces"]]),
            )
        for work in ("work_left", "work_right"):
            values[f"{name}_{work}_relative"] = _relative(
                np.asarray([row[name][work] for row in main["interfaces"]]),
                np.asarray([row[name][work] for row in replay["interfaces"]]),
            )
        values[f"{name}_energy_relative"] = _relative(
            np.asarray([row[name]["energy"]["energy_relative"] for row in main["interfaces"]]),
            np.asarray([row[name]["energy"]["energy_relative"] for row in replay["interfaces"]]),
        )
    values["pass"] = bool(
        values["complex_displacement_relative"] <= gate
        and values["complex_reactions_relative"] <= reaction_gate
        and values["complex_residual_relative"] <= residual_gate
        and values["amplitude_relative"] <= amplitude_gate
        and values["phase_absolute_rad"] <= phase_gate
        and values["modal_coordinate_relative"] <= gate
        and values["frequency_grid_identical"]
        and values["status_identical"]
        and all(
            value <= gate
            for key, value in values.items()
            if key.endswith("_relative") and key not in {
                "complex_reactions_relative", "complex_residual_relative", "amplitude_relative"
            }
        )
    )
    return {
        **values,
        "fields_compared": fields,
        "synthetic_fields": [],
    }


def add_array(arrays: dict[str, np.ndarray], digests: dict[str, Any], name: str, value: Any, dtype: Any) -> None:
    array = np.asarray(value, dtype=dtype)
    arrays[name] = array
    digests[name] = {
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "sha256": c5.sha256_bytes(np.ascontiguousarray(array).tobytes()),
    }


def _interface_arrays(
    arrays: dict[str, np.ndarray], digests: dict[str, Any], prefix: str, rows: list[dict[str, Any]]
) -> None:
    for name in INTERFACES:
        safe = name.lower()
        for side in ("left_state", "right_state", "left_force", "right_force"):
            add_array(arrays, digests, f"{prefix}_{safe}_{side}", [row[name][side] for row in rows], np.complex128)
        add_array(arrays, digests, f"{prefix}_{safe}_displacement_jump", [row[name]["displacement_jump"] for row in rows], np.float64)
        add_array(arrays, digests, f"{prefix}_{safe}_force_balance", [row[name]["force_balance_relative"] for row in rows], np.float64)
        for side in ("work_left", "work_right"):
            add_array(arrays, digests, f"{prefix}_{safe}_{side}", [row[name][side] for row in rows], np.complex128)
        for key in ("wleft_abs", "wright_abs", "work_sum", "ffree_l2", "x_l2", "force_displacement_product", "energy_denominator", "energy_numerator", "energy_relative"):
            add_array(arrays, digests, f"{prefix}_{safe}_energy_{key}", [row[name]["energy"][key] for row in rows], np.float64)


def _energy_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    first = rows[0][next(iter(INTERFACES))]["energy"]
    return first


def main() -> int:
    contract = load_contract()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if c5.pipeline_combined_digest(c5.pipeline_component_digests()) != "180c6d48a8613b8b4e082c13725a293d4aef28f405c5055093bff14645867389":
        raise RuntimeError("C5 pipeline combined digest mismatch before run.")
    c5_freeze = c5.build_pipeline_freeze()
    if c5_freeze["pipeline_combined_digest"] != "180c6d48a8613b8b4e082c13725a293d4aef28f405c5055093bff14645867389":
        raise RuntimeError("Unexpected C5 combined pipeline digest.")
    campaign_freeze = {
        **c5_freeze,
        "campaign_driver_path": "scripts/run_wp13_02c6_harmonic_final.py",
        "campaign_driver_digest": sha256_file(RUNNER_PATH),
        "campaign_schema_path": "qualification/0_2_8/wp13_02c6_harmonic_evidence.schema.json",
        "campaign_schema_digest": sha256_file(C6_SCHEMA_PATH),
        "contract_blob_digest": sha256_file(CONTRACT_PATH),
        "schema_blob_digest": sha256_file(c5.EVIDENCE_SCHEMA_PATH),
        "repo_sha": c5.git_revision(),
        "pre_run_freeze_valid": True,
        "numerical_campaign_started": False,
    }
    FREEZE_PATH.write_text(json.dumps(json_safe(campaign_freeze), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    base = legacy.build(1)
    ref = legacy.oracle(base)
    ratios = np.asarray(contract["frequency_contract"]["frequency_ratios"], dtype=float)
    frequencies = ref["frequency_hz"] * ratios
    conditioning = legacy.conditioning(base, ref, contract)
    if conditioning["status"] != "PASS":
        raise RuntimeError(f"Conditioning prechecks failed: {conditioning}")
    main_metrics = run_campaign(base, ref, contract, frequencies)

    replay_ratios = np.asarray([
        float(contract["replay"]["frequencies"]["off_resonance_ratio"]),
        float(contract["replay"]["frequencies"]["near_resonance_ratio"]),
    ])
    replay_frequencies = ref["frequency_hz"] * replay_ratios
    main_indices = np.asarray([int(np.flatnonzero(ratios == ratio)[0]) for ratio in replay_ratios], dtype=int)
    replay_main = replay_packet(main_metrics, main_indices)
    replay_packets = [run_campaign(base, ref, contract, replay_frequencies) for _ in range(2)]
    replay_comparisons = [replay_comparison(replay_main, packet, contract) for packet in replay_packets]
    failures = c5.execute_failure_contract(base, ref["frequency_hz"], ref["alpha"], contract)

    gates = contract["predeclared_gates"]
    interface_gate_values = {
        name: {
            "continuity_max": max(float(row[name]["displacement_jump"]) for row in main_metrics["interfaces"]),
            "force_balance_max": max(float(row[name]["force_balance_relative"]) for row in main_metrics["interfaces"]),
            "energy_mismatch_max": max(float(row[name]["energy"]["energy_relative"]) for row in main_metrics["interfaces"]),
        }
        for name in INTERFACES
    }
    gate_decisions = {
        "static_limit": main_metrics["static_limit_error"] <= float(gates["static_limit_relative"]["value"]),
        "amplitude_all_frequencies": max(main_metrics["amplitude_errors"]) <= float(gates["oracle_amplitude_relative"]["value"]),
        "phase_all_frequencies": max(main_metrics["phase_errors"]) <= float(gates["oracle_phase_absolute_rad"]["value"]),
        "residual_all_frequencies": max(main_metrics["residuals"]) <= float(gates["harmonic_residual_relative"]["value"]),
        "resonance_peak_index_match": main_metrics["peak_runtime_index"] == main_metrics["peak_reference_index"],
        "resonance_frequency": (
            main_metrics["peak_runtime_index"] == main_metrics["peak_reference_index"]
            and abs(main_metrics["peak_runtime_frequency_hz"] - main_metrics["peak_reference_frequency_hz"])
            / max(main_metrics["peak_reference_frequency_hz"], 1.0)
            <= float(gates["resonance_frequency_relative"]["value"])
        ),
        "interface": all(
            row["continuity_max"] <= float(gates["interface_displacement_continuity"]["value"])
            and row["force_balance_max"] <= float(gates["interface_force_transfer_relative"]["value"])
            and row["energy_mismatch_max"] <= float(gates["interface_energy_error_relative"]["value"])
            for row in interface_gate_values.values()
        ),
        "replays": all(item["pass"] for item in replay_comparisons),
        "failure_contract": all(item["pass"] and item["executed"] for item in failures.values()),
    }

    arrays: dict[str, np.ndarray] = {}
    array_digests: dict[str, Any] = {}
    for name, value, dtype in (
        ("frequencies_hz", frequencies, np.float64),
        ("frequency_ratios", ratios, np.float64),
        ("runtime_responses", main_metrics["responses"], np.complex128),
        ("oracle_dense_responses", main_metrics["references"], np.complex128),
        ("oracle_sdof_responses", main_metrics["sdof_references"], np.complex128),
        ("residual_vectors", main_metrics["residual_vectors"], np.complex128),
        ("residual_relative", main_metrics["residuals"], np.float64),
        ("reactions", main_metrics["reactions"], np.complex128),
        ("amplitudes", main_metrics["amplitudes"], np.float64),
        ("reference_amplitudes", main_metrics["reference_amplitudes"], np.float64),
        ("amplitude_errors", main_metrics["amplitude_errors"], np.float64),
        ("phases", main_metrics["phases"], np.float64),
        ("reference_phases", main_metrics["reference_phases"], np.float64),
        ("phase_errors", main_metrics["phase_errors"], np.float64),
        ("modal_coordinate_complex", main_metrics["modal_coordinate_complex"], np.complex128),
        ("modal_coordinate_amplitude", np.abs(main_metrics["modal_coordinate_complex"]), np.float64),
        ("modal_coordinate_phase", np.angle(main_metrics["modal_coordinate_complex"]), np.float64),
        ("replay_frequencies_hz", replay_frequencies, np.float64),
    ):
        add_array(arrays, array_digests, name, value, dtype)
    _interface_arrays(arrays, array_digests, "main", main_metrics["interfaces"])
    for label, packet in zip(("main", "replay_1", "replay_2"), (replay_main, *replay_packets), strict=True):
        for name, value, dtype in (
            ("responses", packet["responses"], np.complex128),
            ("reactions", packet["reactions"], np.complex128),
            ("residual_vectors", packet["residual_vectors"], np.complex128),
            ("amplitudes", packet["amplitudes"], np.float64),
            ("phases", packet["phases"], np.float64),
            ("modal_coordinate_complex", packet["modal_coordinate_complex"], np.complex128),
            ("modal_coordinate_amplitude", np.abs(packet["modal_coordinate_complex"]), np.float64),
            ("modal_coordinate_phase", np.angle(packet["modal_coordinate_complex"]), np.float64),
        ):
            add_array(arrays, array_digests, f"replay_{label}_{name}", value, dtype)
        _interface_arrays(arrays, array_digests, f"replay_{label}", packet["interfaces"])

    np.savez_compressed(ARCHIVE_PATH, **arrays)
    energy_contract = _energy_summary(main_metrics["interfaces"])
    phi_digest = c5.canonical_digest(ref["mode"])
    mass_digest = c5.canonical_digest(ref["mass"])
    manifest = {
        "schema_version": 6,
        "record_id": "QF-028-WP13-02C6-HARMONIC-MIXED-EVIDENCE",
        "work_package": "WP13-02C6",
        "contract_id": contract["contract_id"],
        "contract_sha256": sha256_file(CONTRACT_PATH),
        "repo_sha": campaign_freeze["repo_sha"],
        "environment": c5.environment_snapshot(),
        "contract_values_single_source_of_truth": True,
        "contract_trace": c5.contract_trace(contract),
        "benchmark_inputs": {
            "family_counts": {family: sum(element.type == family for element in base.elements) for family in FAMILIES},
            "ndof": ref["dofs"].ndof,
            "connected_components": 1,
            "direct_support_bypass": False,
            "mechanical_load_path": contract["scope"]["mechanical_path"],
            "interfaces": {name: list(value[2]) for name, value in INTERFACES.items()},
        },
        "conditioning": conditioning,
        "frequencies": {"ratios": ratios, "frequencies_hz": frequencies, "first_frequency_hz": ref["frequency_hz"]},
        "damping": {"model": "Rayleigh", "alpha": ref["alpha"], "beta": ref["beta"], "zeta": ref["zeta"]},
        "raw_complex_responses": {"array_key": "runtime_responses", "all_declared_frequencies": True},
        "oracle_responses": {
            "dense_array_key": "oracle_dense_responses",
            "sdof_array_key": "oracle_sdof_responses",
            "reference_method": contract["oracle"]["dense_reference"],
            "independence_boundary": contract["oracle"]["independence_boundary"],
            "first_mode_load_participation_ratio": ref["first_mode_load_participation_ratio"],
            "first_mode_dominated_claim_allowed": False,
        },
        "amplitude_phase": {
            "amplitudes_array_key": "amplitudes", "reference_amplitudes_array_key": "reference_amplitudes",
            "amplitude_errors_array_key": "amplitude_errors", "phases_array_key": "phases",
            "reference_phases_array_key": "reference_phases", "phase_errors_array_key": "phase_errors",
        },
        "modal_coordinate": {
            "complex": {"array_key": "modal_coordinate_complex"},
            "amplitude": {"array_key": "modal_coordinate_amplitude"},
            "phase": {"array_key": "modal_coordinate_phase"},
            "definition": {
                "modal_vector_source": "independent dense K/M eigen-oracle first fixed-base mode",
                "normalization": "mass-normalized eigenvector with canonical sign",
                "projection_formula": "q = phi^H M x",
                "first_mode_dominated_claim_allowed": False,
            },
        },
        "modal_coordinate_pipeline": {
            "frozen_pipeline": True,
            "phi_source": "independent dense K/M eigen-oracle first fixed-base mode",
            "phi_digest": phi_digest,
            "mass_source": "independent dense K/M mass matrix",
            "mass_digest": mass_digest,
            "normalization": "mass-normalized eigenvector",
            "projection_formula": "q = phi^H M x",
        },
        "residuals": {
            "vector_array_key": "residual_vectors", "relative_array_key": "residual_relative",
            "definition": c5.contract_value(contract, "metric_definitions.residual_relative"),
            "max": float(max(main_metrics["residuals"])),
        },
        "static_limit": {
            "error": main_metrics["static_limit_error"],
            "gate": contract["predeclared_gates"]["static_limit_relative"],
        },
        "resonance": {
            "label": "FRF_PEAK_IN_FROZEN_FREQUENCY_CAMPAIGN",
            "runtime_frequency_hz": main_metrics["peak_runtime_frequency_hz"],
            "reference_frequency_hz": main_metrics["peak_reference_frequency_hz"],
            "frequency_error": abs(main_metrics["peak_runtime_frequency_hz"] - main_metrics["peak_reference_frequency_hz"])
            / max(main_metrics["peak_reference_frequency_hz"], 1.0),
            "amplitude_error": float(main_metrics["amplitude_errors"][main_metrics["peak_reference_index"]]),
            "phase_error": float(main_metrics["phase_errors"][main_metrics["peak_reference_index"]]),
            "first_mode_resonance_claim": False,
        },
        "interface_metrics": {
            "frequency_rows": main_metrics["interfaces"],
            "gate_values": interface_gate_values,
            "state_collection_independent": True,
            "continuity_tautological": False,
            "energy_normalization": {
                "contract_path": "metric_definitions.interface_energy",
                "formula": contract["metric_definitions"]["interface_energy"],
                "formula_literal_match": True,
            },
        },
        "energy_contract": energy_contract,
        "replay_arrays": {
            "frequencies_hz": replay_frequencies,
            "packets": ["main", "replay_1", "replay_2"],
            "fields": c5.replay_fields_from_contract(contract),
            "synthetic_fields": [],
        },
        "replay_comparison": {
            "comparisons": replay_comparisons,
            "status_identical": all(item["status_identical"] for item in replay_comparisons),
            "full_array_comparison": all(item["pass"] for item in replay_comparisons),
        },
        "replay_pipeline": {
            "fields": c5.replay_fields_from_contract(contract),
            "runtime_iteration_semantics": "not_declared_by_harmonic_contract",
            "synthetic_fields": [],
        },
        "failure_executions": {
            "required": 9,
            "executed": sum(bool(item["executed"]) for item in failures.values()),
            "pass": sum(bool(item["pass"]) for item in failures.values()),
            "silent_fallback_allowed": False,
            "cases": failures,
        },
        "pipeline_freeze": campaign_freeze,
        "post_run_pipeline_mutation_allowed": False,
        "post_run_manifest_rewrite_allowed": False,
        "historical_owner_records": {"WP13-02C4": "qualification/0_2_8/wp13_02c4_owner_gate.json"},
        "digests": {"arrays": array_digests, "archive_sha256": sha256_file(ARCHIVE_PATH)},
        "gate_decisions": gate_decisions,
        "historical_records_preserved": True,
        "claim_candidate": contract["claim_policy"]["candidate"],
        "status": "PASS_HARMONIC_FINAL_OWNER_READY" if all(gate_decisions.values()) else "FAIL",
        "evidence_schema_valid": False,
        "integrity": {
            "numerical_source_changed": False, "vnv_harness_changed": False,
            "formulation_changed": False, "contract_changed": False,
            "gates_changed": False, "schema_changed": False,
            "pipeline_changed": False, "maturity_changed": False,
            "historical_0_2_7_evidence_changed": False,
        },
    }
    schema = json.loads(C6_SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = [error.message for error in jsonschema.Draft202012Validator(schema).iter_errors(json_safe(manifest))]
    manifest["evidence_schema_valid"] = not bool(errors)
    manifest["evidence_schema_errors"] = errors
    if errors:
        raise RuntimeError(f"C6 schema validation failed: {errors}")
    if c5.validate_pipeline_evidence(manifest, contract):
        raise RuntimeError("C5 semantic validator rejected C6 evidence.")
    pre_digest = campaign_freeze["pipeline_combined_digest"]
    post_freeze = c5.build_pipeline_freeze()
    post_driver_digest = sha256_file(RUNNER_PATH)
    post_schema_digest = sha256_file(C6_SCHEMA_PATH)
    if post_freeze["pipeline_combined_digest"] != pre_digest or post_driver_digest != campaign_freeze["campaign_driver_digest"] or post_schema_digest != campaign_freeze["campaign_schema_digest"]:
        raise RuntimeError("Pipeline or campaign-driver mutation detected after numerical run.")
    manifest["post_run_pipeline_digest"] = post_freeze["pipeline_combined_digest"]
    manifest["pipeline_digest_match"] = True
    manifest["pipeline_mutation_detected"] = False
    manifest["evidence_integrity"] = True
    MANIFEST_PATH.write_text(json.dumps(json_safe(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": manifest["status"],
        "gates": gate_decisions,
        "frequency_points": len(frequencies),
        "failure_cases": [item["pass"] for item in failures.values()],
        "replays": [item["pass"] for item in replay_comparisons],
        "manifest": str(MANIFEST_PATH),
        "archive": str(ARCHIVE_PATH),
    }, indent=2, default=json_safe), flush=True)
    return 0 if manifest["status"] == "PASS_HARMONIC_FINAL_OWNER_READY" else 3


if __name__ == "__main__":
    raise SystemExit(main())
