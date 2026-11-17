from __future__ import annotations

import hashlib
import json
from pathlib import Path

from research.j19.replay_archived_harmonic import ROOT, run_replay


def test_j19_replay_five_pinned_nafems_systems_with_checkpoints() -> None:
    contract_path = Path(__file__).resolve().parents[2] / "research" / "j19" / "contracts" / "harmonic_replay_003.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    output = ROOT / "research" / "j19" / "results" / "harmonic_replay_003"
    result = run_replay(contract_path=contract_path, output_directory=output)

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

    assert (output / "replay.csv").is_file()
    assert (output / "amplitude_phase.png").is_file()
    replay = json.loads((output / "replay.json").read_text(encoding="utf-8"))
    assert replay["run_state"] == "COMPLETE"
    assert replay["contract_sha256"] == hashlib.sha256(contract_path.read_bytes()).hexdigest()
    manifest = json.loads((output / "artifact_manifest.json").read_text(encoding="utf-8"))
    assert manifest["contract_id"] == contract["contract_id"]
    assert manifest["contract_sha256"] == replay["contract_sha256"]
