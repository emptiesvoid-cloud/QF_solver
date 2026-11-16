"""Render J5B's archived MITC4 mode shapes for a possible gallery asset.

This is a plotting-only utility. It reads an archived NPZ and does not run
QF Solver, assemble a model, or calculate a reference solution.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "research" / "j5c" / "inputs" / "j5b_attempt_0001" / "modal_shapes.npz"
ATTEMPT_RECORD = ROOT / "research" / "j5c" / "inputs" / "j5b_attempt_0001" / "attempt-0001.json"
OUTPUT_DIR = ROOT / "research" / "j5c" / "results" / "diagnostic-2026-11-16" / "gallery-assets"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render() -> Path:
    with np.load(ARCHIVE, allow_pickle=False) as saved:
        nodes = np.array(saved["nodes"], copy=True)
        quads = np.array(saved["quads"], copy=True)
        translations = np.array(saved["translations"], copy=True)
    attempt = json.loads(ATTEMPT_RECORD.read_text(encoding="utf-8"))
    x_levels = np.unique(nodes[:, 0])
    y_levels = np.unique(nodes[:, 1])
    if len(x_levels) * len(y_levels) != len(nodes) or quads.shape != (256, 4):
        raise ValueError("expected the archived structured 16x16 plate mesh")

    mode_grid = np.empty((4, len(y_levels), len(x_levels)), dtype=float)
    for node_id, (x_value, y_value) in enumerate(nodes[:, :2]):
        ix = int(np.argmin(np.abs(x_levels - x_value)))
        iy = int(np.argmin(np.abs(y_levels - y_value)))
        for mode in range(4):
            mode_grid[mode, iy, ix] = translations[node_id, 2, mode]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image_path = OUTPUT_DIR / "j5b_qf_candidate_mode_shapes.png"
    figure, axes = plt.subplots(2, 2, figsize=(10, 8), constrained_layout=True)
    mode_names = ("(1,1)", "(1,2)", "(2,1)", "(2,2)")
    for mode, axis in enumerate(axes.flat):
        field = mode_grid[mode]
        scale = max(float(np.max(np.abs(field))), np.finfo(float).tiny)
        contour = axis.contourf(
            x_levels,
            y_levels,
            field / scale,
            levels=np.linspace(-1.0, 1.0, 21),
            cmap="coolwarm",
            vmin=-1.0,
            vmax=1.0,
        )
        axis.set_aspect("equal")
        axis.set_xlabel("x (m)")
        axis.set_ylabel("y (m)")
        axis.set_title(f"Mode {mode + 1}: expected order {mode_names[mode]}")
        figure.colorbar(contour, ax=axis, shrink=0.84, label="Normalized UZ")
    figure.suptitle(
        "J5B MITC4 16×16 candidate modes\n"
        "Each vector is normalized independently; sign and repeated-pair basis are arbitrary",
        fontsize=12,
    )
    figure.savefig(image_path, dpi=170)
    plt.close(figure)

    script_path = Path(__file__)
    manifest = {
        "schema": "qf-j5c-gallery-plot-only-manifest-v1",
        "classification": "DEVELOPMENT_DIAGNOSTIC_ONLY",
        "attempt_id": "j5c-j5b-mode-gallery-plot-0001",
        "operation": "plot archived QF Solver UZ vectors only; no FEM, no external solver, no Ritz solve",
        "source_j5c_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_j5b_attempt_id": attempt["attempt_id"],
        "source_j5b_commit": attempt["source_commit"],
        "source_status_preserved": attempt["campaign_status"],
        "archive": {
            "path": ARCHIVE.relative_to(ROOT).as_posix(),
            "sha256": _sha256(ARCHIVE),
        },
        "plot_script": {
            "path": script_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(script_path),
        },
        "output": {
            "path": image_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(image_path),
            "bytes": image_path.stat().st_size,
        },
        "limits": [
            "Mode amplitudes are normalized for visualization, not physical forced response.",
            "The repeated (1,2)/(2,1) pair can rotate or swap; plotted vectors are one archived basis.",
            "This plot is a demonstration and does not validate modal frequencies or eigenpair residuals.",
        ],
    }
    (OUTPUT_DIR / "asset_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return image_path


if __name__ == "__main__":
    print(render().relative_to(ROOT).as_posix())
