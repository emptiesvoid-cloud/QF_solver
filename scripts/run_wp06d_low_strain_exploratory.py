"""Owner-authorized exploratory low-strain WP06-D solid-arch calculations.

This runner is intentionally separate from the frozen R1/R2 qualification
entrypoints. It never updates formal ledgers and never overwrites prior raw
evidence. Its independent post-processing recomputes observables from accepted
production displacements; it is not an independent equilibrium path solver.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCAL_SOURCE = ROOT / "src"
sys.path.insert(0, str(LOCAL_SOURCE))

import numpy as np
from threadpoolctl import threadpool_info, threadpool_limits

import solveur.api.public as public_api
import solveur.io.nonlinear_checkpoint as checkpoint_module
from solveur.api.public import check_mesh, solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore


MESH_ROOT = ROOT / "qualification" / "0_2_9" / "wp06d_candidate_mesh_audit_20260918"
OUT = ROOT / "qualification" / "0_2_9" / "wp06d_low_strain_exploratory_20260918_normalized_dof_r1"
GEOMETRIES = (("rise_span_0_05", 0.05), ("rise_span_0_025", 0.025))
LEVELS = ("M1", "M2", "M3")
CASE_ORDER = tuple((geometry, ratio, level) for geometry, ratio in GEOMETRIES for level in LEVELS)
YOUNG_MODULUS = 100.0
POISSON_RATIO = 0.30
MAX_ACCEPTED_STEPS = 80
MAX_NEWTON_ITERATIONS = 80
NEWTON_TOLERANCE = 1.0e-8
ARC_RADIUS = 0.005
ARC_LOAD_SCALE = 1.0
MIN_ARC_RADIUS = 2.0e-6
LOAD_FACTOR_LIMIT = 5.0
DOF_NAMES = ("UX", "UY", "UZ")
ENVELOPE = {"det_f_min": 0.20, "principal_stretch_min": 0.75, "principal_stretch_max": 1.30, "green_strain_frobenius_max": 0.30}
REFERENCE_FREE_DOFS: dict[str, int] = {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def _write_json(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
    temporary.replace(path)


def _append_jsonl(path: Path, value: Any) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
        stream.flush()


def _plain(value: Any) -> Any:
    if isinstance(value, np.generic):
        return _plain(value.item())
    if isinstance(value, np.ndarray):
        return [_plain(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _load_mesh(geometry: str, level: str) -> dict[str, np.ndarray]:
    path = MESH_ROOT / f"{geometry}_{level}.npz"
    if not path.is_file():
        raise FileNotFoundError(path)
    with np.load(path, allow_pickle=False) as archive:
        mesh = {key: np.asarray(archive[key]).copy() for key in archive.files}
    required = {
        "nodes", "elements", "grid_ijk", "left_support_nodes", "right_support_nodes",
        "nodal_reference_loads", "target_resultant",
    }
    if not required.issubset(mesh):
        raise ValueError(f"Mesh archive is missing fields: {sorted(required - set(mesh))}")
    if mesh["nodes"].ndim != 2 or mesh["nodes"].shape[1] != 3:
        raise ValueError("Mesh nodes must be N×3.")
    if mesh["elements"].ndim != 2 or mesh["elements"].shape[1] != 4:
        raise ValueError("Mesh connectivity must be TET4.")
    if mesh["nodal_reference_loads"].shape != mesh["nodes"].shape:
        raise ValueError("Nodal load field must match the node-coordinate shape.")
    if not all(np.all(np.isfinite(mesh[key])) for key in ("nodes", "nodal_reference_loads", "target_resultant")):
        raise ValueError("Mesh or load archive contains non-finite values.")
    actual_resultant = np.sum(mesh["nodal_reference_loads"], axis=0)
    if not np.allclose(actual_resultant, mesh["target_resultant"], rtol=0.0, atol=1.0e-12):
        raise ValueError("Meshwise nodal loads do not reproduce the archived resultant.")
    if not np.allclose(mesh["target_resultant"], [0.0, 0.0, -1.0], rtol=0.0, atol=1.0e-12):
        raise ValueError("Unexpected diagnostic target resultant.")
    return mesh


def _free_dof_count(mesh: dict[str, np.ndarray]) -> int:
    support_nodes = np.unique(np.concatenate((mesh["left_support_nodes"], mesh["right_support_nodes"])))
    return 3 * (len(mesh["nodes"]) - len(support_nodes))


def _build_model(
    mesh: dict[str, np.ndarray], checkpoint_path: Path, geometry: str
) -> tuple[FiniteElementModel, np.ndarray, np.ndarray, int]:
    nodes = mesh["nodes"]
    elements = mesh["elements"].astype(np.int64, copy=False)
    support_nodes = np.unique(np.concatenate((mesh["left_support_nodes"], mesh["right_support_nodes"]))).astype(int)
    fixed_dofs = [{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in support_nodes]
    loads = [
        {"node": int(node), "dof": DOF_NAMES[component], "value": float(value)}
        for node, vector in enumerate(mesh["nodal_reference_loads"])
        for component, value in enumerate(vector)
        if float(value) != 0.0
    ]
    center_indices = np.flatnonzero(
        (mesh["grid_ijk"][:, 0] == int(np.max(mesh["grid_ijk"][:, 0]) // 2))
        & (mesh["grid_ijk"][:, 1] == int(np.max(mesh["grid_ijk"][:, 1]) // 2))
        & (mesh["grid_ijk"][:, 2] == int(np.max(mesh["grid_ijk"][:, 2]) // 2))
    )
    if center_indices.size != 1:
        raise ValueError("Could not identify exactly one crown-center control node.")
    center_node = int(center_indices[0])
    free_dofs = _free_dof_count(mesh)
    reference_free_dofs = REFERENCE_FREE_DOFS.get(geometry)
    if reference_free_dofs is None or reference_free_dofs <= 0 or free_dofs <= 0:
        raise ValueError(f"Missing valid M1 free-DOF reference for {geometry}.")
    arc_scale = float(np.sqrt(free_dofs / reference_free_dofs))
    arc_radius = ARC_RADIUS * arc_scale
    arc_load_scale = ARC_LOAD_SCALE * arc_scale
    analysis = {
        "type": "nonlinear_static",
        "method": "arc_length",
        "kinematics": "total_lagrangian",
        "target_load_factor": LOAD_FACTOR_LIMIT,
        "max_iterations": MAX_NEWTON_ITERATIONS,
        "tolerance": NEWTON_TOLERANCE,
        "linear_method": "direct",
        "max_arc_steps": MAX_ACCEPTED_STEPS,
        "arc_length_stop_mode": "max_steps",
        "arc_length_allow_load_factor_turning": True,
        "arc_length_load_factor_limit": LOAD_FACTOR_LIMIT,
        "arc_length_radius": arc_radius,
        "max_arc_length_radius": arc_radius,
        "min_arc_length_radius": MIN_ARC_RADIUS * arc_scale,
        "adaptive_arc_length": False,
        "arc_length_load_scale": arc_load_scale,
        "arc_length_control_dof": 3 * center_node + 2,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_interval": 1,
        "checkpoint_keep_steps": True,
    }
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "TET4", "nodes": [int(node) for node in element], "material": "solid"} for element in elements],
        materials={"solid": {"type": "isotropic_3d", "E": YOUNG_MODULUS, "nu": POISSON_RATIO}},
        fixed_dofs=fixed_dofs,
        loads=loads,
        analysis=analysis,
    )
    dofs = model.dof_manager()
    expected = 3 * len(nodes)
    if dofs.ndof != expected:
        raise ValueError(f"Expected node-major XYZ DOFs ({expected}), found {dofs.ndof}.")
    for node in (0, center_node, len(nodes) - 1):
        if [dofs.index(node, name) for name in DOF_NAMES] != [3 * node, 3 * node + 1, 3 * node + 2]:
            raise ValueError("Unexpected global DOF ordering; refusing to run.")
    constrained = np.asarray(
        sorted({dofs.index(condition.node, name) for condition in model.fixed_dofs for name in condition.dofs}),
        dtype=int,
    )
    return model, constrained, support_nodes, center_node


def _reference_kinematics(
    nodes: np.ndarray,
    elements: np.ndarray,
    displacement: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Independent vectorized StVK kinematics/force/energy recomputation; no QF element calls."""
    xyz = nodes[elements]
    jacobian = np.transpose(xyz[:, 1:, :] - xyz[:, :1, :], (0, 2, 1))
    determinant = np.linalg.det(jacobian)
    if np.any(~np.isfinite(determinant)) or np.any(determinant <= 0.0):
        raise ValueError("Independent postprocessor found a non-positive reference TET4.")
    gradients = np.empty((len(elements), 4, 3), dtype=float)
    gradients[:, 1:, :] = np.linalg.inv(jacobian)
    gradients[:, 0, :] = -np.sum(gradients[:, 1:, :], axis=1)
    volumes = determinant / 6.0
    u_nodes = displacement.reshape((-1, 3))
    u_elements = u_nodes[elements]
    deformation = np.eye(3)[None, :, :] + np.einsum("eai,eaj->eij", u_elements, gradients, optimize=True)
    det_f = np.linalg.det(deformation)
    right_cauchy_green = np.einsum("eki,ekj->eij", deformation, deformation, optimize=True)
    green = 0.5 * (right_cauchy_green - np.eye(3)[None, :, :])
    trace_green = np.trace(green, axis1=1, axis2=2)
    lame_lambda = YOUNG_MODULUS * POISSON_RATIO / ((1.0 + POISSON_RATIO) * (1.0 - 2.0 * POISSON_RATIO))
    shear = YOUNG_MODULUS / (2.0 * (1.0 + POISSON_RATIO))
    second_piola = lame_lambda * trace_green[:, None, None] * np.eye(3)[None, :, :] + 2.0 * shear * green
    first_piola = np.einsum("eik,ekj->eij", deformation, second_piola, optimize=True)
    local_force = volumes[:, None, None] * np.einsum("eij,eaj->eai", first_piola, gradients, optimize=True)
    internal_force = np.zeros(3 * len(nodes), dtype=float)
    dof_ids = (3 * elements[:, :, None] + np.arange(3, dtype=int)).reshape(-1)
    np.add.at(internal_force, dof_ids, local_force.reshape(-1))
    energy_density = 0.5 * lame_lambda * trace_green**2 + shear * np.einsum("eij,eij->e", green, green)
    strain_norm = np.linalg.norm(green, axis=(1, 2))
    principal = np.sqrt(np.maximum(np.linalg.eigvalsh(right_cauchy_green), 0.0))
    return (
        internal_force,
        np.asarray([float(np.sum(volumes * energy_density))]),
        det_f,
        principal,
        strain_norm,
    )


