"""Shared TET4 visualization helpers for controlled V&V evidence."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from solveur.core.errors import InputValidationError


def translations_from_result(node_count: int, result: dict[str, Any]) -> np.ndarray:
    """Extract nodal UX/UY/UZ values from a standard result dictionary."""
    values = np.zeros((node_count, 3), dtype=float)
    for row in result.get("displacements", []):
        node = int(row["node"])
        dofs = row["dofs"]
        values[node] = [float(dofs.get(name, 0.0)) for name in ("UX", "UY", "UZ")]
    return values


def load_vtu_displacements(path: str | Path, expected_nodes: int) -> np.ndarray:
    """Read the ASCII displacement array written by QF_solver's VTU exporter."""
    source = Path(path)
    try:
        root = ET.parse(source).getroot()
    except (ET.ParseError, OSError) as exc:
        raise InputValidationError(f"Cannot read V&V VTU displacement file {source}: {exc}") from exc
    array = root.find(".//PointData/DataArray[@Name='Displacement']")
    if array is None or not array.text:
        raise InputValidationError(f"VTU file has no Displacement point array: {source}")
    values = np.fromstring(array.text, sep=" ", dtype=float)
    if values.size != expected_nodes * 3:
        raise InputValidationError(
            f"VTU displacement size mismatch in {source}: {values.size} values for {expected_nodes} nodes."
        )
    translations = values.reshape((expected_nodes, 3))
    if not np.all(np.isfinite(translations)):
        raise InputValidationError(f"VTU displacement array contains non-finite values: {source}")
    return translations


def plot_tet4_deformation(
    path: str | Path,
    model: dict[str, Any],
    translations: np.ndarray,
    scale: float,
    *,
    title: str,
    view: tuple[float, float] = (25.0, -56.0),
) -> None:
    """Plot the exterior TET4 skin with a displacement-magnitude color field."""
    nodes = np.asarray(model["nodes"], dtype=float)
    _validate_shape(nodes, translations)
    deformed = nodes + float(scale) * translations
    polygons, values = visible_tet4_faces(model["elements"], deformed, np.linalg.norm(translations, axis=1))
    figure = plt.figure(figsize=(8.2, 5.8))
    axis = figure.add_subplot(111, projection="3d")
    if polygons:
        maximum = max(max(values), 1.0e-30)
        colors = [plt.get_cmap("viridis")(value / maximum) for value in values]
        axis.add_collection3d(
            Poly3DCollection(polygons, facecolors=colors, edgecolors="#263238", linewidths=0.3)
        )
    set_equal_3d_axes(axis, np.vstack((nodes, deformed)))
    axis.set_xlabel("X [m]")
    axis.set_ylabel("Y [m]")
    axis.set_zlabel("Z [m]")
    axis.set_title(f"{title}\nAmplification = {scale:.4g}")
    axis.view_init(elev=view[0], azim=view[1])
    figure.tight_layout()
    figure.savefig(Path(path), dpi=180, bbox_inches="tight")
    plt.close(figure)


def plot_tet4_cell_field(
    path: str | Path,
    nodes: np.ndarray,
    connectivity: np.ndarray,
    translations: np.ndarray,
    cell_values: np.ndarray,
    scale: float,
    *,
    title: str,
    color_label: str,
    color_maximum: float | None = None,
    view: tuple[float, float] = (25.0, -56.0),
) -> None:
    """Plot an exterior TET4 cell field without materializing element dictionaries."""
    coordinates = np.asarray(nodes, dtype=float)
    cells = np.asarray(connectivity, dtype=np.int64)
    displacements = np.asarray(translations, dtype=float)
    values = np.asarray(cell_values, dtype=float)
    _validate_shape(coordinates, displacements)
    if cells.ndim != 2 or cells.shape[1] != 4 or values.shape != (cells.shape[0],):
        raise InputValidationError(
            "V&V cell-field plot expects connectivity [m,4] and one scalar per cell; "
            f"got cells={cells.shape}, values={values.shape}."
        )
    if not np.all(np.isfinite(values)):
        raise InputValidationError("V&V cell-field plot received non-finite scalar values.")
    deformed = coordinates + float(scale) * displacements
    faces, owners = exterior_tet4_faces(cells)
    polygons = deformed[faces]
    maximum = max(float(color_maximum or np.max(values, initial=0.0)), 1.0e-30)
    normalized = np.clip(values[owners] / maximum, 0.0, 1.0)
    colors = plt.get_cmap("plasma")(normalized)
    figure = plt.figure(figsize=(8.8, 6.1))
    axis = figure.add_subplot(111, projection="3d")
    axis.add_collection3d(
        Poly3DCollection(polygons, facecolors=colors, edgecolors="#263238", linewidths=0.18)
    )
    scalar = plt.cm.ScalarMappable(cmap="plasma", norm=plt.Normalize(vmin=0.0, vmax=maximum))
    scalar.set_array([])
    colorbar = figure.colorbar(scalar, ax=axis, shrink=0.65, pad=0.08)
    colorbar.set_label(color_label)
    set_equal_3d_axes(axis, np.vstack((coordinates, deformed)))
    axis.set_xlabel("X [m]")
    axis.set_ylabel("Y [m]")
    axis.set_zlabel("Z [m]")
    axis.set_title(f"{title}\nAmplification = {scale:.4g}")
    axis.view_init(elev=view[0], azim=view[1])
    figure.tight_layout()
    figure.savefig(Path(path), dpi=180, bbox_inches="tight")
    plt.close(figure)


