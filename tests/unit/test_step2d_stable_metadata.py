"""Guard the stable 0.2.7 metadata reconciliation without rewriting history."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_7"


def _load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_active_stable_metadata_is_reconciled() -> None:
    release_truth = _load("qualification/0_2_7/release_truth.json")
    gates = _load("qualification/0_2_7/gates.json")
    requirements = _load("qualification/0_2_7/requirements.json")

    assert release_truth["target_027"] == {
        "version": "0.2.7",
        "tag": "v0.2.7",
        "tag_status": "EXISTS_AT_PRIOR_SHA",
        "tag_target_sha": "ace411b7326fc31e8109487ce351c002dc993628",
            "branch_candidate_sha": "15fe5f846b803cc02008de36d3c53065d9522807",
        "github_release": "NOT_CREATED",
        "pypi": "NOT_PUBLISHED",
    }
    assert release_truth["level_up_2"]["status"] == "CLOSED"
    assert release_truth["level_up_2"]["level_up_2_progress"] == {"status": "CLOSED", "acquired_percent": 50}
    assert release_truth["level_up_2"]["current_global_progress_percent"] == 100
    assert gates["r0_release_readiness"]["qualification_score"] == "100/100"
    assert gates["r0_release_readiness"]["historical_preclosure_qualification_score"] == "96/100"

    all_requirements = requirements["requirements"] + requirements.get("level_up_requirements", [])
    wp22 = next(item for item in all_requirements if item["work_package"] == "WP22")
    assert wp22["status"] == "PASS_WITH_LIMITATIONS"
    assert wp22["evidence"] == [
        "qualification/0_2_7/r0_release_readiness.json",
        "qualification/0_2_7/step1_release_freeze.json",
    ]


def test_active_surfaces_have_no_stale_prerelease_identity() -> None:
    active_paths = (
        ROOT / "docs/demarrage/installation.md",
        ROOT / "prochaines_etapes.md",
        ROOT / "docs/document_registry.json",
        ROOT / "scripts/capability_registry_v2.py",
        ROOT / "scripts/migrate_capability_registry_v2.py",
    )
    assert all("0.2.7a0" not in path.read_text(encoding="utf-8") for path in active_paths)


def test_historical_prerelease_identity_is_preserved() -> None:
    r0 = _load("qualification/0_2_7/r0_release_readiness.json")
    step1 = _load("qualification/0_2_7/step1_release_freeze.json")

    assert r0["candidate"]["tag"] == "v0.2.7a0"
    assert r0["qualification_integrity"]["score"] == "96/100"
    assert step1["version_before"] == "0.2.7a0"
