"""Synthetic tests for immutable HEX8-SRI sidecar writes; no FEM imports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiments.hex8_sri_equilibrium.campaign import atomic_write_json_new, atomic_write_new_bytes


def test_sidecar_json_is_created_with_a_matching_digest(tmp_path: Path) -> None:
    destination = tmp_path / "evidence" / "case.json"
    payload = {"schema": "synthetic", "verdict": "NOT_RUN"}

    digest = atomic_write_json_new(destination, payload)

    assert json.loads(destination.read_text(encoding="utf-8")) == payload
    assert digest == hashlib.sha256(destination.read_bytes()).hexdigest()
    assert not list(destination.parent.glob("*.tmp"))


def test_sidecar_writer_refuses_replacement_and_cleans_temporary_file(tmp_path: Path) -> None:
    destination = tmp_path / "state.npz"
    original = b"first immutable artifact"
    atomic_write_new_bytes(destination, original)

    with pytest.raises(FileExistsError):
        atomic_write_new_bytes(destination, b"replacement must not be installed")

    assert destination.read_bytes() == original
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob(".*.tmp"))
