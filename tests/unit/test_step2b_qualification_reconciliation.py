"""Guard the active 0.2.7 qualification view without rewriting history."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_7"
ACTIVE_VIEWS = (
    ROOT / "README.md",
    ROOT / "docs/verification/0_2_7/README.md",
    ROOT / "docs/verification/0_2_7/0_2_7_master_plan.md",
    ROOT / "docs/verification/0_2_7/0_2_7_gate_matrix.md",
    ROOT / "docs/verification/0_2_7/0_2_7_progress_tracker.md",
)


def _load(name: str) -> dict:
    return json.loads((QUALIFICATION / name).read_text(encoding="utf-8"))


def test_active_release_views_are_owner_complete() -> None:
    manifest = _load("manifest.json")
    progress = _load("progress.json")
    state = _load("level_up_2_state.json")
    index = _load("level_up_2_index.json")
    gates = _load("gates.json")

    assert manifest["wp22_status"] == "PASS_WITH_LIMITATIONS"
    assert manifest["level_up_2_scope"]["current_global_progress_percent"] == 100
    assert manifest["level_up_2_scope"]["current_work_package"] == "STEP2D"
    assert progress["current_work_package"] == "STEP2D"
    assert progress["current_release_audit"] == "STEP2D_CI_READINESS"
    assert state["current_work_package"] == "STEP2D"
    assert state["next_work_package"] == "STEP3"
    assert index["current_work_package"] == "STEP2D"
    assert index["next_work_package"] == "STEP3"

    active_wp22 = next(
        item for item in progress["level_up_work_packages"] if item["id"] == "WP22"
    )
    assert active_wp22["status"] == "PASS_WITH_LIMITATIONS"
    active_wp09 = next(
        item for item in gates["level_up_2"]["gates"] if item["work_package"] == "LU2-WP09"
    )
    assert active_wp09["status"] == "PASS_WITH_LIMITATIONS"

    # Public entry points avoid internal score/status vocabulary; the detailed
    # qualification views carry the exact owner-complete accounting.
    assert "100/100" not in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "100/100" not in (ROOT / "docs/verification/0_2_7/README.md").read_text(encoding="utf-8")
    for path in ACTIVE_VIEWS[2:]:
        text = path.read_text(encoding="utf-8")
        assert "100/100" in text
        assert "PASS_WITH_LIMITATIONS" in text


def test_historical_preclosure_views_remain_immutable_and_labeled() -> None:
    r0 = _load("r0_release_readiness.json")
    manifest = _load("manifest.json")
    gates = _load("gates.json")

    assert r0["candidate"]["tag"] == "v0.2.7a0"
    assert r0["qualification_integrity"]["score"] == "96/100"
    assert manifest["level_up_scope"]["historical_only"] is True
    assert manifest["level_up_scope"]["current_progress_percent"] == 96
    assert gates["level_up"]["historical_only"] is True
    assert any("WP22_PLANNED" in value for value in (gates["foundation_status"],)) is False
