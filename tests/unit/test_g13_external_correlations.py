"""Contract checks for the 0.2.6 external-correlation consolidation."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_6"


def _load(name: str) -> dict:
    return json.loads((QUALIFICATION / name).read_text(encoding="utf-8"))


def test_g13_registry_has_controlled_classification_counts() -> None:
    registry = _load("g13_external_evidence_registry.json")

    assert registry["gate"] == "026-G13"
    assert registry["status"] == "PASS_WITH_LIMITATIONS"
    assert registry["owner_closeout_status"] == "PASS_WITH_LIMITATIONS"
    assert registry["generated_from_sha"] == "86467fd76a52512d7c9daabbc4d822ac99f96ad0"
    assert registry["worktree_dirty_at_inventory"] is False
    assert registry["new_external_cases_executed"] == 0
    assert len(registry["records"]) == 18
    assert sum(registry["classification_counts"].values()) == len(registry["records"])
    assert registry["classification_counts"]["INTERNAL_ONLY"] == 0


def test_g13_registry_excludes_non_active_evidence_from_claims() -> None:
    registry = _load("g13_external_evidence_registry.json")
    by_id = {record["evidence_id"]: record for record in registry["records"]}

    assert by_id["G08-EULER-TENSION-SUPERSEDED"]["status"] == "SUPERSEDED"
    assert by_id["G08-CODEASTER-026-NOT-COMPARABLE"]["status"] == "NOT_COMPARABLE"
    assert by_id["G04-CODEASTER-026-MISSING"]["status"] == "MISSING"
    assert by_id["G05-HIGH-ORDER-EXTERNAL-026-MISSING"]["status"] == "MISSING"


def test_g13_coverage_and_gap_matrices_are_complete() -> None:
    coverage = _load("g13_external_coverage_matrix.json")
    gaps = _load("g13_missing_evidence_matrix.json")

    assert coverage["gate"] == "026-G13"
    assert len(coverage["records"]) == 15
    assert len({row["capability"] for row in coverage["records"]}) == 15
    assert len(gaps["gaps"]) == 8
    assert {row["priority"] for row in gaps["gaps"]} == {
        "BLOCKING",
        "VALUABLE_NONBLOCKING",
        "LOW_VALUE",
    }
    assert all(row["owner_classification"] == "OWNER_MISSING_ACCEPTED" for row in gaps["gaps"])
    assert all(not row["blocks_current_qualified_claim"] for row in gaps["gaps"])


def test_g13_gate_links_only_its_own_aggregation_artifacts() -> None:
    gates = _load("gates.json")
    gate = next(item for item in gates["gates"] if item["id"] == "026-G13")

    assert gate["status"] == "PASS_WITH_LIMITATIONS"
    assert gate["evidence_ids"] == [
        "g13_external_evidence_registry.json",
        "g13_external_coverage_matrix.json",
        "g13_missing_evidence_matrix.json",
        "g13_owner_closeout.json",
        "0_2_6_g13_external_correlations.md",
    ]
    assert next(item for item in gates["gates"] if item["id"] == "026-G07")["status"] == "NOT_STARTED"


def test_g13_owner_closeout_has_no_current_blocking_gap() -> None:
    closeout = _load("g13_owner_closeout.json")

    assert closeout["status"] == "PASS_WITH_LIMITATIONS"
    assert closeout["owner_blocking"] == []
    assert closeout["public_qualified_capabilities_without_sufficient_external_evidence"] == []
    assert closeout["superseded_excluded"] == ["G08-EULER-TENSION-SUPERSEDED"]
    assert closeout["validation"]["full_regression"] == "SKIPPED_BY_POLICY"
