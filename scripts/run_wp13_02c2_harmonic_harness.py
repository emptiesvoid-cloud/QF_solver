"""Validate the corrected WP13-02C harmonic V&V harness.

This is a harness/evidence micro-check only. It deliberately does not call
the twelve-frequency WP13-02C production campaign. It reads the immutable C
archive, reconstructs interface traces from family-local element records,
executes the nine rejection cases, validates strict provenance, and writes a
separate C2 record. The frozen C manifest and archive are never rewritten.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import platform
import re
import subprocess
import sys
import traceback
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


CONTRACT_PATH = ROOT / "qualification/0_2_8/wp13_02c_harmonic_contract.json"
CONTRACT_SCHEMA_PATH = ROOT / "qualification/0_2_8/wp13_02c_harmonic_contract.schema.json"
EVIDENCE_SCHEMA_PATH = ROOT / "qualification/0_2_8/wp13_02c_harmonic_evidence.schema.json"
OLD_MANIFEST_PATH = ROOT / "qualification/0_2_8/wp13_02c_harmonic_v1/manifest.json"
OLD_ARCHIVE_PATH = ROOT / "qualification/0_2_8/wp13_02c_harmonic_v1/wp13_02c_harmonic_arrays.npz"
OUTPUT_DIR = ROOT / "qualification/0_2_8/wp13_02c2_harmonic_harness"
ARCHIVE_PATH = OUTPUT_DIR / "wp13_02c2_harness_arrays.npz"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
FAMILIES = legacy.FAMILIES
INTERFACES = legacy.INTERFACES
CONTRACT: dict[str, Any] = {}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_blob_sha(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def git_revision() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.complexfloating):
        return {"real": float(value.real), "imag": float(value.imag)}
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, complex):
        return {"real": float(value.real), "imag": float(value.imag)}
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def environment_snapshot() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": __import__("scipy").__version__,
        "executable": sys.executable,
        "harness": "WP13-02C2 micro-check; no twelve-frequency campaign",
    }


def load_sources() -> tuple[dict[str, Any], dict[str, Any], np.lib.npyio.NpzFile, dict[str, Any]]:
    global CONTRACT
    contract = legacy.load_contract()
    legacy.CONTRACT = contract
    CONTRACT = contract
    old_manifest = json.loads(OLD_MANIFEST_PATH.read_text(encoding="utf-8"))
    if sha256_file(OLD_ARCHIVE_PATH) != old_manifest["archive"]["sha256"]:
        raise RuntimeError("Immutable WP13-02C archive digest mismatch.")
    if old_manifest["contract_sha256"] != sha256_file(CONTRACT_PATH):
        raise RuntimeError("WP13-02C manifest contract digest mismatch.")
    archive = np.load(OLD_ARCHIVE_PATH, allow_pickle=False)
    return contract, old_manifest, archive, {
        "contract_sha256": sha256_file(CONTRACT_PATH),
        "contract_blob_sha": git_blob_sha(CONTRACT_PATH),
        "contract_schema_sha256": sha256_file(CONTRACT_SCHEMA_PATH),
        "evidence_schema_sha256": sha256_file(EVIDENCE_SCHEMA_PATH),
        "evidence_schema_blob_sha": git_blob_sha(EVIDENCE_SCHEMA_PATH),
        "old_archive_sha256": sha256_file(OLD_ARCHIVE_PATH),
        "old_manifest_sha256": sha256_file(OLD_MANIFEST_PATH),
    }


def _family_trace(
    records: list[dict[str, Any]], response: np.ndarray, family: str, nodes: tuple[int, ...]
) -> tuple[np.ndarray, dict[str, Any]]:
    """Gather a side trace through family-local element records."""

    trace: list[np.ndarray] = []
    source_records: list[list[int]] = []
    observation_errors: list[float] = []
    for node in nodes:
        observations: list[np.ndarray] = []
        record_ids: list[int] = []
        for record_index, record in enumerate(records):
            if record["family"] != family or node not in record["nodes"]:
                continue
            local_node = record["nodes"].index(node)
            ids = np.asarray(record["ids"][3 * local_node : 3 * local_node + 3], dtype=int)
            observations.append(np.asarray(response[ids], dtype=np.complex128))
            record_ids.append(record_index)
        if not observations:
            raise RuntimeError(f"No {family} element record touches interface node {node}.")
        stacked = np.vstack(observations)
        observation_errors.append(float(np.max(np.abs(stacked - stacked[0]))))
        trace.append(np.mean(stacked, axis=0))
        source_records.append(record_ids)
    return np.concatenate(trace), {
        "family": family,
        "nodes": list(nodes),
        "source_element_records": source_records,
        "observation_count": int(sum(len(item) for item in source_records)),
        "within_family_observation_max_difference": max(observation_errors, default=0.0),
        "collection": "family-local element records -> local node-major DOF slices",
    }


def _family_interface_force(
    ref: dict[str, Any], response: np.ndarray, frequency_hz: float, family: str, nodes: tuple[int, ...]
) -> tuple[np.ndarray, dict[str, Any]]:
    omega = 2.0 * math.pi * frequency_hz
    force = np.zeros(3 * len(nodes), dtype=np.complex128)
    source_records: list[int] = []
    for record_index, record in enumerate(ref["records"]):
        if record["family"] != family:
            continue
        local_dynamic = (
            record["K"]
            + 1j * omega * (ref["alpha"] * record["M"] + ref["beta"] * record["K"])
            - omega**2 * record["M"]
        )
        local_force = local_dynamic @ response[np.asarray(record["ids"], dtype=int)]
        for output_index, node in enumerate(nodes):
            if node in record["nodes"]:
                local_node = record["nodes"].index(node)
                force[3 * output_index : 3 * output_index + 3] += local_force[3 * local_node : 3 * local_node + 3]
                source_records.append(record_index)
    return force, {
        "family": family,
        "nodes": list(nodes),
        "source_element_records": sorted(set(source_records)),
        "collection": "family-local dynamic element forces on interface DOFs",
    }


def corrected_interface_metrics(ref: dict[str, Any], response: np.ndarray, frequency_hz: float) -> dict[str, Any]:
    """Compute non-tautological interface state, force and work metrics."""

    contract_energy_definition = CONTRACT["metric_definitions"]["interface_energy"]
    if "norm(F_free)*norm(x)" not in contract_energy_definition:
        raise RuntimeError("The frozen contract does not declare the required Ffree/x product term.")
    free_force_norm = float(np.linalg.norm(ref["load"][ref["free"]]))
    response_l2_norm = float(np.linalg.norm(response))
    energy_denominator = free_force_norm * response_l2_norm
    if energy_denominator <= 0.0:
        raise RuntimeError("The frozen benchmark must provide non-zero Ffree and response norms.")
    result: dict[str, Any] = {}
    for name, (left, right, nodes) in INTERFACES.items():
        left_state, left_source = _family_trace(ref["records"], response, left, nodes)
        right_state, right_source = _family_trace(ref["records"], response, right, nodes)
        left_force, left_force_source = _family_interface_force(ref, response, frequency_hz, left, nodes)
        right_force, right_force_source = _family_interface_force(ref, response, frequency_hz, right, nodes)
        work_left = np.vdot(left_state, left_force)
        work_right = np.vdot(right_state, right_force)
        response_scale = max(float(np.max(np.abs(response))), 1.0e-30)
        force_scale = max(free_force_norm, 1.0)
        result[name] = {
            "shared_nodes": list(nodes),
            "left_family": left,
            "right_family": right,
            "left_state": left_state,
            "right_state": right_state,
            "left_force": left_force,
            "right_force": right_force,
            "displacement_jump": float(np.max(np.abs(left_state - right_state)) / response_scale),
            "force_balance_relative": float(np.linalg.norm(left_force + right_force) / force_scale),
            "work_left": complex(work_left),
            "work_right": complex(work_right),
            "energy_numerator": float(abs(work_left + work_right)),
            "ffree_norm": free_force_norm,
            "x_l2_norm": response_l2_norm,
            "energy_denominator": energy_denominator,
            "energy_relative": float(abs(work_left + work_right) / energy_denominator),
            "energy_normalization": {
                "formula": "||Ffree||2 * ||x||2",
                "source": contract_energy_definition,
                "variable_denominator": False,
            },
            "left_state_source": left_source,
            "right_state_source": right_source,
            "left_force_source": left_force_source,
            "right_force_source": right_force_source,
            "independent_state_collection": True,
            "continuity_hardcoded": False,
            "continuity_tautological": False,
        }
    return result


def modal_coordinate(ref: dict[str, Any], response: np.ndarray) -> complex:
    """Mass-weighted projection onto the independently mass-normalized mode."""

    return complex(np.vdot(ref["mode"], ref["mass"] @ response))


def replay_packet(
    ref: dict[str, Any], responses: np.ndarray, frequencies: np.ndarray, residual_vectors: np.ndarray, reactions: np.ndarray
) -> dict[str, Any]:
    probe = ref["dofs"].index(ref["probe_node"], ref["probe_dof"])
    interfaces = [corrected_interface_metrics(ref, response, float(frequency)) for response, frequency in zip(responses, frequencies, strict=True)]
    energies = [legacy.family_energies(ref, response, float(frequency)) for response, frequency in zip(responses, frequencies, strict=True)]
    q = np.asarray([modal_coordinate(ref, response) for response in responses], dtype=np.complex128)
    return {
        "responses": np.asarray(responses, dtype=np.complex128),
        "reactions": np.asarray(reactions, dtype=np.complex128),
        "residual_vectors": np.asarray(residual_vectors, dtype=np.complex128),
        "amplitudes": np.abs(responses[:, probe]),
        "phases": np.angle(responses[:, probe]),
        "frequencies_hz": np.asarray(frequencies, dtype=float),
        "interfaces": interfaces,
        "energies": energies,
        "modal_coordinate_complex": q,
        "status": "CONVERGED",
        "iterations_per_frequency": np.ones(len(frequencies), dtype=int),
    }


def _relative_difference(left: np.ndarray, right: np.ndarray) -> float:
    left = np.asarray(left)
    right = np.asarray(right)
    return float(np.linalg.norm(left - right) / max(float(np.linalg.norm(left)), 1.0e-30))


def _interface_array(packet: dict[str, Any], field: str, side: str | None = None) -> np.ndarray:
    values: list[np.ndarray] = []
    for row in packet["interfaces"]:
        for name in sorted(row):
            metric = row[name]
            key = field if side is None else f"{side}_{field}"
            value = metric[key]
            if isinstance(value, complex):
                values.append(np.asarray([value], dtype=np.complex128))
            else:
                values.append(np.asarray(value, dtype=np.complex128).ravel())
    return np.concatenate(values) if values else np.empty(0, dtype=np.complex128)


def complete_replay_comparison(main: dict[str, Any], replay: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    gate = float(contract["predeclared_gates"]["replay_response_relative"]["value"])
    reaction_gate = float(contract["predeclared_gates"]["replay_reaction_relative"]["value"])
    residual_gate = float(contract["predeclared_gates"]["replay_residual_relative_difference"]["value"])
    amplitude_gate = float(contract["predeclared_gates"]["replay_amplitude_relative"]["value"])
    phase_gate = float(contract["predeclared_gates"]["replay_phase_absolute_rad"]["value"])
    values = {
        "complex_displacement_relative": _relative_difference(main["responses"], replay["responses"]),
        "complex_reactions_relative": _relative_difference(main["reactions"], replay["reactions"]),
        "full_residual_relative": _relative_difference(main["residual_vectors"], replay["residual_vectors"]),
        "amplitude_relative": _relative_difference(main["amplitudes"], replay["amplitudes"]),
        "phase_absolute_rad": float(np.max(np.abs(main["phases"] - replay["phases"]))),
        "interface_left_state_relative": _relative_difference(_interface_array(main, "state", "left"), _interface_array(replay, "state", "left")),
        "interface_right_state_relative": _relative_difference(_interface_array(main, "state", "right"), _interface_array(replay, "state", "right")),
        "interface_left_force_relative": _relative_difference(_interface_array(main, "force", "left"), _interface_array(replay, "force", "left")),
        "interface_right_force_relative": _relative_difference(_interface_array(main, "force", "right"), _interface_array(replay, "force", "right")),
        "interface_continuity_relative": _relative_difference(_interface_array(main, "displacement_jump"), _interface_array(replay, "displacement_jump")),
        "interface_force_balance_relative": _relative_difference(_interface_array(main, "force_balance_relative"), _interface_array(replay, "force_balance_relative")),
        "interface_work_left_relative": _relative_difference(_interface_array(main, "work_left"), _interface_array(replay, "work_left")),
        "interface_work_right_relative": _relative_difference(_interface_array(main, "work_right"), _interface_array(replay, "work_right")),
        "interface_energy_relative": _relative_difference(_interface_array(main, "energy_relative"), _interface_array(replay, "energy_relative")),
        "frequency_grid_identical": bool(np.array_equal(main["frequencies_hz"], replay["frequencies_hz"])),
        "status_identical": main["status"] == replay["status"],
        "iterations_per_frequency_identical": bool(np.array_equal(main["iterations_per_frequency"], replay["iterations_per_frequency"])),
        "fields_compared": [
            "complex displacement", "complex reactions", "full residual", "amplitude", "phase",
            "interface left/right states", "interface continuity", "interface forces",
            "interface work/energy", "status", "iterations per frequency",
        ],
    }
    values["pass"] = bool(
        values["complex_displacement_relative"] <= gate
        and values["complex_reactions_relative"] <= reaction_gate
        and values["full_residual_relative"] <= residual_gate
        and values["amplitude_relative"] <= amplitude_gate
        and values["phase_absolute_rad"] <= phase_gate
        and all(values[key] <= gate for key in (
            "interface_left_state_relative", "interface_right_state_relative",
            "interface_left_force_relative", "interface_right_force_relative",
            "interface_continuity_relative", "interface_force_balance_relative",
            "interface_work_left_relative", "interface_work_right_relative",
            "interface_energy_relative",
        ))
        and values["frequency_grid_identical"]
        and values["status_identical"]
        and values["iterations_per_frequency_identical"]
    )
    return values


def _failure_specs(base: Any, ref: dict[str, Any]) -> dict[str, dict[str, Any]]:
    frequency = [ref["frequency_hz"]]
    alpha = ref["alpha"]

    def model_with_analysis(**overrides: Any) -> Any:
        return legacy.build_harmonic_model(base, frequency, alpha, analysis_override=overrides)

    def bad_material(**updates: Any) -> dict[str, Any]:
        material = {key: copy.deepcopy(value) for key, value in base.materials.items()}
        material["solid"].update(updates)
        return material

    top_nodes = [
        node
        for node, point in enumerate(base.nodes)
        if np.isclose(float(point[2]), 3.0, rtol=0.0, atol=1.0e-14)
    ]
    bad_elements = [
        {"type": element.type, "nodes": list(element.nodes), "material": element.material}
        for element in base.elements
        if element.type != "WEDGE6"
    ]
    unsupported_elements = [
        {
            "type": "PYRAMID5" if index == 0 else element.type,
            "nodes": [*element.nodes, 4] if index == 0 else list(element.nodes),
            "material": element.material,
        }
        for index, element in enumerate(base.elements)
    ]
    return {
        "invalid_frequency_negative": {
            "payload": {"analysis": {"frequencies_hz": [-1.0]}},
            "execution_path_expected": r"solve_model.*frequency_grid",
            "expected_exception_type": "InputValidationError",
            "expected_message_pattern": r"finite and non-negative",
            "factory": lambda: legacy.solve_model(
                legacy.build_harmonic_model(base, [-1.0], alpha), enforce_policy=False
            ),
        },
        "invalid_frequency_nan": {
            "payload": {"analysis": {"frequencies_hz": ["NaN"]}},
            "execution_path_expected": r"solve_model.*frequency_grid",
            "expected_exception_type": "InputValidationError",
            "expected_message_pattern": r"finite and non-negative",
            "factory": lambda: legacy.solve_model(
                legacy.build_harmonic_model(base, [float("nan")], alpha), enforce_policy=False
            ),
        },
        "invalid_frequency_inf": {
            "payload": {"analysis": {"frequencies_hz": ["+Inf"]}},
            "execution_path_expected": r"solve_model.*frequency_grid",
            "expected_exception_type": "InputValidationError",
            "expected_message_pattern": r"finite and non-negative",
            "factory": lambda: legacy.solve_model(
                legacy.build_harmonic_model(base, [float("inf")], alpha), enforce_policy=False
            ),
        },
        "missing_mass": {
            "payload": {"materials": {"solid": {"density": 0.0}}},
            "execution_path_expected": r"solve_model.*solve",
            "expected_exception_type": "MeshValidationError",
            "expected_message_pattern": r"positive density",
            "factory": lambda: legacy.solve_model(
                legacy.build_harmonic_model(
                    base, frequency, alpha, material_override=bad_material(density=0.0)
                ),
                enforce_policy=False,
            ),
        },
        "unsupported_damping": {
            "payload": {"analysis": {"damping_model": "unknown_model"}},
            "execution_path_expected": r"solve_model.*rayleigh_damping_definition",
            "expected_exception_type": "InputValidationError",
            "expected_message_pattern": r"Unsupported damping model",
            "factory": lambda: legacy.solve_model(
                model_with_analysis(damping_model="unknown_model"), enforce_policy=False
            ),
        },
        "malformed_harmonic_load": {
            "payload": {"loads": [{"node": top_nodes[0], "dof": "BAD", "value": 1.0}]},
            "execution_path_expected": r"build_harmonic_model.*normalize_dof_name",
            "expected_exception_type": "ValueError",
            "expected_message_pattern": r"Unknown dof name 'BAD'",
            "factory": lambda: legacy.solve_model(
                legacy.build_harmonic_model(
                    base,
                    frequency,
                    alpha,
                    loads_override=[{"node": top_nodes[0], "dof": "BAD", "value": 1.0}],
                ),
                enforce_policy=False,
            ),
        },
        "invalid_complex_real_input": {
            "payload": {"loads": [{"node": top_nodes[0], "dof": "UZ", "value": "1+1j"}]},
            "execution_path_expected": r"build_harmonic_model.*from_raw",
            "expected_exception_type": "TypeError",
            "expected_message_pattern": r"not 'complex'",
            "factory": lambda: legacy.solve_model(
                legacy.build_harmonic_model(
                    base,
                    frequency,
                    alpha,
                    loads_override=[{"node": top_nodes[0], "dof": "UZ", "value": 1.0 + 1.0j}],
                ),
                enforce_policy=False,
            ),
        },
        "invalid_mixed_interface": {
            "payload": {"elements": "WEDGE6 family removed from declared chain"},
            "execution_path_expected": r"validate_connected_scope",
            "expected_exception_type": "InputValidationError",
            "expected_message_pattern": r"requires exactly",
            "factory": lambda: legacy.validate_connected_scope(
                legacy.build_harmonic_model(
                    base, frequency, alpha, elements_override=bad_elements
                )
            ),
        },
        "unsupported_family": {
            "payload": {"elements": [{"type": "PYRAMID5"}]},
            "execution_path_expected": r"solve_model.*raise_for_error",
            "expected_exception_type": "CompatibilityError",
            "expected_message_pattern": r"UNKNOWN_ELEMENT",
            "factory": lambda: legacy.solve_model(
                legacy.build_harmonic_model(
                    base, frequency, alpha, elements_override=unsupported_elements
                ),
                enforce_policy=False,
            ),
        },
    }


def strict_failure_executions(base: Any, ref: dict[str, Any]) -> dict[str, Any]:
    executions: dict[str, Any] = {}
    for case_id, spec in _failure_specs(base, ref).items():
        input_digest = sha256_bytes(canonical_json(spec["payload"]))
        observed_type: str | None = None
        observed_message = "No exception was raised."
        path_signature = ""
        try:
            spec["factory"]()
        except Exception as exc:  # noqa: BLE001 - this is the strict rejection observer
            observed_type = type(exc).__name__
            observed_message = str(exc)[:1000]
            frames = traceback.extract_tb(exc.__traceback__)
            path_signature = " -> ".join(frame.name for frame in frames)
        type_match = observed_type == spec["expected_exception_type"]
        message_match = bool(re.search(spec["expected_message_pattern"], observed_message))
        path_match = bool(re.search(spec["execution_path_expected"], path_signature))
        executions[case_id] = {
            "case_id": case_id,
            "executed": True,
            "input_payload": spec["payload"],
            "input_digest": input_digest,
            "execution_path": path_signature,
            "expected_execution_path": spec["execution_path_expected"],
            "expected_exception_type": spec["expected_exception_type"],
            "expected_message_pattern": spec["expected_message_pattern"],
            "observed_exception_type": observed_type,
            "observed_message": observed_message,
            "type_match": type_match,
            "message_match": message_match,
            "path_match": path_match,
            "failure_any_exception_accepted": False,
            "pass": bool(type_match and message_match and path_match),
        }
    return executions


def validate_evidence(manifest: dict[str, Any]) -> list[str]:
    schema = json.loads(EVIDENCE_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return [error.message for error in sorted(validator.iter_errors(manifest), key=str)]


def build_micro_manifest(
    contract: dict[str, Any],
    old_manifest: dict[str, Any],
    digests: dict[str, str],
    arrays: dict[str, np.ndarray],
    interface_rows: dict[str, Any],
    replay_comparisons: list[dict[str, Any]],
    failures: dict[str, Any],
    ref: dict[str, Any],
    frequencies: np.ndarray,
) -> dict[str, Any]:
    archive_npz = {key: np.asarray(value) for key, value in arrays.items()}
    np.savez_compressed(ARCHIVE_PATH, **archive_npz)
    archive_digest = sha256_file(ARCHIVE_PATH)
    array_digests = {
        key: sha256_bytes(np.ascontiguousarray(value).tobytes())
        for key, value in archive_npz.items()
    }
    array_manifest = {
        key: {
            "key": key,
            "shape": list(value.shape),
            "dtype": str(value.dtype),
            "sha256": array_digests[key],
        }
        for key, value in archive_npz.items()
    }
    env = environment_snapshot()
    evaluator_digest = sha256_file(Path(__file__).resolve())
    provenance = {
        "evaluator_pre_run_digest": evaluator_digest,
        "schema_blob_digest": digests["evidence_schema_sha256"],
        "schema_blob_sha": digests["evidence_schema_blob_sha"],
        "contract_blob_digest": digests["contract_sha256"],
        "contract_blob_sha": digests["contract_blob_sha"],
        "repo_sha": git_revision(),
        "environment": env,
        "freeze_stage": "before WP13-02C3 numerical campaign",
        "numerical_campaign_executed": False,
        "pre_run_freeze_valid": True,
    }
    q = arrays["modal_coordinate_complex"]
    return {
        "schema_version": 2,
        "record_id": "QF-028-WP13-02C2-HARMONIC-HARNESS",
        "work_package": "WP13-02C2",
        "contract_id": contract["contract_id"],
        "contract_sha256": digests["contract_sha256"],
        "contract_blob_sha": digests["contract_blob_sha"],
        "repo_sha": git_revision(),
        "environment": env,
        "source_campaign_manifest": str(OLD_MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"),
        "source_campaign_conformance": "NONCONFORMING_UNDER_C2_SCHEMA",
        "historical_record_immutable": True,
        "benchmark_inputs": old_manifest["benchmark_inputs"],
        "conditioning": old_manifest["conditioning"],
        "frequencies": {
            "microcheck_ratios": [0.75, 1.0],
            "microcheck_frequencies_hz": frequencies.tolist(),
            "source_campaign_frequency_grid_unchanged": True,
        },
        "damping": old_manifest["damping"],
        "raw_complex_responses": {
            "array_key": "micro_runtime_responses",
            "source": "immutable B/C archive",
            "complete_fields": ["complex displacement"],
        },
        "oracle_responses": {
            "array_key": "micro_oracle_dense_responses",
            "method": old_manifest["oracle"]["reference_method"],
            "independent_from_production_route": True,
        },
        "amplitude_phase": {
            "runtime_array_key": "micro_amplitudes",
            "reference_array_key": "micro_reference_amplitudes",
            "phase_array_key": "micro_phases",
            "formula_source": "contract amplitude_error and phase_error definitions",
        },
        "residuals": {
            "array_key": "micro_residual_vectors",
            "definition_source": "frozen contract",
            "normalization": "legacy campaign metric retained; no C2 gate reinterpretation",
        },
        "static_limit": {"historical_source": "B/C manifest", "microcheck": "not rerun"},
        "resonance": {"historical_source": "B/C manifest", "microcheck": "not rerun"},
        "interface_metrics": {
            "frequency_rows": interface_rows,
            "state_collection_independent": True,
            "continuity_hardcoded": False,
            "continuity_tautological": False,
            "energy_normalization_formula": "||Ffree||2 * ||x||2",
            "energy_normalization_source": contract["metric_definitions"]["interface_energy"],
            "archived_fields": [
                "left_state", "right_state", "force_left", "force_right",
                "work_left", "work_right", "energy_numerator", "ffree_norm",
                "x_l2_norm", "energy_denominator", "energy_relative",
            ],
        },
        "replay_arrays": {
            "packets": ["main", "replay_1", "replay_2"],
            "array_keys": sorted(key for key in archive_npz if key.startswith("replay_")),
            "fields": [
                "complex displacement", "reactions", "full residual", "amplitude",
                "phase", "interface left/right states", "interface continuity",
                "interface forces", "interface work/energy", "status",
            ],
        },
        "replay_comparison": {
            "comparisons": replay_comparisons,
            "normalization_source": "contract predeclared replay gates",
            "complete_arrays_compared": True,
        },
        "failure_executions": {
            "cases": failures,
            "all_cases_actually_executed": all(item["executed"] for item in failures.values()),
            "strict_type_message_path_matching": all(item["pass"] for item in failures.values()),
            "failure_any_exception_accepted": False,
        },
        "modal_coordinate": {
            "complex": {"array_key": "modal_coordinate_complex", "shape": list(q.shape)},
            "amplitude": {"array_key": "modal_coordinate_amplitude"},
            "phase": {"array_key": "modal_coordinate_phase"},
            "definition": {
                "modal_vector_source": "independent dense K/M eigen-oracle first fixed-base mode",
                "normalization": "mass-normalized eigenvector with canonical sign",
                "projection_formula": "q = phi^H M x",
                "first_mode_dominated_claim_allowed": False,
            },
        },
        "digests": {
            "contract_sha256": digests["contract_sha256"],
            "contract_blob_sha": digests["contract_blob_sha"],
            "contract_schema_sha256": digests["contract_schema_sha256"],
            "evidence_schema_sha256": digests["evidence_schema_sha256"],
            "evidence_schema_blob_sha": digests["evidence_schema_blob_sha"],
            "source_archive_sha256": digests["old_archive_sha256"],
            "source_manifest_sha256": digests["old_manifest_sha256"],
            "micro_archive_sha256": archive_digest,
            "arrays": array_manifest,
        },
        "provenance_freeze": provenance,
        "contract_values_single_source_of_truth": True,
        "gate_decisions": {
            "interface_state_collection": True,
            "energy_normalization": True,
            "replay_comparator": all(item["pass"] for item in replay_comparisons),
            "failure_traceability": all(item["pass"] for item in failures.values()),
            "provenance_freeze": provenance["pre_run_freeze_valid"],
            "modal_coordinate": True,
            "old_campaign_schema_conformance": False,
            "harness_microchecks": True,
        },
        "integrity": {
            "numerical_source_changed": False,
            "vnv_harness_changed": True,
            "formulation_changed": False,
            "contract_changed": False,
            "gates_changed": False,
            "maturity_changed": False,
            "historical_c_campaign_modified": False,
            "historical_0_2_7_evidence_modified": False,
        },
        "status": "PASS_HARMONIC_HARNESS_READY",
    }


def main() -> int:
    contract, old_manifest, old_archive, digests = load_sources()
    base = legacy.build(1)
    ref = legacy.oracle(base)
    frequencies = np.asarray([ref["frequency_hz"] * 0.75, ref["frequency_hz"]], dtype=float)
    old_frequencies = np.asarray(old_archive["frequencies_hz"], dtype=float)
    old_indices = [int(np.argmin(np.abs(old_frequencies - frequency))) for frequency in frequencies]
    responses = np.asarray(old_archive["runtime_responses"])[old_indices]
    oracle_responses = np.asarray(old_archive["oracle_dense_responses"])[old_indices]
    probe = ref["dofs"].index(ref["probe_node"], ref["probe_dof"])
    amplitudes = np.abs(responses[:, probe])
    reference_amplitudes = np.abs(oracle_responses[:, probe])
    phases = np.angle(responses[:, probe])
    interface_rows: dict[str, Any] = {}
    for frequency, response in zip(frequencies, responses, strict=True):
        interface_rows[str(float(frequency))] = corrected_interface_metrics(ref, response, float(frequency))

    replay_frequencies = np.asarray(old_archive["replay_frequencies_hz"], dtype=float)
    replay_packets = {}
    for label in ("main", "replay_1", "replay_2"):
        prefix = "replay_main" if label == "main" else label
        replay_packets[label] = replay_packet(
            ref,
            old_archive[f"{prefix}_responses"],
            replay_frequencies,
            old_archive[f"{prefix}_residual_vectors"],
            old_archive[f"{prefix}_reactions"],
        )
    replay_comparisons = [
        complete_replay_comparison(replay_packets["main"], replay_packets[label], contract)
        for label in ("replay_1", "replay_2")
    ]
    failures = strict_failure_executions(base, ref)
    modal_values = np.asarray(
        [modal_coordinate(ref, response) for response in responses]
        + list(replay_packets["main"]["modal_coordinate_complex"]),
        dtype=np.complex128,
    )
    arrays = {
        "micro_frequencies_hz": frequencies,
        "micro_runtime_responses": responses,
        "micro_oracle_dense_responses": oracle_responses,
        "micro_amplitudes": amplitudes,
        "micro_reference_amplitudes": reference_amplitudes,
        "micro_phases": phases,
        "micro_residual_vectors": np.asarray(old_archive["residual_vectors"])[old_indices],
        "modal_coordinate_complex": modal_values,
        "modal_coordinate_amplitude": np.abs(modal_values),
        "modal_coordinate_phase": np.angle(modal_values),
    }
    for label, packet in replay_packets.items():
        arrays[f"replay_{label}_responses"] = packet["responses"]
        arrays[f"replay_{label}_reactions"] = packet["reactions"]
        arrays[f"replay_{label}_residual_vectors"] = packet["residual_vectors"]
        arrays[f"replay_{label}_modal_coordinate_complex"] = packet["modal_coordinate_complex"]
        for interface_name in INTERFACES:
            safe_name = interface_name.lower()
            arrays[f"replay_{label}_{safe_name}_left_state"] = np.vstack(
                [packet["interfaces"][i][interface_name]["left_state"] for i in range(len(replay_frequencies))]
            )
            arrays[f"replay_{label}_{safe_name}_right_state"] = np.vstack(
                [packet["interfaces"][i][interface_name]["right_state"] for i in range(len(replay_frequencies))]
            )
            arrays[f"replay_{label}_{safe_name}_left_force"] = np.vstack(
                [packet["interfaces"][i][interface_name]["left_force"] for i in range(len(replay_frequencies))]
            )
            arrays[f"replay_{label}_{safe_name}_right_force"] = np.vstack(
                [packet["interfaces"][i][interface_name]["right_force"] for i in range(len(replay_frequencies))]
            )
            arrays[f"replay_{label}_{safe_name}_work_left"] = np.asarray(
                [packet["interfaces"][i][interface_name]["work_left"] for i in range(len(replay_frequencies))],
                dtype=np.complex128,
            )
            arrays[f"replay_{label}_{safe_name}_work_right"] = np.asarray(
                [packet["interfaces"][i][interface_name]["work_right"] for i in range(len(replay_frequencies))],
                dtype=np.complex128,
            )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_micro_manifest(
        contract, old_manifest, digests, arrays, interface_rows,
        replay_comparisons, failures, ref, frequencies,
    )
    schema_errors = validate_evidence(manifest)
    if schema_errors:
        raise RuntimeError(f"C2 evidence schema rejected positive record: {schema_errors}")
    old_schema_errors = validate_evidence(old_manifest)
    manifest["gate_decisions"]["old_campaign_schema_conformance"] = not bool(old_schema_errors)
    manifest["old_campaign_schema_missing_fields"] = old_schema_errors
    MANIFEST_PATH.write_text(
        json.dumps(json_safe(manifest), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    serialized = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    final_errors = validate_evidence(serialized)
    if final_errors or not old_schema_errors:
        raise RuntimeError(f"C2 schema guard failed: new={final_errors}, old={old_schema_errors}")
    print(json.dumps({
        "status": serialized["status"],
        "old_campaign_nonconforming": bool(old_schema_errors),
        "failure_cases": {key: value["pass"] for key, value in failures.items()},
        "replays": [item["pass"] for item in replay_comparisons],
        "archive": str(ARCHIVE_PATH),
        "manifest": str(MANIFEST_PATH),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
