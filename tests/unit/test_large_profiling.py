from __future__ import annotations

import json
from pathlib import Path

import pytest

from solveur.large.profiling import parse_petsc_log_view, write_petsc_profile_report


def _write_profile(path: Path, *, scale: float = 1.0) -> Path:
    path.write_text(
        "\n".join(
            [
                "size = 2",
                "LocalTimes = {}",
                "LocalMessages = {}",
                "LocalMessageLens = {}",
                "LocalReductions = {}",
                "LocalFlop = {}",
                f"LocalTimes[0] = {10.0 * scale}",
                f"LocalTimes[1] = {8.0 * scale}",
                "LocalMessages[0] = 30.",
                "LocalMessages[1] = 20.",
                "LocalMessageLens[0] = 3000.",
                "LocalMessageLens[1] = 2000.",
                "LocalReductions[0] = 12.",
                "LocalReductions[1] = 12.",
                "LocalFlop[0] = 1000.",
                "LocalFlop[1] = 900.",
                'Stages["Main Stage"]["KSPSolve"][0] = '
                f'{{"count" : 1, "time" : {6.0 * scale}, "numMessages" : 20., '
                '"messageLength" : 2000., "numReductions" : 8., "flop" : 800.}',
                'Stages["Main Stage"]["KSPSolve"][1] = '
                f'{{"count" : 1, "time" : {5.0 * scale}, "numMessages" : 18., '
                '"messageLength" : 1800., "numReductions" : 8., "flop" : 700.}',
                'Stages["Main Stage"]["PCSetUp"][0] = '
                f'{{"count" : 1, "time" : {2.0 * scale}, "numMessages" : 5., '
                '"messageLength" : 500., "numReductions" : 2., "flop" : 100.}',
                'Stages["Main Stage"]["PCSetUp"][1] = '
                f'{{"count" : 1, "time" : {1.5 * scale}, "numMessages" : 4., '
                '"messageLength" : 400., "numReductions" : 2., "flop" : 90.}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_parse_petsc_log_view_aggregates_rank_and_event_metrics(tmp_path: Path) -> None:
    profile = parse_petsc_log_view(_write_profile(tmp_path / "petsc.txt"))

    assert profile["mpi_size"] == 2
    assert profile["rank_time_seconds"]["max"] == pytest.approx(10.0)
    assert profile["rank_time_seconds"]["imbalance"] == pytest.approx(10.0 / 9.0)
    assert profile["communication"]["messages_sum"] == pytest.approx(50.0)
    assert profile["focus_events"]["KSPSolve"]["time_max_seconds"] == pytest.approx(6.0)
    assert profile["focus_events"]["KSPSolve"]["messages_sum"] == pytest.approx(38.0)


def test_profile_report_writes_traceable_json_markdown_and_manifest(tmp_path: Path) -> None:
    first = _write_profile(tmp_path / "block.txt")
    second = _write_profile(tmp_path / "beam.txt", scale=1.5)

    result = write_petsc_profile_report(
        (first, second),
        tmp_path / "report",
        labels=("block", "beam"),
    )

    assert result["status"] == "PASS"
    assert [profile["label"] for profile in result["profiles"]] == ["block", "beam"]
    assert (tmp_path / "report" / "petsc_profile_comparison.md").is_file()
    assert (tmp_path / "report" / "evidence_manifest.json").is_file()
    stored = json.loads((tmp_path / "report" / "petsc_profile_comparison.json").read_text(encoding="utf-8"))
    assert stored["profiles"][1]["total_time_max_seconds"] == pytest.approx(15.0)


def test_profile_parser_rejects_incomplete_or_ambiguous_inputs(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.txt"
    invalid.write_text("size = 2\nLocalTimes[0] = 1.0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected 2"):
        parse_petsc_log_view(invalid)
    profile = _write_profile(tmp_path / "valid.txt")
    with pytest.raises(ValueError, match="match the number"):
        write_petsc_profile_report((profile,), tmp_path / "bad", labels=("one", "two"))
    with pytest.raises(ValueError, match="unique"):
        write_petsc_profile_report((profile, profile), tmp_path / "duplicate", labels=("same", "same"))
