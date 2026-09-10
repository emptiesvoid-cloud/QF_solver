"""Targeted guards for the WP13-02C mixed harmonic campaign."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).parents[2]
CONTRACT = ROOT / "qualification" / "0_2_8" / "wp13_02c_harmonic_contract.json"
SCHEMA = ROOT / "qualification" / "0_2_8" / "wp13_02c_harmonic_contract.schema.json"
EVIDENCE = ROOT / "qualification" / "0_2_8" / "wp13_02c_harmonic_v1" / "manifest.json"
ARCHIVE = ROOT / "qualification" / "0_2_8" / "wp13_02c_harmonic_v1" / "wp13_02c_harmonic_arrays.npz"


def _load() -> tuple[dict, dict, dict]:
    return (
        json.loads(CONTRACT.read_text(encoding="utf-8")),
        json.loads(SCHEMA.read_text(encoding="utf-8")),
        json.loads(EVIDENCE.read_text(encoding="utf-8")),
    )


def test_wp13_02c_contract_is_frozen_and_machine_readable() -> None:
    contract, schema, evidence = _load()
    assert contract["contract_id"] == schema["properties"]["contract_id"]["const"]
    assert contract["contract_id"] == evidence["contract_id"] == "WP13-02C-HARMONIC-MIXED-001"
    assert contract["status"] == "PREDECLARED_NOT_EXECUTED"
    assert contract["creation_sha"] == "046aa459d6290f57a1dc5c8cc32d3ea5e9bdcea7"
    assert contract["predeclared_gates"]["fixed_before_execution"] is True
    assert contract["predeclared_gates"]["post_observation_retuning"] is False
    assert contract["scope"]["connected_components"] == 1
    assert contract["scope"]["direct_support_bypass"] is False
    assert contract["failure_contract"]["all_cases_must_execute"] is True
    assert contract["evidence_schema"]["contract_values_single_source_of_truth"] is True
    assert evidence["contract_unchanged"] is True
    assert evidence["contract_sha256"] == hashlib.sha256(CONTRACT.read_bytes()).hexdigest()


def test_wp13_02c_connected_harmonic_gates_and_interfaces_pass() -> None:
    contract, _, evidence = _load()
    assert evidence["status"] == "PASS_CANDIDATE"
    assert evidence["benchmark_inputs"]["family_counts"] == {"TET4": 3, "WEDGE6": 2, "HEX8": 1}
    assert evidence["benchmark_inputs"]["connected_components"] == 1
    assert evidence["benchmark_inputs"]["direct_support_bypass"] is False
    assert evidence["conditioning"]["status"] == "PASS"
    assert evidence["gate_decisions"] == {
        "static_limit": True,
        "amplitude_all_frequencies": True,
        "phase_all_frequencies": True,
        "residual_all_frequencies": True,
        "resonance_peak_index_match": True,
        "resonance_frequency": True,
        "interface": True,
        "replays": True,
        "failure_contract": True,
    }
    assert len(evidence["frequencies"]["frequencies_hz"]) == len(contract["frequency_contract"]["frequency_ratios"])
    assert evidence["oracle"]["damping_ratio"] == 0.02
    assert evidence["oracle"]["first_frequency_hz"] > 0.0
    assert evidence["metrics"]["static_limit_error"] <= contract["predeclared_gates"]["static_limit_relative"]["value"]
    assert max(evidence["metrics"]["amplitude_errors"]) <= contract["predeclared_gates"]["oracle_amplitude_relative"]["value"]
    assert max(evidence["metrics"]["phase_errors"]) <= contract["predeclared_gates"]["oracle_phase_absolute_rad"]["value"]
    for values in evidence["interface_gate_values"].values():
        assert values["continuity_max"] <= contract["predeclared_gates"]["interface_displacement_continuity"]["value"]
        assert values["force_balance_max"] <= contract["predeclared_gates"]["interface_force_transfer_relative"]["value"]
        assert values["energy_mismatch_max"] <= contract["predeclared_gates"]["interface_energy_error_relative"]["value"]


def test_wp13_02c_archive_replays_and_real_failure_cases() -> None:
    _, _, evidence = _load()
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == evidence["archive"]["sha256"]
    with np.load(ARCHIVE, allow_pickle=False) as arrays:
        assert "runtime_responses" in arrays.files
        assert "oracle_dense_responses" in arrays.files
        assert arrays["runtime_responses"].dtype == np.complex128
        assert arrays["oracle_dense_responses"].dtype == np.complex128
        assert all(np.isfinite(arrays[name]).all() for name in arrays.files)
        for name, metadata in evidence["array_manifest"].items():
            assert tuple(metadata["shape"]) == arrays[name].shape
            assert str(arrays[name].dtype) == metadata["dtype"]
            digest = hashlib.sha256(np.ascontiguousarray(arrays[name]).tobytes()).hexdigest()
            assert digest == metadata["sha256"]
    assert all(item["pass"] for item in evidence["replays"]["comparisons"])
    assert evidence["oracle"]["sdof_control"]["status"] == "SUPPORTING_DIAGNOSTIC_ONLY"
    assert evidence["oracle"]["sdof_control"]["first_mode_dominance_demonstrated"] is False
    failures = evidence["failure_executions"]
    assert len(failures) == 9
    assert all(item["executed"] and item["status"] == "PASS" for item in failures.values())
