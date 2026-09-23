"""Fail-closed contract/runner guard tests for the supplemental WP12 R3.6 campaign."""

from __future__ import annotations

import json

import pytest

from scripts.freeze_wp12_diverse_contract import GATES
from scripts.run_wp12_diverse_code_aster import CampaignError, preflight
from scripts.run_wp12_expanded_code_aster import IMAGE


def test_r36_correlation_gates_are_unchanged_from_frozen_r35() -> None:
    from pathlib import Path

    contract_path = (
        Path(__file__).resolve().parents[2]
        / "qualification/0_2_9/wp12_external_vv_r3_5_expanded_contract.json"
    )
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    assert GATES == contract["gates"]


def test_runner_rejects_preparation_only_contract_before_any_runtime_probe(tmp_path) -> None:
    contract = {
        "revision": "R3_6_DIVERSE_TOPOLOGY_144_CASE_LINEAR_STATIC_CORRELATION",
        "status": "PREPARATION_ONLY",
        "execution_authorized": False,
        "timeout_seconds": 900,
        "memory_limit_mb": 4096,
        "code_aster_version": "18.1.0",
        "code_aster_image": IMAGE,
        "code_aster_image_id": IMAGE.split("@")[-1],
        "external_solver": {
            "name": "Code_Aster",
            "version": "18.1.0",
            "image": IMAGE,
            "image_id": IMAGE.split("@")[-1],
            "modelisation": "3D",
            "fresh_container_per_case": True,
            "cpu_limit": 1,
            "mpi": False,
            "action": "make_etude",
            "timeout_seconds": 900,
            "memory_limit_mb": 4096,
        },
    }
    contract_path = tmp_path / "unfrozen-contract.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    with pytest.raises(CampaignError, match="not frozen and execution-authorized"):
        preflight(contract_path, tmp_path)

    assert list(tmp_path.iterdir()) == [contract_path]
