"""Targeted WP13-02B12 evidence and contract-compliance guards."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from jsonschema import Draft202012Validator

ROOT = Path(__file__).parents[2]
EVIDENCE_DIR = ROOT / "qualification" / "0_2_8" / "wp13_02b12_contract_compliance"
MANIFEST = EVIDENCE_DIR / "manifest.json"
ARCHIVE = EVIDENCE_DIR / "wp13_02b12_arrays.npz"
SCHEMA = ROOT / "qualification" / "0_2_8" / "wp13_02b12_evidence.schema.json"


def _digest(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array, dtype=np.float64).tobytes()).hexdigest()


def test_b12_evidence_schema_and_contract_metrics_are_machine_checked() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(manifest)

    assert manifest["contract_id"] == "WP13-02B4-NEWMARK-MIXED-V2-001"
    assert manifest["contract_sha"] == "8b44792466eacaf1f341a7970502e9b48dbed4e1"
    assert manifest["contract_unchanged"] is True
    assert manifest["gates_unchanged"] is True
    assert manifest["contract_values_single_source_of_truth"] is True
    assert manifest["residual"]["denominator"] == "Fstar"
    assert manifest["residual"]["variable_denominator_used"] is False
    assert manifest["raw_arrays"]["all_required_fields_present"] is True

    with np.load(ARCHIVE, allow_pickle=False) as arrays:
        for name, metadata in manifest["raw_arrays"]["array_manifest"].items():
            assert name in arrays.files
            assert list(arrays[name].shape) == metadata["shape"]
            assert _digest(arrays[name]) == metadata["sha256"]


def test_b12_archives_fit_coefficients_and_replay_step_iterations() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for level in ("T1/20", "T1/40", "T1/80", "T1/160"):
        fit = manifest["fit_coefficients"]["by_level"][level]
        assert all(key in fit["q"] for key in ("c", "s", "fit_residual"))
        assert all(key in fit["probe"] for key in ("c", "s", "fit_residual"))
        assert np.isfinite(fit["q"]["c"])
        assert np.isfinite(fit["q"]["s"])

    replay = manifest["replay_iterations"]
    assert replay["time_grid_identical"] is True
    assert replay["status_sequence_identical"] is True
    assert replay["iterations_per_step_identical"] is True
    assert len(replay["main"]["iterations_per_step"]) == 640
    assert len(replay["replay_1"]["iterations_per_step"]) == 640
    assert len(replay["replay_2"]["iterations_per_step"]) == 640


def test_b12_failure_contract_reports_real_variant_execution_and_blockers() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures = manifest["failure_contract"]
    assert failures["variants_required"] == 27
    assert failures["variants_executed"] == 27
    assert failures["variants_pass"] == 24
    assert failures["categories"]["invalid_dt"]["pass"] is True
    assert failures["categories"]["unsupported_family"]["pass"] is True
    assert set(manifest["decision"]["blockers"]) == {
        "unsupported_damping_unknown_model",
        "invalid_initial_conditions_nonzero_fixed_state",
        "invalid_mixed_interface_family_missing",
    }
    assert failures["silent_fallback"] is False


def test_b12_keeps_distinct_historical_records() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = manifest["historical_records"]
    assert records["owner_gates_preserved"] is True
    assert all(records[key]["present"] for key in ("B5", "B6", "B7", "B8", "B9", "B10", "B11"))
