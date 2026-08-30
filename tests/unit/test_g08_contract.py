"""Controlled contract checks for the 0.2.6 linear-buckling gate bootstrap."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "qualification" / "0_2_6"
DOCS = ROOT / "docs" / "verification" / "0_2_6"


def _load(name: str) -> dict[str, object]:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_g08_contract_is_defined_but_gate_is_not_started() -> None:
    contract = _load("g08_requirements.json")
    assert contract["gate"] == "026-G08"
    assert contract["status"] == "CONTRACT_DEFINED_GATE_NOT_STARTED"
    scope = contract["scope"]
    assert scope["families_supported_by_route"] == ["TET4", "TET10", "HEX8", "HEX20"]
    assert scope["first_mode_only"] is True
    assert contract["gate_boundary"]["current_gate_status"] == "NOT_STARTED"
    assert contract["dependencies"]["not_required_before_execution"] == ["026-G07"]


def test_g08_requirements_cover_policies_without_inventing_bands() -> None:
    contract = _load("g08_requirements.json")
    requirements = contract["requirements"]
    ids = {row["id"] for row in requirements}
    assert ids == {f"G08-{index:03d}" for index in range(1, 10)}
    proposed = [row for row in requirements if row["threshold"]["status"] == "PROPOSED_OWNER_REVIEW"]
    assert len(proposed) == 5
    assert all(row["threshold"]["value"] is None for row in proposed)
    assert contract["threshold_governance"]["status"] == "OWNER_REVIEW_REQUIRED"
    assert "No proposed or null policy" in contract["threshold_governance"]["rule"]


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


def test_g08_contract_is_attached_to_unclosed_gate_and_documented() -> None:
    gates = json.loads((DATA / "gates.json").read_text(encoding="utf-8"))
    g08 = next(row for row in gates["gates"] if row["id"] == "026-G08")
    assert g08["status"] == "NOT_STARTED"
    assert "g08_requirements.json" in g08["evidence_ids"]
    assert "g08_case_registry.json" in g08["evidence_ids"]
    document = (DOCS / "0_2_6_g08_contract.md").read_text(encoding="utf-8")
    assert "`026-G08` is **NOT_STARTED**" in document
    assert "not numerical evidence" in document