def _state_metrics(
    mesh: dict[str, np.ndarray],
    displacement: np.ndarray,
    load_factor: float,
    constrained: np.ndarray,
    center_node: int,
) -> dict[str, Any]:
    nodes = mesh["nodes"]
    elements = mesh["elements"].astype(np.int64, copy=False)
    internal, energy, det_f, principal, strain_norm = _reference_kinematics(nodes, elements, displacement)
    external = load_factor * mesh["nodal_reference_loads"].reshape(-1)
    residual = internal - external
    reactions = np.zeros_like(residual)
    reactions[constrained] = residual[constrained]
    current = nodes + displacement.reshape((-1, 3))
    external_nodes = external.reshape((-1, 3))
    reaction_nodes = reactions.reshape((-1, 3))
    force_balance = np.sum(reaction_nodes + external_nodes, axis=0)
    reference_moment = np.sum(np.cross(nodes, reaction_nodes + external_nodes), axis=0)
    current_moment = np.sum(np.cross(current, reaction_nodes + external_nodes), axis=0)
    force_scale = max(float(np.linalg.norm(np.sum(external_nodes, axis=0))), 1.0e-12)
    moment_scale = max(force_scale * 2.0, 1.0e-12)
    return {
        "load_factor": float(load_factor),
        "q_centerline_crown": -float(displacement.reshape((-1, 3))[center_node, 2]),
        "q_over_rise": None,
        "displacement_l2": float(np.linalg.norm(displacement)),
        "strain_energy_independent_recomputation": float(energy[0]),
        "minimum_det_f": float(np.min(det_f)),
        "minimum_principal_stretch": float(np.min(principal)),
        "maximum_principal_stretch": float(np.max(principal)),
        "maximum_green_strain_frobenius": float(np.max(strain_norm)),
        "free_residual_l2": float(np.linalg.norm(np.delete(residual, constrained))),
        "force_balance_vector": force_balance.tolist(),
        "force_balance_relative": float(np.linalg.norm(force_balance) / force_scale),
        "reference_moment_balance_vector": reference_moment.tolist(),
        "reference_moment_balance_relative": float(np.linalg.norm(reference_moment) / moment_scale),
        "current_moment_balance_vector": current_moment.tolist(),
        "current_moment_balance_relative": float(np.linalg.norm(current_moment) / moment_scale),
    }


