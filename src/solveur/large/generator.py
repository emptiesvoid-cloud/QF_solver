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
    load_component: int = 0,
    load_distribution: str = "uniform",
    decomposition: str = "six",
) -> LargeModel:
    """Generate a structured block split into positive-volume TET4 per cell.

    ``six`` preserves the historical mesh used by the public examples.  The
    optional ``centered`` decomposition connects the centre of each brick to
    its twelve boundary triangles.  It is intended for convergence studies:
    it reduces the directional bias of the repeated six-tet pattern without
    changing the TET4 formulation itself.
    """
    if min(nx, ny, nz) <= 0:
        raise ValueError("Block dimensions nx, ny, nz must be positive.")
    if decomposition not in {"six", "centered"}:
        raise ValueError("TET4 block decomposition must be 'six' or 'centered'.")
    nodes = _nodes(nx, ny, nz, length, height, depth)
    if decomposition == "six":
        tet4 = _tet4(nx, ny, nz)
    else:
        nodes, tet4 = _centered_tet4(nx, ny, nz, nodes)
    fixed_nodes, fixed_components = _fixed_left_face(nx, ny, nz)
    if load_component not in (0, 1, 2):
        raise ValueError("TET4 block load_component must be 0, 1 or 2.")
    if load_distribution not in {"uniform", "tributary", "surface_consistent"}:
        raise ValueError("TET4 block load_distribution must be 'uniform', 'tributary' or 'surface_consistent'.")
    load_nodes, load_components, load_values = _right_face_loads(
        nx,
        ny,
        nz,
        total_load,
        component=load_component,
        tributary=load_distribution == "tributary",
        surface_consistent=load_distribution == "surface_consistent",
    )
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
            "tetrahedra_per_cell": 6 if decomposition == "six" else 12,
            "decomposition": decomposition,
            "load_component": int(load_component),
            "load_distribution": load_distribution,
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


def generate_tet4_cantilever_block(
    path: str | Path,
    *,
    nx: int,
    ny: int,
    nz: int,
    length: float = 4.0,
    height: float = 0.4,
    depth: float = 0.4,
    young: float = 70.0e9,
    poisson: float = 0.3,
    density: float = 7800.0,
    total_load: float = -1.0,
    material: Mapping[str, Any] | None = None,
    decomposition: str = "six",
    load_distribution: str = "tributary",
) -> LargeModel:
    """Generate a nested structured TET4 cantilever with a transverse tip load.

    The fixed face is ``x=0`` and the load is distributed on ``x=length``
    using nodal face weights. Doubling ``nx, ny, nz`` therefore creates a
    deterministic h-refinement sequence without changing the physical model.
    """
    return generate_tet4_block(
        path,
        nx=nx,
        ny=ny,
        nz=nz,
        length=length,
        height=height,
        depth=depth,
        young=young,
        poisson=poisson,
        density=density,
        total_load=total_load,
        material=material,
        load_component=2,
        load_distribution=load_distribution,
        decomposition=decomposition,
    )


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


def _centered_tet4(nx: int, ny: int, nz: int, corner_nodes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Create a conforming twelve-tet-per-cell brick decomposition."""
    base_count = corner_nodes.shape[0]
    centers = np.empty((nx * ny * nz, 3), dtype=float)
    tets: list[list[int]] = []
    faces = (
        ((0, 4, 6), (0, 6, 2)),
        ((1, 3, 7), (1, 7, 5)),
        ((0, 1, 5), (0, 5, 4)),
        ((2, 6, 7), (2, 7, 3)),
        ((0, 2, 3), (0, 3, 1)),
        ((4, 5, 7), (4, 7, 6)),
    )
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                cube = _cube_nodes(i, j, k, ny, nz)
                centers[(i * ny + j) * nz + k] = np.mean(corner_nodes[list(cube)], axis=0)
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                cube = _cube_nodes(i, j, k, ny, nz)
                center_id = base_count + (i * ny + j) * nz + k
                for triangle_pair in faces:
                    for triangle in triangle_pair:
                        # The face orientations are fixed for positive brick
                        # dimensions; every generated determinant is +V/3.
                        tets.append([center_id, *(cube[index] for index in triangle)])
    return np.vstack((corner_nodes, centers)), np.asarray(tets, dtype=np.int64)


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


def _right_face_loads(
    nx: int,
    ny: int,
    nz: int,
    total_load: float,
    *,
    component: int = 0,
    tributary: bool = False,
    surface_consistent: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    face_nodes = np.array([_node_id(nx, j, k, ny, nz) for j in range(ny + 1) for k in range(nz + 1)], dtype=np.int64)
    if surface_consistent:
        # Integrate the uniform traction with the bilinear Q4 face shape
        # functions.  On each rectangular face cell this gives one quarter
        # of the resultant to each corner, without privileging a diagonal.
        weights = np.zeros(face_nodes.size, dtype=float)
        for j in range(ny):
            for k in range(nz):
                local = (j * (nz + 1) + k, (j + 1) * (nz + 1) + k,
                         (j + 1) * (nz + 1) + k + 1, j * (nz + 1) + k + 1)
                for index in local:
                    weights[index] += 0.25
        weights /= np.sum(weights)
    elif tributary:
        weights = np.asarray(
            [
                (0.5 if j in (0, ny) else 1.0) * (0.5 if k in (0, nz) else 1.0)
                for j in range(ny + 1)
                for k in range(nz + 1)
            ],
            dtype=float,
        )
        weights /= np.sum(weights)
    else:
        weights = np.full(face_nodes.size, 1.0 / max(face_nodes.size, 1), dtype=float)
    return face_nodes, np.full(face_nodes.size, component, dtype=np.int8), float(total_load) * weights
