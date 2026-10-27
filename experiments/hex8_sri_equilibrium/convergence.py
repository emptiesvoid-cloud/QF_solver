"""Sparse HEX8/SRI convergence campaign driver.

``run_convergence_case`` performs a global FEM assembly and solve. It must only
be called by the exact test node after official-controller and manifest checks.
Mesh generation, consistent face-load construction and metadata are safe to
exercise in synthetic unit tests without invoking that FEM path.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
from typing import Any

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.linalg import LinearOperator, norm as sparse_norm, onenormest, splu

from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.hex8_sri import Hex8SRIElement
from solveur.materials.solid import SolidMaterial

from .beam_oracle import timoshenko_cantilever_tip
from .campaign_spec import (
    DEPTH_Z_M,
    FORMULATIONS,
    LENGTH_M,
    MESH_LEVELS,
    POISSON_RATIOS,
    TRACTION_Z_PA,
    WIDTH_Y_M,
    YOUNG_MODULUS_PA,
)
from .campaign import HistoricalHex8SRIElement
from .criteria_contract import negative_mean_loaded_face_uz_verdict


@dataclass(frozen=True)
class StructuredHexMesh:
    """Structured affine hex mesh and its exact xyz division counts."""

    nodes_m: np.ndarray
    connectivity: np.ndarray
    divisions_xyz: tuple[int, int, int]


def structured_hex_mesh(
    nx: int,
    ny: int,
    nz: int,
    *,
    length_m: float = LENGTH_M,
    width_y_m: float = WIDTH_Y_M,
    depth_z_m: float = DEPTH_Z_M,
) -> StructuredHexMesh:
    """Generate an affine structured HEX8 mesh without assembling stiffness."""
    divisions = (int(nx), int(ny), int(nz))
    if any(n < 1 for n in divisions):
        raise ValueError("each mesh division count must be a positive integer")
    dimensions = (float(length_m), float(width_y_m), float(depth_z_m))
    if any(not np.isfinite(value) or value <= 0.0 for value in dimensions):
        raise ValueError("all geometry dimensions must be finite and positive")
    nx, ny, nz = divisions
    length, width, depth = dimensions
    nodes = np.asarray(
        [
            (length * ix / nx, width * iy / ny, depth * iz / nz)
            for ix in range(nx + 1)
            for iy in range(ny + 1)
            for iz in range(nz + 1)
        ],
        dtype=np.float64,
    )
    offsets = (
        (0, 0, 0),
        (1, 0, 0),
        (1, 1, 0),
        (0, 1, 0),
        (0, 0, 1),
        (1, 0, 1),
        (1, 1, 1),
        (0, 1, 1),
    )
    connectivity = np.empty((nx * ny * nz, 8), dtype=np.int64)
    element_index = 0
    for ix in range(nx):
        for iy in range(ny):
            for iz in range(nz):
                connectivity[element_index] = [
                    ((ix + dx) * (ny + 1) + iy + dy) * (nz + 1) + iz + dz for dx, dy, dz in offsets
                ]
                element_index += 1
    return StructuredHexMesh(nodes, connectivity, divisions)


def _normalized_linear_face_weights(divisions: int) -> np.ndarray:
    """Integrate 1-D linear shape functions over a uniform boundary mesh."""
    if divisions < 1:
        raise ValueError("face divisions must be positive")
    weights = np.ones(divisions + 1, dtype=np.float64)
    weights[[0, -1]] = 0.5
    return weights / divisions


def consistent_end_face_load(
    mesh: StructuredHexMesh,
    *,
    traction_z_pa: float = TRACTION_Z_PA,
    width_y_m: float = WIDTH_Y_M,
    depth_z_m: float = DEPTH_Z_M,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return consistent nodal force, end-face node IDs, and area weights."""
    nx, ny, nz = mesh.divisions_xyz
    traction = float(traction_z_pa)
    area = float(width_y_m) * float(depth_z_m)
    if not np.isfinite(traction) or not np.isfinite(area) or area <= 0.0:
        raise ValueError("traction must be finite and loaded face area positive")
    wy = _normalized_linear_face_weights(ny)
    wz = _normalized_linear_face_weights(nz)
    nodes_per_x = (ny + 1) * (nz + 1)
    loaded_nodes = np.asarray(
        [nx * nodes_per_x + iy * (nz + 1) + iz for iy in range(ny + 1) for iz in range(nz + 1)],
        dtype=np.int64,
    )
    face_weights = np.asarray([wy[iy] * wz[iz] for iy in range(ny + 1) for iz in range(nz + 1)])
    force = np.zeros(mesh.nodes_m.shape[0] * 3, dtype=np.float64)
    force[3 * loaded_nodes + 2] = traction * area * face_weights
    return force, loaded_nodes, face_weights


