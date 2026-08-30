"""Controlled 0.2.6 G04 contract and case-mapping checks."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "qualification" / "0_2_6"
CONTRACT_PATH = DATA_ROOT / "g04_requirements.json"
MAPPING_PATH = DATA_ROOT / "g04_case_mapping.json"
EVIDENCE_PATH = DATA_ROOT / "g04_execution_evidence.json"
CASE_REGISTRY_PATH = DATA_ROOT / "case_registry.json"
CAPABILITY_PATH = ROOT / "qualification" / "capability_registry.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_g04_contract_is_controlled_and_linear_only() -> None:
    contract = _load(CONTRACT_PATH)

    assert contract["schema_version"] == 1
    assert contract["gate"] == "026-G04"
    assert contract["status"] == "OPEN"
    assert contract["contract_status"] == "CONTROLLED_CANDIDATE"
    assert contract["scope"]["analysis_routes"] == ["linear_static"]
    assert contract["scope"]["no_new_combinations"] is True
    assert {"geometric_nonlinear", "total_lagrangian", "arc_length"}.issubset(
        contract["scope"]["excluded_routes"]
    )


def test_g04_contract_lists_the_registered_element_families_only() -> None:
    contract = _load(CONTRACT_PATH)
    registry = _load(CAPABILITY_PATH)
    expected = {"BEAM2", "MITC3", "MITC4", "TET4", "TET10", "HEX8", "HEX20", "DISCRETE"}
    routes = {row["element"]: row for row in contract["element_routes"]}
    registered = {
        row["CAPABILITY_ID"]
        for row in registry["capabilities"]
        if row["CAPABILITY_ID"].startswith("ELE-")
    }

    assert set(routes) == expected
    assert {row["capability_id"] for row in routes.values()} == {
        f"ELE-{element}" for element in expected
    }
    assert {row["capability_id"] for row in routes.values()} == registered
    assert all(row["status"] == "REGISTERED_REQUIRES_REQUALIFICATION" for row in routes.values())


def test_g04_mapping_has_no_orphan_or_duplicate_lin_shl_cases() -> None:
    mapping = _load(MAPPING_PATH)
    registry = _load(CASE_REGISTRY_PATH)
    expected = {
        row["case_id"] for row in registry["cases"] if row["family"] in {"LIN", "SHL"}
    }
    mapped = [case_id for group in mapping["groups"] for case_id in group["case_ids"]]

    assert len(mapped) == len(set(mapped))
    assert set(mapped) == expected
    assert mapping["summary"] == {
        "source_case_count": 72,
        "mapped_case_count": 72,
        "ready_count": 65,
        "planned_count": 4,
        "not_applicable_count": 3,
    }


def test_g04_mapping_statuses_agree_with_source_execution_state() -> None:
    mapping = _load(MAPPING_PATH)
    source = {
        row["case_id"]: row for row in _load(CASE_REGISTRY_PATH)["cases"] if row["family"] in {"LIN", "SHL"}
    }
    statuses = {
        case_id: group["status"]
        for group in mapping["groups"]
        for case_id in group["case_ids"]
    }

    assert sum(status == "READY" for status in statuses.values()) == 65
    assert sum(status == "PLANNED" for status in statuses.values()) == 4
    assert sum(status == "NOT_APPLICABLE" for status in statuses.values()) == 3
    for case_id, status in statuses.items():
        if status == "READY":
            assert source[case_id]["execution_state"] == "READY"
            assert source[case_id]["analysis_type"] == "linear_static"
        elif status == "PLANNED":
            assert source[case_id]["execution_state"] == "PLANNED"
        else:
            assert source[case_id]["execution_state"] == "PLANNED"
            assert source[case_id]["analysis_type"] != "linear_static"


def test_g04_mapping_references_contract_requirements_without_orphans() -> None:
    contract = _load(CONTRACT_PATH)
    mapping = _load(MAPPING_PATH)
    requirement_ids = {row["id"] for row in contract["requirements"]}
    referenced = {
        requirement_id
        for group in mapping["groups"]
        for requirement_id in group["requirements"]
    }

    assert referenced <= requirement_ids
    assert {"G04-LIN-001", "G04-LIN-002", "G04-LIN-003", "G04-LIN-004"} <= referenced
    assert {"G04-LIN-005", "G04-LIN-006", "G04-LIN-007", "G04-LIN-008"} <= requirement_ids
    assert mapping["mapping_policy"]["no_double_counting"] is True


def test_g04_thresholds_are_explicitly_owner_review_only() -> None:
    contract = _load(CONTRACT_PATH)

    assert contract["minimum_targets"]["status"] == "PROPOSED_OWNER_REVIEW"
    assert all(
        policy["status"] == "EXISTING"
        for policy in contract["policies"]["existing"]
        if policy["id"] != "TOL-026-ANALYTICAL-001"
    )
    policies = contract["policies"]["owner_approved_bounded"]
    assert {policy["status"] for policy in policies} == {"OWNER_APPROVED_BOUNDED"}
    assert [policy["threshold"]["pass"] for policy in policies] == [1e-8, 1e-10, 1e-2]
    assert policies[2]["minimum_levels"] == 3
    assert policies[2]["threshold"]["monotonicity_required"] is False


def test_g04_owner_review_covers_all_requirements_and_analytical_policy() -> None:
    review = _load(CONTRACT_PATH)["owner_review"]

    assert review["status"] == "PASS"
    assert len(review["requirements_reviewed"]) == 8
    assert {row["id"] for row in review["requirements_reviewed"]} == {
        f"G04-LIN-{index:03d}" for index in range(1, 9)
    }
    assert all(
        row["status"] == "APPROVED_BOUNDED"
        and row["measurable"]
        and row["reproducible"]
        and row["artificial_overqualification"] == "NO"
        for row in review["requirements_reviewed"]
    )
    assert review["case_dependent_analytical_tolerance"]["status"] == "APPROVED"


def test_g04_execution_evidence_is_explicit_and_preserves_limitations() -> None:
    evidence = _load(EVIDENCE_PATH)

    assert evidence["gate"] == "026-G04"
    assert evidence["status"] == "PASS_WITH_LIMITATIONS"
    assert evidence["execution"]["source_sha"] == "5e798e2fd052cb4fe8618d06495a2287f29e01b3"
    assert evidence["counts"] == {
        "cases_total": 65,
        "pass": 65,
        "warning": 0,
        "expected_failure": 0,
        "fail": 0,
        "skip": 0,
    }
    assert len(evidence["case_results"]) == 65
    assert {row["result"] for row in evidence["case_results"]} == {"PASS"}
    assert all(row["requirements"] for row in evidence["case_results"])
    mapped = {
        case_id for group in _load(MAPPING_PATH)["groups"] for case_id in group["case_ids"]
        if case_id.startswith(("VNV026-LIN-", "VNV026-HEX-", "VNV026-RBT-", "VNV026-SHL-"))
    }
    assert {row["case_id"] for row in evidence["case_results"]} == {
        case_id for case_id in mapped if case_id not in {"VNV026-LIN-PLN-001", "VNV026-LIN-PLN-002", "VNV026-LIN-PLN-003", "VNV026-LIN-PLN-004"}
        and not case_id.startswith("VNV026-SHL-PLN-")
    }
    assert all(row["policies"]["G04-POL-001"]["status"] == "PASS" for row in evidence["case_results"])
    assert all(row["policies"]["G04-POL-002"]["status"] == "PASS" for row in evidence["case_results"])
    assert evidence["oracle_summary"]["configured_analytical_pass"] == 20
    assert evidence["oracle_summary"]["declared_analytical_without_executable_configuration"] == 30
    assert evidence["policy_summary"]["mesh_convergence"]["status"] == "NOT_EVALUATED"
    assert evidence["requirement_summary"]["G04-LIN-007"]["status"] == "NOT_COVERED"
    assert all(item["status"] == "SKIP" for item in evidence["external_correlations"])
