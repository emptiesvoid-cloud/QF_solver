"""Targeted governance checks for LU2-WP08 scope decisions."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_7"


def _load(relative_path: str) -> dict:
    return json.loads((QUALIFICATION / relative_path).read_text(encoding="utf-8"))


def test_scope_decisions_are_explicit_and_non_promoting() -> None:
    matrix = _load("lu2_wp08_decision_matrix.json")

    assert matrix["status"] == "PASS_WITH_LIMITATIONS"
    assert matrix["source_sha"] == "8ef34e345f970879548a4dfdce4ac5ba32c11bda"
    assert matrix["new_capability_exposed"] is False
    assert matrix["maturity_promoted"] is False
    decisions = {item["axis"]: item for item in matrix["decisions"]}
    assert decisions["mixed_meshes"]["decision"] == "DEFER"
    assert decisions["WEDGE15"]["decision"] == "DEFER"
    assert decisions["PYRAMID5"]["decision"] == "DEFER"
    assert decisions["HEX8R"]["decision"] == "RESEARCH_ONLY"
    assert decisions["SRI"]["decision"] == "RESEARCH_ONLY"
    assert decisions["BBAR"]["decision"] == "RESEARCH_ONLY"


def test_scope_state_and_boundary_are_consistent() -> None:
    matrix = _load("lu2_wp08_decision_matrix.json")
    state = _load("lu2_wp08_state.json")

    assert state["status"] == matrix["status"]
    assert state["decision_matrix"] == "qualification/0_2_7/lu2_wp08_decision_matrix.json"
    assert state["implemented_new_element"] is False
    assert state["fem_formulation_changed"] is False
    assert state["global_progress"]["after_percent"] == 74
    assert matrix["aggregate_decisions"]["HEX8_next_generation"] == "PROTOTYPE_LATER"
    assert matrix["scope_boundary"]["no_mixed_mesh_framework"] is True
    assert "WEDGE15 implementation" in matrix["scope_boundary"]["deferred_to_0_2_8_plus"]


def test_candidate_families_are_not_active_descriptors() -> None:
    descriptors = (ROOT / "src" / "solveur" / "compatibility" / "descriptors.py").read_text(encoding="utf-8")
    element_registry = (ROOT / "src" / "solveur" / "elements" / "registry.py").read_text(encoding="utf-8")

    assert '"WEDGE15"' not in descriptors
    assert '"PYRAMID5"' not in descriptors
    assert '"WEDGE15"' not in element_registry
    assert '"PYRAMID5"' not in element_registry
