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


def test_wp05cde_score_matches_release_progress_ledger() -> None:
    audit = _load(AUDIT)
    progress = _load(QUALIFICATION / "progress.json")

    assert progress["validated_points"] == audit["scores"]["validated_total_after_local_integration"]
    wp05 = cast(dict[str, Any], progress["work_packages"]["WP05"])
    assert wp05["validated_points"] == 5
    assert wp05["status"] == "CLOSED_BOUNDED_WITH_LIMITATIONS"


def test_wp05cde_raw_archives_match_frozen_manifest() -> None:
    audit = _load(AUDIT)
    artifacts = cast(list[dict[str, Any]], audit["raw_artifacts"])

    assert len(artifacts) == 8
    for artifact in artifacts:
        raw_path = ROOT / str(artifact["path"])
        assert raw_path.is_file()
        assert _sha256(raw_path) == artifact["sha256"]
