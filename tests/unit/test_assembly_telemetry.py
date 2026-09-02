"""Targeted tests for optional WP04 assembly progress telemetry."""

from __future__ import annotations

import json
from pathlib import Path

from solveur.large.telemetry import AssemblyTelemetry


def _records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_jsonl_progress_phase_and_million_slices_are_persistent(tmp_path: Path) -> None:
    path = tmp_path / "wp04_5m_progress.jsonl"
    telemetry = AssemblyTelemetry(path, 2_000_000, checkpoint_elements=100_000, run_id="run1", source_sha="a" * 40)
    telemetry.phase("GENERATING")
    telemetry.phase("ASSEMBLING")
    for processed in (100_000, 1_000_000, 2_000_000):
        telemetry.checkpoint(processed)
    telemetry.phase("COMPLETED")
    telemetry.close()

    records = _records(path)
    assert [record["phase"] for record in records] == ["GENERATING", "ASSEMBLING", "MAT_ASSEMBLY", "MAT_ASSEMBLY", "MAT_ASSEMBLY", "COMPLETED"]
    checkpoints = [record for record in records if record["event"] == "checkpoint"]
    assert [record["elements_processed"] for record in checkpoints] == [100_000, 1_000_000, 2_000_000]
    assert checkpoints[-1]["progress_percent"] == 100.0
    assert checkpoints[1]["avg_elements_per_s"] is not None
    assert checkpoints[2]["recent_elements_per_s"] is not None
    assert [item["milestone_elements"] for item in checkpoints[1]["million_element_slices"]] == [1_000_000]
    assert [item["milestone_elements"] for item in checkpoints[2]["million_element_slices"]] == [2_000_000]
    assert all(record["rank"] == 0 for record in records)


def test_global_progress_callback_and_interrupted_log(tmp_path: Path) -> None:
    path = tmp_path / "progress.jsonl"
    telemetry = AssemblyTelemetry(
        path,
        200,
        local_elements_total=100,
        checkpoint_elements=10,
        global_progress=lambda local: local * 2,
    )
    telemetry.phase("MAT_ASSEMBLY")
    telemetry.checkpoint(50)
    telemetry.checkpoint(100)
    telemetry.close()

    checkpoints = [record for record in _records(path) if record["event"] == "checkpoint"]
    assert [record["elements_processed"] for record in checkpoints] == [100, 200]
    assert [record["elements_total"] for record in checkpoints] == [200, 200]


def test_disabled_telemetry_does_not_create_a_log(tmp_path: Path) -> None:
    path = tmp_path / "disabled.jsonl"
    telemetry = AssemblyTelemetry(None, 10)
    telemetry.phase("MAT_ASSEMBLY")
    telemetry.checkpoint(10)
    telemetry.close()
    assert not path.exists()
    assert telemetry.status == "DISABLED"


def test_log_open_failure_degrades_without_raising(tmp_path: Path, caplog) -> None:
    directory = tmp_path / "already-a-directory"
    directory.mkdir()
    telemetry = AssemblyTelemetry(directory, 10)
    telemetry.phase("FAILED")
    telemetry.checkpoint(10)
    telemetry.close()
    assert telemetry.status == "DEGRADED"
    assert "telemetry" in caplog.text.lower()
