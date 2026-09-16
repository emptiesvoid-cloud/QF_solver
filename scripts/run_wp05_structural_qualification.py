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
    sample_region_weighted_sigma_xx,
)
from solveur.core.analyses.geometric_nonlinear import _newton_dead_load
from solveur.core.model import FiniteElementModel
from solveur.elements.solid.hex20 import Hex20Element
from solveur.elements.solid.tet10 import Tet10Element


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


def _model_from_mesh(
    family: str,
    mesh: Any,
    contract: StructuralBenchmarkContract,
) -> tuple[FiniteElementModel, Any, np.ndarray, np.ndarray]:
    """Build the frozen solver model for an already-constructed mesh."""
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


def _model(family: str, level: str, contract: StructuralBenchmarkContract) -> tuple[FiniteElementModel, Any, np.ndarray, np.ndarray]:
    return _model_from_mesh(family, build_mesh(family, level, contract), contract)


def _integration_records(assembly: Any, displacement: np.ndarray) -> list[dict[str, Any]]:
    """Return the frozen reference-coordinate integration-point observables.

    The production assembly already owns the constitutive and kinematic
    evaluation.  This qualification-only adapter adds the reference physical
    location and reference-volume weight required by the WP05 stress contract;
    it deliberately does not create an element-level centroid proxy.
    """
    records: list[dict[str, Any]] = []
    family = str(assembly.element_type)
    for element_index, kernel in enumerate(assembly._kernels):
        element_nodes = assembly.elements[element_index]
        coordinates = assembly.nodes[element_nodes]
        local = displacement[assembly.element_dofs[element_index]]
        points = kernel.integration_point_results(coordinates, local)
        if family == "TET10":
            natural_points = [point for point, _ in kernel._rule()]
            shape_functions = [Tet10Element.shape_functions(point) for point in natural_points]
        elif family == "HEX20":
            natural_points = list(Hex20Element.integration_points)
            shape_functions = [Hex20Element.shape_functions(point) for point in natural_points]
        else:
            raise ValueError(f"Unsupported WP05 integration-record family {family!r}.")
        reference_data = kernel._cached_reference_data(coordinates)
        if len(points) != len(shape_functions) or len(points) != len(reference_data):
            raise ValueError("Production integration data and qualification sampling data differ.")
        for point, shape, (measure, _) in zip(points, shape_functions, reference_data, strict=True):
            reference_coordinates = np.asarray(shape, dtype=float) @ coordinates
            records.append(
                {
                    "element_index": element_index,
                    "integration_point_index": int(point["index"]),
                    "natural_coordinates": np.asarray(natural_points[int(point["index"])], dtype=float).tolist(),
                    "reference_coordinates": reference_coordinates.tolist(),
                    "reference_volume_weight": float(measure),
                    "deformation_gradient": point["deformation_gradient"],
                    "green_lagrange_strain": point["green_lagrange_strain"],
                    "second_piola_stress": point["second_piola_stress"],
                    "cauchy_stress": point["cauchy_stress"],
                    "det_f": float(point["det_f"]),
                }
            )
    return records


def _observables(model: FiniteElementModel, mesh: Any, loads: np.ndarray, fixed_nodes: np.ndarray, displacement: np.ndarray) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    from solveur.core.assembly.geometric import build_total_lagrangian_assembly

    contract = StructuralBenchmarkContract()
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
    volumes = []
    det_values: list[float] = []
    stretch_values: list[np.ndarray] = []
    green_values: list[float] = []
    records = _integration_records(assembly, displacement)
    for record in records:
        deformation = np.asarray(record["deformation_gradient"], dtype=float)
        det_values.append(float(record["det_f"]))
        stretch_values.append(np.linalg.svd(deformation, compute_uv=False))
        green_values.append(float(np.linalg.norm(np.asarray(record["green_lagrange_strain"], dtype=float))))
        volumes.append(float(record["reference_volume_weight"]))
    representative_stress = sample_region_weighted_sigma_xx(records, contract)
    stress_region_records = [
        record
        for record in records
        if (
            contract.sample_region[0][0] <= float(record["reference_coordinates"][0]) / contract.length <= contract.sample_region[0][1]
            and contract.sample_region[1][0] <= float(record["reference_coordinates"][1]) / contract.height <= contract.sample_region[1][1]
            and contract.sample_region[2][0] <= float(record["reference_coordinates"][2]) / contract.depth <= contract.sample_region[2][1]
        )
    ]
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
        "stress_region_status": "FROZEN_INTEGRATION_POINT_REFERENCE_VOLUME",
        "stress_region_integration_point_count": len(stress_region_records),
        "stress_region_reference_volume": float(sum(float(record["reference_volume_weight"]) for record in stress_region_records)),
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
        "integration_reference_coordinates": np.asarray(
            [record["reference_coordinates"] for record in records], dtype=np.float64
        ),
        "integration_volume_weights": np.asarray(volumes, dtype=np.float64),
        "integration_cauchy_stress": np.asarray(
            [record["cauchy_stress"] for record in records], dtype=np.float64
        ),
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


