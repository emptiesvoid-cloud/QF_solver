"""WP07 mixed-solid linear-static contract and evidence guards."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_wp07_mixed_static import _base_model, _case, _failure_contract, _gmsh_import_case


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "qualification/0_2_8/wp07_mixed_static_contract.json"
EVIDENCE = ROOT / "qualification/0_2_8/wp07_mixed_static_vnv.json"
MATRIX = ROOT / "qualification/0_2_8/wp07_mixed_static_matrix.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp07_contract_is_frozen_and_owner_gated() -> None:
    contract = _load(CONTRACT)
    evidence = _load(EVIDENCE)
    matrix = _load(MATRIX)

    assert contract["status"] == "PREDECLARED_CAMPAIGN_CONTRACT"
    assert contract["baseline_sha"] == "d7501fd144daf11a5f51eae5c04d664ebbcdc763"
    assert contract["tolerance_policy"]["fixed_before_execution"] is True
    assert contract["tolerance_policy"]["post_observation_retuning"] is False
    assert evidence["technical_decision"] == "QUALIFIED_BOUNDED_CANDIDATE"
    assert evidence["owner_gate_required"] is True
    assert matrix["summary"]["registry_counts_consistent"] is True
    assert matrix["summary"]["global_state_after_wp07"] == {
        "QUALIFIED_BOUNDED": 32,
        "EXPERIMENTAL": 13,
        "NOT_QUALIFIED": 1,
        "TOTAL": 46,
        "not_qualified_combination": "COMB-HEX8-linear_buckling",
    }


def test_wp07_all_campaign_gates_and_replays_pass() -> None:
    evidence = _load(EVIDENCE)
    assert all(record["status"] == "PASS" for record in evidence["checks"].values())
    assert evidence["replays"]["required"] == 2
    assert evidence["replays"]["deterministic"] is True
    assert len(set(evidence["replays"]["digests"])) == 1
    assert evidence["historical_0_2_7_evidence_changed"] is False
    assert evidence["numerical_source_changed"] is False


def test_wp07_runtime_pairwise_import_and_failure_contract() -> None:
    assert _case(1)["pass"] is True
    assert _case(2)["pass"] is True
    assert _case(4)["pass"] is True
    assert _gmsh_import_case()["status"] == "PASS"
    assert _failure_contract(_base_model(1))["status"] == "PASS"
