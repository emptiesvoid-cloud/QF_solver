from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _median_range(values: list[float]) -> dict[str, float]:
    return {
        "min": float(min(values)),
        "median": float(np.median(values)),
        "max": float(max(values)),
    }


def _guard_row(record: dict[str, Any]) -> dict[str, Any]:
    details = record.get("qf_route_details", {}).get("diagnostics", {})
    required = (
        "residual_norm",
        "relative_residual",
        "matvec_roundoff_bound",
        "norm_relative_roundoff_factor",
        "relative_residual_upper_bound",
        "residual_failure_tolerance",
    )
    missing = [field for field in required if field not in details]
    if missing:
        raise ValueError(f"checkpoint is missing QF guard diagnostics: {missing}")
    residual = float(details["residual_norm"])
    relative = float(details["relative_residual"])
    roundoff = float(details["matvec_roundoff_bound"])
    reference_norm_estimate = residual / relative if relative > 0.0 else math.inf
    relative_roundoff_contribution = roundoff / reference_norm_estimate
    upper_bound = float(details["relative_residual_upper_bound"])
    raw_relative = float(record["diagnostic_reduced_relative_residual_l2"])
    raw_backward = float(record["diagnostic_reduced_backward_error_inf"])
    amplitude = float(record["diagnostic_center_uz_amplitude_mm"])
    condition = record.get("condition_number_2")
    return {
        "frequency_hz": float(record["frequency_hz"]),
        "frequency_role": record.get("frequency_role"),
        "qf_route_status": record["qf_route_status"],
        "qf_relative_residual_l2": relative,
        "qf_residual_norm": residual,
        "qf_matvec_roundoff_bound_norm": roundoff,
        "qf_roundoff_factor_for_norm": float(details["norm_relative_roundoff_factor"]),
        "qf_relative_upper_bound": upper_bound,
        "qf_limit": float(details["residual_failure_tolerance"]),
        "estimated_reference_norm_from_qf_residual": reference_norm_estimate,
        "approx_relative_matvec_roundoff_contribution": relative_roundoff_contribution,
        "upper_bound_to_relative_residual_ratio": upper_bound / relative if relative > 0.0 else None,
        "roundoff_share_of_upper_bound": max(0.0, upper_bound - relative) / upper_bound if upper_bound > 0.0 else None,
        "spsolve_relative_residual_l2": raw_relative,
        "spsolve_backward_error_eta_inf": raw_backward,
        "spsolve_center_uz_amplitude_mm": amplitude,
        "condition_number_2_if_sampled": float(condition) if condition is not None else None,
        "checkpoint_stage": record.get("checkpoint_stage"),
    }


