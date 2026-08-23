from __future__ import annotations

import pytest

from scripts import benchmark_assembly_chunk_sweep as sweep


def test_chunk_sweep_archives_time_memory_and_phase_metrics(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    def fake_run_campaign(sizes, *, chunk_size, repeats):
        assert sizes == [100]
        return {
            "sizes": [
                {
                    "target_dofs": 100,
                    "dofs": 111,
                    "elements": 16,
                    "assembly_seconds": 0.2 / chunk_size,
                    "assembly_seconds_samples": [0.2 / chunk_size] * repeats,
                    "repeat_count": repeats,
                    "assembly_diagnostics": {
                        "final_nnz": 20,
                        "peak_chunk_nnz": 12 * chunk_size,
                        "sparse_memory_bytes": 256,
                        "assembly_phase_seconds": {"chunk_build": 0.2, "chunk_fusion": 0.01},
                    },
                }
            ]
        }

    monkeypatch.setattr(sweep, "run_campaign", fake_run_campaign)
    report = sweep.run_sweep(100, [4, 8], tmp_path / "sweep.json", repeats=2)

    assert report["chunk_sizes"] == [4, 8]
    assert report["sizes"][1]["peak_chunk_nnz"] == 96
    assert report["sizes"][0]["assembly_phase_seconds"]["chunk_build"] == 0.2
    assert report["recommendation"]["status"] == "PASS"
    assert report["recommendation"]["selected_chunk_size"] == 8
    assert (tmp_path / "sweep.json").is_file()


@pytest.mark.parametrize("kwargs, message", [
    ({"target_dofs": 1, "chunk_sizes": [4]}, "target_dofs"),
    ({"target_dofs": 100, "chunk_sizes": []}, "chunk_sizes"),
    ({"target_dofs": 100, "chunk_sizes": [0]}, "chunk_sizes"),
    ({"target_dofs": 100, "chunk_sizes": [4], "repeats": 0}, "repeats"),
])
def test_chunk_sweep_rejects_invalid_configuration(kwargs, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        sweep.run_sweep(**kwargs)


def test_chunk_recommendation_respects_memory_budget_and_reports_blocked() -> None:
    rows = [
        {"chunk_size": 1024, "peak_chunk_nnz": 100, "assembly_seconds": 2.0},
        {"chunk_size": 2048, "peak_chunk_nnz": 200, "assembly_seconds": 1.0},
    ]
    selected = sweep.recommend_chunk_size(rows, memory_budget_bytes=5_000)
    assert selected["selected_chunk_size"] == 2048
    blocked = sweep.recommend_chunk_size(rows, memory_budget_bytes=100)
    assert blocked["status"] == "BLOCKED"
    assert blocked["selected_chunk_size"] is None


def test_chunk_recommendation_rejects_invalid_budget() -> None:
    with pytest.raises(ValueError, match="memory_budget_bytes"):
        sweep.recommend_chunk_size(
            [{"chunk_size": 1, "peak_chunk_nnz": 1, "assembly_seconds": 1.0}],
            memory_budget_bytes=0,
        )
