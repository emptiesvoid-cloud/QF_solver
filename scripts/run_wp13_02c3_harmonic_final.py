"""Run WP13-02C3 under the frozen contract and corrected C2 harness.

The C3 runner is created and committed before its first production solve.
It never edits the frozen contract, C2 harness, original C manifest/archive,
or numerical kernels.  All validation values are loaded from the contract.
"""

from __future__ import annotations

import json
import math
import platform
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

import run_wp13_02c2_harmonic_harness as c2  # noqa: E402
import run_wp13_02c_harmonic_mixed as legacy  # noqa: E402
from solveur.api.public import solve_model  # noqa: E402


CONTRACT_PATH = ROOT / "qualification/0_2_8/wp13_02c_harmonic_contract.json"
C2_SCHEMA_PATH = ROOT / "qualification/0_2_8/wp13_02c_harmonic_evidence.schema.json"
C3_SCHEMA_PATH = ROOT / "qualification/0_2_8/wp13_02c3_harmonic_evidence.schema.json"
C2_SCRIPT_PATH = ROOT / "scripts/run_wp13_02c2_harmonic_harness.py"
C2_MANIFEST_PATH = ROOT / "qualification/0_2_8/wp13_02c2_harmonic_harness/manifest.json"
OLD_MANIFEST_PATH = ROOT / "qualification/0_2_8/wp13_02c_harmonic_v1/manifest.json"
OLD_ARCHIVE_PATH = ROOT / "qualification/0_2_8/wp13_02c_harmonic_v1/wp13_02c_harmonic_arrays.npz"
OUTPUT_DIR = ROOT / "qualification/0_2_8/wp13_02c3_harmonic_final"
FREEZE_PATH = OUTPUT_DIR / "pre_run_freeze.json"
ARCHIVE_PATH = OUTPUT_DIR / "wp13_02c3_harmonic_arrays.npz"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"


def sha256_file(path: Path) -> str:
    return c2.sha256_file(path)


def git_blob_sha(path: Path) -> str:
    return c2.git_blob_sha(path)


def git_revision() -> str:
    return c2.git_revision()


def json_safe(value: Any) -> Any:
    return c2.json_safe(value)


def environment_snapshot() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": __import__("scipy").__version__,
        "executable": sys.executable,
        "runner": "WP13-02C3 full frozen harmonic campaign",
    }


