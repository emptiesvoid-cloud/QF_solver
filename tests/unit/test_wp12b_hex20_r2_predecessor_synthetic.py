"""Synthetic read-only checks for the immutable R1 predecessor; no FEM."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import development_autonomous as controller


def _ledger() -> dict:
    key = (
        f"{controller.WP12B_HEX20_R1_MANDATE_ID}:"
        f"{controller.WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID}:"
        f"{controller.WP12B_HEX20_DIAGNOSTIC_NODEID}"
    )
    return {
        "schema": "qfsolver-development-node-ledger-v1",
        "mandate_id": controller.WP12B_HEX20_R1_MANDATE_ID,
        "entries": {key: [{"attempt": 1, "state": "PROVENANCE_MISMATCH"}]},
    }


def _write(path: Path, value: object, monkeypatch: pytest.MonkeyPatch) -> bytes:
    raw = json.dumps(value, sort_keys=True).encode("utf-8")
    path.write_bytes(raw)
    monkeypatch.setattr(controller, "WP12B_HEX20_R1_LEDGER_SHA256", hashlib.sha256(raw).hexdigest())
    return raw


def test_r1_predecessor_accepts_one_matching_attempt_without_writing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "r1.json"
    before = _write(path, _ledger(), monkeypatch)
    assert controller._validate_wp12b_hex20_r1_predecessor(path) == _ledger()
    assert path.read_bytes() == before


def test_r1_predecessor_refuses_missing_or_changed_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "r1.json"
    with pytest.raises(controller.PolicyError, match="missing or has a different SHA"):
        controller._validate_wp12b_hex20_r1_predecessor(path)
    _write(path, _ledger(), monkeypatch)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(controller.PolicyError, match="missing or has a different SHA"):
        controller._validate_wp12b_hex20_r1_predecessor(path)


@pytest.mark.parametrize("raw", [b"{broken", b'{"value": NaN}'])
def test_r1_predecessor_refuses_invalid_json_even_when_hash_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raw: bytes
) -> None:
    path = tmp_path / "r1.json"
    path.write_bytes(raw)
    monkeypatch.setattr(controller, "WP12B_HEX20_R1_LEDGER_SHA256", hashlib.sha256(raw).hexdigest())
    with pytest.raises(controller.PolicyError, match="unreadable"):
        controller._validate_wp12b_hex20_r1_predecessor(path)
    assert path.read_bytes() == raw


@pytest.mark.parametrize("mutation", ["mandate", "schema", "extra", "attempt", "state"])
def test_r1_predecessor_refuses_incompatible_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    ledger = _ledger()
    key = next(iter(ledger["entries"]))
    if mutation == "mandate":
        ledger["mandate_id"] = "OTHER"
    elif mutation == "schema":
        ledger["schema"] = "other"
    elif mutation == "extra":
        ledger["entries"]["other"] = []
    elif mutation == "attempt":
        ledger["entries"][key][0]["attempt"] = 2
    else:
        ledger["entries"][key][0]["state"] = "PASS"
    path = tmp_path / "r1.json"
    before = _write(path, ledger, monkeypatch)
    with pytest.raises(controller.PolicyError, match="incompatible history"):
        controller._validate_wp12b_hex20_r1_predecessor(path)
    assert path.read_bytes() == before
