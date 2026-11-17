"""Prepare corrected, reproducible J17 figures from archived diagnostics.

This script only reads archived response data and post-processed residuals. It
does not assemble or solve a finite-element model.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "research/j17/results/archived_exact_recheck_002"
OUTPUT = ROOT / "research/j17/site_assets/archived_residual_check_002"
CSV_NAME = "exact_residual_points.csv"
SUMMARY_NAME = "exact_residual_summary.json"
IMAGE_NAME = "exact_residual_vs_guard_bound_175x175.png"
TOLERANCE = 1.0e-7


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_rows() -> tuple[list[dict[str, str]], dict[str, Any]]:
    with (RESULTS / CSV_NAME).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    summary = json.loads((RESULTS / SUMMARY_NAME).read_text(encoding="utf-8"))
    if len(rows) != 15 or summary.get("record_count") != 15:
        raise ValueError("expected the frozen 15-row J17 archive comparison")
    if any(row.get("historical_qf_route_status") != "QF_GUARD_REJECTED" for row in rows):
        raise ValueError("historical J16 route statuses do not match the expected archive")
    return rows, summary


def _plot(rows: list[dict[str, str]]) -> None:
    colors = {
        "spsolve_unscaled": "#176b87",
        "spsolve_row_column_equilibrated": "#b05d21",
        "splu_two_refinements": "#4b8b3b",
    }
    fig, axis = plt.subplots(figsize=(10, 6), constrained_layout=True)
    for variant, color in colors.items():
        selected = sorted(
            (row for row in rows if row["variant"] == variant),
            key=lambda row: float(row["frequency_hz"]),
        )
        frequencies = [float(row["frequency_hz"]) for row in selected]
        exact = [float(row["relative_residual_l2_display_only"]) for row in selected]
        bound = [float(row["qf_relative_upper_bound_recomputed"]) for row in selected]
        axis.semilogy(frequencies, exact, marker="o", color=color, label=f"{variant}: exact represented residual")
        axis.semilogy(
            frequencies,
            bound,
            marker="x",
            linestyle="--",
            color=color,
            alpha=0.75,
            label=f"{variant}: current-guard upper bound",
        )
    axis.axhline(TOLERANCE, color="#333333", linestyle=":", label="unchanged tolerance 1e-7")
    axis.set_xlabel("Frequency (Hz)")
    axis.set_ylabel("Relative residual")
    axis.set_title("J17: exact represented residual vs current-guard bound (175×175)")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend(fontsize=8, ncol=2)
    fig.text(
        0.5,
        -0.025,
        "Exact status concerns stored binary arrays only; all historical QF route points remain rejected.",
        ha="center",
        fontsize=9,
    )
    fig.savefig(OUTPUT / IMAGE_NAME, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _write_manifest(summary: dict[str, Any]) -> None:
    paths = [OUTPUT / CSV_NAME, OUTPUT / SUMMARY_NAME, OUTPUT / IMAGE_NAME, OUTPUT / "README.md"]
    source_manifest = json.loads((RESULTS / "artifact_manifest.json").read_text(encoding="utf-8"))
    source_entries = {item["path"]: item for item in source_manifest["artifacts"]}
    for source_name in (CSV_NAME, SUMMARY_NAME):
        item = source_entries.get(source_name)
        if item is None or _sha256(RESULTS / source_name) != item["sha256"]:
            raise ValueError(f"archived source output failed manifest validation: {source_name}")
    manifest = {
        "schema": "qfsolver-j17-gallery-assets-v1",
        "source_contract_sha256": source_manifest.get("contract_sha256"),
        "source_execution_commit": summary.get("source_git_commit"),
        "source_csv_sha256": _sha256(RESULTS / CSV_NAME),
        "source_summary_sha256": _sha256(RESULTS / SUMMARY_NAME),
        "artifacts": [
            {"path": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in paths
        ],
        "classification": "UNPUBLISHED_DIAGNOSTIC_ASSETS",
    }
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    site_root = ROOT / "research/j17/site_assets"
    site_files = sorted(
        path for path in site_root.rglob("*")
        if path.is_file() and path.name != "artifact_manifest.json"
    )
    site_manifest = {
        "schema": "qfsolver-j17-site-assets-manifest-v1",
        "classification": "UNPUBLISHED_DIAGNOSTIC_ASSETS",
        "artifacts": [
            {
                "path": path.relative_to(site_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in site_files
        ],
    }
    (site_root / "artifact_manifest.json").write_text(
        json.dumps(site_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows, summary = _load_rows()
    shutil.copyfile(RESULTS / CSV_NAME, OUTPUT / CSV_NAME)
    shutil.copyfile(RESULTS / SUMMARY_NAME, OUTPUT / SUMMARY_NAME)
    _plot(rows)
    _write_manifest(summary)


if __name__ == "__main__":
    main()
