"""Build and validate the no-solve WP07-D structural V&V preflight plan."""

from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp07d_structural_vnv_contract.json"
MESH_LEVELS = ("M1", "M2", "M3")
BENCHMARKS = {
    "ACTIVE_SET": "linear_static",
    "PENALTY": "geometric_nonlinear_static",
}


def _git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def accumulate_constant_t3_traction(
    nodes: Any,
    triangular_faces: Any,
    traction: Any,
) -> np.ndarray:
    """Assemble consistent nodal forces for constant traction on T3 faces."""

    coordinates = np.asarray(nodes, dtype=float)
    faces = tuple(tuple(int(index) for index in face) for face in triangular_faces)
    vector = np.asarray(traction, dtype=float)
    if coordinates.ndim != 2 or coordinates.shape[1] != 3:
        raise ValueError("Surface nodes must have shape (n, 3).")
    if vector.shape != (3,) or not np.all(np.isfinite(vector)):
        raise ValueError("Surface traction must be a finite 3-vector.")
    forces = np.zeros_like(coordinates)
    for face in faces:
        if len(face) != 3 or any(index < 0 or index >= len(coordinates) for index in face):
            raise ValueError("Every surface face must contain three valid node indices.")
        first, second, third = coordinates[list(face)]
        area = 0.5 * float(np.linalg.norm(np.cross(second - first, third - first)))
        if not np.isfinite(area) or area <= 0.0:
            raise ValueError("Every surface face must have positive finite area.")
        forces[list(face)] += vector * area / 3.0
    return forces


def resultant_and_moment(nodes: Any, nodal_forces: Any) -> tuple[np.ndarray, np.ndarray]:
    """Return the global resultant and origin moment of nodal forces."""

    coordinates = np.asarray(nodes, dtype=float)
    forces = np.asarray(nodal_forces, dtype=float)
    if coordinates.shape != forces.shape or coordinates.ndim != 2 or coordinates.shape[1] != 3:
        raise ValueError("Nodes and nodal forces must have matching shape (n, 3).")
    if not np.all(np.isfinite(coordinates)) or not np.all(np.isfinite(forces)):
        raise ValueError("Nodes and nodal forces must be finite.")
    resultant = np.array(
        [math.fsum(float(value) for value in forces[:, component]) for component in range(3)],
        dtype=float,
    )
    cross_products = np.cross(coordinates, forces)
    moment = np.array(
        [math.fsum(float(value) for value in cross_products[:, component]) for component in range(3)],
        dtype=float,
    )
    return resultant, moment


def check_load_contract(
    nodes: Any,
    triangular_faces: Any,
    traction: Any,
    expected_resultant: Any,
    expected_moment: Any,
    *,
    tolerance: float = 1.0e-12,
) -> dict[str, Any]:
    """Check deterministic T3 load conservation without running a solve."""

    forces = accumulate_constant_t3_traction(nodes, triangular_faces, traction)
    resultant, moment = resultant_and_moment(nodes, forces)
    reference_resultant = np.asarray(expected_resultant, dtype=float)
    reference_moment = np.asarray(expected_moment, dtype=float)
    resultant_error = float(np.max(np.abs(resultant - reference_resultant)))
    moment_error = float(np.max(np.abs(moment - reference_moment)))
    return {
        "nodal_forces": forces,
        "resultant": resultant,
        "moment": moment,
        "resultant_error": resultant_error,
        "moment_error": moment_error,
        "pass": resultant_error <= tolerance and moment_error <= tolerance,
    }


def load_contract() -> dict[str, Any]:
    """Load the frozen WP07-D contract."""

    with CONTRACT_PATH.open(encoding="utf-8") as stream:
        contract = json.load(stream)
    if not isinstance(contract, dict):
        raise ValueError("WP07-D contract root must be an object.")
    return contract


def validate_contract(contract: dict[str, Any]) -> None:
    """Fail closed if the frozen contract cannot describe six future cases."""

    if contract.get("work_package") != "WP07-D":
        raise ValueError("Unexpected WP07-D work package.")
    levels = tuple(item.get("id") for item in contract.get("mesh_levels", []))
    if levels != MESH_LEVELS:
        raise ValueError("WP07-D requires exactly M1, M2 and M3 in order.")
    benchmarks = contract.get("benchmarks")
    if not isinstance(benchmarks, dict) or tuple(benchmarks) != tuple(BENCHMARKS):
        raise ValueError("WP07-D requires ACTIVE_SET and PENALTY benchmarks.")
    for benchmark_name, route in BENCHMARKS.items():
        benchmark = benchmarks[benchmark_name]
        if benchmark.get("route") != route:
            raise ValueError(f"Unexpected route for {benchmark_name}.")
        if tuple(benchmark.get("mesh_levels", [])) != MESH_LEVELS:
            raise ValueError(f"{benchmark_name} must declare all three mesh levels.")
    execution = contract.get("execution_policy", {})
    if execution.get("structural_solves_allowed") is not False:
        raise ValueError("Structural solves must remain disabled during preparation.")
    if execution.get("external_solver_allowed") is not False:
        raise ValueError("External solver execution must remain disabled during preparation.")
    thresholds = contract.get("thresholds", {})
    mesh_thresholds = thresholds.get("mesh_m2_to_m3", {})
    required_mesh_thresholds = {
        "selected_displacement_relative",
        "reaction_resultant_relative",
        "reaction_moment_relative",
        "contact_resultant_relative",
    }
    equilibrium = thresholds.get("equilibrium", {})
    if not required_mesh_thresholds.issubset(mesh_thresholds) or not {
        "force_relative",
        "moment_relative",
    }.issubset(equilibrium):
        raise ValueError("WP07-D threshold set is incomplete.")


def build_preflight(
    contract: dict[str, Any],
    *,
    source_sha: str | None = None,
    worktree_dirty: bool | None = None,
) -> dict[str, Any]:
    """Build a deterministic, explicitly no-solve execution plan."""

    validate_contract(contract)
    resolved_sha = source_sha or _git("rev-parse", "HEAD")
    dirty = bool(_git("status", "--porcelain")) if worktree_dirty is None else worktree_dirty
    planned_cases = [
        {
            "case_id": f"WP07D-{benchmark_name}-{level}",
            "benchmark": benchmark_name,
            "route": route,
            "mesh_level": level,
            "status": "NOT_EXECUTED",
            "output_path": f"qualification/0_2_9/wp07d_runs/{benchmark_name.lower()}/{level.lower()}.json",
        }
        for benchmark_name, route in BENCHMARKS.items()
        for level in MESH_LEVELS
    ]
    return {
        "schema_version": 1,
        "record_type": "WP07-D_PREPARATION_PREFLIGHT",
        "status": "PREPARATION_ONLY",
        "source_sha": resolved_sha,
        "worktree_dirty": dirty,
        "environment": {"python": sys.version.split()[0], "platform": platform.platform()},
        "planned_cases": planned_cases,
        "replay_cases": ["WP07D-ACTIVE_SET-M2", "WP07D-PENALTY-M1"],
        "reference_comparison": "deferred until formulation-compatible reference is available",
        "capture_fields": [
            "wall_time_s",
            "peak_rss_process",
            "peak_private_or_uss_process",
            "result_json",
            "evidence_manifest",
        ],
        "execution_guard": {
            "structural_solves_enabled": False,
            "external_solver_enabled": False,
            "reason": "WP07-D contract preparation waits for WP04 M3 completion.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional preflight JSON path.")
    args = parser.parse_args()
    preflight = build_preflight(load_contract())
    rendered = json.dumps(preflight, indent=2, sort_keys=True, default=str)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
