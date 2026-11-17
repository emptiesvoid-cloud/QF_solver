from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import matplotlib.axes
import numpy as np
import pytest

from research.j16.harmonic_plotting import plot_harmonic_response
from research.j16.replay_j15_harmonic_plot import replay_archived_plot


def _rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    qf = [
        {
            "frequency_hz": 2.30,
            "qf_route_status": "QF_GUARD_REJECTED",
            "diagnostic_center_uz_amplitude_mm": 17.5,
            "diagnostic_center_uz_phase_degrees": 158.1,
        },
        {
            "frequency_hz": 2.31,
            "qf_route_status": "QF_SOLVE_ACCEPTED",
            "diagnostic_center_uz_amplitude_mm": 22.0,
            "diagnostic_center_uz_phase_degrees": 145.0,
        },
        {
            "frequency_hz": 2.32,
            "qf_route_status": "QF_GUARD_REJECTED",
            "diagnostic_center_uz_amplitude_mm": 19.0,
            "diagnostic_center_uz_phase_degrees": 130.0,
        },
    ]
    reference = [
        {
            "frequency_hz": 2.30,
            "navier_uz_amplitude_mm": 24.4,
            "navier_uz_phase_degrees": 148.6,
        },
        {
            "frequency_hz": 2.31,
            "navier_uz_amplitude_mm": 27.0,
            "navier_uz_phase_degrees": 137.0,
        },
        {
            "frequency_hz": 2.32,
            "navier_uz_amplitude_mm": 30.0,
            "navier_uz_phase_degrees": 124.0,
        },
    ]
    return qf, reference


def test_j16_plot_response_uses_contract_fields_and_marks_rejected_points(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    qf_rows, reference_rows = _rows()
    original_qf = deepcopy(qf_rows)
    original_reference = deepcopy(reference_rows)
    rejected_scatter_frequencies: list[np.ndarray] = []
    original_scatter = matplotlib.axes.Axes.scatter

    def capture_scatter(self, x, y, *args, **kwargs):
        if kwargs.get("marker") == "x":
            rejected_scatter_frequencies.append(np.asarray(x, dtype=float).copy())
        return original_scatter(self, x, y, *args, **kwargs)

    monkeypatch.setattr(matplotlib.axes.Axes, "scatter", capture_scatter)
    destination = tmp_path / "harmonic_amplitude_phase.png"

    plot_harmonic_response(qf_rows, reference_rows, destination)

    assert destination.is_file() and destination.stat().st_size > 0
    assert len(rejected_scatter_frequencies) == 2
    for frequencies in rejected_scatter_frequencies:
        np.testing.assert_array_equal(frequencies, [2.30, 2.32])
    assert qf_rows == original_qf
    assert reference_rows == original_reference
    assert [row["qf_route_status"] for row in qf_rows] == [
        "QF_GUARD_REJECTED",
        "QF_SOLVE_ACCEPTED",
        "QF_GUARD_REJECTED",
    ]


def test_j16_plot_response_reports_missing_reference_field_clearly(tmp_path: Path) -> None:
    qf_rows, reference_rows = _rows()
    del reference_rows[0]["navier_uz_amplitude_mm"]

    with pytest.raises(ValueError, match="missing required field 'navier_uz_amplitude_mm'.*row 0"):
        plot_harmonic_response(qf_rows, reference_rows, tmp_path / "unused.png")


def test_j16_plot_response_rejects_misaligned_frequency_rows(tmp_path: Path) -> None:
    qf_rows, reference_rows = _rows()
    reference_rows[1]["frequency_hz"] = 2.315

    with pytest.raises(ValueError, match="same frequencies"):
        plot_harmonic_response(qf_rows, reference_rows, tmp_path / "unused.png")


def test_j16_archived_plot_replay_preserves_input_statuses_and_bytes(tmp_path: Path) -> None:
    qf_rows, reference_rows = _rows()
    input_rows = [
        {
            **qf,
            "reference_uz_amplitude_mm": reference["navier_uz_amplitude_mm"],
            "reference_uz_phase_degrees": reference["navier_uz_phase_degrees"],
        }
        for qf, reference in zip(qf_rows, reference_rows, strict=True)
    ]
    input_path = tmp_path / "site_data.json"
    input_bytes = (
        json.dumps(
            {
                "postprocess_id": "J15-NAFEMS13H-POSTPROCESS-001",
                "original_run": {"attempt_id": "J15-NAFEMS13H-RES-001", "runner_state": "PYTEST_FAILED"},
                "frequency_rows": input_rows,
            }
        )
        + "\n"
    ).encode("utf-8")
    input_path.write_bytes(input_bytes)
    output_path = tmp_path / "replay.png"
    manifest_path = tmp_path / "replay-manifest.json"

    manifest = replay_archived_plot(input_path, output_path, manifest_path)

    assert manifest["source_run_status"] == "PYTEST_FAILED"
    assert manifest["route_status_counts"] == {"QF_GUARD_REJECTED": 2, "QF_SOLVE_ACCEPTED": 1}
    assert input_path.read_bytes() == input_bytes
    assert output_path.is_file() and output_path.stat().st_size > 0
    assert [row["qf_route_status"] for row in input_rows] == [
        "QF_GUARD_REJECTED",
        "QF_SOLVE_ACCEPTED",
        "QF_GUARD_REJECTED",
    ]
