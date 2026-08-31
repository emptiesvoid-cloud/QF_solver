"""Run the two bounded G07-B2 TL external path correlations."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from run_tl_physical_branch_code_aster import run as run_hex8_external  # noqa: E402
from run_tl_stress_campaign import _external, _fixed_indices, _model  # noqa: E402
from solveur.core.assembly.geometric import build_total_lagrangian_assembly  # noqa: E402
from solveur.core.errors import InfrastructureError  # noqa: E402
from solveur.core.model import FiniteElementModel  # noqa: E402
from solveur.core.nonlinear.iteration import solve_full_newton  # noqa: E402
from solveur.io.manifest import write_json_file  # noqa: E402
from solveur.verification.code_aster_tl_structural import (  # noqa: E402
    CODE_ASTER_IMAGE,
    code_aster_mesh,
    run_code_aster,
)
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh  # noqa: E402


BASELINE_SHA = "1fd3cd41d1dd21e26d90851d89aa60d9429dabd9"
EVIDENCE_ID = "026-G07-B2-TL-EXTERNAL-001"
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_6" / "g07_b2_tl_external"

TET4_CASE = {
    "family": "TET4",
    "cells": [16, 4, 4],
    "length": 4.0,
    "height": 0.5,
    "depth": 0.5,
    "imperfection_ratio": 0.005,
    "critical_load": 1115.4714943181057,
    "endpoint_fraction_critical": 0.8,
    "increments": 16,
}

HEX8_CASE = {
    "id": "HEX8_m4_a10_compression_l0.2_d0.12",
    "family": "HEX8",
    "cells": 4,
    "mode": "compression",
    "load_scale": 0.2,
    "increments": 128,
    "distortion": 0.12,
    "angle": 0.0,
    "aspect": 10.0,
}


def _git(*args: str) -> str:
    import subprocess

    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite_array(value: object) -> bool:
    array = np.asarray(value, dtype=float)
    return bool(np.all(np.isfinite(array)))


class _RecordingAssembly:
    """Record force evaluations while delegating the production assembly unchanged."""

    def __init__(self, assembly: Any):
        self.assembly = assembly
        self.ndof = assembly.ndof
        self.records: list[dict[str, Any]] = []

    def assemble(
        self, displacement: np.ndarray, *, tangent_required: bool = True
    ) -> tuple[np.ndarray, object | None]:
        values = np.asarray(displacement, dtype=float).copy()
        internal, tangent = self.assembly.assemble(values, tangent_required=tangent_required)
        self.records.append(
            {
                "displacement": values,
                "internal": np.asarray(internal, dtype=float).copy(),
                "tangent_required": tangent_required,
            }
        )
        return internal, tangent


def _fixed_dofs_from_nodes(fixed_nodes: np.ndarray) -> np.ndarray:
    return (3 * np.asarray(fixed_nodes, dtype=int)[:, None] + np.arange(3)).reshape(-1)


def _support_reaction(
    residual: np.ndarray, fixed_nodes: np.ndarray
) -> list[float]:
    nodal = (-np.asarray(residual, dtype=float)).reshape(-1, 3)
    return np.sum(nodal[np.asarray(fixed_nodes, dtype=int)], axis=0).tolist()


def _accepted_states(
    recorder: _RecordingAssembly,
    external: np.ndarray,
    fixed: np.ndarray,
    increments: int,
    tolerance: float,
) -> list[np.ndarray]:
    free = np.setdiff1d(np.arange(external.size), fixed)
    states: list[np.ndarray] = []
    cursor = 0
    for step in range(1, increments + 1):
        target = (step / increments) * external
        scale = max(float(np.linalg.norm(target[free])), 1.0)
        selected: np.ndarray | None = None
        selected_index = cursor
        for index in range(cursor, len(recorder.records)):
            record = recorder.records[index]
            relative = float(np.linalg.norm((target - record["internal"])[free]) / scale)
            if relative <= tolerance:
                selected = np.asarray(record["displacement"], dtype=float).copy()
                selected_index = index
                break
        if selected is None:
            raise RuntimeError(f"Could not identify the committed QF state at increment {step}.")
        states.append(selected)
        cursor = selected_index + 1
    return states


def _path_checks(rows: list[dict[str, Any]], displacement_key: str) -> dict[str, Any]:
    if not rows:
        return {
            "finite": False,
            "load_monotone": False,
            "path_continuous": False,
            "row_count": 0,
        }
    factors = np.asarray([row["load_fraction"] for row in rows], dtype=float)
    displacements = np.asarray([row[displacement_key] for row in rows], dtype=float)
    finite = bool(np.all(np.isfinite(factors)) and np.all(np.isfinite(displacements)))
    return {
        "finite": finite,
        "load_monotone": bool(factors.size > 1 and np.all(np.diff(factors) > 0.0)),
        "path_continuous": bool(
            displacements.shape[0] > 1
            and np.all(np.linalg.norm(np.diff(displacements, axis=0), axis=1) > 1.0e-15)
        ),
        "row_count": len(rows),
        "load_fraction_range": [float(factors.min()), float(factors.max())],
    }


def _qf_path(
    model: FiniteElementModel,
    fixed_nodes: np.ndarray,
    loaded_nodes: np.ndarray,
    *,
    increments: int,
    load_fraction_scale: float,
    displacement_key: str,
) -> dict[str, Any]:
    dofs = model.dof_manager()
    fixed = _fixed_indices(model, dofs)
    external = _external(model, dofs)
    assembly = build_total_lagrangian_assembly(model)
    recorder = _RecordingAssembly(assembly)
    tolerance = 1.0e-8
    try:
        _, diagnostics = solve_full_newton(
            recorder,
            external,
            fixed,
            increments=increments,
            tolerance=tolerance,
            max_iterations=100,
        )
        states = _accepted_states(recorder, external, fixed, increments, tolerance)
    except Exception as exc:
        return {
            "status": "FAIL",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "increments": increments,
            "recorded_assembly_calls": len(recorder.records),
        }

    increment_diagnostics = list(diagnostics.get("increments", []))
    free = np.setdiff1d(np.arange(external.size), fixed)
    rows: list[dict[str, Any]] = []
    for index, (state, step_diagnostics) in enumerate(
        zip(states, increment_diagnostics, strict=True), start=1
    ):
        target = (index / increments) * external
        internal, _ = assembly.assemble(state, tangent_required=False)
        residual = target - internal
        free_residual = float(np.linalg.norm(residual[free]))
        reference = max(float(np.linalg.norm(target[free])), 1.0)
        det_f = np.asarray(assembly.deformation_determinants(state), dtype=float)
        loaded = np.asarray(loaded_nodes, dtype=int)
        nodal_displacement = state.reshape(-1, 3)
        loaded_mean = np.mean(nodal_displacement[loaded], axis=0)
        row: dict[str, Any] = {
            "step": index,
            "load_fraction": index / increments,
            "load_fraction_critical": load_fraction_scale * index / increments,
            "relative_residual": float(free_residual / reference),
            "iterations": int(step_diagnostics["iterations"]),
            "loaded_mean_displacement": loaded_mean.tolist(),
            "reaction_resultant_fixed": _support_reaction(residual, np.asarray(fixed_nodes, dtype=int)),
            "reaction_sign_convention": "negative_of_QF_external_minus_internal_residual_at_fixed_dofs",
            "det_f_min": float(det_f.min()),
            "det_f_max": float(det_f.max()),
        }
        row[displacement_key] = np.asarray(
            [row["loaded_mean_displacement"][0], row["loaded_mean_displacement"][2]], dtype=float
        ).tolist()
        rows.append(row)

    return {
        "status": "PASS",
        "increments": increments,
        "rows": rows,
        "maximum_relative_residual": max(row["relative_residual"] for row in rows),
        "minimum_det_f": min(row["det_f_min"] for row in rows),
        "path_checks": _path_checks(rows, displacement_key),
        "recorded_assembly_calls": len(recorder.records),
        "solver": "solve_full_newton / total_lagrangian assembly",
    }


def _tet4_model_and_geometry() -> tuple[FiniteElementModel, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    cells = tuple(int(value) for value in TET4_CASE["cells"])
    length = float(TET4_CASE["length"])
    height = float(TET4_CASE["height"])
    depth = float(TET4_CASE["depth"])
    nodes, elements = _structured_tet4_mesh(*cells, length, height, depth)
    amplitude = float(TET4_CASE["imperfection_ratio"]) * length
    nodes[:, 2] += amplitude * (1.0 - np.cos(0.5 * np.pi * nodes[:, 0] / length))
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], length))
    target_load = float(TET4_CASE["endpoint_fraction_critical"]) * float(TET4_CASE["critical_load"])
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "TET4", "nodes": row.tolist(), "material": "solid"} for row in elements],
        materials={"solid": {"type": "isotropic_3d", "E": 1.0e6, "nu": 0.3}},
        fixed_dofs=[
            {"node": int(node), "dofs": ["UX", "UY", "UZ"]}
            for node in fixed_nodes
        ],
        loads=[
            {"node": int(node), "dof": "UX", "value": -target_load / loaded_nodes.size}
            for node in loaded_nodes
        ],
        analysis={
            "type": "geometric_nonlinear_static",
            "method": "newton_raphson",
            "parameters": {
                "load_increments": int(TET4_CASE["increments"]),
                "max_iterations": 100,
                "tolerance": 1.0e-8,
            },
        },
    )
    return model, nodes, elements, fixed_nodes, loaded_nodes


def _tet4_external_command(tip_node_count: int, increments: int, target_load: float) -> str:
    nodal_force = -target_load / tip_node_count
    return f'''# coding=utf-8
import json
import numpy as np
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS=_F(E=1.0e6, NU=0.3))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
fixed = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="FIXED", DX=0.0, DY=0.0, DZ=0.0))
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="TIP", FX={nodal_force:.16g}))
ramp = DEFI_FONCTION(NOM_PARA="INST", VALE=(0.0, 0.0, 1.0, 1.0))
times = DEFI_LIST_REEL(DEBUT=0.0, INTERVALLE=_F(JUSQU_A=1.0, NOMBRE={increments}))
result = STAT_NON_LINE(
    MODELE=model, CHAM_MATER=field,
    EXCIT=(_F(CHARGE=fixed), _F(CHARGE=load, FONC_MULT=ramp)),
    COMPORTEMENT=_F(RELATION="ELAS", DEFORMATION="GREEN_LAGRANGE"),
    INCREMENT=_F(LIST_INST=times),
    CONVERGENCE=_F(RESI_GLOB_RELA=1.0e-9, ITER_GLOB_MAXI=80),
    NEWTON=_F(MATRICE="TANGENTE", REAC_ITER=1),
    SOLVEUR=_F(METHODE="MUMPS"),
)
CALC_CHAMP(reuse=result, RESULTAT=result, FORCE=("REAC_NODA",))
raw = {{"points": []}}
access = result.getAccessParameters()
for order, instant in zip(result.getIndexes(), access["INST"]):
    if float(instant) <= 0.0:
        continue
    displacement = result.getField("DEPL", order)
    dx, _ = displacement.getValuesWithDescription("DX", ["TIP"])
    dy, _ = displacement.getValuesWithDescription("DY", ["TIP"])
    dz, _ = displacement.getValuesWithDescription("DZ", ["TIP"])
    reaction = result.getField("REAC_NODA", order)
    rx, _ = reaction.getValuesWithDescription("DX", ["FIXED"])
    ry, _ = reaction.getValuesWithDescription("DY", ["FIXED"])
    rz, _ = reaction.getValuesWithDescription("DZ", ["FIXED"])
    raw["points"].append({{
        "load_fraction": float(instant),
        "load_fraction_critical": {float(TET4_CASE["endpoint_fraction_critical"]):.16g} * float(instant),
        "tip_axial_x": float(np.mean(dx)),
        "tip_increment_z": float(np.mean(dz)),
        "tip_mean_displacement": [float(np.mean(dx)), float(np.mean(dy)), float(np.mean(dz))],
        "reaction_resultant_fixed": [float(np.sum(rx)), float(np.sum(ry)), float(np.sum(rz))],
        "stress_status": "NOT_COMPARED_INCOMPATIBLE_COLUMN_FIELD",
    }})
with open("/work/code_aster_column_raw.json", "w", encoding="utf-8") as stream:
    json.dump(raw, stream, indent=2)
FIN()
'''


def _run_tet4_external(output: Path) -> dict[str, Any]:
    model, nodes, elements, fixed_nodes, loaded_nodes = _tet4_model_and_geometry()
    del model
    target_load = float(TET4_CASE["endpoint_fraction_critical"]) * float(TET4_CASE["critical_load"])
    work = output / "code_aster"
    work.mkdir(parents=True, exist_ok=True)
    mesh = work / "imperfect_column_full.mail"
    deck = work / "imperfect_column_full.comm"
    groups = {
        "FIXED": [int(node) + 1 for node in fixed_nodes],
        "TIP": [int(node) + 1 for node in loaded_nodes],
    }
    boundary = sorted(set(groups["FIXED"] + groups["TIP"]))
    mesh.write_text(code_aster_mesh(nodes, elements, boundary, groups=groups), encoding="ascii")
    deck.write_text(
        _tet4_external_command(loaded_nodes.size, int(TET4_CASE["increments"]), target_load),
        encoding="utf-8",
    )
    input_sha256 = {mesh.name: _file_sha256(mesh), deck.name: _file_sha256(deck)}
    try:
        run_code_aster(work, "imperfect_column_full", timeout=1800)
        raw = json.loads((work / "code_aster_column_raw.json").read_text(encoding="utf-8"))
    except InfrastructureError as exc:
        return {
            "status": "NOT_COMPARABLE",
            "classification": "EXTERNAL_TOOL_UNAVAILABLE",
            "external_solver": {"name": "Code_Aster", "image": CODE_ASTER_IMAGE},
            "error_type": type(exc).__name__,
            "error": str(exc),
            "raw_available": False,
            "input_sha256": input_sha256,
        }
    except Exception as exc:
        return {
            "status": "FAIL",
            "classification": "EXTERNAL_DECK_OR_SOLVER_FAILURE",
            "external_solver": {"name": "Code_Aster", "image": CODE_ASTER_IMAGE},
            "error_type": type(exc).__name__,
            "error": str(exc),
            "raw_available": False,
            "input_sha256": input_sha256,
        }
    points = raw.get("points", [])
    amplitude = float(TET4_CASE["imperfection_ratio"]) * float(TET4_CASE["length"])
    for point in points:
        point["tip_displacement_xz"] = [
            float(point["tip_axial_x"]),
            amplitude + float(point["tip_increment_z"]),
        ]
    return {
        "status": "PASS",
        "classification": "OBSERVED_EXTERNAL_PATH",
        "external_solver": {"name": "Code_Aster", "version": "18.1.0", "image": CODE_ASTER_IMAGE},
        "same_geometry": True,
        "same_mesh": True,
        "same_material": True,
        "same_nodal_loads": True,
        "increments": int(TET4_CASE["increments"]),
        "points": points,
        "point_count": len(points),
        "input_sha256": input_sha256,
        "raw_file_sha256": _file_sha256(work / "code_aster_column_raw.json"),
        "stress_comparison": "NOT_COMPARABLE_INCOMPATIBLE_COLUMN_INTEGRATION_MEASURES",
    }


def _compare_paths(
    qf: dict[str, Any],
    external: dict[str, Any],
    *,
    qf_displacement_key: str,
    external_displacement_key: str,
    load_key: str,
    qf_reaction_key: str = "reaction_resultant_fixed",
    external_reaction_key: str = "reaction_resultant_fixed",
) -> dict[str, Any]:
    if qf.get("status") != "PASS" or external.get("status") != "PASS":
        return {
            "result": "NOT_COMPARABLE"
            if external.get("status") == "NOT_COMPARABLE"
            else "FAIL",
            "reason": "Both full runtime paths are required for a comparison.",
        }
    qf_rows = list(qf.get("rows", []))
    external_rows = list(external.get("rows", external.get("points", [])))
    if len(qf_rows) != len(external_rows) or not qf_rows:
        return {
            "result": "FAIL",
            "reason": "QF and external paths do not contain the same number of points.",
            "qf_point_count": len(qf_rows),
            "external_point_count": len(external_rows),
        }
    qf_load = np.asarray([row[load_key] for row in qf_rows], dtype=float)
    external_load = np.asarray([row[load_key] for row in external_rows], dtype=float)
    qf_displacement = np.asarray([row[qf_displacement_key] for row in qf_rows], dtype=float)
    external_displacement = np.asarray(
        [row[external_displacement_key] for row in external_rows], dtype=float
    )
    qf_reaction = np.asarray([row[qf_reaction_key] for row in qf_rows], dtype=float)
    external_reaction = np.asarray([row[external_reaction_key] for row in external_rows], dtype=float)
    load_alignment = float(np.max(np.abs(qf_load - external_load)))
    displacement_difference = np.linalg.norm(qf_displacement - external_displacement, axis=1)
    displacement_reference = np.maximum(np.linalg.norm(external_displacement, axis=1), 1.0e-15)
    reaction_difference = np.linalg.norm(qf_reaction - external_reaction, axis=1)
    reaction_reference = np.maximum(np.linalg.norm(external_reaction, axis=1), 1.0e-15)
    finite = bool(
        _finite_array(qf_load)
        and _finite_array(external_load)
        and _finite_array(qf_displacement)
        and _finite_array(external_displacement)
        and _finite_array(qf_reaction)
        and _finite_array(external_reaction)
    )
    qf_path_checks = qf.get("path_checks", {})
    external_path_checks = _path_checks(external_rows, external_displacement_key)
    valid = bool(
        finite
        and load_alignment <= 1.0e-12
        and qf_path_checks.get("finite") is True
        and qf_path_checks.get("load_monotone") is True
        and qf_path_checks.get("path_continuous") is True
        and external_path_checks.get("finite") is True
        and external_path_checks.get("load_monotone") is True
        and external_path_checks.get("path_continuous") is True
    )
    return {
        "result": "PASS_WITH_LIMITATIONS" if valid else "FAIL",
        "point_count": len(qf_rows),
        "load_alignment_max_abs": load_alignment,
        "displacement_max_relative_difference": float(np.max(displacement_difference / displacement_reference)),
        "displacement_max_absolute_difference": float(np.max(displacement_difference)),
        "reaction_max_relative_difference": float(np.max(reaction_difference / reaction_reference)),
        "reaction_max_absolute_difference": float(np.max(reaction_difference)),
        "qf_max_relative_residual": float(max(row["relative_residual"] for row in qf_rows)),
        "qf_min_det_f": float(min(row["det_f_min"] for row in qf_rows)),
        "qf_path_checks": qf_path_checks,
        "external_path_checks": external_path_checks,
        "finite_fields": finite,
        "reaction_comparison_convention": "QF physical support reaction (-residual at fixed DOFs) versus Code_Aster REAC_NODA",
        "decision_basis": "Full finite path and path-consistency checks are required; differences are reported without introducing a new universal tolerance.",
    }


def _run(output: Path) -> dict[str, Any]:
    source_sha = _git("rev-parse", "HEAD")
    dirty = _git("status", "--porcelain", "--untracked-files=all")
    if dirty:
        raise RuntimeError("G07-B2 evidence must start from a clean source tree.")
    output.mkdir(parents=True, exist_ok=True)

    tet4_model, tet4_nodes, tet4_elements, tet4_fixed_nodes, tet4_loaded_nodes = _tet4_model_and_geometry()
    tet4_external = _run_tet4_external(output / "tet4_external")
    tet4_qf = _qf_path(
        tet4_model,
        tet4_fixed_nodes,
        tet4_loaded_nodes,
        increments=int(TET4_CASE["increments"]),
        load_fraction_scale=float(TET4_CASE["endpoint_fraction_critical"]),
        displacement_key="tip_displacement_xz",
    )
    if tet4_qf.get("status") == "PASS":
        for row in tet4_qf["rows"]:
            row["tip_displacement_xz"] = [
                row["loaded_mean_displacement"][0],
                float(
                    np.mean(tet4_nodes[tet4_loaded_nodes, 2])
                    + row["loaded_mean_displacement"][2]
                ),
            ]
        tet4_qf["path_checks"] = _path_checks(tet4_qf["rows"], "tip_displacement_xz")
    tet4_comparison = _compare_paths(
        tet4_qf,
        tet4_external,
        qf_displacement_key="tip_displacement_xz",
        external_displacement_key="tip_displacement_xz",
        load_key="load_fraction_critical",
    )

    hex8_model, _, _, hex8_fixed_nodes, hex8_loaded_nodes = _model(
        HEX8_CASE["family"],
        HEX8_CASE["cells"],
        HEX8_CASE["mode"],
        HEX8_CASE["load_scale"],
        HEX8_CASE["increments"],
        distortion=HEX8_CASE["distortion"],
        angle=HEX8_CASE["angle"],
        aspect=HEX8_CASE["aspect"],
    )
    hex8_external = run_hex8_external(output / "hex8_external")
    hex8_qf = _qf_path(
        hex8_model,
        hex8_fixed_nodes,
        hex8_loaded_nodes,
        increments=int(HEX8_CASE["increments"]),
        load_fraction_scale=1.0,
        displacement_key="loaded_mean_displacement_vector",
    )
    if hex8_qf.get("status") == "PASS":
        for row in hex8_qf["rows"]:
            row["loaded_mean_displacement_vector"] = row["loaded_mean_displacement"]
        hex8_qf["path_checks"] = _path_checks(hex8_qf["rows"], "loaded_mean_displacement_vector")
    hex8_comparison = _compare_paths(
        hex8_qf,
        hex8_external,
        qf_displacement_key="loaded_mean_displacement_vector",
        external_displacement_key="loaded_mean_displacement",
        load_key="load_factor",
    )

    tet4_complete = bool(
        tet4_external.get("status") == "PASS"
        and tet4_qf.get("status") == "PASS"
        and tet4_external.get("point_count") == int(TET4_CASE["increments"])
        and len(tet4_qf.get("rows", [])) == int(TET4_CASE["increments"])
    )
    hex8_complete = bool(
        hex8_external.get("status") == "OBSERVED_EXTERNAL_PATH"
        and hex8_qf.get("status") == "PASS"
        and len(hex8_external.get("raw", {}).get("rows", [])) == int(HEX8_CASE["increments"])
        and len(hex8_qf.get("rows", [])) == int(HEX8_CASE["increments"])
    )
    hex8_external_normalized = {
        **hex8_external,
        "status": "PASS" if hex8_external.get("status") == "OBSERVED_EXTERNAL_PATH" else hex8_external.get("status"),
        "rows": hex8_external.get("raw", {}).get("rows", []),
    }
    hex8_comparison = _compare_paths(
        hex8_qf,
        hex8_external_normalized,
        qf_displacement_key="loaded_mean_displacement_vector",
        external_displacement_key="loaded_mean_displacement",
        load_key="load_factor",
    )
    routes_pass = bool(
        tet4_complete
        and hex8_complete
        and tet4_comparison.get("result") == "PASS_WITH_LIMITATIONS"
        and hex8_comparison.get("result") == "PASS_WITH_LIMITATIONS"
    )
    payload: dict[str, Any] = {
        "schema_version": 1,
        "evidence_id": EVIDENCE_ID,
        "gate": "026-G07",
        "step": "B2_TL_EXTERNAL_COMPLETION",
        "status": "PASS" if routes_pass else "PARTIAL" if tet4_complete or hex8_complete else "FAIL",
        "baseline_start_sha": BASELINE_SHA,
        "execution_source_sha": source_sha,
        "execution_worktree_dirty": False,
        "functional_source_changed": False,
        "numerical_regression": False,
        "external_solver": {
            "name": "Code_Aster",
            "version": "18.1.0",
            "image": CODE_ASTER_IMAGE,
        },
        "scope_guard": {
            "tl_only": True,
            "arc_length_modified": False,
            "g08_modified": False,
            "new_physics": False,
            "formulation_changed": False,
            "new_thresholds": False,
        },
        "predeclared_comparison_policy": {
            "path_domain": "existing bounded TL domain only",
            "required_fields": ["displacement", "reaction", "QF residual", "path continuity", "QF det(F)"],
            "stress_strain": "compare only if integration measure and sampling are compatible; otherwise NOT_COMPARABLE",
            "decision": "PASS_WITH_LIMITATIONS records finite complete compatible paths and all metrics; no new universal error band is introduced",
            "reaction_sign": "QF physical support reaction is negative of QF external-minus-internal residual at fixed DOFs, compared with Code_Aster REAC_NODA",
        },
        "tl_tet4": {
            "case": TET4_CASE,
            "external_complete": tet4_complete,
            "result": tet4_comparison.get("result", "FAIL"),
            "external": tet4_external,
            "qf": tet4_qf,
            "comparison": tet4_comparison,
            "limitations": [
                "The complete path is bounded to 0.2 through 0.8 of the documented same-mesh critical-load estimate.",
                "Column stress/strain fields are not claimed comparable because QF and Code_Aster integration measures/sampling were not mapped one-to-one.",
                "The result is bounded external evidence, not a general TL or large-deformation qualification.",
            ],
        },
        "tl_hex8": {
            "case": HEX8_CASE,
            "external_complete": hex8_complete,
            "result": hex8_comparison.get("result", "FAIL"),
            "external": hex8_external_normalized,
            "qf": hex8_qf,
            "comparison": hex8_comparison,
            "limitations": [
                "The full path uses the existing 128-point bounded compression case only.",
                "Code_Aster stress, external det(F) and work fields are not transformed into directly comparable QF measures.",
                "The result is bounded branch evidence, not a general HEX8 TL qualification.",
            ],
        },
        "requirements": {
            "G07-TL-008": "PASS_WITH_LIMITATIONS" if routes_pass else "PARTIAL",
            "tl_tet4_complete_history": tet4_complete,
            "tl_hex8_complete_history": hex8_complete,
        },
        "claim": {
            "tl_tet4_owner_candidate": tet4_comparison.get("result", "FAIL"),
            "tl_hex8_owner_candidate": hex8_comparison.get("result", "FAIL"),
            "tl_blocking_gaps_remaining": [] if routes_pass else ["One or both complete path comparisons did not complete."],
            "g07_owner_closeout_ready": False,
            "g07_status_changed": False,
            "arc_length_b1_gap_unchanged": True,
        },
        "provenance": {
            "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "runner": "scripts/run_g07_b2_tl_external.py",
            "baseline_start_sha": BASELINE_SHA,
            "execution_source_sha": source_sha,
            "case_definition_sha256": {
                "TET4": _sha256(TET4_CASE),
                "HEX8": _sha256(HEX8_CASE),
            },
        },
    }
    write_json_file(output / "g07_b2_tl_external_evidence.json", payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    payload = _run(arguments.output.resolve())
    print(
        json.dumps(
            {
                "evidence_id": payload["evidence_id"],
                "status": payload["status"],
                "execution_source_sha": payload["execution_source_sha"],
                "tl_tet4": {
                    "complete": payload["tl_tet4"]["external_complete"],
                    "result": payload["tl_tet4"]["result"],
                },
                "tl_hex8": {
                    "complete": payload["tl_hex8"]["external_complete"],
                    "result": payload["tl_hex8"]["result"],
                },
                "output": str(arguments.output.resolve()),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
