"""Focused governance checks for the Level-Up 2 setup contract."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_7"
PLAN_PATH = QUALIFICATION / "level_up_2_plan.json"
STATE_PATH = QUALIFICATION / "level_up_2_state.json"
INDEX_PATH = QUALIFICATION / "level_up_2_index.json"
BASELINE_SHA = "8f08bfb5a6d4dedcd24966f5474e8c12cbfa5bc3"
WP01_SOURCE_SHA = "e1703b5bc00e9cf2eb92e7e346783c9764201808"
WP02_SOURCE_SHA = "3cb817c9391ef7998c5950d3071c8d9ce1be5dd8"
WP03_SOURCE_SHA = "0a6b573485cb39d07b5e179aecd654af41bbc8e7"
EXECUTION_SOURCE_SHA = "04b07e00ddfe0b339b5790493a607ec902b1ed80"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_lu2_plan_has_exact_scope_and_weight_accounting() -> None:
    plan = _load(PLAN_PATH)
    work_packages = plan["work_packages"]
    conditional = plan["conditional_gates"]

    assert plan["namespace"] == "027-LEVEL-UP-2"
    assert plan["status"] == "OPEN"
    assert plan["source_snapshot"] == BASELINE_SHA
    assert len(work_packages) == 9
    assert work_packages[0]["status"] == "PASS"
    assert sum(item["weight_percent"] for item in work_packages) == 50
    assert [item["id"] for item in work_packages] == [
        "LU2-WP01",
        "LU2-WP02",
        "LU2-WP03",
        "LU2-WP04",
        "LU2-WP05",
        "LU2-WP06",
        "LU2-WP07",
        "LU2-WP08",
        "LU2-WP09",
    ]
    assert {item["id"] for item in conditional} == {"C1", "C2", "C3"}
    assert all(item["weight_percent"] == 0 for item in conditional)

    accounting = plan["global_accounting"]
    assert accounting["level_up_1"] == {
        "weight_percent": 50,
        "acquired_percent": 50,
        "status": "CLOSED",
        "scope": "historical Level-Up 1 qualification and consolidation",
    }
    assert accounting["level_up_2"]["acquired_percent"] == 46
    assert accounting["current_global_progress_percent"] == 96
    assert accounting["weights_total_percent"] == 100


def test_lu2_contracts_and_policies_are_installed_without_execution() -> None:
    plan = _load(PLAN_PATH)
    contracts = plan["contracts"]
    policies = plan["policies"]
    setup = plan["setup_scope"]

    assert all(contracts[name]["status"].startswith("INSTALLED") for name in contracts)
    assert contracts["3M_GOLD"]["restart_required"] is False
    assert contracts["5M_BRONZE"]["converged_solve_claim"] is False
    assert contracts["5M_SILVER"]["replays_required"] == 2
    assert contracts["MPI_V2"]["single_host_rank_targets"] == [2, 4, 8]
    assert contracts["MPI_V2"]["strong_scaling_required"] == "3M"
    assert policies["qualification_is_non_transitive"] is True
    assert policies["fail_closed"] is True
    assert policies["silent_fallback_forbidden"] is True
    assert policies["post_result_retuning_forbidden"] is True
    assert all(value is False for value in setup.values())


def test_lu2_state_index_and_existing_lu1_are_consistent() -> None:
    state = _load(STATE_PATH)
    index = _load(INDEX_PATH)
    legacy_plan = _load(QUALIFICATION / "level_up_plan.json")

    assert state["status"] == "OPEN"
    assert state["source_sha"] == EXECUTION_SOURCE_SHA
    assert state["wp01_source_sha"] == WP01_SOURCE_SHA
    assert state["current_work_package"] == "LU2-WP05"
    assert state["global_accounting"] == {
        "level_up_1": "50/50 CLOSED",
        "level_up_2": "46/50 OPEN",
        "current_global_progress": "96/100",
        "weights_total_percent": 100,
    }
    assert state["execution"]["heavy_benchmark_run"] is True
    assert state["execution"]["full_regression_run"] is False
    assert state["execution"]["existing_evidence_rewritten"] is False
    assert state["readiness"]["ready_for_lu2_wp01"] is True
    assert state["readiness"]["ready_for_lu2_wp02"] is True
    assert state["readiness"]["ready_for_lu2_wp03"] is True
    assert state["readiness"]["ready_for_lu2_wp04"] is True
    assert state["readiness"]["ready_for_lu2_wp08"] is True
    assert state["readiness"]["ready_for_lu2_wp07"] is True
    assert state["readiness"]["ready_for_lu2_wp05"] is True
    assert state["readiness"]["ready_for_heavy_benchmark"] is False
    assert state["readiness"]["next_work_package"] == "LU2-WP09"
    assert state["work_packages"][3]["status"] == "PASS"
    assert state["work_packages"][4]["status"] == "PASS"
    assert state["work_packages"][7]["status"] == "PASS_WITH_LIMITATIONS"
    assert state["work_packages"][1]["status"] == "PASS_WITH_LIMITATIONS"
    assert state["work_packages"][1]["evidence"] == "qualification/0_2_7/wp02_state.json"

    assert index["source_of_truth"] == str(PLAN_PATH.relative_to(ROOT)).replace("\\", "/")
    assert index["state"] == str(STATE_PATH.relative_to(ROOT)).replace("\\", "/")
    assert index["work_package_count"] == 9
    assert index["conditional_gate_count"] == 3
    assert index["weights_sum_percent"] == 50
    assert legacy_plan["plan_id"] == "QF-027-LEVEL-UP-001"
    assert index["historical_lu1"] == {
        "plan": "qualification/0_2_7/level_up_plan.json",
        "preserved": True,
        "active": False,
    }


def test_current_governance_consumers_point_to_lu2_and_keep_baseline_roles() -> None:
    plan = _load(PLAN_PATH)
    manifest = _load(QUALIFICATION / "manifest.json")
    progress = _load(QUALIFICATION / "progress.json")
    release_truth = _load(QUALIFICATION / "release_truth.json")
    gates = _load(QUALIFICATION / "gates.json")
    requirements = _load(QUALIFICATION / "requirements.json")

    assert manifest["current_development_head"] == WP03_SOURCE_SHA
    assert manifest["level_up_2_scope"]["status"] == "OPEN"
    assert manifest["level_up_2_scope"]["current_work_package"] == "LU2-WP05"
    assert manifest["level_up_2_scope"]["level_up_2_acquired_percent"] == 46
    assert manifest["level_up_2_scope"]["current_global_progress_percent"] == 96
    assert manifest["level_up_2_scope"]["wp08_status"] == "PASS_WITH_LIMITATIONS"
    assert manifest["level_up_2_scope"]["pre_lu2_qualified_baseline"] == BASELINE_SHA
    assert all(
        path in manifest["documents"]
        for path in (
            "qualification/0_2_7/level_up_2_plan.json",
            "qualification/0_2_7/level_up_2_state.json",
            "qualification/0_2_7/level_up_2_index.json",
            "qualification/0_2_7/wp02_execution_contract.json",
            "qualification/0_2_7/wp02_state.json",
            "qualification/0_2_7/wp02_runtime/wp02_evidence_index.json",
            "qualification/0_2_7/wp02_runtime/wp02_config_freeze.json",
            "qualification/0_2_7/wp03_execution_contract.json",
            "qualification/0_2_7/lu2_wp03_state.json",
            "qualification/0_2_7/wp04_execution_contract.json",
            "qualification/0_2_7/wp04_runtime/wp04_evidence_index.json",
            "qualification/0_2_7/wp04_runtime/wp04_post_pc_ready_diagnostic.json",
            "qualification/0_2_7/s2_post_pc_ready_diagnostic_state.json",
        )
    )

    assert progress["current_work_package"] == "LU2-WP05"
    assert progress["global_accounting"]["current_global_progress_percent"] == 96
    assert progress["level_up_2"]["status"] == "OPEN"
    assert progress["level_up_2"]["wp02_status"] == "PASS_WITH_LIMITATIONS"
    assert progress["level_up_2"]["wp03_status"] == "PASS_WITH_LIMITATIONS"
    assert progress["level_up_2"]["wp04_status"] == "PASS"
    assert progress["level_up_2"]["wp04_bronze_pass"] is True
    assert progress["level_up_2"]["wp05_status"] == "PASS"
    assert progress["level_up_2"]["wp06_status"] == "PASS_WITH_LIMITATIONS"
    assert progress["level_up_2"]["wp08_status"] == "PASS_WITH_LIMITATIONS"
    assert progress["level_up_2"]["c1_matrix_free_triggered"] is False
    assert release_truth["current_development_head"]["sha"] == WP03_SOURCE_SHA
    assert release_truth["level_up_2"]["status"] == "OPEN"
    assert release_truth["level_up_2"]["wp04_status"] == "PASS"
    assert release_truth["level_up_2"]["wp05_status"] == "PASS"
    assert release_truth["level_up_2"]["wp08_status"] == "PASS_WITH_LIMITATIONS"

    lu2_gates = gates["level_up_2"]
    assert lu2_gates["status"] == "OPEN"
    assert len(lu2_gates["gates"]) == 9
    assert len(lu2_gates["conditional_gates"]) == 3
    assert sum(item["weight_percent"] for item in lu2_gates["gates"]) == 50
    assert lu2_gates["gates"][0]["status"] == "PASS"
    assert lu2_gates["gates"][7]["status"] == "PASS_WITH_LIMITATIONS"

    lu2_requirements = requirements["level_up_2_requirements"]
    assert len(lu2_requirements) == 9
    assert lu2_requirements[0]["status"] == "PASS"
    assert {item["work_package"] for item in lu2_requirements} == {
        f"LU2-WP{index:02d}" for index in range(1, 10)
    }
    assert lu2_requirements[0]["status"] == "PASS"
    assert lu2_requirements[1]["status"] == "PASS_WITH_LIMITATIONS"
    assert lu2_requirements[2]["status"] == "PASS_WITH_LIMITATIONS"
    assert lu2_requirements[3]["status"] == "PASS"
    assert lu2_requirements[4]["status"] == "PASS"
    assert lu2_requirements[5]["status"] == "PASS_WITH_LIMITATIONS"
    assert lu2_requirements[6]["status"] == "PASS_WITH_LIMITATIONS"
    assert lu2_requirements[7]["status"] == "PASS_WITH_LIMITATIONS"
    assert lu2_requirements[8]["status"] == "PLANNED"
    assert plan["registry_guard"] == {
        "source_of_truth": "qualification/0_2_7/capability_registry_v2.json",
        "public_anchor_count": 33,
        "public_combination_count": 46,
        "record_count": 79,
        "maturity_promotion_in_setup": False,
        "qualification_is_non_transitive": True,
    }
