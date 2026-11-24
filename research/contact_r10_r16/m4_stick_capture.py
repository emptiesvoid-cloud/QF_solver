"""Small, fail-closed readers and independent TET4 internal-force recovery for M4 captures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


CAPTURE_SCHEMA = "qf.m4-stick-diagnostic-capture.v1"
CAPTURE_ARRAYS = {
    "nodes",
    "tet4_connectivity",
    "displacements",
    "loads",
    "fixed_dof_indices",
    "dof_map",
    "contact_slave_nodes",
    "contact_normals",
    "contact_tangents",
    "contact_pressures",
    "contact_gaps",
    "contact_active",
    "contact_states",
    "slip_references_in",
    "slip_references_out",
    "tangential_displacements",
    "trial_tangential_forces",
    "tangential_forces",
    "friction_capacities",
    "coulomb_margins",
    "gap_tolerances",
    "tangent_stiffnesses",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_capture_archive(output_dir: Path, *, contract_sha256: str) -> dict[str, Any]:
    """Validate a captured M4 field archive without executing any solver code."""
    output_dir = Path(output_dir).resolve()
    manifest_path = output_dir / "capture-manifest.json"
    archive_path = output_dir / "m4-stick-fields.npz"
    if not manifest_path.is_file() or not archive_path.is_file():
        raise ValueError("capture manifest or field archive is missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("capture manifest is unreadable") from exc
    if (
        manifest.get("schema") != CAPTURE_SCHEMA
        or manifest.get("contract_sha256") != contract_sha256
        or manifest.get("archive_sha256") != sha256_file(archive_path)
    ):
        raise ValueError("capture manifest identity or archive digest is invalid")
    expected_steps = manifest.get("captured_steps")
    expected_contacts = manifest.get("contact_count")
    if type(expected_steps) is not int or not 0 <= expected_steps <= 8:
        raise ValueError("captured step count is invalid")
    if type(expected_contacts) is not int or expected_contacts != 81:
        raise ValueError("contact count is invalid")

    try:
        with np.load(archive_path, allow_pickle=False) as archive:
            if set(archive.files) != CAPTURE_ARRAYS:
                raise ValueError("field archive has a missing or unexpected array")
            arrays = {key: np.asarray(archive[key]) for key in archive.files}
    except (OSError, ValueError, EOFError) as exc:
        raise ValueError("field archive is unreadable or unsafe") from exc

    nodes = arrays["nodes"]
    tets = arrays["tet4_connectivity"]
    if nodes.ndim != 2 or nodes.shape[1] != 3 or not np.issubdtype(nodes.dtype, np.floating):
        raise ValueError("node coordinates have an invalid shape or type")
    if tets.ndim != 2 or tets.shape[1] != 4 or not np.issubdtype(tets.dtype, np.integer):
        raise ValueError("TET4 connectivity has an invalid shape or type")
    if nodes.shape[0] != manifest.get("node_count") or tets.shape[0] != manifest.get("element_count"):
        raise ValueError("field archive dimensions differ from its manifest")
    dofs = 3 * nodes.shape[0]
    contacts = expected_contacts
    steps = expected_steps
    expected_shapes = {
        "displacements": (steps, dofs),
        "loads": (steps, dofs),
        "fixed_dof_indices": (manifest.get("fixed_dof_count"),),
        "dof_map": (nodes.shape[0], 3),
        "contact_slave_nodes": (contacts,),
        "contact_normals": (contacts, 3),
        "contact_tangents": (contacts, 2, 3),
        "contact_pressures": (steps, contacts),
        "contact_gaps": (steps, contacts),
        "contact_active": (steps, contacts),
        "contact_states": (steps, contacts),
        "slip_references_in": (steps, contacts, 2),
        "slip_references_out": (steps, contacts, 2),
        "tangential_displacements": (steps, contacts, 2),
        "trial_tangential_forces": (steps, contacts, 2),
        "tangential_forces": (steps, contacts, 2),
        "friction_capacities": (steps, contacts),
        "coulomb_margins": (steps, contacts),
        "gap_tolerances": (contacts,),
        "tangent_stiffnesses": (contacts,),
    }
    for key, shape in expected_shapes.items():
        if arrays[key].shape != shape:
            raise ValueError(f"field array {key} has an invalid shape")
    for key, array in arrays.items():
        if not np.all(np.isfinite(array)):
            raise ValueError(f"field array {key} contains non-finite values")
    if np.any(tets < 0) or np.any(tets >= nodes.shape[0]):
        raise ValueError("TET4 connectivity references an unknown node")
    if np.any(arrays["contact_slave_nodes"] < 0) or np.any(arrays["contact_slave_nodes"] >= nodes.shape[0]):
        raise ValueError("contact slave list references an unknown node")
    if len(np.unique(arrays["contact_slave_nodes"])) != contacts:
        raise ValueError("contact slave list contains duplicate nodes")
    if np.any(arrays["dof_map"] < 0) or np.any(arrays["dof_map"] >= dofs):
        raise ValueError("degree-of-freedom map references an unknown degree")
    if np.any(arrays["fixed_dof_indices"] < 0) or np.any(arrays["fixed_dof_indices"] >= dofs):
        raise ValueError("fixed degree list references an unknown degree")
    states = arrays["contact_states"]
    if not np.issubdtype(states.dtype, np.integer) or np.any((states < 0) | (states > 3)):
        raise ValueError("contact state encoding is invalid")
    return {
        "schema": CAPTURE_SCHEMA,
        "captured_steps": steps,
        "contact_count": contacts,
        "node_count": int(nodes.shape[0]),
        "element_count": int(tets.shape[0]),
        "archive_sha256": manifest["archive_sha256"],
    }


def tet4_internal_force(
    nodes: np.ndarray,
    connectivity: np.ndarray,
    displacement: np.ndarray,
    *,
    young_modulus_pa: float,
    poisson_ratio: float,
) -> np.ndarray:
    """Reassemble linear-elastic TET4 internal forces by element stress recovery."""
    xyz = np.asarray(nodes, dtype=float)
    tets = np.asarray(connectivity, dtype=np.int64)
    u = np.asarray(displacement, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or tets.ndim != 2 or tets.shape[1] != 4:
        raise ValueError("TET4 mesh arrays have invalid dimensions")
    if u.shape != (3 * xyz.shape[0],):
        raise ValueError("displacement vector has an invalid dimension")
    if not np.isfinite(young_modulus_pa) or young_modulus_pa <= 0.0:
        raise ValueError("Young's modulus must be finite and positive")
    if not np.isfinite(poisson_ratio) or not -1.0 < poisson_ratio < 0.5:
        raise ValueError("Poisson ratio is outside the stable isotropic range")
    if not np.all(np.isfinite(xyz)) or not np.all(np.isfinite(u)):
        raise ValueError("mesh or displacement contains non-finite values")
    if np.any(tets < 0) or np.any(tets >= xyz.shape[0]):
        raise ValueError("TET4 connectivity references an unknown node")

    e_mod = float(young_modulus_pa)
    nu = float(poisson_ratio)
    shear = e_mod / (2.0 * (1.0 + nu))
    lame = e_mod * nu / ((1.0 + nu) * (1.0 - 2.0 * nu))
    constitutive = np.zeros((6, 6), dtype=float)
    constitutive[:3, :3] = lame
    constitutive[0, 0] += 2.0 * shear
    constitutive[1, 1] += 2.0 * shear
    constitutive[2, 2] += 2.0 * shear
    constitutive[3, 3] = shear
    constitutive[4, 4] = shear
    constitutive[5, 5] = shear

    result = np.zeros_like(xyz)
    for element in tets:
        points = xyz[element]
        jacobian = np.column_stack((points[1] - points[0], points[2] - points[0], points[3] - points[0]))
        determinant = float(np.linalg.det(jacobian))
        if not np.isfinite(determinant) or abs(determinant) <= np.finfo(float).tiny:
            raise ValueError("singular TET4 element encountered during stress recovery")
        inverse = np.linalg.inv(jacobian)
        gradients = np.empty((4, 3), dtype=float)
        gradients[1:] = inverse
        gradients[0] = -np.sum(gradients[1:], axis=0)
        b_matrix = np.zeros((6, 12), dtype=float)
        for local, (gx, gy, gz) in enumerate(gradients):
            col = 3 * local
            b_matrix[0, col] = gx
            b_matrix[1, col + 1] = gy
            b_matrix[2, col + 2] = gz
            b_matrix[3, col] = gy
            b_matrix[3, col + 1] = gx
            b_matrix[4, col + 1] = gz
            b_matrix[4, col + 2] = gy
            b_matrix[5, col] = gz
            b_matrix[5, col + 2] = gx
        element_u = u[np.concatenate([np.arange(3 * node, 3 * node + 3) for node in element])]
        strain = b_matrix @ element_u
        stress = constitutive @ strain
        internal = b_matrix.T @ stress * (abs(determinant) / 6.0)
        for local, node in enumerate(element):
            result[node] += internal[3 * local : 3 * local + 3]
    return result.reshape(-1)
