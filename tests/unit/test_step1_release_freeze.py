"""Stable release identity and provenance guards for Step 1."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_7"


def _load(name: str) -> dict:
    return json.loads((QUALIFICATION / name).read_text(encoding="utf-8"))


def test_stable_release_identity_and_claim_boundaries() -> None:
    record = _load("step1_release_freeze.json")
    manifest = _load("manifest.json")
    registry = _load("capability_registry_v2.json")
    gates = _load("gates.json")

    assert record["release"] == "0.2.7"
    assert record["version_before"] == "0.2.7a0"
    assert record["tag"] == "v0.2.7"
    assert record["owner_qualification"] == "COMPLETE_100_PERCENT"
    assert record["claim_boundaries"]["wedge6_static"] == "EXPERIMENTAL"
    assert record["claim_boundaries"]["calculix"] == "NOT_COMPARABLE"
    assert manifest["target_version"] == "0.2.7"
    assert manifest["target_tag"] == "v0.2.7"
    assert manifest["pypi_published"] is False
    assert registry["applicable_version"] == "0.2.7"
    assert all(item["applicable_version"] == "0.2.7" for item in registry["records"])
    assert gates["level_up_2"]["status"] == "CLOSED"
    assert gates["level_up_2"]["global_accounting"]["current_global_progress_percent"] == 100
    wp09 = next(item for item in gates["level_up_2"]["gates"] if item["work_package"] == "LU2-WP09")
    assert wp09["status"] == "PASS_WITH_LIMITATIONS"


def test_historical_candidate_records_are_preserved() -> None:
    record = _load("step1_release_freeze.json")
    r0 = _load("r0_release_readiness.json")
    wp21 = _load("wp21_final_release_truth.json")

    assert record["release_integrity"]["historical_evidence_rewritten"] is False
    assert r0["candidate"]["tag"] == "v0.2.7a0"
    assert wp21["candidate_version"] == "0.2.7a0"
    assert record["historical_provenance"]["foreign_change_stash"].startswith("stash@{0}")
