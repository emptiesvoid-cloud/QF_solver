"""Prepare controlled WP12 TET4 refinement and element-family input models.

This tool generates meshes, model files and mesh/observable input audits only.
It deliberately contains no assembly or solver calls and never launches FEM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from solveur.core.model import FiniteElementModel  # noqa: E402
from solveur.io.model_writer import JsonModelWriter  # noqa: E402
from solveur.large.generator import generate_tet4_cantilever_block  # noqa: E402
from solveur.large.io import save_large_model  # noqa: E402
from solveur.mesh.quality_contract import assess_element  # noqa: E402

from tet4_mechanical_oracles import SurfaceMeasure, linear_static_observables, surface_measure_weights  # noqa: E402


LENGTH_M = 4.0
HEIGHT_M = 0.4
DEPTH_M = 0.4
TIP_X_M = LENGTH_M
TOTAL_LOAD_N = -1.0
YOUNG_MODULUS_PA = 70.0e9
POISSON_RATIO = 0.3
MAX_DOF = 50_000
BASE_CELLS = (5, 1, 1)
REFINEMENT_FACTORS = (1, 2, 4, 8)
FAMILY_COMPARISON_FACTOR = 4
DOF_NAMES = ("UX", "UY", "UZ")
TET10_EDGE_ORDER = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))


def controlled_levels(
    base_cells: tuple[int, int, int] = BASE_CELLS,
    factors: tuple[int, ...] = REFINEMENT_FACTORS,
) -> list[dict[str, int | float]]:
    """Return nested dimensions whose cell side ratio remains 2:1:1."""
    if min(base_cells) <= 0 or not factors:
        raise ValueError("base cell counts and refinement factors must be positive")
    if tuple(sorted(set(factors))) != factors or factors[0] <= 0:
        raise ValueError("refinement factors must be strictly increasing positive integers")
    result: list[dict[str, int | float]] = []
    for factor in factors:
        nx, ny, nz = (int(value * factor) for value in base_cells)
        nodes = (nx + 1) * (ny + 1) * (nz + 1)
        dofs = 3 * nodes
        if dofs > MAX_DOF:
            raise ValueError(f"refinement factor {factor} exceeds the {MAX_DOF} DOF preparation cap")
        result.append(
            {
                "factor": int(factor),
                "nx": nx,
                "ny": ny,
                "nz": nz,
                "elements": 6 * nx * ny * nz,
                "nodes": nodes,
                "dofs": dofs,
                "cell_aspect_ratio": 2.0,
            }
        )
    return result


def _node_id(i: int, j: int, k: int, ny: int, nz: int) -> int:
    return i * (ny + 1) * (nz + 1) + j * (nz + 1) + k


def _structured_hex8(nx: int, ny: int, nz: int) -> np.ndarray:
    connectivity = np.empty((nx * ny * nz, 8), dtype=np.int64)
    cursor = 0
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                # The generator's cube order is i-fast on the local face;
                # reorder it to Hex8Element.node_signs (counter-clockwise).
                cube = (
                    _node_id(i, j, k, ny, nz),
                    _node_id(i + 1, j, k, ny, nz),
                    _node_id(i, j + 1, k, ny, nz),
                    _node_id(i + 1, j + 1, k, ny, nz),
                    _node_id(i, j, k + 1, ny, nz),
                    _node_id(i + 1, j, k + 1, ny, nz),
                    _node_id(i, j + 1, k + 1, ny, nz),
                    _node_id(i + 1, j + 1, k + 1, ny, nz),
                )
                connectivity[cursor] = [cube[index] for index in (0, 1, 3, 2, 4, 5, 7, 6)]
                cursor += 1
    return connectivity


def _consistent_loads(
    nodes: np.ndarray,
    elements: Sequence[Sequence[int]],
    family: str,
    measure: SurfaceMeasure | None = None,
) -> tuple[list[dict[str, Any]], SurfaceMeasure]:
    face_measure = measure or surface_measure_weights(
        nodes, elements, family, axis=0, coordinate=TIP_X_M
    )
    nodal_forces = TOTAL_LOAD_N * face_measure.nodal_area_weights / face_measure.total_area
    loads = [
        {"node": int(node), "dof": "UZ", "value": float(value)}
        for node, value in enumerate(nodal_forces)
        if value != 0.0
    ]
    if not np.isclose(sum(item["value"] for item in loads), TOTAL_LOAD_N, rtol=1.0e-12, atol=1.0e-14):
        raise ArithmeticError(f"{family} consistent tip loads do not conserve the vertical resultant")
    return loads, face_measure


def _large_to_model(
    nodes: np.ndarray,
    elements: np.ndarray,
    materials: dict[str, dict[str, Any]],
    material_names: Sequence[str],
    material_ids: np.ndarray,
    fixed_nodes: np.ndarray,
    fixed_components: np.ndarray,
    loads: list[dict[str, Any]],
    family: str,
) -> FiniteElementModel:
    raw_elements = [
        {
            "type": family,
            "nodes": [int(node) for node in connectivity],
            "material": material_names[int(material_id)],
        }
        for connectivity, material_id in zip(elements, material_ids, strict=True)
    ]
    fixed_by_node: dict[int, set[str]] = {}
    for node, component in zip(fixed_nodes, fixed_components, strict=True):
        fixed_by_node.setdefault(int(node), set()).add(DOF_NAMES[int(component)])
    fixed_dofs = [
        {"node": node, "dofs": sorted(dofs)}
        for node, dofs in sorted(fixed_by_node.items())
    ]
    return FiniteElementModel.from_raw(
        nodes=np.asarray(nodes, dtype=float).tolist(),
        elements=raw_elements,
        materials=materials,
        fixed_dofs=fixed_dofs,
        loads=loads,
        analysis={"type": "linear_static", "method": "direct"},
        units={"system": "SI"},
        verification_profile="quick",
    )


def _build_tet10_model(large_model: Any) -> FiniteElementModel:
    nodes = np.asarray(large_model.nodes, dtype=float)
    edge_nodes: dict[tuple[int, int], int] = {}
    converted_nodes = nodes.tolist()
    connectivity: list[list[int]] = []
    for tet in np.asarray(large_model.tet4, dtype=np.int64):
        corners = [int(node) for node in tet]
        mids: list[int] = []
        for first_local, second_local in TET10_EDGE_ORDER:
            first, second = corners[first_local], corners[second_local]
            edge = (min(first, second), max(first, second))
            midpoint = edge_nodes.get(edge)
            if midpoint is None:
                midpoint = len(converted_nodes)
                converted_nodes.append(((nodes[edge[0]] + nodes[edge[1]]) * 0.5).tolist())
                edge_nodes[edge] = midpoint
            mids.append(midpoint)
        connectivity.append(corners + mids)

    fixed_by_node: dict[int, set[int]] = {}
    for node, component in zip(large_model.fixed_nodes, large_model.fixed_components, strict=True):
        fixed_by_node.setdefault(int(node), set()).add(int(component))
    fixed_nodes = list(int(node) for node in large_model.fixed_nodes)
    fixed_components = list(int(component) for component in large_model.fixed_components)
    for (first, second), midpoint in edge_nodes.items():
        common_components = fixed_by_node.get(first, set()) & fixed_by_node.get(second, set())
        for component in common_components:
            fixed_nodes.append(midpoint)
            fixed_components.append(component)

    all_nodes = np.asarray(converted_nodes, dtype=float)
    loads, _ = _consistent_loads(all_nodes, connectivity, "TET10")
    return _large_to_model(
        all_nodes,
        np.asarray(connectivity, dtype=np.int64),
        dict(large_model.materials),
        tuple(large_model.material_names),
        np.asarray(large_model.material_ids, dtype=np.int64),
        np.asarray(fixed_nodes, dtype=np.int64),
        np.asarray(fixed_components, dtype=np.int64),
        loads,
        "TET10",
    )


def _build_tet4_model(large_model: Any) -> FiniteElementModel:
    connectivity = np.asarray(large_model.tet4, dtype=np.int64)
    loads, _ = _consistent_loads(large_model.nodes, connectivity, "TET4")
    return _large_to_model(
        large_model.nodes,
        connectivity,
        dict(large_model.materials),
        tuple(large_model.material_names),
        np.asarray(large_model.material_ids, dtype=np.int64),
        np.asarray(large_model.fixed_nodes, dtype=np.int64),
        np.asarray(large_model.fixed_components, dtype=np.int64),
        loads,
        "TET4",
    )


def _build_hex8_model(large_model: Any, nx: int, ny: int, nz: int) -> FiniteElementModel:
    connectivity = _structured_hex8(nx, ny, nz)
    loads, _ = _consistent_loads(large_model.nodes, connectivity, "HEX8")
    material_names = tuple(large_model.material_names)
    material_index = {name: index for index, name in enumerate(material_names)}
    material_ids = np.full(connectivity.shape[0], material_index["steel"], dtype=np.int64)
    fixed_mask = np.isclose(large_model.nodes[:, 0], 0.0, atol=1.0e-12)
    fixed_nodes = np.repeat(np.flatnonzero(fixed_mask), 3)
    fixed_components = np.tile(np.arange(3, dtype=np.int64), int(np.count_nonzero(fixed_mask)))
    return _large_to_model(
        large_model.nodes,
        connectivity,
        dict(large_model.materials),
        material_names,
        material_ids,
        fixed_nodes,
        fixed_components,
        loads,
        "HEX8",
    )


def _measure_for_model(model: FiniteElementModel, family: str) -> SurfaceMeasure:
    connectivity = [element.nodes for element in model.elements]
    return surface_measure_weights(model.nodes, connectivity, family, axis=0, coordinate=TIP_X_M)


def _element_quality_summary(model: FiniteElementModel) -> dict[str, Any]:
    family = model.elements[0].type
    metric_names = (
        "signed_volume",
        "aspect_ratio",
        "distortion_metric",
        "min_jacobian_determinant",
        "max_jacobian_determinant",
        "jacobian_determinant_ratio",
        "edge_length_min",
        "edge_length_max",
    )
    values: dict[str, list[float]] = {name: [] for name in metric_names}
    classifications: dict[str, int] = {}
    fatal_count = 0
    warnings: dict[str, int] = {}
    for element_id, element in enumerate(model.elements):
        assessment = assess_element(element_id, family, model.nodes[list(element.nodes)])
        classifications[assessment.classification] = classifications.get(assessment.classification, 0) + 1
        fatal_count += bool(assessment.fatal_findings)
        for warning in assessment.warnings:
            warnings[warning] = warnings.get(warning, 0) + 1
        for name in metric_names:
            metric = assessment.metrics.get(name)
            if metric is not None and np.isfinite(float(metric)):
                values[name].append(float(metric))
    stats: dict[str, dict[str, float]] = {}
    for name, samples in values.items():
        if samples:
            stats[name] = {
                "min": float(np.min(samples)),
                "p05": float(np.quantile(samples, 0.05)),
                "median": float(np.median(samples)),
                "p95": float(np.quantile(samples, 0.95)),
                "max": float(np.max(samples)),
            }
    if family == "TET4" and "distortion_metric" in stats:
        stats["tet4_quality_6sqrt2V_over_rms_edge_cubed"] = {
            name: float(1.0 - stats["distortion_metric"][name])
            for name in ("min", "p05", "median", "p95", "max")
        }
    return {
        "contract": "solveur.mesh.quality_contract.assess_element",
        "family_metric_semantics": "Per-family geometric diagnostics; no universal cross-family threshold is applied.",
        "element_count": len(model.elements),
        "classification_counts": classifications,
        "fatal_element_count": int(fatal_count),
        "warning_counts": warnings,
        "metrics": stats,
    }


def _model_input_audit(model: FiniteElementModel, family: str) -> dict[str, Any]:
    loaded_measure = _measure_for_model(model, family)
    force = np.zeros(3 * model.node_count, dtype=float)
    for load in model.loads:
        component = DOF_NAMES.index(load.dof)
        force[3 * load.node + component] += load.value
    fixed_dofs = np.asarray(
        [3 * condition.node + DOF_NAMES.index(dof) for condition in model.fixed_dofs for dof in condition.dofs],
        dtype=np.int64,
    )
    # Zero displacement and identity stiffness make this an input-shape check
    # only. It does not assemble or solve the finite-element equations.
    observables = linear_static_observables(
        nodes=model.nodes,
        stiffness=np.eye(force.size),
        force_vector=force,
        displacement=np.zeros(force.size),
        fixed_dofs=fixed_dofs,
        load_axis=2,
        loaded_face_measure=loaded_measure,
    )
    expected_resultant = np.array([0.0, 0.0, TOTAL_LOAD_N])
    expected_moment = np.array([-0.2, 4.0, 0.0])
    if not np.allclose(observables["load_resultant_n"], expected_resultant, rtol=1.0e-12, atol=1.0e-13):
        raise ArithmeticError(f"{family} tip-load resultant differs from the common mechanical input")
    if not np.allclose(observables["applied_moment_about_origin_nm"], expected_moment, rtol=1.0e-12, atol=1.0e-13):
        raise ArithmeticError(f"{family} tip-load moment differs from the common mechanical input")
    return {
        "load_resultant_n": observables["load_resultant_n"],
        "applied_moment_about_origin_nm": observables["applied_moment_about_origin_nm"],
        "loaded_face_area_m2": loaded_measure.total_area,
        "loaded_face_element_count": loaded_measure.face_count,
        "fixed_dof_count": int(fixed_dofs.size),
        "free_dof_count": int(force.size - fixed_dofs.size),
        "total_load_entries": len(model.loads),
        "analysis": {"type": model.analysis.type, "method": model.analysis.method},
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_commit(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _save_model(model: FiniteElementModel, path: Path) -> None:
    JsonModelWriter().write(model, path)


def prepare(output_dir: Path) -> dict[str, Any]:
    """Write the controlled sequence and like-geometry family models."""
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing preparation/evidence directory: {output}")
    output.mkdir(parents=True, exist_ok=False)
    script_path = Path(__file__).resolve()
    oracle_path = script_path.with_name("tet4_mechanical_oracles.py")
    source = {
        "git_commit": _source_commit(REPOSITORY_ROOT),
        "preparation_script_sha256": _file_sha256(script_path),
        "mechanical_oracles_sha256": _file_sha256(oracle_path),
    }
    levels = controlled_levels()
    previous_nodes: np.ndarray | None = None
    t4_quality_by_level: list[float] = []
    sequence_rows: list[dict[str, Any]] = []
    factor4_model: Any | None = None
    factor4_path: Path | None = None

    for level in levels:
        factor = int(level["factor"])
        level_dir = output / f"tet4_factor_{factor}"
        model_path = level_dir / "model.npz"
        level_dir.mkdir(parents=False, exist_ok=False)
        large = generate_tet4_cantilever_block(
            model_path,
            nx=int(level["nx"]),
            ny=int(level["ny"]),
            nz=int(level["nz"]),
            length=LENGTH_M,
            height=HEIGHT_M,
            depth=DEPTH_M,
            young=YOUNG_MODULUS_PA,
            poisson=POISSON_RATIO,
            total_load=TOTAL_LOAD_N,
            decomposition="six",
            load_distribution="surface_consistent",
        )
        connectivity = np.asarray(large.tet4, dtype=np.int64)
        tet_coordinates = np.asarray(large.nodes[connectivity], dtype=float)
        signed_volumes = np.einsum(
            "ij,ij->i",
            np.cross(tet_coordinates[:, 1] - tet_coordinates[:, 0], tet_coordinates[:, 2] - tet_coordinates[:, 0]),
            tet_coordinates[:, 3] - tet_coordinates[:, 0],
        ) / 6.0
        total_signed_volume = float(np.sum(signed_volumes))
        if not np.isclose(total_signed_volume, LENGTH_M * HEIGHT_M * DEPTH_M, rtol=1.0e-12, atol=1.0e-14):
            raise ArithmeticError(f"factor {factor} TET4 mesh does not fill the declared beam volume")
        measure = surface_measure_weights(large.nodes, connectivity, "TET4", axis=0, coordinate=TIP_X_M)
        loads, _ = _consistent_loads(large.nodes, connectivity, "TET4", measure)
        large.load_nodes = np.asarray([item["node"] for item in loads], dtype=np.int64)
        large.load_components = np.full(len(loads), 2, dtype=np.int8)
        large.load_values = np.asarray([item["value"] for item in loads], dtype=float)
        large.analysis["large_model"]["load_distribution"] = "tet4_triangle_consistent_uniform_traction"
        large.analysis["large_model"]["load_area_m2"] = measure.total_area
        large.analysis["large_model"]["total_load_n"] = TOTAL_LOAD_N
        save_large_model(large, model_path)

        corner_nodes = np.asarray(large.nodes, dtype=float)
        if previous_nodes is not None:
            lookup = {tuple(np.round(point, 12)) for point in corner_nodes}
            if any(tuple(np.round(point, 12)) not in lookup for point in previous_nodes):
                raise ArithmeticError(f"factor {factor} does not contain all nodes from the previous level")
        previous_nodes = corner_nodes

        finite_model = _build_tet4_model(large)
        geometry = _element_quality_summary(finite_model)
        if geometry["fatal_element_count"]:
            raise ArithmeticError(f"factor {factor} contains invalid TET4 geometry")
        quality = geometry["metrics"]["tet4_quality_6sqrt2V_over_rms_edge_cubed"]
        t4_quality_by_level.append(float(quality["median"]))
        input_audit = _model_input_audit(finite_model, "TET4")
        if int(level["dofs"]) != 3 * finite_model.node_count:
            raise ArithmeticError(f"factor {factor} DOF estimate does not match generated TET4 nodes")
        sequence_rows.append(
            {
                **level,
                "cell_dimensions_m": [LENGTH_M / int(level["nx"]), HEIGHT_M / int(level["ny"]), DEPTH_M / int(level["nz"])],
                "signed_volume_m3": total_signed_volume,
                "mesh_quality": geometry,
                "mechanical_input_audit": input_audit,
                "mesh_file": str(model_path.relative_to(output)),
                "mesh_file_sha256": _file_sha256(model_path),
            }
        )
        if factor == FAMILY_COMPARISON_FACTOR:
            factor4_model, factor4_path = large, model_path

    if not np.allclose(t4_quality_by_level, t4_quality_by_level[0], rtol=0.0, atol=1.0e-12):
        raise ArithmeticError("TET4 shape quality changed across the uniformly scaled nested sequence")
    if factor4_model is None or factor4_path is None:
        raise RuntimeError("the controlled sequence lacks the configured family-comparison factor")

    family_dir = output / "family_comparison_factor_4"
    family_dir.mkdir(parents=False, exist_ok=False)
    factor4_level = next(item for item in levels if int(item["factor"]) == FAMILY_COMPARISON_FACTOR)
    family_models = {
        "TET4": _build_tet4_model(factor4_model),
        "TET10": _build_tet10_model(factor4_model),
        "HEX8": _build_hex8_model(
            factor4_model,
            int(factor4_level["nx"]),
            int(factor4_level["ny"]),
            int(factor4_level["nz"]),
        ),
    }
    family_rows: list[dict[str, Any]] = []
    for family, model in family_models.items():
        if 3 * model.node_count > MAX_DOF:
            raise ValueError(f"{family} family comparison exceeds the {MAX_DOF} DOF input cap")
        model_path = family_dir / f"{family.lower()}_input.json"
        _save_model(model, model_path)
        family_rows.append(
            {
                "family": family,
                "nodes": model.node_count,
                "elements": len(model.elements),
                "dofs": 3 * model.node_count,
                "mesh_quality": _element_quality_summary(model),
                "mechanical_input_audit": _model_input_audit(model, family),
                "model_file": str(model_path.relative_to(output)),
                "model_file_sha256": _file_sha256(model_path),
            }
        )

    corner_coordinates = np.asarray(factor4_model.nodes, dtype=float)
    if any(
        family_models[family].nodes.shape[0] < corner_coordinates.shape[0]
        or not np.allclose(family_models[family].nodes[: corner_coordinates.shape[0]], corner_coordinates, rtol=0.0, atol=1.0e-12)
        for family in ("TET4", "TET10", "HEX8")
    ):
        raise ArithmeticError("family comparison does not preserve the common factor-4 corner-node geometry")

    summary: dict[str, Any] = {
        "study_id": "WP12-TET4-CONTROLLED-PREPARATION-001",
        "status": "PREPARED_NO_FEM_EXECUTED",
        "source": source,
        "execution": {"fem_execution_performed": False, "solver_calls": 0, "displacement_or_reaction_results": None},
        "common_model": {
            "geometry_m": {"length_x": LENGTH_M, "height_y": HEIGHT_M, "depth_z": DEPTH_M},
            "material": {"young_modulus_pa": YOUNG_MODULUS_PA, "poisson_ratio": POISSON_RATIO, "type": "isotropic_3d"},
            "boundary_conditions": "all three translations fixed at x=0",
            "tip_traction": {"direction": [0.0, 0.0, -1.0], "resultant_n": [0.0, 0.0, TOTAL_LOAD_N], "plane": "x=4 m", "integration": "element-family shape-function consistent"},
            "expected_applied_moment_about_origin_nm": [-0.2, 4.0, 0.0],
            "analytical_reference": {"type": "Timoshenko beam diagnostic only; not a 3D oracle"},
        },
        "mesh_sequence": {
            "base_cells": list(BASE_CELLS),
            "refinement_factors": list(REFINEMENT_FACTORS),
            "nested_nodes": True,
            "cell_side_ratio": "2:1:1 at every level",
            "max_dofs": MAX_DOF,
            "levels": sequence_rows,
        },
        "family_comparison": {
            "factor": FAMILY_COMPARISON_FACTOR,
            "same_corner_geometry_and_support": True,
            "integration": "TET4 linear triangles; TET10 quadratic triangles; HEX8 bilinear quadrilaterals",
            "family_quality_thresholds": "No universal cross-family cutoff; retain each family's geometric diagnostics separately.",
            "models": family_rows,
        },
        "observable_definitions": {
            "tip_displacement": "uniform-traction work-conjugate displacement F dot u / Fz; area-weighted mean also recorded after a solve",
            "reactions": "fixed entries of K u - f; report resultant and moment about the origin",
            "equilibrium": "applied plus reaction force/moment resultants",
            "energy": "U=0.5 u dot K u; W=u dot f; record 2U-W and residual-work identity",
            "residual": "free-DOF K u - f from the same supplied matrix; algebraic diagnostic, not an independent formulation oracle",
            "quality": "family-specific signed volume, edge aspect, Jacobian and distortion summaries with p05/median/p95",
        },
        "prepared_source_mesh_file": str(factor4_path.relative_to(output)),
    }
    summary_path = output / "preparation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    summary["summary_sha256"] = _file_sha256(summary_path)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_output = Path(__file__).resolve().parents[2].parent / "evidence" / "tet4" / "preparation" / "quality-sequence-v1"
    parser.add_argument("--output", type=Path, default=default_output, help="new output/evidence directory; must not exist")
    args = parser.parse_args()
    summary = prepare(args.output)
    print(json.dumps({"status": summary["status"], "output": str(args.output.resolve()), "levels": len(summary["mesh_sequence"]["levels"]), "family_models": len(summary["family_comparison"]["models"]), "fem_execution_performed": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
