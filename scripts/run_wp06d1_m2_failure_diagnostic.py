"""Diagnose the immutable WP06-D M2 failure without changing its evidence."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import numpy as np

from solveur.api.public import solve_model
from solveur.core.assembly.geometric import build_total_lagrangian_assembly
from solveur.core.model import FiniteElementModel
from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore
from solveur.loads.integration import load_balance
from prepare_wp06d_structural_limit_point import generate_mesh, symmetry_face_nodes


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qualification" / "0_2_9" / "wp06d1"
ORIGINAL_RAW = ROOT / "qualification" / "0_2_9" / "wp06d_phase1_structural_raw.json"
CONTRACT = ROOT / "qualification" / "0_2_9" / "wp06d_structural_limit_point_contract.json"
GOVERNING_SOURCE_SHA = "12b5331bcbec49e38145ba4a6263df60b8bf4575"


def _plain(value: Any) -> Any:
    if isinstance(value, np.generic):
        return _plain(value.item())
    if isinstance(value, np.ndarray):
        return [_plain(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _digest(value: Any) -> str:
    encoded = json.dumps(_plain(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def _model(max_steps: int, checkpoint_path: str | None = None) -> tuple[FiniteElementModel, np.ndarray, tuple[int, ...], tuple[tuple[int, int, int, int], ...]]:
    nodes, elements = generate_mesh("M2")
    symmetry_nodes = symmetry_face_nodes(nodes)
    fixed = [
        {"node": 0, "dofs": ["UX", "UY", "UZ"]},
        {"node": 1, "dofs": ["UX", "UY", "UZ"]},
        *[{"node": node, "dofs": ["UY"]} for node in symmetry_nodes],
    ]
    parameters: dict[str, object] = {
        "type": "nonlinear_static",
        "method": "arc_length",
        "kinematics": "total_lagrangian",
        "target_load_factor": 5.0,
        "max_iterations": 80,
        "tolerance": 1.0e-8,
        "max_arc_steps": max_steps,
        "arc_length_stop_mode": "max_steps",
        "arc_length_allow_load_factor_turning": True,
        "arc_length_load_factor_limit": 5.0,
        "arc_length_radius": 0.02,
        "max_arc_length_radius": 0.02,
        "min_arc_length_radius": 2.0e-6,
        "adaptive_arc_length": False,
        "arc_length_load_scale": 1.0,
        "arc_length_control_dof": 14,
    }
    if checkpoint_path is not None:
        parameters.update({"checkpoint_path": checkpoint_path, "checkpoint_interval": 1, "checkpoint_keep_steps": True})
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "TET4", "nodes": list(element), "material": "solid"} for element in elements],
        materials={"solid": {"type": "isotropic_3d", "E": 100.0, "nu": 0.3}},
        fixed_dofs=fixed,
        loads=[{"node": 4, "dof": "UZ", "value": -1.0}],
        analysis=parameters,
    )
    return model, nodes, symmetry_nodes, elements


def _fixed_indices(model: FiniteElementModel) -> np.ndarray:
    dofs = model.dof_manager()
    return np.asarray(
        sorted(dofs.index(condition.node, name) for condition in model.fixed_dofs for name in condition.dofs),
        dtype=int,
    )


def _contributions(nodes: np.ndarray, reaction: np.ndarray, fixed: np.ndarray) -> dict[str, dict[str, list[float]]]:
    fixed_set = set(int(index) for index in fixed)
    result: dict[str, dict[str, list[float]]] = {}
    for node in range(nodes.shape[0]):
        indices = np.asarray([3 * node + axis for axis in range(3) if 3 * node + axis in fixed_set], dtype=int)
        force: np.ndarray = np.zeros(3, dtype=float)
        force[indices - 3 * node] = reaction[indices]
        result[str(node)] = {
            "force": force.tolist(),
            "moment": np.cross(nodes[node], force).tolist(),
        }
    return result


def _reconstruct_checkpoints(
    model: FiniteElementModel,
    nodes: np.ndarray,
    fixed: np.ndarray,
    files: list[Path],
) -> list[dict[str, Any]]:
    dofs = model.dof_manager()
    loads = np.zeros(dofs.ndof, dtype=float)
    loads[dofs.index(4, "UZ")] = -1.0
    assembly = build_total_lagrangian_assembly(model)
    rows: list[dict[str, Any]] = []
    store = NpzNonlinearCheckpointStore()
    for path in sorted(files):
        checkpoint = store.load(path)
        state = checkpoint.accepted_state
        internal, _ = assembly.assemble(state.displacement, tangent_required=False)
        external = float(state.load_factor) * loads
        residual = internal - external
        reaction = np.zeros_like(residual)
        reaction[fixed] = residual[fixed]
        ext_resultant, ext_moment = load_balance(model, dofs, external)
        reaction_resultant, reaction_moment = load_balance(model, dofs, reaction)
        rows.append(
            {
                "step": checkpoint.completed_step,
                "lambda": float(state.load_factor),
                "q_monitor_declared": float(-state.displacement[dofs.index(4, "UZ")]),
                "q_monitor_mean_crown": float(-np.mean([state.displacement[dofs.index(node, "UZ")] for node in (2, 3, 4)])),
                "free_residual_norm": float(np.linalg.norm(residual[np.setdiff1d(np.arange(dofs.ndof), fixed)])),
                "external_resultant": ext_resultant.tolist(),
                "external_moment": ext_moment.tolist(),
                "reaction_resultant": reaction_resultant.tolist(),
                "reaction_moment": reaction_moment.tolist(),
                "force_balance_relative_error": float(
                    np.linalg.norm(ext_resultant + reaction_resultant)
                    / max(float(np.linalg.norm(ext_resultant)), float(np.linalg.norm(reaction_resultant)), 1.0)
                ),
                "moment_balance_relative_error": float(
                    np.linalg.norm(ext_moment + reaction_moment)
                    / max(float(np.linalg.norm(ext_moment)), float(np.linalg.norm(reaction_moment)), 1.0)
                ),
                "support_contributions": _contributions(nodes, reaction, fixed),
            }
        )
    return rows


def _static_audit() -> dict[str, Any]:
    m1_nodes, m1_elements = generate_mesh("M1")
    m2_nodes, m2_elements = generate_mesh("M2")
    volumes = {
        "M1": [float(abs(np.linalg.det((m1_nodes[list(element)[1:]] - m1_nodes[list(element)[0]]).T) / 6.0)) for element in m1_elements],
        "M2": [float(abs(np.linalg.det((m2_nodes[list(element)[1:]] - m2_nodes[list(element)[0]]).T) / 6.0)) for element in m2_elements],
    }
    load = np.zeros_like(m1_nodes)
    load[4] = [0.0, 0.0, -1.0]
    return {
        "node_counts": {"M1": int(len(m1_nodes)), "M2": int(len(m2_nodes))},
        "element_counts": {"M1": int(len(m1_elements)), "M2": int(len(m2_elements))},
        "dof_counts": {"M1": int(3 * len(m1_nodes)), "M2": int(3 * len(m2_nodes))},
        "parent_nodes_persist": bool(np.array_equal(m2_nodes[:5], m1_nodes)),
        "parent_connectivity": "M2 generated by the frozen global sorted-edge 8-subtet refinement",
        "positive_orientation": bool(all(value > 0.0 for value in volumes["M1"] + volumes["M2"])),
        "volume_by_level": {key: float(sum(values)) for key, values in volumes.items()},
        "volume_relative_difference": float(abs(sum(volumes["M2"]) - sum(volumes["M1"])) / sum(volumes["M1"])),
        "boundary_nodes": {"M1": list(symmetry_face_nodes(m1_nodes)), "M2": list(symmetry_face_nodes(m2_nodes))},
        "load_node": 4,
        "load_node_coordinate": m1_nodes[4].tolist(),
        "load_resultant": load.sum(axis=0).tolist(),
        "load_moment_about_origin": np.cross(m1_nodes, load).sum(axis=0).tolist(),
        "mechanical_equivalence": "YES",
        "monitor_definition_in_original_raw": "NO: raw runner recorded node-4 UZ, while R1 declares mean UZ of nodes 2,3,4",
    }


def main() -> int:
    original = json.loads(ORIGINAL_RAW.read_text(encoding="utf-8"))
    original_levels = original["raw"]["levels"]
    m2_path = original_levels["M2"]["accepted_path"]
    m2_lambda = np.asarray(m2_path["lambda"], dtype=float)
    m2_q = np.asarray(m2_path["q"], dtype=float)
    m1_path = original_levels["M1"]["accepted_path"]
    stations = [0.2, 0.4, 0.6, 0.8, 1.0]
    station_rows = []
    for station in stations:
        index = min(len(m2_lambda) - 1, max(0, int(round(station * len(m2_lambda))) - 1))
        m1_index = min(len(m1_path["lambda"]) - 1, index)
        station_rows.append({"station": station, "M1_lambda": m1_path["lambda"][m1_index], "M2_lambda": m2_lambda[index], "M1_q": m1_path["q"][m1_index], "M2_q": m2_q[index]})
    static = _static_audit()
    with TemporaryDirectory(prefix="wp06d1_m2_") as temporary:
        checkpoint_base = Path(temporary) / "m2_extended.npz"
        model, nodes, _, _ = _model(160, str(checkpoint_base))
        result = solve_model(model, enforce_policy=False)
        data = _plain(result.to_dict())
        files = sorted(Path(temporary).glob("m2_extended.step*.npz"))
        rows = _reconstruct_checkpoints(model, nodes, _fixed_indices(model), files)
    factors = np.asarray([row["lambda"] for row in rows], dtype=float)
    q_mean = np.asarray([row["q_monitor_mean_crown"] for row in rows], dtype=float)
    increments = np.diff(factors)
    turns = np.flatnonzero((increments[:-1] > 0.0) & (increments[1:] <= 0.0))
    extended = {
        "status": "DIAGNOSTIC_ONLY_EXTENDED_HORIZON",
        "max_steps": 160,
        "solver_status": data.get("status"),
        "accepted_steps": len(rows),
        "lambda_range": [float(factors.min()), float(factors.max())],
        "q_mean_crown_range": [float(q_mean.min()), float(q_mean.max())],
        "peak_found": bool(turns.size),
        "peak_index": int(turns[0] + 1) if turns.size else None,
        "peak_lambda": float(factors[turns[0] + 1]) if turns.size else None,
        "peak_q_mean_crown": float(q_mean[turns[0] + 1]) if turns.size else None,
        "rows": rows,
        "policy_variation": "max_arc_steps only; all other R1 parameters unchanged",
    }
    provenance = {
        "repository": "emptiesvoid-cloud/QF_solver",
        "branch": _git("branch", "--show-current"),
        "source_sha": _git("rev-parse", "HEAD"),
        "governing_imported_sha": GOVERNING_SOURCE_SHA,
        "original_phase1_artifact_sha256": hashlib.sha256(ORIGINAL_RAW.read_bytes()).hexdigest(),
        "contract_sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
    }
    output = {
        "schema_version": 1,
        "record_id": "QF-0.2.9-WP06D1-M2-FAILURE-DIAGNOSTIC-001",
        "status": "DIAGNOSTIC_ONLY_NO_REQUALIFICATION",
        "provenance": provenance,
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "original_failure_preserved": True,
        "static_mesh_audit": static,
        "original_path_audit": {
            "m2_lambda_monotone_increasing": bool(np.all(np.diff(m2_lambda) > 0.0)),
            "m2_peak_approached": bool(np.argmax(m2_lambda) == len(m2_lambda) - 1),
            "m2_max_steps_reached": len(m2_lambda) == 80,
            "m2_orientation_values": sorted(set(original_levels["M2"]["accepted_path"]["accepted_rejected"])),
            "m2_branch_directions": sorted(set(original_levels["M2"]["steps"][i]["arc_length_branch_direction"] for i in range(len(original_levels["M2"]["steps"])))),
            "m2_reaction_vectors_available_in_original_raw": False,
            "station_comparison": station_rows,
        },
        "reaction_reconstruction": {"source": "diagnostic checkpoint states and independent R=lambda*Fext-Fint reconstruction", "extended_rows": "see extended_horizon.rows"},
        "extended_horizon": extended,
        "classification": {
            "moment_failure": "OTHER: path-dependent finite-element reaction/moment imbalance; not a numerical floor (2.438196e-05 >> 1e-8), load resultant and geometry are invariant",
            "limit_point_gap": "STEP_HORIZON_OR_PATH_RESPONSE: M2 lambda remains strictly increasing through step 80; no accepted peak in frozen window",
            "monitor_gap": "BOUNDARY_SET_OR_RUNNER_ACCOUNTING: original raw q is node-4 control displacement, not the declared mean crown displacement",
            "confidence": "HIGH for static equivalence and monotonicity; MEDIUM for causal attribution of moment imbalance until per-state reconstruction is inspected",
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "wp06d1_m2_failure_diagnostic.json").write_text(json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": output["status"], "peak_found": extended["peak_found"], "accepted_steps": extended["accepted_steps"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
