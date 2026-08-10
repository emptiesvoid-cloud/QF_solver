"""Matplotlib visualization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection

from mitc4.constants import DOF_PER_NODE


@dataclass
class DeformationPlotter:
    scale: float = 1.0

    def plot(
        self,
        nodes: np.ndarray,
        quads: np.ndarray,
        U: np.ndarray,
        *,
        title: str,
        png: Path | None = None,
        show: bool = False,
    ) -> None:
        displacements = U.reshape((-1, DOF_PER_NODE))[:, :3]
        deformed = nodes + self.scale * displacements
        mag = np.linalg.norm(displacements, axis=1)
        mag_max = max(float(mag.max()), 1.0e-30)

        fig = plt.figure(figsize=(10.5, 7.0))
        ax = fig.add_subplot(111, projection="3d")
        cmap = plt.get_cmap("viridis")

        faces = [deformed[conn] for conn in quads]
        colors = [cmap(float(mag[conn].mean() / mag_max)) for conn in quads]
        collection = Poly3DCollection(faces, facecolors=colors, edgecolors="k", linewidths=0.25, alpha=0.95)
        ax.add_collection3d(collection)

        edges: set[tuple[int, int]] = set()
        for conn in quads:
            for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)):
                i = int(conn[a])
                j = int(conn[b])
                edges.add((min(i, j), max(i, j)))
        wire_segments = [[nodes[i], nodes[j]] for i, j in sorted(edges)]
        ax.add_collection3d(Line3DCollection(wire_segments, colors="0.65", linewidths=0.35, alpha=0.55))

        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0.0, vmax=mag_max))
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, shrink=0.62, pad=0.08)
        cbar.set_label("Displacement norm")

        all_pts = np.vstack((nodes, deformed))
        mins = all_pts.min(axis=0)
        maxs = all_pts.max(axis=0)
        center = 0.5 * (mins + maxs)
        radius = 0.55 * max(maxs - mins)
        if radius <= 0.0:
            radius = 1.0
        ax.set_xlim(center[0] - radius, center[0] + radius)
        ax.set_ylim(center[1] - radius, center[1] + radius)
        ax.set_zlim(center[2] - radius, center[2] + radius)
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        ax.set_title(title)
        ax.view_init(elev=24.0, azim=-58.0)
        fig.tight_layout()

        if png is not None:
            png.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(png, dpi=180)
        if show:
            plt.show()
        plt.close(fig)

