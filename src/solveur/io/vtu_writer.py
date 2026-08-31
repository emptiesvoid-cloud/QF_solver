"""VTU export for viewing solved models in ParaView."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from solveur.core.dofs import TRANSLATION_DOFS
from solveur.core.model import FiniteElementModel


VTK_CELL_TYPES = {
    "BEAM2": 3,
    "MITC3": 5,
    "MITC4": 9,
    "TET4": 10,
    "HEX8": 12,
    "TET10": 24,
    "HEX20": 25,
    "WEDGE6": 13,
}


class VtuResultWriter:
    """Write a minimal ASCII VTU unstructured grid for displacement results."""

    def write(self, result: object, model: FiniteElementModel, path: str | Path) -> None:
        if not hasattr(result, "displacements") or not hasattr(result, "dofs"):
            raise ValueError("VTU export requires a static displacement result.")
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        connectivity, offsets, cell_types = self._cells(model)
        target.write_text(
            "\n".join(
                [
                    '<?xml version="1.0"?>',
                    '<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian">',
                    "  <UnstructuredGrid>",
                    f'    <Piece NumberOfPoints="{model.node_count}" NumberOfCells="{len(model.elements)}">',
                    "      <Points>",
                    f'        <DataArray type="Float64" NumberOfComponents="3" format="ascii">{_array(model.nodes.ravel())}</DataArray>',
                    "      </Points>",
                    "      <Cells>",
                    f'        <DataArray type="Int32" Name="connectivity" format="ascii">{_array(connectivity)}</DataArray>',
                    f'        <DataArray type="Int32" Name="offsets" format="ascii">{_array(offsets)}</DataArray>',
                    f'        <DataArray type="UInt8" Name="types" format="ascii">{_array(cell_types)}</DataArray>',
                    "      </Cells>",
                    "      <PointData Vectors=\"Displacement\">",
                    f'        <DataArray type="Float64" Name="Displacement" NumberOfComponents="3" format="ascii">{_array(_displacement_vectors(result, model))}</DataArray>',
                    f'        <DataArray type="Float64" Name="DisplacementMagnitude" format="ascii">{_array(_displacement_magnitudes(result, model))}</DataArray>',
                    f'        <DataArray type="Float64" Name="NodalVonMises" format="ascii">{_array(_nodal_scalar(result, model, "von_mises"))}</DataArray>',
                    f'        <DataArray type="Float64" Name="NodalStressTrace" format="ascii">{_array(_nodal_scalar(result, model, "stress_trace"))}</DataArray>',
                    f'        <DataArray type="Float64" Name="NodalPrincipalStress" NumberOfComponents="3" format="ascii">{_array(_nodal_vector(result, model, "principal_stress", 3))}</DataArray>',
                    f'        <DataArray type="Float64" Name="ShellTopNodalVonMises" format="ascii">{_array(_nodal_scalar(result, model, "shell_top_von_mises"))}</DataArray>',
                    f'        <DataArray type="Float64" Name="ShellBottomNodalVonMises" format="ascii">{_array(_nodal_scalar(result, model, "shell_bottom_von_mises"))}</DataArray>',
                    "      </PointData>",
                    "      <CellData Scalars=\"VonMises\">",
                    f'        <DataArray type="Int32" Name="ElementIndex" format="ascii">{_array(range(len(model.elements)))}</DataArray>',
                    f'        <DataArray type="Float64" Name="VonMises" format="ascii">{_array(_von_mises(result, model))}</DataArray>',
                    f'        <DataArray type="Int32" Name="HasVonMises" format="ascii">{_array(_has_von_mises(result, model))}</DataArray>',
                    f'        <DataArray type="Float64" Name="StressTrace" format="ascii">{_array(_cell_scalar(result, model, "stress_trace"))}</DataArray>',
                    f'        <DataArray type="Float64" Name="HydrostaticPressure" format="ascii">{_array(_cell_scalar(result, model, "hydrostatic_pressure"))}</DataArray>',
                    f'        <DataArray type="Float64" Name="PrincipalStress" NumberOfComponents="3" format="ascii">{_array(_cell_vector(result, model, "principal_stress", 3))}</DataArray>',
                    f'        <DataArray type="Float64" Name="PrincipalStrain" NumberOfComponents="3" format="ascii">{_array(_cell_vector(result, model, "principal_strain", 3))}</DataArray>',
                    f'        <DataArray type="Float64" Name="ShellTopVonMises" format="ascii">{_array(_shell_face_scalar(result, model, "top", "von_mises"))}</DataArray>',
                    f'        <DataArray type="Float64" Name="ShellBottomVonMises" format="ascii">{_array(_shell_face_scalar(result, model, "bottom", "von_mises"))}</DataArray>',
                    "      </CellData>",
                    "    </Piece>",
                    "  </UnstructuredGrid>",
                    "</VTKFile>",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _cells(model: FiniteElementModel) -> tuple[list[int], list[int], list[int]]:
        connectivity: list[int] = []
        offsets: list[int] = []
        cell_types: list[int] = []
        offset = 0
        for element in model.elements:
            if element.type not in VTK_CELL_TYPES:
                raise ValueError(f"VTU export does not support element type {element.type!r}.")
            nodes = [int(node) for node in element.nodes]
            connectivity.extend(nodes)
            offset += len(nodes)
            offsets.append(offset)
            cell_types.append(VTK_CELL_TYPES[element.type])
        return connectivity, offsets, cell_types


def _displacement_vectors(result: object, model: FiniteElementModel) -> np.ndarray:
    dofs = result.dofs
    values = np.asarray(result.displacements, dtype=float)
    vectors = np.zeros((model.node_count, 3), dtype=float)
    for node in range(model.node_count):
        for component, dof in enumerate(TRANSLATION_DOFS):
            if dofs.has(node, dof):
                vectors[node, component] = values[dofs.index(node, dof)]
    return vectors.ravel()


def _displacement_magnitudes(result: object, model: FiniteElementModel) -> np.ndarray:
    return np.linalg.norm(_displacement_vectors(result, model).reshape((model.node_count, 3)), axis=1)


def _von_mises(result: object, model: FiniteElementModel) -> list[float]:
    values = _element_result_map(result)
    return [float(values.get(index, {}).get("von_mises", 0.0)) for index in range(len(model.elements))]


def _has_von_mises(result: object, model: FiniteElementModel) -> list[int]:
    values = _element_result_map(result)
    return [1 if "von_mises" in values.get(index, {}) else 0 for index in range(len(model.elements))]


def _cell_scalar(result: object, model: FiniteElementModel, key: str) -> list[float]:
    values = _element_result_map(result)
    return [float(values.get(index, {}).get(key, 0.0)) for index in range(len(model.elements))]


def _cell_vector(result: object, model: FiniteElementModel, key: str, size: int) -> list[float]:
    values = _element_result_map(result)
    output: list[float] = []
    for index in range(len(model.elements)):
        raw = values.get(index, {}).get(key, [])
        vector = [float(value) for value in raw[:size]] if isinstance(raw, list) else []
        vector.extend([0.0] * (size - len(vector)))
        output.extend(vector[:size])
    return output


def _shell_face_scalar(result: object, model: FiniteElementModel, face_name: str, key: str) -> list[float]:
    values = _element_result_map(result)
    output: list[float] = []
    for index in range(len(model.elements)):
        face_value = 0.0
        for face in values.get(index, {}).get("shell_faces", []):
            if face.get("face") == face_name:
                face_value = float(face.get(key, 0.0))
                break
        output.append(face_value)
    return output


def _nodal_scalar(result: object, model: FiniteElementModel, key: str) -> list[float]:
    mapped = _nodal_result_map(result)
    return [float(mapped.get(node, {}).get(key, 0.0)) for node in range(model.node_count)]


def _nodal_vector(result: object, model: FiniteElementModel, key: str, size: int) -> list[float]:
    mapped = _nodal_result_map(result)
    output: list[float] = []
    for node in range(model.node_count):
        raw = mapped.get(node, {}).get(key, [])
        vector = [float(value) for value in raw[:size]] if isinstance(raw, list) else []
        vector.extend([0.0] * (size - len(vector)))
        output.extend(vector[:size])
    return output


def _element_result_map(result: object) -> dict[int, dict[str, Any]]:
    mapped: dict[int, dict[str, Any]] = {}
    for item in getattr(result, "element_results", []):
        if "element" in item:
            mapped[int(item["element"])] = item
    return mapped


def _nodal_result_map(result: object) -> dict[int, dict[str, Any]]:
    mapped: dict[int, dict[str, Any]] = {}
    for item in getattr(result, "nodal_results", []):
        if "node" in item:
            mapped[int(item["node"])] = item
    return mapped


def _array(values: object) -> str:
    array = np.asarray(list(values) if not isinstance(values, np.ndarray) else values)
    if array.size == 0:
        return ""
    if np.issubdtype(array.dtype, np.integer):
        return " ".join(str(int(value)) for value in array.ravel())
    return " ".join(f"{float(value):.12g}" for value in array.ravel())
