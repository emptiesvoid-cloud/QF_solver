from __future__ import annotations

import json
from pathlib import Path

from research.j19.replay_archived_harmonic import OUTPUT, run_replay


def test_j19_replay_five_pinned_nafems_systems_with_checkpoints() -> None:
    contract_path = Path(__file__).resolve().parents[2] / "research" / "j19" / "contracts" / "harmonic_replay_001.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    result = run_replay()

    assert result["run_state"] == "COMPLETE"
    assert len(result["results"]) == len(contract["frequencies"]) == 5
    assert [row["frequency_hz"] for row in result["results"]] == [
        item["frequency_hz"] for item in contract["frequencies"]
    ]
    for row, item in zip(result["results"], contract["frequencies"], strict=True):
        assert row["record_state"] == "COMPLETE"
        assert row["input_sha256"] == item["sha256"]
        assert row["matrix_shape"] == [175, 175]
        assert row["csr_stored_entries"] == 3607
        assert len(row["solution_real"]) == len(row["solution_imag"]) == 175
        assert row["current_guard_outcome"] in {"GUARD_ACCEPTED", "GUARD_REJECTED"}
        assert row["exact_represented_system"]["status"] in {"PASS", "FAIL", "INCONCLUSIVE"}

    assert (OUTPUT / "replay.csv").is_file()
    assert (OUTPUT / "amplitude_phase.png").is_file()
    assert json.loads((OUTPUT / "replay.json").read_text(encoding="utf-8"))["run_state"] == "COMPLETE"
