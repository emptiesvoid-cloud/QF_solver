"""Targeted WP11 J2 evidence-contract tests."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "run_wp11_j2_closure.py"
SPEC = importlib.util.spec_from_file_location("run_wp11_j2_closure", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_wp11_case_catalog_is_complete_and_deterministic() -> None:
    assert MODULE.validate_case_catalog(MODULE.WP11_CASES) == []
    assert len(MODULE.WP11_CASES) == 9
    assert len({case["case_id"] for case in MODULE.WP11_CASES}) == len(MODULE.WP11_CASES)
    assert set().union(*(set(case["element_families"]) for case in MODULE.WP11_CASES)) == set(
        MODULE.ELEMENT_FAMILIES
    )


def test_wp11_catalog_rejects_missing_tolerance_and_duplicate_ids() -> None:
    invalid = [dict(MODULE.WP11_CASES[0]), dict(MODULE.WP11_CASES[0])]
    invalid[0].pop("tolerance")
    errors = MODULE.validate_case_catalog(invalid)
    assert any("missing fields: tolerance" in error for error in errors)
    assert "case IDs are not unique" in errors


def test_wp11_increments_are_explicitly_characterization_only() -> None:
    increment_case = next(case for case in MODULE.WP11_CASES if "INCREMENT" in case["case_id"])
    assert increment_case["tolerance"] == "NO_NEW_UNIVERSAL_THRESHOLD; report family-specific sensitivity"
    assert increment_case["expected_failure"] == "coarse difficult paths may be non-convergent"


def test_wp11_does_not_promote_finite_kinematic_j2() -> None:
    assert all("FINITE" not in case["capability_refs"] for case in MODULE.WP11_CASES)


def test_wp11_generated_evidence_is_complete_and_replay_digest_is_stable() -> None:
    evidence_path = ROOT / "qualification/0_2_7/wp11_j2_evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["status"] == "PASS_WITH_LIMITATIONS"
    assert len(evidence["source_sha"]) == 40
    assert evidence["source_dirty_at_execution"] is False
    assert evidence["summary"]["unexpected_failures"] == 0
    assert evidence["results"]["newton"]["status"] == "PASS_CHARACTERIZED"
    assert evidence["results"]["increment_refinement"]["status"] == "PASS_CHARACTERIZED"
    assert set(evidence["results"]["families"]) == set(MODULE.ELEMENT_FAMILIES)
    assert MODULE._digest(MODULE._stable(evidence["results"])) == evidence["result_digest"]
