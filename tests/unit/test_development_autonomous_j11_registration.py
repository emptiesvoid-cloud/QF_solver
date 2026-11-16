"""Checks for the isolated J11 exact-node development execution registration."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

from scripts import development_autonomous as runner


ROOT = Path(__file__).resolve().parents[2]


def test_j11_scope_is_bound_to_exact_nodes_one_thread_and_one_attempt_each() -> None:
    policy = runner.load_policy()
    entry = policy["worktrees"]["j11"]
    assert entry["branch"] == "work/0.3.0-j11"
    assert entry["baseline_commit"] == "0d6b6384c7b334d664e7645d75c8413499b9036f"
    assert entry["allowed_nodeids"] == list(runner.J11_NODEIDS)
    assert entry["attempt_limits_per_nodeid"] == runner.J11_ATTEMPT_LIMITS
    assert entry["budgets"] == runner.J11_BUDGETS
    assert all(value == "1" for value in entry["thread_environment"].values())
    assert entry["node_attempt_ledger"]["path"] == "node-attempt-ledger-j11.json"


def test_j11_scope_registration_binds_both_family_contracts() -> None:
    registration = json.loads((ROOT / "research/j11/execution_scope_registration.json").read_text(encoding="utf-8"))
    assert registration["owner_mandate_id"] == "QF_SOLVER_0.3.0_J11_OWNER_2026-11-16"
    assert registration["development_mandate_id"] == "DEVELOPMENT_AUTONOMOUS-J11-2026-11-16-v1"
    assert registration["allowed_nodeids"] == list(runner.J11_NODEIDS)
    assert registration["attempt_limits_per_nodeid"] == runner.J11_ATTEMPT_LIMITS
    assert set(registration["family_contracts"]) == {
        "research/j11_transient/contracts/tet10_axial_bar_contract.json",
        "research/j11_hex8/contracts/hex8_j7_reconstruction_contract.json",
        "research/j11_transient/contracts/tet10_axial_bar_contract_corrective_v2.json",
        "research/j11_hex8/contracts/hex8_j7_reconstruction_contract_corrective_v2.json",
    }
    for relative, expected_sha in registration["family_contract_sha256_canonical"].items():
        contract_bytes = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(contract_bytes).hexdigest() == expected_sha
        contract = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        assert contract["owner_mandate_id"] == registration["owner_mandate_id"]
        assert contract["development_mandate_id"] == registration["development_mandate_id"]
        assert contract["attempts"]["exact_node_attempt_limit"] == 1
    assert [item["prior_run_state"] for item in registration["corrective_attempts"]] == [
        "PYTEST_FAILED",
        "PYTEST_FAILED",
    ]
    assert all("criteria" not in item for item in registration["corrective_attempts"])


def test_j11_preflight_dispatches_to_its_exact_node_handler(monkeypatch) -> None:
    expected = {"state": "PREFLIGHT_PASS", "worktree_id": "j11"}
    monkeypatch.setattr(runner, "_preflight_j11_pytest", lambda target, preflight_id: expected)
    result = runner.preflight_pytest("j11", runner.J11_NODEIDS[0], "pf-0123456789ab")
    assert result is expected
