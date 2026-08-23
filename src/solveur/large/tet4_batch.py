"""Vectorized constant-strain TET4 kernels for large-model assembly."""

from __future__ import annotations

import numpy as np


def tet4_stiffness_batch(coords: np.ndarray, elasticity: np.ndarray) -> np.ndarray:
    """Return one 12x12 stiffness matrix per TET4 in a vectorized batch."""
    points = np.asarray(coords, dtype=float)
    constitutive = np.asarray(elasticity, dtype=float)
    if points.ndim != 3 or points.shape[1:] != (4, 3):
        raise ValueError("Batched TET4 coordinates must have shape (n, 4, 3).")
    if constitutive.shape != (6, 6):
        raise ValueError("TET4 elasticity matrix must have shape (6, 6).")
    if points.shape[0] == 0:
        return np.empty((0, 12, 12), dtype=float)
    _, volumes, gradients = _tet4_geometry_batch(points)
    b_matrix = _strain_displacement_batch(gradients)
    stiffness = volumes[:, None, None] * np.einsum(
        "eia,ij,ejb->eab",
        b_matrix,
        constitutive,
        b_matrix,
        optimize=True,
    )
    return 0.5 * (stiffness + stiffness.transpose(0, 2, 1))


def tet4_mass_batch(coords: np.ndarray, density: np.ndarray | float) -> np.ndarray:
    """Return the consistent translational mass matrix for each TET4.

    The scalar tetrahedral shape-function integral is ``rho * V / 20``;
    each 3-by-3 nodal block is this scalar times 2 on the diagonal and 1
    off-diagonal.  Keeping this kernel batched gives the modal/Newmark large
    path the same chunked memory behaviour as the stiffness assembly.
    """
    points = np.asarray(coords, dtype=float)
    if points.ndim != 3 or points.shape[1:] != (4, 3):
        raise ValueError("Batched TET4 coordinates must have shape (n, 4, 3).")
    _, volumes, _ = _tet4_geometry_batch(points)
    values = np.asarray(density, dtype=float)
    if values.ndim == 0:
        values = np.full(points.shape[0], float(values), dtype=float)
    if values.shape != (points.shape[0],):
        raise ValueError("TET4 density must be a scalar or one value per element.")
    if np.any(values <= 0.0):
        raise ValueError("TET4 modal mass requires positive density.")
    scalar = values * volumes / 20.0
    mass = np.zeros((points.shape[0], 12, 12), dtype=float)
    identity = np.eye(3)
    for row in range(4):
        for column in range(4):
            mass[:, 3 * row : 3 * row + 3, 3 * column : 3 * column + 3] = (
                scalar * (2.0 if row == column else 1.0)
            )[:, None, None] * identity
    return mass


def element_dofs_batch(nodes: np.ndarray) -> np.ndarray:
    """Return direct translation dof indices for a TET4 connectivity batch."""
    connectivity = np.asarray(nodes, dtype=np.int64)
    if connectivity.ndim != 2 or connectivity.shape[1] != 4:
        raise ValueError("Batched TET4 connectivity must have shape (n, 4).")
    return (3 * connectivity[:, :, None] + np.arange(3, dtype=np.int64)).reshape((-1, 12))


def apply_homogeneous_constraints_batch(
    stiffness: np.ndarray,
    element_dofs: np.ndarray,
    fixed_mask: np.ndarray,
) -> np.ndarray:
    """Zero constrained rows and columns in a batch without Python loops."""
    if not np.any(fixed_mask):
        return stiffness
    free = ~fixed_mask[element_dofs]
    return stiffness * free[:, :, None] * free[:, None, :]


def petsc_block_values_batch(stiffness: np.ndarray) -> np.ndarray:
    """Return contiguous scalar rows accepted by PETSc blocked insertion."""
    values = np.asarray(stiffness, dtype=float)
    if values.ndim != 3 or values.shape[1:] != (12, 12):
        raise ValueError("Batched TET4 stiffness must have shape (n, 12, 12).")
    return values.copy()


