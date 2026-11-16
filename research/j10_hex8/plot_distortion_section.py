"""Render a readable X-Z section from the archived J10 HEX8 geometry states.

This is a plotting-only postprocessor. It does not assemble or solve a FEM model.
The plotted z coordinate is visually enlarged by a fixed, disclosed factor.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
import numpy as np
from matplotlib.ticker import FuncFormatter

matplotlib.use("Agg")
from matplotlib import pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
RESULT_DIR = ROOT / "research/j10/results/diagnostic-2026-11-16/hex8_j7_distortion"
STATE_PATH = RESULT_DIR / "hex8_j7_distortion_states.npz"
RESULT_PATH = RESULT_DIR / "result.json"
OUTPUT_PATH = RESULT_DIR / "site_hex8_j7_geometry_section.png"
MANIFEST_PATH = RESULT_DIR / "geometry_section_postprocess.json"
Z_DISPLAY_SCALE = 200.0
MID_Y_M = 0.5


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _section_faces(connectivity: np.ndarray, coordinates: np.ndarray) -> list[np.ndarray]:
    faces: dict[tuple[int, ...], np.ndarray] = {}
    for cell in connectivity:
        nodes = cell[np.isclose(coordinates[cell, 1], MID_Y_M, rtol=0.0, atol=1.0e-12)]
        if nodes.size != 4:
            continue
        center = coordinates[nodes][:, (0, 2)].mean(axis=0)
        points = coordinates[nodes][:, (0, 2)]
        order = np.argsort(np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0]))
        ordered = nodes[order]
        faces[tuple(sorted(int(node) for node in ordered))] = ordered
    return list(faces.values())


def create_figure() -> dict[str, object]:
    if not STATE_PATH.is_file() or not RESULT_PATH.is_file():
        raise FileNotFoundError("The archived J10 HEX8 result and state NPZ are required.")

    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    state_hash = result["state_npz"]["sha256"]
    if _sha256(STATE_PATH) != state_hash:
        raise ValueError("The archived state NPZ does not match the J10 result digest.")

    with np.load(STATE_PATH, allow_pickle=False) as state:
        connectivity = np.asarray(state["connectivity_hex8"], dtype=np.int64)
        geometries = [np.asarray(state[f"coordinates_alpha_{i}"], dtype=np.float64) for i in range(4)]

    if connectivity.ndim != 2 or connectivity.shape[1] != 8 or any(points.shape != (45, 3) for points in geometries):
        raise ValueError("Unexpected HEX8 geometry state shape; expected 16 HEX8 cells and 45 nodes.")
    alphas = [float(level["alpha"]) for level in result["levels"]]
    if len(alphas) != 4:
        raise ValueError("The archived diagnostic must contain exactly four geometry levels.")

    reference = geometries[0]
    faces = _section_faces(connectivity, reference)
    if not faces:
        raise ValueError("No HEX8 faces were found on the y=0.5 m section.")

    colors = ("#2166ac", "#1b9e77", "#d95f02", "#7570b3")
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharex=True, sharey=True)
    axes_flat = axes.ravel()
    for index, (ax, points, alpha) in enumerate(zip(axes_flat, geometries, alphas, strict=True)):
        for face in faces:
            polygon = np.concatenate((face, face[:1]))
            base_xz = reference[polygon][:, (0, 2)]
            current_xz = points[polygon][:, (0, 2)]
            if index:
                ax.plot(
                    base_xz[:, 0],
                    base_xz[:, 1] * Z_DISPLAY_SCALE,
                    color="#aaaaaa",
                    linewidth=0.7,
                    linestyle="--",
                    zorder=1,
                )
            ax.plot(
                current_xz[:, 0],
                current_xz[:, 1] * Z_DISPLAY_SCALE,
                color=colors[index],
                linewidth=1.15,
                zorder=2,
            )

        moved = np.flatnonzero(np.abs(points[:, 2] - reference[:, 2]) > 1.0e-12)
        if moved.size:
            ax.scatter(
                points[moved, 0],
                points[moved, 2] * Z_DISPLAY_SCALE,
                color="#c51b29",
                s=19,
                zorder=4,
                label="nœuds intérieurs déplacés",
            )

        z_display = points[:, 2] * Z_DISPLAY_SCALE
        z_center = float(np.mean(z_display))
        ax.annotate(
            "",
            xy=(19.55, z_center - 2.2),
            xytext=(19.55, z_center + 0.6),
            arrowprops={"arrowstyle": "-|>", "color": "#111111", "lw": 1.3},
            zorder=5,
        )
        ax.text(18.75, z_center + 1.15, "résultante −1 N en z", fontsize=8, ha="center")
        ax.axvline(0.0, color="#111111", linewidth=2.0, zorder=3)
        ax.set_title(f"α = {alpha:.2f}" + (" — référence" if index == 0 else ""))
        ax.set_xlim(-0.25, 20.1)
        ax.set_ylim(float(np.min(reference[:, 2]) * Z_DISPLAY_SCALE - 1.0), float(np.max(reference[:, 2]) * Z_DISPLAY_SCALE + 1.0))
        ax.grid(True, color="#dddddd", linewidth=0.55)
        ax.set_aspect("equal", adjustable="box")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _position: f"{value / Z_DISPLAY_SCALE:.3f}"))
        if index:
            ax.plot([], [], color="#aaaaaa", linestyle="--", label="géométrie α=0")
        if moved.size:
            ax.legend(loc="upper right", fontsize=7, framealpha=0.9)

    for ax in axes_flat[2:]:
        ax.set_xlabel("x [m]")
    for ax in axes_flat[::2]:
        ax.set_ylabel("z physique [m] (affichage ×200)")
    fig.suptitle(
        "HEX8-SRI J7 — coupe x–z à y=0,5 m\n"
        "géométrie du maillage, sans déformée mécanique; appui x=0 et résultante appliquée à x=20 m",
        y=0.99,
    )
    fig.tight_layout(rect=(0.02, 0.03, 0.99, 0.91))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=180, bbox_inches="tight")
    plt.close(fig)

    manifest = {
        "schema": "qf-j10-geometry-section-postprocess-v1",
        "classification": "PLOTTING_ONLY_NO_FEM",
        "input_state_npz": STATE_PATH.name,
        "input_state_npz_sha256": state_hash,
        "input_result_sha256": _sha256(RESULT_PATH),
        "postprocessor": "research/j10_hex8/plot_distortion_section.py",
        "postprocessor_sha256": _sha256(Path(__file__).resolve()),
        "output_figure": OUTPUT_PATH.name,
        "output_figure_sha256": _sha256(OUTPUT_PATH),
        "section_y_m": MID_Y_M,
        "vertical_display_scale": Z_DISPLAY_SCALE,
        "interpretation": "Geometry-only x-z section. The z-axis display is enlarged 200x; tick labels remain physical metres. The arrows show only the applied resultant, not elementwise pressure.",
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return manifest


if __name__ == "__main__":
    print(json.dumps(create_figure(), indent=2, ensure_ascii=False))
