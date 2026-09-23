"""Prospective, diagnostic-only WP09 TET4 bounded corotational study.

The campaign runner is evidence tooling.  It does not change solver mechanics,
thresholds, material data, or the WP09 score.  Each primary and replay solve
runs in its own Python process from the frozen contract commit.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
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
from solveur.mesh.topology import TET4_FACES  # noqa: E402
from solveur.mesh.validation import MeshValidator  # noqa: E402

CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp09_tet4_consistent_traction_study_contract.json"
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_9" / "wp09_tet4_consistent_traction_study_r1"
POLICY_CODE_DIGEST = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
RUNTIME_POLICY_DIGEST = "895d3c932278c0207b207318216c263a427636d57738bef730917fdc7d9b0ef5"
LOAD_SCALE = 0.25
LOAD_PATH = (0.25, 0.5, 0.75, 1.0)
MATERIAL = {
    "type": "von_mises_elastoplastic_3d",
    "E": 1000.0,
    "nu": 0.3,
    "yield_stress": 0.02,
    "hardening_modulus": 10.0,
}
LEVELS = (("H1", (1, 1, 1)), ("H2", (2, 2, 2)), ("H3", (3, 3, 3)))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, default=_json_default, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


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
        key = tuple(round(float(point[axis]), 14) for axis in range(3))
        if key not in node_ids:
            node_ids[key] = len(coordinates)
            coordinates.append(key)
        return node_ids[key]

    templates = ((0, 1, 3, 4), (1, 2, 3, 6), (1, 3, 4, 6), (1, 4, 5, 6), (3, 4, 6, 7))
    elements: list[list[int]] = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                x0, x1 = i / nx, (i + 1) / nx
                y0, y1 = j / ny, (j + 1) / ny
                z0, z1 = k / nz, (k + 1) / nz
                corners = np.asarray(
                    ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                     (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)),
                    dtype=float,
                )
                corner_ids = [node_id(point) for point in corners]
                for template in templates:
                    tet = [corner_ids[index] for index in template]
                    points = np.asarray([coordinates[index] for index in tet], dtype=float)
                    if Tet4Element.signed_volume(points) < 0.0:
                        tet[2], tet[3] = tet[3], tet[2]
                    elements.append(tet)
    return np.asarray(coordinates, dtype=float), elements


def _boundary_surface_loads(
    nodes: np.ndarray, elements: list[list[int]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    faces: list[tuple[int, int, tuple[int, int, int], float]] = []
    seen: set[frozenset[int]] = set()
    for element_index, element in enumerate(elements):
        for face_index, local_face in enumerate(TET4_FACES):
            global_face = tuple(int(element[position]) for position in local_face)
            key = frozenset(global_face)
            if key in seen:
                continue
            face_coords = nodes[list(global_face)]
            if not np.allclose(face_coords[:, 0], 1.0, atol=1.0e-13, rtol=0.0):
                continue
            area = 0.5 * float(np.linalg.norm(np.cross(face_coords[1] - face_coords[0], face_coords[2] - face_coords[0])))
            if area <= 0.0:
                raise ValueError(f"Degenerate x=1 TET4 face on element {element_index}.")
            seen.add(key)
            faces.append((element_index, face_index, global_face, area))
    if not faces:
        raise ValueError("No TET4 x=1 boundary faces were found.")

    total_area = sum(face[3] for face in faces)
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
        for element_index, face_index, _, _ in faces
    ]
    analytic_resultant = np.zeros(3)
    analytic_moment = np.zeros(3)
    for _, _, global_face, area in faces:
        face_force = np.asarray((traction * area, 0.0, 0.0))
        analytic_resultant += face_force
        analytic_moment += np.cross(np.mean(nodes[list(global_face)], axis=0), face_force)
    metadata = {
        "face_count": len(faces),
        "face_areas": [float(face[3]) for face in faces],
        "total_area": float(total_area),
        "traction_magnitude": float(traction),
        "traction_direction": [1.0, 0.0, 0.0],
        "reference_resultant": [LOAD_SCALE, 0.0, 0.0],
        "analytic_resultant": analytic_resultant.tolist(),
        "analytic_moment_about_origin": analytic_moment.tolist(),
        "face_ids": [[int(face[0]), int(face[1])] for face in faces],
    }
    return loads, metadata


def _model(cells: tuple[int, int, int]) -> tuple[FiniteElementModel, dict[str, Any]]:
    nodes, elements = _mesh(*cells)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0, atol=1.0e-13, rtol=0.0))
    loads, surface_metadata = _boundary_surface_loads(nodes, elements)
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "TET4", "nodes": item, "material": "j2"} for item in elements],
        materials={"j2": dict(MATERIAL)},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        distributed_loads=loads,
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


def _load_balance(model: FiniteElementModel, surface_metadata: dict[str, Any]) -> dict[str, Any]:
    dofs = model.dof_manager()
    integrator = DistributedLoadIntegrator()
    resultant = np.zeros(3)
    moment = np.zeros(3)
    for index, load in enumerate(model.distributed_loads):
        details = dict(integrator.integrate_sparse(model, dofs, load, index).details)
        resultant += np.asarray(details["resultant"], dtype=float)
        moment += np.asarray(details["moment_about_origin"], dtype=float)
    expected_force = np.asarray((LOAD_SCALE, 0.0, 0.0))
    expected_moment = np.asarray((0.0, LOAD_SCALE / 2.0, -LOAD_SCALE / 2.0))
    return {
        "integrated_resultant": resultant.tolist(),
        "integrated_moment_about_origin": moment.tolist(),
        "analytic_resultant": surface_metadata["analytic_resultant"],
        "analytic_moment_about_origin": surface_metadata["analytic_moment_about_origin"],
        "expected_resultant": expected_force.tolist(),
        "expected_moment_about_origin": expected_moment.tolist(),
        "resultant_error_norm": float(np.linalg.norm(resultant - expected_force)),
        "moment_error_norm": float(np.linalg.norm(moment - expected_moment)),
        "production_vs_analytic_resultant_error_norm": float(
            np.linalg.norm(resultant - np.asarray(surface_metadata["analytic_resultant"], dtype=float))
        ),
        "production_vs_analytic_moment_error_norm": float(
            np.linalg.norm(moment - np.asarray(surface_metadata["analytic_moment_about_origin"], dtype=float))
        ),
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


def _metrics(result: Any, elapsed: float) -> dict[str, Any]:
    steps = list(result.solver.get("steps", []))
    points = [point for element in result.element_results for point in element.get("integration_points", [])]
    det = [float(point["det_f"]) for point in points if "det_f" in point]
    strain = [float(point["corotational_strain_norm"]) for point in points if "corotational_strain_norm" in point]
    stress = [float(element["von_mises"]) for element in result.element_results if "von_mises" in element]
    states = [state for rows in result.material_states.values() for state in rows]
    equilibrium = _equilibrium(result)
    energy = sum(float(step.get("incremental_internal_work", 0.0)) for step in steps)
    if not energy:
        energy = sum(float(element.get("strain_energy", 0.0)) for element in result.element_results)
    return {
        "status": str(result.status),
        "node_count": int(result.node_count),
        "element_count": int(result.element_count),
        "dof_count": int(result.displacements.size),
        "selected_displacement": float(np.max(np.abs(result.displacements))),
        "displacement_norm": float(np.linalg.norm(result.displacements)),
        "reaction_norm": float(np.linalg.norm(equilibrium["reaction_resultant"])),
        "energy": float(energy),
        "von_mises_max": max(stress, default=float("nan")),
        "equivalent_plastic_strain_max": max(
            (float(state.get("equivalent_plastic_strain", 0.0)) for state in states), default=0.0
        ),
        "plastic_dissipation_max": max((float(state.get("plastic_dissipation", 0.0)) for state in states), default=0.0),
        "min_det_f": min(det, default=float("nan")),
        "max_local_strain_norm": max(strain, default=float("nan")),
        "accepted_steps": len(steps) if str(result.status) == "PASS" else 0,
        "step_count": len(steps),
        "newton_iterations": sum(int(step.get("iterations", 0)) for step in steps),
        "rejected_increments": int(result.solver.get("rejected_increments", 0)),
        "fallback_count": int(result.solver.get("fallback_count", 0)),
        "elapsed_seconds_observational_only": elapsed,
        "equilibrium": equilibrium,
    }


def _gate(row: dict[str, Any], contract: dict[str, Any]) -> tuple[bool, list[str]]:
    gates = contract["gates"]
    failures: list[str] = []
    if row.get("status") != gates["production_status"]:
        failures.append("production_status")
    for field in ("selected_displacement", "reaction_norm", "energy", "von_mises_max", "min_det_f", "max_local_strain_norm"):
        if not _finite(row.get(field)):
            failures.append(f"nonfinite:{field}")
    equilibrium = row.get("equilibrium", {})
    for field, gate in (
        ("free_relative_residual", "free_residual_relative_max"),
        ("force_balance_relative_error", "force_equilibrium_relative_max"),
        ("moment_balance_relative_error", "moment_equilibrium_relative_max"),
    ):
        value = equilibrium.get(field, float("nan"))
        if not _finite(value) or float(value) > gates[gate]:
            failures.append(field)
    if _finite(row.get("min_det_f")) and float(row["min_det_f"]) < gates["minimum_det_f"]:
        failures.append("det_f")
    if _finite(row.get("max_local_strain_norm")) and float(row["max_local_strain_norm"]) > gates["maximum_local_strain_norm"]:
        failures.append("local_strain")
    for field, expected in (("accepted_steps", gates["accepted_steps"]), ("rejected_increments", gates["rejected_increments"]), ("fallback_count", gates["fallback_count"])):
        if row.get(field) != expected:
            failures.append(field)
    return not failures, failures


def _replay_gate(primary: dict[str, Any], replay: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    fields = ("selected_displacement", "reaction_norm", "energy", "von_mises_max", "equivalent_plastic_strain_max", "plastic_dissipation_max")
    errors = {field: _relative(float(primary[field]), float(replay[field])) for field in fields}
    passed = all(value <= contract["gates"]["replay_relative_tolerance"] for value in errors.values())
    return {"status": "PASS" if passed else "FAIL_CLOSED", "relative_errors": errors}


def _mesh_gate(coarse: dict[str, Any], fine: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    limits = contract["gates"]["mesh_comparison"]
    deltas = {
        "selected_displacement": _relative(coarse["selected_displacement"], fine["selected_displacement"]),
        "reaction": _relative(coarse["reaction_norm"], fine["reaction_norm"]),
        "energy": _relative(coarse["energy"], fine["energy"]),
        "von_mises": _relative(coarse["von_mises_max"], fine["von_mises_max"]),
    }
    failures = [name for name, value in deltas.items() if value > limits[f"{name}_relative_max"]]
    return {"status": "PASS" if not failures else "FAIL_CLOSED", "relative_deltas": deltas, "failures": failures}


def _verify_frozen_contract(contract: dict[str, Any]) -> dict[str, Any]:
    if _git("branch", "--show-current") != contract["study_branch"]:
        raise RuntimeError("Unexpected branch; refusing structural study.")
    dirty = _git("status", "--porcelain")
    if dirty:
        raise RuntimeError(f"Working tree is not clean; refusing structural study: {dirty}")
    head = _git("rev-parse", "HEAD")
    runner_commit = contract["frozen_runner_commit"]
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", runner_commit, "HEAD"], cwd=ROOT, check=False)
    if ancestor.returncode != 0:
        raise RuntimeError("Frozen runner commit is not an ancestor of execution HEAD.")
    runner_path = ROOT / contract["runner_path"]
    if _sha256(runner_path) != contract["runner_sha256"]:
        raise RuntimeError("Runner SHA-256 differs from the frozen contract.")
    reference_path = ROOT / contract["reference"]["script"]
    if _sha256(reference_path) != contract["reference"]["reference_sha256"]:
        raise RuntimeError("Independent observable checker SHA-256 differs from the frozen contract.")
    base = contract["governing_base_sha"]
    src_check = subprocess.run(["git", "diff", "--quiet", base, "HEAD", "--", "src"], cwd=ROOT, check=False)
    if src_check.returncode != 0:
        raise RuntimeError("Production source differs from governing base; diagnostic runner must not execute.")
    return {"branch": contract["study_branch"], "execution_sha": head, "working_tree_clean": True}


def _single_stage(stage: str, label: str, output: Path, contract: dict[str, Any]) -> int:
    started = time.perf_counter()
    cells = dict((name, cell) for name, cell in LEVELS)[stage]
    path = output / f"{stage.lower()}_tet4_{label}.json"
    metadata = {
        "study": "WP09 TET4 consistent-traction diagnostic R1",
        "family": "TET4",
        "stage": stage,
        "cells": list(cells),
        "contract_sha256": _sha256(CONTRACT_PATH),
        "execution_sha": _git("rev-parse", "HEAD"),
        "policy_code_digest": POLICY_CODE_DIGEST,
        "runtime_policy_digest": RUNTIME_POLICY_DIGEST,
        "python_pid": os.getpid(),
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "load_definition": "global +UX consistent linear triangular-face surface traction; not equal-share nodal forces",
    }
    try:
        model, surface = _model(cells)
        quality = MeshValidator().validate(model)
        load_balance = _load_balance(model, surface)
        if quality.to_dict().get("status") != "PASS":
            raise RuntimeError("mesh-quality precheck did not PASS")
        if load_balance["resultant_error_norm"] > 1.0e-12 or load_balance["moment_error_norm"] > 1.0e-12:
            raise RuntimeError("integrated load resultant/moment precheck did not PASS")
        result = solve_model(model, enforce_policy=True)
        metrics = _metrics(result, time.perf_counter() - started)
        data = {
            **metadata,
            "status": metrics["status"],
            "surface_load": surface,
            "load_balance": load_balance,
            "mesh_quality": quality.to_dict(),
            "metrics": metrics,
            "observable_source": {
                "displacements": result.to_dict()["displacements"],
                "solver_steps": result.solver.get("steps", []),
                "element_results": result.element_results,
                "material_states": result.material_states,
                "equilibrium": metrics["equilibrium"],
            },
            "result": result.to_dict(),
        }
        _write_json(path, data)
        print(json.dumps({"raw_path": str(path), "status": metrics["status"], "metrics": metrics}, default=_json_default))
        return 0 if metrics["status"] == "PASS" else 2
    except Exception as exc:  # noqa: BLE001 - preserve fail-closed evidence.
        _write_json(path, {
            **metadata,
            "status": "FAIL_CLOSED",
            "failure_kind": type(exc).__name__,
            "failure": str(exc),
            "elapsed_seconds_observational_only": time.perf_counter() - started,
        })
        print(json.dumps({"raw_path": str(path), "status": "FAIL_CLOSED", "failure": str(exc)}))
        return 2


def _run_child(stage: str, label: str, output: Path) -> dict[str, Any]:
    command = [sys.executable, str(Path(__file__).resolve()), "--single-stage", stage, "--label", label, "--output", str(output)]
    started = time.perf_counter()
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    elapsed = time.perf_counter() - started
    stdout_path = output / f"{stage.lower()}_tet4_{label}.stdout.log"
    stderr_path = output / f"{stage.lower()}_tet4_{label}.stderr.log"
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    raw_path = output / f"{stage.lower()}_tet4_{label}.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8")) if raw_path.exists() else {"status": "FAIL_CLOSED_MISSING_RAW"}
    return {
        "process_id": process.pid,
        "exit_code": process.returncode,
        "elapsed_seconds_observational_only": elapsed,
        "raw_path": str(raw_path.relative_to(ROOT)),
        "raw_sha256": _sha256(raw_path) if raw_path.exists() else None,
        "stdout_path": str(stdout_path.relative_to(ROOT)),
        "stderr_path": str(stderr_path.relative_to(ROOT)),
        "status": raw.get("status", "FAIL_CLOSED"),
        "metrics": raw.get("metrics"),
        "failure": raw.get("failure"),
    }


def _run_reference(output: Path) -> dict[str, Any]:
    reference_path = ROOT / "scripts" / "run_wp09_tet4_consistent_traction_reference.py"
    reference_dir = output / "independent_observable_recomputation"
    process = subprocess.run(
        [sys.executable, str(reference_path), "--input", str(output), "--output", str(reference_dir)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    (output / "reference.stdout.log").write_text(process.stdout, encoding="utf-8")
    (output / "reference.stderr.log").write_text(process.stderr, encoding="utf-8")
    summary = reference_dir / "summary.json"
    return json.loads(summary.read_text(encoding="utf-8")) if summary.exists() else {"status": "FAIL_CLOSED_MISSING_SUMMARY", "exit_code": process.returncode}


def _campaign(output: Path, contract: dict[str, Any]) -> int:
    frozen = _verify_frozen_contract(contract)
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty evidence directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    campaign: dict[str, Any] = {
        "status": "RUNNING",
        "study": "WP09 TET4 consistent-traction diagnostic R1",
        "scope": "diagnostic-only; no official score or WP09 HEX8/HEX20/TET10 status change",
        **frozen,
        "contract_path": str(CONTRACT_PATH.relative_to(ROOT)),
        "contract_sha256": _sha256(CONTRACT_PATH),
        "runner_sha256": _sha256(Path(__file__).resolve()),
        "policy_code_digest": POLICY_CODE_DIGEST,
        "runtime_policy_digest": RUNTIME_POLICY_DIGEST,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "machine": {"platform": platform.platform(), "python": platform.python_version(), "processor": platform.processor(), "logical_cpu_count": os.cpu_count()},
        "stages": {},
        "official_points_awarded": False,
        "production_source_changed": False,
    }
    _write_json(output / "campaign.json", campaign)
    primaries: dict[str, dict[str, Any]] = {}
    for stage, cells in LEVELS:
        primary = _run_child(stage, "primary", output)
        passed, failures = _gate(primary.get("metrics") or {}, contract)
        replay = _run_child(stage, "replay", output) if passed else {"status": "SKIPPED_PRIMARY_GATE_FAILURE"}
        replay_gate = _replay_gate(primary["metrics"], replay["metrics"], contract) if passed and replay.get("status") == "PASS" else {"status": "SKIPPED_DEPENDENCY" if not passed else "FAIL_CLOSED"}
        stage_status = "PASS" if passed and replay_gate["status"] == "PASS" else "FAIL_CLOSED"
        campaign["stages"][stage] = {
            "cells": list(cells),
            "node_count_expected": (cells[0] + 1) * (cells[1] + 1) * (cells[2] + 1),
            "element_count_expected": 5 * cells[0] * cells[1] * cells[2],
            "dof_count_expected": 3 * (cells[0] + 1) * (cells[1] + 1) * (cells[2] + 1),
            "status": stage_status,
            "primary": primary,
            "structural_gate": {"status": "PASS" if passed else "FAIL_CLOSED", "failures": failures},
            "replay": replay,
            "replay_gate": replay_gate,
        }
        if stage_status == "PASS":
            primaries[stage] = primary["metrics"]
        _write_json(output / "campaign.json", campaign)

    if all(stage in primaries for stage in ("H2", "H3")):
        campaign["mesh_gate_h2_to_h3"] = _mesh_gate(primaries["H2"], primaries["H3"], contract)
    else:
        campaign["mesh_gate_h2_to_h3"] = {"status": "SKIPPED_DEPENDENCY"}
    campaign["independent_observable_recomputation"] = _run_reference(output)
    reference_pass = campaign["independent_observable_recomputation"].get("status") == "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION"
    all_stage_pass = all(campaign["stages"].get(stage, {}).get("status") == "PASS" for stage, _ in LEVELS)
    campaign["status"] = (
        "PASS_CANDIDATE_DIAGNOSTIC_ONLY"
        if all_stage_pass and campaign["mesh_gate_h2_to_h3"]["status"] == "PASS" and reference_pass
        else "FAIL_CLOSED_DIAGNOSTIC"
    )
    campaign["completed_utc"] = datetime.now(timezone.utc).isoformat()
    _write_json(output / "campaign.json", campaign)
    return 0 if campaign["status"] == "PASS_CANDIDATE_DIAGNOSTIC_ONLY" else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--single-stage", choices=[name for name, _ in LEVELS])
    parser.add_argument("--label", choices=("primary", "replay"), default="primary")
    args = parser.parse_args()
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    output = args.output.resolve()
    if args.single_stage:
        return _single_stage(args.single_stage, args.label, output, contract)
    return _campaign(output, contract)


if __name__ == "__main__":
    raise SystemExit(main())