def tet4_response_batch(
    coords: np.ndarray,
    local_displacements: np.ndarray,
    elasticity: np.ndarray,
) -> dict[str, np.ndarray]:
    """Return constant TET4 strain, stress and invariants for one batch."""
    points = np.asarray(coords, dtype=float)
    displacement = np.asarray(local_displacements, dtype=float)
    constitutive = np.asarray(elasticity, dtype=float)
    if points.ndim != 3 or points.shape[1:] != (4, 3):
        raise ValueError("Batched TET4 coordinates must have shape (n, 4, 3).")
    if displacement.shape != (points.shape[0], 12):
        raise ValueError("Batched TET4 displacements must have shape (n, 12).")
    if constitutive.shape != (6, 6):
        raise ValueError("TET4 elasticity matrix must have shape (6, 6).")
    if points.shape[0] == 0:
        empty6 = np.empty((0, 6), dtype=float)
        return {
            "volume": np.empty(0, dtype=float),
            "strain": empty6,
            "stress": empty6.copy(),
            "von_mises": np.empty(0, dtype=float),
            "strain_energy": np.empty(0, dtype=float),
        }
    _, volumes, gradients = _tet4_geometry_batch(points)
    b_matrix = _strain_displacement_batch(gradients)
    strain = np.einsum("eij,ej->ei", b_matrix, displacement, optimize=True)
    stress = np.einsum("ij,ej->ei", constitutive, strain, optimize=True)
    sx, sy, sz, txy, tyz, txz = stress.T
    von_mises = np.sqrt(
        np.maximum(
            0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2)
            + 3.0 * (txy**2 + tyz**2 + txz**2),
            0.0,
        )
    )
    strain_energy = 0.5 * volumes * np.einsum("ei,ei->e", strain, stress, optimize=True)
    return {
        "volume": volumes,
        "strain": strain,
        "stress": stress,
        "von_mises": von_mises,
        "strain_energy": strain_energy,
    }


def _tet4_geometry_batch(points: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return edges, signed volumes and shape-function gradients in batches.

    The constant-strain TET4 gradients are the barycentric gradients of the
    four nodes. Computing them from oriented face normals avoids forming one
    small dense inverse per element while preserving the signed-volume check.
    ``edge_matrix`` is returned because callers may use it for diagnostics.
    """
    edge_matrix = np.stack(
        (points[:, 1] - points[:, 0], points[:, 2] - points[:, 0], points[:, 3] - points[:, 0]),
        axis=2,
    )
    determinant = np.linalg.det(edge_matrix)
    volumes = determinant / 6.0
    invalid = np.flatnonzero(volumes <= 1.0e-14)
    if invalid.size:
        index = int(invalid[0])
        raise ValueError(f"Invalid batched TET4 volume {volumes[index]:.6e} at batch index {index}.")

    edge_01 = edge_matrix[:, :, 0]
    edge_02 = edge_matrix[:, :, 1]
    edge_03 = edge_matrix[:, :, 2]
    safe_determinant = determinant[:, None]
    gradient_1 = np.cross(edge_02, edge_03) / safe_determinant
    gradient_2 = np.cross(edge_03, edge_01) / safe_determinant
    gradient_3 = np.cross(edge_01, edge_02) / safe_determinant
    gradient_0 = -(gradient_1 + gradient_2 + gradient_3)
    gradients = np.stack((gradient_0, gradient_1, gradient_2, gradient_3), axis=1)
    return edge_matrix, volumes, gradients


def _strain_displacement_batch(gradients: np.ndarray) -> np.ndarray:
    count = gradients.shape[0]
    b = np.zeros((count, 6, 12), dtype=float)
    for node in range(4):
        column = 3 * node
        gx = gradients[:, node, 0]
        gy = gradients[:, node, 1]
        gz = gradients[:, node, 2]
        b[:, 0, column] = gx
        b[:, 1, column + 1] = gy
        b[:, 2, column + 2] = gz
        b[:, 3, column] = gy
        b[:, 3, column + 1] = gx
        b[:, 4, column + 1] = gz
        b[:, 4, column + 2] = gy
        b[:, 5, column] = gz
        b[:, 5, column + 2] = gx
    return b
