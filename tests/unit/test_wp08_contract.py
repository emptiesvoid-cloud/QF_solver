"""Targeted contract checks for the WP08 WEDGE6 static vertical slice."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "qualification" / "0_2_7"


def _load(relative_path: str) -> object:
    return json.loads((DATA / relative_path).read_text(encoding="utf-8"))


def test_wp08_state_matches_catalog_and_evidence() -> None:
    state = _load("wp08_state.json")
    catalog = _load("vnv_v2/wp08_cases.json")
    evidence = _load("vnv_v2/wp08_evidence.json")

    assert isinstance(state, dict)
    assert isinstance(catalog, list)
    assert isinstance(evidence, list)
    assert state["status"] == "PASS"
    assert state["public_maturity"] == "EXPERIMENTAL"
    assert state["public_qualification"] == "DEFERRED"
    assert state["case_count"] == len(catalog) == len(evidence) == 15
    assert len({case["case_id"] for case in catalog}) == 15
    assert {item["verdict"] for item in evidence} == {"PASS", "EXPECTED_FAILURE_PASS"}
    assert sum(item["verdict"] == "PASS" for item in evidence) == 14
    assert sum(item["verdict"] == "EXPECTED_FAILURE_PASS" for item in evidence) == 1
    assert all(item["source_sha"] == state["evidence_source_sha"] for item in evidence)
    assert state["verdict_counts"] == {
        "PASS": 14,
        "EXPECTED_FAILURE_PASS": 1,
        "FAIL": 0,
        "SKIPPED_EXTERNAL_UNAVAILABLE": 0,
    }


def test_wp08_catalog_keeps_static_scope_and_expected_failure_explicit() -> None:
    catalog = _load("vnv_v2/wp08_cases.json")

    assert isinstance(catalog, list)
    assert {case["element"] for case in catalog} == {"WEDGE6"}
    assert {case["analysis"] for case in catalog} == {"linear_static"}
    assert all(case["execution_tier"] == "T1" for case in catalog)
    inverted = next(case for case in catalog if case["case_id"] == "WP08-INVERTED")
    assert inverted["expected_failure"] == "WEDGE6_JACOBIAN_CERTIFICATE_INVALID"
    assert inverted["oracle"]["type"] == "FAILURE_EXPECTATION"
