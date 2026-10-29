"""Synthetic read-only checks for the immutable R1 predecessor; no FEM."""

from __future__ import annotations

import hashlib
import json
import os
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


def test_r2_ledger_binding_accepts_distinct_paths_without_creating_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    predecessor = tmp_path / "r1.json"
    before = _write(predecessor, _ledger(), monkeypatch)
    ledger, lock = tmp_path / "r2.json", tmp_path / "r2.lock"
    assert controller._validate_wp12b_hex20_r2_ledger_binding(
        predecessor_path=predecessor, ledger_path=ledger, lock_path=lock
    ) == _ledger()
    assert predecessor.read_bytes() == before
    assert not ledger.exists() and not lock.exists()


@pytest.mark.parametrize("alias", ["ledger", "lock", "ledger_lock"])
def test_r2_ledger_binding_refuses_path_aliases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, alias: str
) -> None:
    predecessor = tmp_path / "r1.json"
    before = _write(predecessor, _ledger(), monkeypatch)
    ledger, lock = tmp_path / "r2.json", tmp_path / "r2.lock"
    if alias == "ledger":
        ledger = predecessor
    elif alias == "lock":
        lock = predecessor
    else:
        lock = ledger
    with pytest.raises(controller.PolicyError, match="distinct"):
        controller._validate_wp12b_hex20_r2_ledger_binding(
            predecessor_path=predecessor, ledger_path=ledger, lock_path=lock
        )
    assert predecessor.read_bytes() == before


def test_r2_ledger_binding_refuses_changed_predecessor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    predecessor = tmp_path / "r1.json"
    _write(predecessor, _ledger(), monkeypatch)
    predecessor.write_bytes(predecessor.read_bytes() + b" ")
    with pytest.raises(controller.PolicyError, match="different SHA"):
        controller._validate_wp12b_hex20_r2_ledger_binding(
            predecessor_path=predecessor, ledger_path=tmp_path / "r2.json", lock_path=tmp_path / "r2.lock"
        )


def test_r2_ledger_binding_refuses_hardlink_to_predecessor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    predecessor = tmp_path / "r1.json"
    before = _write(predecessor, _ledger(), monkeypatch)
    alias = tmp_path / "r2.json"
    os.link(predecessor, alias)
    with pytest.raises(controller.PolicyError, match="alias"):
        controller._validate_wp12b_hex20_r2_ledger_binding(
            predecessor_path=predecessor, ledger_path=alias, lock_path=tmp_path / "r2.lock"
        )
    assert predecessor.read_bytes() == before


def test_r2_reservation_is_independent_and_single_use(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    predecessor = tmp_path / "r1.json"
    original = _write(predecessor, _ledger(), monkeypatch)
    monkeypatch.setattr(controller, "WP12B_HEX20_R1_LEDGER_PATH", predecessor)
    ledger, lock = tmp_path / "r2.json", tmp_path / "r2.lock"
    arguments = {
        "mandate_id": controller.WP12B_HEX20_R2_MANDATE_ID,
        "worktree_id": controller.WP12B_HEX20_R2_WORKTREE_ID,
        "target": controller.WP12B_HEX20_DIAGNOSTIC_NODEID,
        "series_id": "synthetic-run",
        "source_fingerprint": "a" * 64,
        "controller_fingerprint": "b" * 64,
        "reason": "synthetic reservation without FEM",
        "maximum": 1,
        "total_maximum": 1,
        "authorization_id": "synthetic-auth",
        "owner_decision_id": "synthetic-decision",
        "predecessor": {
            "path": str(predecessor.resolve()),
            "sha256": controller.WP12B_HEX20_R1_LEDGER_SHA256,
            "mandate_id": controller.WP12B_HEX20_R1_MANDATE_ID,
        },
        "require_ledger_snapshot": True,
    }
    key, number = controller._reserve_node_attempt(ledger, lock, **arguments)
    assert number == 1
    saved = ledger.read_bytes()
    payload = json.loads(saved)
    assert payload["predecessor"] == arguments["predecessor"]
    assert payload["entries"][key][0]["owner_decision_id"] == "synthetic-decision"
    with pytest.raises(controller.PolicyError, match="exhausted"):
        controller._reserve_node_attempt(
            ledger, lock, **arguments, expected_ledger_sha256=hashlib.sha256(saved).hexdigest()
        )
    assert ledger.read_bytes() == saved
    assert predecessor.read_bytes() == original


@pytest.mark.parametrize("mutation", ["target", "decision", "fingerprint", "budget", "predecessor", "snapshot"])
def test_r2_reservation_refuses_invalid_inputs_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    predecessor = tmp_path / "r1.json"
    original = _write(predecessor, _ledger(), monkeypatch)
    monkeypatch.setattr(controller, "WP12B_HEX20_R1_LEDGER_PATH", predecessor)
    ledger, lock = tmp_path / "r2.json", tmp_path / "r2.lock"
    arguments = {
        "mandate_id": controller.WP12B_HEX20_R2_MANDATE_ID,
        "worktree_id": controller.WP12B_HEX20_R2_WORKTREE_ID,
        "target": controller.WP12B_HEX20_DIAGNOSTIC_NODEID,
        "series_id": "synthetic-run",
        "source_fingerprint": "a" * 64,
        "controller_fingerprint": "b" * 64,
        "reason": "synthetic reservation without FEM",
        "maximum": 1,
        "total_maximum": 1,
        "authorization_id": "synthetic-auth",
        "owner_decision_id": "synthetic-decision",
        "predecessor": {
            "path": str(predecessor.resolve()),
            "sha256": controller.WP12B_HEX20_R1_LEDGER_SHA256,
            "mandate_id": controller.WP12B_HEX20_R1_MANDATE_ID,
        },
        "require_ledger_snapshot": True,
    }
    if mutation == "target":
        arguments["target"] = "tests/unit/test_other.py::test_other"
    elif mutation == "decision":
        arguments["owner_decision_id"] = None
    elif mutation == "fingerprint":
        arguments["source_fingerprint"] = "invalid"
    elif mutation == "budget":
        arguments["maximum"] = 2
    elif mutation == "predecessor":
        arguments["predecessor"]["sha256"] = "0" * 64
    else:
        arguments["require_ledger_snapshot"] = False
    with pytest.raises(controller.PolicyError, match="reservation identity"):
        controller._reserve_node_attempt(ledger, lock, **arguments)
    assert not ledger.exists() and not lock.exists()
    assert predecessor.read_bytes() == original


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
