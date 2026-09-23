"""Run the WP09 TET10 R2 consistent-traction extension campaign.

This is evidence tooling only.  It does not alter production mechanics,
solver policy, thresholds, fallback behavior, or the official WP09 ledger.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from solveur.api import solve_model  # noqa: E402
from solveur.core.model import FiniteElementModel  # noqa: E402
from solveur.elements.solid.tet4 import Tet4Element  # noqa: E402
from solveur.loads.integration import DistributedLoadIntegrator  # noqa: E402
from solveur.mesh.topology import TET10_FACES  # noqa: E402
from solveur.mesh.validation import MeshValidator  # noqa: E402


CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp09_tet10_r2_consistent_traction_contract.json"
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_9" / "wp09_tet10_r2_consistent_traction"
FAMILY = "TET10"
LOAD_SCALE = 0.25
LOAD_PATH = (0.25, 0.5, 0.75, 1.0)
MATERIAL = {"type": "von_mises_elastoplastic_3d", "E": 1000.0, "nu": 0.3, "yield_stress": 0.02, "hardening_modulus": 10.0}
POLICY_DIGEST = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
LEVELS = (("H1", (1, 1, 1)), ("H2", (2, 2, 2)), ("H3", (3, 3, 3)))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def _finite(value: Any) -> bool:
    try:
        return bool(np.isfinite(np.asarray(value, dtype=float)).all())
    except (TypeError, ValueError):
        return False


def _relative(left: float, right: float) -> float:
    return abs(left - right) / max(abs(left), abs(right), 1.0e-14)


def _mesh(nx: int, ny: int, nz: int) -> tuple[np.ndarray, list[list[int]]]:
    node_ids: dict[tuple[float, float, float], int] = {}
    coordinates: list[tuple[float, float, float]] = []

    def node_id(point: np.ndarray | tuple[float, float, float]) -> int:
        key = (round(float(point[0]), 14), round(float(point[1]), 14), round(float(point[2]), 14))
        if key not in node_ids:
            node_ids[key] = len(coordinates)
            coordinates.append(key)
        return node_ids[key]

    edge_order = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
    tet_templates = ((0, 1, 3, 4), (1, 2, 3, 6), (1, 3, 4, 6), (1, 4, 5, 6), (3, 4, 6, 7))
    elements: list[list[int]] = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                x0, x1 = i / nx, (i + 1) / nx
                y0, y1 = j / ny, (j + 1) / ny
                z0, z1 = k / nz, (k + 1) / nz
                corners = np.asarray(
                    [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                     [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]],
                    dtype=float,
                )
                corner_ids = [node_id(point) for point in corners]
                for template in tet_templates:
                    tet = [corner_ids[index] for index in template]
                    tet_points = np.asarray([coordinates[index] for index in tet], dtype=float)
                    if Tet4Element.signed_volume(tet_points) < 0.0:
                        tet[2], tet[3] = tet[3], tet[2]
                    midpoint_ids = [
                        node_id(0.5 * (np.asarray(coordinates[tet[first]]) + np.asarray(coordinates[tet[second]])))
                        for first, second in edge_order
                    ]
                    elements.append(tet + midpoint_ids)
    return np.asarray(coordinates, dtype=float), elements


def _boundary_surface_loads(nodes: np.ndarray, elements: list[list[int]]) -> tuple[list[dict[str, object]], dict[str, object]]:
    candidates: list[tuple[int, int, tuple[int, ...], float]] = []
    seen: set[frozenset[int]] = set()
    for element_index, element in enumerate(elements):
        for face_index, local_face in enumerate(TET10_FACES):
            global_face = tuple(int(element[position]) for position in local_face)
            key = frozenset(global_face)
            face_coords = nodes[list(global_face)]
            if key in seen or not np.allclose(face_coords[:, 0], 1.0):
                continue
            corners = face_coords[:3]
            area = 0.5 * float(np.linalg.norm(np.cross(corners[1] - corners[0], corners[2] - corners[0])))
            if area <= 0.0:
                raise ValueError(f"Degenerate x=1 TET10 face on element {element_index}.")
            seen.add(key)
            candidates.append((element_index, face_index, global_face, area))
    if not candidates:
        raise ValueError("No TET10 x=1 boundary faces were found.")
    total_area = sum(item[3] for item in candidates)
    traction = LOAD_SCALE / total_area
    loads = [
        {
            "type": "surface_traction",
            "element": element_index,
            "face": face_index,
            "value": [traction, 0.0, 0.0],
            "coordinate_system": "global",
            "follower": False,
        }
        for element_index, face_index, _, _ in candidates
    ]
    return loads, {
        "face_count": len(candidates),
        "face_area": [float(item[3]) for item in candidates],
        "total_area": float(total_area),
        "traction_magnitude": float(traction),
        "traction_direction": [1.0, 0.0, 0.0],
        "reference_resultant": [LOAD_SCALE, 0.0, 0.0],
        "face_ids": [[int(item[0]), int(item[1])] for item in candidates],
    }


def _model(cells: tuple[int, int, int]) -> tuple[FiniteElementModel, dict[str, Any]]:
    nodes, elements = _mesh(*cells)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    distributed_loads, surface_metadata = _boundary_surface_loads(nodes, elements)
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": FAMILY, "nodes": item, "material": "j2"} for item in elements],
        materials={"j2": dict(MATERIAL)},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        distributed_loads=distributed_loads,
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "load_path": list(LOAD_PATH),
            "max_iterations": 40,
            "tolerance": 1.0e-9,
            "kinematics": "corotational_j2",
            "corotational_max_local_strain": 0.05,
            "contact_mode": "none",
            "contact_finite_sliding": False,
            "contact_max_penetration": 0.05,
        },
    )
    return model, surface_metadata


def _load_metadata(model: FiniteElementModel) -> dict[str, Any]:
    dofs = model.dof_manager()
    integrator = DistributedLoadIntegrator()
    resultant: np.ndarray = np.zeros(3, dtype=float)
    moment: np.ndarray = np.zeros(3, dtype=float)
    contributions: list[dict[str, Any]] = []
    for index, load in enumerate(model.distributed_loads):
        integrated = integrator.integrate_sparse(model, dofs, load, index)
        details = dict(integrated.details)
        resultant += np.asarray(details["resultant"], dtype=float)
        moment += np.asarray(details["moment_about_origin"], dtype=float)
        contributions.append(details)
    expected = np.asarray((LOAD_SCALE, 0.0, 0.0), dtype=float)
    return {
        "resultant": resultant.tolist(),
        "moment_about_origin": moment.tolist(),
        "expected_resultant": expected.tolist(),
        "resultant_error_norm": float(np.linalg.norm(resultant - expected)),
        "contributions": contributions,
    }


def _equilibrium(result: Any) -> dict[str, Any]:
    audit = result.audit.equilibrium if result.audit is not None else {}
    return {
        "free_relative_residual": float(audit.get("free_relative_residual", float("nan"))),
        "force_balance_relative_error": float(audit.get("force_balance_relative_error", float("nan"))),
        "moment_balance_relative_error": float(audit.get("moment_balance_relative_error", float("nan"))),
        "reaction_resultant": [float(value) for value in audit.get("reaction_resultant", ())],
        "reaction_moment": [float(value) for value in audit.get("reaction_moment", ())],
    }


def _metrics(result: Any, elapsed_seconds: float) -> dict[str, object]:
    steps = list(result.solver.get("steps", []))
    point_rows = [point for element in result.element_results for point in element.get("integration_points", [])]
    det_values = [float(point["det_f"]) for point in point_rows if "det_f" in point]
    local_strain_values = [float(point["corotational_strain_norm"]) for point in point_rows if "corotational_strain_norm" in point]
    stress_values = [float(element.get("von_mises", 0.0)) for element in result.element_results if "von_mises" in element]
    plastic_values = [float(state.get("equivalent_plastic_strain", 0.0)) for states in result.material_states.values() for state in states]
    dissipation_values = [float(state.get("plastic_dissipation", 0.0)) for states in result.material_states.values() for state in states]
    energy = sum(float(step.get("incremental_internal_work", 0.0)) for step in steps)
    if not energy:
        energy = sum(float(element.get("strain_energy", 0.0)) for element in result.element_results)
    equilibrium = _equilibrium(result)
    return {
        "status": str(result.status),
        "run_verdict": getattr(getattr(result, "run_verdict", None), "value", "UNAVAILABLE"),
        "node_count": int(result.node_count),
        "element_count": int(result.element_count),
        "dof_count": int(result.displacements.size),
        "selected_displacement": float(np.max(np.abs(result.displacements))),
        "displacement_norm": float(np.linalg.norm(result.displacements)),
        "reaction_norm": float(np.linalg.norm(equilibrium["reaction_resultant"])),
        "energy": float(energy),
        "von_mises_max": max(stress_values, default=0.0),
        "equivalent_plastic_strain_max": max(plastic_values, default=0.0),
        "plastic_dissipation_max": max(dissipation_values, default=0.0),
        "min_det_f": min(det_values, default=float("nan")),
        "max_local_strain_norm": max(local_strain_values, default=float("nan")),
        "accepted_steps": len(steps) if str(result.status) == "PASS" else 0,
        "step_count": len(steps),
        "newton_iterations": sum(int(step.get("iterations", 0)) for step in steps),
        "rejected_increments": int(result.solver.get("rejected_increments", 0)),
        "fallback_count": int(result.solver.get("fallback_count", 0)),
        "elapsed_seconds": elapsed_seconds,
        "equilibrium": equilibrium,
    }


def _run_one(stage: str, cells: tuple[int, int, int], output: Path, label: str) -> dict[str, Any]:
    started = time.perf_counter()
    path = output / f"{label.lower()}_tet10.json"
    try:
        model, surface_metadata = _model(cells)
        quality = MeshValidator().validate(model)
        load_metadata = _load_metadata(model)
        result = solve_model(model, enforce_policy=True)
        metrics = _metrics(result, time.perf_counter() - started)
        result_dict = result.to_dict()
        raw = {
            "study": "WP09 TET10 R2 consistent traction",
            "family": FAMILY,
            "stage": stage,
            "cells": list(cells),
            "contract_path": str(CONTRACT_PATH),
            "contract_sha256": _sha256(CONTRACT_PATH),
            "source_sha": _git("rev-parse", "HEAD"),
            "policy_code_digest": POLICY_DIGEST,
            "load_definition": "consistent TET10 quadratic triangular surface traction",
            "surface_load": surface_metadata,
            "load_balance": load_metadata,
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
        return {"raw_path": str(path), "stage": stage, "cells": list(cells), **metrics}
    except Exception as exc:  # noqa: BLE001 - preserve fail-closed evidence.
        failure = {
            "study": "WP09 TET10 R2 consistent traction",
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
    if not isinstance(equilibrium, dict):
        failures.append("equilibrium_missing")
        equilibrium = {}
    for name, limit_name in (("free_relative_residual", "free_residual_relative_max"), ("force_balance_relative_error", "force_equilibrium_relative_max"), ("moment_balance_relative_error", "moment_equilibrium_relative_max")):
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
        "selected_displacement": _relative(float(coarse["selected_displacement"]), float(fine["selected_displacement"])),
        "reaction": _relative(float(coarse["reaction_norm"]), float(fine["reaction_norm"])),
        "energy": _relative(float(coarse["energy"]), float(fine["energy"])),
        "von_mises": _relative(float(coarse["von_mises_max"]), float(fine["von_mises_max"])),
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
        "study": "WP09 TET10 R2 consistent traction",
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
    reference_run = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_wp09_tet10_extension_reference.py"), "--input", str(output), "--output", str(reference_dir)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    (output / "reference_stdout.log").write_text(reference_run.stdout, encoding="utf-8")
    (output / "reference_stderr.log").write_text(reference_run.stderr, encoding="utf-8")
    reference = json.loads((reference_dir / "summary.json").read_text(encoding="utf-8")) if (reference_dir / "summary.json").exists() else {"status": "FAIL_CLOSED_MISSING_SUMMARY"}
    campaign["independent_reference"] = reference
    campaign["status"] = "PASS_CANDIDATE" if campaign["mesh_gate_h2_to_h3"]["status"] == "PASS" and reference["status"] == "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION" else "FAIL_CLOSED"
    campaign["working_tree_at_end"] = _git("status", "--short")
    (output / "campaign.json").write_text(json.dumps(campaign, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")
    lines = [
        "# WP09 TET10 R2 — consistent traction and 3-D refinement",
        "",
        f"Status: `{campaign['status']}`",
        f"Source SHA: `{campaign['source_sha']}`",
        f"Contract SHA-256: `{campaign['contract_sha256']}`",
        "",
        "| Stage | Cells | Status |",
        "|---|---|---|",
    ]
    for stage, cells in LEVELS:
        row = campaign["stages"].get(stage, {"status": "NOT_RUN"})
        lines.append(f"| {stage} | `{cells[0]}×{cells[1]}×{cells[2]}` | `{row['status']}` |")
    lines.extend(["", f"Mesh gate H2→H3: `{campaign['mesh_gate_h2_to_h3']['status']}`", f"Reference: `{reference['status']}`", ""])
    (output / "campaign.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": campaign["status"], "stages": campaign["stages"], "mesh_gate": campaign["mesh_gate_h2_to_h3"], "reference": reference.get("status")}, indent=2))
    return 0 if campaign["status"] == "PASS_CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
