"""Exact-node entry point for the bounded J18 archived harmonic replay."""

from __future__ import annotations

import numpy as np

from research.j18.replay_archived_harmonic import run_archived_frequency_replay


def test_j18_replay_archived_nafems_13h_frequencies() -> None:
    result = run_archived_frequency_replay()

    assert result["frequency_count"] == 3
    assert result["model_identity"]["free_dof_count"] == 175
    assert result["model_identity"]["center_reduced_uz_dof"] == 86
    assert [row["frequency_hz"] for row in result["results"]] == [
        2.375818178440047,
        2.417,
        2.418,
    ]
    for row in result["results"]:
        assert np.isfinite(row["center_uz_amplitude_mm"])
        assert np.isfinite(row["center_uz_phase_degrees"])
        assert np.isfinite(row["float64_relative_residual"])
        assert row["current_guard_outcome"] in {"GUARD_ACCEPTED", "GUARD_REJECTED"}
        assert row["observed_residual_roundoff"]["status"] in {
            "OBSERVED_ERROR_WITHIN_BOUND",
            "OBSERVED_ERROR_EXCEEDS_BOUND",
            "INCONCLUSIVE",
        }
        assert row["exact_represented_system"]["status"] in {"PASS", "FAIL", "INCONCLUSIVE"}
        assert row["input_sha256"]
