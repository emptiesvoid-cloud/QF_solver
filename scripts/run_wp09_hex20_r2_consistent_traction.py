"""Run WP09 HEX20 R2 with consistent QUAD8 traction and 3-D refinement."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.run_wp09_hex20_extension import (  # noqa: E402
    _equilibrium,
    _finite,
    _git,
    _json_default,
    _metrics,
    _relative,
    _sha256,
)
from solveur.api import solve_model  # noqa: E402
from solveur.core.model import FiniteElementModel  # noqa: E402
from solveur.mesh.validation import MeshValidator  # noqa: E402


CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp09_hex20_r2_consistent_traction_contract.json"
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_9" / "wp09_hex20_r2_consistent_traction"
POLICY_DIGEST = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
FAMILY = "HEX20"
LEVELS = (("H1", (1, 1, 1)), ("H2", (2, 2, 2)), ("H3", (3, 3, 3)))
LOAD_SCALE = 0.25
LOAD_PATH = (0.25, 0.5, 0.75, 1.0)
MATERIAL = {
    "type": "von_mises_elastoplastic_3d",
    "E": 1000.0,
    "nu": 0.3,
    "yield_stress": 0.02,
    "hardening_modulus": 10.0,
}
EDGE_ORDER = (
    (0, 1),
    (0, 3),
    (0, 4),
    (1, 2),
    (1, 5),
    (2, 3),
    (2, 6),
    (3, 7),
    (4, 5),
    (4, 7),
    (5, 6),
    (6, 7),
)


def _quad8_shape(r: float, s: float) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(
        [
            -0.25 * (1 - r) * (1 - s) * (1 + r + s),
            -0.25 * (1 + r) * (1 - s) * (1 - r + s),
            -0.25 * (1 + r) * (1 + s) * (1 - r - s),
            -0.25 * (1 - r) * (1 + s) * (1 + r - s),
            0.5 * (1 - r * r) * (1 - s),
            0.5 * (1 + r) * (1 - s * s),
            0.5 * (1 - r * r) * (1 + s),
            0.5 * (1 - r) * (1 - s * s),
        ],
        dtype=float,
    )
    derivatives = np.asarray(
        [
            [0.25 * (1 - s) * (2 * r + s), 0.25 * (1 - r) * (r + 2 * s)],
            [0.25 * (1 - s) * (2 * r - s), -0.25 * (1 + r) * (r - 2 * s)],
            [0.25 * (1 + s) * (2 * r + s), 0.25 * (1 + r) * (r + 2 * s)],
            [0.25 * (1 + s) * (2 * r - s), -0.25 * (1 - r) * (r - 2 * s)],
            [-r * (1 - s), -0.5 * (1 - r * r)],
            [0.5 * (1 - s * s), -(1 + r) * s],
            [-r * (1 + s), 0.5 * (1 - r * r)],
            [-0.5 * (1 - s * s), -(1 - r) * s],
        ],
        dtype=float,
    )
    return values, derivatives


def _mesh(nx: int, ny: int, nz: int) -> tuple[np.ndarray, list[list[int]], list[tuple[int, list[int]]]]:
    node_ids: dict[tuple[float, float, float], int] = {}
    coordinates: list[tuple[float, float, float]] = []

    def node_id(point: np.ndarray | tuple[float, float, float]) -> int:
        key = tuple(round(float(value), 14) for value in point)
        if key not in node_ids:
            node_ids[key] = len(coordinates)
            coordinates.append(key)
        return node_ids[key]

    elements: list[list[int]] = []
    loaded_faces: list[tuple[int, list[int]]] = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                x0, x1 = i / nx, (i + 1) / nx
                y0, y1 = j / ny, (j + 1) / ny
                z0, z1 = k / nz, (k + 1) / nz
                corners = np.asarray(
                    [
                        [x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                        [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1],
                    ],
                    dtype=float,
                )
                corner_ids = [node_id(point) for point in corners]
                midpoint_ids = [
                    node_id(0.5 * (corners[first] + corners[second]))
                    for first, second in EDGE_ORDER
                ]
                element_id = len(elements)
                elements.append(corner_ids + midpoint_ids)
                if i == nx - 1:
                    # x=+1 face, ordered as QUAD8 in (y,z):
                    # corners 1,2,6,5 and mids 1-2,2-6,5-6,1-5.
                    loaded_faces.append(
                        (
                            element_id,
                            [
                                corner_ids[1], corner_ids[2], corner_ids[6], corner_ids[5],
                                midpoint_ids[3], midpoint_ids[6], midpoint_ids[10], midpoint_ids[4],
                            ],
                        )
                    )
    return np.asarray(coordinates, dtype=float), elements, loaded_faces


def _consistent_face_loads(nodes: np.ndarray, loaded_faces: list[tuple[int, list[int]]], total_load: float) -> tuple[dict[int, float], dict[str, list[float]]]:
    contributions: dict[int, float] = {}
    abscissa = 1.0 / np.sqrt(3.0)
    for _, face in loaded_faces:
        face_coordinates = nodes[face][:, 1:]
        for r in (-abscissa, abscissa):
            for s in (-abscissa, abscissa):
                shape, derivatives = _quad8_shape(r, s)
                jacobian = derivatives.T @ face_coordinates
                determinant = abs(float(np.linalg.det(jacobian)))
                for node, value in zip(face, shape, strict=True):
                    contributions[node] = contributions.get(node, 0.0) + float(value * determinant * total_load)
    resultant = [float(sum(contributions.values())), 0.0, 0.0]
    # r x (Fx, 0, 0) = (0, z*Fx, -y*Fx).
    moment = [
        0.0,
        float(sum(nodes[node, 2] * value for node, value in contributions.items())),
        float(sum(-nodes[node, 1] * value for node, value in contributions.items())),
    ]
    return contributions, {"resultant": resultant, "origin_moment": moment}


def _model(cells: tuple[int, int, int]) -> tuple[FiniteElementModel, dict[str, Any]]:
    nx, ny, nz = cells
    nodes, elements, loaded_faces = _mesh(nx, ny, nz)
    contributions, load_audit = _consistent_face_loads(nodes, loaded_faces, LOAD_SCALE)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loads = [
        {"node": int(node), "dof": "UX", "value": float(value)}
        for node, value in sorted(contributions.items())
        if abs(value) > 1.0e-16
    ]
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": FAMILY, "nodes": item, "material": "j2"} for item in elements],
        materials={"j2": dict(MATERIAL)},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=loads,
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "load_path": list(LOAD_PATH),
            "max_iterations": 40,
            "tolerance": 1.0e-9,
            "parameters": {
                "kinematics": "corotational_j2",
                "corotational_max_local_strain": 0.05,
                "adaptive_load_steps": False,
            },
        },
    )
    expected = LOAD_SCALE
    if not np.isclose(sum(loads_item["value"] for loads_item in loads), expected, rtol=0.0, atol=1.0e-12):
        raise ValueError("Consistent QUAD8 traction did not preserve the total resultant.")
    return model, {"load": load_audit, "loaded_face_count": len(loaded_faces), "load_node_count": len(loads)}


def _run_one(stage: str, cells: tuple[int, int, int], output: Path, label: str) -> dict[str, Any]:
    started = time.perf_counter()
    path = output / f"{label.lower()}_hex20.json"
    try:
        model, load_info = _model(cells)
        quality = MeshValidator().validate(model)
        result = solve_model(model, enforce_policy=True)
        metrics = _metrics(result, time.perf_counter() - started)
        result_dict = result.to_dict()
        raw = {
            "study": "WP09 HEX20 R2 consistent traction",
            "family": FAMILY,
            "stage": stage,
            "cells": list(cells),
            "label": label,
            "contract_path": str(CONTRACT_PATH),
            "contract_sha256": _sha256(CONTRACT_PATH),
            "source_sha": _git("rev-parse", "HEAD"),
            "policy_code_digest": POLICY_DIGEST,
            "load_definition": "consistent QUAD8 2x2 Gauss surface traction",
            "load_info": load_info,
            "mesh_quality": quality.to_dict(),
            "metrics": metrics,
            "observable_source": {
                "displacements": result_dict["displacements"],
                "solver_steps": result.solver.get("steps", []),
                "element_results": result.element_results,
                "material_states": result.material_states,
                "equilibrium": _equilibrium(result),
            },
            "result": result_dict,
        }
        path.write_text(json.dumps(raw, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")
        return {"raw_path": str(path), "stage": stage, "cells": list(cells), **metrics, "load_info": load_info}
    except Exception as exc:  # noqa: BLE001 - preserve fail-closed evidence.
        failure = {
            "study": "WP09 HEX20 R2 consistent traction",
            "family": FAMILY,
            "stage": stage,
            "cells": list(cells),
            "label": label,
            "source_sha": _git("rev-parse", "HEAD"),
            "status": "FAIL_EXCEPTION",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "elapsed_seconds": time.perf_counter() - started,
        }
        path.write_text(json.dumps(failure, indent=2), encoding="utf-8")
        return failure


def _gate(row: dict[str, Any], contract: dict[str, Any]) -> tuple[bool, list[str]]:
    limits = contract["gates"]
    failures: list[str] = []
    if row.get("status") != limits["production_status"]:
        failures.append("production_status")
    for name in ("selected_displacement", "reaction_norm", "energy", "von_mises_max", "min_det_f", "max_local_strain_norm"):
        if not _finite(row.get(name)):
            failures.append(f"nonfinite:{name}")
    equilibrium = row.get("equilibrium", {})
    for name, limit_name in (
        ("free_relative_residual", "free_residual_relative_max"),
        ("force_balance_relative_error", "force_equilibrium_relative_max"),
        ("moment_balance_relative_error", "moment_equilibrium_relative_max"),
    ):
        value = equilibrium.get(name, float("nan"))
        if not _finite(value) or float(value) > limits[limit_name]:
            failures.append(name)
    if float(row.get("min_det_f", -np.inf)) < limits["minimum_det_f"]:
        failures.append("det_f")
    if float(row.get("max_local_strain_norm", np.inf)) > limits["maximum_local_strain_norm"]:
        failures.append("local_strain")
    if int(row.get("accepted_steps", -1)) != limits["accepted_steps"]:
        failures.append("accepted_steps")
    if int(row.get("rejected_increments", -1)) != limits["rejected_increments"]:
        failures.append("rejected_increments")
    if int(row.get("fallback_count", -1)) != limits["fallback_count"]:
        failures.append("fallback_count")
    return not failures, failures


def _replay_gate(primary: dict[str, Any], replay: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    names = ("selected_displacement", "reaction_norm", "energy", "von_mises_max", "equivalent_plastic_strain_max")
    errors = {name: _relative(float(primary[name]), float(replay[name])) for name in names}
    tolerance = contract["gates"]["replay_relative_tolerance"]
    return {"status": "PASS" if all(value <= tolerance for value in errors.values()) else "FAIL_CLOSED", "relative_errors": errors}


def _mesh_gate(coarse: dict[str, Any], fine: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    thresholds = contract["gates"]["mesh_comparison"]
    deltas = {
        "selected_displacement": _relative(coarse["selected_displacement"], fine["selected_displacement"]),
        "reaction": _relative(coarse["reaction_norm"], fine["reaction_norm"]),
        "energy": _relative(coarse["energy"], fine["energy"]),
        "von_mises": _relative(coarse["von_mises_max"], fine["von_mises_max"]),
    }
    failures = [name for name, value in deltas.items() if value > thresholds[f"{name}_relative_max"]]
    return {"status": "PASS" if not failures else "FAIL_CLOSED", "deltas": deltas, "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    campaign: dict[str, Any] = {
        "status": "RUNNING",
        "study": "WP09 HEX20 R2 consistent traction",
        "branch": _git("branch", "--show-current"),
        "source_sha": _git("rev-parse", "HEAD"),
        "contract_sha256": _sha256(CONTRACT_PATH),
        "policy_code_digest": POLICY_DIGEST,
        "working_tree_at_start": _git("status", "--short"),
        "machine": {"platform": platform.platform(), "python": platform.python_version()},
        "load_definition": contract["load_definition"],
        "stages": {},
        "formal_points": "0/pending",
    }
    primaries: dict[str, dict[str, Any]] = {}
    for stage, cells in LEVELS:
        primary = _run_one(stage, cells, output, stage)
        primaries[stage] = primary
        passed, failures = _gate(primary, contract)
        replay = _run_one(stage, cells, output, f"{stage}_replay") if passed else {"status": "SKIPPED_DEPENDENCY"}
        replay_status = _replay_gate(primary, replay, contract) if passed else {"status": "SKIPPED_DEPENDENCY"}
        campaign["stages"][stage] = {
            "status": "PASS" if passed and replay_status["status"] == "PASS" else "FAIL_CLOSED",
            "cells": list(cells),
            "primary": primary,
            "structural_gate": {"status": "PASS" if passed else "FAIL_CLOSED", "failures": failures},
            "replay": replay_status,
        }
        if campaign["stages"][stage]["status"] != "PASS":
            break
    if all(campaign["stages"].get(stage, {}).get("status") == "PASS" for stage, _ in LEVELS):
        campaign["mesh_gate_h2_to_h3"] = _mesh_gate(primaries["H2"], primaries["H3"], contract)
    else:
        campaign["mesh_gate_h2_to_h3"] = {"status": "SKIPPED_DEPENDENCY"}
    reference_dir = output / "independent_reference"
    command = [
        sys.executable,
        str(ROOT / "scripts" / "run_wp09_hex20_extension_reference.py"),
        "--input",
        str(output),
        "--output",
        str(reference_dir),
    ]
    reference_run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    (output / "reference_stdout.log").write_text(reference_run.stdout, encoding="utf-8")
    (output / "reference_stderr.log").write_text(reference_run.stderr, encoding="utf-8")
    reference = json.loads((reference_dir / "summary.json").read_text(encoding="utf-8")) if (reference_dir / "summary.json").exists() else {"status": "FAIL_CLOSED_MISSING_SUMMARY"}
    campaign["independent_reference"] = reference
    campaign["status"] = "PASS_CANDIDATE" if campaign["mesh_gate_h2_to_h3"]["status"] == "PASS" and reference["status"] == "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION" else "FAIL_CLOSED"
    campaign["working_tree_at_end"] = _git("status", "--short")
    (output / "campaign.json").write_text(json.dumps(campaign, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")
    lines = [
        "# WP09 HEX20 R2 — consistent traction and 3-D refinement",
        "",
        f"Status: `{campaign['status']}`",
        f"Source SHA: `{campaign['source_sha']}`",
        f"Contract SHA-256: `{campaign['contract_sha256']}`",
        "",
        "| Stage | Cells | Status |",
        "|---|---|---|",
    ]
    for stage, cells in LEVELS:
        lines.append(f"| {stage} | {cells} | {campaign['stages'].get(stage, {}).get('status', 'NOT_RUN')} |")
    lines.extend([
        "",
        f"Mesh gate H2→H3: `{campaign['mesh_gate_h2_to_h3']['status']}`",
        f"Independent observable recomputation: `{reference.get('status', 'UNKNOWN')}`",
        "",
        "No WP09 points are awarded by this runner. HEX8 official evidence remains unchanged.",
    ])
    (output / "campaign.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": campaign["status"], "stages": campaign["stages"], "mesh_gate": campaign["mesh_gate_h2_to_h3"], "reference": reference.get("status")}, indent=2))
    return 0 if campaign["status"] == "PASS_CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
