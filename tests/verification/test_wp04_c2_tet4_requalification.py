"""Controlled WP04-C2 TET4 finer-mesh requalification harness.

The contract is frozen before this module executes a nonlinear mesh.  It uses
the same physical problem and public sparse Newton route as WP04-C/C1.  A
resource limit is evidence, never a reason to change an element, load,
tolerance, or solver policy.
"""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
from scipy.sparse.linalg import spsolve

from solveur.core.analyses.geometric_nonlinear import _newton_dead_load
from solveur.core.nonlinear.state import NonlinearState
from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.materials.solid import SolidMaterial


ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_9"
CONTRACT = QUALIFICATION / "wp04_c2_tet4_requalification_contract.json"
SUMMARY_PATH = QUALIFICATION / "wp04_c2_tet4_requalification.json"
RAW_PATH = QUALIFICATION / "wp04_c2_tet4_requalification_raw.npz"
HISTORICAL_C = QUALIFICATION / "wp04_c_tet4_structural_summary.json"
HISTORICAL_C1 = QUALIFICATION / "wp04_c1_tet4_mesh_diagnosis.json"

LENGTH, HEIGHT, DEPTH = 4.0, 0.5, 0.5
MATERIAL = SolidMaterial(E=1.0e6, nu=0.30)
TOTAL_LOAD = np.asarray([0.0, -50.0, 0.0])
LEVELS: dict[str, tuple[int, int, int]] = {
    "C2-M1": (32, 16, 16),
    "C2-M2": (48, 24, 24),
    "C2-M3": (64, 32, 32),
    "C2-M4": (96, 48, 48),
}
REQUIRED = ("C2-M1", "C2-M2", "C2-M3")


def _mesh(cells: tuple[int, int, int]) -> tuple[np.ndarray, np.ndarray]:
    nx, ny, nz = cells
    coordinates = np.stack(
        np.meshgrid(np.linspace(0.0, LENGTH, nx + 1), np.linspace(0.0, HEIGHT, ny + 1), np.linspace(0.0, DEPTH, nz + 1), indexing="ij"),
        axis=-1,
    ).reshape(-1, 3)

    def node(i: int, j: int, k: int) -> int:
        return i * (ny + 1) * (nz + 1) + j * (nz + 1) + k

    pattern = ((0, 1, 3, 7), (0, 3, 2, 7), (0, 2, 6, 7), (0, 6, 4, 7), (0, 4, 5, 7), (0, 5, 1, 7))
    elements: list[list[int]] = []
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                cube = [node(a, b, c) for a, b, c in ((i, j, k), (i + 1, j, k), (i, j + 1, k), (i + 1, j + 1, k), (i, j, k + 1), (i + 1, j, k + 1), (i, j + 1, k + 1), (i + 1, j + 1, k + 1))]
                elements.extend([[cube[index] for index in tetrahedron] for tetrahedron in pattern])
    return coordinates, np.asarray(elements, dtype=int)


def _case(level: str) -> dict[str, Any]:
    nodes, elements = _mesh(LEVELS[level])
    assembly = TotalLagrangianTet4Assembly(nodes, elements, MATERIAL)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], LENGTH))
    fixed = (3 * fixed_nodes[:, None] + np.arange(3)).reshape(-1)
    external = np.zeros(assembly.ndof)
    external.reshape(-1, 3)[loaded_nodes] = TOTAL_LOAD / loaded_nodes.size
    centroid = np.mean(nodes[elements], axis=1)
    stress_mask = ((centroid[:, 0] / LENGTH >= 0.40) & (centroid[:, 0] / LENGTH <= 0.60) & (centroid[:, 1] / HEIGHT >= 0.75) & (centroid[:, 1] / HEIGHT <= 0.90) & (centroid[:, 2] / DEPTH >= 0.25) & (centroid[:, 2] / DEPTH <= 0.75))
    if not np.any(stress_mask):
        raise AssertionError("The frozen stress region has no contributing TET4 elements.")
    return {"nodes": nodes, "elements": elements, "assembly": assembly, "fixed": fixed, "loaded_nodes": loaded_nodes, "external": external, "stress_mask": stress_mask, "centroid": centroid}


def _free(ndof: int, fixed: np.ndarray) -> np.ndarray:
    return np.setdiff1d(np.arange(ndof), fixed)


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), 1.0e-12)


