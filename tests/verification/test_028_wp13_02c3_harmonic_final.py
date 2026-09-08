"""Targeted WP13-02C3 final-campaign evidence checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import jsonschema


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "qualification/0_2_8/wp13_02c3_harmonic_final/manifest.json"
ARCHIVE_PATH = ROOT / "qualification/0_2_8/wp13_02c3_harmonic_final/wp13_02c3_harmonic_arrays.npz"
FREEZE_PATH = ROOT / "qualification/0_2_8/wp13_02c3_harmonic_final/pre_run_freeze.json"
SCHEMA_PATH = ROOT / "qualification/0_2_8/wp13_02c3_harmonic_evidence.schema.json"
CONTRACT_PATH = ROOT / "qualification/0_2_8/wp13_02c_harmonic_contract.json"
OLD_MANIFEST_PATH = ROOT / "qualification/0_2_8/wp13_02c_harmonic_v1/manifest.json"
C2_MANIFEST_PATH = ROOT / "qualification/0_2_8/wp13_02c2_harmonic_harness/manifest.json"
C2_SCRIPT_PATH = ROOT / "scripts/run_wp13_02c2_harmonic_harness.py"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_c3_schema_and_contract_freeze_are_valid() -> None:
    manifest = _manifest()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(manifest))
    assert errors == []
    assert manifest["status"] == "PASS_HARMONIC_FINAL_OWNER_READY"
    assert manifest["contract_id"] == "WP13-02C-HARMONIC-MIXED-001"
    assert manifest["contract_sha256"] == hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest()
    assert manifest["provenance_freeze"]["pre_run_freeze_valid"] is True
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    assert freeze["pre_run_freeze_valid"] is True
    assert freeze["evaluator_pre_run_digest"] == hashlib.sha256(C2_SCRIPT_PATH.read_bytes()).hexdigest()


def test_exact_frequency_grid_oracle_and_all_numerical_gates_pass() -> None:
    manifest = _manifest()
    expected_ratios = [0.0, 0.25, 0.5, 0.75, 0.9, 0.98, 1.0, 1.02, 1.1, 1.25, 1.5, 2.0]
    assert manifest["frequencies"]["ratios"] == expected_ratios
    assert len(manifest["frequencies"]["frequencies_hz"]) == 12
    assert manifest["conditioning"]["status"] == "PASS"
    assert manifest["oracle_responses"]["first_mode_dominated_claim_allowed"] is False
    assert all(manifest["gate_decisions"].values())
    assert manifest["static_limit"]["error"] <= 1.0e-8
    assert manifest["resonance"]["label"] == "FRF_PEAK_IN_FROZEN_FREQUENCY_CAMPAIGN"


def test_independent_interface_evidence_uses_contract_energy_product() -> None:
    manifest = _manifest()
    interfaces = manifest["interface_metrics"]
    assert interfaces["state_collection_independent"] is True
    assert interfaces["continuity_tautological"] is False
    assert interfaces["energy_normalization"]["formula"] == "||Ffree||2 * ||x||2"
    assert interfaces["energy_normalization"]["matches_contract_product_term"] is True
    assert set(interfaces["gate_values"]) == {"TET4_WEDGE6", "WEDGE6_HEX8"}
    for row in interfaces["frequency_rows"]:
        for metric in row.values():
            assert metric["independent_state_collection"] is True
            assert metric["continuity_tautological"] is False
            assert metric["energy_denominator"] == metric["ffree_norm"] * metric["x_l2_norm"]


def test_modal_replay_failure_and_archive_evidence_are_complete() -> None:
    manifest = _manifest()
    archive = np.load(ARCHIVE_PATH, allow_pickle=False)
    assert manifest["modal_coordinate"]["definition"]["projection_formula"] == "q = phi^H M x"
    assert manifest["modal_coordinate"]["definition"]["first_mode_dominated_claim_allowed"] is False
    for key in ("modal_coordinate_complex", "modal_coordinate_amplitude", "modal_coordinate_phase"):
        assert key in archive.files
    required_replay_fields = {
        "complex displacement", "complex reactions", "full residual", "amplitude",
        "phase", "modal coordinate", "interface left/right states",
        "interface continuity", "interface forces", "interface work/energy",
        "status", "iterations",
    }
    for comparison in manifest["replay_comparison"]["comparisons"]:
        assert comparison["pass"] is True
        assert required_replay_fields.issubset(comparison["fields_compared"])
        assert comparison["status_identical"] is True
        assert comparison["interface_fields_complete"] if "interface_fields_complete" in comparison else True
    failures = manifest["failure_executions"]
    assert failures["required"] == 9
    assert failures["executed"] == 9
    assert failures["pass"] == 9
    for case in failures["cases"].values():
        assert case["type_match"] and case["message_match"] and case["path_match"]
        assert case["failure_any_exception_accepted"] is False
    assert manifest["evidence_schema_valid"] is True
    assert manifest["historical_records_preserved"] is True


def test_historical_c_and_c2_records_are_unchanged() -> None:
    manifest = _manifest()
    c2 = json.loads(C2_MANIFEST_PATH.read_text(encoding="utf-8"))
    old = json.loads(OLD_MANIFEST_PATH.read_text(encoding="utf-8"))
    old_archive = ROOT / "qualification/0_2_8/wp13_02c_harmonic_v1/wp13_02c_harmonic_arrays.npz"
    assert old["status"] == "PASS_CANDIDATE"
    assert c2["status"] == "PASS_HARMONIC_HARNESS_READY"
    assert c2["source_campaign_conformance"] == "NONCONFORMING_UNDER_C2_SCHEMA"
    assert hashlib.sha256(old_archive.read_bytes()).hexdigest() == old["archive"]["sha256"]
    assert manifest["integrity"]["historical_results_preserved"] is True
    assert manifest["integrity"]["historical_0_2_7_evidence_changed"] is False
