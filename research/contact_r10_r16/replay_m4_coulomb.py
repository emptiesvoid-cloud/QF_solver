"""Recompute M4 planar-contact checks from retained fields without solving FEM."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from research.contact_r10_r16.m4_stick_capture import (
    sha256_file,
    tet4_internal_force,
    validate_capture_archive,
)


def replay(output: Path, contract_path: Path) -> dict:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    validation = validate_capture_archive(output, contract_sha256=sha256_file(contract_path))
    capture = json.loads((output / "capture-manifest.json").read_text(encoding="utf-8"))
    if (
        capture["nodeid"] != contract["nodeid"]
        or capture["scope"] != contract["scope"]
        or capture["source_tree"] != contract["source"]["solver_src_tree"]
        or capture["source_commit"] != contract["source"]["product_source_commit"]
    ):
        raise ValueError("Archive and contract identities differ")

    with np.load(output / "m4-stick-fields.npz", allow_pickle=False) as fields:
        nodes, tets, dofs = (fields[name] for name in ("nodes", "tet4_connectivity", "dof_map"))
        slave = fields["contact_slave_nodes"]
        master = np.setdiff1d(np.arange(len(nodes)), np.unique(tets))
        fixed = np.isin(dofs, fields["fixed_dof_indices"])
        tangent = fields["contact_tangents"]
        master_x = contract["case"]["contact"]["master_plane_x_m"]
        if (
            not len(master) or not np.all(nodes[master, 0] == master_x)
            or not np.all(fixed[master]) or np.any(fixed[slave])
            or set(np.unique(dofs)) != set(range(nodes.size))
            or not np.all(fields["contact_normals"] == [-1, 0, 0])
            or not np.all(tangent[:, :, 0] == 0)
            or not np.allclose(tangent @ tangent.transpose(0, 2, 1), np.eye(2), atol=1e-14, rtol=0)
        ):
            raise ValueError("Replay requires the fixed planar M4 master and orthonormal tangents")
        mu = contract["case"]["contact"]["friction_coefficient"]
        material = contract["case"]["material"]
        thresholds = contract["criteria"]
        gap_tolerance = thresholds["normal_gap_tolerance_m"]
        rows = []
        for i, (u, load) in enumerate(zip(fields["displacements"], fields["loads"], strict=True)):
            u_xyz, applied = u[dofs], load[dofs]
            if np.any(u_xyz[master]) or np.any(applied[master]):
                raise ValueError("Replay requires zero master displacement and load")
            force = tet4_internal_force(
                nodes, tets, u_xyz.ravel(),
                young_modulus_pa=material["young_modulus_pa"], poisson_ratio=material["poisson_ratio"],
            ).reshape(nodes.shape)
            pressure = fields["contact_pressures"][i]
            tangent_force = fields["tangential_forces"][i]
            active = fields["contact_active"][i]
            state = fields["contact_states"][i]
            gap = (master_x - nodes[slave, 0]) - u_xyz[slave, 0]
            relative = np.einsum("ijk,ik->ij", tangent, u_xyz[slave])
            trial = fields["tangent_stiffnesses"][:, None] * (relative - fields["slip_references_in"][i])
            trial_norm = np.linalg.norm(trial, axis=1)
            cap = mu * np.maximum(pressure, 0.0)
            scale = np.ones_like(cap)
            beyond = trial_norm > cap
            scale[beyond] = cap[beyond] / trial_norm[beyond]
            projection_error = np.linalg.norm(tangent_force - scale[:, None] * trial, axis=1)
            contact = np.zeros_like(nodes)
            contact[slave] = -np.einsum("ijk,ij->ik", tangent, tangent_force)
            contact[slave, 0] = -pressure
            residual = force - applied - contact
            total = applied + contact + np.where(fixed, residual, 0.0)
            force_scale = max(float(np.linalg.norm(applied, axis=1).sum()), 1.0)
            moment_scale = force_scale * max(float(np.linalg.norm(nodes, axis=1).max()), 1.0)
            row = {
                "step": i + 1,
                "gap_capture_error_m": float(np.max(np.abs(gap - fields["contact_gaps"][i]))),
                "trial_capture_error_N": float(np.max(np.abs(trial - fields["trial_tangential_forces"][i]))),
                "normal_reaction_error_N": float(np.max(np.abs(applied[slave, 0] - force[slave, 0] - pressure))),
                "scaled_coulomb_residual": float(np.max(projection_error / np.maximum(cap, 1.0))),
                "normal_and_state_gates": bool(
                    np.all(np.abs(gap[active]) <= gap_tolerance)
                    and np.all(pressure[active] >= -gap_tolerance)
                    and np.all(gap[~active] >= -gap_tolerance)
                    and np.all(pressure[~active] == 0.0)
                    and np.all(np.linalg.norm(tangent_force[~active], axis=1) <= gap_tolerance)
                    and np.all(np.isin(state[active & (pressure > gap_tolerance)], (1, 2)))
                    and np.all(state[~active | (pressure <= gap_tolerance)] == 0)
                ),
                "free_equilibrium_relative": float(
                    np.linalg.norm(residual[~fixed]) / max(float(np.linalg.norm(applied[~fixed])), 1.0)
                ),
                "global_force_relative": float(np.linalg.norm(total.sum(axis=0)) / force_scale),
                "global_moment_relative": float(np.linalg.norm(np.cross(nodes, total).sum(axis=0)) / moment_scale),
            }
            rows.append(row)
    return {**validation, "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("contract", type=Path)
    args = parser.parse_args()
    print(json.dumps(replay(args.output, args.contract), indent=2, allow_nan=False))
