"""Controls for pairwise history comparison of the archived J10 TET10 mesh family."""

from __future__ import annotations

import numpy as np
import pytest
from pathlib import Path

from research.j11_transient.j10_spatial_pairwise import analyze_archived_j10, pairwise_history_difference


ROOT = Path(__file__).resolve().parents[2]


def test_pairwise_history_difference_uses_one_shared_scale() -> None:
    result = pairwise_history_difference(
        np.asarray((0.0, 1.0, 2.0)),
        np.asarray((0.0, 2.0, 4.0)),
        shared_scale_m=2.0,
    )
    assert result["rms_absolute_difference_m"] == pytest.approx(np.sqrt(5.0 / 3.0))
    assert result["peak_absolute_difference_m"] == 2.0
    assert result["rms_normalized_to_shared_oracle_peak"] == pytest.approx(np.sqrt(5.0 / 3.0) / 2.0)
    assert result["peak_normalized_to_shared_oracle_peak"] == 1.0


def test_pairwise_history_difference_rejects_different_time_grids() -> None:
    with pytest.raises(ValueError, match="same physical time grid"):
        pairwise_history_difference(np.zeros(2), np.zeros(3), shared_scale_m=1.0)


def test_archived_j10_pairwise_postprocessing_matches_frozen_inputs() -> None:
    contract_path = ROOT / "research/j11_transient/contracts/j10_spatial_sensitivity_postprocess_contract_v3.json"
    result = analyze_archived_j10(contract_path=contract_path)
    pairs = result["pairwise_mesh_changes"]
    assert result["classification"] == "DETERMINISTIC_POSTPROCESSING_OF_ARCHIVED_J10_DATA"
    assert result["inputs"]["source_execution_status_preserved"] == "COMPLETED_EXPLORATORY"
    assert result["inputs"]["source_reference_type"] == "full-order semidiscrete modal state-space oracle"
    assert [pair["refinement_axis_added"] for pair in pairs] == [
        "axial x refinement",
        "transverse y refinement",
        "transverse z refinement",
    ]
    assert [pair["common_observation_count"] for pair in pairs] == [192, 192, 192]
    assert [pair["rms_normalized_to_shared_oracle_peak"] for pair in pairs] == pytest.approx(
        [0.189125, 0.0172688, 0.0858667], rel=2e-5
    )
    assert [pair["peak_normalized_to_shared_oracle_peak"] for pair in pairs] == pytest.approx(
        [0.510111, 0.0445018, 0.2577596], rel=2e-5
    )
