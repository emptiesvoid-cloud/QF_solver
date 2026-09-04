"""Focused S3 expanded-validation matrix contracts."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "qualification" / "0_2_7" / "s3_validation_matrix.json"


def _load() -> dict:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def test_s3_matrix_has_bounded_high_value_case_set() -> None:
    matrix = _load()
    cases = matrix["new_cases"]

    assert matrix["gate"] == "S3"
    assert matrix["status"] == "PASS_WITH_LIMITATIONS"
    assert len(cases) == 24
    assert len({case["case_id"] for case in cases}) == len(cases)
    assert matrix["counts"]["fail"] == 0
    assert matrix["counts"]["promotions"] == 0
    assert matrix["governance"]["progress_change"] == 0


def test_s3_cases_cover_invariants_and_fail_closed_outcomes() -> None:
    matrix = _load()
    cases = matrix["new_cases"]
    statuses = {case["execution_status"] for case in cases}

    assert {"displacement", "reaction_equilibrium", "energy", "finite"}.issubset(
        {item for case in cases for item in case["invariants"]}
    )
    assert {"EXPECTED_FAILURE_PASS", "TARGETED_REPLAY_PASS"}.issubset(statuses)
    assert all(case.get("evidence_refs") for case in cases)
    assert all(case["maturity_impact"] in {"KEEP", "BOUND_MORE_STRICTLY"} for case in cases)
    assert {case["expected_failure"] for case in cases if case["execution_status"] == "EXPECTED_FAILURE_PASS"} == {
        "NON_CONVERGENCE",
        "UNSUPPORTED_CAPABILITY",
        "INVALID_INPUT",
        "UNKNOWN_ELEMENT",
    }


def test_s3_replay_external_and_c3_policies_are_explicit() -> None:
    matrix = _load()

    assert matrix["replay"]["deterministic"] is True
    assert matrix["replay"]["nan_inf_free"] is True
    assert matrix["replay"]["expected_failures_preserved"] is True
    assert matrix["external_vv"]["no_invented_values"] is True
    assert matrix["claim_policy"]["qualification_is_non_transitive"] is True
    assert matrix["claim_policy"]["c3_10m_speedup_public_qualified"] is False
    assert matrix["governance"]["maturity_promoted"] is False


def test_s3_evidence_references_exist() -> None:
    matrix = _load()
    refs = {
        ref
        for case in matrix["new_cases"]
        for ref in case["evidence_refs"]
    }
    refs.update(matrix["external_vv"]["evidence_refs"])

    assert all((ROOT / ref).is_file() for ref in refs)


def test_s3_is_registered_without_changing_weighted_progress() -> None:
    matrix = _load()
    manifest = json.loads((ROOT / "qualification" / "0_2_7" / "manifest.json").read_text(encoding="utf-8"))
    index = json.loads((ROOT / "qualification" / "0_2_7" / "level_up_2_index.json").read_text(encoding="utf-8"))
    state = json.loads((ROOT / "qualification" / "0_2_7" / "level_up_2_state.json").read_text(encoding="utf-8"))
    gates = json.loads((ROOT / "qualification" / "0_2_7" / "gates.json").read_text(encoding="utf-8"))

    assert matrix["global_progress_percent"] == 96
    assert manifest["s3_release_pre_gate"]["source_of_truth"] == "qualification/0_2_7/s3_validation_matrix.json"
    assert index["s3_release_pre_gate"]["new_case_count"] == 24
    assert state["s3_release_pre_gate"]["global_progress_unchanged"] is True
    assert gates["s3_release_pre_gate"]["status"] == "PASS_WITH_LIMITATIONS"
