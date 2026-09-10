"""Targeted WP13-02C5 evidence-pipeline checks; no harmonic campaign."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import numpy as np
import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_wp13_02c5_harmonic_pipeline as pipeline


ROOT = Path(__file__).resolve().parents[2]
C4_RECORD = ROOT / "qualification/0_2_8/wp13_02c4_owner_gate.json"


def test_literal_energy_formula_and_components() -> None:
    contract = pipeline.load_contract()
    metric = pipeline.energy_metric_from_contract(contract, 2.0 + 3.0j, -1.0 + 4.0j, 2.0, 3.0)
    assert metric["formula_literal_match"] is True
    assert metric["work_sum"] == pytest.approx(abs(2.0 + 3.0j) + abs(-1.0 + 4.0j))
    assert metric["force_displacement_product"] == pytest.approx(6.0)
    assert metric["energy_denominator"] == pytest.approx(metric["work_sum"])
    assert metric["contract_path"] == "metric_definitions.interface_energy"


def test_actual_failure_inputs_are_executed_and_strictly_serialized() -> None:
    contract = pipeline.load_contract()
    base = pipeline.legacy.build(1)
    manifest = json.loads(
        (ROOT / "qualification/0_2_8/wp13_02c3_harmonic_final/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    failures = pipeline.execute_failure_contract(
        base,
        float(manifest["frequencies"]["first_frequency_hz"]),
        float(manifest["damping"]["alpha"]),
        contract,
    )
    assert len(failures) == 9
    assert all(not item["failure_any_exception_accepted"] for item in failures.values())
    assert all(not isinstance(item["actual_input"].get("elements"), str) for item in failures.values())
    assert all(not pipeline.validate_failure_record(case_id, item, contract) for case_id, item in failures.items())


def test_pipeline_freeze_and_c4_record() -> None:
    freeze = pipeline.build_pipeline_freeze()
    pipeline.assert_pipeline_unchanged(freeze)
    assert freeze["post_run_pipeline_mutation_allowed"] is False
    assert freeze["post_run_manifest_rewrite_allowed"] is False
    assert json.loads(C4_RECORD.read_text(encoding="utf-8"))["verdict"] == "REJECT_CONTRACT_VIOLATION"


def test_modal_projection_is_in_pipeline_and_replay_has_no_synthetic_fields() -> None:
    contract = pipeline.load_contract()
    phi = np.array([1.0, 0.0])
    mass = np.diag([2.0, 3.0])
    response = np.array([1.0 + 2.0j, 0.0 + 0.0j])
    q, record = pipeline.modal_coordinate(phi, mass, response, phi_source="test", mass_source="test")
    assert q == pytest.approx(2.0 + 4.0j)
    assert record["projection_formula"] == "q = phi^H M x"
    assert "iterations" not in pipeline.replay_fields_from_contract(contract)


def test_c3_manifest_is_rejected_by_semantic_c5_validator() -> None:
    contract = pipeline.load_contract()
    old = json.loads(
        (ROOT / "qualification/0_2_8/wp13_02c3_harmonic_final/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    errors = pipeline.validate_pipeline_evidence(old, contract)
    assert errors
    assert any("energy" in error for error in errors)
    assert any("failure" in error or "missing" in error for error in errors)
    assert any("pipeline" in error or "post-run" in error for error in errors)
    assert any("modal" in error or "replay" in error for error in errors)


def test_positive_schema_fixture_is_valid_and_negative_mutations_fail() -> None:
    contract = pipeline.load_contract()
    freeze = pipeline.build_pipeline_freeze()
    base = pipeline.legacy.build(1)
    old = json.loads(
        (ROOT / "qualification/0_2_8/wp13_02c3_harmonic_final/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    failures = pipeline.execute_failure_contract(
        base,
        float(old["frequencies"]["first_frequency_hz"]),
        float(old["damping"]["alpha"]),
        contract,
    )
    energy = pipeline.energy_metric_from_contract(contract, 1.0 + 0.0j, -1.0 + 0.0j, 2.0, 3.0)
    positive = pipeline.make_c5_microcheck_manifest(contract, freeze, failures, energy)
    schema = json.loads((ROOT / "qualification/0_2_8/wp13_02c5_pipeline.schema.json").read_text(encoding="utf-8"))
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(positive)) == []
    assert pipeline.validate_pipeline_evidence(positive, contract) == []

    negative = copy.deepcopy(positive)
    negative["failure_executions"]["cases"]["unsupported_family"]["actual_input"] = {
        "elements": "PYRAMID5"
    }
    assert pipeline.validate_pipeline_evidence(negative, contract)


def test_each_c5_semantic_negative_guard_is_active() -> None:
    contract = pipeline.load_contract()
    freeze = pipeline.build_pipeline_freeze()
    base = pipeline.legacy.build(1)
    old = json.loads(
        (ROOT / "qualification/0_2_8/wp13_02c3_harmonic_final/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    failures = pipeline.execute_failure_contract(
        base,
        float(old["frequencies"]["first_frequency_hz"]),
        float(old["damping"]["alpha"]),
        contract,
    )
    positive = pipeline.make_c5_microcheck_manifest(
        contract,
        freeze,
        failures,
        pipeline.energy_metric_from_contract(contract, 1.0 + 0.0j, -1.0 + 0.0j, 2.0, 3.0),
    )

    cases = {
        "energy": ("energy_contract", "literal_definition", "wrong"),
        "pipeline_digest": ("pipeline_freeze", "pipeline_combined_digest", "0" * 64),
        "post_run_pipeline": (None, "post_run_pipeline_mutation_allowed", True),
        "post_run_manifest": (None, "post_run_manifest_rewrite_allowed", True),
        "synthetic_iterations": ("replay_pipeline", "runtime_iteration_semantics", "synthetic"),
        "modal_not_frozen": ("modal_coordinate_pipeline", "frozen_pipeline", False),
        "missing_c4": ("historical_owner_records", "WP13-02C4", "missing.json"),
    }
    for name, (parent, key, value) in cases.items():
        mutated = copy.deepcopy(positive)
        if parent is None:
            mutated[key] = value
        else:
            mutated[parent][key] = value
        errors = pipeline.validate_pipeline_evidence(mutated, contract)
        assert errors, name