def analyze_archived_guard(
    checkpoint_dir: Path,
    input_manifest_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Reconcile stored J15 guard diagnostics without assembling or solving."""
    input_manifest = json.loads(input_manifest_path.read_text(encoding="utf-8"))
    if input_manifest.get("frequency_artifact_count") != len(input_manifest.get("frequency_artifacts", [])):
        raise ValueError("J15 input manifest frequency_artifact_count does not match its inventory")
    verified = 0
    for artifact in input_manifest["frequency_artifacts"]:
        path = checkpoint_dir / artifact["path"]
        if not path.is_file() or _sha256(path) != artifact["sha256_raw"]:
            raise ValueError(f"J15 checkpoint hash mismatch: {artifact['path']}")
        verified += 1

    json_paths = sorted(checkpoint_dir.glob("frequency_*.json"))
    rows: list[dict[str, Any]] = []
    for json_path in json_paths:
        record = json.loads(json_path.read_text(encoding="utf-8"))
        rows.append(_guard_row(record))
    if len(rows) != 152:
        raise ValueError(f"Expected 152 J15 frequency checkpoints, found {len(rows)}")
    rows.sort(key=lambda row: row["frequency_hz"])

    statuses = Counter(row["qf_route_status"] for row in rows)
    if statuses != Counter({"QF_GUARD_REJECTED": 152}):
        raise ValueError(f"Unexpected J15 QF route statuses: {dict(statuses)}")
    qf_relative = [row["qf_relative_residual_l2"] for row in rows]
    upper_bounds = [row["qf_relative_upper_bound"] for row in rows]
    raw_relative = [row["spsolve_relative_residual_l2"] for row in rows]
    backward = [row["spsolve_backward_error_eta_inf"] for row in rows]
    amplitudes = [row["spsolve_center_uz_amplitude_mm"] for row in rows]
    roundoff_contrib = [row["approx_relative_matvec_roundoff_contribution"] for row in rows]
    bound_ratio = [float(row["upper_bound_to_relative_residual_ratio"]) for row in rows]
    correlation = float(np.corrcoef(upper_bounds, amplitudes)[0, 1])

    output_dir.mkdir(parents=True, exist_ok=False)
    csv_path = output_dir / "guard_frequency_diagnostics.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    figure, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True, constrained_layout=True)
    frequency = np.asarray([row["frequency_hz"] for row in rows], dtype=float)
    axes[0].semilogy(frequency, upper_bounds, color="#b23a48", label="QF upper bound")
    axes[0].semilogy(frequency, qf_relative, color="#176b87", label="QF computed relative residual")
    axes[0].axhline(float(rows[0]["qf_limit"]), color="#666666", linestyle="--", label="unchanged limit 1e-7")
    axes[0].set_ylabel("Relative residual metric")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend()
    axes[1].plot(frequency, amplitudes, color="#b23a48", label="spsolve raw |UZ| (unaccepted)")
    axes[1].set_ylabel("Center |UZ| (mm)")
    axes[1].set_xlabel("Frequency (Hz)")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend()
    axes[0].set_title("J15 archived guard bound and raw diagnostic response; all points remain rejected")
    figure_path = output_dir / "guard_bound_vs_frequency.png"
    figure.savefig(figure_path, dpi=160)
    plt.close(figure)

    condition_points = [
        {
            "frequency_hz": row["frequency_hz"],
            "condition_number_2": row["condition_number_2_if_sampled"],
        }
        for row in rows
        if row["condition_number_2_if_sampled"] is not None
    ]
    summary = {
        "schema": "qfsolver-j16-j15-guard-analysis-v1",
        "classification": "ARCHIVED_CHECKPOINT_ANALYSIS_NO_ASSEMBLY_OR_SOLVER_CALL",
        "source_attempt_id": "J15-NAFEMS13H-RES-001",
        "source_run_status": "PYTEST_FAILED",
        "checkpoint_count": len(rows),
        "verified_frequency_artifact_hash_count": verified,
        "qf_route_status_counts": dict(sorted(statuses.items())),
        "qf_relative_residual_l2": _median_range(qf_relative),
        "qf_relative_upper_bound": _median_range(upper_bounds),
        "approx_relative_matvec_roundoff_contribution": _median_range(roundoff_contrib),
        "upper_bound_to_relative_residual_ratio": _median_range(bound_ratio),
        "spsolve_relative_residual_l2": _median_range(raw_relative),
        "spsolve_backward_error_eta_inf": _median_range(backward),
        "spsolve_diagnostic_amplitude_mm": _median_range(amplitudes),
        "pearson_correlation_upper_bound_vs_raw_amplitude": correlation,
        "condition_number_sample_count": len(condition_points),
        "condition_number_sample_points": condition_points,
        "roundoff_formula_interpretation": (
            "The guard adds a sparse-matvec/subtraction roundoff norm to the computed residual norm, "
            "then divides an outward-rounded numerator by a downward-rounded lower bound on "
            "max(||b||2, ||Ax||2). The recorded relative_residual is only the computed residual ratio. "
            "The backward error in the raw spsolve checkpoint uses an infinity-norm denominator and "
            "is not the same quantity."
        ),
        "observed_reconstruction_limit": (
            "The checkpoints do not contain the assembled impedance matrices. This analysis verifies "
            "the archived roundoff-bound diagnostics and their frequency trend; it does not independently "
            "recompute the matrix product or the guard from the matrix."
        ),
    }
    summary_path = output_dir / "guard_analysis_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    artifacts = []
    for path in (csv_path, figure_path, summary_path):
        artifacts.append({"path": path.name, "bytes": path.stat().st_size, "sha256_raw": _sha256(path)})
    manifest = {
        "schema": "qfsolver-j16-guard-analysis-output-manifest-v1",
        "input_manifest_sha256_raw": _sha256(input_manifest_path),
        "verified_frequency_artifact_count": verified,
        "artifacts": artifacts,
    }
    (output_dir / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(analyze_archived_guard(args.checkpoint_dir, args.input_manifest, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
