"""Guards for the prospective 0.2.9 Unified Nonlinear Mechanics baseline."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_9"
DOCS = ROOT / "docs" / "verification" / "0_2_9"


def _load(name: str) -> dict[str, object]:
    return json.loads((QUALIFICATION / name).read_text(encoding="utf-8"))


def test_step_up_baseline_preserves_release_identity_and_registry_boundary() -> None:
    baseline = _load("baseline.json")

    assert baseline["baseline_sha"] == "032c8602e9bb3d7033f0fd696bf0ca7d82257e10"
    assert baseline["release_0_2_8"]["tag"] == "v0.2.8"
    assert baseline["inherited_registry"] == {
        "source": "qualification/0_2_8/consolidated_registry.json",
        "QUALIFIED_BOUNDED": 32,
        "EXPERIMENTAL": 14,
        "NOT_QUALIFIED": 0,
        "total": 46,
        "boundary": "Element/analysis combinations only; mixed workflows and separate capabilities remain outside the 46 records.",
    }


def test_step_up_roadmap_is_frozen_at_one_hundred_points() -> None:
    roadmap = _load("roadmap.json")
    points = [entry["points"] for entry in roadmap["work_packages"]]

    assert [entry["id"] for entry in roadmap["work_packages"]] == [f"WP{index:02d}" for index in range(15)]
    assert sum(points) == 100
    assert roadmap["total_points"] == 100
    assert roadmap["frozen"] is True


def test_step_up_requires_owner_decision_before_j2_geometry_work() -> None:
    decisions = _load("owner_decisions.json")
    decision = decisions["open_decisions"][0]

    assert decision["id"] == "OD-029-01"
    assert decision["status"] == "OPEN"
    assert decision["default_without_owner_approval"] == "D"
    assert [option["id"] for option in decision["options"]] == ["A", "B", "C", "D"]


def test_step_up_and_wp03_documents_are_present_and_status_is_explicit() -> None:
    expected = {
        "README.md",
        "architecture-baseline.md",
        "requirements.md",
        "gate-matrix.md",
        "known-limitations.md",
        "progress.md",
        "owner-decisions.md",
        "wp01-unified-nonlinear-core-contract.md",
        "wp01-b-foundation-evidence.md",
        "wp01-ownership-model.md",
        "wp01-state-transaction-contract.md",
        "wp01-migration-matrix.md",
        "wp01-failure-retry-matrix.md",
        "wp01-gate-matrix.md",
        "wp01-c-load-control-migration.md",
        "wp01-d-continuation-migration.md",
        "wp01-owner-closure.md",
        "wp02-state-checkpoint-contract.md",
        "wp02-compatibility-matrix.md",
        "wp02-failure-matrix.md",
        "wp02-gate-matrix.md",
        "wp02-implementation-plan.md",
        "wp02-b-schema-v2-foundation.md",
        "wp02-c-fixed-adaptive-restart.md",
        "wp02-d-arc-length-restart.md",
        "wp02-d1-material-state-alias.md",
        "wp02-e-independent-closure.md",
        "wp03-robustness-contract.md",
        "wp03-architecture-map.md",
        "wp03-failure-retry-matrix.md",
        "wp03-baseline-campaign.md",
        "wp03-gate-matrix.md",
        "wp03-implementation-plan.md",
        "wp03-b-baseline.md",
        "wp03-b-robustness-authority.md",
    }

    assert {path.name for path in DOCS.glob("*.md")} == expected
    assert "not a release claim" in (DOCS / "README.md").read_text(encoding="utf-8").lower()
    assert "NOT_VALIDATED" in (DOCS / "known-limitations.md").read_text(encoding="utf-8")


def test_wp01_contract_is_prospective_and_preserves_the_open_j2_geometry_decision() -> None:
    contract = _load("wp01_unified_nonlinear_core_contract.json")
    migration = _load("wp01_migration_matrix.json")
    progress = _load("progress.json")

    assert contract["status"] == "PROSPECTIVE_CONTRACT_PHASE"
    assert contract["canonical_equations"]["residual"] == (
        "R(u, lambda, state) = lambda * F_ext - F_internal - F_contact"
    )
    assert contract["canonical_equations"]["tangent"] == ("K_T = K_material + K_geometric + K_contact")
    assert len(contract["prospective_gates"]) == 10
    assert contract["owner_decisions"]["OD-029-01"].startswith("OPEN")
    assert {entry["classification"] for entry in migration["entries"]} == {
        "RETAIN",
        "ADAPT",
        "WRAP",
        "MIGRATE",
        "DEPRECATE_LATER",
        "RESEARCH_COMPATIBILITY",
    }
    assert progress["work_packages"]["WP00"]["status"] == "CLOSED"
    assert progress["work_packages"]["WP01"] == {
        "points": 12,
        "status": "CLOSED",
        "validated_points": 12,
    }
    assert progress["validated_points"] == 22
    closure = _load("wp01_owner_closure.json")
    assert closure["status"] == "CLOSED"
    assert closure["owner_approval_recorded"] is True
    assert closure["auditor_decision"] == "GO_WITH_LIMITATIONS"
    assert closure["score"] == {"awarded": 12, "available": 12}
    assert closure["validated_total"] == {"awarded": 16, "available": 100}
    assert closure["integrity"]["maturity_changed"] is False
    assert progress["work_packages"]["WP02"] == {
        "points": 6,
        "status": "CLOSED",
        "validated_points": 6,
    }
    assert progress["work_packages"]["WP03"] == {
        "points": 7,
        "status": "STAGNATION_LINESEARCH_AUTHORITY",
        "validated_points": 0,
    }
    assert progress["total_points"] == 100
    wp02 = _load("wp02_state_checkpoint_contract.json")
    assert wp02["target_checkpoint_schema_version"] == 2
    assert wp02["v1_compatibility"]["policy"] == "READ_V1_WRITE_V2_BOUNDED"
    wp03 = _load("wp03_robustness_contract.json")
    assert wp03["status"] == "PROSPECTIVE_CONTRACT_FROZEN"
    assert wp03["baseline_sha"] == "ecc09f0bae2dab867c12d7e471860887f6ef0548"
    assert len(wp03["gate_record"]) == 10
    assert all(value == "PROSPECTIVE_NOT_DEMONSTRATED" for value in wp03["gate_record"].values())
    baseline = _load("wp03_baseline_campaign.json")
    assert baseline["status"] == "FROZEN_NOT_EXECUTED"
    assert len(baseline["cases"]) == 16
