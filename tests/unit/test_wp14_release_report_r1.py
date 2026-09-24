"""Fail-closed contract for the WP14 R1 Owner-review result."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "qualification" / "0_2_9" / "wp14" / "wp14_r1_final.json"


def test_wp14_final_record_remains_hold_without_awarding_points() -> None:
    report = json.loads(RECORD.read_text(encoding="utf-8"))

    assert report["final_status"] == "HOLD_OWNER_REVIEW"
    assert report["ledger"]["wp14_official_points"] == "0/1"
    assert report["ledger"]["official_total_after_execution"] == "95/100"
    assert report["ledger"]["owner_award_required"] is True
    assert report["owner_review"]["no_implicit_score_award"] is True


def test_wp14_final_record_fails_closed_on_release_gates() -> None:
    report = json.loads(RECORD.read_text(encoding="utf-8"))
    gates = report["gates"]

    assert gates["WP14-G01-PROVENANCE"]["status"] == "PASS"
    assert gates["WP14-G02-LEDGER"]["status"] == "PASS"
    assert gates["WP14-G04-STANDARD-QUALITY"]["status"] == "FAIL"
    assert gates["WP14-G05-ENGINEERING"]["status"] == "FAIL"
    assert gates["WP14-G06-DOCUMENTATION"]["status"] == "FAIL"
    assert gates["WP14-G07-PACKAGE-AND-PUBLIC-SOURCE"]["status"] == "FAIL"
    assert gates["WP14-G08-PLATFORM-MATRIX"]["status"] == "NOT_RUN"
    assert gates["WP14-G09-RELEASE-AUTHORITY"]["status"] == "OWNER_GATED"


def test_wp14_candidate_branch_push_is_separate_from_qualification_and_merge() -> None:
    provenance = json.loads(RECORD.read_text(encoding="utf-8"))["provenance"]

    assert provenance["wp14_branch_pushed"] is True
    assert provenance["wp14_branch_pushed_during_qualification"] is False
    assert provenance["post_qualification_push_sha"] == "3e41cbc315b6790279199ef3251e6d3122a60c12"
    assert provenance["merge_performed"] is False


def test_wp14_committed_review_artifacts_do_not_embed_workstation_paths() -> None:
    text = RECORD.read_text(encoding="utf-8")
    report = (ROOT / "docs" / "verification" / "0_2_9" / "wp14-r1-release-qualification-report.md").read_text(encoding="utf-8")

    for content in (text, report):
        assert "C:\\Users\\" not in content
        assert "/home/" not in content
