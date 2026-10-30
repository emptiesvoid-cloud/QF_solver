"""Local HEX8/SRI cantilever assembly and immutable run-sidecar support.

This module intentionally bypasses the production element registry and global
solver. It is only imported by the explicitly gated research tests.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from scipy.linalg import solve

from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.hex8_sri import Hex8SRIElement
from solveur.materials.solid import SolidMaterial


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PARENT = "2aa994f34900f39bef8df9db5fb025157fb694bb"
RESIDUAL_TOLERANCE = 1.0e-7
DOF_COUNT = 3
CASE_FORMULATIONS = {"hex8_standard", "sri_historical", "sri_corrected"}
FACE_QUADRATURE_WEIGHTS = (0.25, 0.5, 0.25)
LOCAL_CONNECTIVITY_OFFSETS = (
    (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
    (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),
)


class HistoricalHex8SRIElement(Hex8SRIElement):
    """Controlled ablation of the center-point volumetric quadrature weight.

    The legacy-named case uses the parent-source central volumetric expression
    with weight 1 instead of the corrected weight 8. It is not a bit-for-bit
    reproduction of the historical arithmetic path.
    """

    historical_parent_commit = SOURCE_PARENT

    def volumetric_stiffness(self, coords: np.ndarray) -> np.ndarray:
        self.validate_geometry(coords)
        _, volumetric = self._constitutive_split(self.material)
        point = self.volumetric_integration_points[0]
        b_matrix, determinant = self.b_matrix(coords, point)
        stiffness = determinant * (b_matrix.T @ volumetric @ b_matrix)
        return 0.5 * (stiffness + stiffness.T)


def mesh_data() -> tuple[np.ndarray, np.ndarray]:
    """Return the fixed 20x1x1 m mesh: 45 nodes and 16 affine HEX8 cells."""
    nodes = np.asarray(
        [(5.0 * ix, 0.5 * iy, 0.5 * iz) for ix in range(5) for iy in range(3) for iz in range(3)],
        dtype=float,
    )
    connectivity = []
    for ix in range(4):
        for iy in range(2):
            for iz in range(2):
                connectivity.append(
                    [((ix + dx) * 3 + iy + dy) * 3 + iz + dz for dx, dy, dz in LOCAL_CONNECTIVITY_OFFSETS]
                )
    return nodes, np.asarray(connectivity, dtype=np.int64)


def _element_type(formulation: str):
    if formulation == "hex8_standard":
        return Hex8Element
    if formulation == "sri_historical":
        return HistoricalHex8SRIElement
    if formulation == "sri_corrected":
        return Hex8SRIElement
    raise ValueError(f"unknown campaign formulation: {formulation}")


def _dof_indices(node_ids: np.ndarray) -> np.ndarray:
    return (3 * node_ids[:, None] + np.arange(DOF_COUNT, dtype=np.int64)).reshape(-1)


def _load_vector(nodes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    force = np.zeros(nodes.shape[0] * DOF_COUNT, dtype=float)
    loaded_nodes = np.asarray([((4 * 3) + iy) * 3 + iz for iy in range(3) for iz in range(3)])
    for iy in range(3):
        for iz in range(3):
            index = iy * 3 + iz
            force[3 * loaded_nodes[index] + 2] = -FACE_QUADRATURE_WEIGHTS[iy] * FACE_QUADRATURE_WEIGHTS[iz]
    return force, loaded_nodes


def assemble_and_solve(formulation: str, poisson_ratio: float) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Assemble/solve one paired case using only local element stiffness calls."""
    if formulation not in CASE_FORMULATIONS:
        raise ValueError(f"unknown campaign formulation: {formulation}")
    nodes, connectivity = mesh_data()
    material = SolidMaterial(E=1.0e6, nu=float(poisson_ratio))
    element = _element_type(formulation)(material)
    ndof = nodes.shape[0] * DOF_COUNT
    stiffness = np.zeros((ndof, ndof), dtype=float)
    local_stiffness = np.zeros((connectivity.shape[0], 24, 24), dtype=float)
    jacobian_determinants = np.zeros((connectivity.shape[0], 9), dtype=float)

    import time

    total_start = time.perf_counter()
    assembly_start = total_start
    for element_index, node_ids in enumerate(connectivity):
        coords = nodes[node_ids]
        local = element.stiffness(coords)
        local_stiffness[element_index] = local
        dofs = _dof_indices(node_ids)
        stiffness[np.ix_(dofs, dofs)] += local
        points = ((0.0, 0.0, 0.0), *Hex8Element.integration_points)
        jacobian_determinants[element_index] = [Hex8Element.jacobian_determinant(coords, p) for p in points]
    assembly_seconds = time.perf_counter() - assembly_start

    force, loaded_nodes = _load_vector(nodes)
    fixed = np.arange(27, dtype=np.int64)
    free = np.arange(27, ndof, dtype=np.int64)
    reduced = stiffness[np.ix_(free, free)]
    solve_start = time.perf_counter()
    displacement = np.zeros(ndof, dtype=float)
    displacement[free] = solve(reduced, force[free], assume_a="sym", check_finite=True)
    solve_seconds = time.perf_counter() - solve_start

    post_start = time.perf_counter()
    residual = stiffness @ displacement - force
    free_residual = residual[free]
    relative_residual = float(
        np.linalg.norm(free_residual)
        / max(np.linalg.norm(force[free]), np.linalg.norm(reduced @ displacement[free]), 1.0)
    )
    reactions = residual[fixed]
    strains = np.empty((connectivity.shape[0], 8, 6), dtype=float)
    for element_index, node_ids in enumerate(connectivity):
        coords = nodes[node_ids]
        local_u = displacement[_dof_indices(node_ids)]
        for point_index, point in enumerate(Hex8Element.integration_points):
            b_matrix, _ = Hex8Element.b_matrix(coords, point)
            strains[element_index, point_index] = b_matrix @ local_u

    face_weights = np.asarray(
        [FACE_QUADRATURE_WEIGHTS[iy] * FACE_QUADRATURE_WEIGHTS[iz] for iy in range(3) for iz in range(3)]
    )
    signed_mean_uz = float(face_weights @ displacement[3 * loaded_nodes + 2])
    internal_energy = float(0.5 * displacement @ (stiffness @ displacement))
    external_work = float(displacement @ force)
    force_sum = np.sum(force.reshape(-1, 3), axis=0)
    reaction_sum = np.sum(reactions.reshape(-1, 3), axis=0)
    full_reaction = np.zeros((nodes.shape[0], 3), dtype=float)
    full_reaction.reshape(-1)[fixed] = reactions
    force_closure = force_sum + np.sum(full_reaction, axis=0)
    moment_force = np.sum(np.cross(nodes, force.reshape(-1, 3)), axis=0)
    moment_reaction = np.sum(np.cross(nodes, full_reaction), axis=0)
    moment_closure = moment_force + moment_reaction
    condition_number = float(np.linalg.cond(reduced, p=2))
    postprocess_seconds = time.perf_counter() - post_start
    total_seconds = time.perf_counter() - total_start

    finite_arrays = (stiffness, reduced, displacement, strains, free_residual, reactions, jacobian_determinants)
    finite = all(bool(np.all(np.isfinite(array))) for array in finite_arrays)
    positive_jacobians = bool(np.all(jacobian_determinants > 0.0))
    residual_pass = bool(np.isfinite(relative_residual) and relative_residual <= RESIDUAL_TOLERANCE)
    record: dict[str, Any] = {
        "case": {"formulation": formulation, "E_Pa": 1.0e6, "poisson_ratio": float(poisson_ratio)},
        "units": {"displacement": "m", "strain": "dimensionless", "energy": "J", "force": "N", "moment": "N·m", "time": "s"},
        "observables": {
            "signed_mean_loaded_face_UZ_m": signed_mean_uz,
            "displacement_vector_m": displacement.tolist(),
            "displacement_l2_m": float(np.linalg.norm(displacement)),
            "gauss_strain_dimensionless": strains.tolist(),
            "internal_energy_J": internal_energy,
            "external_load_work_J": external_work,
            "energy_defect_J": float(2.0 * internal_energy - external_work),
            "energy_defect_normalized": float(abs(2.0 * internal_energy - external_work) / max(abs(external_work), 1.0)),
            "free_residual_N": free_residual.tolist(),
            "free_residual_l2_N": float(np.linalg.norm(free_residual)),
            "relative_free_residual": relative_residual,
            "support_reactions_N": reactions.tolist(),
            "support_reaction_resultant_N": reaction_sum.tolist(),
            "force_closure_N": force_closure.tolist(),
            "force_closure_l2_N": float(np.linalg.norm(force_closure)),
            "force_closure_relative": float(np.linalg.norm(force_closure) / max(np.linalg.norm(force_sum), np.linalg.norm(reaction_sum), 1.0)),
            "moment_closure_Nm": moment_closure.tolist(),
            "moment_closure_l2_Nm": float(np.linalg.norm(moment_closure)),
            "moment_closure_relative": float(np.linalg.norm(moment_closure) / max(np.linalg.norm(moment_force), np.linalg.norm(moment_reaction), 1.0)),
            "condition_number_2_Kff": condition_number,
            "condition_number_method": "numpy.linalg.cond(Kff, p=2), dense 108x108",
            "jacobian_determinants_center_then_gauss_m3": jacobian_determinants.tolist(),
            "timing_seconds": {
                "assembly": assembly_seconds,
                "solve": solve_seconds,
                "postprocess": postprocess_seconds,
                "calculation_total": total_seconds,
            },
        },
        "criteria_verdicts": {
            "all_observed_arrays_finite": "PASS" if finite else "FAIL",
            "all_center_and_gauss_jacobians_positive": "PASS" if positive_jacobians else "FAIL",
            "existing_direct_relative_residual_tolerance_1e-7": "PASS" if residual_pass else "FAIL",
            "force_and_moment_closure": "REPORTED_NO_ADDITIONAL_THRESHOLD",
            "energy_defect": "REPORTED_NO_ADDITIONAL_THRESHOLD",
            "spatial_convergence": "NOT_ASSESSED_SINGLE_MESH",
        },
    }
    arrays = {
        "K": stiffness,
        "Kff": reduced,
        "element_stiffness": local_stiffness,
        "nodes_m": nodes,
        "connectivity": connectivity,
        "fixed_dofs": fixed,
        "free_dofs": free,
        "F_N": force,
        "u_m": displacement,
        "free_residual_N": free_residual,
        "support_reactions_N": reactions,
        "gauss_strains": strains,
        "jacobian_determinants_m3": jacobian_determinants,
    }
    return record, arrays