def _first_limit_point(states: list[dict[str, Any]]) -> dict[str, Any] | None:
    for index in range(1, len(states) - 1):
        before, peak, after = states[index - 1 : index + 2]
        if (
            peak["load_factor"] > before["load_factor"]
            and after["load_factor"] <= peak["load_factor"]
            and before["q_centerline_crown"] < peak["q_centerline_crown"] < after["q_centerline_crown"]
        ):
            return {
                "state_index_zero_based": index,
                "accepted_step": int(peak["step"]),
                "load_factor": peak["load_factor"],
                "q_centerline_crown": peak["q_centerline_crown"],
                "six_post_limit_endpoint_step": int(states[index + 6]["step"]) if index + 6 < len(states) else None,
            }
    return None


def _run_case(geometry: str, ratio: float, level: str, index: int) -> dict[str, Any]:
    case_id = f"{geometry}_{level}"
    case_dir = OUT / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    mesh_path = MESH_ROOT / f"{geometry}_{level}.npz"
    mesh = _load_mesh(geometry, level)
    checkpoint_path = case_dir / "accepted_state.npz"
    model, constrained, support_nodes, center_node = _build_model(mesh, checkpoint_path, geometry)
    mesh_report = check_mesh(model)
    if mesh_report.status == "FAIL":
        raise RuntimeError("Pre-solve mesh validation failed: " + "; ".join(mesh_report.errors))
    event_path = case_dir / "events.jsonl"
    _append_jsonl(event_path, {"event": "CASE_START", "case_id": case_id, "utc": datetime.now(timezone.utc).isoformat()})
    _write_json(
        OUT / "progress.json",
        {"status": "RUNNING", "current_case": case_id, "completed_cases": index, "total_cases": len(CASE_ORDER), "updated_utc": datetime.now(timezone.utc).isoformat()},
    )
    print(f"CASE_START {case_id} nodes={len(mesh['nodes'])} elements={len(mesh['elements'])} dofs={model.dof_manager().ndof}", flush=True)
    started = time.perf_counter()
    solve_status = "COMPLETED"
    solve_error: dict[str, Any] | None = None
    result_data: dict[str, Any] | None = None
    try:
        result = solve_model(model, enforce_policy=False)
        result_data = result.to_dict()
    except Exception as error:
        solve_status = "SOLVE_FAILED"
        solve_error = {"type": type(error).__name__, "message": str(error), "diagnostics": _plain(getattr(error, "diagnostics", {}))}
    checkpoint_files = sorted(case_dir.glob("accepted_state.step*.npz"))
    store = NpzNonlinearCheckpointStore()
    states: list[dict[str, Any]] = []
    displacements: list[np.ndarray] = []
    for checkpoint_file in checkpoint_files:
        checkpoint = store.load(checkpoint_file, model=model, expected_dofs=model.dof_manager().ndof)
        displacement = checkpoint.accepted_state.displacement.copy()
        state = _state_metrics(mesh, displacement, float(checkpoint.accepted_state.load_factor), constrained, center_node)
        state["step"] = int(checkpoint.completed_step)
        state["q_over_rise"] = state["q_centerline_crown"] / (2.0 * ratio)
        states.append(state)
        displacements.append(displacement)
        _append_jsonl(event_path, {"event": "ACCEPTED_STATE_POSTPROCESSED", "case_id": case_id, "step": state["step"], "lambda": state["load_factor"], "q_over_rise": state["q_over_rise"]})
    raw_path = case_dir / "accepted_path_raw.npz"
    np.savez_compressed(
        raw_path,
        steps=np.asarray([row["step"] for row in states], dtype=np.int32),
        load_factors=np.asarray([row["load_factor"] for row in states], dtype=float),
        displacements=np.asarray(displacements, dtype=float) if displacements else np.empty((0, model.dof_manager().ndof)),
    )
    limit = _first_limit_point(states)
    if limit is not None and limit["six_post_limit_endpoint_step"] is not None:
        endpoint_index = int(limit["state_index_zero_based"]) + 6
        path_through_endpoint = states[: endpoint_index + 1]
        limit["envelope_through_endpoint"] = {
            "pass": all(
                row["minimum_det_f"] >= ENVELOPE["det_f_min"]
                and row["minimum_principal_stretch"] >= ENVELOPE["principal_stretch_min"]
                and row["maximum_principal_stretch"] <= ENVELOPE["principal_stretch_max"]
                and row["maximum_green_strain_frobenius"] <= ENVELOPE["green_strain_frobenius_max"]
                for row in path_through_endpoint
            ),
            "checked_steps": [row["step"] for row in path_through_endpoint],
            "bounds": ENVELOPE,
        }
    result = {
        "case_id": case_id,
        "geometry": {"rise_span_ratio": ratio, "rise": 2.0 * ratio, "span": 2.0, "section": [0.10, 0.10]},
        "mesh_level": level,
        "nodes": int(len(mesh["nodes"])),
        "elements": int(len(mesh["elements"])),
        "dofs": int(model.dof_manager().ndof),
        "continuation_metric": {
            "kind": "free_dof_normalized_euclidean_augmented_arc_length_proxy",
            "free_dofs": _free_dof_count(mesh),
            "reference_free_dofs_m1": REFERENCE_FREE_DOFS[geometry],
            "scale": float(np.sqrt(_free_dof_count(mesh) / REFERENCE_FREE_DOFS[geometry])),
            "arc_length_radius": float(model.analysis.parameters["arc_length_radius"]),
            "arc_length_load_scale": float(model.analysis.parameters["arc_length_load_scale"]),
            "normalization_equation": "(n_free_M1/n_free)*||du_free||_2^2 + (base_load_scale*d_lambda)^2 = base_radius^2",
        },
        "fixed_support_nodes": int(len(support_nodes)),
        "crown_center_control_node": center_node,
        "mesh_input_sha256": _sha256(mesh_path),
        "case_status": solve_status,
        "solver_error": solve_error,
        "solver_result_status": result_data.get("status") if result_data else None,
        "solver_summary": result_data.get("solver", {}) if result_data else None,
        "accepted_state_count": len(states),
        "accepted_path": states,
        "first_limit_point_diagnostic": limit,
        "full_path_envelope_pass": all(
            row["minimum_det_f"] >= ENVELOPE["det_f_min"]
            and row["minimum_principal_stretch"] >= ENVELOPE["principal_stretch_min"]
            and row["maximum_principal_stretch"] <= ENVELOPE["principal_stretch_max"]
            and row["maximum_green_strain_frobenius"] <= ENVELOPE["green_strain_frobenius_max"]
            for row in states
        ) if states else None,
        "elapsed_seconds": time.perf_counter() - started,
        "raw_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
        "raw_path_sha256": _sha256(raw_path),
        "checkpoint_hashes": {str(path.relative_to(ROOT)).replace("\\", "/"): _sha256(path) for path in checkpoint_files},
        "observable_method": "independent vectorized StVK kinematics/internal-force recomputation from production accepted displacements; not an independent path solver",
        "formal_qualification_claimed": False,
    }
    _write_json(case_dir / "case_result.json", result)
    _append_jsonl(event_path, {"event": "CASE_END", "case_id": case_id, "status": solve_status, "accepted_states": len(states), "elapsed_seconds": result["elapsed_seconds"]})
    print(f"CASE_END {case_id} status={solve_status} accepted={len(states)} elapsed_s={result['elapsed_seconds']:.1f} limit={limit}", flush=True)
    return result


