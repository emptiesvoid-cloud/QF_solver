"""Unit checks for the isolated J9 development-runner registration."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import development_autonomous as runner


def test_j9_scope_is_bound_to_exact_nodes_one_thread_and_private_namespace(tmp_path: Path) -> None:
    registration = runner.J9_NODEIDS
    assert registration == (
        "tests/verification/test_j9_hex8_controlled_distortion.py::test_j9_hex8_constant_domain_distortion_sweep",
        "tests/verification/test_j9_tet10_newmark.py::test_j9_tet10_direct_and_modal_newmark_time_mesh_study",
        "tests/verification/test_j9_tet10_newmark.py::test_j9_tet10_direct_newmark_time_mesh_study",
    )
    assert runner.J9_BUDGETS["timeout_seconds"] == 1200
    assert runner.J9_BUDGETS["archive_size_limit_mib"] == 128
    assert all(value == "1" for value in runner.J9_THREAD_ENVIRONMENT.values())
    assert runner._series_root(tmp_path, "fem_exploratory", "j9") == tmp_path / "worktrees" / "j9"
    root = Path(__file__).resolve().parents[2]
    registration = json.loads((root / "research/j9/execution_scope_registration.json").read_text(encoding="utf-8"))
    assert registration["allowed_nodeids"] == list(runner.J9_NODEIDS)
    assert registration["attempt_limit_per_nodeid"] == 1
    for relative in registration["family_contracts"]:
        contract = json.loads((root / relative).read_text(encoding="utf-8"))
        assert contract["execution"]["attempts"] == 1
        assert contract["execution"]["budgets"]["timeout_seconds"] == runner.J9_BUDGETS["timeout_seconds"]
