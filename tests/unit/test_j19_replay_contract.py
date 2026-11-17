from __future__ import annotations

import hashlib

import pytest

from research.j19.replay_archived_harmonic import _verified_frequency_inputs, _verify_contract_source_hashes


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
