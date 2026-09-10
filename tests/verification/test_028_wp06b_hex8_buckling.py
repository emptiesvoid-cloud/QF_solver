"""WP06B root-cause, remediation and non-promotion guards."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.run_wp06_hex8_buckling import _model, _solve_case
from solveur.api import solve_model


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "qualification/0_2_8/wp06b_hex8_buckling_contract.json"
EVIDENCE = ROOT / "qualification/0_2_8/wp06b_hex8_buckling_vnv.json"
MATRIX = ROOT / "qualification/0_2_8/wp06b_maturity_matrix.json"
WP06 = ROOT / "qualification/0_2_8/wp06_hex8_buckling_vnv.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp06b_root_causes_and_frozen_policy_are_recorded() -> None:
    contract = _load(CONTRACT)
    evidence = _load(EVIDENCE)

    assert contract["status"] == "ROOT_CAUSE_AUDIT_AND_MINIMAL_REMEDIATION"
    assert contract["baseline_sha"] == "be8fbd99d8a3d3b8e4ee3b8d867842389b063061"
    assert contract["scope"]["no_scope_change"] is True
    assert contract["tolerance_policy"]["changed"] is False
    assert contract["root_cause_audit"]["euler_factor"]["classification"] == "MODEL_SCOPE_LIMITATION"
    assert contract["root_cause_audit"]["invalid_orientation"]["classification"] == "TEST_ORACLE_PROBLEM"
    assert contract["root_cause_audit"]["replay_determinism"]["classification"] == "SOLVER_NONDETERMINISM"
    assert evidence["technical_decision"] == "NOT_QUALIFIED"
    assert evidence["fixes_applied"]["tolerances_changed"] is False
    assert evidence["fixes_applied"]["mesh_or_boundary_scope_changed"] is False


def test_wp06b_repeated_sparse_solves_are_exactly_replayable() -> None:
    first = solve_model(_model("cantilever", counts=(2, 2, 2)), enforce_policy=False)
    second = solve_model(_model("cantilever", counts=(2, 2, 2)), enforce_policy=False)

    assert first.solver["critical_factor"] == second.solver["critical_factor"]
    np.testing.assert_array_equal(first.displacements, second.displacements)


def test_wp06b_invalid_orientation_is_rejected_and_primary_gates_remain_failed() -> None:
    evidence = _load(EVIDENCE)
    invalid = _solve_case("cantilever", counts=(1, 1, 1), invalid_orientation=True)

    assert invalid["status"] == "EXPECTED_FAILURE"
    assert invalid["failure_type"] == "MeshValidationError"
    assert "Invalid HEX8 Jacobian determinant" in invalid["failure_message"]
    assert evidence["robustness_campaign"]["status"] == "PASS"
    assert evidence["robustness_campaign"]["invalid_orientation"]["explicit_failure"] is True
    assert evidence["primary_campaign"]["status"] == "FAIL"
    assert evidence["replays"]["deterministic"] is True
    assert evidence["external_oracle"]["status"] == "SKIPPED_EXTERNAL_UNAVAILABLE"


def test_wp06b_preserves_wp06_and_global_maturity_state() -> None:
    evidence = _load(EVIDENCE)
    matrix = _load(MATRIX)
    wp06 = _load(WP06)

    assert wp06["baseline_sha"] == "1dac48f88c07f1f5450f693702263472824f42bb"
    assert wp06["technical_decision"] == "NOT_QUALIFIED"
    for configuration in ("cantilever", "pinned_pinned_lateral"):
        assert evidence["primary_campaign"]["summaries"][configuration]["critical_factors"] == wp06[
            "primary_campaign"
        ]["summaries"][configuration]["critical_factors"]
    assert evidence["historical_0_2_7_evidence_changed"] is False
    assert matrix["summary"]["global_state_after_wp06b"] == {
        "QUALIFIED_BOUNDED": 32,
        "EXPERIMENTAL": 13,
        "NOT_QUALIFIED": 1,
        "TOTAL": 46,
        "not_qualified_combination": "COMB-HEX8-linear_buckling",
    }
    assert matrix["summary"]["registry_counts_consistent"] is True
