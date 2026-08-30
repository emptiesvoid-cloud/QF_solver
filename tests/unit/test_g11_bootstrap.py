"""Machine-readable 026-G11 bootstrap contract checks."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "qualification" / "0_2_6"
CONTRACT = DATA / "g11_requirements.json"
MAPPING = DATA / "g11_evidence_mapping.json"
ADVERSARIAL = DATA / "g11_adversarial_cases.json"


def test_g11_candidate_contract_defines_all_failure_categories_without_closeout() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["gate"] == "026-G11"
    assert contract["status"] == "OPEN"
    assert contract["contract_status"] == "OWNER_REVIEWED_CANDIDATE"
    assert contract["official_gate_status"] == "NOT_STARTED"
    assert contract["governance"]["official_gate_closeout"] == "not performed"
    assert contract["governance"]["G04_G08_G07_TL_G09_untouched"] is True
    requirements = {row["id"]: row for row in contract["requirements"]}
    assert set(requirements) == {f"G11-DIAG-{index:03d}" for index in range(1, 9)}
    for row in requirements.values():
        assert row["failure_classes"]
        assert row["expected_behavior"]
        assert row["oracle"]
        assert row["evidence"]
        assert row["status"] in {"READY", "PARTIAL", "PLANNED", "NOT_APPLICABLE"}
    assert contract["policies"]["new"] == []
    assert contract["failure_taxonomy"]["UNCONTROLLED"]["observed_in_reviewed_evidence"] == []
    assert "single cross-route failure envelope" in contract["failure_taxonomy"]["MISSING"]
    envelope = contract["common_failure_envelope"]
    assert envelope["status"] == "OWNER_APPROVED_BOUNDED"
    assert set(envelope["required_fields"]) == {
        "FAILURE_CLASS",
        "ROUTE",
        "EXPECTED_BEHAVIOR",
        "ERROR_TYPE_OR_CODE",
        "STATE_PRESERVED",
        "DETERMINISTIC",
        "NO_NAN_INF",
        "NO_SILENT_PASS",
        "EVIDENCE_ID",
    }
    assert envelope["thresholds"] == "none"
    assert contract["planned_case_specification"].endswith("g11_adversarial_cases.json")
    assert contract["runner"]["path"] == "src/solveur/verification/g11_runner.py"
    assert contract["runner"]["full_campaign_executed"] is False


def test_g11_mapping_preserves_historical_boundaries_and_native_case_limitations() -> None:
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    assert mapping["status"] == "FOCUSED_NATIVE_EVIDENCE"
    assert mapping["official_gate_closeout"] == "DEFERRED"
    assert mapping["other_gates_changed"] is False
    assert len(mapping["mappings"]) >= 8
    for row in mapping["mappings"]:
        assert row["evidence"]
        assert row["requirements"]
        assert row["classification"] in {"READY", "PARTIAL", "PLANNED", "NOT_APPLICABLE"}
        assert row["requalification"]
    assert "four focused native adversarial cases" in mapping["classifications"]["PARTIAL"]
    assert "complete cross-route adversarial campaign" in mapping["classifications"]["PLANNED"]
    assert mapping["future_g11_campaign_gaps"]


def test_g11_owner_review_keeps_four_priority_cases_bounded() -> None:
    cases = json.loads(ADVERSARIAL.read_text(encoding="utf-8"))
    assert cases["status"] == "OWNER_APPROVED_FOR_EXECUTION"
    assert cases["execution_state"] == "NATIVE_EXECUTION_RECORDED"
    assert cases["execution_prohibited_in_this_review"] is False
    assert [case["case_id"] for case in cases["cases"]] == [
        "VNV026-ADV-PLN-001",
        "VNV026-ADV-PLN-002",
        "VNV026-ADV-PLN-003",
        "VNV026-ADV-PLN-004",
    ]
    assert {case["failure_class"] for case in cases["cases"]} == {
        "singular_linear_system",
        "unsupported_load_element_pair",
        "MAX_ITERATIONS",
        "rejected_increment",
    }
    for case in cases["cases"]:
        assert case["status"] == "PLANNED"
        assert "no_nan_inf" in case["oracle"]
        assert "no_silent_pass" in case["oracle"]
        assert case["requirements"]
