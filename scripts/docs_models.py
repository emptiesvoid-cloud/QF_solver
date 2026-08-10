"""Deterministic finite-element models used only by the documentation campaign."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import numpy as np

from scripts.docs_support import write_json
from solveur.api import generate_large_tet4_block
from solveur.core.model import FiniteElementModel
from solveur.large.io import save_large_model


class DocumentationModelFactory:
    """Build versioned inputs for visual and convergence demonstrations."""

    def __init__(self, root: str | Path, output_dir: str | Path) -> None:
        self.root = Path(root).resolve()
        self.output_dir = Path(output_dir).resolve()

    def tet4_cantilever(self, refinement: int) -> tuple[FiniteElementModel, Path]:
        model_path = self.output_dir / f"tet4_cantilever_r{refinement}.json"
        large_path = self.output_dir / f"tet4_cantilever_r{refinement}.npz"
        large = generate_large_tet4_block(
            large_path,
            nx=4 * refinement,
            ny=refinement,
            nz=refinement,
            length=4.0,
            height=1.0,
            depth=1.0,
            young=70.0e9,
            poisson=0.3,
            total_load=-1000.0,
        )
        large.load_components[:] = 2
        save_large_model(large, large_path)
        model = standard_model_from_large(large)
        self.write_model(model, model_path)
        return model, model_path

    def tet10_cantilever(self) -> tuple[FiniteElementModel, Path]:
        tet4_model, _ = self.tet4_cantilever(1)
        nodes, connectivities = upgrade_tet4_to_tet10(
            tet4_model.nodes,
            [element.nodes for element in tet4_model.elements],
        )
        fixed = [
            {"node": index, "dofs": ["UX", "UY", "UZ"]}
            for index, point in enumerate(nodes)
            if abs(float(point[0])) <= 1.0e-12
        ]
        tip_nodes = [index for index, point in enumerate(nodes) if abs(float(point[0]) - 4.0) <= 1.0e-12]
        loads = [{"node": index, "dof": "UZ", "value": -1000.0 / len(tip_nodes)} for index in tip_nodes]
        model = FiniteElementModel.from_raw(
            nodes=nodes.tolist(),
            elements=[
                {"type": "TET10", "nodes": list(connectivity), "material": "aluminium"}
                for connectivity in connectivities
            ],
            materials={
                "aluminium": {"type": "isotropic_3d", "E": 70.0e9, "nu": 0.3, "density": 2700.0}
            },
            fixed_dofs=fixed,
            loads=loads,
            analysis={"type": "linear_static", "method": "direct"},
            verification_profile="engineering",
        )
        path = self.output_dir / "tet10_cantilever.json"
        self.write_model(model, path)
        return model, path

    def mitc4_plate(self) -> tuple[FiniteElementModel, Path]:
        nx, ny = 8, 2
        nodes = [[i / nx, 0.2 * j / ny, 0.0] for i in range(nx + 1) for j in range(ny + 1)]

        def node(i: int, j: int) -> int:
            return i * (ny + 1) + j

        elements = [
            {
                "type": "MITC4",
                "nodes": [node(i, j), node(i + 1, j), node(i + 1, j + 1), node(i, j + 1)],
                "material": "skin",
            }
            for i in range(nx)
            for j in range(ny)
        ]
        fixed = [
            {"node": node(0, j), "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}
            for j in range(ny + 1)
        ]
        tip = [node(nx, j) for j in range(ny + 1)]
        loads = [{"node": index, "dof": "UZ", "value": -1000.0 / len(tip)} for index in tip]
        model = FiniteElementModel.from_raw(
            nodes=nodes,
            elements=elements,
            materials={"skin": {"type": "shell_isotropic", "E": 210.0e9, "nu": 0.3, "t": 0.01}},
            fixed_dofs=fixed,
            loads=loads,
            analysis={"type": "linear_static", "method": "direct"},
            verification_profile="engineering",
        )
        path = self.output_dir / "mitc4_plate_bending.json"
        self.write_model(model, path)
        return model, path

    @staticmethod
    def write_model(model: FiniteElementModel, path: str | Path) -> None:
        payload = {
            "schema_version": model.schema_version,
            "units": model.units,
            "verification_profile": model.verification_profile,
            "analysis": {"type": model.analysis.type, "method": model.analysis.method, **model.analysis.parameters},
            "nodes": model.nodes.tolist(),
            "elements": [asdict(element) for element in model.elements],
            "materials": model.materials,
            "fixed_dofs": [asdict(condition) for condition in model.fixed_dofs],
            "loads": [asdict(load) for load in model.loads],
        }
        write_json(path, payload)


def standard_model_from_large(model: object) -> FiniteElementModel:
    fixed_nodes = sorted(set(int(value) for value in model.fixed_nodes))
    fixed = [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes]
    names = ("UX", "UY", "UZ")
    loads = [
        {"node": int(node), "dof": names[int(component)], "value": float(value)}
        for node, component, value in zip(model.load_nodes, model.load_components, model.load_values)
    ]
    return FiniteElementModel.from_raw(
        nodes=model.nodes.tolist(),
        elements=[
            {"type": "TET4", "nodes": row.tolist(), "material": "aluminium"}
            for row in model.tet4
        ],
        materials={"aluminium": {"type": "isotropic_3d", "E": 70.0e9, "nu": 0.3, "density": 2700.0}},
        fixed_dofs=fixed,
        loads=loads,
        analysis={"type": "linear_static", "method": "direct"},
        verification_profile="engineering",
    )


def upgrade_tet4_to_tet10(
    nodes: np.ndarray,
    connectivities: list[tuple[int, ...]],
) -> tuple[np.ndarray, list[tuple[int, ...]]]:
    coordinates = [np.asarray(point, dtype=float) for point in nodes]
    midside: dict[tuple[int, int], int] = {}

    def midpoint(first: int, second: int) -> int:
        key = (min(first, second), max(first, second))
        if key not in midside:
            midside[key] = len(coordinates)
            coordinates.append(0.5 * (coordinates[key[0]] + coordinates[key[1]]))
        return midside[key]

    upgraded = []
    for a, b, c, d in connectivities:
        upgraded.append(
            (
                a,
                b,
                c,
                d,
                midpoint(a, b),
                midpoint(b, c),
                midpoint(c, a),
                midpoint(a, d),
                midpoint(b, d),
                midpoint(c, d),
            )
        )
    return np.asarray(coordinates, dtype=float), upgraded


def mean_tip_displacement(model: FiniteElementModel, result: object, *, component: str) -> float:
    maximum_x = float(np.max(model.nodes[:, 0]))
    nodes = np.where(np.isclose(model.nodes[:, 0], maximum_x))[0]
    values = [result.displacements[result.dofs.index(int(node), component)] for node in nodes]
    return float(np.mean(values))


def unit_tet10_coordinates() -> np.ndarray:
    return np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.5, 0.0, 0.0],
            [0.5, 0.5, 0.0],
            [0.0, 0.5, 0.0],
            [0.0, 0.0, 0.5],
            [0.5, 0.0, 0.5],
            [0.0, 0.5, 0.5],
        ]
    )
