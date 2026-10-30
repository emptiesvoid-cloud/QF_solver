"""Synthetic controller checks; no FEM body, official preflight, or reservation."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import wp12_vv3d_tet4_l3_diagnostic as diagnostic


def _record(fields: dict, *, sequence: int, previous: str) -> dict:
    body = {"schema": "qf-vv3d-tet4-l3-diagnostic-ledger-v1", "sequence": sequence,
            "previous_record_sha256": previous, "scope_id": diagnostic.PREVIOUS_SCOPE,
            "case_id": diagnostic.CASE, "r1_sha256": diagnostic.REGISTRATION["r1_sha256"],
            "r2_sha256": diagnostic.REGISTRATION["r2_sha256"],
            **fields}
    body["record_sha256"] = diagnostic.digest(diagnostic.canonical(body))
    return body


def _previous_diagnostic_bytes(*, status: str = "DIAGNOSTIC_STOP") -> bytes:
    start = _record({"event": "ATTEMPT_STARTED", "run_id": "diag-previous",
                     "attempt_id": "diag-previous-attempt-1", "reservation_id": "diag-res-previous",
                     "reserved_seconds": 2400, "prior_attempts": 5,
                     "prior_elapsed_seconds": 1355.1373992000008}, sequence=1, previous="0" * 64)
    finish = _record({"event": "ATTEMPT_FINISHED", "run_id": "diag-previous",
                      "attempt_id": "diag-previous-attempt-1", "status": status,
                      "elapsed_seconds": 2400.2913701999933,
                      "combined_elapsed_seconds": 3755.428769399994},
                     sequence=2, previous=start["record_sha256"])
    return diagnostic.canonical(start) + b"\n" + diagnostic.canonical(finish) + b"\n"


def test_previous_diagnostic_ledger_hash_and_terminal_are_validated() -> None:
    raw = _previous_diagnostic_bytes()
    result = diagnostic.validate_previous_diagnostic_ledger(raw, diagnostic.digest(raw))
    assert result["attempts"] == 1
    assert result["elapsed_seconds"] == 2400.2913701999933
    assert result["status"] == "DIAGNOSTIC_STOP"

    with pytest.raises(ValueError, match="hash|digest"):
        diagnostic.validate_previous_diagnostic_ledger(raw, "f" * 64)
    inconsistent = _previous_diagnostic_bytes(status="PASS")
    with pytest.raises(ValueError, match="terminal|STOP|status"):
        diagnostic.validate_previous_diagnostic_ledger(inconsistent, diagnostic.digest(inconsistent))


def test_predecessor_history_reads_three_ledgers_without_mutation(tmp_path: Path, monkeypatch) -> None:
    r1 = tmp_path / "r1.jsonl"
    r2 = tmp_path / "r2.jsonl"
    old_diagnostic = tmp_path / "previous-diagnostic.jsonl"
    r1_raw, r2_raw = b"synthetic-r1-ledger\n", b"synthetic-r2-ledger\n"
    for path, raw in ((r1, r1_raw), (r2, r2_raw)):
        path.write_bytes(raw)

    config = {**diagnostic.REGISTRATION,
              "r1_sha256": diagnostic.digest(r1_raw), "r2_sha256": diagnostic.digest(r2_raw),
              "predecessor_diagnostic_sha256": "pending"}
    monkeypatch.setattr(diagnostic, "REGISTRATION", config)
    monkeypatch.setattr(diagnostic, "R1_PATH", r1)
    monkeypatch.setattr(diagnostic, "R2_PATH", r2)
    monkeypatch.setattr(diagnostic, "PREVIOUS_DIAGNOSTIC_PATH", old_diagnostic)
    old_raw = _previous_diagnostic_bytes()
    config["predecessor_diagnostic_sha256"] = diagnostic.digest(old_raw)
    old_diagnostic.write_bytes(old_raw)

    r2_records = [
        {"event": "ATTEMPT_STARTED", "case_id": case}
        for case in ("VV3D-TET4-L1", "VV3D-TET4-L2", "VV3D-TET4-L3")
    ] + [
        {"event": "ATTEMPT_FINISHED", "case_id": case, "status": status,
         "elapsed_seconds": elapsed}
        for case, status, elapsed in (("VV3D-TET4-L1", "PASS", 100.0),
                                      ("VV3D-TET4-L2", "PASS", 200.0),
                                      ("VV3D-TET4-L3", "INFRA_ERROR", 355.1373992000008))
    ]

    class SyntheticR2Ledger:
        def __init__(self, *_args, **_kwargs):
            pass

        def _read_unlocked(self):
            return copy.deepcopy(r2_records)

        def _predecessor(self):
            return 2, 700.0

    fake_controller = SimpleNamespace(
        _load_vv3d_r2_ledger_module=lambda: SimpleNamespace(RecoveryR2Ledger=SyntheticR2Ledger))
    before = tuple(path.read_bytes() for path in (r1, r2, old_diagnostic))
    history = diagnostic.predecessor_history(fake_controller)

    assert history["r1_attempts"] == 2
    assert history["r2_attempts"] == 3
    assert history["previous_diagnostic_attempts"] == 1
    assert history["elapsed_seconds"] == 3755.428769399994
    assert history["r1_sha256"] == config["r1_sha256"]
    assert history["r2_sha256"] == config["r2_sha256"]
    assert history["previous_diagnostic_sha256"] == config["predecessor_diagnostic_sha256"]
    assert tuple(path.read_bytes() for path in (r1, r2, old_diagnostic)) == before


def test_previous_diagnostic_hash_mismatch_fails_closed_in_history(tmp_path: Path, monkeypatch) -> None:
    r1, r2, old_diagnostic = (tmp_path / name for name in ("r1", "r2", "previous.jsonl"))
    r1.write_bytes(b"synthetic-r1")
    r2.write_bytes(b"synthetic-r2")
    config = {**diagnostic.REGISTRATION, "r1_sha256": diagnostic.digest(r1.read_bytes()),
              "r2_sha256": diagnostic.digest(r2.read_bytes()),
              "predecessor_diagnostic_sha256": "0" * 64}
    monkeypatch.setattr(diagnostic, "REGISTRATION", config)
    monkeypatch.setattr(diagnostic, "R1_PATH", r1)
    monkeypatch.setattr(diagnostic, "R2_PATH", r2)
    monkeypatch.setattr(diagnostic, "PREVIOUS_DIAGNOSTIC_PATH", old_diagnostic)
    old_diagnostic.write_bytes(_previous_diagnostic_bytes())

    records = ([{"event": "ATTEMPT_STARTED", "case_id": case}
                for case in ("VV3D-TET4-L1", "VV3D-TET4-L2", "VV3D-TET4-L3")] +
               [{"event": "ATTEMPT_FINISHED", "case_id": case, "status": status,
                 "elapsed_seconds": elapsed}
                for case, status, elapsed in (("VV3D-TET4-L1", "PASS", 100.0),
                                              ("VV3D-TET4-L2", "PASS", 200.0),
                                              ("VV3D-TET4-L3", "INFRA_ERROR", 355.1373992000008))])

    class SyntheticR2Ledger:
        def __init__(self, *_args, **_kwargs):
            pass

        def _read_unlocked(self):
            return records

        def _predecessor(self):
            return 2, 700.0

    fake_controller = SimpleNamespace(
        _load_vv3d_r2_ledger_module=lambda: SimpleNamespace(RecoveryR2Ledger=SyntheticR2Ledger))
    with pytest.raises(ValueError, match="hash|digest"):
        diagnostic.predecessor_history(fake_controller)


def test_combined_budget_counts_all_predecessors_before_new_reservation() -> None:
    predecessor = {"r1_attempts": 2, "r2_attempts": 3, "previous_diagnostic_attempts": 1,
                   "elapsed_seconds": 3755.428769399994}
    budget = diagnostic.combined_budget(predecessor, diagnostic.REGISTRATION)
    assert budget == {
        "attempts_before": 6,
        "attempts_after_reservation": 7,
        "elapsed_seconds_before": 3755.428769399994,
        "elapsed_seconds_after_reservation": 4955.428769399994,
        "attempt_limit": 24,
        "elapsed_limit_seconds": 28800,
    }

    with pytest.raises(ValueError, match="attempt|budget"):
        diagnostic.combined_budget({"r1_attempts": 24, "r2_attempts": 0,
                                    "previous_diagnostic_attempts": 0, "elapsed_seconds": 1.0},
                                   diagnostic.REGISTRATION)
    with pytest.raises(ValueError, match="time|seconds|budget"):
        diagnostic.combined_budget({"r1_attempts": 1, "r2_attempts": 0,
                                    "previous_diagnostic_attempts": 0, "elapsed_seconds": 27601.0},
                                   diagnostic.REGISTRATION)


def test_new_diagnostic_scope_is_isolated_and_cannot_reuse_old_scope() -> None:
    assert diagnostic.SCOPE == "wp12_vv3d_tet4_l3_optimized_diagnostic"
    policy = {"diagnostic_scopes": {
        diagnostic.PREVIOUS_SCOPE: {"historical_read_only": True},
        diagnostic.SCOPE: copy.deepcopy(diagnostic.REGISTRATION),
    }}
    assert diagnostic.registration(policy)["timeout_seconds"] == 1200
    old_scope_policy = {"diagnostic_scopes": {
        "wp12_vv3d_tet4_l3_diagnostic": copy.deepcopy(diagnostic.REGISTRATION)}}
    with pytest.raises(ValueError, match="registration|scope"):
        diagnostic.registration(old_scope_policy)


def test_inspect_accepts_only_a_separate_synthetic_evidence_root(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source"
    field_error = source / "experiments/wp12_vv3d_adaptive/field_error_draft.py"
    field_error.parent.mkdir(parents=True)
    field_error_raw = b"synthetic field-error draft\n"
    field_error.write_bytes(field_error_raw)
    old_evidence = tmp_path / "old-evidence"
    new_evidence = tmp_path / "new-evidence"
    monkeypatch.setattr(diagnostic, "PREVIOUS_EVIDENCE_ROOT", old_evidence)

    class SyntheticController:
        ROOT = tmp_path

        def load_policy(self):
            return {"diagnostic_scopes": {
                diagnostic.PREVIOUS_SCOPE: {"historical_read_only": True},
                diagnostic.SCOPE: config,
            }}

        def _git_identity(self, *_args, **_kwargs):
            return {"head": "synthetic-head", "tree": "synthetic-tree", "status_short": ""}

        def _worktree_source_fingerprint(self, *_args, **_kwargs):
            return "a" * 64

        def _stable_fingerprint(self, _provenance):
            return "synthetic-controller-fingerprint"

    config = {**diagnostic.REGISTRATION, "root": str(source), "evidence_root": str(new_evidence),
              "branch": "synthetic-branch", "head": "synthetic-head", "tree": "synthetic-tree",
              "source_fingerprint_sha256": "a" * 64,
              "field_error_draft_sha256": diagnostic.digest(field_error_raw)}
    monkeypatch.setattr(diagnostic, "REGISTRATION", config)
    monkeypatch.setattr(diagnostic, "controller_provenance", lambda _controller: {
        "identity": {"status_short": "", "branch": ""}})
    monkeypatch.setattr(diagnostic, "predecessor_history", lambda _controller: {
        "r1_attempts": 2, "r2_attempts": 3, "previous_diagnostic_attempts": 1,
        "elapsed_seconds": 3755.428769399994})
    report = diagnostic.inspect(SyntheticController())
    assert report["scope_id"] == diagnostic.SCOPE
    assert report["combined_budget"]["attempts_after_reservation"] == 7
    assert not new_evidence.exists()

    config["evidence_root"] = str(old_evidence)
    with pytest.raises(ValueError, match="distinct new evidence root"):
        diagnostic.inspect(SyntheticController())
    assert not old_evidence.exists()

    config["evidence_root"] = str(new_evidence)
    new_evidence.mkdir()
    ledger = new_evidence / config["ledger"]
    ledger.write_bytes(b"synthetic prior reservation\n")
    before = ledger.read_bytes()
    with pytest.raises(ValueError, match="implicit retry|already exists"):
        diagnostic.inspect(SyntheticController())
    assert ledger.read_bytes() == before


def test_attempt_ledger_rejects_any_implicit_retry(tmp_path: Path) -> None:
    ledger = tmp_path / "synthetic-optimized-ledger.jsonl"
    start = diagnostic._append_record(ledger, {
        "event": "ATTEMPT_STARTED", "run_id": "synthetic-run", "attempt_id": "synthetic-attempt",
        "reserved_seconds": 1200, "prior_attempts": 6, "prior_elapsed_seconds": 3755.428769399994,
    }, first=True)
    with pytest.raises((FileExistsError, ValueError)):
        diagnostic._append_record(ledger, {
            "event": "ATTEMPT_STARTED", "run_id": "synthetic-retry", "attempt_id": "retry-attempt",
        }, first=True)
    diagnostic._append_record(ledger, {
        "event": "ATTEMPT_FINISHED", "run_id": "synthetic-run", "attempt_id": "synthetic-attempt",
        "status": "DIAGNOSTIC_STOP", "elapsed_seconds": 0.25,
    }, first=False)
    finished = ledger.read_bytes()
    assert json.loads(finished.splitlines()[0])["record_sha256"] == start["record_sha256"]
    with pytest.raises(ValueError, match="single-attempt|retry|open"):
        diagnostic._append_record(ledger, {
            "event": "ATTEMPT_FINISHED", "run_id": "synthetic-run", "attempt_id": "synthetic-attempt",
            "status": "DIAGNOSTIC_STOP", "elapsed_seconds": 0.25,
        }, first=False)
    assert ledger.read_bytes() == finished
