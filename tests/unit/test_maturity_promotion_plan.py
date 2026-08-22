"""Consistency tests for the evidence-extension plan of release 0.2.1a0."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "qualification" / "element_analysis_matrix.json"
PLAN = ROOT / "qualification" / "maturity_promotion_0_2_1.json"
REQUIREMENTS = ROOT / "qualification" / "requirements.json"


def _matrix_scopes() -> dict[str, str]:
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    scopes: dict[str, str] = {}
    for family in matrix["families"].values():
        for entry in family.values():
            if not isinstance(entry, dict) or not entry.get("scope"):
                continue
            scope = str(entry["scope"])
            status = str(entry["status"])
            previous = scopes.setdefault(scope, status)
            assert previous == status, f"ambiguous status for {scope}"
    return scopes


def test_promotion_plan_covers_every_supported_matrix_scope_once() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    matrix_scopes = _matrix_scopes()
    planned = [str(entry["scope"]) for entry in plan["scope_plans"]]
    supplementary = [str(entry["scope"]) for entry in plan["supplementary_material_scopes"]]
    expected = {
        scope for scope, status in matrix_scopes.items() if status != "unsupported"
    }

    assert len(planned + supplementary) == len(set(planned + supplementary))
    matrix_planned = set(planned) | {scope for scope in supplementary if scope in matrix_scopes}
    assert matrix_planned == expected
    assert plan["policy"]["new_capabilities_allowed"] is False


def test_promotion_plan_statuses_and_templates_match_the_authoritative_matrix() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    matrix_scopes = _matrix_scopes()
    templates = plan["evidence_templates"]
    allowed_targets = {"stable", "owner_accepted", "experimental", "research"}

    for entry in plan["scope_plans"]:
        scope = str(entry["scope"])
        assert entry["current_status"] == matrix_scopes[scope]
        assert entry["target_status"] in allowed_targets
        assert entry["template"] in templates
        assert templates[entry["template"]]["required"]
        assert entry["priority"] in {"P1", "P2", "P3"}

    for entry in plan["supplementary_material_scopes"]:
        scope = str(entry["scope"])
        if scope not in matrix_scopes:
            continue
        assert entry["current_status"] == matrix_scopes[scope]
        assert entry["target_status"] in allowed_targets
        assert entry["template"] in templates


def test_supplementary_material_scopes_exist_in_the_requirement_registry() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    requirements = json.loads(REQUIREMENTS.read_text(encoding="utf-8"))
    known_scopes = set(requirements["scopes"])

    for entry in plan["supplementary_material_scopes"]:
        assert entry["scope"] in known_scopes
        assert entry["template"] in plan["evidence_templates"]
