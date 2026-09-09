"""Contracts for the cumulative 0.2.8 machine-readable registry."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "qualification" / "0_2_8" / "consolidated_registry.json"


def _registry() -> dict[str, object]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def test_consolidated_registry_reconciles_the_46_source_combinations() -> None:
    registry = _registry()
    combinations = registry["combination_registry"]
    assert combinations["total"] == 46
    assert combinations["state_counts"] == {
        "QUALIFIED_BOUNDED": 32,
        "EXPERIMENTAL": 14,
        "NOT_QUALIFIED": 0,
    }
    assert len(combinations["records"]) == 46
    assert len({row["capability_id"] for row in combinations["records"]}) == 46
    assert combinations["not_qualified_combination"] is None


def test_internal_feasibility_is_separate_from_public_combinations() -> None:
    registry = _registry()
    kernels = registry["internal_research_kernels"]
    pyramid = next(row for row in kernels if row["element_family"] == "PYRAMID5")
    assert pyramid["public_registered"] is False
    assert pyramid["status"] == "FEASIBLE_CONTINUE"
    assert all(row["element_family"] != "PYRAMID5" for row in registry["combination_registry"]["records"])


def test_mixed_and_research_workflows_are_not_inflated_into_46_combinations() -> None:
    registry = _registry()
    workflows = registry["separate_workflows"]
    assert {row["record_kind"] for row in workflows} == {
        "mixed_workflow_qualification",
        "mixed_workflow_capability",
        "internal_feasibility_kernel",
        "separate_experimental_capability",
        "bounded_performance_evidence",
        "experimental_capability",
    }
    assert registry["combination_registry"]["total"] == 46