def _dof_indices(node_ids: np.ndarray) -> np.ndarray:
    return (3 * node_ids[:, None] + np.arange(3, dtype=np.int64)).reshape(-1)


def _element_class(formulation: str):
    if formulation == "hex8_standard":
        return Hex8Element
    if formulation == "sri_historical":
        return HistoricalHex8SRIElement
    if formulation == "sri_corrected":
        return Hex8SRIElement
    raise ValueError(f"unknown HEX8-SRI formulation: {formulation}")


def _sparse_one_norm_condition_estimate(matrix: csr_matrix, factorization: Any) -> float:
    """Estimate cond_1(Kff) from the matrix and its LU inverse operator.

    This is not an eigensolve. The estimate shares the sparse factorization
    already used for the static solve and is recorded as an estimate, not an
    acceptance gate.
    """
    inverse = LinearOperator(
        matrix.shape,
        matvec=factorization.solve,
        rmatvec=lambda vector: factorization.solve(vector, trans="T"),
        dtype=np.float64,
    )
    return float(onenormest(matrix) * onenormest(inverse))


def run_convergence_case(
    formulation: str,
    poisson_ratio: float,
    divisions_xyz: tuple[int, int, int],
    *,
    criteria: dict[str, float],
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Assemble and solve a single registered convergence FEM case."""
    if os.environ.get("QF_DEVELOPMENT_AUTONOMOUS") != "1":
        raise PermissionError("convergence FEM is only callable inside the official controller child")
    if formulation not in FORMULATIONS or divisions_xyz not in MESH_LEVELS:
        raise ValueError("unregistered formulation or mesh level")
    if poisson_ratio not in POISSON_RATIOS:
        raise ValueError("this first campaign is limited to ν=0.3 and ν=0.4999")

    from time import perf_counter

    mesh = structured_hex_mesh(*divisions_xyz)
    n_elements = mesh.connectivity.shape[0]
    ndof = mesh.nodes_m.shape[0] * 3
    element_dof_count = 24
    contributions_per_element = element_dof_count**2
    contribution_count = n_elements * contributions_per_element
    row_indices = np.empty(contribution_count, dtype=np.int32)
    column_indices = np.empty(contribution_count, dtype=np.int32)
    values = np.empty(contribution_count, dtype=np.float64)
    jacobian_determinants = np.empty((n_elements, 9), dtype=np.float64)
    gauss_strains = np.empty((n_elements, 8, 6), dtype=np.float64)

    material = SolidMaterial(E=YOUNG_MODULUS_PA, nu=float(poisson_ratio))
    element = _element_class(formulation)(material)
    sample_points = ((0.0, 0.0, 0.0), *Hex8Element.integration_points)
    assembly_started = perf_counter()
    for element_index, node_ids in enumerate(mesh.connectivity):
        coordinates = mesh.nodes_m[node_ids]
        dofs = _dof_indices(node_ids)
        local_stiffness = element.stiffness(coordinates)
        offset = element_index * contributions_per_element
        row_indices[offset : offset + contributions_per_element] = np.repeat(dofs, element_dof_count)
        column_indices[offset : offset + contributions_per_element] = np.tile(dofs, element_dof_count)
        values[offset : offset + contributions_per_element] = local_stiffness.ravel()
        jacobian_determinants[element_index] = [
            Hex8Element.jacobian_determinant(coordinates, point) for point in sample_points
        ]
    assembly_seconds = perf_counter() - assembly_started

    stiffness = coo_matrix((values, (row_indices, column_indices)), shape=(ndof, ndof), dtype=np.float64).tocsr()
    stiffness.sum_duplicates()
    stiffness.eliminate_zeros()
    force, loaded_nodes, face_weights = consistent_end_face_load(mesh)
    fixed_nodes = np.arange((divisions_xyz[1] + 1) * (divisions_xyz[2] + 1), dtype=np.int64)
    fixed_dofs = _dof_indices(fixed_nodes)
    free_mask = np.ones(ndof, dtype=bool)
    free_mask[fixed_dofs] = False
    free_dofs = np.flatnonzero(free_mask)
    reduced = stiffness[free_dofs, :][:, free_dofs].tocsr()

    solve_started = perf_counter()
    factorization = splu(reduced.tocsc(), permc_spec="MMD_AT_PLUS_A")
    displacement = np.zeros(ndof, dtype=np.float64)
    displacement[free_dofs] = factorization.solve(force[free_dofs])
    solve_seconds = perf_counter() - solve_started

    post_started = perf_counter()
    for element_index, node_ids in enumerate(mesh.connectivity):
        coordinates = mesh.nodes_m[node_ids]
        local_displacement = displacement[_dof_indices(node_ids)]
        for point_index, point in enumerate(Hex8Element.integration_points):
            b_matrix, _determinant = Hex8Element.b_matrix(coordinates, point)
            gauss_strains[element_index, point_index] = b_matrix @ local_displacement
    residual = np.asarray(stiffness @ displacement - force)
    free_residual = residual[free_dofs]
    reactions = residual[fixed_dofs]
    displacement_nodes = displacement.reshape(-1, 3)
    face_displacement = displacement_nodes[loaded_nodes, 2]
    signed_mean_uz = float(face_weights @ face_displacement)
    internal_force = np.asarray(stiffness @ displacement)
    internal_energy = float(0.5 * displacement @ internal_force)
    external_work = float(displacement @ force)
    force_sum = force.reshape(-1, 3).sum(axis=0)
    reaction_nodes = np.zeros_like(displacement_nodes)
    reaction_nodes.reshape(-1)[fixed_dofs] = reactions
    reaction_sum = reaction_nodes.sum(axis=0)
    force_closure = force_sum + reaction_sum
    force_moment = np.cross(mesh.nodes_m, force.reshape(-1, 3)).sum(axis=0)
    reaction_moment = np.cross(mesh.nodes_m, reaction_nodes).sum(axis=0)
    moment_closure = force_moment + reaction_moment
    relative_residual = float(
        np.linalg.norm(free_residual)
        / max(np.linalg.norm(force[free_dofs]), np.linalg.norm(reduced @ displacement[free_dofs]), 1.0)
    )
    force_closure_relative = float(
        np.linalg.norm(force_closure) / max(np.linalg.norm(force_sum), np.linalg.norm(reaction_sum), 1.0)
    )
    moment_closure_relative = float(
        np.linalg.norm(moment_closure) / max(np.linalg.norm(force_moment), np.linalg.norm(reaction_moment), 1.0)
    )
    energy_identity_relative = (
        float(abs(2.0 * internal_energy - external_work) / abs(external_work)) if external_work != 0.0 else float("inf")
    )
    symmetry_relative = float(sparse_norm(stiffness - stiffness.T) / sparse_norm(stiffness))
    condition_estimate = _sparse_one_norm_condition_estimate(reduced, factorization)
    postprocess_seconds = perf_counter() - post_started

    beam = timoshenko_cantilever_tip(
        length_m=LENGTH_M,
        width_y_m=WIDTH_Y_M,
        depth_z_m=DEPTH_Z_M,
        young_modulus_pa=YOUNG_MODULUS_PA,
        poisson_ratio=poisson_ratio,
        transverse_resultant_n=TRACTION_Z_PA * WIDTH_Y_M * DEPTH_Z_M,
    )
    finite = all(
        bool(np.all(np.isfinite(array)))
        for array in (stiffness.data, displacement, residual, reactions, gauss_strains, jacobian_determinants)
    ) and all(
        math.isfinite(value)
        for value in (
            signed_mean_uz,
            internal_energy,
            external_work,
            relative_residual,
            force_closure_relative,
            moment_closure_relative,
            energy_identity_relative,
        )
    )
    jacobians_positive = bool(np.all(jacobian_determinants > 0.0))
    verdicts = {
        "finite_state": "PASS" if finite else "FAIL",
        "positive_sampled_jacobians_center_and_gauss": "PASS" if jacobians_positive else "FAIL",
        "free_residual": "PASS" if relative_residual <= criteria["free_residual_relative_max"] else "FAIL",
        "force_closure": "PASS" if force_closure_relative <= criteria["force_closure_relative_max"] else "FAIL",
        "moment_closure": "PASS" if moment_closure_relative <= criteria["moment_closure_relative_max"] else "FAIL",
        "energy_identity": "PASS" if energy_identity_relative <= criteria["energy_identity_relative_max"] else "FAIL",
        "negative_mean_loaded_face_uz": negative_mean_loaded_face_uz_verdict(signed_mean_uz),
        "independent_3d_reference_error": "NOT_ASSESSED_NO_QUALIFIED_ORACLE",
        "single_case_convergence": "NOT_ASSESSED_REQUIRES_PAIRED_LEVELS",
    }
    record = {
        "case": {
            "formulation": formulation,
            "poisson_ratio": float(poisson_ratio),
            "divisions_xyz": list(divisions_xyz),
            "element_count": int(n_elements),
            "node_count": int(mesh.nodes_m.shape[0]),
            "dof_count": int(ndof),
            "fixed_dof_count": int(fixed_dofs.size),
            "free_dof_count": int(free_dofs.size),
        },
        "units": {
            "displacement": "m",
            "strain": "dimensionless",
            "energy": "J",
            "force": "N",
            "moment": "N·m",
            "time": "s",
        },
        "observables": {
            "signed_mean_loaded_face_UZ_m": signed_mean_uz,
            "loaded_face_mean_definition": "consistent area-weighted Q1 face average",
            "timoshenko_trend_reference_m": beam.total_m,
            "timoshenko_relative_difference_not_error_m": float(abs(signed_mean_uz - beam.total_m) / abs(beam.total_m)),
            "max_abs_gauss_strain_dimensionless": float(np.max(np.abs(gauss_strains))),
            "internal_energy_J": internal_energy,
            "external_load_work_J": external_work,
            "energy_identity_relative": energy_identity_relative,
            "free_residual_l2_N": float(np.linalg.norm(free_residual)),
            "free_residual_relative": relative_residual,
            "support_reaction_resultant_N": reaction_sum.tolist(),
            "force_closure_N": force_closure.tolist(),
            "force_closure_relative": force_closure_relative,
            "moment_closure_Nm": moment_closure.tolist(),
            "moment_closure_relative": moment_closure_relative,
            "stiffness_symmetry_relative_frobenius": symmetry_relative,
            "condition_number_1_estimate_Kff": condition_estimate,
            "condition_estimator": "scipy.onenormest(A) * scipy.onenormest(LU-inverse operator); estimate, no eigensolve",
            "jacobian_determinants_center_then_gauss_m3": jacobian_determinants.tolist(),
            "timing_seconds": {
                "element_assembly": assembly_seconds,
                "sparse_global_solve": solve_seconds,
                "postprocess": postprocess_seconds,
            },
        },
        "criteria_verdicts": verdicts,
    }
    state = {
        "K_data": stiffness.data,
        "K_indices": stiffness.indices,
        "K_indptr": stiffness.indptr,
        "K_shape": np.asarray(stiffness.shape, dtype=np.int64),
        "nodes_m": mesh.nodes_m,
        "connectivity": mesh.connectivity,
        "fixed_dofs": fixed_dofs,
        "free_dofs": free_dofs,
        "F_N": force,
        "u_m": displacement,
        "free_residual_N": free_residual,
        "support_reactions_N": reactions,
        "gauss_strains": gauss_strains,
        "jacobian_determinants_m3": jacobian_determinants,
        "loaded_nodes": loaded_nodes,
        "loaded_face_weights": face_weights,
    }
    return record, state
