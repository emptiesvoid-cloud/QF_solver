"""Unit checks for the isolated J10 development-runner registration."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import development_autonomous as runner


def test_j10_scope_is_bound_to_exact_nodes_one_thread_and_private_namespace(tmp_path: Path) -> None:
    expected = (
        "tests/verification/test_j10_tet10_fixed_excitation.py::test_j10_tet10_same_physical_excitation_time_mesh_study",
        "tests/verification/test_j10_hex8_j7_geometry.py::test_j10_hex8_j7_domain_preserving_distortion",
        "tests/verification/test_j10_tet10_modal_smoke.py::test_j10_tet10_modal_route_smoke",
    )
    assert runner.J10_NODEIDS == expected
    assert runner.J10_BUDGETS == {
        "timeout_seconds": 1800,
        "rss_soft_limit_mib": 2048,
        "process_tree_limit": 4,
        "output_total_limit_mib": 8,
        "output_stream_limit_mib": 4,
        "temporary_limit_mib": 512,
        "archive_size_limit_mib": 128,
    }
    assert all(value == "1" for value in runner.J10_THREAD_ENVIRONMENT.values())
    assert runner._series_root(tmp_path, "fem_exploratory", "j10") == tmp_path / "worktrees" / "j10"

    root = Path(__file__).resolve().parents[2]
    registration = json.loads((root / "research/j10/execution_scope_registration.json").read_text(encoding="utf-8"))
    assert registration["allowed_nodeids"] == list(expected)
    assert registration["attempt_limit_per_nodeid"] == 1
    assert set(registration["family_contracts"]) == {
        "research/j10_transient/contracts/tet10_fixed_excitation_contract.json",
        "research/j10_hex8/contracts/hex8_j7_distortion_contract.json",
        "research/j10_modal/contracts/tet10_modal_route_smoke_contract.json",
    }
    for relative in registration["family_contracts"]:
        contract = json.loads((root / relative).read_text(encoding="utf-8"))
        assert contract["execution"]["attempts"] == 1
        assert contract["execution"]["budgets"]["timeout_seconds"] == runner.J10_BUDGETS["timeout_seconds"]


def test_j10_preflight_dispatches_to_its_own_exact_node_handler(monkeypatch) -> None:
    expected = {"state": "PREFLIGHT_PASS", "worktree_id": "j10"}
    monkeypatch.setattr(runner, "_preflight_j10_pytest", lambda target, preflight_id: expected)
    result = runner.preflight_pytest(
        "j10",
        runner.J10_NODEIDS[0],
        "pf-0123456789ab",
    )
    assert result is expected


def test_j10_environment_uses_approved_one_thread_configuration(tmp_path: Path) -> None:
    environment = runner.build_child_environment(
        tmp_path,
        base={},
        thread_environment=runner.J10_THREAD_ENVIRONMENT,
    )
    assert all(environment[name] == "1" for name in runner.J10_THREAD_ENVIRONMENT)
    assert environment["QF_DEVELOPMENT_AUTONOMOUS"] == "1"