def exterior_tet4_faces(connectivity: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return oriented exterior faces and their owner elements using array operations."""
    cells = np.asarray(connectivity, dtype=np.int64)
    if cells.ndim != 2 or cells.shape[1] != 4:
        raise InputValidationError(f"TET4 connectivity must have shape [m,4], got {cells.shape}.")
    faces = np.concatenate(
        (
            cells[:, (0, 2, 1)],
            cells[:, (0, 1, 3)],
            cells[:, (1, 2, 3)],
            cells[:, (2, 0, 3)],
        )
    )
    owners = np.tile(np.arange(cells.shape[0], dtype=np.int64), 4)
    keys = np.sort(faces, axis=1)
    _, inverse, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    exterior = counts[inverse] == 1
    return faces[exterior], owners[exterior]


def write_tet4_displacement_vtu(path: str | Path, model: dict[str, Any], translations: np.ndarray) -> None:
    """Write a compact ASCII VTU carrying an analytic TET4 displacement field."""
    nodes = np.asarray(model["nodes"], dtype=float)
    _validate_shape(nodes, translations)
    if any(str(item.get("type", "")).upper() != "TET4" for item in model["elements"]):
        raise InputValidationError("V&V TET4 VTU writer received a non-TET4 element.")
    connectivity = [tuple(int(node) for node in item["nodes"][:4]) for item in model["elements"]]
    coordinates = " ".join(f"{value:.16e}" for value in nodes.ravel())
    vectors = " ".join(f"{value:.16e}" for value in translations.ravel())
    magnitudes = " ".join(f"{value:.16e}" for value in np.linalg.norm(translations, axis=1))
    cell_nodes = " ".join(str(node) for cell in connectivity for node in cell)
    offsets = " ".join(str(4 * (index + 1)) for index in range(len(connectivity)))
    types = " ".join("10" for _ in connectivity)
    Path(path).write_text(
        "<?xml version=\"1.0\"?>\n"
        "<VTKFile type=\"UnstructuredGrid\" version=\"0.1\" byte_order=\"LittleEndian\">\n"
        "  <UnstructuredGrid>\n"
        f"    <Piece NumberOfPoints=\"{len(nodes)}\" NumberOfCells=\"{len(connectivity)}\">\n"
        "      <PointData Vectors=\"Displacement\">\n"
        "        <DataArray type=\"Float64\" Name=\"Displacement\" NumberOfComponents=\"3\" "
        f"format=\"ascii\">{vectors}</DataArray>\n"
        "        <DataArray type=\"Float64\" Name=\"DisplacementMagnitude\" "
        f"format=\"ascii\">{magnitudes}</DataArray>\n"
        "      </PointData>\n"
        "      <Points><DataArray type=\"Float64\" NumberOfComponents=\"3\" "
        f"format=\"ascii\">{coordinates}</DataArray></Points>\n"
        "      <Cells>\n"
        f"        <DataArray type=\"Int64\" Name=\"connectivity\" format=\"ascii\">{cell_nodes}</DataArray>\n"
        f"        <DataArray type=\"Int64\" Name=\"offsets\" format=\"ascii\">{offsets}</DataArray>\n"
        f"        <DataArray type=\"UInt8\" Name=\"types\" format=\"ascii\">{types}</DataArray>\n"
        "      </Cells>\n"
        "    </Piece>\n"
        "  </UnstructuredGrid>\n"
        "</VTKFile>\n",
        encoding="utf-8",
    )


def visible_tet4_faces(
    elements: list[dict[str, Any]], nodes: np.ndarray, nodal_values: np.ndarray
) -> tuple[list[np.ndarray], list[float]]:
    """Return exterior triangular faces and averaged nodal values."""
    definitions = ((0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3))
    usage: dict[tuple[int, ...], tuple[int, ...] | None] = {}
    for element in elements:
        connectivity = tuple(int(index) for index in element["nodes"][:4])
        for local in definitions:
            face = tuple(connectivity[index] for index in local)
            key = tuple(sorted(face))
            usage[key] = None if key in usage else face
    polygons: list[np.ndarray] = []
    values: list[float] = []
    for face in usage.values():
        if face is not None:
            indices = np.asarray(face, dtype=int)
            polygons.append(nodes[indices])
            values.append(float(np.mean(nodal_values[indices])))
    return polygons, values


def set_equal_3d_axes(axis: Any, points: np.ndarray) -> None:
    """Set equal, stable bounds around a 3D point cloud."""
    minimum = np.min(points, axis=0)
    maximum = np.max(points, axis=0)
    center = 0.5 * (minimum + maximum)
    radius = max(float(np.max(maximum - minimum)) * 0.55, 1.0e-9)
    axis.set_xlim(center[0] - radius, center[0] + radius)
    axis.set_ylim(center[1] - radius, center[1] + radius)
    axis.set_zlim(center[2] - radius, center[2] + radius)
    axis.set_box_aspect((1.0, 1.0, 1.0))


def _validate_shape(nodes: np.ndarray, translations: np.ndarray) -> None:
    if nodes.ndim != 2 or nodes.shape[1] != 3 or translations.shape != nodes.shape:
        raise InputValidationError(
            f"V&V visualization expects matching [n,3] arrays, got nodes={nodes.shape}, u={translations.shape}."
        )
