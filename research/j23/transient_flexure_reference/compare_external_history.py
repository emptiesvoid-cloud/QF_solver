"""Compare an Abaqus ODB export with archived QF histories at common times."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_rows(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"no rows in {path}")
    columns = rows[0].keys()
    return {name: np.asarray([float(row[name]) for row in rows], dtype=np.float64) for name in columns}


def compare_histories(
    qf_csv: Path,
    external_csv: Path,
    output_json: Path,
    output_plot: Path,
    qf_reactions_csv: Path | None = None,
) -> dict[str, Any]:
    qf = read_rows(qf_csv)
    external = read_rows(external_csv)
    qf_t = qf["time_s"]
    ext_t = external["time_s"]
    start = max(float(qf_t[0]), float(ext_t[0]))
    end = min(float(qf_t[-1]), float(ext_t[-1]))
    common_mask = (qf_t >= start) & (qf_t <= end)
    common_t = qf_t[common_mask]
    if len(common_t) < 2:
        raise ValueError("fewer than two shared physical-time samples")

    metrics: dict[str, Any] = {
        "status": "DESCRIPTIVE_EXTERNAL_COMPARISON",
        "sample_count": int(len(common_t)),
        "common_time_interval_s": [start, end],
        "external_interpolation": "linear interpolation from exported Abaqus field times onto the archived QF time grid; no extrapolation",
        "normalization": "RMS and maximum absolute displacement differences divided by the QF peak absolute displacement at the same probe over the common interval; no pointwise division near zero.",
        "probes": {},
    }
    figure, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True, constrained_layout=True)
    for axis, probe in zip(axes, ("midspan", "tip")):
        qf_values = qf[f"qf_{probe}_uz_m"][common_mask]
        ext_values = np.interp(common_t, ext_t, external[f"{probe}_uz_m"])
        difference = ext_values - qf_values
        denominator = float(np.max(np.abs(qf_values)))
        if denominator == 0.0:
            raise ValueError(f"QF displacement peak is zero at {probe}; normalized error is undefined")
        qf_peak_index = int(np.argmax(np.abs(qf_values)))
        ext_peak_index = int(np.argmax(np.abs(ext_values)))
        metrics["probes"][probe] = {
            "qf_peak_abs_m": denominator,
            "qf_peak_time_s": float(common_t[qf_peak_index]),
            "external_peak_abs_m": float(np.max(np.abs(ext_values))),
            "external_peak_time_s": float(common_t[ext_peak_index]),
            "rms_abs_difference_m": float(np.sqrt(np.mean(difference**2))),
            "max_abs_difference_m": float(np.max(np.abs(difference))),
            "rms_difference_normalized_to_qf_peak": float(np.sqrt(np.mean(difference**2)) / denominator),
            "max_difference_normalized_to_qf_peak": float(np.max(np.abs(difference)) / denominator),
            "peak_time_difference_s": float(common_t[ext_peak_index] - common_t[qf_peak_index]),
        }
        axis.plot(common_t * 1e3, qf_values * 1e3, label="QF TET10")
        axis.plot(common_t * 1e3, ext_values * 1e3, linestyle="--", label="Abaqus C3D10")
        axis.set_ylabel(f"{probe.capitalize()} $U_z$ (mm)")
        axis.grid(True, alpha=0.3)
        axis.legend(loc="best")
    axes[-1].set_xlabel("Physical time (ms)")
    figure.suptitle("J23 external comparison — descriptive, same archived mesh and nodal load")
    figure.savefig(output_plot, dpi=160)
    plt.close(figure)

    if qf_reactions_csv is not None:
        qf_reactions = read_rows(qf_reactions_csv)
        raw_reaction_times = qf_reactions["time_s"]
        repeated_time_mask = np.concatenate(([False], np.diff(raw_reaction_times) == 0.0))
        for duplicate_index in np.flatnonzero(repeated_time_mask):
            for name, values in qf_reactions.items():
                if float(values[duplicate_index]) != float(values[duplicate_index - 1]):
                    raise ValueError("duplicate QF reaction checkpoint time has differing values")
        unique_mask = np.concatenate(([True], np.diff(raw_reaction_times) != 0.0))
        qf_reactions = {name: values[unique_mask] for name, values in qf_reactions.items()}
        reaction_mask = (qf_reactions["time_s"] >= start) & (qf_reactions["time_s"] <= end)
        reaction_times = qf_reactions["time_s"][reaction_mask]
        if len(reaction_times) < 2:
            raise ValueError("fewer than two shared archived reaction checkpoints")
        reaction_metrics: dict[str, Any] = {
            "sample_count": int(len(reaction_times)),
            "checkpoint_stride_s": 0.0008,
            "external_interpolation": "linear interpolation onto the 0.8 ms archived QF checkpoint times",
            "force_normalization": "maximum Euclidean norm of the archived QF support reaction vector over the common interval",
            "moment_normalization": "maximum Euclidean norm of the archived QF support reaction moment vector over the common interval",
            "components": {},
        }
        for label, qf_columns, ext_columns in (
            ("force", ("qf_reaction_fx_n", "qf_reaction_fy_n", "qf_reaction_fz_n"), ("reaction_fx_n", "reaction_fy_n", "reaction_fz_n")),
            ("moment", ("qf_reaction_mx_nm", "qf_reaction_my_nm", "qf_reaction_mz_nm"), ("reaction_mx_nm", "reaction_my_nm", "reaction_mz_nm")),
        ):
            qf_vector = np.column_stack([qf_reactions[column][reaction_mask] for column in qf_columns])
            ext_vector = np.column_stack([np.interp(reaction_times, ext_t, external[column]) for column in ext_columns])
            vector_difference = ext_vector - qf_vector
            qf_norm = np.linalg.norm(qf_vector, axis=1)
            error_norm = np.linalg.norm(vector_difference, axis=1)
            scale = float(np.max(qf_norm))
            if scale == 0.0:
                raise ValueError(f"QF support reaction {label} scale is zero; normalized difference is undefined")
            reaction_metrics["components"][label] = {
                "qf_peak_vector_norm": scale,
                "rms_vector_difference": float(np.sqrt(np.mean(error_norm**2))),
                "max_vector_difference": float(np.max(error_norm)),
                "rms_difference_normalized_to_qf_peak": float(np.sqrt(np.mean(error_norm**2)) / scale),
                "max_difference_normalized_to_qf_peak": float(np.max(error_norm) / scale),
            }
        metrics["support_reactions"] = reaction_metrics
    output_json.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qf-csv", type=Path, default=Path("site_assets/qf_euler_bernoulli_probe_histories.csv"))
    parser.add_argument("--external-csv", type=Path, default=Path("abaqus_history.csv"))
    parser.add_argument("--qf-reactions-csv", type=Path, default=Path("site_assets/qf_support_reaction_checkpoints.csv"))
    parser.add_argument("--output-json", type=Path, default=Path("site_assets/qf_abaqus_comparison_metrics.json"))
    parser.add_argument("--output-plot", type=Path, default=Path("site_assets/qf_abaqus_history_comparison.png"))
    args = parser.parse_args()
    print(json.dumps(compare_histories(args.qf_csv, args.external_csv, args.output_json, args.output_plot, args.qf_reactions_csv), indent=2))


if __name__ == "__main__":
    main()