def _mesh_metrics(case: dict[str, Any]) -> dict[str, Any]:
    nodes = np.asarray(case["nodes"])
    elements = np.asarray(case["elements"])
    volumes = np.asarray(case["assembly"].volumes)
    loaded = np.asarray(case["loaded_nodes"])
    applied = np.asarray(case["external"]).reshape(-1, 3)[loaded]
    weights = -applied[:, 1]
    return {
        "nodes": int(nodes.shape[0]), "elements": int(elements.shape[0]), "dofs": int(case["assembly"].ndof),
        "domain_volume_error": float(abs(np.sum(volumes) - 1.0)), "orientation_failures": int(np.count_nonzero(volumes <= 0.0)),
        "total_load": np.sum(applied, axis=0).tolist(), "load_centroid": np.average(nodes[loaded], axis=0, weights=weights).tolist(),
        "stress_region_elements": int(np.count_nonzero(case["stress_mask"])), "stress_region_volume": float(np.sum(volumes[case["stress_mask"]])),
    }


def _equilibrium(case: dict[str, Any], displacement: np.ndarray, internal: np.ndarray) -> dict[str, float]:
    reactions = np.zeros_like(internal)
    reactions[case["fixed"]] = internal[case["fixed"]] - case["external"][case["fixed"]]
    physical = case["nodes"] + displacement.reshape(-1, 3)
    external = case["external"].reshape(-1, 3)
    reaction = reactions.reshape(-1, 3)
    force = np.sum(external, axis=0) + np.sum(reaction, axis=0)
    moment = np.sum(np.cross(physical, external), axis=0) + np.sum(np.cross(physical, reaction), axis=0)
    force_scale = max(float(np.linalg.norm(np.sum(external, axis=0))), float(np.linalg.norm(np.sum(reaction, axis=0))), 1.0)
    moment_scale = max(float(np.linalg.norm(np.sum(np.cross(physical, external), axis=0))), float(np.linalg.norm(np.sum(np.cross(physical, reaction), axis=0))), 1.0)
    return {"force_relative_error": float(np.linalg.norm(force) / force_scale), "moment_relative_error": float(np.linalg.norm(moment) / moment_scale), "reaction_resultant_norm": float(np.linalg.norm(np.sum(reaction, axis=0)))}


def _observe(case: dict[str, Any], displacement: np.ndarray) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    assembly = case["assembly"]
    states = assembly.element_states(displacement)
    volumes = np.asarray(assembly.volumes)[case["stress_mask"]]
    sigma_xx = np.asarray(states["cauchy_stress"])[case["stress_mask"], 0, 0]
    stretches = np.linalg.svd(np.asarray(states["deformation_gradient"]), compute_uv=False)
    green = np.linalg.norm(np.asarray(states["green_lagrange_strain"]), axis=(1, 2))
    return {
        "tip_displacement": float(np.mean(displacement.reshape(-1, 3)[case["loaded_nodes"], 1])),
        "strain_energy": float(assembly.strain_energy(displacement)),
        "representative_stress_sigma_xx": float(np.dot(volumes, sigma_xx) / np.sum(volumes)),
        "minimum_det_f": float(np.min(states["det_f"])), "minimum_principal_stretch": float(np.min(stretches)),
        "maximum_principal_stretch": float(np.max(stretches)), "maximum_green_lagrange_norm": float(np.max(green)),
    }, {"det_f": np.asarray(states["det_f"]), "green_norm": green, "displacement": displacement}


def _linear(level: str) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    started = perf_counter()
    case = _case(level)
    _, tangent = case["assembly"].assemble(np.zeros(case["assembly"].ndof), tangent_required=True)
    if tangent is None:
        raise AssertionError("Missing zero-state tangent.")
    displacement = np.zeros(case["assembly"].ndof)
    free = _free(case["assembly"].ndof, case["fixed"])
    displacement[free] = np.asarray(spsolve(tangent[free, :][:, free], case["external"][free]))
    observed, arrays = _observe(case, displacement)
    observed.update({"mesh": _mesh_metrics(case), "runtime_seconds": perf_counter() - started})
    return observed, arrays


def _nonlinear(level: str) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    started = perf_counter()
    case = _case(level)
    accepted: list[NonlinearState] = []
    def callback(_step: int, state: NonlinearState) -> None:
        accepted.append(state.detached_copy())
    displacement, diagnostics = _newton_dead_load(case["assembly"], case["external"], case["fixed"], increments=12, tolerance=1.0e-10, max_iterations=40, initial_state=NonlinearState(np.zeros(case["assembly"].ndof), continuation_state={"accepted_step": 0}), target_load_factors=[step / 12 for step in range(1, 13)], accepted_state_callback=callback)
    if len(accepted) != 12:
        raise AssertionError("C2 must observe only the twelve accepted states.")
    internal, _ = case["assembly"].assemble(displacement, tangent_required=False)
    observed, arrays = _observe(case, displacement)
    observed.update({"mesh": _mesh_metrics(case), "equilibrium": _equilibrium(case, displacement, internal), "runtime_seconds": perf_counter() - started, "newton_iterations": int(sum(int(row["iterations"]) for row in diagnostics["increments"])), "accepted_digest": accepted[-1].digest, "accepted_factors": [state.load_factor for state in accepted]})
    return observed, arrays


