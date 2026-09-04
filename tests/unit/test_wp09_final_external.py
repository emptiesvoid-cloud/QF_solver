"""Targeted checks for the final WP09 external evidence corpus."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "qualification/0_2_7/external_oracles/wedge6/wp09_final_contract.json"
CATALOG = ROOT / "qualification/0_2_7/vnv_v2/wp09_final_external_cases.json"
EVIDENCE = ROOT / "qualification/0_2_7/vnv_v2/wp09_final_external_evidence.json"
STATE = ROOT / "qualification/0_2_7/wp09_final_state.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_final_contract_catalog_and_evidence_have_the_same_declared_cases() -> None:
    contract = _load(CONTRACT)
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    evidence = _load(EVIDENCE)
    contract_ids = [row["case_id"] for row in contract["cases"]]
    catalog_ids = [row["case_id"] for row in catalog]
    evidence_ids = [row["case_id"] for row in evidence["records"]]
    assert len(contract_ids) == 12
    assert contract_ids == catalog_ids == evidence_ids
    assert all(row["status"] == "READY" for row in contract["cases"])
    assert all(row["execution_tier"] == "T2" for row in catalog)
    assert all(row["oracle"]["type"] == "EXTERNAL_SOLVER" for row in catalog)


def test_final_external_evidence_is_complete_and_bounded() -> None:
    contract = _load(CONTRACT)
    evidence = _load(EVIDENCE)
    state = _load(STATE)
    assert evidence["status"] == "PASS_WITH_LIMITATIONS"
    assert evidence["summary"] == {
        "cases_total": 12,
        "external_cases_run": 12,
        "external_pass": 12,
        "external_fail": 0,
        "external_skipped": 0,
    }
    assert evidence["primary_observables"] == ["displacement", "total_reaction", "strain_energy"]
    assert evidence["calculix"]["state"] == "NOT_COMPARABLE"
    assert evidence["legacy_internal_corpus"]["preserved"] is True
    assert evidence["legacy_internal_corpus"]["rerun"] is False
    assert evidence["tolerance_policy"]["fixed_before_execution"] is True
    assert evidence["tolerance_policy"]["post_result_retuning"] is False
    assert state["execution_source_sha"] == evidence["source_sha"]
    assert state["public_maturity"] == "EXPERIMENTAL"
    assert state["public_qualification"] == "DEFERRED"
    for record in evidence["records"]:
        assert record["verdict"] == "PASS_EXTERNAL_CORRELATION_BOUNDED"
        assert record["oracle"]["state"] == "PASS"
        assert record["oracle"]["image_digest"].startswith("sha256:")
        assert record["oracle"]["output_digest"]
        assert set(record["oracle"]["deck_digests"]) == {
            record["case_id"].lower() + suffix for suffix in (".comm", ".mail", ".export")
        }
        for observable, comparison in record["comparison"].items():
            assert comparison["tolerance"] == contract["tolerance_policy"][record["tolerance_class"]]["tolerances"][observable]
            assert comparison["verdict"] == "PASS"
            assert comparison["relative_error"] <= comparison["tolerance"]


def test_final_external_replay_and_numeric_scope_are_explicit() -> None:
    evidence = _load(EVIDENCE)
    assert evidence["determinism"]["qf_final_case"] == "PASS"
    assert evidence["determinism"]["external_final_case"]["status"] == "PASS"
    assert evidence["existing_fem_numerics_changed"] is False
    assert evidence["full_regression_run"] is False
    assert evidence["pushed"] is False
    assert any("WEDGE6 remains EXPERIMENTAL" in item for item in evidence["limitations"])
