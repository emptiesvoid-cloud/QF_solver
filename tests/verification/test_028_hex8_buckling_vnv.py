"""WP06 HEX8 buckling technical campaign and registry guards."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "qualification/0_2_7/capability_registry_v2.json"
CONTRACT = ROOT / "qualification/0_2_8/wp06_hex8_buckling_contract.json"
EVIDENCE = ROOT / "qualification/0_2_8/wp06_hex8_buckling_vnv.json"
MATRIX = ROOT / "qualification/0_2_8/wp06_maturity_matrix.json"
WP03_MATRIX = ROOT / "qualification/0_2_8/wp03_maturity_matrix.json"
WP04_MATRIX = ROOT / "qualification/0_2_8/wp04_maturity_matrix.json"
WP05_OWNER = ROOT / "qualification/0_2_8/wp05_owner_gate_final.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp06_keeps_hex8_buckling_not_qualified_and_reconciles_46() -> None:
    source = _load(SOURCE)
    evidence = _load(EVIDENCE)
    matrix = _load(MATRIX)

    combinations = [
        row for row in source["records"] if row["record_kind"] == "combination"
    ]
    assert len(combinations) == 46
    states = {row["capability_id"]: row["qualification_state"] for row in combinations}
    assert Counter(states.values()) == Counter(
        {"QUALIFIED_BOUNDED": 20, "EXPERIMENTAL": 25, "NOT_QUALIFIED": 1}
    )

    for path in (WP03_MATRIX, WP04_MATRIX):
        for decision in _load(path)["decisions"]:
            states[decision["source_record"]] = decision["public_maturity"]
    owner = _load(WP05_OWNER)["decision"]
    states[owner["source_record"]] = owner["resulting_maturity"]
    assert Counter(states.values()) == Counter(
        {"QUALIFIED_BOUNDED": 32, "EXPERIMENTAL": 13, "NOT_QUALIFIED": 1}
    )
    assert [key for key, value in states.items() if value == "NOT_QUALIFIED"] == [
        "COMB-HEX8-linear_buckling"
    ]
    assert states["COMB-WEDGE6-linear_static"] == "QUALIFIED_BOUNDED"

    assert evidence["technical_decision"] == "NOT_QUALIFIED"
    assert evidence["public_maturity"] == "NOT_QUALIFIED"
    assert matrix["decision"]["technical_decision"] == "NOT_QUALIFIED"
    assert matrix["decision"]["promotion_applied"] is False
    assert matrix["summary"]["global_state_after_wp06"] == {
        "QUALIFIED_BOUNDED": 32,
        "EXPERIMENTAL": 13,
        "NOT_QUALIFIED": 1,
        "TOTAL": 46,
        "not_qualified_combination": "COMB-HEX8-linear_buckling",
    }


def test_wp06_frozen_gates_and_failed_closure_are_recorded() -> None:
    contract = _load(CONTRACT)
    evidence = _load(EVIDENCE)

    assert contract["status"] == "PREDECLARED_CAMPAIGN_CONTRACT"
    assert contract["baseline_sha"] == "1dac48f88c07f1f5450f693702263472824f42bb"
    assert contract["tolerance_policy"]["fixed_before_execution"] is True
    assert contract["tolerance_policy"]["post_observation_retuning"] is False
    assert contract["tolerance_policy"]["analytical_factor_relative_error"] == 0.10
    assert contract["tolerance_policy"]["refinement_final_adjacent_factor_change"] == 0.01

    assert evidence["primary_campaign"]["status"] == "FAIL"
    assert evidence["robustness_campaign"]["status"] == "FAIL"
    assert evidence["external_oracle"]["status"] == "SKIPPED_EXTERNAL_UNAVAILABLE"
    assert evidence["replays"]["required"] == 2
    assert evidence["replays"]["deterministic"] is False
    assert evidence["integrity"]["numerical_source_changed"] is False
    assert evidence["integrity"]["historical_0_2_7_evidence_changed"] is False
    assert evidence["bugs"] == {"found": False, "fixed": False}


def test_wp06_primary_rows_have_internal_residual_and_kg_passes() -> None:
    evidence = _load(EVIDENCE)
    rows = evidence["primary_campaign"]["rows"]

    assert len(rows) == 6
    assert all(row["status"] == "PASS" for row in rows)
    assert all(row["expected_passes"]["preload"] for row in rows)
    assert all(row["expected_passes"]["kg_symmetry"] for row in rows)
    assert all(row["expected_passes"]["eigen_residual"] for row in rows)
    assert all(row["expected_passes"]["analytical_factor"] is False for row in rows)
    assert all(row["expected_passes"]["analytical_mode"] for row in rows)
