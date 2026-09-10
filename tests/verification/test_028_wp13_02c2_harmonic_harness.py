"""Targeted WP13-02C2 harness/evidence checks; no production campaign run."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import run_wp13_02c2_harmonic_harness as harness  # noqa: E402


MANIFEST_PATH = ROOT / "qualification/0_2_8/wp13_02c2_harmonic_harness/manifest.json"
OLD_MANIFEST_PATH = ROOT / "qualification/0_2_8/wp13_02c_harmonic_v1/manifest.json"
ARCHIVE_PATH = ROOT / "qualification/0_2_8/wp13_02c2_harmonic_harness/wp13_02c2_harness_arrays.npz"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_c2_positive_evidence_schema_and_old_campaign_negative_guard() -> None:
    manifest = _manifest()
    old_manifest = json.loads(OLD_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert harness.validate_evidence(manifest) == []
    old_errors = harness.validate_evidence(old_manifest)
    assert old_errors
    assert manifest["source_campaign_conformance"] == "NONCONFORMING_UNDER_C2_SCHEMA"
    assert manifest["old_campaign_schema_missing_fields"]


def test_interface_collection_is_independent_and_energy_formula_is_fixed() -> None:
    manifest = _manifest()
    rows = manifest["interface_metrics"]["frequency_rows"]
    assert manifest["contract_values_single_source_of_truth"] is True
    assert manifest["interface_metrics"]["state_collection_independent"] is True
    assert manifest["interface_metrics"]["continuity_hardcoded"] is False
    assert manifest["interface_metrics"]["continuity_tautological"] is False
    assert manifest["interface_metrics"]["energy_normalization_formula"] == "||Ffree||2 * ||x||2"
    assert "norm(F_free)*norm(x)" in manifest["interface_metrics"]["energy_normalization_source"]
    for frequency_row in rows.values():
        for metric in frequency_row.values():
            assert metric["independent_state_collection"] is True
            assert metric["continuity_hardcoded"] is False
            assert metric["continuity_tautological"] is False
            assert metric["energy_denominator"] == metric["ffree_norm"] * metric["x_l2_norm"]
            assert metric["energy_relative"] >= 0.0


def test_replay_comparator_covers_interface_and_status_fields() -> None:
    manifest = _manifest()
    required = {
        "complex displacement",
        "complex reactions",
        "full residual",
        "amplitude",
        "phase",
        "interface left/right states",
        "interface continuity",
        "interface forces",
        "interface work/energy",
        "status",
    }
    for comparison in manifest["replay_comparison"]["comparisons"]:
        assert comparison["pass"] is True
        assert required.issubset(comparison["fields_compared"])
        assert comparison["status_identical"] is True


def test_failure_cases_require_strict_provenance_matches() -> None:
    cases = _manifest()["failure_executions"]["cases"]
    assert len(cases) == 9
    for case in cases.values():
        assert case["executed"] is True
        assert case["input_digest"]
        assert case["execution_path"]
        assert case["type_match"] is True
        assert case["message_match"] is True
        assert case["path_match"] is True
        assert case["failure_any_exception_accepted"] is False
        assert case["pass"] is True


def test_provenance_modal_coordinate_and_archive_are_complete() -> None:
    manifest = _manifest()
    archive = np.load(ARCHIVE_PATH, allow_pickle=False)
    assert manifest["provenance_freeze"]["pre_run_freeze_valid"] is True
    assert manifest["provenance_freeze"]["numerical_campaign_executed"] is False
    assert len(manifest["provenance_freeze"]["evaluator_pre_run_digest"]) == 64
    modal = manifest["modal_coordinate"]
    for key in ("modal_coordinate_complex", "modal_coordinate_amplitude", "modal_coordinate_phase"):
        assert key in archive.files
    assert modal["definition"]["projection_formula"] == "q = phi^H M x"
    assert modal["definition"]["first_mode_dominated_claim_allowed"] is False
    for key in ("raw_complex_responses", "oracle_responses", "replay_arrays"):
        assert manifest[key]
