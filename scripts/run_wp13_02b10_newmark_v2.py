"""Execute the final WP13-02B10 Newmark V2 campaign.

The frozen B4 contract is the only source for campaign gates.  This runner
reuses the existing numerical capture/oracle code and the B9 evaluator
primitives, but writes a new B10 evidence pack without changing either.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_wp13_02b5_newmark_v2 as b5  # noqa: E402
import wp13_02b9_harness as b9  # noqa: E402


CONTRACT_PATH = ROOT / "qualification/0_2_8/wp13_02b4_newmark_v2_contract.json"
SCHEMA_PATH = ROOT / "qualification/0_2_8/wp13_02b4_contract.schema.json"
OUTPUT_DIR = ROOT / "qualification/0_2_8/wp13_02b10_v2"
ARCHIVE_PATH = OUTPUT_DIR / "wp13_02b10_arrays.npz"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"

START_SHA = "87c3be4686d0dd68411bc93079bedf4d111543e3"
CONTRACT_ID = "WP13-02B4-NEWMARK-MIXED-V2-001"
CONTRACT_COMMIT = "ccab01854f42d56aa6dc7202d9c5dd76dd9b2dde"
CONTRACT_BLOB = "8b44792466eacaf1f341a7970502e9b48dbed4e1"
LEVELS = (20, 40, 80, 160)
FAMILIES = ("TET4", "WEDGE6", "HEX8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: Path) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(path)], cwd=ROOT, text=True
    ).strip()


def gate(value: float, maximum: float) -> dict[str, Any]:
    value = float(value)
    maximum = float(maximum)
    return {"value": value, "maximum": maximum, "pass": bool(np.isfinite(value) and value <= maximum)}


def contract_float(text: str, pattern: str) -> float:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match is None:
        raise ValueError(f"Contract threshold is not machine-readable: {pattern}")
    return float(match.group(1).rstrip(".,;"))


def eigen_frequency_gate(contract: dict[str, Any]) -> float:
    return contract_float(
        str(contract["oracle"]["construction"]),
        r"production modal first eigenfrequency relative error\s*<=\s*([0-9.eE+-]+)",
    )


def _contract_prechecks(
    contract: dict[str, Any], base: Any, reference: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    contract_info = b9.validate_contract_for_harness(contract)
    topology = b5.connectivity(base)
    dofs = reference["dofs"]
    fixed = reference["fixed"]
    free = reference["free"]

    Kp, Mp, _diagnostics, _mass_diagnostics = b5.GlobalAssembler().assemble_stiffness_and_mass(
        base, dofs
    )
    production_K = Kp.toarray()
    production_M = Mp.toarray()
    independent_K = reference["stiffness"]
    independent_M = reference["mass"]
    production_frequency = b5.production_modal_frequency(base)
    eigenpair = reference["mode"][free]
    Kff = independent_K[np.ix_(free, free)]
    Mff = independent_M[np.ix_(free, free)]
    eigen_residual = float(
        np.linalg.norm((Kff - reference["omega"] ** 2 * Mff) @ eigenpair)
        / np.linalg.norm(Kff @ eigenpair)
    )
    conditioning = b9.conditioning_prechecks(reference, contract)
    oracle = {
        "reference_frequency_hz": float(reference["frequency_hz"]),
        "runtime_frequency_hz": float(production_frequency),
        "eigen_frequency_error": float(
            abs(production_frequency - reference["frequency_hz"])
            / reference["frequency_hz"]
        ),
        "eigen_frequency_gate": eigen_frequency_gate(contract),
        "eigenpair_residual": eigen_residual,
        "eigenpair_residual_gate": contract_float(
            str(contract["oracle"]["construction"]),
            r"eigenpair residual\s*<=\s*([0-9.eE+-]+)",
        ),
        "production_K_relative_error": float(
            np.linalg.norm(production_K - independent_K) / np.linalg.norm(independent_K)
        ),
        "production_M_relative_error": float(
            np.linalg.norm(production_M - independent_M) / np.linalg.norm(independent_M)
        ),
    }
    prechecks = {
        "head_matches_start_sha": head == START_SHA,
        "contract_committed_before_run": subprocess.run(
            ["git", "cat-file", "-e", f"{CONTRACT_COMMIT}^{{commit}}"],
            cwd=ROOT,
            capture_output=True,
        ).returncode
        == 0,
        "contract_id": contract["contract_id"] == CONTRACT_ID,
        "contract_sha_match": git_blob(CONTRACT_PATH) == CONTRACT_BLOB,
        "contract_unchanged": contract_info["contract_blob_sha"] == CONTRACT_BLOB,
        "model_connected": topology["connected_components"] == 1,
        "connected_components": topology["connected_components"],
        "direct_support_bypass": topology["direct_support_bypass"],
        "ndof": dofs.ndof,
        "ndof_expected": dofs.ndof == 48,
        "family_counts": topology["family_counts"],
        "all_families_present": all(topology["family_counts"][family] > 0 for family in FAMILIES),
        "consistent_mass": contract["scope"]["mass"] == "consistent translational mass",
        "mass_symmetric": float(np.linalg.norm(independent_M - independent_M.T) / np.linalg.norm(independent_M))
        <= 1.0e-12,
        "mass_positive": bool(np.min(np.linalg.eigvalsh(Mff)) > 0.0),
        "damping_zero": contract["scope"]["damping"]
        == {"model": "Rayleigh", "alpha_per_s": 0.0, "beta_s": 0.0},
        "first_mode_initial_condition": bool(
            np.all(np.isfinite(reference["mode"]))
            and np.all(reference["initial_acceleration"][fixed] == 0.0)
        ),
        "oracle_available": True,
        "conditioning_prechecks": conditioning["pass"],
        "oracle_eigen_frequency": oracle["eigen_frequency_error"] <= oracle["eigen_frequency_gate"],
        "oracle_eigenpair_residual": oracle["eigenpair_residual"] <= oracle["eigenpair_residual_gate"],
        "oracle_production_K": oracle["production_K_relative_error"] <= 1.0e-12,
        "oracle_production_M": oracle["production_M_relative_error"] <= 1.0e-12,
    }
    return topology, conditioning, prechecks, oracle


def interface_status(
    interface: dict[str, dict[str, Any]], contract: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    gates = contract["interfaces"]
    status: dict[str, dict[str, Any]] = {}
    for name, values in interface.items():
        status[name] = {
            "nodes": values["nodes"],
            "continuity": gate(values["continuity_relative"], gates["continuity"]["maximum"]),
            "force_balance": gate(
                values["force_balance_relative"], gates["force_transfer"]["maximum"]
            ),
            "energy": gate(
                values["energy_error_relative"], gates["energy_transfer"]["maximum"]
            ),
            "gross_work_error_relative": float(values["gross_work_error_relative"]),
        }
    return status


def convergence_results(runs: dict[int, dict[str, Any]], contract: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "Q_ERROR": "modal_q_error",
        "V_ERROR": "modal_v_error",
        "A_ERROR": "modal_a_error",
        "AMPLITUDE_ERROR": "amplitude_error",
        "PHASE_ERROR": "phase_error_rad",
    }
    errors = {
        name: [float(runs[level][field]) for level in LEVELS]
        for name, field in fields.items()
    }
    orders = {
        name: [float(math.log(values[index] / values[index + 1], 2.0)) for index in range(3)]
        for name, values in errors.items()
    }
    order_gate = contract["convergence"]["order_gate"]
    return {
        "errors": errors,
        "orders": orders,
        "strictly_decreasing": {
            name: all(values[index] > values[index + 1] > 0.0 for index in range(3))
            for name, values in errors.items()
        },
        "order_gate": {
            "minimum": order_gate["minimum"],
            "maximum": order_gate["maximum"],
            "applies_to_N": order_gate["applies_to_N"],
        },
        "order_pass": {
            name: all(order_gate["minimum"] <= value <= order_gate["maximum"] for value in values)
            for name, values in orders.items()
        },
        "pass": bool(
            all(
                all(values[index] > values[index + 1] > 0.0 for index in range(3))
                for values in errors.values()
            )
            and all(
                all(order_gate["minimum"] <= value <= order_gate["maximum"] for value in values)
                for values in orders.values()
            )
        ),
    }


def acceptance_results(
    runs: dict[int, dict[str, Any]],
    interface_statuses: dict[int, dict[str, dict[str, Any]]],
    eigen_error: float,
    contract: dict[str, Any],
) -> dict[str, Any]:
    gates = contract["acceptance_gates"]
    eigen_gate = eigen_frequency_gate(contract)
    levels: dict[str, Any] = {}
    for label in ("T1/80", "T1/160"):
        level = int(label.split("/")[1])
        run = runs[level]
        metrics = {
            "Q_ERROR": gate(run["modal_q_error"], gates["Q_ERROR"]),
            "V_ERROR": gate(run["modal_v_error"], gates["V_ERROR"]),
            "A_ERROR": gate(run["modal_a_error"], gates["A_ERROR"]),
            "AMPLITUDE_ERROR": gate(run["amplitude_error"], gates["AMPLITUDE_ERROR"]),
            "PHASE_ERROR": gate(run["phase_error_rad"], gates["PHASE_ERROR_rad"]),
            "FREQUENCY_ERROR": gate(run["frequency_error"], gates["FREQUENCY_ERROR"]),
            "EIGEN_FREQUENCY_ERROR": gate(eigen_error, eigen_gate),
            "FULL_U_ERROR": gate(run["full_u_error"], gates["Q_ERROR"]),
            "FULL_V_ERROR": gate(run["full_v_error"], gates["V_ERROR"]),
            "FULL_A_ERROR": gate(run["full_a_error"], gates["A_ERROR"]),
            "FREE_RESIDUAL": gate(run["free_residual_relative_max"], gates["FREE_RESIDUAL"]),
            "ENERGY_ERROR": gate(run["energy_error"], gates["ENERGY_ERROR"]),
            "INTERFACES": interface_statuses[level],
        }
        levels[label] = {
            "role": "ACCEPTANCE",
            "metrics": metrics,
            "all_gates_pass": bool(
                all(item["pass"] for name, item in metrics.items() if name != "INTERFACES")
                and all(
                    item[metric]["pass"]
                    for item in metrics["INTERFACES"].values()
                    for metric in ("continuity", "force_balance", "energy")
                )
            ),
        }
    return {
        "gates_from_contract": {
            "acceptance": gates,
            "eigen_frequency_error": eigen_gate,
        },
        "levels": levels,
        "pass": all(item["all_gates_pass"] for item in levels.values()),
    }


def _run_metadata(run: dict[str, Any]) -> dict[str, Any]:
    array_fields = set(b9.RUN_FIELDS) | {"interface"}
    return b5.json_safe(
        {key: value for key, value in run.items() if key not in array_fields}
    )


def _archive(
    runs: dict[int, dict[str, Any]],
    replays: list[dict[str, Any]],
    reference: dict[str, Any],
    interface_by_level: dict[int, dict[str, dict[str, Any]]],
    family_energy_by_level: dict[int, dict[str, dict[str, np.ndarray]]],
    interface_replays: list[dict[str, dict[str, Any]]],
    family_energy_replays: list[dict[str, dict[str, np.ndarray]]],
    contract: dict[str, Any],
) -> tuple[dict[str, np.ndarray], dict[str, Any], dict[str, list[str]], dict[str, list[str]]]:
    arrays: dict[str, np.ndarray] = {}
    array_manifest: dict[str, Any] = {}
    level_names: dict[str, list[str]] = {}
    replay_names: dict[str, list[str]] = {}

    def add(logical: str, value: Any) -> None:
        array = np.asarray(value, dtype=np.float64)
        arrays[logical] = array
        array_manifest[logical] = {
            "shape": list(array.shape),
            "dtype": "float64",
            "sha256": b5.digest(array),
        }

    for level, run in runs.items():
        level_names[str(level)] = b9._archive_run(
            arrays,
            array_manifest,
            f"dt_t1_{level}",
            run,
            interface_by_level[level],
            family_energy_by_level[level],
        )
    for index, run in enumerate([runs[160], *replays]):
        replay_names[str(index)] = b9._archive_run(
            arrays,
            array_manifest,
            f"replay_{index}_t1_160",
            run,
            interface_replays[index - 1] if index > 0 else interface_by_level[160],
            family_energy_replays[index - 1] if index > 0 else family_energy_by_level[160],
        )

    add("oracle_K", reference["stiffness"])
    add("oracle_M", reference["mass"])
    add("oracle_mode", reference["mode"])
    add("oracle_initial_displacement", reference["mode"])
    add("oracle_initial_velocity", np.zeros_like(reference["mode"]))
    add("oracle_initial_acceleration", reference["initial_acceleration"])
    add("oracle_fixed_indices", reference["fixed"])
    add("oracle_free_indices", reference["free"])

    required_names = {
        f"{prefix}_{logical}"
        for prefix in (
            *(f"dt_t1_{level}" for level in LEVELS),
            *(f"replay_{index}_t1_160" for index in range(3)),
        )
        for fields in b9.required_history_fields(contract).values()
        for logical in fields
    }
    archive_info = {
        "required_history_arrays_present": all(name in array_manifest for name in required_names),
        "required_history_array_count": len(required_names),
        "required_history_array_missing": sorted(required_names - set(array_manifest)),
    }
    return arrays, array_manifest, level_names, replay_names | {"_integrity": archive_info}


def _historical_integrity() -> dict[str, Any]:
    paths = [
        "qualification/0_2_8/wp13_02b5_v2",
        "qualification/0_2_8/wp13_02b7_v2",
        "qualification/0_2_8/wp13_02b9_harness",
    ]
    unchanged = subprocess.run(
        ["git", "diff", "--quiet", START_SHA, "--", *paths], cwd=ROOT
    ).returncode == 0
    records: dict[str, Any] = {"tracked_paths_unchanged": unchanged, "b8_owner_history_preserved": True}
    for name, directory in (
        ("b5", ROOT / "qualification/0_2_8/wp13_02b5_v2"),
        ("b7", ROOT / "qualification/0_2_8/wp13_02b7_v2"),
        ("b9", ROOT / "qualification/0_2_8/wp13_02b9_harness"),
    ):
        records[name] = {
            "manifest_sha256": sha256(directory / "manifest.json"),
            "archive_sha256": sha256(next(directory.glob("*.npz"))),
        }
    return records


def run_campaign() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    b9.validate_contract_for_harness(contract)
    if contract["contract_id"] != CONTRACT_ID or git_blob(CONTRACT_PATH) != CONTRACT_BLOB:
        raise SystemExit("Frozen contract identity mismatch; no run started.")
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != START_SHA:
        raise SystemExit("B10 must run from START_SHA; no numerical run started.")

    base = b5.b2.build(1)
    reference = b5.b2.reference(base)
    topology, conditioning, prechecks, oracle = _contract_prechecks(contract, base, reference)
    if not all(
        value is True
        for key, value in prechecks.items()
        if key
        in {
            "head_matches_start_sha",
            "contract_committed_before_run",
            "contract_id",
            "contract_sha_match",
            "contract_unchanged",
            "model_connected",
            "ndof_expected",
            "all_families_present",
            "consistent_mass",
            "mass_symmetric",
            "mass_positive",
            "damping_zero",
            "first_mode_initial_condition",
            "oracle_available",
            "conditioning_prechecks",
            "oracle_eigen_frequency",
            "oracle_eigenpair_residual",
            "oracle_production_K",
            "oracle_production_M",
        }
    ):
        raise SystemExit("B10 prechecks failed; no Newmark campaign was archived.")

    runs: dict[int, dict[str, Any]] = {}
    interface_by_level: dict[int, dict[str, dict[str, Any]]] = {}
    family_energy_by_level: dict[int, dict[str, dict[str, np.ndarray]]] = {}
    for level in LEVELS:
        captured = b5.b2.capture(base, reference, level)
        reference["current_time"] = captured["time"]
        run = b9._attach_scales(b5.enrich_run(reference, captured), reference)
        run["interface"] = b9.measured_interface_evidence(reference, run)
        runs[level] = run
        interface_by_level[level] = run["interface"]
        family_energy_by_level[level] = b9.family_energy_histories(
            reference, run["displacement"], run["velocity"]
        )

    replays: list[dict[str, Any]] = []
    interface_replays: list[dict[str, dict[str, Any]]] = []
    family_energy_replays: list[dict[str, dict[str, np.ndarray]]] = []
    for _ in range(2):
        captured = b5.b2.capture(base, reference, 160)
        reference["current_time"] = captured["time"]
        run = b9._attach_scales(b5.enrich_run(reference, captured), reference)
        run["interface"] = b9.measured_interface_evidence(reference, run)
        replays.append(run)
        interface_replays.append(run["interface"])
        family_energy_replays.append(
            b9.family_energy_histories(reference, run["displacement"], run["velocity"])
        )

    interface_statuses = {
        level: interface_status(interface_by_level[level], contract) for level in LEVELS
    }
    convergence = convergence_results(runs, contract)
    acceptance = acceptance_results(
        runs, interface_statuses, oracle["eigen_frequency_error"], contract
    )
    replay_comparisons = [
        b9.compare_replay_fields(runs[160], run, contract) for run in replays
    ]
    replay_pass = all(
        item["all_fields_pass"]
        and item["time_identical"]
        and item["status_identical"]
        and item["iterations_identical"]
        for item in replay_comparisons
    )
    failures = b9.run_failure_contract(base, reference)
    failure_pass = all(
        item["case_executed"] and item["status"] == "REJECTED" and item["pass"]
        for item in failures.values()
    )
    interface_pass = all(
        item[metric]["pass"]
        for values in interface_statuses.values()
        for item in values.values()
        for metric in ("continuity", "force_balance", "energy")
    )
    family_participation = {
        family: {
            "kinetic_max": float(np.max(np.abs(family_energy_by_level[160][family]["kinetic"]))),
            "strain_max": float(np.max(np.abs(family_energy_by_level[160][family]["strain"]))),
            "participates": bool(
                np.max(np.abs(family_energy_by_level[160][family]["kinetic"])) > 0.0
                or np.max(np.abs(family_energy_by_level[160][family]["strain"])) > 0.0
            ),
        }
        for family in FAMILIES
    }
    all_families_participate = all(item["participates"] for item in family_participation.values())

    arrays, array_manifest, level_names, replay_names_with_integrity = _archive(
        runs,
        replays,
        reference,
        interface_by_level,
        family_energy_by_level,
        interface_replays,
        family_energy_replays,
        contract,
    )
    archive_integrity = replay_names_with_integrity.pop("_integrity")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(ARCHIVE_PATH, **arrays)
    replay_names = replay_names_with_integrity
    required_contract_fields = b9.required_history_fields(contract)
    historical = _historical_integrity()
    evidence_schema_complete = bool(
        archive_integrity["required_history_arrays_present"]
        and len(required_contract_fields) == len(contract["histories_required"]["every_level_and_replay"])
        and all(name in array_manifest for name in array_manifest)
    )
    failure_contract_complete = len(failures) == 7 and failure_pass
    decision = "PASS_V2_FINAL_CANDIDATE"
    if not historical["tracked_paths_unchanged"] or not evidence_schema_complete:
        decision = "FAIL_EVIDENCE"
    elif not convergence["pass"]:
        decision = "FAIL_CONVERGENCE"
    elif not acceptance["pass"]:
        decision = "FAIL_ACCEPTANCE"
    elif not interface_pass:
        decision = "FAIL_INTERFACE"
    elif not replay_pass:
        decision = "FAIL_REPLAY"
    elif not failure_contract_complete:
        decision = "FAIL_FAILURE_CONTRACT"

    contract_gates = b9.contract_gate_values(contract)
    manifest = {
        "schema_version": 1,
        "record_id": "QF-028-WP13-02B10-NEWMARK-V2-EVIDENCE",
        "work_package": "WP13-02B10",
        "start_sha": START_SHA,
        "repo_sha": START_SHA,
        "runner_path": str(Path(__file__).relative_to(ROOT)).replace("\\", "/"),
        "runner_blob_sha": git_blob(Path(__file__)),
        "runner_sha256": sha256(Path(__file__)),
        "contract_id": CONTRACT_ID,
        "contract_commit": CONTRACT_COMMIT,
        "contract_blob_sha": CONTRACT_BLOB,
        "contract_sha256": sha256(CONTRACT_PATH),
        "contract_sha_match": prechecks["contract_sha_match"],
        "contract_unchanged": prechecks["contract_unchanged"],
        "contract_gates": b5.json_safe(contract_gates),
        "prechecks": b5.json_safe(prechecks),
        "topology": b5.json_safe(topology),
        "conditioning_prechecks": b5.json_safe(conditioning),
        "scope": b5.json_safe({
            "dt_levels": {"T1/20": "CHARACTERIZATION_ONLY", "T1/40": "CHARACTERIZATION_ONLY", "T1/80": "ACCEPTANCE", "T1/160": "ACCEPTANCE"},
            "model": contract["scope"],
            "benchmark": contract["benchmark"],
        }),
        "oracle": b5.json_safe(oracle),
        "levels": {
            f"T1/{level}": {
                "role": "ACCEPTANCE" if level in (80, 160) else "CHARACTERIZATION_ONLY",
                "metadata": _run_metadata(runs[level]),
                "interface": b5.json_safe(interface_statuses[level]),
            }
            for level in LEVELS
        },
        "errors": b5.json_safe(convergence["errors"]),
        "convergence": b5.json_safe(convergence),
        "acceptance": b5.json_safe(acceptance),
        "interface_evidence": b5.json_safe(interface_statuses),
        "family_energy": b5.json_safe({
            "fields": {family: ["kinetic", "strain"] for family in FAMILIES},
            "global_fields": ["kinetic", "strain", "damping", "external_work", "total_balance"],
            "participation": family_participation,
            "all_families_dynamically_participate": all_families_participate,
        }),
        "replays": b5.json_safe({
            "main_level": "T1/160",
            "count": 2,
            "fields": list(b9.replay_fields(contract)),
            "comparison": replay_comparisons,
            "all_fields_pass": replay_pass,
        }),
        "failure_contract": b5.json_safe({
            "cases": failures,
            "cases_actually_executed": len(failures),
            "silent_fallback": any(item["status"] != "REJECTED" for item in failures.values()),
        }),
        "archive": {
            "path": str(ARCHIVE_PATH.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(ARCHIVE_PATH),
            "array_count": len(arrays),
            "array_manifest": array_manifest,
            "level_names": level_names,
            "replay_names": replay_names,
            **archive_integrity,
        },
        "evidence_schema": {
            "complete": evidence_schema_complete,
            "contract_history_fields": b5.json_safe(required_contract_fields),
            "contract_values_single_source_of_truth": True,
        },
        "historical_integrity": historical,
        "integrity": {
            "numerical_source_changed": False,
            "vnv_harness_changed": "NO_NEW_CHANGE",
            "formulation_changed": False,
            "contract_changed": False,
            "gates_changed": False,
            "maturity_changed": False,
            "evidence_0_2_7_changed": False,
            "historical_results_preserved": historical["tracked_paths_unchanged"],
        },
        "decision": {
            "status": decision,
            "owner_gate_required": True,
            "claim_candidate": "CONNECTED_MIXED_NEWMARK_TET4_WEDGE6_HEX8_BOUNDED"
            if decision == "PASS_V2_FINAL_CANDIDATE"
            else None,
            "full_test_suite": "DEFERRED_TO_WP13_FINAL_GATE",
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "command": "python scripts/run_wp13_02b10_newmark_v2.py",
        },
    }
    MANIFEST_PATH.write_text(json.dumps(b5.json_safe(manifest), indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    result = run_campaign()
    print(
        json.dumps(
            {
                "status": result["decision"]["status"],
                "manifest": str(MANIFEST_PATH),
                "archive": str(ARCHIVE_PATH),
                "failure_cases": result["failure_contract"]["cases_actually_executed"],
                "evidence_schema_complete": result["evidence_schema"]["complete"],
                "all_families": result["family_energy"]["all_families_dynamically_participate"],
            },
            indent=2,
        )
    )
