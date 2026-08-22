"""Guardrails for the accepted-to-stable maturity gate."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "qualification" / "stable_promotion_criteria_0_2_1.json"


def test_stable_promotion_registry_has_nine_common_gates() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert payload["policy"]["promotion_is_never_automatic"] is True
    criteria = payload["common_criteria"]
    assert [item["id"] for item in criteria] == [f"ST-C0{index}" for index in range(1, 10)]
    assert all(item["required"] for item in criteria)


def test_stable_requires_owner_decision_and_closed_recommendations() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rules = payload["decision_rules"]
    assert "ST-C01..ST-C09" in rules["stable"]
    assert "critical recommendation" in rules["stable"]
    assert payload["promotion_record"]["next_step"] == "ST-01 recommendation closure ledger"


def test_stable_requires_three_independent_cases_and_one_percent_error_limit() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    criteria = {item["id"]: item for item in payload["common_criteria"]}
    assert criteria["ST-C04"]["minimum_cases"] == 3
    assert payload["policy"]["primary_engineering_error_limit"] == 0.01


def test_engineering_relative_error_limits_are_capped_at_one_percent() -> None:
    payload = json.loads(
        (ROOT / "qualification" / "maturity_criteria_0_2_1.json").read_text(
            encoding="utf-8"
        )
    )
    for scope in payload["scopes"]:
        for criterion in scope.get("criteria", []):
            for assertion in criterion.get("assertions", []):
                path = assertion.get("path", "").lower()
                expected = assertion.get("expected")
                if assertion.get("op") != "less_equal" or not isinstance(expected, (int, float)):
                    continue
                if "modal_error_percent" in path:
                    assert expected <= 1.0, (scope["scope"], criterion["id"], path)
                elif "load_increment_policy" not in path and "mesh_increment" not in path and any(
                    token in path for token in ("error", "difference", "increment", "rms", "drift")
                ):
                    assert expected <= 0.01, (scope["scope"], criterion["id"], path)
