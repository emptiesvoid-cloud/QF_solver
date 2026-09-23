"""Bounded WP11 linear-static element-family extension.

The legacy WP11 route remains TET4-only.  This module is an additive bridge
for small, homogeneous element-family cases used to verify that the existing
solid kernels can be exercised through the PETSc/MPI backend envelope.

It intentionally does not modify ``LargeModel`` or the legacy TET4 assembly
path.  The extension is bounded: one canonical element per case, replicated
input, root-side reference assembly, and no scaling claim.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import spsolve

from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel
from solveur.elements.registry import ElementRegistry
from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.hex20 import Hex20Element
from solveur.elements.solid.tet10 import Tet10Element


SUPPORTED_WP11_FAMILIES = ("TET4", "HEX8", "TET10", "HEX20")
MATERIAL = {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7_800.0}
TOTAL_LOAD = -1_000.0


@dataclass(frozen=True)
class LinearSystem:
    """Assembled unconstrained system and the constrained DOF indices."""

    stiffness: csr_matrix
    loads: np.ndarray
    fixed: np.ndarray


def normalize_family(value: str) -> str:
    """Return a supported WP11 family name or fail closed."""

    family = str(value).strip().upper()
    if family not in SUPPORTED_WP11_FAMILIES:
        allowed = ", ".join(SUPPORTED_WP11_FAMILIES)
        raise ValueError(f"Unsupported WP11 family {value!r}; allowed: {allowed}.")
    return family


def build_wp11_family_model(family: str) -> FiniteElementModel:
    """Build the canonical homogeneous static case for one element family."""

    normalized = normalize_family(family)
    coordinates, connectivity = _canonical_geometry(normalized)
    fixed_nodes = np.flatnonzero(coordinates[:, 0] <= 1.0e-14).tolist()
    load_nodes = np.flatnonzero(coordinates[:, 0] >= 1.0 - 1.0e-14).tolist()
    if not fixed_nodes or not load_nodes:
        raise ValueError(f"Canonical {normalized} geometry has no fixed or loaded face nodes.")
    nodal_load = TOTAL_LOAD / float(len(load_nodes))
    return FiniteElementModel.from_raw(
        nodes=coordinates.tolist(),
        elements=[{"type": normalized, "nodes": connectivity[0].tolist(), "material": "solid"}],
        materials={"solid": dict(MATERIAL)},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=[{"node": int(node), "dof": "UZ", "value": nodal_load} for node in load_nodes],
        analysis={"type": "linear_static", "method": "cg", "parameters": {"rtol": 1.0e-12, "max_it": 10_000}},
        units={"system": "SI"},
        verification_profile="wp11_multifamily_bounded",
    )


def assemble_linear_system(model: FiniteElementModel) -> LinearSystem:
    """Assemble the family case with the existing standard element kernels."""

    dofs = model.dof_manager()
    assembler = GlobalAssembler(chunk_size=1)
    stiffness = assembler.assemble_stiffness(model, dofs).tocsr()
    loads = np.asarray(assembler.assemble_loads(model, dofs), dtype=float)
    fixed = np.asarray(assembler.fixed_indices(model, dofs), dtype=np.int64)
    return LinearSystem(stiffness=stiffness, loads=loads, fixed=fixed)


def solve_linear_system(system: LinearSystem) -> tuple[np.ndarray, dict[str, Any]]:
    """Solve the constrained system with SciPy and return observables."""

    matrix = system.stiffness
    fixed = np.asarray(system.fixed, dtype=np.int64)
    rhs = np.asarray(system.loads, dtype=float).copy()
    constrained = lil_matrix(matrix, copy=True)
    if fixed.size:
        constrained[fixed, :] = 0.0
        constrained[:, fixed] = 0.0
        constrained[fixed, fixed] = 1.0
        rhs[fixed] = 0.0
    displacement = np.asarray(spsolve(constrained.tocsr(), rhs), dtype=float)
    return displacement, linear_observables(system, displacement)


def linear_observables(system: LinearSystem, displacement: np.ndarray) -> dict[str, Any]:
    """Calculate deterministic diagnostics from a raw displacement vector."""

    values = np.asarray(displacement, dtype=float)
    if values.shape != (system.stiffness.shape[0],) or not np.all(np.isfinite(values)):
        raise ValueError("WP11 displacement vector has an invalid shape or non-finite values.")
    residual = np.asarray(system.stiffness @ values - system.loads, dtype=float)
    free_mask = np.ones(values.size, dtype=bool)
    free_mask[system.fixed] = False
    reaction = residual[system.fixed]
    load_norm = max(float(np.linalg.norm(system.loads)), 1.0)
    free_residual = residual[free_mask]
    return {
        "dof_count": int(values.size),
        "displacement_l2": float(np.linalg.norm(values)),
        "displacement_inf": float(np.max(np.abs(values), initial=0.0)),
        "free_residual_l2": float(np.linalg.norm(free_residual)),
        "free_residual_inf": float(np.max(np.abs(free_residual), initial=0.0)),
        "free_residual_relative_l2": float(np.linalg.norm(free_residual) / load_norm),
        "reaction_l2": float(np.linalg.norm(reaction)),
        "reaction_inf": float(np.max(np.abs(reaction), initial=0.0)),
        "energy": float(0.5 * values @ (system.stiffness @ values)),
        "load_l2": float(np.linalg.norm(system.loads)),
        "fixed_dof_count": int(system.fixed.size),
        "finite": True,
    }


def model_fingerprint(model: FiniteElementModel) -> str:
    """Hash the canonical model inputs without depending on JSON formatting."""

    payload = {
        "nodes": np.asarray(model.nodes, dtype=np.float64).tolist(),
        "elements": [
            {"type": item.type, "nodes": list(item.nodes), "material": item.material}
            for item in model.elements
        ],
        "materials": model.materials,
        "fixed_dofs": [{"node": item.node, "dofs": list(item.dofs)} for item in model.fixed_dofs],
        "loads": [{"node": item.node, "dof": item.dof, "value": item.value} for item in model.loads],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def displacement_fingerprint(displacement: np.ndarray) -> str:
    """Hash a displacement vector using a canonical float64 representation."""

    values = np.asarray(displacement, dtype=np.float64)
    digest = hashlib.sha256()
    digest.update(np.asarray(values.shape, dtype=np.int64).tobytes())
    digest.update(values.tobytes(order="C"))
    return digest.hexdigest()


def _canonical_geometry(family: str) -> tuple[np.ndarray, np.ndarray]:
    if family == "TET4":
        return (
            np.asarray(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))),
            np.asarray(((0, 1, 2, 3),), dtype=np.int64),
        )
    if family == "TET10":
        corners = np.asarray(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))
        tet_mids = np.asarray(
            [0.5 * (corners[first] + corners[second]) for first, second, _ in Tet10Element.edge_nodes]
        )
        return np.vstack((corners, tet_mids)), np.asarray((tuple(range(10)),), dtype=np.int64)
    corners = np.asarray(
        [0.5 * (np.asarray(signs, dtype=float) + 1.0) for signs in Hex8Element.node_signs],
        dtype=float,
    )
    if family == "HEX8":
        return corners, np.asarray((tuple(range(8)),), dtype=np.int64)
    edge_mids: list[np.ndarray] = []
    for free_axis, fixed_axes, fixed_signs in Hex20Element.edge_data:
        signs_a: np.ndarray = np.zeros(3, dtype=float)
        signs_b: np.ndarray = np.zeros(3, dtype=float)
        for axis, sign in zip(fixed_axes, fixed_signs, strict=True):
            signs_a[axis] = sign
            signs_b[axis] = sign
        signs_a[free_axis] = -1.0
        signs_b[free_axis] = 1.0
        first = int(np.flatnonzero(np.all(Hex8Element.node_signs == signs_a, axis=1))[0])
        second = int(np.flatnonzero(np.all(Hex8Element.node_signs == signs_b, axis=1))[0])
        edge_mids.append(0.5 * (corners[first] + corners[second]))
    return np.vstack((corners, np.asarray(edge_mids))), np.asarray((tuple(range(20)),), dtype=np.int64)


def family_node_count(family: str) -> int:
    """Return the registry node count for a supported family."""

    return int(ElementRegistry.get(normalize_family(family)).node_count)
