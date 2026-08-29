"""Focused governance checks for the 0.2.6 G07 contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "qualification" / "0_2_6"
DOCS = ROOT / "docs" / "verification" / "0_2_6"


def _load(name: str) -> dict[str, Any]:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_g07_contract_is_bounded_and_not_closed() -> None:
    contract = _load("g07_requirements.json")

    assert contract["gate"] == "026-G07"
    assert contract["status"] == "CONTRACT_DEFINED_GATE_NOT_STARTED"
    scope = contract["scope"]
    assert scope["total_lagrangian_elasticity"]["candidate_qualified_families"] == ["TET4", "HEX8"]
    assert scope["total_lagrangian_elasticity"]["research_families"] == ["TET10", "HEX20"]
    assert scope["arc_length"]["target_maturity"] == "PASS_INTERNAL_RESEARCH"
    assert "finite-kinematic J2" in scope["excluded"]


def test_g07_proposed_thresholds_cannot_be_numeric() -> None:
    contract = _load("g07_requirements.json")

    requirements = contract["requirements"]
    proposed = [row for row in requirements if row["threshold"]["status"] == "PROPOSED_OWNER_REVIEW"]
    assert len(proposed) == contract["threshold_governance"]["proposed_owner_review_count"]
    assert proposed
    assert all(row["threshold"]["value"] is None for row in proposed)


def test_g07_matrix_does_not_promote_research_routes() -> None:
    matrix = _load("g07_capability_matrix.json")

    assert matrix["status"] == "CONTRACT_DEFINED_GATE_NOT_STARTED"
    rows = matrix["rows"]
    by_key = {(row["capability"], row["element"]): row for row in rows}
    assert by_key[("ANA-GEOMETRIC-NONLINEAR", "TET4")]["target_maturity"] == "QUALIFIED_BOUNDED_CANDIDATE"
    assert by_key[("ANA-GEOMETRIC-NONLINEAR", "HEX8")]["target_maturity"] == "QUALIFIED_BOUNDED_CANDIDATE"
    assert by_key[("ANA-GEOMETRIC-NONLINEAR", "TET10")]["status"] == "RESEARCH_ONLY"
    assert by_key[("ANA-GEOMETRIC-NONLINEAR", "HEX20")]["status"] == "RESEARCH_ONLY"
    assert by_key[("ANA-ARC-LENGTH", "TET4")]["status"] == "EXPERIMENTAL_NOT_QUALIFIED"
    assert all(row["target_maturity"] != "QUALIFIED" for row in rows)


def test_g06_documentation_matches_machine_readable_gate() -> None:
    gates = _load("gates.json")
    g06 = next(row for row in gates["gates"] if row["id"] == "026-G06")
    gate_doc = (DOCS / "0_2_6_gate_matrix.md").read_text(encoding="utf-8")

    assert g06["status"] == "PASS_WITH_LIMITATIONS"
    assert "| `026-G06` | J2 maturity extension | PASS_WITH_LIMITATIONS |" in gate_doc
    assert "| `026-G06` | J2 maturity extension | NOT_STARTED |" not in gate_doc


def test_g07_gate_references_contract_without_closing() -> None:
    gates = _load("gates.json")
    g07 = next(row for row in gates["gates"] if row["id"] == "026-G07")

    assert g07["status"] == "NOT_STARTED"
    assert "g07_requirements.json" in g07["evidence_ids"]
    assert "g07_capability_matrix.json" in g07["evidence_ids"]