def _deltas(rows: dict[str, dict[str, Any]], left: str, right: str) -> dict[str, float]:
    return {
        "displacement": _relative(rows[right]["tip_displacement"], rows[left]["tip_displacement"]),
        "energy": _relative(rows[right]["strain_energy"], rows[left]["strain_energy"]),
        "stress": _relative(rows[right]["representative_stress_sigma_xx"], rows[left]["representative_stress_sigma_xx"]),
        "reaction": _relative(rows[right].get("equilibrium", {"reaction_resultant_norm": 50.0})["reaction_resultant_norm"], rows[left].get("equilibrium", {"reaction_resultant_norm": 50.0})["reaction_resultant_norm"]),
    }


def test_c2_contract_is_frozen_before_results() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["status"] == "FROZEN_BEFORE_RESULT_EXECUTION"
    assert contract["mesh_sequence"]["C2-M3"]["cells"] == [64, 32, 32]
    assert contract["thresholds"]["tip_displacement_relative"] == 0.02


def run_campaign(output_dir: Path | None = None) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Execute the predeclared C2 campaign and persist a bounded outcome."""
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    linear: dict[str, dict[str, Any]] = {}
    nonlinear: dict[str, dict[str, Any]] = {}
    arrays: dict[str, np.ndarray] = {}
    resource_error: str | None = None
    try:
        for level in REQUIRED:
            row, raw = _linear(level)
            linear[level] = row
            for key, value in raw.items():
                arrays[f"linear_{level}_{key}"] = value
    except (MemoryError, OSError, RuntimeError) as exc:
        resource_error = f"linear {level}: {type(exc).__name__}: {exc}"
    if resource_error is None:
        try:
            for level in REQUIRED:
                row, raw = _nonlinear(level)
                nonlinear[level] = row
                for key, value in raw.items():
                    arrays[f"nonlinear_{level}_{key}"] = value
        except (MemoryError, OSError, RuntimeError) as exc:
            resource_error = f"nonlinear {level}: {type(exc).__name__}: {exc}"
    status = "UNRESOLVED_RESOURCE_LIMIT" if resource_error else "EXECUTED_TARGETED"
    final_pair: dict[str, float] | None = None
    if len(nonlinear) == 3:
        final_pair = _deltas(nonlinear, "C2-M2", "C2-M3")
        pass_pair = final_pair["displacement"] <= 0.02 and final_pair["energy"] <= 0.02 and final_pair["stress"] <= 0.10 and final_pair["reaction"] <= 0.02
        status = "PASS_REQUALIFIED_CANDIDATE" if pass_pair else "FAIL_CURRENT_TET4_SCOPE"
    summary = {
        "schema_version": 1,
        "record_id": "QF-SOLVER-0.2.9-WP04-C2-TET4-REQUALIFICATION-001",
        "work_package": "WP04-C2",
        "status": status,
        "contract": str(CONTRACT.relative_to(ROOT)).replace("\\", "/"),
        "contract_status": contract["status"],
        "historical_wp04_c": {"status": "FAIL", "hold_sha": "a5c3031f6b28b00476e328daff4845a741a5c161"},
        "wp04_c1_diagnosis": {"value": "SLOW_TET4_DISCRETIZATION_CONVERGENCE", "sha": "f52465b008f0171c26386a7e24824f5d1cc9d807"},
        "linear": linear,
        "nonlinear": nonlinear,
        "final_pair": final_pair,
        "resource_error": resource_error,
        "full_test_suite_run": False,
        "production_source_changed": False,
        "numerical_formulation_changed": False,
        "maturity_changed": False,
        "G04-10": "PASS_REQUALIFIED" if status == "PASS_REQUALIFIED_CANDIDATE" else ("UNRESOLVED_RESOURCE_LIMIT" if resource_error else "FAIL_CURRENT_TET4_SCOPE"),
    }
    destination = QUALIFICATION if output_dir is None else Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / SUMMARY_PATH.name).write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    np.savez_compressed(destination / RAW_PATH.name, **arrays)  # type: ignore[arg-type]
    return summary, arrays


if __name__ == "__main__":
    run_campaign()
