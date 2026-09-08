"""Integrity guards for the WP13-02B5 Newmark V2 campaign."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).parents[2]
EVIDENCE = ROOT / "qualification" / "0_2_8" / "wp13_02b5_v2" / "manifest.json"
ARCHIVE = ROOT / "qualification" / "0_2_8" / "wp13_02b5_v2" / "wp13_02b5_arrays.npz"
CONTRACT = ROOT / "qualification" / "0_2_8" / "wp13_02b4_newmark_v2_contract.json"
SCHEMA = ROOT / "qualification" / "0_2_8" / "wp13_02b4_contract.schema.json"

START_SHA = "ccab01854f42d56aa6dc7202d9c5dd76dd9b2dde"
CONTRACT_BLOB = "8b44792466eacaf1f341a7970502e9b48dbed4e1"


def _digest(array: np.ndarray) -> str:
    return hashlib.sha256(
        np.ascontiguousarray(array, dtype=np.float64).tobytes()
    ).hexdigest()


def _load() -> tuple[dict, dict]:
    return (
        json.loads(EVIDENCE.read_text(encoding="utf-8")),
        json.loads(CONTRACT.read_text(encoding="utf-8")),
    )


def test_wp13_02b5_contract_and_prechecks_are_frozen() -> None:
    evidence, contract = _load()

    assert EVIDENCE.is_file()
    assert SCHEMA.is_file()
    assert evidence["start_sha"] == START_SHA
    assert evidence["contract_commit"] == START_SHA
    assert evidence["contract_id"] == "WP13-02B4-NEWMARK-MIXED-V2-001"
    assert evidence["contract_blob_sha"] == CONTRACT_BLOB
    assert evidence["contract_committed_before_run"] is True
    assert evidence["contract_unchanged"] is True
    assert contract["status"] == "PREDECLARED_NOT_EXECUTED"
    assert contract["contract_id"] == evidence["contract_id"]
    assert [level["role"] for level in contract["time_discretization"]["levels"]] == [
        "CHARACTERIZATION_ONLY",
        "CHARACTERIZATION_ONLY",
        "ACCEPTANCE",
        "ACCEPTANCE",
    ]
    assert [level["name"] for level in contract["time_discretization"]["levels"]] == [
        "T1/20",
        "T1/40",
        "T1/80",
        "T1/160",
    ]

    prechecks = evidence["prechecks"]
    assert prechecks["model_connected"] is True
    assert prechecks["connected_components"] == 1
    assert prechecks["direct_support_bypass"] is False
    assert prechecks["ndof"] == 48
    assert prechecks["ndof_expected"] is True
    assert prechecks["family_counts"] == {"TET4": 3, "WEDGE6": 2, "HEX8": 1}
    assert prechecks["families_present"] is True
    assert prechecks["consistent_mass"] is True
    assert prechecks["mass_symmetric"] is True
    assert prechecks["mass_positive"] is True
    assert prechecks["damping_zero"] is True
    assert prechecks["first_mode_initial_condition"] is True
    assert prechecks["oracle_available"] is True


def test_wp13_02b5_acceptance_convergence_and_interfaces_are_archived() -> None:
    evidence, contract = _load()
    levels = evidence["levels"]
    assert list(levels) == ["20", "40", "80", "160"]
    assert all(levels[level]["solver_status"] == "PASS" for level in levels)
    assert evidence["interface_gates_all_levels"] is True

    convergence = evidence["convergence"]
    assert all(convergence["strictly_decreasing"].values())
    assert all(convergence["order_pass"].values())
    assert all(
        1.5 <= order <= 2.5
        for orders in convergence["orders"].values()
        for order in orders
    )
    assert contract["convergence"]["order_gate"] == {
        "minimum": 1.5,
        "maximum": 2.5,
        "applies_to_N": [20, 40, 80],
        "inclusive": True,
    }

    for level in ("80", "160"):
        acceptance = evidence["acceptance"][level]
        for metric, result in acceptance.items():
            if metric != "interfaces":
                assert result["pass"] is True, (level, metric)
        for interface in ("TET4_WEDGE6", "WEDGE6_HEX8"):
            assert all(
                result["pass"] is True
                for result in acceptance["interfaces"][interface].values()
            )

    assert evidence["oracle"]["eigen_frequency_error"] <= 1.0e-8
    assert evidence["oracle"]["independence"]


def test_wp13_02b5_archive_and_replays_are_integrity_checked() -> None:
    evidence, _ = _load()
    assert ARCHIVE.is_file()
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == evidence["archive"]["sha256"]

    with np.load(ARCHIVE, allow_pickle=False) as arrays:
        assert len(arrays.files) == evidence["archive"]["array_count"] == 166
        for name, metadata in evidence["archive"]["array_manifest"].items():
            assert name in arrays.files
            assert arrays[name].shape == tuple(metadata["shape"])
            assert str(arrays[name].dtype) == metadata["dtype"]
            assert np.isfinite(arrays[name]).all()
            assert _digest(arrays[name]) == metadata["sha256"]

    replay = evidence["replays"]["comparison"]
    assert evidence["replays"]["main_level"] == "T1/160"
    assert evidence["replays"]["count"] == 2
    assert replay["all_fields_pass"] is True
    assert replay["same_status"] is True
    assert replay["same_iterations"] is True
    for item in replay["per_replay"]:
        assert item["all_fields_pass"] is True
        assert item["status_identical"] is True
        assert item["iterations_identical"] is True
        assert all(item[field] <= 1.0e-12 for field in (
            "displacement",
            "velocity",
            "acceleration",
            "q",
            "residual_norm",
            "energy_total",
            "reactions",
        ))


def test_wp13_02b5_failure_contract_failure_is_explicit() -> None:
    evidence, contract = _load()
    failures = evidence["failure_contract"]
    for name in (
        "invalid_dt",
        "missing_mass",
        "unsupported_damping",
        "unsupported_time_load",
        "invalid_initial_conditions_unknown_dof",
        "invalid_mixed_interface",
    ):
        assert failures[name]["status"] == "REJECTED"
    assert failures["unsupported_family"]["status"] == "UNSUPPORTED_ROUTE"
    assert failures["invalid_initial_conditions_non_list"]["status"] == "NOT_REJECTED"
    assert contract["failure_contract"]["silent_fallback_allowed"] is False
    assert evidence["silent_fallback"] is False
    assert evidence["decision"]["status"] == "FAIL_FAILURE_CONTRACT"
    assert evidence["decision"]["claim_candidate"] is None
    assert evidence["integrity"] == {
        "numerical_source_changed": False,
        "formulation_changed": False,
        "gates_changed": False,
        "maturity_changed": False,
        "evidence_0_2_7_changed": False,
        "historical_v1_rewritten": False,
    }
