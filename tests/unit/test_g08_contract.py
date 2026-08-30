"""Controlled contract checks for the 0.2.6 linear-buckling gate bootstrap."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "qualification" / "0_2_6"
DOCS = ROOT / "docs" / "verification" / "0_2_6"


def _load(name: str) -> dict[str, object]:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_g08_contract_records_owner_closeout_status() -> None:
    contract = _load("g08_requirements.json")
    assert contract["gate"] == "026-G08"
    assert contract["status"] == "CONTRACT_EXECUTED_OWNER_CLOSED_WITH_LIMITATIONS"
    scope = contract["scope"]
    assert scope["families_supported_by_route"] == ["TET4", "TET10", "HEX8", "HEX20"]
    assert scope["first_mode_only"] is True
    assert contract["gate_boundary"]["current_gate_status"] == "PASS_WITH_LIMITATIONS"
    assert contract["dependencies"]["not_required_before_execution"] == ["026-G07"]


def test_g08_requirements_cover_policies_without_inventing_bands() -> None:
    contract = _load("g08_requirements.json")
    requirements = contract["requirements"]
    ids = {row["id"] for row in requirements}
    assert ids == {f"G08-{index:03d}" for index in range(1, 10)}
    approved = [row for row in requirements if row["threshold"]["status"] == "OWNER_APPROVED_BOUNDED"]
    assert len(approved) == 5
    assert contract["threshold_governance"]["status"] == "OWNER_APPROVED_BOUNDED"
    assert contract["threshold_governance"]["proposed_owner_review_count"] == 0
    assert "cannot be changed after observing results" in contract["threshold_governance"]["rule"]


def test_g08_owner_review_preserves_bounded_scope_before_execution_closeout() -> None:
    review = _load("g08_owner_contract_review.json")
    assert review["status"] == "OWNER_APPROVED_BOUNDED_CONTRACT_NOT_CLOSED"
    assert review["start_sha"] == "4145f1f42ed5aec513ccf05e215e16e590132546"
    assert review["functional_code_changed"] is False
    assert review["gate_closure_granted"] is False
    assert review["decisions"]["mesh_refinement"]["minimum_compatible_levels"] == 3
    assert review["decisions"]["mode_quality"]["scope"] == "first mode only"


def test_g08_case_registry_maps_cases_to_requirements_and_states() -> None:
    contract = _load("g08_requirements.json")
    requirements = {row["id"] for row in contract["requirements"]}
    registry = _load("g08_case_registry.json")
    cases = registry["cases"]
    assert len({row["case_id"] for row in cases}) == len(cases)
    assert {row["status"] for row in cases} == {"READY", "PLANNED", "NOT_APPLICABLE", "NOT_SUPPORTED"}
    assert all(set(row["requirements"]).issubset(requirements) for row in cases)
    assert registry["gate"] == "026-G08"
    assert sum(row["status"] == "READY" for row in cases) == 3
    assert sum(row["status"] == "PLANNED" for row in cases) == 9
    assert sum(row["status"] == "NOT_APPLICABLE" for row in cases) == 2
    assert sum(row["status"] == "NOT_SUPPORTED" for row in cases) == 2
    referenced = {req for row in cases for req in row["requirements"]}
    assert referenced == requirements


def test_g08_owner_closeout_is_attached_to_gate_and_documented() -> None:
    closeout = _load("g08_owner_closeout.json")
    assert closeout["status"] == "PASS_WITH_LIMITATIONS"
    assert closeout["execution_source_sha"] == "6589443e1404a2749ac6c0a9b911f00dd9cb8753"
    assert closeout["functional_code_changed"] is False
    assert closeout["family_decisions"]["TET4"]["decision"] == "QUALIFIED_BOUNDED"
    assert closeout["family_decisions"]["TET10"]["decision"] == "PASS_WITH_LIMITATIONS"
    assert closeout["family_decisions"]["HEX8"]["decision"] == "PASS_WITH_LIMITATIONS"
    assert closeout["family_decisions"]["HEX20"]["decision"] == "MORE_EVIDENCE_REQUIRED"
    gates = json.loads((DATA / "gates.json").read_text(encoding="utf-8"))
    g08 = next(row for row in gates["gates"] if row["id"] == "026-G08")
    assert g08["status"] == "PASS_WITH_LIMITATIONS"
    assert "g08_requirements.json" in g08["evidence_ids"]
    assert "g08_case_registry.json" in g08["evidence_ids"]
    assert "g08_owner_contract_review.json" in g08["evidence_ids"]
    assert "g08_execution_evidence.json" in g08["evidence_ids"]
    assert "g08_calculix_correlation.json" in g08["evidence_ids"]
    assert "g08_owner_closeout.json" in g08["evidence_ids"]
    document = (DOCS / "0_2_6_g08_contract.md").read_text(encoding="utf-8")
    assert "`026-G08` is **PASS_WITH_LIMITATIONS**" in document
    assert "Owner closeout" in document


def test_g08_closeout_preserves_external_and_mesh_limitations() -> None:
    closeout = _load("g08_owner_closeout.json")
    assert closeout["external_evidence"]["CalculiX"]["HEX20"] == "BLOCKED_EXTERNAL_TOOL"
    assert closeout["external_evidence"]["Code_Aster"] == "SKIPPED_NOT_COMPARABLE"
    assert "HEX20" not in closeout["qualified_bounded_scope"]["families"]
    assert "G08-005" in closeout["requirements"]["satisfied_bounded"]
