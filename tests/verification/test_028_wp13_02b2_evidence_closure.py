"""Guards for the WP13-02B2 archived Newmark evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).parents[2]
RAW = ROOT / "qualification" / "0_2_8" / "wp13_02b2_raw"
MANIFEST = RAW / "manifest.json"
ARCHIVE = RAW / "wp13_02b2_raw_arrays.npz"
CONTRACT = ROOT / "qualification" / "0_2_8" / "wp13_02a_newmark_contract.json"


def _digest(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array, dtype=np.float64).tobytes()).hexdigest()


def test_wp13_02b2_preserves_contract_and_records_ambiguity() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert manifest["contract_id"] == contract["contract_id"]
    assert manifest["contract_blob_sha"] == "7e5af8374e33e8d45a61d4a60b01127802bfca64"
    assert manifest["contract_unchanged"] is True
    assert manifest["contract_interpretation"]["contract_ambiguity"] is True
    assert manifest["decision"]["status"] == "CONTRACT_AMBIGUITY_BLOCKING"
    assert manifest["integrity"]["original_contract_rewritten"] is False
    assert manifest["integrity"]["prior_02b_results_rewritten"] is False


def test_wp13_02b2_archive_contains_all_levels_and_full_replays() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected_lengths = {20: 81, 40: 161, 80: 321, 160: 641}
    replay_fields = (
        "displacement",
        "velocity",
        "acceleration",
        "reactions",
        "energy_total",
        "residual_norm",
    )

    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == manifest["raw_archive"]["sha256"]
    with np.load(ARCHIVE, allow_pickle=False) as arrays:
        for level, length in expected_lengths.items():
            prefix = f"dt_t1_{level}_"
            assert arrays[f"{prefix}time"].shape == (length,)
            for field in ("displacement", "velocity", "acceleration"):
                assert arrays[f"{prefix}{field}"].shape == (length, 48)
            assert arrays[f"{prefix}reactions"].shape == (length, 12)
            for field in ("residual_norm", "energy_total", "modal_q", "modal_v", "modal_a"):
                assert arrays[f"{prefix}{field}"].shape == (length,)
            for field in ("q_error", "v_error", "a_error"):
                assert np.isfinite(manifest["modal_analytical_controls"][str(level)][field])
        for replay in (1, 2):
            for field in replay_fields:
                assert arrays[f"replay_{replay}_t1_160_{field}"].shape[0] == 641

        for name, metadata in manifest["raw_archive"]["array_manifest"].items():
            assert arrays[name].shape == tuple(metadata["shape"])
            assert _digest(arrays[name]) == metadata["sha256"]


def test_wp13_02b2_replays_interface_energy_and_failure_contract_are_archived() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    replay = manifest["replays"]["comparison"]
    assert replay["digests_identical"] is True
    assert replay["iterations_identical"] is True
    assert all(replay[field] <= 1.0e-12 for field in (
        "displacement_relative_l2",
        "velocity_relative_l2",
        "acceleration_relative_l2",
        "reaction_relative_l2",
        "residual_relative_l2",
        "energy_relative_l2",
    ))

    for interface in ("TET4_WEDGE6", "WEDGE6_HEX8"):
        evidence = manifest["runs"]["160"]["interface_energy"][interface]
        assert "power_left_W" in evidence
        assert "power_right_W" in evidence
        assert "energy_closure_error_J" in evidence
        assert evidence["energy_closure_error_J"] >= 0.0

    expected_rejections = (
        "invalid_dt",
        "missing_mass",
        "unsupported_damping",
        "unsupported_time_load",
        "invalid_initial_conditions",
        "invalid_mixed_interface",
    )
    failures = manifest["failure_contract"]
    assert all(failures[name]["status"] == "REJECTED" for name in expected_rejections)
    assert failures["unsupported_family"]["status"] == "UNSUPPORTED_ROUTE"
