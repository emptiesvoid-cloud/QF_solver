"""Execute one frozen WP05-C/D high-order structural qualification case.

This is qualification tooling only.  Meshes, loads and observables are
delegated to the frozen WP05 preparation harness; equilibrium is solved by
the existing Total-Lagrangian production solver.
"""

# This script prepends the checkout's src tree before importing the package.
# ruff: noqa: E402

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter, process_time
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
for import_root in (str(ROOT), str(SOURCE_ROOT)):
    if import_root in sys.path:
        sys.path.remove(import_root)
    sys.path.insert(0, import_root)

from scripts.wp05_cd_structural_harness import (
    CONTRACT_JSON,
    MESH_LEVELS,
    StructuralBenchmarkContract,
    build_mesh,
    check_load_conservation,
    mesh_quality,
    nodal_load_vector,
)
from solveur.core.analyses.geometric_nonlinear import _newton_dead_load
from solveur.core.model import FiniteElementModel


DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_9" / "overnight_r2" / "wp05_runs"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _git_branch() -> str:
    return subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()


def _policy_digest(contract: StructuralBenchmarkContract) -> str:
    value = {
        "linear_solver": "minres",
        "linear_preconditioner": "jacobi",
        "linear_rtol": 1.0e-11,
        "linear_atol": 1.0e-14,
        "linear_maxiter": 10_000,
        "linear_direct_fallback": False,
        "line_search": "existing",
        "floor_aware_termination": True,
        "tolerance": 1.0e-10,
        "load_increments": 12,
        "contract_digest": _sha256(CONTRACT_JSON),
        "mesh_thresholds": dict(contract.mesh_thresholds),
    }
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _model(family: str, level: str, contract: StructuralBenchmarkContract) -> tuple[FiniteElementModel, Any, np.ndarray, np.ndarray]:
    mesh = build_mesh(family, level, contract)
    loads = nodal_load_vector(mesh, contract)
    fixed_nodes = np.flatnonzero(np.isclose(mesh.coordinates[:, 0], 0.0, rtol=0.0, atol=1.0e-13))
    fixed = [{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes]
    nodal_loads = [
        {"node": int(node), "dof": name, "value": float(loads[node, component])}
        for node in range(mesh.nodes)
        for component, name in enumerate(("UX", "UY", "UZ"))
        if loads[node, component] != 0.0
    ]
    parameters: dict[str, Any] = {
        "load_increments": 12,
        "tolerance": 1.0e-10,
        "max_iterations": 40,
        "nonlinear_assembly_chunk_size": 256,
    }
    if family == "TET10":
        parameters["tet10_nonlinear_quadrature"] = "hammer4"
    model = FiniteElementModel.from_raw(
        nodes=mesh.coordinates.tolist(),
        elements=[{"type": family, "nodes": list(nodes), "material": "solid"} for nodes in mesh.connectivity],
        materials={"solid": {"type": "isotropic_3d", "E": contract.young_modulus, "nu": contract.poisson_ratio}},
        fixed_dofs=fixed,
        loads=nodal_loads,
        analysis={"type": "geometric_nonlinear_static", "method": "newton_raphson", "parameters": parameters},
        units={"system": "SI"},
    )
    return model, mesh, loads, fixed_nodes


def _observables(model: FiniteElementModel, mesh: Any, loads: np.ndarray, fixed_nodes: np.ndarray, displacement: np.ndarray) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    from solveur.core.assembly.geometric import build_total_lagrangian_assembly

    assembly = build_total_lagrangian_assembly(model)
    internal, _ = assembly.assemble(displacement, tangent_required=False)
    fixed = np.concatenate([3 * fixed_nodes + component for component in range(3)]).astype(int)
    reactions = np.zeros_like(internal)
    reactions[fixed] = internal[fixed] - loads.reshape(-1)[fixed]
    deformed = mesh.coordinates + displacement.reshape(-1, 3)
    reaction_vectors = reactions.reshape(-1, 3)
    external_vectors = loads
    external_resultant = np.sum(external_vectors, axis=0)
    reaction_resultant = np.sum(reaction_vectors, axis=0)
    external_moment = np.sum(np.cross(deformed, external_vectors), axis=0)
    reaction_moment = np.sum(np.cross(deformed, reaction_vectors), axis=0)
    element_states = assembly.element_states(displacement)
    centroids = np.asarray([np.mean(mesh.coordinates[list(nodes)], axis=0) for nodes in mesh.connectivity])
    region = (
        (centroids[:, 0] / 4.0 >= 0.40) & (centroids[:, 0] / 4.0 <= 0.60)
        & (centroids[:, 1] / 0.5 >= 0.70) & (centroids[:, 1] / 0.5 <= 0.95)
        & (centroids[:, 2] / 0.5 >= 0.20) & (centroids[:, 2] / 0.5 <= 0.80)
    )
    stress_region_status = "FROZEN_CENTROID_REGION"
    if not np.any(region):
        # The coarsest H1 mesh has no element centroid in the frozen volume
        # even though its integration points cover it.  Keep H1 executable as
        # a preflight and mark its centroid proxy explicitly; H2/H3 use the
        # frozen region without this proxy.
        distance = np.sum((centroids - np.array([2.0, 0.4125, 0.25])) ** 2, axis=1)
        region[np.argmin(distance)] = True
        stress_region_status = "H1_CENTROID_PROXY_SUPPORT_ONLY"
    volumes = []
    det_values: list[float] = []
    stretch_values: list[np.ndarray] = []
    green_values: list[float] = []
    stress_values = []
    for index, kernel in enumerate(assembly._kernels):
        local = displacement[assembly.element_dofs[index]]
        points = kernel.integration_point_results(mesh.coordinates[assembly.elements[index]], local)
        volumes.append(sum(float(point["weight"]) for point in points))
        for point in points:
            deformation = np.asarray(point["deformation_gradient"], dtype=float)
            det_values.append(float(point["det_f"]))
            stretch_values.append(np.linalg.svd(deformation, compute_uv=False))
            green_values.append(float(np.linalg.norm(np.asarray(point["green_lagrange_strain"], dtype=float))))
        stress_values.append(float(element_states["cauchy_stress"][index, 0, 0]))
    volumes_array = np.asarray(volumes, dtype=float)
    representative_stress = float(np.dot(volumes_array[region], np.asarray(stress_values)[region]) / np.sum(volumes_array[region]))
    tip = np.mean(displacement[np.asarray(mesh.end_face_nodes) * 3 + 1])
    force_imbalance = external_resultant + reaction_resultant
    moment_imbalance = external_moment + reaction_moment
    force_scale = max(float(np.linalg.norm(external_resultant)), float(np.linalg.norm(reaction_resultant)), 1.0)
    moment_scale = max(float(np.linalg.norm(external_moment)), float(np.linalg.norm(reaction_moment)), 1.0)
    observed = {
        "tip_displacement": float(tip),
        "reaction_resultant": reaction_resultant.tolist(),
        "reaction_moment": reaction_moment.tolist(),
        "strain_energy": float(assembly.strain_energy(displacement)),
        "representative_sigma_xx": representative_stress,
        "stress_region_status": stress_region_status,
        "minimum_detF": float(np.min(det_values)),
        "minimum_principal_stretch": float(np.min(stretch_values)),
        "maximum_principal_stretch": float(np.max(stretch_values)),
        "maximum_green_lagrange_norm": float(np.max(green_values)),
        "external_resultant": external_resultant.tolist(),
        "external_moment": external_moment.tolist(),
        "force_equilibrium_relative": float(np.linalg.norm(force_imbalance) / force_scale),
        "moment_equilibrium_relative": float(np.linalg.norm(moment_imbalance) / moment_scale),
        "envelope_status": bool(
            np.min(det_values) >= 0.20
            and np.min(stretch_values) >= 0.75
            and np.max(stretch_values) <= 1.30
            and np.max(green_values) <= 0.30
        ),
    }
    arrays = {
        "coordinates": np.asarray(mesh.coordinates, dtype=np.float64),
        "connectivity": np.asarray(mesh.connectivity, dtype=np.int64),
        "loads": np.asarray(loads, dtype=np.float64),
        "displacement": np.asarray(displacement, dtype=np.float64),
        "reactions": np.asarray(reactions, dtype=np.float64),
        "detF": np.asarray(det_values, dtype=np.float64),
        "principal_stretches": np.asarray(stretch_values, dtype=np.float64),
        "green_lagrange_norm": np.asarray(green_values, dtype=np.float64),
    }
    return observed, arrays


def run_case(family: str, level: str, output: Path) -> dict[str, Any]:
    contract = StructuralBenchmarkContract()
    mesh = build_mesh(family, level, contract)
    case_dir = output / family / level
    case_dir.mkdir(parents=True, exist_ok=True)
    result_path = case_dir / "result.json"
    raw_path = case_dir / "raw.npz"
    started = perf_counter()
    cpu_started = process_time()
    payload: dict[str, Any] = {
        "status": "RUNNING",
        "source_sha": _git_sha(),
        "branch_at_capture": _git_branch(),
        "evidence_schema_version": 2,
        "contract_sha256": _sha256(CONTRACT_JSON),
        "governing_policy_digest": _policy_digest(contract),
        "contract_path": str(CONTRACT_JSON.relative_to(ROOT)).replace("\\", "/"),
        "family": family,
        "mesh_level": level,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "node_count": mesh.nodes,
        "element_count": mesh.elements,
        "dof_count": mesh.dofs,
        "mesh_quality": mesh_quality(mesh),
        "load_check": check_load_conservation(mesh, contract),
        "solver_route": "geometric_nonlinear_static / MINRES + Jacobi / canonical line search / floor-aware termination",
        "thresholds": dict(contract.mesh_thresholds),
    }
    _write_json(result_path, payload)
    try:
        model, mesh, loads, fixed_nodes = _model(family, level, contract)
        from solveur.core.assembly.geometric import build_total_lagrangian_assembly
        from solveur.core.nonlinear.robustness import NonlinearRobustnessOptions

        assembly = build_total_lagrangian_assembly(model)
        fixed = np.concatenate([3 * fixed_nodes + component for component in range(3)]).astype(int)
        options = NonlinearRobustnessOptions(
            linear_solver="minres",
            linear_preconditioner="jacobi",
            linear_rtol=1.0e-11,
            linear_atol=1.0e-14,
            linear_maxiter=10_000,
            linear_residual_tolerance=1.0e-10,
            linear_backward_error_tolerance=1.0e-10,
            linear_direct_fallback=False,
            line_search="existing",
            floor_aware_termination=True,
        )
        options.validate()
        displacement, diagnostics = _newton_dead_load(
            assembly,
            loads.reshape(-1),
            fixed,
            increments=12,
            tolerance=1.0e-10,
            max_iterations=40,
            determinant_assembly=assembly,
            robustness_options=options,
        )
        observed, arrays = _observables(model, mesh, loads, fixed_nodes, displacement)
        np.savez_compressed(raw_path, **arrays)  # type: ignore[arg-type]
        payload.update(
            {
                "status": "PASS",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "wall_time_s": perf_counter() - started,
                "cpu_time_s": process_time() - cpu_started,
                "observables": observed,
                "solver_diagnostics": diagnostics,
                "raw_npz": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
                "raw_sha256": _sha256(raw_path),
                "accepted_load_factors": [item.get("load_factor") for item in diagnostics.get("increments", []) if isinstance(item, dict)],
                "newton_iterations": sum(int(item.get("iterations", 0)) for item in diagnostics.get("increments", []) if isinstance(item, dict)),
                "fallback_count": sum(int(item.get("fallback_count", 0)) for item in diagnostics.get("increments", []) if isinstance(item, dict)),
            }
        )
    except Exception as exc:
        payload.update(
            {
                "status": "FAILED",
                "terminal_classification": type(exc).__name__,
                "error": str(exc),
                "wall_time_s": perf_counter() - started,
                "cpu_time_s": process_time() - cpu_started,
            }
        )
    _write_json(result_path, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", choices=("TET10", "HEX20"), required=True)
    parser.add_argument("--mesh", choices=tuple(level.name for level in MESH_LEVELS), required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run_case(args.family, args.mesh, args.output.resolve())
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
