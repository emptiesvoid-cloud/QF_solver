"""Post-process pairwise mesh changes in the archived J10 TET10 histories."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "research/j11_transient/contracts/j10_spatial_sensitivity_postprocess_contract.json"
RESULT_PATH = ROOT / "research/j10/results/diagnostic-2026-11-16/tet10_fixed_excitation/result.json"
STATES_PATH = ROOT / "research/j10/results/diagnostic-2026-11-16/tet10_fixed_excitation/tet10_fixed_excitation_states.npz"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def pairwise_history_difference(lower: np.ndarray, upper: np.ndarray, *, shared_scale_m: float) -> dict[str, float]:
    lower_values = np.asarray(lower, dtype=np.float64)
    upper_values = np.asarray(upper, dtype=np.float64)
    if lower_values.ndim != 1 or upper_values.shape != lower_values.shape:
        raise ValueError("Pairwise histories must be one-dimensional arrays on the same physical time grid")
    if not np.isfinite(lower_values).all() or not np.isfinite(upper_values).all():
        raise ValueError("Pairwise histories must be finite")
    if not np.isfinite(shared_scale_m) or shared_scale_m <= 0.0:
        raise ValueError("The shared normalization scale must be finite and positive")
    difference = upper_values - lower_values
    rms = float(np.sqrt(np.mean(difference**2)))
    peak = float(np.max(np.abs(difference)))
    return {
        "rms_absolute_difference_m": rms,
        "peak_absolute_difference_m": peak,
        "rms_normalized_to_shared_oracle_peak": rms / shared_scale_m,
        "peak_normalized_to_shared_oracle_peak": peak / shared_scale_m,
    }


def analyze_archived_j10(*, contract_path: Path = CONTRACT_PATH, result_path: Path = RESULT_PATH, states_path: Path = STATES_PATH) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if _sha256(result_path) != contract["inputs"]["result_json_sha256_raw"]:
        raise ValueError("J10 result JSON does not match the frozen post-processing contract")
    if _sha256(states_path) != contract["inputs"]["states_npz_sha256_raw"]:
        raise ValueError("J10 state archive does not match the frozen post-processing contract")
    for item in contract["source_identity"]:
        if _canonical_sha256(ROOT / item["path"]) != item["canonical_sha256"]:
            raise ValueError(f"J11 post-processing source differs from its frozen contract: {item['path']}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("execution_status") != "COMPLETED_EXPLORATORY":
        raise ValueError("The archived J10 result is not the expected exploratory completion")
    if result.get("source_head") != contract["source_run"]["source_head"]:
        raise ValueError("The archived J10 source head differs from the post-processing contract")
    if result.get("nodeid") != contract["source_run"]["nodeid"]:
        raise ValueError("The archived J10 nodeid differs from the post-processing contract")
    if result.get("contract_sha256") != contract["source_run"]["contract_sha256"]:
        raise ValueError("The archived J10 run contract differs from the post-processing contract")
    if result.get("source_fingerprint") != contract["source_run"]["source_fingerprint"]:
        raise ValueError("The archived J10 source fingerprint differs from the post-processing contract")

    rows = result["mesh_levels"]
    indices = contract["comparison"]["mesh_indices"]
    dt = float(contract["comparison"]["dt_s"])
    scale = float(result["normalization"]["global_oracle_peak_m"])
    pair_results = []
    with np.load(states_path, allow_pickle=False) as archive:
        common_times = np.asarray(archive[f"times_dt{dt:.7f}_s"], dtype=np.float64)
        expected_count = int(contract["comparison"]["expected_observation_count"])
        expected_interval = np.asarray(contract["comparison"]["time_interval_s"], dtype=np.float64)
        if common_times.shape != (expected_count,) or not np.array_equal(common_times[[0, -1]], expected_interval):
            raise ValueError("The archived physical time grid differs from the contracted count or endpoints")
        if not np.allclose(np.diff(common_times), dt, rtol=0.0, atol=1.0e-14):
            raise ValueError("The archived physical time grid differs from the contracted time step")
        for lower_index, upper_index, axis_name in zip(indices[:-1], indices[1:], contract["comparison"]["changed_axes"], strict=True):
            lower = np.asarray(archive[f"oracle_m{lower_index}_dt{dt:.7f}_uz_m"], dtype=np.float64)
            upper = np.asarray(archive[f"oracle_m{upper_index}_dt{dt:.7f}_uz_m"], dtype=np.float64)
            if lower.shape != common_times.shape or upper.shape != common_times.shape:
                raise ValueError("An archived oracle history does not match the common physical time grid")
            lower_coordinates = np.asarray(archive[f"coordinates_m_{lower_index}"], dtype=np.float64)
            upper_coordinates = np.asarray(archive[f"coordinates_m_{upper_index}"], dtype=np.float64)
            lower_probe = np.asarray(rows[lower_index]["measurement_position_m"], dtype=np.float64)
            upper_probe = np.asarray(rows[upper_index]["measurement_position_m"], dtype=np.float64)
            lower_probe_node = int(rows[lower_index]["measurement_node"])
            upper_probe_node = int(rows[upper_index]["measurement_node"])
            if not np.array_equal(lower_probe, upper_probe):
                raise ValueError("The J10 pair does not use the same physical probe position")
            if not np.array_equal(lower_coordinates[lower_probe_node], lower_probe):
                raise ValueError("The lower J10 mesh probe is not represented by its recorded physical node")
            if not np.array_equal(upper_coordinates[upper_probe_node], upper_probe):
                raise ValueError("The upper J10 mesh probe is not represented by its recorded physical node")
            load_data = []
            for mesh_index in (lower_index, upper_index):
                coordinates = np.asarray(archive[f"coordinates_m_{mesh_index}"], dtype=np.float64)
                load_vector = np.asarray(archive[f"tip_load_vector_m{mesh_index}_n"], dtype=np.float64).reshape((-1, 3))
                nonzero = np.argwhere(np.abs(load_vector) > 1.0e-14)
                if len(nonzero) != 1 or tuple(nonzero[0][1:]) != (2,):
                    raise ValueError("Expected the same single-node negative-Z point load on each J10 mesh")
                loaded_node = int(nonzero[0][0])
                loaded_position = coordinates[loaded_node]
                resultant = np.sum(load_vector, axis=0)
                if not np.allclose(resultant, (0.0, 0.0, -1.0), rtol=0.0, atol=1.0e-14):
                    raise ValueError("The J10 archived point-load resultant differs from the contracted -1 N load")
                if not np.array_equal(loaded_position, (2.0, 0.2, 0.2)):
                    raise ValueError("The J10 point load is not at the contracted physical end-face center")
                load_data.append({"loaded_position_m": loaded_position.tolist(), "resultant_n": resultant.tolist()})
            pair_results.append({
                "lower_mesh_cells": rows[lower_index]["cells"],
                "upper_mesh_cells": rows[upper_index]["cells"],
                "refinement_axis_added": axis_name,
                "common_probe_position_m": lower_probe.tolist(),
                "common_time_step_s": dt,
                "common_observation_count": int(len(common_times)),
                "load_checks": load_data,
                **pairwise_history_difference(lower, upper, shared_scale_m=scale),
                "scope": "Pairwise change in the QF same-M/K semidiscrete oracle histories; not a continuum error or formal convergence result.",
            })

    return {
        "schema": "qf-j11-j10-pairwise-mesh-postprocess-v1",
        "contract_id": contract["contract_id"],
        "classification": "DETERMINISTIC_POSTPROCESSING_OF_ARCHIVED_J10_DATA",
        "source_run": contract["source_run"],
        "inputs": {
            "result_json_sha256_raw": _sha256(result_path),
            "states_npz_sha256_raw": _sha256(states_path),
            "source_execution_status_preserved": result["execution_status"],
        "source_reference_type": result["reference"]["type"],
        },
        "normalization": {
            "shared_oracle_peak_m": scale,
            "formula": "pairwise oracle-history RMS/peak difference divided by the archived common global oracle peak",
        },
        "formal_acceptance_thresholds": "none; descriptive post-processing only",
        "pairwise_mesh_changes": pair_results,
        "interpretation": "The exact physical point load and nodal probe coordinates are unchanged. Pairwise differences isolate the effect of each added mesh direction on this discretized QF model, but the J10 oracle uses the same QF M/K operators and is not an independent continuum reference.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = analyze_archived_j10()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
