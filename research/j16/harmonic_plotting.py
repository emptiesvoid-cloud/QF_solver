"""Plot harmonic response rows while retaining their route status."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402


def _column(source_rows: list[dict[str, Any]], field: str, label: str) -> np.ndarray:
    values: list[float] = []
    for index, row in enumerate(source_rows):
        if field not in row:
            raise ValueError(f"plot_harmonic_response missing required field {field!r} in {label} row {index}")
        try:
            value = float(row[field])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"plot_harmonic_response field {field!r} in {label} row {index} must be numeric"
            ) from exc
        if not math.isfinite(value):
            raise ValueError(f"plot_harmonic_response field {field!r} in {label} row {index} must be finite")
        values.append(value)
    return np.asarray(values, dtype=float)


def plot_harmonic_response(
    rows: list[dict[str, Any]], reference_rows: list[dict[str, Any]], path: Path
) -> None:
    """Write amplitude and phase plots without changing either input table."""
    if len(rows) != len(reference_rows):
        raise ValueError(
            "plot_harmonic_response requires the same number of QF and reference rows "
            f"(got {len(rows)} and {len(reference_rows)})"
        )

    frequencies = _column(rows, "frequency_hz", "QF")
    reference_frequencies = _column(reference_rows, "frequency_hz", "reference")
    if not np.allclose(frequencies, reference_frequencies, rtol=0.0, atol=1.0e-12):
        raise ValueError("plot_harmonic_response QF and reference rows must use the same frequencies")
    qf_amplitude = _column(rows, "diagnostic_center_uz_amplitude_mm", "QF")
    qf_phase = _column(rows, "diagnostic_center_uz_phase_degrees", "QF")
    ref_amplitude = _column(reference_rows, "navier_uz_amplitude_mm", "Navier reference")
    ref_phase = _column(reference_rows, "navier_uz_phase_degrees", "Navier reference")
    route_statuses = [row.get("qf_route_status") for row in rows]
    if any(not isinstance(status, str) or not status for status in route_statuses):
        raise ValueError("plot_harmonic_response requires a non-empty qf_route_status for every QF row")
    if np.any(qf_amplitude < 0.0) or np.any(ref_amplitude < 0.0):
        raise ValueError("plot_harmonic_response amplitude fields must be nonnegative")

    max_amplitude = float(np.max(qf_amplitude))
    phase_mask = (qf_amplitude >= 0.05 * max_amplitude) & (qf_amplitude > 0.0)
    rejected = np.asarray([status != "QF_SOLVE_ACCEPTED" for status in route_statuses], dtype=bool)
    figure, axes = plt.subplots(2, 1, figsize=(9, 8), sharex=True, constrained_layout=True)
    axes[0].plot(frequencies, qf_amplitude, color="#b23a48", label="QF response")
    axes[0].plot(frequencies, ref_amplitude, "--", color="#176b87", label="Reference")
    axes[0].scatter(
        frequencies[rejected],
        qf_amplitude[rejected],
        marker="x",
        s=15,
        color="#5f0f40",
        label="QF route rejected; diagnostic vector shown",
    )
    axes[0].set_ylabel("Center |UZ| (mm)")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(fontsize=8)
    axes[1].plot(frequencies[phase_mask], qf_phase[phase_mask], color="#b23a48", label="QF response")
    axes[1].plot(frequencies[phase_mask], ref_phase[phase_mask], "--", color="#176b87", label="Reference")
    rejected_phase = rejected & phase_mask
    axes[1].scatter(
        frequencies[rejected_phase],
        qf_phase[rejected_phase],
        marker="x",
        s=15,
        color="#5f0f40",
        label="QF route rejected; diagnostic phase shown",
    )
    axes[1].set_xlabel("Frequency (Hz)")
    axes[1].set_ylabel("Phase of UZ (degrees)")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(fontsize=8)
    axes[0].set_title("Harmonic response — route statuses retained")
    figure.savefig(path, dpi=160)
    plt.close(figure)
