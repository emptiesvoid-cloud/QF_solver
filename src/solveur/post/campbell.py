"""Plot/export projections for an already tracked :class:`CampbellResult`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from solveur.core.results import CampbellResult
from solveur.core.errors import InfrastructureError, InputValidationError


_PLOTABLE_STATUSES = {"CLEAR_MATCH", "UNTRACKED", "DEGENERATE_CLUSTER"}


def save_campbell_plot(
    result: CampbellResult,
    path: str | Path,
    *,
    show_one_x: bool = False,
    title: str = "Experimental Campbell diagram",
) -> Path:
    """Render stored branches without assigning, smoothing, or interpolating them."""

    if not isinstance(result, CampbellResult):
        raise InputValidationError("save_campbell_plot requires a CampbellResult.")
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise InfrastructureError("Campbell plotting requires the optional matplotlib dependency.") from exc

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    speeds = np.asarray(result.spin_speeds_rad_s, dtype=float)
    figure, axis = plt.subplots()
    for branch in result.branches:
        line_x: list[float] = []
        line_y: list[float] = []

        def flush() -> None:
            if line_x:
                axis.plot(line_x, line_y, marker="o", label=branch["branch_id"])
                line_x.clear()
                line_y.clear()

        for index, sample in enumerate(branch["samples"]):
            if sample is None or sample.get("ambiguity_status") not in _PLOTABLE_STATUSES:
                flush()
                continue
            frequencies = [float(value) for value in sample.get("frequencies_hz", [])]
            if len(frequencies) != 1:
                flush()
                if frequencies:
                    axis.scatter([speeds[index]] * len(frequencies), frequencies, marker="x", label=f"{branch['branch_id']} cluster")
                continue
            line_x.append(float(speeds[index]))
            line_y.append(frequencies[0])
        flush()

    if show_one_x:
        axis.plot(speeds, np.abs(speeds) / (2.0 * np.pi), linestyle="--", label="1x frequency coincidence")
    axis.set_xlabel("Spin speed (rad/s)")
    axis.set_ylabel("Frequency (Hz)")
    axis.set_title(title)
    axis.grid(True, alpha=0.25)
    handles, labels = axis.get_legend_handles_labels()
    if handles:
        axis.legend()
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    plt.close(figure)
    return destination


def campbell_rows(result: CampbellResult) -> list[dict[str, Any]]:
    """Flatten result samples for tabular export; ambiguous gaps remain explicit."""

    if not isinstance(result, CampbellResult):
        raise InputValidationError("campbell_rows requires a CampbellResult.")
    rows: list[dict[str, Any]] = []
    for branch in result.branches:
        for sample in branch["samples"]:
            if sample is None:
                continue
            for mode_position, frequency in enumerate(sample["frequencies_hz"]):
                rows.append(
                    {
                        "branch_id": branch["branch_id"],
                        "spin_speed_rad_s": sample["spin_speed_rad_s"],
                        "frequency_hz": frequency,
                        "ambiguity_status": sample["ambiguity_status"],
                        "source_mode_index": sample["source_mode_indices"][mode_position],
                        "qep_residual": sample["qep_residuals"][mode_position],
                        "complex_eigenvalue": sample["eigenvalues"][mode_position],
                    }
                )
    return rows