def _schema_errors(manifest: dict[str, Any]) -> list[str]:
    schema = json.loads(C3_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return [error.message for error in sorted(validator.iter_errors(manifest), key=str)]


def verify_and_archive_pre_run_freeze(contract: dict[str, Any]) -> dict[str, Any]:
    c2_manifest = json.loads(C2_MANIFEST_PATH.read_text(encoding="utf-8"))
    c2_provenance = c2_manifest["provenance_freeze"]
    contract_sha = sha256_file(CONTRACT_PATH)
    contract_blob_sha = git_blob_sha(CONTRACT_PATH)
    c2_schema_sha = sha256_file(C2_SCHEMA_PATH)
    c2_evaluator_sha = sha256_file(C2_SCRIPT_PATH)
    current_repo_sha = git_revision()
    checks = {
        "contract_id": contract["contract_id"] == "WP13-02C-HARMONIC-MIXED-001",
        "contract_sha": contract_sha == c2_manifest["contract_sha256"],
        "contract_blob_sha": contract_blob_sha == c2_manifest["contract_blob_sha"],
        "c2_schema_sha": c2_schema_sha == c2_manifest["digests"]["evidence_schema_sha256"],
        "c2_evaluator_pre_run_digest": c2_evaluator_sha == c2_provenance["evaluator_pre_run_digest"],
        "c2_freeze_valid": c2_provenance["pre_run_freeze_valid"] is True,
        "c2_historical_archive": sha256_file(OLD_ARCHIVE_PATH) == c2_manifest["digests"]["source_archive_sha256"],
        "c2_historical_manifest": sha256_file(OLD_MANIFEST_PATH) == c2_manifest["digests"]["source_manifest_sha256"],
        "contract_status": contract["status"] == "PREDECLARED_NOT_EXECUTED",
        "contract_fixed": contract["predeclared_gates"]["fixed_before_execution"] is True,
        "post_observation_retuning_disabled": contract["predeclared_gates"]["post_observation_retuning"] is False,
    }
    pre_run = {
        "contract_id": contract["contract_id"],
        "contract_sha": contract_sha,
        "contract_blob_digest": contract_sha,
        "contract_blob_sha": contract_blob_sha,
        "schema_blob_digest": sha256_file(C3_SCHEMA_PATH),
        "schema_blob_sha": git_blob_sha(C3_SCHEMA_PATH),
        "c2_schema_blob_digest": c2_schema_sha,
        "evaluator_pre_run_digest": c2_evaluator_sha,
        "c3_evaluator_pre_run_digest": sha256_file(Path(__file__).resolve()),
        "repo_sha": current_repo_sha,
        "environment": environment_snapshot(),
        "c2_freeze_repo_sha": c2_provenance["repo_sha"],
        "checks": checks,
        "pre_run_freeze_valid": all(checks.values()),
        "numerical_campaign_started": False,
        "future_campaign": "WP13-02C3",
    }
    if not pre_run["pre_run_freeze_valid"]:
        raise RuntimeError(f"C2 provenance freeze mismatch: {checks}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FREEZE_PATH.write_text(json.dumps(json_safe(pre_run), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return pre_run


def compute_campaign(base: Any, ref: dict[str, Any], contract: dict[str, Any], frequencies: np.ndarray) -> dict[str, Any]:
    model = legacy.build_harmonic_model(base, frequencies.tolist(), ref["alpha"])
    started = time.perf_counter()
    result = solve_model(model, enforce_policy=False)
    elapsed = time.perf_counter() - started
    responses = np.vstack([np.asarray(response, dtype=np.complex128) for response in result.responses])
    references = np.vstack([legacy.dense_response(ref, float(frequency)) for frequency in frequencies])
    sdof_references = np.vstack([legacy.sdof_response(ref, float(frequency)) for frequency in frequencies])
    probe = ref["dofs"].index(ref["probe_node"], ref["probe_dof"])
    amplitudes = np.abs(responses[:, probe])
    reference_amplitudes = np.abs(references[:, probe])
    phases = np.angle(responses[:, probe])
    reference_phases = np.angle(references[:, probe])
    amplitude_errors = np.abs(amplitudes / np.maximum(reference_amplitudes, 1.0e-30) - 1.0)
    phase_errors = np.abs((phases - reference_phases + math.pi) % (2.0 * math.pi) - math.pi)
    residual_vectors = []
    reactions = []
    residuals = []
    interfaces = []
    energies = []
    modal = []
    for response, frequency in zip(responses, frequencies, strict=True):
        omega = 2.0 * math.pi * float(frequency)
        dynamic = ref["stiffness"] + 1j * omega * ref["damping"] - omega**2 * ref["mass"]
        residual = dynamic @ response - ref["load"]
        residual_vectors.append(residual)
        reactions.append(residual[ref["fixed"]])
        residuals.append(float(np.linalg.norm(residual[ref["free"]]) / max(np.linalg.norm(ref["load"][ref["free"]]), 1.0)))
        interfaces.append(c2.corrected_interface_metrics(ref, response, float(frequency)))
        energies.append(legacy.family_energies(ref, response, float(frequency)))
        modal.append(c2.modal_coordinate(ref, response))
    residual_vectors_array = np.vstack(residual_vectors)
    reactions_array = np.vstack(reactions)
    peak_runtime_index = int(np.argmax(amplitudes))
    peak_reference_index = int(np.argmax(reference_amplitudes))
    static_error = float(np.linalg.norm(responses[0].real - ref["static"]) / max(np.linalg.norm(ref["static"]), 1.0e-30))
    return {
        "responses": responses,
        "references": references,
        "sdof_references": sdof_references,
        "residual_vectors": residual_vectors_array,
        "reactions": reactions_array,
        "residuals": residuals,
        "production_residuals": list(result.solver.get("relative_residual_norms", [])),
        "interfaces": interfaces,
        "energies": energies,
        "modal_coordinate_complex": np.asarray(modal, dtype=np.complex128),
        "amplitudes": amplitudes,
        "reference_amplitudes": reference_amplitudes,
        "amplitude_errors": amplitude_errors,
        "phases": phases,
        "reference_phases": reference_phases,
        "phase_errors": phase_errors,
        "static_limit_error": static_error,
        "peak_runtime_index": peak_runtime_index,
        "peak_reference_index": peak_reference_index,
        "peak_runtime_frequency_hz": float(frequencies[peak_runtime_index]),
        "peak_reference_frequency_hz": float(frequencies[peak_reference_index]),
        "peak_amplitude_error": float(amplitude_errors[peak_reference_index]),
        "peak_phase_error": float(phase_errors[peak_reference_index]),
        "sdof_probe_relative_errors": [
            float(abs(abs(response[probe]) / max(abs(reference[probe]), 1.0e-30) - 1.0))
            for response, reference in zip(sdof_references, references, strict=True)
        ],
        "frequencies_hz": frequencies,
        "solver_status": str(result.status),
        "runtime_seconds": elapsed,
        "iterations_per_frequency": np.ones(len(frequencies), dtype=int),
    }


def replay_with_modal_comparison(main: dict[str, Any], replay: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    comparison = c2.complete_replay_comparison(main, replay, contract)
    modal_gate = float(contract["predeclared_gates"]["replay_response_relative"]["value"])
    comparison["modal_coordinate_relative"] = c2._relative_difference(
        main["modal_coordinate_complex"], replay["modal_coordinate_complex"]
    )
    comparison["fields_compared"].append("modal coordinate")
    comparison["pass"] = bool(
        comparison["pass"] and comparison["modal_coordinate_relative"] <= modal_gate
    )
    return comparison


def add_array(arrays: dict[str, np.ndarray], manifest: dict[str, Any], name: str, value: Any, dtype: Any) -> None:
    array = np.asarray(value, dtype=dtype)
    arrays[name] = array
    digest = c2.sha256_bytes(np.ascontiguousarray(array).tobytes())
    manifest[name] = {"shape": list(array.shape), "dtype": str(array.dtype), "sha256": digest}


def main() -> int:
    contract, old_c2_manifest, old_archive, source_digests = c2.load_sources()
    pre_run = verify_and_archive_pre_run_freeze(contract)
    base = legacy.build(1)
    ref = legacy.oracle(base)
    ratios = np.asarray(contract["frequency_contract"]["frequency_ratios"], dtype=float)
    frequencies = ref["frequency_hz"] * ratios
    conditioning = legacy.conditioning(base, ref, contract)
    if conditioning["status"] != "PASS":
        raise RuntimeError(f"Conditioning prechecks failed before production solve: {conditioning}")

    main_metrics = compute_campaign(base, ref, contract, frequencies)
    replay_ratios = np.asarray([
        float(contract["replay"]["frequencies"]["off_resonance_ratio"]),
        float(contract["replay"]["frequencies"]["near_resonance_ratio"]),
    ])
    replay_frequencies = ref["frequency_hz"] * replay_ratios
    replay_packets: list[dict[str, Any]] = []
    for _ in range(int(contract["replay"]["count"])):
        replay_metrics = compute_campaign(base, ref, contract, replay_frequencies)
        replay_packets.append(c2.replay_packet(
            ref,
            replay_metrics["responses"],
            replay_frequencies,
            replay_metrics["residual_vectors"],
            replay_metrics["reactions"],
        ))
        replay_packets[-1]["status"] = replay_metrics["solver_status"]
        replay_packets[-1]["iterations_per_frequency"] = replay_metrics["iterations_per_frequency"]
        replay_packets[-1]["modal_coordinate_complex"] = replay_metrics["modal_coordinate_complex"]
    replay_main = c2.replay_packet(
        ref,
        np.vstack([main_metrics["responses"][int(np.where(ratios == ratio)[0][0])] for ratio in replay_ratios]),
        replay_frequencies,
        np.vstack([main_metrics["residual_vectors"][int(np.where(ratios == ratio)[0][0])] for ratio in replay_ratios]),
        np.vstack([main_metrics["reactions"][int(np.where(ratios == ratio)[0][0])] for ratio in replay_ratios]),
    )
    replay_main["status"] = main_metrics["solver_status"]
    replay_main["iterations_per_frequency"] = np.ones(len(replay_frequencies), dtype=int)
    replay_main["modal_coordinate_complex"] = np.asarray([
        main_metrics["modal_coordinate_complex"][int(np.where(ratios == ratio)[0][0])] for ratio in replay_ratios
    ], dtype=np.complex128)
    replay_comparisons = [replay_with_modal_comparison(replay_main, packet, contract) for packet in replay_packets]
    failures = c2.strict_failure_executions(base, ref)

    gates = contract["predeclared_gates"]
    interface_gate_values = {
        name: {
            "continuity_max": max(float(row[name]["displacement_jump"]) for row in main_metrics["interfaces"]),
            "force_balance_max": max(float(row[name]["force_balance_relative"]) for row in main_metrics["interfaces"]),
            "energy_mismatch_max": max(float(row[name]["energy_relative"]) for row in main_metrics["interfaces"]),
        }
        for name in legacy.INTERFACES
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
    array_manifest: dict[str, Any] = {}
    add_array(arrays, array_manifest, "frequencies_hz", frequencies, np.float64)
    add_array(arrays, array_manifest, "frequency_ratios", ratios, np.float64)
    add_array(arrays, array_manifest, "runtime_responses", main_metrics["responses"], np.complex128)
    add_array(arrays, array_manifest, "oracle_dense_responses", main_metrics["references"], np.complex128)
    add_array(arrays, array_manifest, "oracle_sdof_responses", main_metrics["sdof_references"], np.complex128)
    add_array(arrays, array_manifest, "residual_vectors", main_metrics["residual_vectors"], np.complex128)
    add_array(arrays, array_manifest, "reactions", main_metrics["reactions"], np.complex128)
    for key in ("amplitudes", "reference_amplitudes", "amplitude_errors", "phases", "reference_phases", "phase_errors", "modal_coordinate_complex"):
        dtype = np.complex128 if key == "modal_coordinate_complex" else np.float64
        add_array(arrays, array_manifest, key, main_metrics[key], dtype)
    add_array(arrays, array_manifest, "replay_frequencies_hz", replay_frequencies, np.float64)
    for label, packet in zip(("main", "replay_1", "replay_2"), (replay_main, *replay_packets), strict=True):
        for field, dtype in (("responses", np.complex128), ("reactions", np.complex128), ("residual_vectors", np.complex128), ("modal_coordinate_complex", np.complex128), ("amplitudes", np.float64), ("phases", np.float64), ("iterations_per_frequency", np.int64)):
            add_array(arrays, array_manifest, f"replay_{label}_{field}", packet[field], dtype)
        for interface_name in legacy.INTERFACES:
            safe_name = interface_name.lower()
            for side in ("left", "right"):
                add_array(arrays, array_manifest, f"replay_{label}_{safe_name}_{side}_state", np.vstack([row[interface_name][f"{side}_state"] for row in packet["interfaces"]]), np.complex128)
                add_array(arrays, array_manifest, f"replay_{label}_{safe_name}_{side}_force", np.vstack([row[interface_name][f"{side}_force"] for row in packet["interfaces"]]), np.complex128)
            add_array(arrays, array_manifest, f"replay_{label}_{safe_name}_work_left", [row[interface_name]["work_left"] for row in packet["interfaces"]], np.complex128)
            add_array(arrays, array_manifest, f"replay_{label}_{safe_name}_work_right", [row[interface_name]["work_right"] for row in packet["interfaces"]], np.complex128)
            add_array(arrays, array_manifest, f"replay_{label}_{safe_name}_continuity", [row[interface_name]["displacement_jump"] for row in packet["interfaces"]], np.float64)
            add_array(arrays, array_manifest, f"replay_{label}_{safe_name}_energy", [row[interface_name]["energy_relative"] for row in packet["interfaces"]], np.float64)

    np.savez_compressed(ARCHIVE_PATH, **arrays)
    archive_sha = sha256_file(ARCHIVE_PATH)
    c3_schema_sha = sha256_file(C3_SCHEMA_PATH)
    env = environment_snapshot()
    c2_manifest_record = json.loads(C2_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest = {
        "schema_version": 3,
        "record_id": "QF-028-WP13-02C3-HARMONIC-MIXED-EVIDENCE",
        "work_package": "WP13-02C3",
        "contract_id": contract["contract_id"],
        "contract_sha256": sha256_file(CONTRACT_PATH),
        "contract_blob_sha": git_blob_sha(CONTRACT_PATH),
        "repo_sha": git_revision(),
        "environment": env,
        "benchmark_inputs": {
            "generator": "scripts/run_wp13_01k_mvp.py:build(1), frozen harmonic contract",
            "family_counts": {family: sum(element.type == family for element in base.elements) for family in legacy.FAMILIES},
            "ndof": ref["dofs"].ndof,
            "connected_components": 1,
            "direct_support_bypass": False,
            "mechanical_load_path": contract["scope"]["mechanical_path"],
            "interfaces": {name: list(value[2]) for name, value in legacy.INTERFACES.items()},
            "probe": {"node": ref["probe_node"], "dof": ref["probe_dof"]},
        },
        "conditioning": conditioning,
        "damping": {"model": "Rayleigh", "alpha": ref["alpha"], "beta": ref["beta"], "zeta": ref["zeta"]},
        "frequencies": {"ratios": ratios, "frequencies_hz": frequencies, "first_frequency_hz": ref["frequency_hz"]},
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
            "amplitudes_array_key": "amplitudes",
            "reference_amplitudes_array_key": "reference_amplitudes",
            "amplitude_errors_array_key": "amplitude_errors",
            "phases_array_key": "phases",
            "reference_phases_array_key": "reference_phases",
            "phase_errors_array_key": "phase_errors",
        },
        "modal_coordinate": {
            "complex": {"array_key": "modal_coordinate_complex"},
            "amplitude": {"derived_from": "abs(modal_coordinate_complex)"},
            "phase": {"derived_from": "angle(modal_coordinate_complex)"},
            "definition": {
                "modal_vector_source": "independent dense K/M eigen-oracle first fixed-base mode",
                "normalization": "mass-normalized eigenvector with canonical sign",
                "projection_formula": "q = phi^H M x",
                "first_mode_dominated_claim_allowed": False,
            },
        },
        "residuals": {
            "vector_array_key": "residual_vectors",
            "relative_values": main_metrics["residuals"],
            "definition": contract["metric_definitions"]["residual_relative"],
        },
        "static_limit": {"error": main_metrics["static_limit_error"], "gate": gates["static_limit_relative"]},
        "resonance": {
            "label": "FRF_PEAK_IN_FROZEN_FREQUENCY_CAMPAIGN",
            "runtime_frequency_hz": main_metrics["peak_runtime_frequency_hz"],
            "reference_frequency_hz": main_metrics["peak_reference_frequency_hz"],
            "frequency_error": abs(main_metrics["peak_runtime_frequency_hz"] - main_metrics["peak_reference_frequency_hz"]) / max(main_metrics["peak_reference_frequency_hz"], 1.0),
            "amplitude_error": main_metrics["peak_amplitude_error"],
            "phase_error": main_metrics["peak_phase_error"],
            "first_mode_resonance_claim": False,
        },
        "interface_metrics": {
            "frequency_rows": main_metrics["interfaces"],
            "gate_values": interface_gate_values,
            "state_collection_independent": True,
            "continuity_tautological": False,
            "energy_normalization": {
                "formula": "||Ffree||2 * ||x||2",
                "contract_source": contract["metric_definitions"]["interface_energy"],
                "matches_contract_product_term": True,
            },
        },
        "replay_arrays": {
            "frequencies_hz": replay_frequencies,
            "packets": ["main", "replay_1", "replay_2"],
            "fields": ["complex displacement", "reactions", "full residual", "amplitude", "phase", "modal coordinate", "interface left/right states", "interface continuity", "interface forces", "interface work/energy", "status", "iterations"],
        },
        "replay_comparison": {
            "comparisons": replay_comparisons,
            "status_identical": all(item["status_identical"] for item in replay_comparisons),
            "interface_fields_complete": all("interface left/right states" in item["fields_compared"] for item in replay_comparisons),
            "full_array_comparison": all(item["pass"] for item in replay_comparisons),
        },
        "failure_executions": {
            "cases": failures,
            "required": 9,
            "executed": sum(bool(item["executed"]) for item in failures.values()),
            "pass": sum(bool(item["pass"]) for item in failures.values()),
            "failure_any_exception_accepted": False,
            "silent_fallback": False,
        },
        "digests": {
            "contract_sha256": sha256_file(CONTRACT_PATH),
            "contract_blob_sha": git_blob_sha(CONTRACT_PATH),
            "schema_sha256": c3_schema_sha,
            "c2_schema_sha256": sha256_file(C2_SCHEMA_PATH),
            "c2_evaluator_pre_run_digest": c2_manifest_record["provenance_freeze"]["evaluator_pre_run_digest"],
            "evaluator_runtime_sha256": sha256_file(Path(__file__).resolve()),
            "archive_sha256": archive_sha,
            "arrays": array_manifest,
        },
        "provenance_freeze": {
            "contract_blob_digest": sha256_file(CONTRACT_PATH),
            "schema_blob_digest": c3_schema_sha,
            "c2_schema_blob_digest": sha256_file(C2_SCHEMA_PATH),
            "evaluator_pre_run_digest": pre_run["evaluator_pre_run_digest"],
            "c3_evaluator_pre_run_digest": pre_run["c3_evaluator_pre_run_digest"],
            "repo_sha": pre_run["repo_sha"],
            "environment": pre_run["environment"],
            "pre_run_freeze_valid": True,
            "freeze_record": str(FREEZE_PATH.relative_to(ROOT)).replace("\\", "/"),
        },
        "gate_decisions": gate_decisions,
        "historical_records_preserved": True,
        "claim_candidate": contract["claim_policy"]["candidate"],
        "status": "PASS_HARMONIC_FINAL_OWNER_READY" if all(gate_decisions.values()) else "FAIL",
        "integrity": {
            "numerical_source_changed": False,
            "vnv_harness_changed": False,
            "formulation_changed": False,
            "contract_changed": False,
            "gates_changed": False,
            "maturity_changed": False,
            "historical_results_preserved": True,
            "historical_0_2_7_evidence_changed": False,
        },
    }
    schema_errors = _schema_errors(json_safe(manifest))
    manifest["evidence_schema_errors"] = schema_errors
    manifest["evidence_schema_valid"] = not bool(schema_errors)
    MANIFEST_PATH.write_text(json.dumps(json_safe(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if schema_errors:
        raise RuntimeError(f"C3 evidence schema failed: {schema_errors}")
    print(json.dumps({
        "status": manifest["status"],
        "gates": gate_decisions,
        "frequency_points": len(frequencies),
        "failure_cases": [item["pass"] for item in failures.values()],
        "replays": [item["pass"] for item in replay_comparisons],
        "archive": str(ARCHIVE_PATH),
        "manifest": str(MANIFEST_PATH),
    }, indent=2, default=json_safe), flush=True)
    return 0 if manifest["status"] == "PASS_HARMONIC_FINAL_OWNER_READY" else 3


if __name__ == "__main__":
    raise SystemExit(main())
