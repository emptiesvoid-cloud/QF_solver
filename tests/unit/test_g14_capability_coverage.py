"""Focused contracts for the 0.2.6 final capability-coverage audit."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "qualification" / "capability_registry.json"
G14_PATH = ROOT / "qualification" / "0_2_6" / "g14_capability_coverage.json"
CLEANUP_PATH = ROOT / "qualification" / "0_2_6" / "g14_release_cleanup_items.json"
GATES_PATH = ROOT / "qualification" / "0_2_6" / "gates.json"
G07_PATH = ROOT / "qualification" / "0_2_6" / "g07_owner_closeout.json"
G08_PATH = ROOT / "qualification" / "0_2_6" / "g08_owner_final_review.json"
G13_PATH = ROOT / "qualification" / "0_2_6" / "g13_owner_closeout.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_g14_classes_cover_exactly_the_public_registry() -> None:
    registry = _load(REGISTRY_PATH)
    g14 = _load(G14_PATH)
    public_ids = set(registry["public_capability_ids"])
    classes = g14["coverage"]
    classified = [capability_id for values in classes.values() for capability_id in values]

    assert g14["status"] == "PASS_WITH_LIMITATIONS"
    assert g14["registry_count"] == len(registry["capabilities"]) == 33
    assert g14["public_count"] == len(public_ids) == 33
    assert g14["public_element_analysis_combinations"] == len(registry["public_analysis_combinations"]) == 44
    assert len(classified) == len(set(classified))
    assert set(classified) == public_ids


def test_g14_records_no_capability_gap_and_keeps_cleanup_explicit() -> None:
    g14 = _load(G14_PATH)
    cleanup = _load(CLEANUP_PATH)

    assert g14["checks"]["missing_from_registry"] == []
    assert g14["checks"]["missing_implementation"] == []
    assert g14["checks"]["owner_claim_conflicts"] == []
    assert cleanup["capability_gaps_blocking_g14"] == []
    assert cleanup["full_regression_run_in_this_audit"] is False
    assert {item["id"] for item in cleanup["items"]} == {
        "G14-CLEAN-001",
        "G14-CLEAN-002",
        "G14-CLEAN-003",
        "G14-CLEAN-004",
        "G14-CLEAN-005",
        "G14-CLEAN-006",
        "G14-CLEAN-007",
        "G14-CLEAN-008",
        "G14-CLEAN-009",
    }


def test_g14_gate_is_closed_with_g15_still_open() -> None:
    gates = _load(GATES_PATH)["gates"]
    by_id = {gate["id"]: gate for gate in gates}

    assert by_id["026-G14"]["status"] == "PASS_WITH_LIMITATIONS"
    assert by_id["026-G14"]["full_regression"] == "SKIPPED_BY_POLICY"
    assert by_id["026-G15"]["status"] == "NOT_STARTED"


def test_g14_preserves_sensitive_owner_status_guardrails() -> None:
    g14 = _load(G14_PATH)
    g07 = _load(G07_PATH)
    g08 = _load(G08_PATH)
    g13 = _load(G13_PATH)
    guardrails = g14["public_status_guardrails"]

    assert guardrails["G07_TL_HEX8"] == g07["route_dispositions"]["TL_HEX8"]
    assert guardrails["G07_ARC_002"] == g07["route_dispositions"]["ARC002_REFINED_MESH_COMPARABILITY"]
    assert guardrails["G08_HEX8_BUCKLING"] == g08["family_decisions"]["HEX8"]["decision"]
    assert guardrails["G13"] == g13["status"]
    assert guardrails["G10_FINITE_KINEMATIC_J2"] == "NOT_QUALIFIED"
    assert guardrails["G10_COUPLED_ROUTES"] == "EXPERIMENTAL_OR_NOT_QUALIFIED"
