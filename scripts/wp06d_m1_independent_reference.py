"""Independent post-processing proof for a WP06-D M1 accepted path.

This module deliberately does not import ``solveur`` or any production runner.
It consumes only the frozen mesh archive and the lossless accepted displacement
path.  It recomputes the TET4 StVK internal force, energy, deformation
envelope, force balance, and both moment conventions.  The current-coordinate
moment is the primary equilibrium observable; the reference-coordinate moment
is retained as a diagnostic because dead loads are evaluated at the current
support/load positions in the spatial equilibrium check.

This is an independent observable recomputation, not an independent nonlinear
arc-length path solve.  It therefore cannot by itself authorize M2/M3 or
formal WP06-D points.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable

import numpy as np


DEFAULT_FORCE_TOLERANCE = 1.0e-8
DEFAULT_MOMENT_TOLERANCE = 1.0e-8
DEFAULT_COMPARISON_RTOL = 2.0e-10
DEFAULT_COMPARISON_ATOL = 1.0e-13


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def _finite_array(value: Any, *, shape: tuple[int, ...], name: str) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must have shape {shape} and contain finite values.")
    return array


def _load_mesh(path: Path) -> dict[str, np.ndarray]:
    required = {
        "nodes",
        "elements",
        "grid_ijk",
        "left_support_nodes",
        "right_support_nodes",
        "nodal_reference_loads",
        "target_resultant",
    }
    with np.load(path, allow_pickle=False) as archive:
        missing = required.difference(archive.files)
        if missing:
            raise ValueError(f"Mesh archive is missing fields: {sorted(missing)}")
        mesh = {key: np.asarray(archive[key]).copy() for key in archive.files}
    nodes = mesh["nodes"]
    elements = mesh["elements"]
    if nodes.ndim != 2 or nodes.shape[1] != 3 or not np.all(np.isfinite(nodes)):
        raise ValueError("Mesh nodes must be a finite N x 3 array.")
    if elements.ndim != 2 or elements.shape[1] != 4:
        raise ValueError("Independent reference requires TET4 connectivity.")
    if not np.issubdtype(elements.dtype, np.integer):
        raise ValueError("TET4 connectivity must use integer node identifiers.")
    if np.any(elements < 0) or np.any(elements >= len(nodes)):
        raise ValueError("TET4 connectivity references an invalid node.")
    if mesh["nodal_reference_loads"].shape != nodes.shape:
        raise ValueError("Nodal reference loads must have the same shape as nodes.")
    if not np.all(np.isfinite(mesh["nodal_reference_loads"])):
        raise ValueError("Nodal reference loads contain non-finite values.")
    resultant = np.sum(mesh["nodal_reference_loads"], axis=0)
    if not np.allclose(resultant, mesh["target_resultant"], rtol=0.0, atol=1.0e-12):
        raise ValueError("Nodal reference loads do not reproduce target resultant.")
    return mesh


def _support_dofs(mesh: dict[str, np.ndarray]) -> np.ndarray:
    support_nodes = np.unique(
        np.concatenate((mesh["left_support_nodes"], mesh["right_support_nodes"]))
    ).astype(int)
    if support_nodes.size == 0:
        raise ValueError("Independent reference requires non-empty support sets.")
    dofs = (3 * support_nodes[:, None] + np.arange(3, dtype=int)).reshape(-1)
    return np.unique(dofs)


def _q_node_ids(mesh: dict[str, np.ndarray], grid_ijk: Iterable[Iterable[int]]) -> tuple[int, ...]:
    grid = np.asarray(mesh["grid_ijk"])
    identifiers: list[int] = []
    for coordinate in grid_ijk:
        target = np.asarray(tuple(int(value) for value in coordinate), dtype=grid.dtype)
        matches = np.flatnonzero(np.all(grid == target, axis=1))
        if matches.size != 1:
            raise ValueError(f"Monitor coordinate {tuple(target)} is not unique.")
        identifiers.append(int(matches[0]))
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Independent monitor contains duplicate nodes.")
    return tuple(identifiers)


def _vectorized_stvk_internal_response(
    nodes: np.ndarray,
    elements: np.ndarray,
    displacement: np.ndarray,
    *,
    young_modulus: float,
    poisson_ratio: float,
) -> tuple[np.ndarray, float, np.ndarray, np.ndarray, np.ndarray]:
    """Return internal force and envelope quantities without production calls."""

    if displacement.shape != (3 * len(nodes),) or not np.all(np.isfinite(displacement)):
        raise ValueError("Displacement vector has an invalid shape or non-finite values.")
    jacobian = np.transpose(
        nodes[elements][:, 1:, :] - nodes[elements][:, :1, :], (0, 2, 1)
    )
    determinant = np.linalg.det(jacobian)
    if not np.all(np.isfinite(determinant)) or np.any(determinant <= 0.0):
        raise ValueError("Independent reference found a non-positive TET4 orientation.")
    gradients: np.ndarray = np.empty((len(elements), 4, 3), dtype=float)
    gradients[:, 1:, :] = np.linalg.inv(jacobian)
    gradients[:, 0, :] = -np.sum(gradients[:, 1:, :], axis=1)
    volumes = determinant / 6.0
    u_nodes = displacement.reshape((-1, 3))
    u_elements = u_nodes[elements]
    identity = np.eye(3)
    deformation = identity[None, :, :] + np.einsum(
        "eai,eaj->eij", u_elements, gradients, optimize=True
    )
    det_f = np.linalg.det(deformation)
    if not np.all(np.isfinite(det_f)) or np.any(det_f <= 0.0):
        raise ValueError("Independent reference found a non-positive det(F).")
    right_cauchy_green = np.einsum(
        "eki,ekj->eij", deformation, deformation, optimize=True
    )
    green = 0.5 * (right_cauchy_green - identity[None, :, :])
    trace_green = np.trace(green, axis1=1, axis2=2)
    lame_lambda = young_modulus * poisson_ratio / (
        (1.0 + poisson_ratio) * (1.0 - 2.0 * poisson_ratio)
    )
    shear = young_modulus / (2.0 * (1.0 + poisson_ratio))
    second_piola = (
        lame_lambda * trace_green[:, None, None] * identity[None, :, :]
        + 2.0 * shear * green
    )
    first_piola = np.einsum("eik,ekj->eij", deformation, second_piola, optimize=True)
    local_force = volumes[:, None, None] * np.einsum(
        "eij,eaj->eai", first_piola, gradients, optimize=True
    )
    internal_force: np.ndarray = np.zeros(3 * len(nodes), dtype=float)
    dofs = (3 * elements[:, :, None] + np.arange(3, dtype=int)).reshape(-1)
    np.add.at(internal_force, dofs, local_force.reshape(-1))
    energy_density = 0.5 * lame_lambda * trace_green**2 + shear * np.einsum(
        "eij,eij->e", green, green
    )
    principal = np.sqrt(np.maximum(np.linalg.eigvalsh(right_cauchy_green), 0.0))
    strain_norm = np.linalg.norm(green, axis=(1, 2))
    return (
        internal_force,
        float(np.sum(volumes * energy_density)),
        det_f,
        principal,
        strain_norm,
    )


def _first_limit_point(
    steps: np.ndarray, load_factors: np.ndarray, q_values: np.ndarray
) -> dict[str, Any] | None:
    for index in range(1, len(steps) - 1):
        before = index - 1
        after = index + 1
        if (
            load_factors[index] > load_factors[before]
            and load_factors[after] <= load_factors[index]
            and q_values[before] < q_values[index] < q_values[after]
        ):
            endpoint = index + 6
            return {
                "state_index_zero_based": index,
                "peak_step": int(steps[index]),
                "peak_load_factor": float(load_factors[index]),
                "peak_q": float(q_values[index]),
                "post_limit_endpoint_step": int(steps[endpoint]) if endpoint < len(steps) else None,
            }
    return None


def _compare_scalar(expected: float, observed: float) -> bool:
    return bool(np.isclose(expected, observed, rtol=DEFAULT_COMPARISON_RTOL, atol=DEFAULT_COMPARISON_ATOL))


def audit_campaign(campaign: Path, output: Path | None = None) -> dict[str, Any]:
    """Recompute and audit one existing M1 path; never performs a structural solve."""

    definition_path = campaign / "benchmark_definition.json"
    case_path = campaign / "case" / "case_result.json"
    raw_path = campaign / "case" / "accepted_path_raw.npz"
    mesh_candidates = sorted((campaign / "mesh").glob("*.npz"))
    if len(mesh_candidates) != 1:
        raise ValueError("Expected exactly one mesh NPZ in the campaign mesh directory.")
    mesh_path = mesh_candidates[0]
    for path in (definition_path, case_path, raw_path, mesh_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    definition = json.loads(definition_path.read_text(encoding="utf-8"))
    case = json.loads(case_path.read_text(encoding="utf-8"))
    mesh = _load_mesh(mesh_path)
    with np.load(raw_path, allow_pickle=False) as archive:
        required = {"steps", "load_factors", "displacements"}
        if not required.issubset(archive.files):
            raise ValueError("Accepted path archive is missing required arrays.")
        steps = np.asarray(archive["steps"])
        load_factors = np.asarray(archive["load_factors"], dtype=float)
        displacements = np.asarray(archive["displacements"], dtype=float)

    if steps.ndim != 1 or not np.issubdtype(steps.dtype, np.integer):
        raise ValueError("Accepted steps must be a one-dimensional integer array.")
    if load_factors.shape != steps.shape or displacements.shape != (len(steps), 3 * len(mesh["nodes"])):
        raise ValueError("Accepted path arrays are not aligned with the mesh DOF count.")
    if len(steps) < 3 or np.any(np.diff(steps) != 1):
        raise ValueError("Accepted path must contain consecutive states.")
    if not np.all(np.isfinite(load_factors)) or not np.all(np.isfinite(displacements)):
        raise ValueError("Accepted path contains non-finite values.")

    q_meta = case.get("q_observable", {})
    grid_ijk = q_meta.get("grid_ijk")
    if not isinstance(grid_ijk, list) or len(grid_ijk) != 3:
        raise ValueError("Case does not declare exactly three independent q monitor coordinates.")
    q_nodes = _q_node_ids(mesh, grid_ijk)
    declared_nodes = tuple(int(value) for value in q_meta.get("node_ids", ()))
    if declared_nodes and declared_nodes != q_nodes:
        raise ValueError("Declared q node IDs do not match the mesh grid coordinates.")
    constrained = _support_dofs(mesh)
    nodes = mesh["nodes"]
    elements: np.ndarray = mesh["elements"].astype(np.int64, copy=False)
    external_reference = mesh["nodal_reference_loads"].reshape(-1)
    material = definition.get("material", {})
    young = float(material.get("E", 100.0))
    poisson = float(material.get("nu", 0.30))

    rows: list[dict[str, Any]] = []
    max_differences: dict[str, float] = {}
    recorded_rows = case.get("accepted_path", [])
    if len(recorded_rows) not in (0, len(steps)):
        raise ValueError("Recorded accepted path has a different number of states.")
    for index, (step, load_factor, displacement) in enumerate(
        zip(steps, load_factors, displacements, strict=True)
    ):
        internal, energy, det_f, principal, strain_norm = _vectorized_stvk_internal_response(
            nodes,
            elements,
            displacement,
            young_modulus=young,
            poisson_ratio=poisson,
        )
        external = float(load_factor) * external_reference
        residual = internal - external
        reactions = np.zeros_like(residual)
        reactions[constrained] = residual[constrained]
        nodal_balance = (reactions + external).reshape((-1, 3))
        current_nodes = nodes + displacement.reshape((-1, 3))
        force_balance = np.sum(nodal_balance, axis=0)
        reference_moment = np.sum(np.cross(nodes, nodal_balance), axis=0)
        current_moment = np.sum(np.cross(current_nodes, nodal_balance), axis=0)
        force_scale = max(float(np.linalg.norm(np.sum(external.reshape((-1, 3)), axis=0))), 1.0e-12)
        moment_scale = max(force_scale * 2.0, 1.0e-12)
        q_value = -float(np.mean(displacement.reshape((-1, 3))[list(q_nodes), 2]))
        row = {
            "step": int(step),
            "load_factor": float(load_factor),
            "q": q_value,
            "strain_energy": energy,
            "minimum_det_f": float(np.min(det_f)),
            "minimum_principal_stretch": float(np.min(principal)),
            "maximum_principal_stretch": float(np.max(principal)),
            "maximum_green_strain_frobenius": float(np.max(strain_norm)),
            "free_residual_l2": float(np.linalg.norm(np.delete(residual, constrained))),
            "force_balance_relative": float(np.linalg.norm(force_balance) / force_scale),
            "reference_moment_balance_relative": float(np.linalg.norm(reference_moment) / moment_scale),
            "current_moment_balance_relative": float(np.linalg.norm(current_moment) / moment_scale),
        }
        if recorded_rows:
            recorded = recorded_rows[index]
            comparisons = {
                "load_factor": (float(recorded["load_factor"]), row["load_factor"]),
                "q_mean_crown_nodes_2_3_4": (float(recorded["q_mean_crown_nodes_2_3_4"]), row["q"]),
                "strain_energy_independent_recomputation": (
                    float(recorded["strain_energy_independent_recomputation"]),
                    row["strain_energy"],
                ),
                "current_moment_balance_relative": (
                    float(recorded["current_moment_balance_relative"]),
                    row["current_moment_balance_relative"],
                ),
            }
            for name, (expected, observed) in comparisons.items():
                difference = abs(expected - observed)
                max_differences[name] = max(max_differences.get(name, 0.0), difference)
                if not _compare_scalar(expected, observed):
                    raise ValueError(f"Recorded {name} diverges at step {step}.")
        rows.append(row)

    steps_array = np.asarray([row["step"] for row in rows], dtype=int)
    q_values = np.asarray([row["q"] for row in rows], dtype=float)
    independently_detected = _first_limit_point(steps_array, load_factors, q_values)
    envelope = definition.get("envelope_unchanged", {})
    envelope_checks = [
        row["minimum_det_f"] >= float(envelope.get("det_f_min", 0.20))
        and row["minimum_principal_stretch"] >= float(envelope.get("principal_stretch_min", 0.75))
        and row["maximum_principal_stretch"] <= float(envelope.get("principal_stretch_max", 1.30))
        and row["maximum_green_strain_frobenius"] <= float(envelope.get("green_strain_frobenius_max", 0.30))
        for row in rows
    ]
    equilibrium = {
        "force_max": max(row["force_balance_relative"] for row in rows),
        "current_moment_max": max(row["current_moment_balance_relative"] for row in rows),
        "reference_moment_max_diagnostic": max(
            row["reference_moment_balance_relative"] for row in rows
        ),
        "free_residual_max": max(row["free_residual_l2"] for row in rows),
        "force_tolerance": DEFAULT_FORCE_TOLERANCE,
        "current_moment_tolerance": DEFAULT_MOMENT_TOLERANCE,
        "force_pass": max(row["force_balance_relative"] for row in rows) <= DEFAULT_FORCE_TOLERANCE,
        "current_moment_pass": max(row["current_moment_balance_relative"] for row in rows)
        <= DEFAULT_MOMENT_TOLERANCE,
        "reference_moment_is_diagnostic_only": True,
    }
    limit_pass = (
        independently_detected is not None
        and independently_detected["post_limit_endpoint_step"] is not None
    )
    envelope_pass = bool(all(envelope_checks))
    equilibrium_pass = bool(equilibrium["force_pass"] and equilibrium["current_moment_pass"])
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": (
            "PASS_DIAGNOSTIC_ONLY"
            if limit_pass and envelope_pass and equilibrium_pass
            else "FAIL_CLOSED_DIAGNOSTIC"
        ),
        "evidence_kind": "INDEPENDENT_OBSERVABLE_RECOMPUTATION",
        "formal_requalification_claimed": False,
        "structural_solve_run": False,
        "independent_path_solve_run": False,
        "replay_run": False,
        "campaign": str(campaign),
        "campaign_source_sha256": _sha256(campaign / "campaign_final.json"),
        "mesh_sha256": _sha256(mesh_path),
        "raw_path_sha256": _sha256(raw_path),
        "case_result_sha256": _sha256(case_path),
        "benchmark_definition_sha256": _sha256(definition_path),
        "independent_reference_source": "scripts/wp06d_m1_independent_reference.py",
        "independent_reference_source_sha256": _sha256(Path(__file__).resolve()),
        "accepted_state_count": int(len(rows)),
        "q_monitor": {"grid_ijk": grid_ijk, "node_ids": list(q_nodes)},
        "limit_point": {
            "status": (
                "PASS_INDEPENDENT_RECOMPUTATION_WITH_SIX_POST_LIMIT_STATES"
                if independently_detected is not None
                and independently_detected["post_limit_endpoint_step"] is not None
                else "FAIL_CLOSED_NO_INDEPENDENT_LIMIT_POINT"
            ),
            "result": independently_detected,
            "rule": "local load maximum, q strictly increasing, six accepted post-limit states",
        },
        "envelope": {"full_path_pass": envelope_pass, "checked_states": len(rows)},
        "equilibrium": equilibrium,
        "recorded_comparison": {
            "status": "PASS" if recorded_rows else "NOT_AVAILABLE",
            "max_absolute_differences": max_differences,
            "tolerance": {"rtol": DEFAULT_COMPARISON_RTOL, "atol": DEFAULT_COMPARISON_ATOL},
        },
        "reference_moment_interpretation": (
            "Reference-position X moment is retained for diagnosis only. "
            "The primary equilibrium gate uses current positions X+u, as frozen "
            "by the Owner preparation decision."
        ),
        "source_provenance": {
            "git_branch": _git(campaign.parents[2], "branch", "--show-current"),
            "git_head": _git(campaign.parents[2], "rev-parse", "HEAD"),
        },
    }
    if output is not None:
        if output.exists():
            raise FileExistsError(f"Refusing to overwrite independent evidence: {output}")
        output.mkdir(parents=True)
        result_path = output / "independent_reference_result.json"
        state_path = output / "state_metrics.jsonl"
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        state_path.write_text(
            "".join(json.dumps(row, sort_keys=True, allow_nan=False) + "\n" for row in rows),
            encoding="utf-8",
        )
        manifest = {
            "schema_version": 1,
            "algorithm": "sha256",
            "manifest_excludes_itself": True,
            "files": [
                {
                    "path": result_path.name,
                    "sha256": _sha256(result_path),
                    "size_bytes": result_path.stat().st_size,
                },
                {
                    "path": state_path.name,
                    "sha256": _sha256(state_path),
                    "size_bytes": state_path.stat().st_size,
                },
            ],
        }
        (output / "independent_reference_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path, help="Existing WP06-D campaign directory")
    parser.add_argument("--output", type=Path, required=True, help="New evidence directory")
    args = parser.parse_args()
    result = audit_campaign(args.campaign.resolve(), args.output.resolve())
    print(
        "INDEPENDENT_REFERENCE_STATUS="
        f"{result['status']} limit={result['limit_point']['status']} "
        f"states={result['accepted_state_count']} "
        f"current_moment_max={result['equilibrium']['current_moment_max']:.6e}",
        flush=True,
    )
    return 0 if result["status"] == "PASS_DIAGNOSTIC_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
