"""Synthetic large TET4 benchmark model generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import numpy as np

from solveur.large.io import save_large_model
from solveur.large.materials import create_large_material
from solveur.large.model import LargeModel


def generate_tet4_block(
    path: str | Path,
    *,
    nx: int,
    ny: int,
    nz: int,
    length: float = 1.0,
    height: float = 1.0,
    depth: float = 1.0,
    young: float = 210.0e9,
    poisson: float = 0.3,
    density: float = 7800.0,
    total_load: float = 1000.0,
    material: Mapping[str, Any] | None = None,
) -> LargeModel:
    """Generate a structured block split into six positive-volume TET4 per cell."""
    if min(nx, ny, nz) <= 0:
        raise ValueError("Block dimensions nx, ny, nz must be positive.")
    nodes = _nodes(nx, ny, nz, length, height, depth)
    tet4 = _tet4(nx, ny, nz)
    fixed_nodes, fixed_components = _fixed_left_face(nx, ny, nz)
    load_nodes, load_components, load_values = _right_face_loads(nx, ny, nz, total_load)
    analysis = {
        "type": "linear_static",
        "method": "cg",
        "parameters": {"rtol": 1.0e-12, "max_it": 10000},
        "large_model": {
            "kind": "structured_tet4_block",
            "nx": int(nx),
            "ny": int(ny),
            "nz": int(nz),
            "length": float(length),
            "height": float(height),
            "depth": float(depth),
            "tetrahedra_per_cell": 6,
        },
    }
    material_data = (
        dict(material)
        if material is not None
        else {"type": "isotropic_3d", "E": young, "nu": poisson, "density": density}
    )
    # Validate here so generated HDF5/NPZ artifacts are immediately solvable.
    create_large_material(material_data)
    model = LargeModel(
        nodes=nodes,
        tet4=tet4,
        material_ids=np.zeros(tet4.shape[0], dtype=np.int64),
        materials={"steel": material_data},
        material_names=("steel",),
        fixed_nodes=fixed_nodes,
        fixed_components=fixed_components,
        load_nodes=load_nodes,
        load_components=load_components,
        load_values=load_values,
        analysis=analysis,
        units={"system": "SI"},
    )
    save_large_model(model, path)
    return model


def recommended_block_for_dofs(target_dofs: int) -> tuple[int, int, int]:
    """Return near-cubic cell counts that reach at least target_dofs."""
    if target_dofs <= 0:
        raise ValueError("target_dofs must be positive.")
    target_nodes = int(np.ceil(target_dofs / 3.0))
    cells = max(1, int(np.ceil(target_nodes ** (1.0 / 3.0))) - 1)
    while 3 * (cells + 1) ** 3 < target_dofs:
        cells += 1
    return cells, cells, cells


def _nodes(nx: int, ny: int, nz: int, length: float, height: float, depth: float) -> np.ndarray:
    x = np.linspace(0.0, length, nx + 1)
    y = np.linspace(0.0, height, ny + 1)
    z = np.linspace(0.0, depth, nz + 1)
    grid = np.stack(np.meshgrid(x, y, z, indexing="ij"), axis=-1)
    return grid.reshape((-1, 3))


def _tet4(nx: int, ny: int, nz: int) -> np.ndarray:
    tets = np.empty((6 * nx * ny * nz, 4), dtype=np.int64)
    cursor = 0
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                cube = _cube_nodes(i, j, k, ny, nz)
                local = (
                    (0, 1, 3, 7),
                    (0, 3, 2, 7),
                    (0, 2, 6, 7),
                    (0, 6, 4, 7),
                    (0, 4, 5, 7),
                    (0, 5, 1, 7),
                )
                for tet in local:
                    tets[cursor] = [cube[index] for index in tet]
                    cursor += 1
    return tets


def _cube_nodes(i: int, j: int, k: int, ny: int, nz: int) -> tuple[int, ...]:
    return (
        _node_id(i, j, k, ny, nz),
        _node_id(i + 1, j, k, ny, nz),
        _node_id(i, j + 1, k, ny, nz),
        _node_id(i + 1, j + 1, k, ny, nz),
        _node_id(i, j, k + 1, ny, nz),
        _node_id(i + 1, j, k + 1, ny, nz),
        _node_id(i, j + 1, k + 1, ny, nz),
        _node_id(i + 1, j + 1, k + 1, ny, nz),
    )


def _node_id(i: int, j: int, k: int, ny: int, nz: int) -> int:
    return i * (ny + 1) * (nz + 1) + j * (nz + 1) + k


def _fixed_left_face(nx: int, ny: int, nz: int) -> tuple[np.ndarray, np.ndarray]:
    del nx
    face_nodes = np.array([_node_id(0, j, k, ny, nz) for j in range(ny + 1) for k in range(nz + 1)], dtype=np.int64)
    return np.repeat(face_nodes, 3), np.tile(np.arange(3, dtype=np.int8), face_nodes.size)


def _right_face_loads(nx: int, ny: int, nz: int, total_load: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    face_nodes = np.array([_node_id(nx, j, k, ny, nz) for j in range(ny + 1) for k in range(nz + 1)], dtype=np.int64)
    values = np.full(face_nodes.size, float(total_load) / max(face_nodes.size, 1), dtype=float)
    return face_nodes, np.zeros(face_nodes.size, dtype=np.int8), values
