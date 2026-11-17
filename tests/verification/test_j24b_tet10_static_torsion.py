"""One-owner-authorized, four-mesh J24B static torsion campaign.

The launcher invokes this exact node only after a collect-only preflight.
Each mesh gets an atomic checkpoint in the controller's attempt output.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
import psutil

from solveur.benchmarks.solid_extended import apply_consistent_circular_torsion
from solveur.core.qualification import enforce_qualification_policy
from solveur.core.router import AnalysisRouter
from solveur.mesh.gmsh_importer import GmshModelImporter


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "research/j24b/tet10_torsion/contract.json"
CORRECTED_H1_CONTRACT_PATH = ROOT / "research/j24b/tet10_torsion/contract-002-h1-digest-corrected.json"
LEVELS = ("h1", "h2", "h3", "h4")
ORIGINAL_NODEID = "tests/verification/test_j24b_tet10_static_torsion.py::test_j24b_tet10_static_torsion_four_meshes"
CORRECTED_H1_NODEID = (
    "tests/verification/test_j24b_tet10_static_torsion.py::"
    "test_j24b_tet10_static_torsion_four_meshes_corrected_h1_digest"
)
TORQUE_NM = 1000.0
RADIUS_M = 0.5
POLAR_MOMENT_M4 = 0.5 * math.pi * RADIUS_M**4
TIP_TWIST_REFERENCE_RAD = TORQUE_NM * 3.0 / (
    (80.0e9 / (2.0 * (1.0 + 0.3))) * POLAR_MOMENT_M4
)


def test_j24b_tet10_static_torsion_four_meshes() -> None:
    """Run each frozen level once, checkpoint it, then apply frozen criteria."""
    _run_campaign(_load_contract(), _output_root())


def test_j24b_tet10_static_torsion_four_meshes_corrected_h1_digest() -> None:
    """Repeat the four-level campaign under the distinct corrected-input contract."""
    _run_campaign(
        _load_contract(CORRECTED_H1_CONTRACT_PATH, expected_nodeid=CORRECTED_H1_NODEID),
        _output_root(),
    )


def _output_root() -> Path:
    output_text = os.environ.get("QF_DEV_OUTPUT_DIR")
    if not output_text:
        raise RuntimeError("J24B FEM execution must use the registered launcher output directory")
    output_root = Path(output_text).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    return output_root


def _run_campaign(contract: dict[str, Any], output_root: Path) -> None:
    levels = contract["inputs"]["levels"]
    rows: list[dict[str, Any]] = []

    for level in LEVELS:
        level_dir = output_root / level
        level_dir.mkdir(exist_ok=False)
        level_started = time.perf_counter()
        process = psutil.Process()
        level_input = levels[level]
        mesh_path = ROOT / contract["inputs"]["mesh_directory"] / level_input["mesh"]
        setup_path = ROOT / contract["inputs"]["mesh_directory"] / level_input["setup"]
        initial = {
            "schema": "qf-j24b-tet10-torsion-checkpoint-v1",
            "contract_id": contract["contract_id"],
            "level": level,
            "state": "SOLVE_PENDING",
            "mesh_sha256": _sha256(mesh_path),
            "setup_sha256": _sha256(setup_path),
            "expected_mesh_sha256": level_input["mesh_sha256"],
            "started_at_unix_seconds": time.time(),
            "rss_at_start_bytes": process.memory_info().rss,
        }
        _atomic_json(level_dir / "checkpoint.json", initial)
        try:
            if initial["mesh_sha256"] != level_input["mesh_sha256"]:
                raise ValueError(f"{level}: frozen mesh digest mismatch")
            if initial["setup_sha256"] != contract["inputs"]["setup_sha256"]:
                raise ValueError(f"{level}: frozen setup digest mismatch")
            row = _solve_level(level, mesh_path, setup_path, level_dir, contract)
            row["resource_observations"].update(
                {
                    "level_elapsed_seconds": time.perf_counter() - level_started,
                    "rss_at_level_start_bytes": initial["rss_at_start_bytes"],
                    "rss_after_level_bytes": process.memory_info().rss,
                    "rss_measurement": "process RSS sampled at phase boundaries; runner records campaign peak separately",
                }
            )
            completed = {**row, "state": "RESULT_CHECKPOINTED"}
            rows.append(completed)
            _atomic_json(level_dir / "checkpoint.json", {**initial, **completed})
        except Exception as exc:
            failure = {
                **initial,
                "state": "LEVEL_FAILED_OR_INCOMPLETE",
                "exception_type": type(exc).__name__,
                "exception": str(exc),
                "resource_observations": {
                    "level_elapsed_seconds": time.perf_counter() - level_started,
                    "rss_at_level_start_bytes": initial["rss_at_start_bytes"],
                    "rss_after_level_bytes": process.memory_info().rss,
                },
                "finished_at_unix_seconds": time.time(),
            }
            _atomic_json(level_dir / "checkpoint.json", failure)
            rows.append({"level": level, "state": "LEVEL_FAILED_OR_INCOMPLETE", "exception": failure["exception"]})

    summary = _campaign_summary(rows, contract)
    _atomic_json(output_root / "campaign_summary.json", summary)
    assert summary["status"] != "INCONCLUSIVE", summary["reasons"]
    assert summary["status"] != "FAIL", summary["reasons"]


def _load_contract(
    contract_path: Path = CONTRACT_PATH,
    *,
    expected_nodeid: str = ORIGINAL_NODEID,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("status") != "FROZEN_BEFORE_SOLVE":
        raise ValueError("J24B contract is not frozen for execution")
    if tuple(contract["inputs"]["levels"]) != LEVELS:
        raise ValueError("J24B mesh levels differ from the frozen contract")
    if contract["execution_scope"]["exact_nodeid"] != expected_nodeid:
        raise ValueError("J24B contract is bound to a different exact execution nodeid")
    return contract


def _solve_level(
    level: str,
    mesh_path: Path,
    setup_path: Path,
    output_dir: Path,
    contract: dict[str, Any],
) -> dict[str, Any]:
    process = psutil.Process()
    phase_times: dict[str, float] = {}
    phase_rss: dict[str, int] = {"before_model_import_bytes": process.memory_info().rss}
    started = time.perf_counter()
    phase_started = time.perf_counter()
    model = GmshModelImporter().import_model(mesh_path, setup_path).model
    input_validation = _validate_model_input(model, contract)
    phase_times["model_import_and_input_validation_seconds"] = time.perf_counter() - phase_started
    phase_rss["after_model_import_and_input_validation_bytes"] = process.memory_info().rss
    phase_started = time.perf_counter()
    load_diagnostics = apply_consistent_circular_torsion(model, TORQUE_NM)
    applied_force, applied_moment = _reintegrate_loads(model)
    applied_force_ratio = float(np.linalg.norm(applied_force) / (TORQUE_NM / RADIUS_M))
    torque_error = abs(float(applied_moment[0]) - TORQUE_NM) / TORQUE_NM
    phase_times["terminal_load_build_and_independent_reintegration_seconds"] = time.perf_counter() - phase_started
    phase_rss["after_load_build_and_reintegration_bytes"] = process.memory_info().rss

    phase_started = time.perf_counter()
    result = enforce_qualification_policy(AnalysisRouter().solve(model), model)
    phase_times["assembly_solve_and_solver_audit_seconds"] = time.perf_counter() - phase_started
    phase_rss["after_assembly_solve_and_solver_audit_bytes"] = process.memory_info().rss
    if result.audit is None:
        raise RuntimeError("static solve returned no solver audit")
    equilibrium = result.audit.equilibrium
    phase_started = time.perf_counter()
    displacement = np.asarray(
        [
            [result.displacements[result.dofs.index(node, dof)] for dof in ("UX", "UY", "UZ")]
            for node in range(model.node_count)
        ],
        dtype=float,
    )
    _atomic_npz(
        output_dir / "displacements_xyz.npz",
        node_coordinates=np.asarray(model.nodes, dtype=float),
        displacements_xyz=displacement,
    )
    maximum_x = float(np.max(model.nodes[:, 0]))
    end_tolerance = 1.0e-10 * max(abs(maximum_x), 1.0)
    end_nodes = np.flatnonzero(np.abs(model.nodes[:, 0] - maximum_x) <= end_tolerance)
    if end_nodes.size == 0:
        raise ValueError("no mesh nodes lie on the controlled x=L measurement plane")
    end_coordinates = np.asarray(model.nodes[end_nodes], dtype=float)
    angle = _end_twist(end_coordinates, displacement[end_nodes])
    stress_rows, stress_relative_error = _integration_point_stresses(model, result)
    _atomic_csv(output_dir / "integration_point_stresses.csv", stress_rows)

    force_imbalance = np.asarray(equilibrium["force_imbalance"], dtype=float)
    moment_imbalance = np.asarray(equilibrium["moment_imbalance_about_origin"], dtype=float)
    reaction_force_closure = float(np.linalg.norm(force_imbalance) / (TORQUE_NM / RADIUS_M))
    reaction_moment_x_closure = float(abs(moment_imbalance[0]) / TORQUE_NM)
    free_relative_residual = float(equilibrium["free_relative_residual"])
    free_residual_norm = float(equilibrium["free_residual_norm"])
    fixed_dofs = {
        result.dofs.index(int(condition.node), dof)
        for condition in model.fixed_dofs
        for dof in condition.dofs
    }
    loaded_dofs = {result.dofs.index(int(load.node), load.dof) for load in model.loads}
    if loaded_dofs & fixed_dofs:
        raise ValueError("the declared terminal load includes a constrained degree of freedom")
    if model.linear_constraints():
        raise ValueError("the J24B residual denominator check does not cover multipoint constraints")
    external_load_norm = float(equilibrium["external_load_norm"])
    # All declared loads are on free DOFs in this frozen model, so ||f_free||
    # is exactly the solver's full external-load norm here.
    free_residual_denominator = max(external_load_norm, 1.0)
    twist_error = abs(angle - TIP_TWIST_REFERENCE_RAD) / abs(TIP_TWIST_REFERENCE_RAD)
    criteria = contract["criteria_values"]
    checks = {
        "solver_returned_pass": result.status == "PASS",
        "load_torque_relative_error": torque_error <= criteria["load_torque_relative_error_max"],
        "load_force_resultant_over_T_over_R": applied_force_ratio <= criteria["load_force_resultant_over_T_over_R_max"],
        "free_relative_residual": free_relative_residual <= criteria["free_relative_residual_max"],
        "reaction_force_closure": reaction_force_closure <= criteria["reaction_force_closure_max"],
        "reaction_x_moment_closure": reaction_moment_x_closure <= criteria["reaction_x_moment_closure_max"],
    }
    if level == "h4":
        checks["h4_tip_twist_relative_error"] = twist_error <= criteria["h4_tip_twist_relative_error_max"]

    record = {
        "schema": "qf-j24b-tet10-torsion-result-v1",
        "contract_id": contract["contract_id"],
        "level": level,
        "mesh_sha256": _sha256(mesh_path),
        "setup_sha256": _sha256(setup_path),
        "mesh": {"node_count": model.node_count, "element_count": len(model.elements), "dof_count": result.ndof},
        "input_validation": input_validation,
        "load": {
            "requested_torque_Nm": TORQUE_NM,
            "reintegrated_force_N": applied_force.tolist(),
            "reintegrated_moment_about_origin_Nm": applied_moment.tolist(),
            "force_resultant_over_T_over_R": applied_force_ratio,
            "torque_relative_error": torque_error,
            "route_diagnostics": load_diagnostics,
        },
        "response": {
            "tip_twist_rad": angle,
            "saint_venant_tip_twist_rad": TIP_TWIST_REFERENCE_RAD,
            "tip_twist_relative_error": twist_error,
            "free_residual_norm_N": free_residual_norm,
            "free_residual_normalization_N": free_residual_denominator,
            "external_load_norm_N": external_load_norm,
            "free_relative_residual": free_relative_residual,
            "external_work_J": float(equilibrium["external_work_at_final_load"]),
            "secant_internal_energy_J": float(equilibrium["secant_internal_energy"]),
            "linear_energy_identity_relative_error": float(equilibrium["linear_energy_identity_relative_error"]),
            "reaction_force_closure_over_T_over_R": reaction_force_closure,
            "reaction_moment_x_closure_over_T": reaction_moment_x_closure,
            "reaction_resultant_N": equilibrium["reaction_resultant"],
            "reaction_moment_about_origin_Nm": equilibrium["reaction_moment_about_origin"],
            "support_reactions": equilibrium["reactions"],
            "integration_point_volume_weighted_stress_l2_relative_error": stress_relative_error,
        },
        "stress_method": "TET10 stiffness integration points at their actual physical coordinates; nodal extrapolation is not used for this comparison.",
        "integration_point_count": len(stress_rows),
        "solver": {
            "status": result.status,
            "run_verdict": result.run_verdict.value,
            "method": result.method,
            "solver": result.solver,
            "audit_diagnostic": result.audit.to_dict(detail="diagnostic"),
        },
        "checks": checks,
        "resource_observations": {
            "phase_times_seconds": phase_times,
            "phase_boundary_rss_bytes": phase_rss,
            "postprocessing_seconds": time.perf_counter() - phase_started,
            "level_elapsed_seconds": time.perf_counter() - started,
            "rss_at_level_end_bytes": process.memory_info().rss,
            "rss_measurement": "process RSS sampled at phase boundaries; runner records campaign peak separately",
        },
        "point_status": "POINT_CHECKS_PASS" if all(checks.values()) else "POINT_CHECKS_FAIL",
        "scope_limit": "One configuration and one mesh level; only the four-level aggregate can evaluate the refinement ratio. No general TET10 route qualification is implied.",
    }
    _atomic_json(output_dir / "result_checkpoint.json", record)
    return record


def _validate_model_input(model: Any, contract: dict[str, Any]) -> dict[str, Any]:
    geometry = contract["model"]["geometry"]
    material_contract = contract["model"]["material"]
    tolerance = 1.0e-10 * max(float(geometry["length_m"]), 1.0)
    x = np.asarray(model.nodes[:, 0], dtype=float)
    radial = np.hypot(model.nodes[:, 1], model.nodes[:, 2])
    if not np.isfinite(model.nodes).all():
        raise ValueError("mesh coordinates contain non-finite values")
    if abs(float(np.min(x))) > tolerance or abs(float(np.max(x)) - float(geometry["length_m"])) > tolerance:
        raise ValueError("mesh axial bounds differ from the frozen 0 <= x <= L geometry")
    if float(np.max(radial)) > float(geometry["radius_m"]) + tolerance:
        raise ValueError("mesh extends outside the frozen circular shaft radius")
    if not all(str(element.type).upper() == "TET10" for element in model.elements):
        raise ValueError("frozen J24B mesh contains a non-TET10 element")
    if any(element.material != "solid" for element in model.elements):
        raise ValueError("frozen J24B mesh contains an unexpected material assignment")
    if model.units != {"system": "SI"}:
        raise ValueError(f"unexpected unit system: {model.units}")
    if model.analysis.type != "linear_static" or model.analysis.method != "direct":
        raise ValueError("model analysis route differs from the frozen linear-static direct solve")
    if model.verification_profile != "engineering":
        raise ValueError("verification profile differs from the frozen engineering profile")
    material = model.materials.get("solid")
    if not isinstance(material, dict):
        raise ValueError("solid material is missing from imported model")
    for field, contract_field in (("E", "young_modulus_Pa"), ("nu", "poisson_ratio"), ("density", "density_kg_m3")):
        if not math.isclose(float(material.get(field, math.nan)), float(material_contract[contract_field]), rel_tol=0.0, abs_tol=0.0):
            raise ValueError(f"imported material {field} differs from the frozen contract")

    root_nodes = set(np.flatnonzero(np.abs(x) <= tolerance).tolist())
    expected_fixed = {(node, dof) for node in root_nodes for dof in ("UX", "UY", "UZ")}
    actual_fixed = {(int(condition.node), dof) for condition in model.fixed_dofs for dof in condition.dofs}
    if actual_fixed != expected_fixed:
        raise ValueError("fixed translations do not match exactly the x=0 cross-section")
    if model.loads or model.distributed_loads:
        raise ValueError("imported model must be unloaded before the frozen terminal torque is applied")
    if model.multipoint_constraints or model.rbe2 or model.rbe3:
        raise ValueError("J24B model does not support uncontracted multipoint constraints")
    return {
        "axial_bounds_m": [float(np.min(x)), float(np.max(x))],
        "maximum_mesh_radius_m": float(np.max(radial)),
        "element_families": sorted({str(element.type).upper() for element in model.elements}),
        "root_support_node_count": len(root_nodes),
        "fixed_translation_dof_count": len(actual_fixed),
        "material": {key: float(material[key]) for key in ("E", "nu", "density")},
        "units": model.units,
        "analysis": {"type": model.analysis.type, "method": model.analysis.method},
        "verification_profile": model.verification_profile,
    }


def _reintegrate_loads(model: Any) -> tuple[np.ndarray, np.ndarray]:
    force = np.zeros(3, dtype=float)
    moment = np.zeros(3, dtype=float)
    axis = {"UX": 0, "UY": 1, "UZ": 2}
    for load in model.loads:
        vector = np.zeros(3, dtype=float)
        vector[axis[load.dof]] = float(load.value)
        force += vector
        moment += np.cross(np.asarray(model.nodes[int(load.node)], dtype=float), vector)
    return force, moment


def _end_twist(coordinates: np.ndarray, displacement: np.ndarray) -> float:
    y = coordinates[:, 1]
    z = coordinates[:, 2]
    uy = displacement[:, 1]
    uz = displacement[:, 2]
    denominator = float(np.sum(y * y + z * z))
    if denominator <= 0.0:
        raise ValueError("end section has no radial spread for the twist fit")
    return float(np.sum(y * uz - z * uy) / denominator)


def _integration_point_stresses(model: Any, result: Any) -> tuple[list[dict[str, Any]], float]:
    rows: list[dict[str, Any]] = []
    numerator = 0.0
    denominator = 0.0
    for element in result.element_results:
        for point in element.get("integration_points", []):
            coordinates = np.asarray(point["coordinates"], dtype=float)
            stress = np.asarray(point["stress"], dtype=float)
            weight = float(point["weight"])
            expected_xy = -TORQUE_NM * coordinates[2] / POLAR_MOMENT_M4
            expected_xz = TORQUE_NM * coordinates[1] / POLAR_MOMENT_M4
            difference_squared = float((stress[3] - expected_xy) ** 2 + (stress[5] - expected_xz) ** 2)
            reference_squared = float(expected_xy**2 + expected_xz**2)
            numerator += weight * difference_squared
            denominator += weight * reference_squared
            rows.append(
                {
                    "element": int(element["element"]),
                    "point": int(point["index"]),
                    "x_m": float(coordinates[0]),
                    "y_m": float(coordinates[1]),
                    "z_m": float(coordinates[2]),
                    "physical_volume_weight_m3": weight,
                    "qf_Sxy_Pa": float(stress[3]),
                    "sv_Sxy_Pa": expected_xy,
                    "qf_Sxz_Pa": float(stress[5]),
                    "sv_Sxz_Pa": expected_xz,
                    "other_stress_components_Pa": json.dumps([float(value) for value in stress[[0, 1, 2, 4]]]),
                }
            )
    if not rows or denominator <= 0.0:
        raise ValueError("TET10 result did not provide usable integration-point shear stresses")
    return rows, math.sqrt(numerator / denominator)


def _campaign_summary(rows: list[dict[str, Any]], contract: dict[str, Any]) -> dict[str, Any]:
    failures = [row for row in rows if row.get("state") == "LEVEL_FAILED_OR_INCOMPLETE"]
    completed = [row for row in rows if row.get("state") == "RESULT_CHECKPOINTED"]
    reasons: list[str] = []
    if failures or len(completed) != len(LEVELS):
        reasons.append("one or more mesh levels have no complete result checkpoint")
        status = "INCONCLUSIVE"
    else:
        for row in completed:
            failed_checks = [name for name, passed in row["checks"].items() if not passed]
            if failed_checks:
                reasons.append(f"{row['level']} failed checks: {', '.join(failed_checks)}")
        h1 = next(row for row in completed if row["level"] == "h1")
        h4 = next(row for row in completed if row["level"] == "h4")
        ratio = float(h1["response"]["tip_twist_relative_error"]) / max(
            float(h4["response"]["tip_twist_relative_error"]), np.finfo(float).tiny
        )
        ratio_threshold = float(contract["criteria_values"]["h1_to_h4_tip_twist_error_reduction_ratio_min"])
        if ratio < ratio_threshold:
            reasons.append(f"h1-to-h4 tip-twist error reduction ratio is below frozen threshold {ratio_threshold:g}")
        if reasons:
            status = "FAIL"
        else:
            status = "PASS"
        for row in completed:
            row["campaign_indicators"] = {
                "h1_to_h4_tip_twist_error_reduction_ratio": ratio,
                "h1_to_h4_tip_twist_error_reduction_ratio_threshold": ratio_threshold,
            }
    return {
        "schema": "qf-j24b-tet10-torsion-campaign-summary-v1",
        "contract_id": contract["contract_id"],
        "status": status,
        "scope_limit": "Applies only to this small-strain isotropic linear-static circular-shaft TET10 model, material, load, support and four frozen meshes.",
        "reasons": reasons,
        "mesh_levels": rows,
    }


def _atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _atomic_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("refusing to write an empty integration-point stress table")
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as stream:
        np.savez_compressed(stream, **arrays)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
