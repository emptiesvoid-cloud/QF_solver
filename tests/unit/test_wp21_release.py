"""Focused WP21 release-truth and compatibility contracts."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_7"


def _load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_wp21_state_records_bounded_cleanup_without_maturity_promotion() -> None:
    state = _load("qualification/0_2_7/wp21_state.json")

    assert state["status"] == "PASS_WITH_LIMITATIONS"
    assert state["version"] == "0.2.7a0"
    assert state["branch"] == "codex/0.2.7-foundation"
    assert state["registry"]["public_capability_count"] == 33
    assert state["registry"]["unjustified_promotions"] == 0
    assert state["functional_source_changed"] is False
    assert state["fem_formulation_changed"] is False
    assert state["tolerances_changed"] is False
    assert state["ready_for_owner_release"] is True


def test_wp21_release_truth_keeps_parent_and_candidate_roles_distinct() -> None:
    truth = _load("qualification/0_2_7/wp21_final_release_truth.json")

    assert truth["candidate_version"] == "0.2.7a0"
    assert truth["parent_release"]["version"] == "0.2.6a0"
    assert truth["parent_release"]["qualification_snapshot"] != truth["parent_release"]["release_source_snapshot"]
    assert truth["publication_state"] == {
        "tag": "NOT_CREATED",
        "github_release": "NOT_CREATED",
        "pypi": "NOT_PUBLISHED",
    }
    assert truth["owner_decisions_preserved"] is True


def test_wp21_evidence_paths_and_registry_counts_are_current() -> None:
    state = _load("qualification/0_2_7/wp21_state.json")
    truth = _load("qualification/0_2_7/wp21_final_release_truth.json")
    registry = _load("qualification/0_2_7/capability_registry_v2.json")

    assert len(registry["public_capability_ids"]) == 33
    assert len(registry["combination_record_ids"]) == 46
    assert len(registry["records"]) == 79
    assert all((ROOT / path).is_file() for path in truth["evidence"].values())
    assert (ROOT / state["provenance"]["golden_replay_evidence"]).is_file()
    assert (QUALIFICATION / "wp21_public_document_audit.json").is_file()
    assert (QUALIFICATION / "golden" / "wp21_replay_evidence.json").is_file()


def test_wp21_golden_replay_has_no_mismatch_and_keeps_expected_failure() -> None:
    records = _load("qualification/0_2_7/golden/wp21_replay_evidence.json")

    assert len(records) == 9
    assert sum(record["verdict"] == "PASS" for record in records) == 8
    assert sum(record["verdict"] == "EXPECTED_FAILURE_PASS" for record in records) == 1
    assert all(record["source_sha"] for record in records)
    assert all(record["result_digest"] for record in records)
