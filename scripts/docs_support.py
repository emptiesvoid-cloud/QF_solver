"""Deterministic geometry, table and plotting helpers for documentation evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection  # noqa: E402


TRANSLATION_DOFS = ("UX", "UY", "UZ")
TET_FACES = ((0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3))


def tetra_boundary_faces(connectivities: Iterable[Sequence[int]]) -> np.ndarray:
    """Return exterior corner faces from TET4 or TET10 connectivities."""
    occurrences: dict[tuple[int, int, int], tuple[int, int, int] | None] = {}
    counts: dict[tuple[int, int, int], int] = {}
    for connectivity in connectivities:
        corners = tuple(int(value) for value in connectivity[:4])
        if len(corners) != 4:
            raise ValueError("A tetrahedral connectivity must expose four corner nodes.")
        for local_face in TET_FACES:
            oriented = tuple(corners[index] for index in local_face)
            key = tuple(sorted(oriented))
            counts[key] = counts.get(key, 0) + 1
            occurrences[key] = oriented
    return np.asarray(
        [occurrences[key] for key in sorted(counts) if counts[key] == 1],
        dtype=int,
    ).reshape((-1, 3))


def automatic_deformation_scale(
    nodes: np.ndarray,
    translations: np.ndarray,
    *,
    target_fraction: float = 0.18,
) -> float:
    """Scale the largest displacement to a fixed fraction of model size."""
    coordinates = np.asarray(nodes, dtype=float)
    displacement = np.asarray(translations, dtype=float)
    if coordinates.shape != displacement.shape or coordinates.ndim != 2 or coordinates.shape[1] != 3:
        raise ValueError("nodes and translations must both have shape (n, 3).")
    if not 0.0 < target_fraction <= 1.0:
        raise ValueError("target_fraction must be in (0, 1].")
    span = np.ptp(coordinates, axis=0)
    model_size = float(np.linalg.norm(span))
    maximum = float(np.max(np.linalg.norm(displacement, axis=1))) if displacement.size else 0.0
    if model_size <= 1.0e-30 or maximum <= 1.0e-30:
        return 1.0
    return target_fraction * model_size / maximum


def nodal_translations(model: object, result: object, vector: np.ndarray | None = None) -> np.ndarray:
    """Map a compact solver vector to one translation triplet per model node."""
    values = np.asarray(vector if vector is not None else getattr(result, "displacements"), dtype=float)
    dofs = getattr(result, "dofs")
    node_count = int(getattr(model, "node_count"))
    translations = np.zeros((node_count, 3), dtype=float)
    for node in range(node_count):
        for component, name in enumerate(TRANSLATION_DOFS):
            if dofs.has(node, name):
                translations[node, component] = values[dofs.index(node, name)]
    return translations


def plot_deformed_model(
    model: object,
    result: object,
    output: str | Path,
    *,
    title: str,
    vector: np.ndarray | None = None,
    color_label: str = "Norme du deplacement [m]",
) -> float:
    """Render original/deformed shell or tetrahedral geometry and return the scale."""
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    nodes = np.asarray(getattr(model, "nodes"), dtype=float)
    translations = nodal_translations(model, result, vector)
    scale = automatic_deformation_scale(nodes, translations)
    deformed = nodes + scale * translations
    magnitude = np.linalg.norm(translations, axis=1)
    maximum = max(float(np.max(magnitude)), 1.0e-30)
    elements = list(getattr(model, "elements"))
    tetra = [element.nodes for element in elements if str(element.type).upper() in {"TET4", "TET10"}]
    quads = [element.nodes for element in elements if str(element.type).upper() == "MITC4"]

    fig = plt.figure(figsize=(9.4, 6.3))
    ax = fig.add_subplot(111, projection="3d")
    # Cividis remains distinguishable for the most common colour-vision deficits.
    cmap = plt.get_cmap("cividis")
    faces: list[np.ndarray] = []
    face_values: list[float] = []
    if tetra:
        boundary = tetra_boundary_faces(tetra)
        faces.extend(deformed[face] for face in boundary)
        face_values.extend(float(np.mean(magnitude[face])) for face in boundary)
    for quad in quads:
        connectivity = np.asarray(quad, dtype=int)
        faces.append(deformed[connectivity])
        face_values.append(float(np.mean(magnitude[connectivity])))
    if faces:
        colors = [cmap(value / maximum) for value in face_values]
        collection = Poly3DCollection(
            faces,
            facecolors=colors,
            edgecolors="#263238",
            linewidths=0.55,
            alpha=0.93,
        )
        ax.add_collection3d(collection)

    edges = _unique_edges(elements)
    if edges:
        original_segments = [[nodes[a], nodes[b]] for a, b in edges]
        ax.add_collection3d(
            Line3DCollection(original_segments, colors="#7f8c8d", linewidths=0.8, alpha=0.75, linestyles="dashed")
        )

    fixed_nodes = sorted({int(condition.node) for condition in getattr(model, "fixed_dofs", [])})
    if fixed_nodes:
        fixed = nodes[np.asarray(fixed_nodes, dtype=int)]
        ax.scatter(fixed[:, 0], fixed[:, 1], fixed[:, 2], marker="s", s=24, color="#1f2933", label="Noeud bloque")
    _plot_load_arrows(ax, model, nodes)

    if any(str(element.type).upper() == "TET10" for element in elements):
        ax.scatter(
            deformed[:, 0],
            deformed[:, 1],
            deformed[:, 2],
            s=8,
            facecolors="white",
            edgecolors="#111111",
            linewidths=0.45,
            alpha=0.9,
        )

    scalar = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0.0, vmax=maximum))
    scalar.set_array([])
    colorbar = fig.colorbar(scalar, ax=ax, shrink=0.64, pad=0.08)
    colorbar.set_label(color_label)
    _set_equal_axes(ax, np.vstack((nodes, deformed)))
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.set_zlabel("Z [m]")
    ax.set_title(f"{title}\nFacteur d'amplification = {scale:.3g}")
    ax.view_init(elev=25.0, azim=-56.0)
    if fixed_nodes or getattr(model, "loads", []):
        ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(target, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return float(scale)


def plot_link_model(
    model: object,
    result: object,
    output: str | Path,
    *,
    title: str,
    vector: np.ndarray | None = None,
) -> float:
    """Render original and deformed beam, spring or rigid-link geometry."""
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    nodes = np.asarray(getattr(model, "nodes"), dtype=float)
    translations = nodal_translations(model, result, vector)
    scale = automatic_deformation_scale(nodes, translations)
    if len(nodes) == 1:
        maximum = max(float(np.linalg.norm(translations[0])), 1.0e-30)
        scale = 0.35 / maximum
    deformed = nodes + scale * translations
    links: list[tuple[int, int, str]] = []
    for element in getattr(model, "elements", []):
        if str(element.type).upper() == "BEAM2":
            links.append((int(element.nodes[0]), int(element.nodes[1]), "BEAM2"))
    for relation in getattr(model, "rbe2", []):
        links.extend((int(relation.master), int(slave), "RBE2") for slave in relation.slaves)
    for spring in getattr(model, "springs", []):
        if spring.node_b is not None:
            links.append((int(spring.node_a), int(spring.node_b), "ressort"))

    fig = plt.figure(figsize=(9.0, 5.8))
    ax = fig.add_subplot(111, projection="3d")
    for first, second, label in links:
        original = nodes[[first, second]]
        displaced = deformed[[first, second]]
        ax.plot(*original.T, color="#7f8c8d", linestyle="--", linewidth=1.1)
        ax.plot(*displaced.T, color="#155e75", linewidth=2.2, label=label)
    if len(nodes) == 1:
        anchor = nodes[0] - np.asarray([0.45, 0.0, 0.0])
        ax.plot(*np.vstack((anchor, nodes[0])).T, color="#7f8c8d", linestyle="--")
        ax.plot(*np.vstack((anchor, deformed[0])).T, color="#155e75", linewidth=2.2, label="ressort")
        points = np.vstack((anchor, nodes, deformed))
    else:
        points = np.vstack((nodes, deformed))
    ax.scatter(*nodes.T, color="#7f8c8d", s=26, label="initial")
    ax.scatter(*deformed.T, color="#b94b22", s=42, label="deforme")
    _plot_load_arrows(ax, model, nodes)
    _set_equal_axes(ax, points)
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.set_zlabel("Z [m]")
    ax.set_title(f"{title}\nFacteur d'amplification = {scale:.3g}")
    handles, labels = ax.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    ax.legend(unique.values(), unique.keys(), fontsize=8, loc="upper left")
    ax.view_init(elev=24.0, azim=-56.0)
    fig.tight_layout()
    fig.savefig(target, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return float(scale)


def plot_line_series(
    output: str | Path,
    series: Sequence[dict[str, Any]],
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    yscale: str = "linear",
) -> None:
    """Render deterministic line series for residual/convergence plots."""
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    markers = ("o", "s", "^", "D", "v", "P")
    for index, item in enumerate(series):
        ax.plot(
            np.asarray(item["x"], dtype=float),
            np.asarray(item["y"], dtype=float),
            marker=markers[index % len(markers)],
            markersize=4,
            linewidth=1.5,
            label=str(item["label"]),
        )
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_yscale(yscale)
    ax.grid(True, which="both", color="#d5dadd", linewidth=0.6)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(target, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_log_categories(
    output: str | Path,
    labels: Sequence[str],
    values: Sequence[float],
    *,
    title: str,
    ylabel: str,
) -> None:
    """Render positive categorical values on a colour-safe logarithmic axis."""
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    observed = np.maximum(np.asarray(values, dtype=float), 1.0e-30)
    positions = np.arange(len(labels), dtype=float)
    cmap = plt.get_cmap("cividis")
    colours = cmap(np.linspace(0.12, 0.88, max(len(labels), 2)))[: len(labels)]
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    ax.scatter(positions, observed, c=colours, s=72, edgecolors="#111111", linewidths=0.65, zorder=3)
    for position, value in zip(positions, observed):
        ax.annotate(
            f"{value:.2e}",
            (position, value),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=8,
        )
    ax.set_xticks(positions, labels)
    ax.set_yscale("log")
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Methode")
    ax.set_title(title)
    ax.grid(True, which="both", axis="y", color="#d5dadd", linewidth=0.6)
    fig.tight_layout()
    fig.savefig(target, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_dual_axis(
    output: str | Path,
    x: Sequence[float],
    left: Sequence[float],
    right: Sequence[float],
    *,
    title: str,
    xlabel: str,
    left_label: str,
    right_label: str,
) -> None:
    """Render two related histories without normalizing away their units."""
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig, left_axis = plt.subplots(figsize=(9.2, 5.4))
    right_axis = left_axis.twinx()
    line_left = left_axis.plot(x, left, color="#155e75", linewidth=1.7, label=left_label)
    line_right = right_axis.plot(x, right, color="#b94b22", linewidth=1.5, label=right_label)
    left_axis.set_xlabel(xlabel)
    left_axis.set_ylabel(left_label, color="#155e75")
    right_axis.set_ylabel(right_label, color="#b94b22")
    left_axis.grid(True, color="#d5dadd", linewidth=0.6)
    left_axis.legend(line_left + line_right, [left_label, right_label], fontsize=8, loc="best")
    left_axis.set_title(title)
    fig.tight_layout()
    fig.savefig(target, dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_markdown_table(path: str | Path, headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> None:
    """Write a compact deterministic Markdown table."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(markdown_value(value) for value in row) + " |" for row in rows)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def markdown_value(value: Any) -> str:
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, float):
        if value == 0.0:
            return "0"
        if abs(value) >= 1.0e4 or abs(value) < 1.0e-3:
            return f"{value:.6e}"
        return f"{value:.6g}"
    if value is None:
        return "non disponible"
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def plot_tetra_formulation(output: str | Path, *, quadratic: bool) -> None:
    """Draw an annotated TET4 or TET10 geometry as an offline SVG."""
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    corners = np.asarray([[0.0, 0.0, 0.0], [1.25, 0.0, 0.0], [0.18, 1.0, 0.0], [0.28, 0.30, 1.05]])
    edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
    fig = plt.figure(figsize=(8.8, 5.8))
    ax = fig.add_subplot(111, projection="3d")
    ax.add_collection3d(Line3DCollection([[corners[a], corners[b]] for a, b in edges], colors="#155e75", linewidths=2.0))
    ax.scatter(corners[:, 0], corners[:, 1], corners[:, 2], color="#b94b22", s=42)
    for index, point in enumerate(corners, start=1):
        ax.text(*point, f"  {index}", fontsize=10, weight="bold")
    if quadratic:
        edge_labels = (5, 6, 7, 8, 9, 10)
        midpoints = []
        for label, (a, b) in zip(edge_labels, edges):
            midpoint = 0.5 * (corners[a] + corners[b])
            midpoints.append(midpoint)
            ax.text(*midpoint, f" {label}", fontsize=9, color="#8a5a00")
        middle = np.asarray(midpoints)
        ax.scatter(middle[:, 0], middle[:, 1], middle[:, 2], color="#e0a229", s=26)
    origin = np.asarray([-0.1, -0.1, -0.05])
    ax.quiver(*origin, 0.35, 0, 0, color="#a12b2b", arrow_length_ratio=0.15)
    ax.quiver(*origin, 0, 0.35, 0, color="#1f6f43", arrow_length_ratio=0.15)
    ax.quiver(*origin, 0, 0, 0.35, color="#155e75", arrow_length_ratio=0.15)
    ax.text(*(origin + [0.38, 0, 0]), "r")
    ax.text(*(origin + [0, 0.38, 0]), "s")
    ax.text(*(origin + [0, 0, 0.38]), "t")
    _set_equal_axes(ax, corners)
    ax.set_axis_off()
    ax.set_title("TET10: sommets et noeuds d'arete" if quadratic else "TET4: orientation et coordonnees naturelles")
    fig.tight_layout()
    fig.savefig(target, format="svg", bbox_inches="tight")
    plt.close(fig)


