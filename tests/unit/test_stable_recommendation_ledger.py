"""Guardrails for recommendation closure before stable promotion."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "qualification" / "stable_recommendation_ledger_0_2_1.json"


def test_recommendation_ledger_has_unique_ids_and_open_initial_state() -> None:
    payload = json.loads(LEDGER.read_text(encoding="utf-8"))
    entries = payload["entries"]
    ids = [entry["id"] for entry in entries]
    assert len(ids) == len(set(ids))
    assert len(entries) >= 29
    assert {entry["status"] for entry in entries} == {"open", "in_progress"}
    assert all(entry["status"] == "in_progress" or "progress_artifact" not in entry for entry in entries)
    assert all(entry["closure_evidence"] for entry in entries)


def test_first_stable_batch_is_tet4_baseline_and_requires_global_records() -> None:
    batch = json.loads(LEDGER.read_text(encoding="utf-8"))["next_batch"]
    assert batch["id"] == "ST-01-A"
    assert batch["scopes"] == ["tet4-linear-static", "tet4-modal", "tet4-transient-dynamic", "tet4-harmonic-response"]
    assert "REC-ST-028" in batch["blocking_entries"]
    assert "REC-ST-029" in batch["blocking_entries"]
