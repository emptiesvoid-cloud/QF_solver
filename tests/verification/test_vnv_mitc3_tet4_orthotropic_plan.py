"""Regression checks for the 2026-08-22 V&V plan and evidence registry."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "qualification" / "vnv" / "vnv_plan_mitc3_tet4_orthotropic_2026-08-22.json"
ADDENDUM = ROOT / "qualification" / "reviews" / "owner_validation_addendum_mitc3_orthotropic_2026-08-22.json"
TL_TICKETS = ROOT / "qualification" / "tickets" / "tet4_total_lagrangian_phase2_2026-08-22.json"


def load_registry() -> dict[str, object]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_vnv_registry_references_existing_evidence() -> None:
    registry = load_registry()
    scopes = registry["scopes"]
    assert isinstance(scopes, list)
    assert len(scopes) == 4
    for scope in scopes:
        assert isinstance(scope, dict)
        evidence_paths = scope["evidence_paths"]
        assert isinstance(evidence_paths, list)
        assert evidence_paths
        assert all((ROOT / str(path)).is_file() for path in evidence_paths)


def test_vnv_registry_preserves_tet4_tl_gate() -> None:
    registry = load_registry()
    scopes = registry["scopes"]
    assert isinstance(scopes, list)
    tet4_tl = next(scope for scope in scopes if scope["id"] == "tet4-total-lagrangian-structural-v2")
    assert tet4_tl["current_owner_decision"] == "more_evidence_required"
    assert tet4_tl["technical_status"] == "PASS_RESEARCH_BUT_NOT_STABLE"
    measurements = tet4_tl["measurements"]
    assert isinstance(measurements, dict)
    assert measurements["stable_gate"] == "BLOCKED"
    assert float(measurements["h5_euler_error"]) > 0.01


def test_vnv_registry_keeps_one_percent_evidence_for_stable_bounded_scopes() -> None:
    registry = load_registry()
    scopes = registry["scopes"]
    assert isinstance(scopes, list)
    stable_ids = {
        "mitc3-laminate-dynamic-thin-planar",
        "mitc3-laminate-static-curved-mixed-transverse",
        "orthotropic-solid-tet4-tet10-static",
    }
    for scope in scopes:
        if scope["id"] not in stable_ids:
            continue
        measurements = scope["measurements"]
        assert isinstance(measurements, dict)
        assert (
            measurements.get("one_percent_gate") in {"PASS", "PASS_FOR_TET4_FINAL_AND_TET10"}
            or measurements.get("fine_errors_under_one_percent") is True
        )


def test_owner_addendum_contains_only_the_confirmed_scopes() -> None:
    addendum = json.loads(ADDENDUM.read_text(encoding="utf-8"))
    decisions = addendum["decisions"]
    assert {row["scope"] for row in decisions} == {
        "mitc3-laminate-dynamic-thin-planar",
        "mitc3-laminate-static-curved-mixed-transverse",
        "orthotropic-solid-tet4-tet10-static",
    }
    assert addendum["status"] == "owner_confirmed_applied_pending_final_audit"


def test_tet4_tl_phase_two_tickets_keep_promotion_blocked() -> None:
    tickets = json.loads(TL_TICKETS.read_text(encoding="utf-8"))
    assert tickets["status"] == "research_resource_limited"
    assert tickets["current_maturity"] == "research"
    assert tickets["current_decision"] == "more_evidence_required"
    assert len(tickets["tickets"]) == 10
    assert tickets["tickets"][-1]["status"] == "blocked_until_independent_review"
