"""WP13-02C6b sequencing guards; no harmonic campaign."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_wp13_02c5_harmonic_pipeline as c5
import run_wp13_02c6b_pipeline as c6b


ROOT = Path(__file__).resolve().parents[2]
PARTIAL_C6 = ROOT / "qualification/0_2_8/wp13_02c6_harmonic_final/wp13_02c6_harmonic_arrays.npz"


def _candidate() -> dict:
    contract = c5.load_contract()
    base = c5.legacy.build(1)
    failures = c5.execute_failure_contract(base, 1.0, 0.0, contract)
    freeze = c6b.build_c6c_pre_run_freeze()
    energy = c5.energy_metric_from_contract(contract, 1.0 + 0.0j, -1.0 + 0.0j, 2.0, 3.0)
    return {
        "schema_version": 6,
        "record_id": "C6B-TEST-CANDIDATE",
        "work_package": "WP13-02C6",
        "contract_id": contract["contract_id"],
        "contract_sha256": c6b.sha256_file(c5.CONTRACT_PATH),
        "repo_sha": c6b.git_revision(),
        "environment": {"test": "c6b"},
        "contract_values_single_source_of_truth": True,
        "benchmark_inputs": {"connected_components": 1},
        "conditioning": {"status": "PASS"},
        "frequencies": {"ratios": [0.0]},
        "damping": {"model": "Rayleigh"},
        "raw_complex_responses": {"array_key": "runtime_responses"},
        "oracle_responses": {"dense_array_key": "oracle_dense_responses"},
        "amplitude_phase": {"amplitudes_array_key": "amplitudes"},
        "modal_coordinate": {"complex": {"array_key": "modal_coordinate_complex"}},
        "modal_coordinate_pipeline": {
            "frozen_pipeline": True,
            "phi_source": "test",
            "phi_digest": "a" * 64,
            "mass_source": "test",
            "mass_digest": "b" * 64,
            "normalization": "mass-normalized eigenvector",
            "projection_formula": "q = phi^H M x",
        },
        "residuals": {"vector_array_key": "residual_vectors"},
        "static_limit": {"error": 0.0},
        "resonance": {"label": "FRF_PEAK_IN_FROZEN_FREQUENCY_CAMPAIGN"},
        "interface_metrics": {"state_collection_independent": True},
        "energy_contract": energy,
        "replay_arrays": {"fields": c5.replay_fields_from_contract(contract)},
        "replay_comparison": {"full_array_comparison": True},
        "replay_pipeline": {
            "fields": c5.replay_fields_from_contract(contract),
            "runtime_iteration_semantics": "not_declared_by_harmonic_contract",
            "synthetic_fields": [],
        },
        "failure_executions": {
            "required": 9,
            "executed": len(failures),
            "pass": sum(bool(item["pass"]) for item in failures.values()),
            "silent_fallback_allowed": False,
            "cases": failures,
        },
        "pipeline_freeze": freeze,
        "post_run_pipeline_mutation_allowed": False,
        "post_run_manifest_rewrite_allowed": False,
        "historical_owner_records": {"WP13-02C4": "qualification/0_2_8/wp13_02c4_owner_gate.json"},
        "digests": {"test": "c" * 64},
        "gate_decisions": {"test": True},
        "historical_records_preserved": True,
        "evidence_schema_valid": False,
        "semantic_validator_valid": False,
        "integrity": {"numerical_source_changed": False},
    }


def test_valid_candidate_promotes_only_after_both_validations() -> None:
    candidate = _candidate()
    contract = c5.load_contract()
    assert c6b.validate_candidate_manifest(candidate) == []
    assert c6b.validate_c6_semantics(candidate, contract) == []
    final = c6b.promote_candidate(candidate, post_run_digest=candidate["pipeline_freeze"]["pipeline_combined_digest"])
    assert c6b.validate_final_manifest(final) == []
    assert final["evidence_schema_valid"] is True
    assert final["semantic_validator_valid"] is True


def test_invalid_candidate_does_not_claim_final_validity() -> None:
    candidate = _candidate()
    candidate["evidence_schema_valid"] = True
    errors = c6b.validate_candidate_manifest(candidate)
    assert any("evidence_schema_valid" in error for error in errors)
    final, record = c6b.finalize_candidate(candidate, c5.load_contract())
    assert final is None
    assert record is not None
    assert record["stage"] == "schema"


def test_semantic_failure_has_no_qualified_manifest() -> None:
    candidate = _candidate()
    candidate["energy_contract"]["literal_definition"] = "wrong"
    errors = c6b.validate_c6_semantics(candidate, c5.load_contract())
    assert errors
    record = c6b.partial_failure_record("semantic_validation", errors)
    assert record["status"] == "FAIL/BLOCKED"
    assert record["final_claim_allowed"] is False
    assert record["qualified_manifest_created"] is False


def test_failure_contract_failure_is_recorded_without_qualification() -> None:
    candidate = _candidate()
    candidate["failure_executions"]["cases"]["missing_mass"]["pass"] = False
    final, record = c6b.finalize_candidate(candidate, c5.load_contract())
    assert final is None
    assert record is not None
    assert record["stage"] == "failure_contract"
    assert record["final_claim_allowed"] is False


def test_replay_failure_is_recorded_without_qualification() -> None:
    candidate = _candidate()
    candidate["replay_pipeline"]["fields"] = []
    final, record = c6b.finalize_candidate(candidate, c5.load_contract())
    assert final is None
    assert record is not None
    assert record["stage"] == "replay"


def test_freeze_mismatch_is_blocked() -> None:
    freeze = c6b.build_c6c_pre_run_freeze()
    broken = copy.deepcopy(freeze)
    broken["pipeline_component_digests"]["c6_campaign_driver"] = "0" * 64
    with pytest.raises(c6b.C6bComplianceError, match="component digest"):
        c6b.assert_c6c_pipeline_unchanged(broken)
    candidate = _candidate()
    candidate["pipeline_freeze"]["pipeline_combined_digest"] = "0" * 64
    final, record = c6b.finalize_candidate(candidate, c5.load_contract())
    assert final is None
    assert record is not None
    assert record["stage"] == "freeze"


def test_final_manifest_and_npz_are_write_once(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    archive_path = tmp_path / "arrays.npz"
    c6b.write_final_manifest_once(manifest_path, {"status": "PASS"})
    with pytest.raises(c6b.C6bComplianceError, match="rewrite"):
        c6b.write_final_manifest_once(manifest_path, {"status": "MUTATED"})
    c6b.write_archive_once(archive_path, {"x": [1.0]})
    with pytest.raises(c6b.C6bComplianceError, match="rewrite"):
        c6b.write_archive_once(archive_path, {"x": [2.0]})


def test_c6_partial_evidence_and_status_record_are_preserved() -> None:
    status = json.loads(c6b.C6_STATUS_RECORD_PATH.read_text(encoding="utf-8"))
    before = hashlib.sha256(PARTIAL_C6.read_bytes()).hexdigest()
    assert status["c6_status"] == "BLOCKED_SCHEMA_SEQUENCE"
    assert status["c6_final_evidence"] is False
    assert hashlib.sha256(PARTIAL_C6.read_bytes()).hexdigest() == before


def test_c6c_prospective_digest_is_not_the_old_c5_digest() -> None:
    freeze = c6b.build_c6c_pre_run_freeze()
    assert freeze["pipeline_combined_digest"] != "180c6d48a8613b8b4e082c13725a293d4aef28f405c5055093bff14645867389"
    assert len(freeze["pipeline_combined_digest"]) == 64
    record = json.loads(c6b.C6C_FREEZE_RECORD_PATH.read_text(encoding="utf-8"))
    assert c6b.validate_c6c_freeze_record(record) == []
