"""Deterministic WP12 gallery of additional 3D solid correlation models.

This additive catalog expands topology and elastic-material coverage while
reusing the frozen element conventions and traction integration from R3.6.
It is validation tooling only and does not alter production solver mechanics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from solveur.core.model import FiniteElementModel
from solveur.large.multifamily import assemble_linear_system

from scripts.wp12_expanded_models import (
    FAMILIES,
    LOADS,
    _equivalent_nodal_loads,
    _hex_connectivity,
    _tet_connectivity,
    model_fingerprint,
)


GEOMETRIES: dict[str, tuple[float, float, float]] = {
    "triangular_prism": (2.0, 1.0, 1.0),
    "tee_section_beam": (2.0, 1.0, 1.0),
    "i_section_beam": (2.0, 1.0, 1.0),
    "channel_section_beam": (2.0, 1.0, 1.0),
    "box_tube_beam": (2.0, 1.0, 1.0),
    "cruciform_beam": (2.0, 1.0, 1.0),
}
MESHES_BY_GEOMETRY: dict[str, dict[str, tuple[int, int, int]]] = {
    geometry: {"H1": (1, 5, 5), "H2": (2, 5, 5), "H3": (4, 5, 5)}
    for geometry in GEOMETRIES
}
MATERIALS: dict[str, dict[str, float | str]] = {
    "steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.30, "density": 7800.0},
    "aluminum": {"type": "isotropic_3d", "E": 69.0e9, "nu": 0.33, "density": 2700.0},
    "polymer": {"type": "isotropic_3d", "E": 3.2e9, "nu": 0.38, "density": 1200.0},
}
@dataclass(frozen=True)
class GalleryCase:
    case_id: str
    family: str
    geometry: str
    material_variant: str
    material: dict[str, float | str]
    dimensions: tuple[float, float, float]
    mesh: str
    divisions: tuple[int, int, int]
    load_case: str
    resultant: tuple[float, float, float]
    model: Any
    system: Any
    connectivity: np.ndarray
    fingerprint: str
    load_area: float
    load_moment: tuple[float, float, float]


def _active_cross_section_cell(geometry: str, j: int, k: int) -> bool:
    if geometry == "triangular_prism":
        return j + k <= 4
    if geometry == "tee_section_beam":
        return j == 2 or k == 4
    if geometry == "i_section_beam":
        return j == 2 or k in (0, 4)
    if geometry == "channel_section_beam":
        return j == 0 or k in (0, 4)
    if geometry == "box_tube_beam":
        return j in (0, 4) or k in (0, 4)
    if geometry == "cruciform_beam":
        return j == 2 or k == 2
    raise ValueError(f"Unknown WP12 gallery geometry {geometry!r}.")


def active_cell_mask(geometry: str, divisions: tuple[int, int, int]) -> np.ndarray:
    """Return the exact voxel mask, repeated along x for one frozen topology."""
    nx, ny, nz = divisions
    if (ny, nz) != (5, 5):
        raise ValueError("WP12 gallery cross-sections are frozen to a 5x5 cell grid.")
    section = np.asarray(
        [[_active_cross_section_cell(geometry, j, k) for k in range(nz)] for j in range(ny)],
        dtype=bool,
    )
    if not np.any(section):
        raise ValueError(f"{geometry}: frozen cross-section is empty.")
    return np.tile(section.reshape(1, -1), nx).reshape(-1)


def mesh_for_case(
    family: str, geometry: str, mesh: str
) -> tuple[np.ndarray, np.ndarray, tuple[float, float, float], tuple[int, int, int]]:
    family = family.upper()
    if family not in FAMILIES or geometry not in GEOMETRIES or mesh not in MESHES_BY_GEOMETRY[geometry]:
        raise ValueError("Unknown WP12 gallery element family, geometry, or mesh.")
    dimensions = GEOMETRIES[geometry]
    divisions = MESHES_BY_GEOMETRY[geometry][mesh]
    if family.startswith("HEX"):
        coordinates, full_connectivity = _hex_connectivity(family, dimensions, divisions)
    else:
        coordinates, full_connectivity = _tet_connectivity(family, dimensions, divisions)
    active = active_cell_mask(geometry, divisions)
    if family.startswith("TET"):
        active = np.repeat(active, 6)
    if active.shape != (len(full_connectivity),) or not np.any(active):
        raise ValueError("WP12 gallery cell mask does not align with generated connectivity.")
    connectivity = np.asarray(full_connectivity[active], dtype=np.int64)
    used_nodes = np.unique(connectivity)
    remap: np.ndarray = np.full(len(coordinates), -1, dtype=np.int64)
    remap[used_nodes] = np.arange(used_nodes.size, dtype=np.int64)
    coordinates = np.asarray(coordinates, dtype=np.float64)[used_nodes]
    connectivity = remap[connectivity]
    if np.any(connectivity < 0) or np.unique(connectivity).size != used_nodes.size:
        raise ValueError("WP12 gallery node compaction produced an invalid mesh.")
    return coordinates, connectivity, dimensions, divisions


def build_case(
    family: str,
    geometry: str,
    material_variant: str,
    mesh: str,
    load_case: str,
) -> GalleryCase:
    family = family.upper()
    if material_variant not in MATERIALS:
        raise ValueError(f"Unknown WP12 gallery material {material_variant!r}.")
    if load_case not in LOADS:
        raise ValueError(f"Unknown WP12 gallery load case {load_case!r}.")
    material = dict(MATERIALS[material_variant])
    coordinates, connectivity, dimensions, divisions = mesh_for_case(family, geometry, mesh)
    resultant = LOADS[load_case]
    nodal_loads, load_area, load_moment = _equivalent_nodal_loads(
        family, coordinates, connectivity, dimensions, resultant
    )
    fixed_nodes = np.flatnonzero(np.isclose(coordinates[:, 0], 0.0, rtol=0.0, atol=1.0e-12))
    if fixed_nodes.size == 0:
        raise ValueError(f"{geometry}: fixed root plane is empty.")
    elements = [{"type": family, "nodes": row.tolist(), "material": "solid"} for row in connectivity]
    loads = [
        {"node": int(node), "dof": dof, "value": float(nodal_loads[node, axis])}
        for node in range(len(coordinates))
        for axis, dof in enumerate(("UX", "UY", "UZ"))
        if nodal_loads[node, axis] != 0.0
    ]
    model = FiniteElementModel.from_raw(
        nodes=coordinates.tolist(),
        elements=elements,
        materials={"solid": material},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=loads,
        analysis={"type": "linear_static", "method": "direct"},
        units={"system": "SI"},
        verification_profile="wp12_gallery_linear_static_correlation_r4",
    )
    system = assemble_linear_system(model)
    fingerprint = model_fingerprint(family, coordinates, connectivity, system.fixed, system.loads, material)
    case_id = f"{family.lower()}_{geometry}_{material_variant}_{mesh.lower()}_{load_case.lower()}"
    return GalleryCase(
        case_id=case_id,
        family=family,
        geometry=geometry,
        material_variant=material_variant,
        material=material,
        dimensions=dimensions,
        mesh=mesh,
        divisions=divisions,
        load_case=load_case,
        resultant=resultant,
        model=model,
        system=system,
        connectivity=connectivity,
        fingerprint=fingerprint,
        load_area=load_area,
        load_moment=load_moment,
    )


def case_matrix() -> list[tuple[str, str, str, str, str]]:
    return [
        (family, geometry, material, mesh, load_case)
        for family in FAMILIES
        for geometry in GEOMETRIES
        for material in MATERIALS
        for mesh in MESHES_BY_GEOMETRY[geometry]
        for load_case in LOADS
    ]


def case_catalog() -> list[GalleryCase]:
    return [build_case(*row) for row in case_matrix()]


def topology_summary() -> dict[str, int]:
    return {
        geometry: int(np.count_nonzero(active_cell_mask(geometry, (1, 5, 5))))
        for geometry in GEOMETRIES
    }
