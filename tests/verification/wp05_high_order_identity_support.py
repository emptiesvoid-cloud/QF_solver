"""Controlled, production-independent WP05-A/B identity fixtures."""

from __future__ import annotations

from typing import Any

import numpy as np

from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.assembly.geometric import build_total_lagrangian_assembly
from solveur.core.model import FiniteElementModel
from solveur.materials.solid import SolidMaterial


MATERIAL_E = 1.0
MATERIAL_NU = 0.3


def tet10_coordinates() -> np.ndarray:
    """Return the canonical straight-sided unit TET10 coordinates."""

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
        ],
        dtype=float,
    )


def hex20_coordinates() -> np.ndarray:
    """Return the canonical unit HEX20 coordinates in Gmsh order."""

    corners: np.ndarray = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
        ],
        dtype=float,
    )
    edge_pairs = (
        (0, 1),
        (0, 3),
        (0, 4),
        (1, 2),
        (1, 5),
        (2, 3),
        (2, 6),
        (3, 7),
        (4, 5),
        (4, 7),
        (5, 6),
        (6, 7),
    )
    return np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in edge_pairs]])


def coordinates_for_family(family: str) -> np.ndarray:
    """Return canonical coordinates for one supported high-order family."""

    normalized = family.upper()
    if normalized == "TET10":
        return tet10_coordinates()
    if normalized == "HEX20":
        return hex20_coordinates()
    raise ValueError(f"Unsupported WP05 family {family!r}.")


def material() -> SolidMaterial:
    """Use unit modulus so frozen scaled identity bounds remain transparent."""

    return SolidMaterial(E=MATERIAL_E, nu=MATERIAL_NU)


def model_for_family(
    family: str,
    *,
    analysis_type: str = "geometric_nonlinear_static",
    loads: list[dict[str, Any]] | None = None,
    fixed_dofs: list[dict[str, Any]] | None = None,
    parameters: dict[str, Any] | None = None,
) -> FiniteElementModel:
    """Build a one-element model without invoking production file I/O."""

    normalized = family.upper()
    nodes = coordinates_for_family(normalized)
    method = "direct" if analysis_type == "linear_static" else "newton_raphson"
    analysis: dict[str, Any] = {
        "type": analysis_type,
        "method": method,
        "parameters": dict(parameters or {}),
    }
    if analysis_type == "geometric_nonlinear_static":
        analysis["parameters"].setdefault("load_increments", 6)
        analysis["parameters"].setdefault("tolerance", 1.0e-8)
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": normalized, "nodes": list(range(len(nodes))), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": MATERIAL_E, "nu": MATERIAL_NU}},
        fixed_dofs=fixed_dofs,
        loads=loads,
        analysis=analysis,
    )


def tl_assembly(family: str, *, nonlinear_quadrature: str = "hammer4") -> Any:
    """Build the existing high-order TL assembly used by both identity tests."""

    parameters = {"tet10_nonlinear_quadrature": nonlinear_quadrature}
    return build_total_lagrangian_assembly(model_for_family(family, parameters=parameters))


def affine_deformation_gradient() -> np.ndarray:
    """Frozen nontrivial affine deformation used by both families."""

    return np.asarray(
        [[1.04, 0.03, 0.0], [0.0, 0.98, 0.02], [0.0, 0.0, 1.01]],
        dtype=float,
    )


def affine_displacement(coordinates: np.ndarray, deformation: np.ndarray) -> np.ndarray:
    """Interpolate ``u = (F-I)X`` at every high-order node."""

    return (np.asarray(coordinates) @ (np.asarray(deformation) - np.eye(3)).T).reshape(-1)


def rotation_matrix(axis: np.ndarray, angle: float) -> np.ndarray:
    """Return a proper Rodrigues rotation for a non-infinitesimal test."""

    unit_axis = np.asarray(axis, dtype=float)
    unit_axis = unit_axis / np.linalg.norm(unit_axis)
    skew = np.asarray(
        [
            [0.0, -unit_axis[2], unit_axis[1]],
            [unit_axis[2], 0.0, -unit_axis[0]],
            [-unit_axis[1], unit_axis[0], 0.0],
        ]
    )
    return np.eye(3) + np.sin(angle) * skew + (1.0 - np.cos(angle)) * (skew @ skew)


def rigid_body_displacement(coordinates: np.ndarray, axis: np.ndarray, angle: float) -> np.ndarray:
    """Return nodal displacement induced by a proper finite rotation."""

    return affine_displacement(coordinates, rotation_matrix(axis, angle))


def stvk_oracle(deformation: np.ndarray) -> dict[str, np.ndarray | float]:
    """Evaluate the independent Green--Lagrange/StVK affine oracle."""

    deformation = np.asarray(deformation, dtype=float)
    green = 0.5 * (deformation.T @ deformation - np.eye(3))
    strain = np.asarray(
        [green[0, 0], green[1, 1], green[2, 2], 2.0 * green[0, 1], 2.0 * green[1, 2], 2.0 * green[0, 2]],
        dtype=float,
    )
    stress = material().elasticity_matrix @ strain
    return {
        "green": green,
        "strain": strain,
        "stress": stress,
        "energy_density": float(0.5 * strain @ stress),
    }