def plot_mitc4_formulation(output: str | Path) -> None:
    """Draw MITC4 local axes, numbering and tying points as an offline SVG."""
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    nodes = np.asarray([[-1.0, -0.65], [1.0, -0.55], [0.85, 0.75], [-0.9, 0.65]])
    tying = {"A": (0.0, -0.6), "B": (0.92, 0.0), "C": (0.0, 0.7), "D": (-0.95, 0.0)}
    fig, ax = plt.subplots(figsize=(8.8, 5.5))
    closed = np.vstack((nodes, nodes[0]))
    ax.plot(closed[:, 0], closed[:, 1], color="#155e75", linewidth=2.0)
    ax.scatter(nodes[:, 0], nodes[:, 1], color="#b94b22", s=42, zorder=3)
    for index, point in enumerate(nodes, start=1):
        ax.text(point[0] + 0.04, point[1] + 0.04, str(index), fontsize=10, weight="bold")
    for name, point in tying.items():
        ax.scatter(*point, marker="s", color="#e0a229", s=30, zorder=3)
        ax.text(point[0] + 0.04, point[1] + 0.04, name, fontsize=9)
    ax.arrow(-0.55, -0.3, 0.45, 0, color="#a12b2b", width=0.008, head_width=0.06, length_includes_head=True)
    ax.arrow(-0.55, -0.3, 0, 0.4, color="#1f6f43", width=0.008, head_width=0.06, length_includes_head=True)
    ax.text(-0.05, -0.34, "$e_1$")
    ax.text(-0.61, 0.15, "$e_2$")
    ax.text(0.18, 0.02, "$e_3=e_1\\times e_2$ (normal)", color="#155e75")
    ax.set_aspect("equal")
    ax.set_xlim(-1.25, 1.3)
    ax.set_ylim(-0.9, 1.0)
    ax.set_axis_off()
    ax.set_title("MITC4: base locale et points de tying")
    fig.tight_layout()
    fig.savefig(target, format="svg", bbox_inches="tight")
    plt.close(fig)


