"""Publish controlled stress and strain fields for documentation benchmarks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import Normalize  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection  # noqa: E402

from scripts.docs_support import nodal_translations, write_json
from solveur.io.manifest import sha256


@dataclass(frozen=True)
class FieldDefinition:
    """Describe one non-negative element field and its publication convention."""

    key: str
    suffix: str
    label: str
    cmap: str
    extractor: Callable[[dict[str, Any]], float | None]


def publish_benchmark_fields(
    model: object,
    result: object,
    result_data: dict[str, Any],
    output_prefix: Path,
    title: str,
    scale: float,
) -> dict[str, Any]:
    """Write every mechanically meaningful field available in a result."""
    element_count = len(model.elements)
    rows = _indexed_rows(result_data.get("element_results", []), element_count)
    definitions = (
        FieldDefinition(
            "von_mises",
            "von_mises",
            "Contrainte equivalente de von Mises [unite du modele]",
            "cividis",
            _stress_measure,
        ),
        FieldDefinition(
            "strain_measure",
            "strain_measure",
            _strain_label(model),
            "viridis",
            _strain_measure,
        ),
        FieldDefinition(
            "equivalent_plastic_strain",
            "plastic_strain",
            "Deformation plastique equivalente cumulee [-]",
            "magma",
            _plastic_strain_measure,
        ),
    )
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    published: list[dict[str, Any]] = []
    for definition in definitions:
        extracted = [definition.extractor(row) if row is not None else None for row in rows]
        available = [value for value in extracted if value is not None]
        if not available:
            continue
        if len(available) != element_count:
            raise RuntimeError(
                f"Field {definition.key} covers {len(available)}/{element_count} elements for {title}."
            )
        values = np.asarray(available, dtype=float)
        if not np.all(np.isfinite(values)) or np.any(values < 0.0):
            raise RuntimeError(f"Field {definition.key} contains invalid values for {title}.")
        output = output_prefix.with_name(f"{output_prefix.name}_{definition.suffix}.png")
        _plot_field(model, result, values, output, title, scale, definition)
        published.append(
            {
                "key": definition.key,
                "path": output.name,
                "sha256": sha256(output),
                "minimum": float(np.min(values)),
                "maximum": float(np.max(values)),
                "element_count": element_count,
                "label": definition.label,
            }
        )
    report = {
        "schema_version": 1,
        "title": title,
        "element_count": element_count,
        "deformation_scale": float(scale),
        "fields": published,
    }
    write_json(output_prefix.with_name(f"{output_prefix.name}_field_summary.json"), report)
    return report


def equivalent_strain_3d(values: list[float] | np.ndarray) -> float:
    """Return von-Mises equivalent strain from engineering-shear Voigt data."""
    strain = np.asarray(values, dtype=float)
    if strain.shape != (6,):
        raise ValueError("A 3D engineering strain vector must contain six components.")
    normal = strain[:3]
    deviatoric = normal - np.mean(normal)
    tensor_shear = 0.5 * strain[3:]
    norm_squared = float(np.dot(deviatoric, deviatoric) + 2.0 * np.dot(tensor_shear, tensor_shear))
    return math.sqrt(max(2.0 * norm_squared / 3.0, 0.0))


def shell_face_strain_measure(values: list[float] | np.ndarray) -> float:
    """Return the in-plane tensor norm for engineering-shear shell strains."""
    strain = np.asarray(values, dtype=float)
    if strain.shape != (3,):
        raise ValueError("A shell face strain vector must contain three components.")
    return math.sqrt(max(float(strain[0] ** 2 + strain[1] ** 2 + 0.5 * strain[2] ** 2), 0.0))


def beam_curvature_measure(values: list[float] | np.ndarray) -> float:
    """Return the Euclidean norm of the three BEAM2 generalized curvatures."""
    strain = np.asarray(values, dtype=float)
    if strain.shape != (6,):
        raise ValueError("A BEAM2 generalized strain vector must contain six components.")
    return float(np.linalg.norm(strain[3:]))


def _stress_measure(row: dict[str, Any]) -> float | None:
    if "von_mises" in row:
        return abs(float(row["von_mises"]))
    faces = row.get("shell_faces", [])
    values = [abs(float(face["von_mises"])) for face in faces if "von_mises" in face]
    return max(values) if values else None


def _strain_measure(row: dict[str, Any]) -> float | None:
    if "strain" in row:
        return equivalent_strain_3d(row["strain"])
    faces = row.get("shell_faces", [])
    values = [shell_face_strain_measure(face["strain"]) for face in faces if "strain" in face]
    if values:
        return max(values)
    if "membrane_strain" in row:
        return shell_face_strain_measure(row["membrane_strain"])
    if "generalized_strain" in row:
        return beam_curvature_measure(row["generalized_strain"])
    return None


def _plastic_strain_measure(row: dict[str, Any]) -> float | None:
    if "equivalent_plastic_strain" in row:
        return abs(float(row["equivalent_plastic_strain"]))
    state = row.get("material_state", {})
    if "equivalent_plastic_strain" in state:
        return abs(float(state["equivalent_plastic_strain"]))
    return None


def _strain_label(model: object) -> str:
    families = {str(element.type).upper() for element in model.elements}
    if families == {"BEAM2"}:
        return "Norme des courbures generalisees [1/unite de longueur]"
    if families <= {"MITC3", "MITC4"}:
        return "Norme tensorielle maximale des deformations de face [-]"
    return "Deformation equivalente de von Mises [-]"


def _indexed_rows(raw_rows: list[dict[str, Any]], element_count: int) -> list[dict[str, Any] | None]:
    rows: list[dict[str, Any] | None] = [None] * element_count
    for position, row in enumerate(raw_rows):
        index = int(row.get("element", position))
        if not 0 <= index < element_count or rows[index] is not None:
            raise RuntimeError(f"Invalid or duplicate element result index: {index}.")
        rows[index] = row
    return rows


def _plot_field(
    model: object,
    result: object,
    values: np.ndarray,
    output: Path,
    title: str,
    scale: float,
    definition: FieldDefinition,
) -> None:
    nodes = np.asarray(model.nodes, dtype=float)
    translations = nodal_translations(model, result)
    deformed = nodes + scale * translations
    patches, patch_owners = _surface_patches(model.elements, deformed)
    segments, segment_owners = _beam_segments(model.elements, deformed)
    if not patches and not segments:
        raise RuntimeError(f"No drawable exterior geometry exists for {title}.")
    maximum = max(float(np.max(values, initial=0.0)), 1.0e-30)
    minimum = min(float(np.min(values, initial=0.0)), 0.0)
    norm = Normalize(vmin=minimum, vmax=maximum)
    cmap = plt.get_cmap(definition.cmap)
    figure = plt.figure(figsize=(9.4, 6.3))
    axis = figure.add_subplot(111, projection="3d")
    if patches:
        colors = [cmap(norm(float(values[owner]))) for owner in patch_owners]
        axis.add_collection3d(
            Poly3DCollection(patches, facecolors=colors, edgecolors="#263238", linewidths=0.42, alpha=0.96)
        )
    if segments:
        collection = Line3DCollection(segments, cmap=cmap, norm=norm, linewidths=5.0)
        collection.set_array(np.asarray([values[owner] for owner in segment_owners], dtype=float))
        axis.add_collection3d(collection)
    original_edges = _model_edges(model.elements)
    axis.add_collection3d(
        Line3DCollection(
            [[nodes[first], nodes[second]] for first, second in original_edges],
            colors="#6b7280",
            linewidths=0.55,
            alpha=0.62,
        )
    )
    scalar = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    scalar.set_array([])
    colorbar = figure.colorbar(scalar, ax=axis, shrink=0.64, pad=0.08)
    colorbar.set_label(definition.label)
    _equal_axes(axis, np.vstack((nodes, deformed)))
    axis.set_xlabel("X")
    axis.set_ylabel("Y")
    axis.set_zlabel("Z")
    axis.set_title(f"{title}\n{definition.label}, amplification = {scale:.3g}")
    axis.view_init(elev=25.0, azim=-56.0)
    figure.tight_layout()
    figure.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(figure)


def _surface_patches(elements: list[object], nodes: np.ndarray) -> tuple[list[np.ndarray], list[int]]:
    tetra_faces = ((0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3))
    face_uses: dict[tuple[int, ...], list[tuple[tuple[int, ...], int]]] = {}
    patches: list[np.ndarray] = []
    owners: list[int] = []
    for owner, element in enumerate(elements):
        connectivity = tuple(int(value) for value in element.nodes)
        element_type = str(element.type).upper()
        if element_type == "MITC4":
            patches.append(nodes[np.asarray(connectivity[:4], dtype=int)])
            owners.append(owner)
        elif element_type == "MITC3":
            patches.append(nodes[np.asarray(connectivity[:3], dtype=int)])
            owners.append(owner)
        elif element_type in {"TET4", "TET10"}:
            for local in tetra_faces:
                face = tuple(connectivity[index] for index in local)
                face_uses.setdefault(tuple(sorted(face)), []).append((face, owner))
    for key in sorted(face_uses):
        if len(face_uses[key]) == 1:
            face, owner = face_uses[key][0]
            patches.append(nodes[np.asarray(face, dtype=int)])
            owners.append(owner)
    return patches, owners


def _beam_segments(elements: list[object], nodes: np.ndarray) -> tuple[list[np.ndarray], list[int]]:
    segments: list[np.ndarray] = []
    owners: list[int] = []
    for owner, element in enumerate(elements):
        if str(element.type).upper() != "BEAM2":
            continue
        connectivity = tuple(int(value) for value in element.nodes)
        segments.append(nodes[np.asarray(connectivity[:2], dtype=int)])
        owners.append(owner)
    return segments, owners


def _model_edges(elements: list[object]) -> list[tuple[int, int]]:
    edges: set[tuple[int, int]] = set()
    for element in elements:
        connectivity = tuple(int(value) for value in element.nodes)
        element_type = str(element.type).upper()
        if element_type in {"TET4", "TET10"}:
            pairs = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
        elif element_type == "MITC4":
            pairs = ((0, 1), (1, 2), (2, 3), (3, 0))
        elif element_type == "MITC3":
            pairs = ((0, 1), (1, 2), (2, 0))
        elif element_type == "BEAM2":
            pairs = ((0, 1),)
        else:
            continue
        edges.update(tuple(sorted((connectivity[first], connectivity[second]))) for first, second in pairs)
    return sorted(edges)


def _equal_axes(axis: object, points: np.ndarray) -> None:
    minimum = np.min(points, axis=0)
    maximum = np.max(points, axis=0)
    center = 0.5 * (minimum + maximum)
    radius = max(float(np.max(maximum - minimum)) * 0.55, 1.0e-9)
    axis.set_xlim(center[0] - radius, center[0] + radius)
    axis.set_ylim(center[1] - radius, center[1] + radius)
    axis.set_zlim(center[2] - radius, center[2] + radius)
