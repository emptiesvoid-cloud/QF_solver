"""One-case-at-a-time WP12 TET4 convergence and family FEM targets.

The exact test functions below are registered individually by the shared
development controller. Each target solves exactly one prepared model.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from solveur.api import solve_model
from solveur.core.dofs import DofManager
from solveur.core.model import FiniteElementModel
from solveur.io.json_reader import JsonModelReader
from solveur.large.audit import inspect_large_model
from solveur.large.io import load_large_model
from solveur.mesh.quality_contract import assess_element
from solveur.verification.tet4_structured_convergence import timoshenko_tip_displacement

from scripts.wp12_dev.tet4_mechanical_oracles import surface_average, surface_measure_weights


PREPARATION_ROOT = Path(r"E:\QFSolverAgents\evidence\tet4\preparation\quality-sequence-v2")
PREPARATION_SUMMARY = PREPARATION_ROOT / "preparation_summary.json"
PREPARATION_SUMMARY_SHA256 = "00f776b3143388f8f8ff2012fb8d1c87206e521e575331bf39ae9ea4eaa3786d"
CASE_EVIDENCE_ROOT = Path(r"E:\QFSolverAgents\evidence\tet4\fem-cases-wp12-v1")
MAX_DOFS = 50_000
MAX_CASES_PER_ATTEMPT = 1
LENGTH_M = 4.0
WIDTH_M = 0.4
HEIGHT_M = 0.4
TIP_X_M = 4.0
DOF_NAMES = ("UX", "UY", "UZ")
TET10_EDGE_ORDER = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))

_TET4_MODEL_SHA256 = {
    1: "b234341a25e9f785ebfc3c4510ec8bfa10aa074e94746d65d3f4cd3703315067",
    2: "4fd79eb54a89afa9e32354be54360a2b8b4e4a1b832e5eb37c5d9daa82401234",
    4: "fb84d299612e0c9b021fa0c2b3fa651ae7dba1b5dc955620d42504cafe4d1e4b",
    8: "c080e5dad2ae32e50c6e0f573dbd3dff2dcdac3d572361c5a421b030615b9acd",
}
_FAMILY_MODEL_SHA256 = {
    "TET4": "a615822d953f3cbffb07e3f98150a20cb8c01c037781d78fb387c84bafc7ce00",
    "TET10": "c2f480111ea09e79129abf4e32ae04de8a606f71a7ce0d5bf85f0a6b39e7dedc",
    "HEX8": "ba58dcf0ba2aa9092518711008daad3a97964a91ba63952327969c7ae4888124",
}
_CASE_SPECS = {
    "tet4_factor_1": {"family": "TET4", "factor": 1, "cells": (5, 1, 1), "dofs": 72, "elements": 30},
    "tet4_factor_2": {"family": "TET4", "factor": 2, "cells": (10, 2, 2), "dofs": 297, "elements": 240},
    "tet4_factor_4": {
        "family": "TET4",
        "factor": 4,
        "cells": (20, 4, 4),
        "dofs": 1575,
        "elements": 1920,
        "roles": ["refinement", "family_comparison_TET4_baseline"],
    },
    "tet4_factor_8": {"family": "TET4", "factor": 8, "cells": (40, 8, 8), "dofs": 9963, "elements": 15360},
    "tet10_factor_4": {"family": "TET10", "factor": 4, "cells": (20, 4, 4), "dofs": 9963, "elements": 1920},
    "hex8_factor_4": {"family": "HEX8", "factor": 4, "cells": (20, 4, 4), "dofs": 1575, "elements": 320},
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_preparation_summary() -> dict[str, Any]:
    if _sha256(PREPARATION_SUMMARY) != PREPARATION_SUMMARY_SHA256:
        raise AssertionError("prepared WP12 mesh summary hash does not match the frozen input identity")
    return json.loads(PREPARATION_SUMMARY.read_text(encoding="utf-8"))


def _tet4_model_from_large(large: Any) -> FiniteElementModel:
    material_names = tuple(large.material_names)
    elements = [
        {
            "type": "TET4",
            "nodes": [int(node) for node in connectivity],
            "material": material_names[int(material_id)],
        }
        for connectivity, material_id in zip(large.tet4, large.material_ids, strict=True)
    ]
    fixed_by_node: dict[int, set[str]] = {}
    for node, component in zip(large.fixed_nodes, large.fixed_components, strict=True):
        fixed_by_node.setdefault(int(node), set()).add(DOF_NAMES[int(component)])
    fixed_dofs = [
        {"node": node, "dofs": sorted(components)}
        for node, components in sorted(fixed_by_node.items())
    ]
    loads = [
        {"node": int(node), "dof": DOF_NAMES[int(component)], "value": float(value)}
        for node, component, value in zip(
            large.load_nodes, large.load_components, large.load_values, strict=True
        )
    ]
    return FiniteElementModel.from_raw(
        nodes=np.asarray(large.nodes, dtype=float).tolist(),
        elements=elements,
        materials=dict(large.materials),
        fixed_dofs=fixed_dofs,
        loads=loads,
        analysis={"type": "linear_static", "method": "direct"},
        units=dict(large.units),
        verification_profile="quick",
    )


def _prepared_case(case_id: str) -> tuple[FiniteElementModel, dict[str, Any], Any | None, str, Path]:
    spec = _CASE_SPECS[case_id]
    summary = _read_preparation_summary()
    large = None
    if spec["family"] == "TET4":
        prepared_row = next(
            row for row in summary["mesh_sequence"]["levels"] if row["factor"] == spec["factor"]
        )
        model_path = PREPARATION_ROOT / prepared_row["mesh_file"]
        expected_hash = _TET4_MODEL_SHA256[int(spec["factor"])]
        large = load_large_model(model_path)
        model = _tet4_model_from_large(large)
        if int(spec["factor"]) == 4:
            comparison_row = next(
                row for row in summary["family_comparison"]["models"] if row["family"] == "TET4"
            )
            comparison_path = PREPARATION_ROOT / comparison_row["model_file"]
            if _sha256(comparison_path) != _FAMILY_MODEL_SHA256["TET4"]:
                raise AssertionError("prepared TET4 family comparison model hash changed")
            comparison_model = JsonModelReader().read(comparison_path)
            if not _same_tet4_model(model, comparison_model):
                raise AssertionError("factor-4 TET4 sequence model differs from the family-comparison baseline")
            prepared_quality = comparison_row["mesh_quality"]
        else:
            prepared_quality = prepared_row["mesh_quality"]
    else:
        prepared_row = next(
            row for row in summary["family_comparison"]["models"] if row["family"] == spec["family"]
        )
        model_path = PREPARATION_ROOT / prepared_row["model_file"]
        expected_hash = _FAMILY_MODEL_SHA256[str(spec["family"])]
        model = JsonModelReader().read(model_path)
        prepared_quality = prepared_row["mesh_quality"]
    if _sha256(model_path) != expected_hash:
        raise AssertionError(f"prepared {spec['family']} input hash does not match its frozen identity")
    if model.analysis.method != "direct":
        raise AssertionError("all comparison cases must use the same direct sparse solver route")
    if model.node_count * 3 != int(spec["dofs"]) or len(model.elements) != int(spec["elements"]):
        raise AssertionError(f"prepared {case_id} size differs from its registered DDL/element selection")
    if any(element.type != spec["family"] for element in model.elements):
        raise AssertionError(f"prepared {case_id} contains a different element family")
    return model, prepared_quality, large, expected_hash, model_path


def _same_tet4_model(first: FiniteElementModel, second: FiniteElementModel) -> bool:
    return bool(
        np.array_equal(first.nodes, second.nodes)
        and first.elements == second.elements
        and first.fixed_dofs == second.fixed_dofs
        and first.loads == second.loads
        and first.materials == second.materials
        and first.analysis.method == second.analysis.method == "direct"
    )


def _quality_with_mean(
    model: FiniteElementModel,
    prepared_quality: dict[str, Any],
    large: Any | None,
) -> dict[str, Any]:
    result = dict(prepared_quality)
    result["metrics"] = {key: dict(value) for key, value in prepared_quality["metrics"].items()}
    if large is not None:
        quality = inspect_large_model(large).details["tet4_quality"]
        result["metrics"]["tet4_quality_6sqrt2V_over_rms_edge_cubed"]["mean"] = float(
            quality["quality"]["mean"]
        )
        for name in ("aspect_ratio", "signed_volume"):
            result["metrics"].setdefault(name, {})["mean"] = float(quality[name]["mean"])
        result["invalid_element_count"] = int(quality["invalid_volume_count"])
        if result["invalid_element_count"]:
            raise AssertionError("prepared TET4 mesh contains invalid element geometry")
        return result

    family = model.elements[0].type
    measured: dict[str, list[float]] = {}
    fatal_count = 0
    warning_counts: dict[str, int] = {}
    for element_id, element in enumerate(model.elements):
        assessment = assess_element(element_id, family, model.nodes[list(element.nodes)])
        fatal_count += int(bool(assessment.fatal_findings))
        for warning in assessment.warnings:
            warning_counts[warning] = warning_counts.get(warning, 0) + 1
        for name, value in assessment.metrics.items():
            if value is not None and isinstance(value, (int, float, np.number)) and np.isfinite(float(value)):
                measured.setdefault(name, []).append(float(value))
    for name, samples in measured.items():
        result["metrics"].setdefault(name, {})["mean"] = float(np.mean(samples))
    result["fatal_element_count"] = fatal_count
    result["warning_counts"] = warning_counts
    if fatal_count:
        raise AssertionError(f"prepared {family} mesh has invalid element geometry")
    return result


def _selection_guard(model: FiniteElementModel, expected_dofs: int) -> None:
    selected = int(os.environ.get("QF_DEV_SELECTED_DOFS", "-1"))
    cap = int(os.environ.get("QF_DEV_MAX_DOFS", "-1"))
    cases = int(os.environ.get("QF_DEV_MAX_FEM_CASES", "-1"))
    worktree = os.environ.get("QF_DEV_WORKTREE_ID")
    if selected != expected_dofs or model.dof_manager().ndof != expected_dofs:
        raise AssertionError("registered selected DDL does not match this prepared model")
    if cap != MAX_DOFS or selected > cap:
        raise AssertionError("prepared model exceeds the registered WP12 TET4 DDL cap")
    if cases != MAX_CASES_PER_ATTEMPT or worktree != "wp12_tet4":
        raise AssertionError("this exact target must run as one case in the wp12_tet4 scope")


def _validate_common_model_contract(model: FiniteElementModel) -> dict[str, float]:
    if model.units.get("system") != "SI":
        raise AssertionError("prepared WP12 models must use SI units")
    if not np.allclose(model.nodes.min(axis=0), [0.0, 0.0, 0.0], rtol=0.0, atol=1.0e-12):
        raise AssertionError("prepared WP12 model minimum coordinates differ from the shared beam geometry")
    if not np.allclose(
        model.nodes.max(axis=0), [LENGTH_M, WIDTH_M, HEIGHT_M], rtol=0.0, atol=1.0e-12
    ):
        raise AssertionError("prepared WP12 model maximum coordinates differ from the shared beam geometry")
    if len(model.materials) != 1:
        raise AssertionError("prepared WP12 comparisons must use one common material")
    material = next(iter(model.materials.values()))
    if (
        material.get("type") != "isotropic_3d"
        or not np.isclose(float(material.get("E", np.nan)), 70.0e9, rtol=1.0e-12, atol=0.0)
        or not np.isclose(float(material.get("nu", np.nan)), 0.3, rtol=0.0, atol=1.0e-14)
    ):
        raise AssertionError("prepared WP12 model material differs from the common isotropic elastic material")

    root_nodes = set(np.flatnonzero(np.isclose(model.nodes[:, 0], 0.0, rtol=0.0, atol=1.0e-12)).tolist())
    fixed_by_node = {condition.node: set(condition.dofs) for condition in model.fixed_dofs}
    expected_fixed = {node: {"UX", "UY", "UZ"} for node in root_nodes}
    if fixed_by_node != expected_fixed:
        raise AssertionError("prepared WP12 support must fix all translations exactly on x=0")
    if model.distributed_loads or model.springs or model.multipoint_constraints or model.contacts:
        raise AssertionError("prepared WP12 comparisons must not include additional loads or constraint mechanisms")
    if any(load.dof != "UZ" or not np.isclose(model.nodes[load.node, 0], TIP_X_M, rtol=0.0, atol=1.0e-12) for load in model.loads):
        raise AssertionError("prepared WP12 load must be a vertical nodal representation on x=4 m")
    if not np.isclose(sum(load.value for load in model.loads), -1.0, rtol=1.0e-12, atol=1.0e-14):
        raise AssertionError("prepared WP12 nodal loads must sum to -1 N")
    return {"young_modulus_pa": float(material["E"]), "poisson_ratio": float(material["nu"])}


def _fixed_dof_indices(model: FiniteElementModel, dofs: DofManager) -> np.ndarray:
    return np.asarray(
        [dofs.index(condition.node, name) for condition in model.fixed_dofs for name in condition.dofs],
        dtype=np.int64,
    )


def _case_result(case_id: str) -> dict[str, Any]:
    spec = _CASE_SPECS[case_id]
    model, prepared_quality, large, input_sha256, model_path = _prepared_case(case_id)
    selected_dofs = int(spec["dofs"])
    _selection_guard(model, selected_dofs)
    material_properties = _validate_common_model_contract(model)
    quality = _quality_with_mean(model, prepared_quality, large)

    connectivity = [element.nodes for element in model.elements]
    face_measure = surface_measure_weights(model.nodes, connectivity, str(spec["family"]), axis=0, coordinate=TIP_X_M)
    if not np.isclose(face_measure.total_area, WIDTH_M * HEIGHT_M, rtol=1.0e-12, atol=1.0e-14):
        raise AssertionError("prepared loaded-face geometry does not retain the shared 0.4 m by 0.4 m section")
    dofs = model.dof_manager()
    force = np.zeros(dofs.ndof, dtype=float)
    for load in model.loads:
        force[dofs.index(load.node, load.dof)] += float(load.value)
    fixed = _fixed_dof_indices(model, dofs)
    free = np.setdiff1d(np.arange(dofs.ndof, dtype=np.int64), fixed, assume_unique=False)
    free_load_norm = float(np.linalg.norm(force[free]))
    total_fz = float(sum(force[dofs.index(node, "UZ")] for node in range(model.node_count)))
    if not np.isclose(total_fz, -1.0, rtol=1.0e-12, atol=1.0e-14):
        raise AssertionError("prepared model does not retain the -1 N vertical tip resultant")

    run_name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    case_directory = CASE_EVIDENCE_ROOT / case_id / run_name
    case_directory.mkdir(parents=True, exist_ok=False)
    rss_before = _rss_bytes()
    started = time.perf_counter()
    result = solve_model(model, enforce_policy=False)
    solve_seconds = float(time.perf_counter() - started)
    rss_after = _rss_bytes()
    if result.audit is None:
        raise AssertionError("linear-static result did not provide its mechanical audit")
    if result.status != "PASS":
        raise AssertionError(f"linear-static solve returned {result.status!r}, expected PASS")
    displacement = np.asarray(result.displacements, dtype=float)
    if displacement.shape != (dofs.ndof,) or not np.isfinite(displacement).all():
        raise AssertionError("linear-static solve returned an invalid displacement vector")
    if result.dofs.ndof != selected_dofs:
        raise AssertionError("solver DDL count differs from the registered selected DDL")

    nodal_displacement = np.zeros((model.node_count, 3), dtype=float)
    for node in range(model.node_count):
        for component, name in enumerate(DOF_NAMES):
            nodal_displacement[node, component] = displacement[dofs.index(node, name)]
    tip_nodes = np.flatnonzero(np.isclose(model.nodes[:, 0], TIP_X_M, rtol=0.0, atol=1.0e-12))
    mean_tip_uz = surface_average(nodal_displacement, face_measure, component=2)
    arithmetic_tip_uz = float(np.mean(nodal_displacement[tip_nodes, 2]))
    translation_norms = np.linalg.norm(nodal_displacement, axis=1)
    max_node = int(np.argmax(translation_norms))

    equilibrium = dict(result.audit.equilibrium)
    external_work = float(equilibrium["external_work_at_final_load"])
    strain_energy = float(equilibrium["secant_internal_energy"])
    work_conjugate = external_work / total_fz
    free_residual_norm = float(equilibrium["free_residual_norm"])
    relative_residual_free_load = (
        free_residual_norm / free_load_norm if free_load_norm > 0.0 else (0.0 if free_residual_norm == 0.0 else None)
    )
    energy_identity = float(2.0 * strain_energy - external_work)
    energy_identity_relative_work_scale = abs(energy_identity) / max(abs(external_work), np.finfo(float).tiny)
    expected_moment = np.asarray([-0.2, 4.0, 0.0])
    actual_load = np.asarray(equilibrium["external_resultant"], dtype=float)
    actual_moment = np.asarray(equilibrium["external_moment_about_origin"], dtype=float)
    if not np.allclose(actual_load, [0.0, 0.0, -1.0], rtol=1.0e-12, atol=1.0e-13):
        raise AssertionError("solver-side integrated force resultant differs from the prepared load oracle")
    if not np.allclose(actual_moment, expected_moment, rtol=1.0e-12, atol=1.0e-13):
        raise AssertionError("solver-side integrated load moment differs from the prepared load oracle")
    if not np.isclose(mean_tip_uz, work_conjugate, rtol=1.0e-9, atol=1.0e-15):
        raise AssertionError("consistent traction work-conjugate displacement differs from face average")

    beam_reference = timoshenko_tip_displacement(-1.0, 4.0, 0.4, 0.4, 70.0e9, 0.3)
    record: dict[str, Any] = {
        "schema": "qf-wp12-tet4-prepared-fem-case-v1",
        "case_id": case_id,
        "roles": list(spec.get("roles", ["refinement" if spec["family"] == "TET4" else "family_comparison"])),
        "status": str(result.status),
        "input": {
            "family": str(spec["family"]),
            "cells": list(spec["cells"]),
            "nodes": int(model.node_count),
            "elements": int(len(model.elements)),
            "total_dofs": int(dofs.ndof),
            "fixed_dofs": int(fixed.size),
            "free_dofs": int(free.size),
            "material": material_properties,
            "solver_method": str(result.method),
            "input_model_path": str(model_path),
            "input_model_sha256": input_sha256,
            "loaded_face_area_m2": float(face_measure.total_area),
            "loaded_face_element_count": int(face_measure.face_count),
        },
        "mesh_quality": quality,
        "solution": {
            "solve_seconds": solve_seconds,
            "mean_loaded_face_uz_area_weighted_m": float(mean_tip_uz),
            "mean_loaded_face_uz_arithmetic_nodes_m": arithmetic_tip_uz,
            "work_conjugate_displacement_m": float(work_conjugate),
            "max_nodal_translation_m": float(translation_norms[max_node]),
            "max_nodal_translation_node_id_zero_based": max_node,
            "max_nodal_translation_node_xyz_m": model.nodes[max_node].tolist(),
            "free_residual_norm_n": free_residual_norm,
            "free_residual_norm_over_free_load_norm": relative_residual_free_load,
            "free_residual_normalization": "||r_free||_2 / ||F_free||_2; zero-load case is explicitly represented as 0 or null",
            "solver_audit_relative_residual": float(equilibrium["free_relative_residual"]),
            "solver_audit_relative_residual_normalization": "||r_free||_2 / max(||F_free||_2, 1 N); SI-value floor inherited from SolverAudit",
            "reactions": equilibrium["reactions"],
            "reaction_resultant_n": equilibrium["reaction_resultant"],
            "reaction_moment_about_origin_nm": equilibrium["reaction_moment_about_origin"],
            "applied_resultant_n": equilibrium["external_resultant"],
            "applied_moment_about_origin_nm": equilibrium["external_moment_about_origin"],
            "force_imbalance_n": equilibrium["force_imbalance"],
            "moment_imbalance_nm": equilibrium["moment_imbalance_about_origin"],
            "force_balance_relative_error": float(equilibrium["force_balance_relative_error"]),
            "moment_balance_relative_error": float(equilibrium["moment_balance_relative_error"]),
            "strain_energy_j": strain_energy,
            "external_work_j": external_work,
            "twice_energy_minus_work_j": energy_identity,
            "energy_identity_relative_error_work_scale": float(energy_identity_relative_work_scale),
            "energy_identity_relative_error_normalization": "|2U-W| / |W|; separate from SolverAudit's 1 J denominator floor",
            "linear_energy_identity_relative_error": float(equilibrium["linear_energy_identity_relative_error"]),
            "solver_audit_energy_error_normalization": "|2U-W| / max(|W|, 1 J); the 1 J floor is inherited from SolverAudit",
            "timoshenko_beam_diagnostic_uz_m": float(beam_reference),
            "relative_difference_to_beam_diagnostic": float(abs(mean_tip_uz - beam_reference) / abs(beam_reference)),
            "solver_metadata": _scalar_mapping(result.solver),
            "mesh_validation": {
                "status": str(result.mesh_report.status),
                "errors": list(result.mesh_report.errors),
                "warnings": list(result.mesh_report.warnings),
            },
            "rss_before_bytes": rss_before,
            "rss_after_bytes": rss_after,
            "rss_positive_delta_bytes": None if rss_before is None or rss_after is None else max(0, rss_after - rss_before),
            "rss_measurement": "NOT_MEASURED" if rss_before is None or rss_after is None else "PROCESS_RSS_SAMPLES; controller also samples the process tree",
        },
        "limitations": [
            "Development observation only; not qualification evidence.",
            "The Timoshenko value is a diagnostic, not an independent 3D oracle.",
            "The residual is reported from the solver's assembled-system audit; the two normalizations are distinguished above.",
        ],
    }
    np.save(case_directory / "displacement.npy", displacement, allow_pickle=False)
    (case_directory / "mechanics.json").write_text(
        json.dumps(record, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print("WP12_TET4_FEM_RESULT=" + json.dumps(record, separators=(",", ":"), allow_nan=False))
    return record


def _rss_bytes() -> int | None:
    try:
        import psutil
    except ModuleNotFoundError:
        return None
    return int(psutil.Process().memory_info().rss)


def _scalar_mapping(values: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in values.items():
        if value is None or isinstance(value, (str, bool, int, float)):
            result[str(key)] = value
        elif isinstance(value, np.generic):
            result[str(key)] = value.item()
    return result


def test_wp12_tet4_refinement_factor_1() -> None:
    _case_result("tet4_factor_1")


def test_wp12_tet4_refinement_factor_2() -> None:
    _case_result("tet4_factor_2")


def test_wp12_tet4_refinement_factor_4() -> None:
    _case_result("tet4_factor_4")


def test_wp12_tet4_refinement_factor_8() -> None:
    _case_result("tet4_factor_8")


def test_wp12_tet10_family_comparison_factor_4() -> None:
    _case_result("tet10_factor_4")


def test_wp12_hex8_family_comparison_factor_4() -> None:
    _case_result("hex8_factor_4")