def _unique_edges(elements: Sequence[object]) -> list[tuple[int, int]]:
    edges: set[tuple[int, int]] = set()
    for element in elements:
        connectivity = tuple(int(value) for value in element.nodes)
        element_type = str(element.type).upper()
        if element_type in {"TET4", "TET10"}:
            pairs = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
        elif element_type == "MITC4":
            pairs = ((0, 1), (1, 2), (2, 3), (3, 0))
        elif element_type == "BEAM2":
            pairs = ((0, 1),)
        else:
            continue
        for first, second in pairs:
            a, b = connectivity[first], connectivity[second]
            edges.add((min(a, b), max(a, b)))
    return sorted(edges)


def _plot_load_arrows(ax: object, model: object, nodes: np.ndarray) -> None:
    nodal: dict[int, np.ndarray] = {}
    for load in getattr(model, "loads", []):
        if load.dof not in TRANSLATION_DOFS:
            continue
        vector = nodal.setdefault(int(load.node), np.zeros(3, dtype=float))
        vector[TRANSLATION_DOFS.index(load.dof)] += float(load.value)
    if not nodal:
        return
    model_size = max(float(np.linalg.norm(np.ptp(nodes, axis=0))), 1.0)
    maximum = max(float(np.linalg.norm(vector)) for vector in nodal.values())
    for node, vector in nodal.items():
        direction = vector / max(maximum, 1.0e-30) * 0.18 * model_size
        start = nodes[node] - direction
        ax.quiver(*start, *direction, color="#a12b2b", arrow_length_ratio=0.18, linewidth=1.2, label="Charge" if node == min(nodal) else None)


def _set_equal_axes(ax: object, points: np.ndarray) -> None:
    minimum = np.min(points, axis=0)
    maximum = np.max(points, axis=0)
    center = 0.5 * (minimum + maximum)
    radius = 0.56 * max(float(np.max(maximum - minimum)), 1.0)
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)
