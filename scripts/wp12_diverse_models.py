"""Prospective WP12 model catalog with non-prismatic 3D topologies.

This additive catalog leaves the frozen R3.5 generator untouched. It reuses
its element conventions and consistent face-traction integration while
removing structured cells to create stepped, re-entrant, and perforated solid
models for a future external-correlation revision.
"""

from __future__ import annotations

import re

import numpy as np

from solveur.core.model import FiniteElementModel
from solveur.large.multifamily import assemble_linear_system

from scripts.run_wp12_expanded_code_aster import _comm_text as _r3_comm_text
from scripts.run_wp12_expanded_code_aster import _mesh_text as _r3_mesh_text
from scripts.wp12_expanded_models import (
    FAMILIES,
    LOADS,
    MATERIAL,
    ExpandedCase,
    _equivalent_nodal_loads,
    _hex_connectivity,
    _tet_connectivity,
    model_fingerprint,
)


GEOMETRIES: dict[str, tuple[float, float, float]] = {
    "l_section_beam": (2.0, 1.0, 1.0),
    "perforated_prism": (2.0, 1.0, 1.0),
    "stepped_cantilever": (2.0, 1.0, 1.0),
}

MESHES_BY_GEOMETRY: dict[str, dict[str, tuple[int, int, int]]] = {
    # Keep each cross-section fixed within its geometry so H1/H2/H3 sample the
    # same physical solid. Refinement is axial only for these correlation
    # families; this is not presented as an isotropic mesh-convergence study.
    "l_section_beam": {"H1": (1, 3, 3), "H2": (2, 3, 3), "H3": (4, 3, 3)},
    "perforated_prism": {"H1": (1, 3, 3), "H2": (2, 3, 3), "H3": (4, 3, 3)},
    "stepped_cantilever": {"H1": (2, 2, 2), "H2": (4, 2, 2), "H3": (8, 2, 2)},
}

EXPECTED_VOLUME_FRACTION = {
    "l_section_beam": 5.0 / 9.0,
    "perforated_prism": 8.0 / 9.0,
    "stepped_cantilever": 5.0 / 8.0,
}
END_FACE_AREA_FRACTION = {
    "l_section_beam": 5.0 / 9.0,
    "perforated_prism": 8.0 / 9.0,
    "stepped_cantilever": 1.0 / 4.0,
}


def _active_cell(geometry: str, i: int, j: int, k: int, divisions: tuple[int, int, int]) -> bool:
    nx, ny, nz = divisions
    if geometry == "l_section_beam":
        arm_y, arm_z = ny // 3, nz // 3
        return j < arm_y or k < arm_z
    if geometry == "perforated_prism":
        hole_y = ny // 3 <= j < 2 * ny // 3
        hole_z = nz // 3 <= k < 2 * nz // 3
        return not (hole_y and hole_z)
    if geometry == "stepped_cantilever":
        return i < nx // 2 or (j < ny // 2 and k < nz // 2)
    raise ValueError(f"Unknown diverse WP12 geometry {geometry!r}.")


def mesh_for_case(
    family: str, geometry: str, mesh: str
) -> tuple[np.ndarray, np.ndarray, tuple[float, float, float], tuple[int, int, int]]:
    family = family.upper()
    if family not in FAMILIES or geometry not in GEOMETRIES or mesh not in MESHES_BY_GEOMETRY[geometry]:
        raise ValueError("Unknown family, diverse geometry, or mesh in WP12 case.")
    dimensions = GEOMETRIES[geometry]
    divisions = MESHES_BY_GEOMETRY[geometry][mesh]
    if family in {"HEX8", "HEX20"}:
        coordinates, full_connectivity = _hex_connectivity(family, dimensions, divisions)
    else:
        coordinates, full_connectivity = _tet_connectivity(family, dimensions, divisions)

    active = np.asarray(
        [
            _active_cell(geometry, i, j, k, divisions)
            for i in range(divisions[0])
            for j in range(divisions[1])
            for k in range(divisions[2])
        ],
        dtype=bool,
    )
    if family.startswith("TET"):
        active = np.repeat(active, 6)
    if active.shape != (len(full_connectivity),) or not np.any(active):
        raise ValueError("Diverse WP12 cell mask does not align with generated connectivity.")
    connectivity = np.asarray(full_connectivity[active], dtype=np.int64)

    used_nodes = np.unique(connectivity)
    remap: np.ndarray = np.full(len(coordinates), -1, dtype=np.int64)
    remap[used_nodes] = np.arange(used_nodes.size, dtype=np.int64)
    coordinates = np.asarray(coordinates, dtype=np.float64)[used_nodes]
    connectivity = remap[connectivity]
    if np.any(connectivity < 0):
        raise ValueError("Diverse WP12 connectivity compaction produced an invalid node index.")
    return coordinates, connectivity, dimensions, divisions


def build_case(family: str, geometry: str, mesh: str, load_case: str) -> ExpandedCase:
    family = family.upper()
    if load_case not in LOADS:
        raise ValueError(f"Unknown load case {load_case!r}.")
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
        materials={"solid": dict(MATERIAL)},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=loads,
        analysis={"type": "linear_static", "method": "direct"},
        units={"system": "SI"},
        verification_profile="wp12_diverse_linear_static_correlation_r3_6",
    )
    system = assemble_linear_system(model)
    fingerprint = model_fingerprint(family, coordinates, connectivity, system.fixed, system.loads, MATERIAL)
    case_id = f"{family.lower()}_{geometry.lower()}_{mesh.lower()}_{load_case.lower()}"
    return ExpandedCase(
        case_id=case_id,
        family=family,
        geometry=geometry,
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


def case_catalog() -> list[ExpandedCase]:
    return [
        build_case(family, geometry, mesh, load_case)
        for family in FAMILIES
        for geometry in GEOMETRIES
        for mesh in MESHES_BY_GEOMETRY[geometry]
        for load_case in LOADS
    ]


_ASTER_NODE_PREFIXES = "ABCDEFGHIJKLMOPQRSTUVWXYZ"  # Keep N reserved for legacy N<number> labels.
_ASTER_NODE_SUFFIXES = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _compact_aster_node_name(index: int) -> str:
    """Return a deterministic two-character, letter-prefixed ASTER node name."""
    if index < 0 or index >= len(_ASTER_NODE_PREFIXES) * len(_ASTER_NODE_SUFFIXES):
        raise ValueError("Compact ASTER node labels support indices 0 through 899.")
    prefix = _ASTER_NODE_PREFIXES[index // len(_ASTER_NODE_SUFFIXES)]
    return f"{prefix}{_ASTER_NODE_SUFFIXES[index % len(_ASTER_NODE_SUFFIXES)]}"


def _compact_aster_node_labels(text: str) -> str:
    """Compact the legacy N<number> labels without changing records or values."""

    def replace(match: re.Match[str]) -> str:
        return _compact_aster_node_name(int(match.group(1)) - 1)

    return re.sub(r"\bN([1-9][0-9]*)\b", replace, text)


def code_aster_mesh_text(case: ExpandedCase) -> str:
    """Serialize this prospective catalog case within ASTER's 80-column limit."""
    return _compact_aster_node_labels(_r3_mesh_text(case))


def code_aster_command_text(case: ExpandedCase) -> str:
    """Serialize matching compact node references in the ASTER command file."""
    return _compact_aster_node_labels(_r3_comm_text(case))
