"""Read-only checks and mechanics post-processing for archived HEX8-SRI runs.

This module deliberately does not import the solver, the campaign assembler, or
any FEM runner. It only reads arrays that were already archived.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import hashlib

import numpy as np


REQUIRED_ARCHIVE_ARRAYS = frozenset(
    {
        "K",
        "Kff",
        "nodes_m",
        "fixed_dofs",
        "free_dofs",
        "F_N",
        "u_m",
        "free_residual_N",
        "support_reactions_N",
    }
)


def sha256_file(path: Path) -> str:
    """Return SHA-256 of an existing file without changing it."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file_hash(path: Path, expected_sha256: str) -> dict[str, object]:
    """Report MISSING_ARTIFACT or INTEGRITY_MISMATCH without repairing files."""

    path = Path(path)
    if not path.is_file():
        return {"path": str(path), "status": "MISSING_ARTIFACT", "actual_sha256": None}
    actual = sha256_file(path)
    return {
        "path": str(path),
        "status": "PASS" if actual == expected_sha256 else "INTEGRITY_MISMATCH",
        "expected_sha256": expected_sha256,
        "actual_sha256": actual,
    }


def recompute_archived_state(arrays: Mapping[str, np.ndarray]) -> dict[str, object]:
    """Recompute algebraic observables from an already archived linear system.

    This is post-processing of stored K, F, u, geometry, and DOF maps. It does
    not build element matrices, assemble a system, solve, or compute eigenmodes.
    The reported condition number uses the 2-norm condition of archived Kff.
    """

    missing = REQUIRED_ARCHIVE_ARRAYS.difference(arrays)
    if missing:
        raise ValueError("archive is missing required arrays: " + ", ".join(sorted(missing)))

    stiffness = np.asarray(arrays["K"], dtype=float)
    reduced = np.asarray(arrays["Kff"], dtype=float)
    nodes = np.asarray(arrays["nodes_m"], dtype=float)
    fixed = np.asarray(arrays["fixed_dofs"], dtype=np.int64).reshape(-1)
    free = np.asarray(arrays["free_dofs"], dtype=np.int64).reshape(-1)
    force = np.asarray(arrays["F_N"], dtype=float).reshape(-1)
    displacement = np.asarray(arrays["u_m"], dtype=float).reshape(-1)
    saved_free_residual = np.asarray(arrays["free_residual_N"], dtype=float).reshape(-1)
    saved_reactions = np.asarray(arrays["support_reactions_N"], dtype=float).reshape(-1)

    dof_count = displacement.size
    if dof_count == 0 or dof_count % 3:
        raise ValueError("displacement vector length must be a positive multiple of three")
    if stiffness.shape != (dof_count, dof_count) or reduced.shape != (free.size, free.size):
        raise ValueError("K or Kff has an incompatible shape")
    if force.shape != displacement.shape or nodes.shape != (dof_count // 3, 3):
        raise ValueError("force or node coordinates have an incompatible shape")
    if saved_free_residual.shape != free.shape or saved_reactions.shape != fixed.shape:
        raise ValueError("saved residuals or reactions have an incompatible shape")
    if np.any(fixed < 0) or np.any(free < 0) or np.any(fixed >= dof_count) or np.any(free >= dof_count):
        raise ValueError("DOF map contains an out-of-range index")
    all_dofs = np.concatenate((fixed, free))
    if np.unique(fixed).size != fixed.size or np.unique(free).size != free.size:
        raise ValueError("DOF map contains duplicate indices")
    if not np.array_equal(np.sort(all_dofs), np.arange(dof_count)):
        raise ValueError("fixed and free DOFs must form a disjoint partition")
    if not all(np.all(np.isfinite(value)) for value in (stiffness, reduced, nodes, force, displacement)):
        raise ValueError("archive contains non-finite primary arrays")

    reduced_from_global = stiffness[np.ix_(free, free)]
    if not np.array_equal(reduced, reduced_from_global):
        raise ValueError("archived Kff differs from the free-free block of archived K")

    residual = stiffness @ displacement - force
    free_residual = residual[free]
    reactions = residual[fixed]
    full_reactions = np.zeros_like(force)
    full_reactions[fixed] = reactions
    nodal_force = force.reshape(-1, 3)
    nodal_reactions = full_reactions.reshape(-1, 3)
    force_resultant = np.sum(nodal_force, axis=0)
    reaction_resultant = np.sum(nodal_reactions, axis=0)
    force_closure = force_resultant + reaction_resultant
    moment_force = np.sum(np.cross(nodes, nodal_force), axis=0)
    moment_reaction = np.sum(np.cross(nodes, nodal_reactions), axis=0)
    moment_closure = moment_force + moment_reaction

    internal_energy = float(0.5 * displacement @ (stiffness @ displacement))
    external_work = float(displacement @ force)
    energy_defect = float(2.0 * internal_energy - external_work)
    tiny = np.finfo(float).tiny
    symmetry_defect = float(np.linalg.norm(stiffness - stiffness.T, ord="fro"))
    stiffness_norm = float(np.linalg.norm(stiffness, ord="fro"))
    free_scale = max(float(np.linalg.norm(force[free])), float(np.linalg.norm(reduced @ displacement[free])), 1.0)
    force_scale = max(float(np.linalg.norm(force_resultant)), float(np.linalg.norm(reaction_resultant)), 1.0)
    moment_scale = max(float(np.linalg.norm(moment_force)), float(np.linalg.norm(moment_reaction)), 1.0)

    return {
        "free_residual_N": free_residual.tolist(),
        "free_residual_l2_N": float(np.linalg.norm(free_residual)),
        "free_residual_relative": float(np.linalg.norm(free_residual) / free_scale),
        "free_residual_max_abs_difference_from_archive_N": float(
            np.max(np.abs(free_residual - saved_free_residual), initial=0.0)
        ),
        "support_reactions_N": reactions.tolist(),
        "support_reactions_max_abs_difference_from_archive_N": float(
            np.max(np.abs(reactions - saved_reactions), initial=0.0)
        ),
        "support_reaction_resultant_N": reaction_resultant.tolist(),
        "force_closure_N": force_closure.tolist(),
        "force_closure_l2_N": float(np.linalg.norm(force_closure)),
        "force_closure_relative": float(np.linalg.norm(force_closure) / force_scale),
        "moment_closure_Nm": moment_closure.tolist(),
        "moment_closure_l2_Nm": float(np.linalg.norm(moment_closure)),
        "moment_closure_relative": float(np.linalg.norm(moment_closure) / moment_scale),
        "internal_energy_J": internal_energy,
        "external_load_work_J": external_work,
        "energy_defect_J": energy_defect,
        "energy_defect_relative_dimensionless": float(abs(energy_defect) / max(abs(external_work), tiny)),
        "stiffness_symmetry_defect_fro": symmetry_defect,
        "stiffness_symmetry_relative_fro": float(symmetry_defect / max(stiffness_norm, tiny)),
        "condition_number_2_Kff": float(np.linalg.cond(reduced, p=2)),
        "reduced_matrix_matches_global_block": True,
    }


def load_npz_arrays(path: Path) -> dict[str, np.ndarray]:
    """Read numerical arrays from an archived NPZ without permitting pickle."""

    with np.load(Path(path), allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}
