from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "qualification/0_2_9/wp14/wp14_r1_release_contract.json"


def test_wp14_r1_contract_is_frozen_to_governing_candidate_and_active_allocation() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["contract_id"] == "QF-029-WP14-RELEASE-QUALIFICATION-R1"
    assert contract["status"] == "FROZEN_PROSPECTIVE"
    assert contract["baseline"] == {
        "branch": "0.2.9-unified-nonlinear",
        "source_sha": "b2485f98260c7ca9892997eefa3a327637d83cd3",
        "contract_freeze_branch": "codex/wp14-release-qualification",
    }
    assert contract["score_context"]["active_allocation"] == {
        "WP13": 1,
        "WP14": 1,
        "WP15": 2,
    }
    assert contract["score_context"]["official_total_before_wp14"] == "95/100"
    assert contract["score_context"]["wp14_official_points_before_review"] == "0/1"
    assert contract["score_context"]["owner_award_required"] is True


def test_wp14_r1_contract_covers_all_release_quality_jobs_without_authorizing_publish() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in contract["frozen_gates"]}

    assert set(gates) == {
        "WP14-G01-PROVENANCE",
        "WP14-G02-LEDGER",
        "WP14-G03-CLAIMS-AND-REGISTRY",
        "WP14-G04-STANDARD-QUALITY",
        "WP14-G05-ENGINEERING",
        "WP14-G06-DOCUMENTATION",
        "WP14-G07-PACKAGE-AND-PUBLIC-SOURCE",
        "WP14-G08-PLATFORM-MATRIX",
        "WP14-G09-RELEASE-AUTHORITY",
    }
    assert "python qf_solver.py verify-all --profile engineering" in gates["WP14-G05-ENGINEERING"]["commands"]
    assert "mkdocs build --strict -f .github/pages/mkdocs.yml" in gates["WP14-G06-DOCUMENTATION"]["commands"]
    assert contract["scope"]["production_mechanics_changes_allowed"] is False
    assert any("release tag" in item for item in contract["scope"]["excluded_owner_gates"])
    assert contract["final_status_rule"]["official_award"].startswith("Never derived")


def test_wp14_r1_score_context_matches_machine_ledger_owner_record_and_historical_roadmap() -> None:
    progress = json.loads((ROOT / "qualification/0_2_9/progress.json").read_text(encoding="utf-8"))
    decisions = json.loads((ROOT / "qualification/0_2_9/owner_decisions.json").read_text(encoding="utf-8"))
    roadmap = json.loads((ROOT / "qualification/0_2_9/roadmap.json").read_text(encoding="utf-8"))
    decision = next(item for item in decisions["closed_decisions"] if item["id"] == "OD-029-WP13-R2.1-01")
    progress_doc = (ROOT / "docs/verification/0_2_9/progress.md").read_text(encoding="utf-8")

    assert progress["validated_points"] == 95
    assert sum(item["validated_points"] for item in progress["work_packages"].values()) == 95
    assert progress["work_packages"]["WP14"] == {"points": 1, "status": "NOT_STARTED", "validated_points": 0}
    assert decision["active_allocation_revision"]["allocations"] == {"WP13": 1, "WP14": 1, "WP15": 2}
    assert decision["active_allocation_revision"]["status"] == "OWNER_CONFIRMED"
    assert decision["global_official_total_after"] == "95/100"
    assert {item["id"]: item["points"] for item in roadmap["work_packages"] if item["id"] in {"WP13", "WP14"}} == {
        "WP13": 2,
        "WP14": 2,
    }
    assert "95 / 100" in progress_doc
    assert "WP14 | 1 | Not started" in progress_doc
