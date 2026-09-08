"""Targeted WP13-02B15 residual normalization and schema guards."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
from jsonschema import Draft202012Validator

ROOT = Path(__file__).parents[2]
B13 = ROOT / "qualification" / "0_2_8" / "wp13_02b13_v2"
B15 = ROOT / "qualification" / "0_2_8" / "wp13_02b15_residual_normalization"
B15_MANIFEST = B15 / "manifest.json"
B15_ARCHIVE = B15 / "wp13_02b15_residual_arrays.npz"
SCHEMA = ROOT / "qualification" / "0_2_8" / "wp13_02b15_evidence.schema.json"
START_SHA = "6c5d5852e26a40fddf968692bdc98b102839ec0e"


def _digest(value: np.ndarray) -> str:
    return hashlib.sha256(
        np.ascontiguousarray(value, dtype=np.float64).tobytes()
    ).hexdigest()


def _load() -> tuple[dict, dict, dict]:
    manifest = json.loads(B15_MANIFEST.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    b13_manifest = json.loads((B13 / "manifest.json").read_text(encoding="utf-8"))
    return manifest, schema, b13_manifest


def test_b15_schema_and_source_digests_are_valid() -> None:
    manifest, schema, b13_manifest = _load()
    Draft202012Validator(schema).validate(manifest)
    assert manifest["source_residual_arrays_valid"] is True
    assert manifest["residual"]["denominator_source"] == "Fstar"
    assert manifest["residual"]["variable_denominator_used"] is False
    assert manifest["fstar"]["value_N"] == 36256.97002179186
    assert manifest["archive"]["array_count"] == 7
    assert manifest["source"]["old_history_preserved"] is True
    assert len(b13_manifest["repo_sha"]) == 40
    assert manifest["source"]["b13_campaign_repo_sha"] == b13_manifest["repo_sha"]

    with np.load(B15_ARCHIVE, allow_pickle=False) as arrays:
        for name, metadata in manifest["archive"]["array_manifest"].items():
            assert name in arrays.files
            assert list(arrays[name].shape) == metadata["shape"]
            assert _digest(arrays[name]) == metadata["sha256"]


def test_b15_histories_use_fstar_and_replay_arrays_match() -> None:
    manifest, _, _ = _load()
    with np.load(B13 / "wp13_02b13_arrays.npz", allow_pickle=False) as source:
        with np.load(B15_ARCHIVE, allow_pickle=False) as derived:
            free = np.asarray(source["oracle_free_indices"], dtype=int)
            fstar = manifest["fstar"]["value_N"]
            for label, tag in (("T1/20", "20"), ("T1/40", "40"), ("T1/80", "80"), ("T1/160", "160")):
                expected = np.linalg.norm(
                    source[f"dt_t1_{tag}_residual_vector"][:, free], axis=1
                ) / fstar
                actual = derived[f"dt_t1_{tag}_residual_relative_fstar"]
                assert np.array_equal(actual, expected)
                assert manifest["residual"]["by_level"][label]["max_value"] == float(np.max(expected))

            main = derived["replay_0_t1_160_residual_relative_fstar"]
            for replay in ("replay_1", "replay_2"):
                other = derived[f"{replay}_t1_160_residual_relative_fstar"]
                assert np.max(np.abs(main - other)) <= 1.0e-12
    assert manifest["replay_history_comparison"]["main_replay_1"]["pass"] is True
    assert manifest["replay_history_comparison"]["main_replay_2"]["pass"] is True


def test_schema_rejects_old_b13_and_variable_denominator_evidence() -> None:
    manifest, schema, b13_manifest = _load()
    validator = Draft202012Validator(schema)
    assert validator.is_valid(b13_manifest) is False

    invalid = copy.deepcopy(manifest)
    invalid["residual"]["denominator_source"] = "variable_residual_reference"
    assert validator.is_valid(invalid) is False
    assert manifest["source"]["old_b13_evidence_detected_nonconforming"] is True


def test_iterations_and_history_records_are_preserved() -> None:
    manifest, _, _ = _load()
    iterations = manifest["iterations"]
    assert manifest["iterations_contract_status"] == "PASS"
    assert all(iterations[name] == [1] * 640 for name in ("main", "replay_1", "replay_2"))
    assert all(manifest["historical_records"][name]["present"] for name in (
        "B5", "B6", "B7", "B8", "B9", "B10", "B11", "B12", "B12b", "B13", "B14"
    ))
