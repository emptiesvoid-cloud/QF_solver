from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from research.j19.replay_archived_harmonic import (
    _validated_contract_fields,
    _verified_frequency_inputs,
    _verify_contract_source_hashes,
)


def test_j19_replay_contract_verifies_per_frequency_archive_digest(tmp_path) -> None:
    archive = tmp_path / "system.npz"
    archive.write_bytes(b"pinned represented system")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    contract = {
        "frequencies": [
            {
                "frequency_hz": 2.375,
                "archive_path": archive.name,
                "sha256": digest,
            }
        ]
    }

    verified = _verified_frequency_inputs(contract, root=tmp_path)

    assert verified == contract["frequencies"]
    contract["frequencies"][0]["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="input SHA-256 mismatch"):
        _verified_frequency_inputs(contract, root=tmp_path)


def test_j19_replay_contract_rejects_missing_or_duplicate_frequency_metadata(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="nonempty frequency list"):
        _verified_frequency_inputs({"frequencies": []}, root=tmp_path)
    with pytest.raises(RuntimeError, match="SHA-256 digest"):
        _verified_frequency_inputs(
            {"frequencies": [{"frequency_hz": 2.3, "archive_path": "system.npz"}]},
            root=tmp_path,
        )

    archive = tmp_path / "system.npz"
    archive.write_bytes(b"data")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    duplicate = {
        "frequencies": [
            {"frequency_hz": 2.3, "archive_path": archive.name, "sha256": digest},
            {"frequency_hz": 2.3, "archive_path": archive.name, "sha256": digest},
        ]
    }
    with pytest.raises(RuntimeError, match="finite and unique"):
        _verified_frequency_inputs(duplicate, root=tmp_path)


def test_j19_replay_contract_verifies_pinned_source_hashes(tmp_path) -> None:
    source = tmp_path / "replay.py"
    source.write_text("frozen source", encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    contract = {"source_hashes": {source.name: digest}}

    _verify_contract_source_hashes(contract, root=tmp_path)

    source.write_text("mutated source", encoding="utf-8")
    with pytest.raises(RuntimeError, match="source SHA-256 mismatch"):
        _verify_contract_source_hashes(contract, root=tmp_path)


def test_j19_contract_uses_nested_baseline_and_model_metadata() -> None:
    root = Path(__file__).resolve().parents[2]
    contract_path = root / "research" / "j19" / "contracts" / "harmonic_replay_002.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    source_commit, shape, stored_entries, center_dof, limits = _validated_contract_fields(contract)

    assert source_commit == contract["baseline"]["source_code_commit"]
    assert shape == (175, 175)
    assert stored_entries == 3607
    assert center_dof == 86
    assert limits["max_seconds_per_frequency"] == 5
    assert "source_code_commit" not in contract
    assert "center_reduced_uz_dof" not in contract


def test_j19_contract_rejects_missing_nested_baseline_or_model_fields() -> None:
    with pytest.raises(RuntimeError, match="full source_code_commit SHA"):
        _validated_contract_fields({"baseline": {}, "model": {}, "exact_limits": {}})
