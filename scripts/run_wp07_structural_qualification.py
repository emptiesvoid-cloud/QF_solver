"""Execute one frozen WP07-D contact case; qualification tooling only."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for import_root in (str(ROOT), str(SRC)):
    if import_root in sys.path:
        sys.path.remove(import_root)
    sys.path.insert(0, import_root)

from scripts.prepare_wp07d_structural_vnv import (  # noqa: E402
    EXPECTED_MOMENT,
    EXPECTED_RESULTANT,
    MASTER_NODES,
    TRACTION,
    _triangle_area,
    generate_structured_tet4_mesh,
)
from solveur.api import solve_model  # noqa: E402
from solveur.core.model import FiniteElementModel  # noqa: E402


DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_9" / "overnight_r2" / "wp07_runs"
CONTRACT = ROOT / "qualification" / "0_2_9" / "wp07d_structural_vnv_contract.json"


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _build(level: str, route: str) -> tuple[FiniteElementModel, np.ndarray, np.ndarray]:
    mesh = generate_structured_tet4_mesh(level)
    nodes = np.vstack((mesh.nodes, MASTER_NODES))
    master_offset = len(mesh.nodes)
    loads: np.ndarray = np.zeros((len(nodes), 3), dtype=float)
    for face in mesh.top_faces:
        area = _triangle_area(mesh.nodes[list(face)])
        for node in face:
            loads[node] += TRACTION * area / 3.0
    fixed = [
        {"node": int(node), "dofs": ["UX", "UY", "UZ"]}
        for node, point in enumerate(mesh.nodes)
        if abs(float(point[0])) <= 1.0e-14
    ]
    fixed.extend({"node": master_offset + i, "dofs": ["UX", "UY", "UZ"]} for i in range(3))
    nodal_loads = [
        {"node": int(node), "dof": dof, "value": float(loads[node, component])}
        for node in range(len(nodes))
        for component, dof in enumerate(("UX", "UY", "UZ"))
        if loads[node, component] != 0.0
    ]
    contacts = [{
        "name": "wp07d_master",
        "slave_node": int(mesh.slave_nodes[0]),
        "slave_patch_nodes": [int(node) for node in mesh.slave_nodes],
        "master_nodes": [master_offset, master_offset + 1, master_offset + 2],
        "master_faces": [[master_offset, master_offset + 1, master_offset + 2]],
        "friction_coefficient": 0.0,
    }]
    parameters: dict[str, Any] = {"contact_search_mode": "initial"}
    analysis_type = "linear_static"
    method = "direct"
    if route == "PENALTY":
        analysis_type = "geometric_nonlinear_static"
        method = "newton_raphson"
        parameters.update({
            "load_increments": 8,
            "tolerance": 1.0e-10,
            "max_iterations": 40,
            "contact_mode": "penalty",
            "contact_penalty": 1.0e8,
            "experimental_linear_solver": "minres",
            "experimental_linear_preconditioner": "jacobi",
            "experimental_linear_rtol": 1.0e-11,
            "experimental_linear_atol": 1.0e-14,
            "experimental_linear_maxiter": 10000,
            "experimental_linear_direct_fallback": False,
            "experimental_linear_backward_error_tolerance": 1.0e-10,
            "experimental_line_search": "existing",
            "experimental_floor_aware_termination": True,
        })
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "TET4", "nodes": list(element), "material": "solid"} for element in mesh.elements],
        materials={"solid": {"type": "isotropic_3d", "E": 1.0e6, "nu": 0.30}},
        fixed_dofs=fixed,
        loads=nodal_loads,
        contacts=contacts,
        analysis={"type": analysis_type, "method": method, "parameters": parameters},
        units={"system": "SI"},
    )
    return model, mesh.nodes, loads


def run_case(level: str, route: str, output: Path) -> dict[str, Any]:
    model, body_nodes, loads = _build(level, route)
    target = output / route / level
    result_path = target / "result.json"
    raw_path = target / "raw.npz"
    started = perf_counter()
    payload: dict[str, Any] = {
        "status": "RUNNING",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "contract_path": str(CONTRACT.relative_to(ROOT)).replace("\\", "/"),
        "route": route,
        "mesh_level": level,
        "node_count": model.node_count,
        "element_count": len(model.elements),
        "dof_count": model.dof_manager().ndof,
        "expected_resultant": EXPECTED_RESULTANT.tolist(),
        "expected_moment": EXPECTED_MOMENT.tolist(),
    }
    _write(result_path, payload)
    try:
        result = solve_model(model)
        displacement = np.asarray(result.displacements, dtype=float)
        np.savez_compressed(raw_path, body_nodes=body_nodes, loads=loads, displacement=displacement)
        payload.update({
            "status": "PASS",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "wall_time_s": perf_counter() - started,
            "solver": result.solver,
            "raw_npz": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
            "raw_sha256": _sha(raw_path),
        })
    except Exception as exc:
        payload.update({"status": "FAILED", "terminal_classification": type(exc).__name__, "error": str(exc), "wall_time_s": perf_counter() - started})
    _write(result_path, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--route", choices=("ACTIVE_SET", "PENALTY"), required=True)
    parser.add_argument("--mesh", choices=("M1", "M2", "M3"), required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run_case(args.mesh, args.route, args.output)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
