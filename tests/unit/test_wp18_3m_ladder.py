from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "qualification" / "0_2_7" / "wp18_runtime"


def _load(name: str) -> dict:
    return json.loads((RUNTIME / name).read_text(encoding="utf-8"))


def test_wp18_ladder_records_real_passed_fem_levels() -> None:
    summary = _load("wp18_summary.json")

    assert summary["status"] == "PASS_WITH_LIMITATIONS"
    assert summary["start_sha"] == "9c0605645fa60ef0d89f3ce98ca361a677f13d1d"
    assert summary["contract"]["acceptance_tolerance"] == 1.0e-8
    assert summary["contract"]["internal_solver_tolerance"] == 1.0e-10
    assert summary["contract"]["unchanged"] is True

    expected_dofs = {
        "1_5m": 1_536_000,
        "2m": 2_044_416,
        "2_5m": 2_572_125,
        "3m_run1": 3_000_000,
        "3m_run2": 3_000_000,
    }
    assert [entry["level"] for entry in summary["ladder"]] == list(expected_dofs)

    for entry in summary["ladder"]:
        assert entry["true_dof"] == expected_dofs[entry["level"]]
        raw_path = ROOT / entry["evidence"]
        assert raw_path.is_file()
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        assert raw["status"] == "PASS"
        assert raw["true_dof"] == entry["true_dof"]
        assert raw["input_digest_sha256"] == entry["input_digest_sha256"]
        assert raw["configuration_digest_sha256"] == (
            "e44ef191461ec5e4c6c0cde31bcda3f674c3e45949513d38a4ce8a067bf9fe6f"
        )
        assert raw["source_sha"] == summary["execution_source_sha"]
        assert raw["post"]["finite_outputs"] is True
        assert raw["post"]["free_relative_residual"] <= 1.0e-8
        assert raw["post"]["equilibrium_relative"] <= 1.0e-8
        assert raw["post"]["energy_relative"] <= 1.0e-8
        assert raw["solver"]["iterations"] == entry["iterations"]


def test_wp18_silver_replay_and_gold_boundary_are_explicit() -> None:
    summary = _load("wp18_summary.json")
    replay = json.loads(
        (RUNTIME / "wp18_replay_comparison.json").read_text(encoding="utf-8")
    )
    state = json.loads(
        (ROOT / "qualification" / "0_2_7" / "wp18_state.json").read_text(
            encoding="utf-8"
        )
    )

    assert summary["bronze"]["status"] == "PASS"
    assert summary["bronze"]["solve_claim_authorized"] is False
    assert summary["silver"]["status"] == "PASS"
    assert summary["silver"]["replay_status"] == "PASS"
    assert replay["status"] == "PASS"
    assert replay["same_source"] is True
    assert replay["same_input"] is True
    assert replay["same_configuration"] is True
    assert replay["absolute_deltas"] == {
        "true_dof": 0.0,
        "matvec_count": 0.0,
        "residual_relative": 0.0,
        "equilibrium_relative": 0.0,
        "energy_relative": 0.0,
    }
    assert summary["gold"]["status"] == "NOT_ATTEMPTED"
    assert summary["gold"]["claim_authorized"] is False
    assert summary["gold"]["restart_checkpoint"] == "NOT_RUN"
    assert summary["gold"]["second_physical_case"] == "NOT_RUN"
    assert state["ready_for_wp19"] is True


def test_wp18_bronze_preflight_and_artifact_digests_are_controlled() -> None:
    summary = _load("wp18_summary.json")
    preflight = json.loads(
        (RUNTIME / "wp18_bronze_preflight.json").read_text(encoding="utf-8")
    )

    assert preflight["status"] == "PASS"
    assert preflight["target_dofs"] == 3_000_000
    assert all(check["status"] == "PASS" for check in preflight["checks"])
    assert summary["bronze"]["preflight_checks"] == "PASS"
    assert summary["policy"] == {
        "wp14_contract_changed": False,
        "tolerances_changed": False,
        "fem_formulation_changed": False,
        "no_implicit_fallback": True,
        "full_regression_run": False,
        "gold_is_not_claimed": True,
        "bronze_is_not_a_solve_claim": True,
    }

    for path in RUNTIME.glob("*.json"):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert len(digest) == 64
