"""Contract checks for the G10 Lot 1 research audit record."""

import json
from pathlib import Path


ROOT = Path(__file__).parents[2]
MATRIX_PATH = ROOT / "qualification" / "0_2_6" / "g10_research_audit_matrix.json"
GATES_PATH = ROOT / "qualification" / "0_2_6" / "gates.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _gate_record(gates: dict, gate_id: str) -> dict:
    return next(gate for gate in gates["gates"] if gate["id"] == gate_id)


def test_g10_audit_matrix_has_controlled_provenance_and_scope() -> None:
    matrix = _load_json(MATRIX_PATH)

    assert matrix["gate"] == "026-G10"
    assert matrix["status"] == "IN_PROGRESS"
    assert matrix["lot"] == "G10-LOT1"
    assert matrix["provenance"]["execution_source_sha"] == (
        "51b3a7c8ace6731830109984a01ce31f79c44401"
    )
    assert matrix["provenance"]["execution_worktree_dirty"] is False
    assert matrix["audit_findings"]["functional_source_changed"] is False
    assert matrix["audit_findings"]["numerical_regression_detected"] is False


def test_g10_audit_matrix_covers_routes_requirements_and_cases() -> None:
    matrix = _load_json(MATRIX_PATH)

    routes = matrix["route_inventory"]
    requirements = matrix["requirements"]
    cases = matrix["bounded_campaign"]["cases"]

    assert len(routes) == 10
    assert len({route["id"] for route in routes}) == len(routes)
    assert len(requirements) == 9
    assert len({requirement["id"] for requirement in requirements}) == 9
    assert len(cases) == 12
    assert matrix["bounded_campaign"]["result"] == {
        "tests_passed": 171,
        "tests_failed": 0,
        "tests_skipped": 0,
        "campaign_type": "targeted",
        "full_regression": "SKIPPED_BY_POLICY",
    }


def test_g10_audit_does_not_promote_deferred_research_routes() -> None:
    matrix = _load_json(MATRIX_PATH)
    decision = matrix["decision"]

    assert "finite_kinematic_j2" in decision["not_qualified"]
    assert "arc_length_continuation" in decision["experimental_only"]
    assert "j2_plus_geometry_plus_contact" in decision["experimental_only"]
    assert decision["owner_closeout"] is False
    assert matrix["external_correlation"]["status"] == "DEFERRED_LIMITATION"


def test_g10_owner_review_selects_only_comparable_high_value_routes() -> None:
    matrix = _load_json(MATRIX_PATH)
    review = matrix["owner_review"]
    selection = review["external_selection"]

    assert review["status"] == "PARTIAL"
    assert selection["selected_count"] == 2
    assert [row["route"] for row in selection["selected_routes"]] == [
        "arc_length_continuation",
        "total_lagrangian_elasticity",
    ]
    assert all(row["owner_gate"] == "026-G07" for row in selection["selected_routes"])
    assert any(row["route"] == "finite_kinematic_j2" for row in selection["not_selected"])
    assert review["no_threshold_changes"] is True
    assert review["g07_reopened"] is False


def test_g10_gate_registry_points_to_controlled_evidence() -> None:
    matrix = _load_json(MATRIX_PATH)
    gates = _load_json(GATES_PATH)
    gate = _gate_record(gates, "026-G10")

    assert gate["status"] == "IN_PROGRESS"
    assert gate["title"] == "Advanced Nonlinear / Research Audit"
    assert gate["evidence_ids"] == [
        "g10_research_audit_matrix.json",
        "0_2_6_g10_lot1.md",
        "0_2_6_g10_owner_review_lot1.md",
        "g10_selected_external_evidence.json",
        "g10_selected_external_manifest.json",
        "0_2_6_g10_selected_external_campaign.md",
    ]
    assert matrix["decision"]["gate_status"] == gate["status"]
