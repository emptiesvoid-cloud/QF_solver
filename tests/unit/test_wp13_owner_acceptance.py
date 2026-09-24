"""Keep the Owner-approved WP13 award and active point allocation consistent."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_9"
DECISION_PATH = (
    QUALIFICATION
    / "wp13_r2_multifamily"
    / "wp13_owner_acceptance_r2_1.json"
)


def _load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_wp13_owner_award_matches_official_progress_ledger() -> None:
    decision = _load(DECISION_PATH)
    progress = _load(QUALIFICATION / "progress.json")
    owner_decisions = _load(QUALIFICATION / "owner_decisions.json")

    wp13 = cast(dict[str, Any], progress["work_packages"]["WP13"])
    assert decision["status"] == "CLOSED_OWNER_ACCEPTED_WITH_LIMITATIONS"
    assert decision["owner_decision"]["awarded_points"] == "1/1"
    assert decision["owner_decision"]["official_total_before"] == "94/100"
    assert decision["owner_decision"]["official_total_after"] == "95/100"
    assert wp13["points"] == wp13["validated_points"] == 1
    assert wp13["owner_decision_id"] == decision["decision_id"]
    assert progress["validated_points"] == 95
    assert sum(
        int(package["points"])
        for package in cast(dict[str, dict[str, Any]], progress["work_packages"]).values()
    ) == progress["total_points"] == 100
    assert sum(
        int(package["validated_points"])
        for package in cast(dict[str, dict[str, Any]], progress["work_packages"]).values()
    ) == progress["validated_points"]
    assert any(
        item["id"] == decision["decision_id"]
        for item in cast(list[dict[str, Any]], owner_decisions["closed_decisions"])
    )


def test_owner_approved_reduced_allocation_preserves_historical_roadmap() -> None:
    decision = _load(DECISION_PATH)
    progress = _load(QUALIFICATION / "progress.json")
    roadmap = _load(QUALIFICATION / "roadmap.json")
    allocation = cast(dict[str, Any], decision["active_allocation_revision"])

    assert allocation["owner_confirmed"] is True
    assert {key: allocation[key] for key in ("WP13", "WP14", "WP15")} == {
        "WP13": 1,
        "WP14": 1,
        "WP15": 2,
    }
    assert sum(int(allocation[key]) for key in ("WP13", "WP14", "WP15")) == 4
    assert allocation["historical_frozen_roadmap_preserved"] is True
    frozen = {
        item["id"]: item["points"]
        for item in cast(list[dict[str, Any]], roadmap["work_packages"])
    }
    assert frozen["WP13"] == 2
    assert frozen["WP14"] == 2
    assert "WP15" not in frozen
    assert progress["work_packages"]["WP13"]["points"] == 1
    assert progress["work_packages"]["WP14"]["points"] == 1
    assert progress["work_packages"]["WP15"]["points"] == 2


def test_wp13_owner_decision_binds_the_reviewed_contract_and_manifest() -> None:
    decision = _load(DECISION_PATH)
    wp13 = QUALIFICATION / "wp13_r2_multifamily"

    bindings = {
        "contract_sha256": wp13 / "wp13_r2_1_execution_contract.json",
        "execution_record_sha256": wp13 / "wp13_r2_execution_record.json",
        "raw_manifest_sha256": wp13 / "wp13_r2_raw_evidence_manifest.json",
    }
    for field, path in bindings.items():
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == decision[field]