def finite_difference_step(displacement: np.ndarray) -> float:
    """Prospective central-difference step from machine epsilon and DOF scale."""

    scale = max(1.0, float(np.linalg.norm(np.asarray(displacement), ord=np.inf)))
    return float(np.cbrt(np.finfo(float).eps) * scale)


def energy_gradient_metrics(family: str) -> tuple[float, float]:
    """Return relative energy-gradient discrepancy and the declared step."""

    coordinates = coordinates_for_family(family)
    displacement = affine_displacement(coordinates, affine_deformation_gradient())
    assembly = tl_assembly(family)
    internal, _ = assembly.assemble(displacement)
    step = finite_difference_step(displacement)
    numerical = np.empty_like(internal)
    for index in range(internal.size):
        plus = displacement.copy()
        minus = displacement.copy()
        plus[index] += step
        minus[index] -= step
        numerical[index] = (assembly.strain_energy(plus) - assembly.strain_energy(minus)) / (2.0 * step)
    relative = float(np.linalg.norm(numerical - internal) / max(np.linalg.norm(internal), np.finfo(float).eps))
    return relative, step


def tangent_metrics(family: str) -> tuple[float, float, float, list[int]]:
    """Return full FD Frobenius, sampled-column, symmetry, and sampled DOFs."""

    coordinates = coordinates_for_family(family)
    displacement = affine_displacement(coordinates, affine_deformation_gradient())
    assembly = tl_assembly(family)
    internal, tangent = assembly.assemble(displacement)
    del internal
    assert tangent is not None
    matrix = tangent.toarray()
    step = finite_difference_step(displacement)
    numerical = np.empty_like(matrix)
    for index in range(matrix.shape[1]):
        plus = displacement.copy()
        minus = displacement.copy()
        plus[index] += step
        minus[index] -= step
        numerical[:, index] = (assembly.assemble(plus, tangent_required=False)[0] - assembly.assemble(minus, tangent_required=False)[0]) / (2.0 * step)
    frobenius = float(np.linalg.norm(matrix - numerical) / max(np.linalg.norm(numerical), np.finfo(float).eps))
    if family.upper() == "TET10":
        sampled = [*range(3), *range(12, 15)]
    else:
        sampled = [*range(3), *range(24, 27)]
    column_errors = [
        float(
            np.linalg.norm(matrix[:, index] - numerical[:, index])
            / max(np.linalg.norm(numerical[:, index]), np.finfo(float).eps)
        )
        for index in sampled
    ]
    symmetry = float(np.linalg.norm(matrix - matrix.T) / max(np.linalg.norm(matrix), np.finfo(float).eps))
    return frobenius, max(column_errors), symmetry, sampled


def structural_model(family: str, analysis_type: str, load: float) -> FiniteElementModel:
    """Build the tiny end-loaded fixture for the small-displacement limit."""

    coordinates = coordinates_for_family(family)
    fixed_nodes = np.flatnonzero(np.isclose(coordinates[:, 0], 0.0))
    loaded_nodes = np.flatnonzero(np.isclose(coordinates[:, 0], 1.0))
    fixed = [{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes]
    loads = [
        {"node": int(node), "dof": "UX", "value": float(load / len(loaded_nodes))}
        for node in loaded_nodes
    ]
    parameters = {"load_increments": 6, "tolerance": 1.0e-8}
    return model_for_family(
        family,
        analysis_type=analysis_type,
        loads=loads,
        fixed_dofs=fixed,
        parameters=parameters,
    )


def external_load_vector(model: FiniteElementModel) -> tuple[Any, np.ndarray, np.ndarray]:
    """Return DOF manager, load vector, and fixed indices for reaction checks."""

    dofs = model.dof_manager()
    loads = np.zeros(dofs.ndof, dtype=float)
    for load in model.loads:
        loads[dofs.index(load.node, load.dof)] += load.value
    fixed = np.unique(
        [dofs.index(condition.node, name) for condition in model.fixed_dofs for name in condition.dofs]
    )
    return dofs, loads, fixed


def linear_reaction(model: FiniteElementModel, displacement: np.ndarray) -> np.ndarray:
    """Recover fixed reactions from the linear production stiffness."""

    dofs, loads, fixed = external_load_vector(model)
    internal = GlobalAssembler().assemble_stiffness(model, dofs) @ displacement
    reaction = internal - loads
    return reaction[fixed]


def tl_reaction(model: FiniteElementModel, displacement: np.ndarray) -> np.ndarray:
    """Recover fixed reactions from the TL internal-force assembly."""

    _, loads, fixed = external_load_vector(model)
    internal = build_total_lagrangian_assembly(model).assemble(displacement, tangent_required=False)[0]
    return (internal - loads)[fixed]
