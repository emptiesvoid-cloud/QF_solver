"""Integrity guards for the WP13-02B7 rerun after input validation remediation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).parents[2]
EVIDENCE = ROOT / "qualification" / "0_2_8" / "wp13_02b7_v2" / "manifest.json"
ARCHIVE = ROOT / "qualification" / "0_2_8" / "wp13_02b7_v2" / "wp13_02b7_arrays.npz"
CONTRACT = ROOT / "qualification" / "0_2_8" / "wp13_02b4_newmark_v2_contract.json"
HISTORICAL_B5 = ROOT / "qualification" / "0_2_8" / "wp13_02b5_v2" / "manifest.json"

START_SHA = "fc6b32c8ea1fff0a98390b7788018b14e2ac4891"
CONTRACT_COMMIT = "ccab01854f42d56aa6dc7202d9c5dd76dd9b2dde"
CONTRACT_BLOB = "8b44792466eacaf1f341a7970502e9b48dbed4e1"


def _digest(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array, dtype=np.float64).tobytes()).hexdigest()


def _load() -> tuple[dict, dict]:
    return (
        json.loads(EVIDENCE.read_text(encoding="utf-8")),
        json.loads(CONTRACT.read_text(encoding="utf-8")),
    )


def test_wp13_02b7_contract_prechecks_and_history_are_preserved() -> None:
    evidence, contract = _load()
    historical_b5 = json.loads(HISTORICAL_B5.read_text(encoding="utf-8"))

    assert evidence["start_sha"] == START_SHA
    assert evidence["contract_commit"] == CONTRACT_COMMIT
    assert evidence["contract_id"] == contract["contract_id"] == "WP13-02B4-NEWMARK-MIXED-V2-001"
    assert evidence["contract_blob_sha"] == CONTRACT_BLOB
    assert evidence["contract_committed_before_run"] is True
    assert evidence["contract_unchanged"] is True
    assert evidence["prechecks"]["model_connected"] is True
    assert evidence["prechecks"]["connected_components"] == 1
    assert evidence["prechecks"]["direct_support_bypass"] is False
    assert evidence["prechecks"]["ndof"] == 48
    assert evidence["prechecks"]["family_counts"] == {"TET4": 3, "WEDGE6": 2, "HEX8": 1}
    assert evidence["prechecks"]["consistent_mass"] is True
    assert evidence["prechecks"]["damping_zero"] is True
    assert evidence["prechecks"]["first_mode_initial_condition"] is True
    assert historical_b5["decision"]["status"] == "FAIL_FAILURE_CONTRACT"
    assert historical_b5["failure_contract"]["invalid_initial_conditions_non_list"]["status"] == "NOT_REJECTED"


def test_wp13_02b7_convergence_acceptance_and_interface_gates_pass() -> None:
    evidence, contract = _load()
    assert list(evidence["levels"]) == ["20", "40", "80", "160"]
    assert contract["acceptance_gates"]["applies_to"] == ["T1/80", "T1/160"]
    assert evidence["interface_gates_all_levels"] is True
    convergence = evidence["convergence"]
    assert all(convergence["strictly_decreasing"].values())
    assert all(convergence["order_pass"].values())
    assert all(
        1.5 <= order <= 2.5
        for orders in convergence["orders"].values()
        for order in orders
    )
    for level in ("80", "160"):
        acceptance = evidence["acceptance"][level]
        assert all(result["pass"] for key, result in acceptance.items() if key != "interfaces")
        assert all(
            result["pass"]
            for interface in acceptance["interfaces"].values()
            for result in interface.values()
        )


def test_wp13_02b7_archive_oracle_replays_and_failure_contract() -> None:
    evidence, _ = _load()
    assert evidence["decision"]["status"] == "PASS_V2_CANDIDATE"
    assert evidence["decision"]["claim_candidate"] == "CONNECTED_MIXED_NEWMARK_TET4_WEDGE6_HEX8_BOUNDED"
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == evidence["archive"]["sha256"]

    with np.load(ARCHIVE, allow_pickle=False) as arrays:
        assert len(arrays.files) == evidence["archive"]["array_count"] == 166
        for name, metadata in evidence["archive"]["array_manifest"].items():
            assert arrays[name].shape == tuple(metadata["shape"])
            assert str(arrays[name].dtype) == metadata["dtype"]
            assert np.isfinite(arrays[name]).all()
            assert _digest(arrays[name]) == metadata["sha256"]

    replay = evidence["replays"]["comparison"]
    assert replay["all_fields_pass"] is True
    assert replay["same_status"] is True
    assert replay["same_iterations"] is True
    for item in replay["per_replay"]:
        assert item["all_fields_pass"] is True
        assert item["status_identical"] is True
        assert item["iterations_identical"] is True
        assert all(item[field] <= 1.0e-12 for field in (
            "displacement", "velocity", "acceleration", "q", "residual_norm", "energy_total", "reactions"
        ))

    failures = evidence["failure_contract"]
    for name in (
        "invalid_dt", "missing_mass", "unsupported_damping", "unsupported_time_load",
        "invalid_initial_conditions_unknown_dof", "invalid_initial_conditions_non_list", "invalid_mixed_interface",
    ):
        assert failures[name]["status"] == "REJECTED"
    assert failures["unsupported_family"]["status"] == "UNSUPPORTED_ROUTE"
    assert evidence["silent_fallback"] is False
    assert evidence["integrity"] == {
        "numerical_source_changed": False,
        "input_validation_source_changed": True,
        "formulation_changed": False,
        "contract_changed": False,
        "gates_changed": False,
        "maturity_changed": False,
        "evidence_0_2_7_changed": False,
        "historical_b5_rewritten": False,
    }