def _validate_models() -> None:
    for geometry, ratio, level in CASE_ORDER:
        mesh = _load_mesh(geometry, level)
        model, _constrained, support_nodes, _center = _build_model(
            mesh, OUT / "preflight-checkpoint.npz", geometry
        )
        report = check_mesh(model)
        if report.status == "FAIL":
            raise RuntimeError(f"{geometry}/{level} mesh validation failed: {'; '.join(report.errors)}")
        if len(support_nodes) != len(mesh["left_support_nodes"]) + len(mesh["right_support_nodes"]):
            raise RuntimeError(f"{geometry}/{level} support sets overlap.")
        print(
            f"PREFLIGHT_PASS {geometry}/{level} nodes={len(mesh['nodes'])} "
            f"elements={len(mesh['elements'])} dofs={model.dof_manager().ndof} "
            f"free_dofs={_free_dof_count(mesh)} "
            f"arc_radius={model.analysis.parameters['arc_length_radius']:.9g} "
            f"load_scale={model.analysis.parameters['arc_length_load_scale']:.9g}",
            flush=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-only", action="store_true", help="validate all candidate models without solving")
    args = parser.parse_args()
    if _git("branch", "--show-current") != "codex/wp06-score-requalification":
        raise SystemExit("Refusing to run outside the isolated WP06 diagnostic branch.")
    if _git("status", "--porcelain", "--", "src/solveur"):
        raise SystemExit("Refusing to run: production solver source has uncommitted changes.")
    for module_path in (Path(public_api.__file__).resolve(), Path(checkpoint_module.__file__).resolve()):
        try:
            module_path.relative_to(LOCAL_SOURCE.resolve())
        except ValueError as error:
            raise SystemExit(f"Refusing to run with a non-worktree solver import: {module_path}") from error
    if args.preflight_only:
        for geometry, _ratio in GEOMETRIES:
            REFERENCE_FREE_DOFS[geometry] = _free_dof_count(_load_mesh(geometry, "M1"))
        _validate_models()
        return 0
    if OUT.exists():
        raise SystemExit(f"Refusing to overwrite exploratory output: {OUT}")
    for geometry, _ratio in GEOMETRIES:
        REFERENCE_FREE_DOFS[geometry] = _free_dof_count(_load_mesh(geometry, "M1"))
    _validate_models()
    OUT.mkdir(parents=True, exist_ok=False)
    dirty_paths = _git("status", "--porcelain").splitlines()
    source_files = sorted((ROOT / "src" / "solveur").rglob("*.py"))
    source_digest = hashlib.sha256()
    for source in source_files:
        source_digest.update(source.relative_to(ROOT).as_posix().encode("utf-8"))
        source_digest.update(b"\0")
        source_digest.update(source.read_bytes())
        source_digest.update(b"\0")
    metadata = {
        "study": "Owner-authorized exploratory low-strain WP06-D candidate model comparison",
        "classification": "DIAGNOSTIC_ONLY_NOT_FORMAL_REQUALIFICATION",
        "owner_authorization": "User explicitly approved launching the candidate calculations in this conversation.",
        "branch": _git("branch", "--show-current"),
        "head_sha": _git("rev-parse", "HEAD"),
        "execution_source_sha": _git("rev-parse", "HEAD"),
        "working_tree_dirty_at_start": bool(dirty_paths),
        "dirty_paths_at_start": dirty_paths,
        "production_source_worktree_diff": False,
        "production_source_tree_sha256": source_digest.hexdigest(),
        "solver_api_module": str(Path(public_api.__file__).resolve()),
        "checkpoint_module": str(Path(checkpoint_module.__file__).resolve()),
        "runner_sha256": _sha256(Path(__file__).resolve()),
        "mesh_manifest_sha256": _sha256(MESH_ROOT / "candidate_mesh_audit_manifest.json"),
        "geometries_and_order": [{"geometry": geometry, "rise_span_ratio": ratio, "levels": list(LEVELS)} for geometry, ratio in GEOMETRIES],
        "case_order": [f"{geometry}_{level}" for geometry, _ratio, level in CASE_ORDER],
        "material": {"model": "StVK", "young_modulus": YOUNG_MODULUS, "poisson_ratio": POISSON_RATIO},
        "supports": "full clamped end faces; all translations fixed at both end-bearing patches; no symmetry plane constraint",
        "load": "meshwise consistent nodal-equivalent crown-patch dead load; resultant [0,0,-1]",
        "solver": {"method": "arc_length", "linear_method": "direct", "tolerance": NEWTON_TOLERANCE, "max_newton_iterations": MAX_NEWTON_ITERATIONS, "base_arc_length_radius_m1": ARC_RADIUS, "base_load_scale_m1": ARC_LOAD_SCALE, "min_arc_length_radius_m1": MIN_ARC_RADIUS, "max_accepted_steps": MAX_ACCEPTED_STEPS, "adaptive_arc_length": False, "load_factor_limit": LOAD_FACTOR_LIMIT, "fallback": "no explicit fallback enabled"},
        "continuation_metric": {
            "kind": "free_dof_normalized_euclidean_augmented_arc_length_proxy",
            "formula": "(n_free_M1/n_free)*||du_free||_2^2 + (base_load_scale*d_lambda)^2 = base_radius^2",
            "scaling": "arc_length_radius and arc_length_load_scale are both multiplied by sqrt(n_free/n_free_M1)",
            "limitation": "DOF-count normalization is a diagnostic proxy, not a volume-weighted continuum metric or frozen qualification contract.",
            "reference_free_dofs_by_geometry": REFERENCE_FREE_DOFS,
        },
        "observable_convention": "q is negative UZ at the full-model crown centerline node; reference and current-coordinate moment balances are both reported; selected envelope is evaluated at every archived accepted state",
        "independent_check": "standalone vectorized StVK kinematics/internal-force recomputation; no independent nonlinear path solve or replay",
        "formal_contract_or_ledger_modified": False,
        "historical_r1_r2_evidence_modified": False,
        "production_mechanics_changed": False,
        "thresholds_changed": False,
        "parallel_solves": False,
        "blas_threads_during_limit_probe": None,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
    }
    cases: list[dict[str, Any]] = []
    with threadpool_limits(limits=1):
        metadata["blas_threads_during_limit_probe"] = threadpool_info()
        _write_json(OUT / "study_metadata.json", metadata)
        _write_json(OUT / "progress.json", {"status": "READY", "completed_cases": 0, "total_cases": len(CASE_ORDER), "updated_utc": datetime.now(timezone.utc).isoformat()})
        for index, (geometry, ratio, level) in enumerate(CASE_ORDER):
            try:
                case = _run_case(geometry, ratio, level, index)
            except Exception as error:
                case = {"case_id": f"{geometry}_{level}", "case_status": "PRECHECK_OR_POSTPROCESS_FAILED", "error_type": type(error).__name__, "error": str(error)}
                _write_json(OUT / f"{geometry}_{level}_runner_error.json", case)
                print(f"CASE_ERROR {case['case_id']} {case['error_type']}: {case['error']}", flush=True)
            cases.append(case)
            _write_json(OUT / "study_partial.json", {"metadata": metadata, "completed_cases": cases})
            _write_json(OUT / "progress.json", {"status": "RUNNING", "completed_cases": len(cases), "total_cases": len(CASE_ORDER), "last_case": case["case_id"], "last_case_status": case["case_status"], "updated_utc": datetime.now(timezone.utc).isoformat()})
    by_geometry: dict[str, Any] = {}
    for geometry, ratio in GEOMETRIES:
        mesh_cases = [row for row in cases if row.get("geometry", {}).get("rise_span_ratio") == ratio]
        by_geometry[geometry] = {
            "rise_span_ratio": ratio,
            "levels": [
                {
                    "level": row.get("mesh_level"),
                    "status": row.get("case_status"),
                    "accepted_states": row.get("accepted_state_count"),
                    "limit_point": row.get("first_limit_point_diagnostic"),
                    "endpoint": row.get("accepted_path", [])[-1] if row.get("accepted_path") else None,
                    "elapsed_seconds": row.get("elapsed_seconds"),
                }
                for row in mesh_cases
            ],
        }
    completed = len(cases) == len(CASE_ORDER)
    all_ran = completed and all(row.get("case_status") == "COMPLETED" for row in cases)
    final = {
        "schema_version": 1,
        "status": "COMPLETED_DIAGNOSTIC_ONLY" if all_ran else "INCOMPLETE_DIAGNOSTIC",
        "metadata": metadata,
        "cases": cases,
        "geometry_comparison": by_geometry,
        "interpretation_limits": [
            "These calculations are exploratory and cannot award WP06-D points or replace formal R2/R3 evidence.",
            "The independent post-processing recomputes observables from production displacement states; it is not an independent equilibrium path solve.",
            "No deterministic replay was run.",
            "The 80-step horizon and M1-referenced free-DOF-normalized arc metric are exploratory settings, not a frozen contract.",
            "A missing detected limit point, failed solve, or envelope violation remains visible and is not converted to PASS.",
        ],
    }
    _write_json(OUT / "study_final.json", final)
    _write_json(OUT / "progress.json", {"status": final["status"], "completed_cases": len(cases), "total_cases": len(CASE_ORDER), "updated_utc": datetime.now(timezone.utc).isoformat()})
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "integrity_manifest.json")
    _write_json(OUT / "integrity_manifest.json", {"schema_version": 1, "study_status": final["status"], "files": {str(path.relative_to(ROOT)).replace("\\", "/"): _sha256(path) for path in files}})
    print(f"STUDY_END status={final['status']} output={OUT}", flush=True)
    return 0 if all_ran else 2


if __name__ == "__main__":
    raise SystemExit(main())
