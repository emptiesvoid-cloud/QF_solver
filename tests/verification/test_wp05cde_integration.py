"""Validate the Owner-approved, bounded WP05-C/D/E integration record."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_9"
AUDIT = QUALIFICATION / "wp05cde_integration" / "wp05_cde_integration_audit.json"


def _load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_wp05cde_integration_records_owner_scope_and_score() -> None:
    audit = _load(AUDIT)
    scores = cast(dict[str, Any], audit["scores"])
    owner = cast(dict[str, Any], audit["owner_decision"])
    governance = cast(dict[str, Any], audit["governance"])

    assert audit["status"] == "LOCAL_GOVERNING_INTEGRATION_COMPLETE_UNPUSHED"
    assert owner["status"] == "APPROVED_WITH_LIMITATIONS"
    assert owner["wp05e_acceptance"].startswith("ACCEPT 1/1 CANDIDATE")
    assert scores["wp05c"] == scores["wp05d"] == scores["wp05e"] == "1/1"
    assert scores["wp05_after_local_integration"] == "5/5"
    assert scores["validated_total_before"] == 58
    assert scores["validated_total_after_local_integration"] == 61
    assert scores["remote_published_total"] == 58
    assert governance["production_mechanics_changed"] is False
    assert governance["thresholds_changed"] is False
    assert governance["historical_fail_closed_preserved"] is True
    assert governance["full_repository_suite_run"] is False


def test_wp05cde_cross_family_gates_and_external_limit_are_explicit() -> None:
    audit = _load(AUDIT)
    comparisons = cast(dict[str, Any], audit["cross_family_comparisons"])
    owner = cast(dict[str, Any], audit["owner_decision"])

    assert comparisons["all_pass"] is True
    assert comparisons["displacement_relative_delta"] <= comparisons["displacement_limit"]
    assert comparisons["reaction_resultant_relative_delta"] <= comparisons["reaction_resultant_limit"]
    assert comparisons["reaction_moment_relative_delta"] <= comparisons["reaction_moment_limit"]
    assert comparisons["strain_energy_relative_delta"] <= comparisons["strain_energy_limit"]
    assert comparisons["historical_common_sigma_xx_relative_delta"] <= comparisons["historical_common_sigma_xx_limit"]
    assert comparisons["external_solver_correlation"] == "NOT_RUN_DEFERRED"
    assert "DEFERRED_TO_FUTURE_VALIDATION" in owner["external_solver_comparison"]


def test_release_ledger_includes_wp05_and_wp07_owner_awards() -> None:
    audit = _load(AUDIT)
    progress = _load(QUALIFICATION / "progress.json")
    owner_decisions = _load(QUALIFICATION / "owner_decisions.json")
    roadmap = _load(QUALIFICATION / "roadmap.json")
    decisions = cast(list[dict[str, Any]], owner_decisions["closed_decisions"])
    wp07d = next(item for item in decisions if item["id"] == "OD-029-WP07-D-R1-01")
    wp07e = next(item for item in decisions if item["id"] == "OD-029-WP07-E-R2-01")

    wp05_total = audit["scores"]["validated_total_after_local_integration"]
    assert wp05_total == 61
    assert wp07d["consolidated_ledger_before"] == wp05_total
    assert wp07d["consolidated_ledger_after"] == 64
    assert wp07e["consolidated_ledger_before"] == wp07d["consolidated_ledger_after"]
    assert wp07e["consolidated_ledger_after"] == 66
    # The Owner decision records the historical WP07-E checkpoint; the active
    # consolidated ledger includes later WP09-WP13 awards.
    assert progress["validated_points"] >= wp07e["consolidated_ledger_after"]
    roadmap_allocation_sum = sum(
        item["points"] for item in roadmap["work_packages"]
    )
    assert roadmap_allocation_sum == roadmap["total_points"] == 100
    assert owner_decisions["ledger_reconciliation"]["frozen_roadmap_allocations_sum"] == roadmap_allocation_sum
    assert owner_decisions["ledger_reconciliation"]["allocation_mismatch_status"] == "CONSISTENT"
    wp05 = cast(dict[str, Any], progress["work_packages"]["WP05"])
    assert wp05["validated_points"] == 5
    assert wp05["status"] == "CLOSED_BOUNDED_WITH_LIMITATIONS"
    wp07 = cast(dict[str, Any], progress["work_packages"]["WP07"])
    assert wp07["validated_points"] == 10
    assert wp07["status"] == "OWNER_ACCEPTED_A_TO_E_BOUNDED_WITH_LIMITATIONS"
    assert wp07["prior_owner_award_preserved"] is True
    assert wp07["requalification_status"] == "OWNER_ACCEPTED_R2_5_SCOPED_REQUALIFICATION_WITH_LIMITATIONS"
    assert wp07["requalification_decision_id"] == "OD-029-WP07-D-R2.5-01"
    assert wp07["requalification_source_sha"] == "3c749f30f95a53b4eaadb2159accb4349e6d7ee7"
    wp08 = cast(dict[str, Any], progress["work_packages"]["WP08"])
    assert wp08["validated_points"] == 8
    assert wp08["prior_owner_award_preserved"] is True
    assert wp08["requalification_status"] == (
        "OPEN_FRICTIONAL_CONTACT_REQUALIFICATION_PENDING_FROZEN_CONTRACT_AND_EXECUTION_AUTHORIZATION"
    )
    assert progress["total_points"] == 100


def test_wp05cde_raw_archives_match_frozen_manifest() -> None:
    audit = _load(AUDIT)
    artifacts = cast(list[dict[str, Any]], audit["raw_artifacts"])

    assert len(artifacts) == 8
    for artifact in artifacts:
        raw_path = ROOT / str(artifact["path"])
        assert raw_path.is_file()
        assert _sha256(raw_path) == artifact["sha256"]
