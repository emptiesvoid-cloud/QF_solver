"""Mesh-family-neutral linear-static observables for WP12 development studies.

This module contains post-processing only. It does not assemble a stiffness
matrix, call a solver, or launch FEM work.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from solveur.mesh.topology import HEX8_FACES, TET10_FACES, TET4_FACES


@dataclass(frozen=True)
class SurfaceMeasure:
    """Integrated surface measure weights for one declared boundary plane."""

    nodal_area_weights: np.ndarray
    total_area: float
    face_count: int


def surface_measure_weights(
    nodes: Any,
    elements: Sequence[Sequence[int]],
    family: str,
    *,
    axis: int,
    coordinate: float,
    atol: float = 1.0e-12,
) -> SurfaceMeasure:
    """Integrate element shape functions over planar exterior faces.

    TET4 uses linear triangular faces, TET10 uses quadratic triangular faces,
    and HEX8 uses bilinear quadrilateral faces. The returned weights integrate
    a constant field to the actual geometric surface area for each family.
    """
    points = np.asarray(nodes, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError("nodes must be a finite (n, 3) array")
    if axis not in (0, 1, 2) or not np.isfinite(coordinate) or atol < 0.0:
        raise ValueError("face plane must use a valid axis, finite coordinate and nonnegative tolerance")
    normalized = family.upper()
    face_patterns = {
        "TET4": TET4_FACES,
        "TET10": TET10_FACES,
        "HEX8": HEX8_FACES,
    }.get(normalized)
    if face_patterns is None:
        raise ValueError("surface integration supports only TET4, TET10 and HEX8")
    expected_nodes = {"TET4": 4, "TET10": 10, "HEX8": 8}[normalized]
    weights = np.zeros(points.shape[0], dtype=float)
    total_area = 0.0
    face_count = 0
    for element in elements:
        connectivity = tuple(int(node) for node in element)
        if len(connectivity) != expected_nodes or min(connectivity, default=-1) < 0 or max(connectivity, default=0) >= len(points):
            raise ValueError(f"invalid {normalized} connectivity")
        for pattern in face_patterns:
            face = tuple(connectivity[index] for index in pattern)
            corner_count = 3 if normalized in {"TET4", "TET10"} else 4
            corners = face[:corner_count]
            face_xyz = points[np.asarray(face, dtype=np.int64)]
            if not np.all(np.abs(face_xyz[:, axis] - coordinate) <= atol):
                continue
            xyz = face_xyz[:corner_count]
            if corner_count == 3:
                area = 0.5 * float(np.linalg.norm(np.cross(xyz[1] - xyz[0], xyz[2] - xyz[0])))
            else:
                area = 0.5 * float(np.linalg.norm(np.cross(xyz[1] - xyz[0], xyz[2] - xyz[0])))
                area += 0.5 * float(np.linalg.norm(np.cross(xyz[2] - xyz[0], xyz[3] - xyz[0])))
            if not np.isfinite(area) or area <= 0.0:
                raise ValueError("boundary face has nonpositive or nonfinite area")
            total_area += area
            face_count += 1
            if normalized == "TET4":
                weights[np.asarray(face, dtype=np.int64)] += area / 3.0
            elif normalized == "TET10":
                # For P2 triangles, each corner shape integrates to zero and
                # each of the three edge shapes integrates to one third area.
                weights[np.asarray(face[3:6], dtype=np.int64)] += area / 3.0
            else:
                weights[np.asarray(face, dtype=np.int64)] += area / 4.0
    if face_count == 0 or total_area <= 0.0:
        raise ValueError("no positive-area element face lies on the requested plane")
    if not np.isclose(float(np.sum(weights)), total_area, rtol=1.0e-12, atol=1.0e-14):
        raise ArithmeticError("surface shape-function weights do not integrate a constant field to the area")
    return SurfaceMeasure(weights, total_area, face_count)


def surface_average(
    displacement: Any,
    measure: SurfaceMeasure,
    *,
    component: int,
) -> float:
    """Return the shape-function-integrated average displacement on a face."""
    values = np.asarray(displacement, dtype=float)
    if values.ndim == 1:
        if values.size != 3 * measure.nodal_area_weights.size:
            raise ValueError("flat displacement vector must contain three translations per node")
        values = values.reshape((-1, 3))
    if values.shape != (measure.nodal_area_weights.size, 3) or not np.isfinite(values).all():
        raise ValueError("displacement must be a finite (n_nodes, 3) array")
    if component not in (0, 1, 2):
        raise ValueError("component must be 0, 1 or 2")
    return float(np.dot(measure.nodal_area_weights, values[:, component]) / measure.total_area)


def _matrix_row_sum_norm(matrix: Any) -> float:
    absolute = abs(matrix)
    row_sums = np.asarray(absolute.sum(axis=1), dtype=float).reshape(-1)
    return float(np.max(row_sums, initial=0.0))


def linear_static_observables(
    *,
    nodes: Any,
    stiffness: Any,
    force_vector: Any,
    displacement: Any,
    fixed_dofs: Any,
    load_axis: int = 2,
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
    loaded_face_measure: SurfaceMeasure | None = None,
) -> dict[str, Any]:
    """Recover forces, residuals, work and energy identities from a solution.

    The residual is the algebraic residual of the supplied stiffness matrix;
    it is useful for convergence and equilibrium checks but is not an
    independent element-formulation oracle.
    """
    xyz = np.asarray(nodes, dtype=float)
    force = np.asarray(force_vector, dtype=float).reshape(-1)
    u = np.asarray(displacement, dtype=float).reshape(-1)
    fixed = np.asarray(fixed_dofs, dtype=np.int64).reshape(-1)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
        raise ValueError("nodes must be a finite (n, 3) array")
    ndof = 3 * xyz.shape[0]
    if force.shape != (ndof,) or u.shape != (ndof,) or not np.isfinite(force).all() or not np.isfinite(u).all():
        raise ValueError("force and displacement must be finite vectors with three entries per node")
    if getattr(stiffness, "shape", None) != (ndof, ndof):
        raise ValueError("stiffness matrix shape must match the three translational DOFs per node")
    matrix_data = getattr(stiffness, "data", stiffness)
    if not np.isfinite(np.asarray(matrix_data)).all():
        raise ValueError("stiffness matrix must contain only finite values")
    if load_axis not in (0, 1, 2) or len(origin) != 3 or not np.isfinite(origin).all():
        raise ValueError("load axis and moment origin are invalid")
    if fixed.size and (np.any(fixed < 0) or np.any(fixed >= ndof)):
        raise ValueError("fixed DOF index lies outside the model")
    fixed = np.unique(fixed)
    free = np.setdiff1d(np.arange(ndof, dtype=np.int64), fixed, assume_unique=True)

    internal = np.asarray(stiffness @ u, dtype=float).reshape(-1)
    residual = internal - force
    reactions = np.zeros(ndof, dtype=float)
    reactions[fixed] = residual[fixed]
    nodal_force = force.reshape((-1, 3))
    nodal_reaction = reactions.reshape((-1, 3))
    resultant = np.sum(nodal_force, axis=0)
    reaction_resultant = np.sum(nodal_reaction, axis=0)
    moment_load = np.sum(np.cross(xyz - np.asarray(origin, dtype=float), nodal_force), axis=0)
    moment_reaction = np.sum(np.cross(xyz - np.asarray(origin, dtype=float), nodal_reaction), axis=0)
    free_residual = residual[free]
    free_force = force[free]
    residual_norm = float(np.linalg.norm(free_residual))
    free_force_norm = float(np.linalg.norm(free_force))
    relative_residual = residual_norm / free_force_norm if free_force_norm > 0.0 else (0.0 if residual_norm == 0.0 else None)
    free_matrix = stiffness[free, :]
    backward_denominator = (
        _matrix_row_sum_norm(free_matrix) * float(np.linalg.norm(u, ord=np.inf))
        + float(np.linalg.norm(free_force, ord=np.inf))
        if free.size
        else 0.0
    )
    backward_error = (
        float(np.linalg.norm(free_residual, ord=np.inf)) / backward_denominator
        if backward_denominator > 0.0
        else (0.0 if residual_norm == 0.0 else None)
    )
    strain_energy = 0.5 * float(np.dot(u, internal))
    external_work = float(np.dot(u, force))
    residual_work_all = float(np.dot(u, residual))
    residual_work_free = float(np.dot(u[free], free_residual))
    force_component = float(resultant[load_axis])
    load_conjugate = external_work / force_component if force_component != 0.0 else None
    displacement_by_node = u.reshape((-1, 3))
    translations = np.linalg.norm(displacement_by_node, axis=1)
    max_node = int(np.argmax(translations)) if translations.size else None
    average = (
        surface_average(displacement_by_node, loaded_face_measure, component=load_axis)
        if loaded_face_measure is not None
        else None
    )
    return {
        "load_resultant_n": resultant.tolist(),
        "reaction_resultant_n": reaction_resultant.tolist(),
        "force_equilibrium_residual_n": (resultant + reaction_resultant).tolist(),
        "applied_moment_about_origin_nm": moment_load.tolist(),
        "reaction_moment_about_origin_nm": moment_reaction.tolist(),
        "moment_equilibrium_residual_nm": (moment_load + moment_reaction).tolist(),
        "free_residual_norm_n": residual_norm,
        "free_residual_max_abs_n": float(np.max(np.abs(free_residual), initial=0.0)),
        "free_load_norm_n": free_force_norm,
        "free_residual_relative_to_free_load": relative_residual,
        "free_residual_backward_error_inf": backward_error,
        "residual_method": "K_supplied_times_u_minus_f; same-matrix diagnostic, not an independent formulation oracle",
        "strain_energy_j": strain_energy,
        "external_work_j": external_work,
        "twice_energy_minus_work_j": 2.0 * strain_energy - external_work,
        "residual_work_all_dofs_j": residual_work_all,
        "residual_work_free_dofs_j": residual_work_free,
        "energy_identity_minus_all_residual_work_j": 2.0 * strain_energy - external_work - residual_work_all,
        "energy_identity_minus_free_residual_work_j": 2.0 * strain_energy - external_work - residual_work_free,
        "fixed_displacement_norm_m": float(np.linalg.norm(u[fixed])) if fixed.size else 0.0,
        "work_conjugate_displacement_m": load_conjugate,
        "area_weighted_loaded_face_displacement_m": average,
        "max_nodal_translation_m": float(translations[max_node]) if max_node is not None else 0.0,
        "max_nodal_translation_node_id_zero_based": max_node,
    }