def _json_bytes(record: Mapping[str, Any]) -> bytes:
    return (json.dumps(record, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def atomic_write_new_bytes(path: Path, payload: bytes) -> str:
    """Atomically install bytes without ever replacing an existing artifact."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temp_path = Path(temp_name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp_path, path)  # create-if-absent is atomic on the same filesystem
        return hashlib.sha256(payload).hexdigest()
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def atomic_write_json_new(path: Path, record: Mapping[str, Any]) -> str:
    return atomic_write_new_bytes(path, _json_bytes(record))


def make_run_sidecar(
    *,
    record: Mapping[str, Any],
    arrays_path: Path,
    arrays_sha256: str,
    manifest_path: Path,
    manifest_sha256: str,
    science_identity: Mapping[str, Any],
    controller_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind observables to immutable source, controller, manifest and arrays."""
    return {
        "schema": "qfsolver-hex8-sri-run-sidecar-v1",
        "campaign_id": "HEX8-SRI-CANTILEVER-6-2026-10-26",
        "science_identity": dict(science_identity),
        "controller_identity": dict(controller_identity),
        "manifest_identity": {
            "path": str(manifest_path),
            "sha256": manifest_sha256,
        },
        "state_artifact": {
            "path": str(arrays_path),
            "sha256": arrays_sha256,
        },
        **dict(record),
    }
