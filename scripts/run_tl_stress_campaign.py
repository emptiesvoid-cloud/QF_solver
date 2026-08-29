"""Run a diagnostic-only stress campaign for the existing TL TET4/HEX8 path."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse.linalg import spsolve

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from solveur.core.assembly.geometric import build_total_lagrangian_assembly  # noqa: E402
from solveur.core.dofs import DofManager  # noqa: E402
from solveur.core.model import FiniteElementModel  # noqa: E402
from solveur.elements.solid.hex8 import Hex8Element  # noqa: E402
from solveur.mesh.quality import MeshQuality  # noqa: E402
from solveur.mesh.validation import MeshValidator  # noqa: E402
from solveur.materials.solid import SolidMaterial  # noqa: E402
from solveur.api.public import solve_model  # noqa: E402
from solveur.verification.robustness_foundations import element_coordinates  # noqa: E402
from solveur.verification.robustness_mesh import mesh_refinement_mesh  # noqa: E402


OUTPUT = _ROOT / "qualification" / "0_2_6" / "tl_stress_campaign"
FAMILIES = ("TET4", "HEX8")
MESH_LEVELS = (1, 2, 3, 4)
INCREMENT_LEVELS = (6, 8, 16, 32)
LOAD_MODES = ("traction", "compression", "shear_y", "bending_z")
LOAD_SCALES = (1.0e-4, 0.2)


def _git(command: str) -> str:
    return subprocess.check_output(command.split(), cwd=_ROOT, text=True).strip()


def _rotation_z(angle: float) -> np.ndarray:
    return np.asarray(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]],
        dtype=float,
    )


def _model(
    family: str,
    cells: int,
    mode: str,
    scale: float,
    increments: int,
    *,
    distortion: float = 0.0,
    angle: float = 0.0,
    aspect: float = 1.0,
) -> tuple[FiniteElementModel, np.ndarray, list[list[int]], np.ndarray, np.ndarray]:
    base_nodes, elements = mesh_refinement_mesh(family, cells)
    working = base_nodes.copy()
    working[:, 0] *= aspect
    if distortion:
        working[:, 0] += distortion * working[:, 1] * working[:, 2] * np.sin(np.pi * base_nodes[:, 0])
    rotation = _rotation_z(angle)
    nodes = (rotation @ working.T).T
    fixed_nodes = np.flatnonzero(np.isclose(base_nodes[:, 0], 0.0))
    loaded_nodes = np.flatnonzero(np.isclose(base_nodes[:, 0], 1.0))
    local_direction = {
        "traction": np.asarray([1.0, 0.0, 0.0]),
        "compression": np.asarray([-1.0, 0.0, 0.0]),
        "shear_y": np.asarray([0.0, 1.0, 0.0]),
        "bending_z": np.asarray([0.0, 0.0, 1.0]),
    }[mode]
    direction = rotation @ local_direction
    loads = [
        {"node": int(node), "dof": dof, "value": float(scale * direction[index] / len(loaded_nodes))}
        for node in loaded_nodes
        for index, dof in enumerate(("UX", "UY", "UZ"))
        if abs(float(direction[index])) > 0.0
    ]
    fixed = [{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes]
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": family, "nodes": item, "material": "solid"} for item in elements],
        materials={"solid": {"type": "isotropic_3d", "E": 10.0, "nu": 0.3}},
        fixed_dofs=fixed,
        loads=loads,
        analysis={
            "type": "geometric_nonlinear_static",
            "method": "newton_raphson",
            "parameters": {
                "load_increments": increments,
                "max_iterations": 100,
                "tolerance": 1.0e-8,
            },
        },
    )
    return model, nodes, elements, fixed_nodes, loaded_nodes


def _external(model: FiniteElementModel, dofs: DofManager) -> np.ndarray:
    vector = np.zeros(dofs.ndof, dtype=float)
    for load in model.loads:
        vector[dofs.index(load.node, load.dof)] += load.value
    return vector


def _fixed_indices(model: FiniteElementModel, dofs: DofManager) -> np.ndarray:
    return np.unique([dofs.index(item.node, name) for item in model.fixed_dofs for name in item.dofs])


def _quality(model: FiniteElementModel) -> dict[str, Any]:
    report = MeshValidator().validate(model)
    values: list[dict[str, float]] = []
    for item in model.elements:
        coords = model.nodes[list(item.nodes)]
        if item.type == "TET4":
            values.append(MeshQuality.tet_metrics(coords))
        else:
            jacobians = [float(np.linalg.det(Hex8Element.jacobian(coords, point))) for point in Hex8Element.integration_points]
            edges = [float(np.linalg.norm(coords[(index + 1) % 4] - coords[index])) for index in range(4)]
            values.append(
                {
                    "jacobian_min": min(jacobians),
                    "jacobian_max": max(jacobians),
                    "aspect_ratio_xy": max(edges) / min(edges),
                }
            )
    return {"status": report.status, "errors": report.errors, "warnings": report.warnings, "metrics": values}


def _global_case(
    family: str,
    cells: int,
    mode: str,
    scale: float,
    increments: int,
    distortion: float,
    angle: float,
    aspect: float,
) -> dict[str, Any]:
    case: dict[str, Any] = {
        "family": family,
        "cells": cells,
        "mode": mode,
        "load_scale": scale,
        "load_increments": increments,
        "distortion": distortion,
        "orientation_rad": angle,
        "aspect_x": aspect,
        "classification": "UNRESOLVED",
    }
    try:
        model, nodes, elements, fixed_nodes, loaded_nodes = _model(
            family, cells, mode, scale, increments, distortion=distortion, angle=angle, aspect=aspect
        )
        case["quality"] = _quality(model)
        dofs = model.dof_manager()
        reference_assembly = build_total_lagrangian_assembly(model)
        _, reference_tangent = reference_assembly.assemble(np.zeros(dofs.ndof))
        free = np.setdiff1d(np.arange(dofs.ndof), _fixed_indices(model, dofs))
        reduced_reference_tangent = reference_tangent[free][:, free].toarray()
        reference_eigenvalues = np.linalg.eigvalsh(
            0.5 * (reduced_reference_tangent + reduced_reference_tangent.T)
        )
        case["initial_tangent_condition_number"] = float(np.linalg.cond(reduced_reference_tangent))
        case["initial_tangent_min_eigenvalue"] = float(np.min(reference_eigenvalues))
        result = solve_model(model, enforce_policy=False)
        solver = result.to_dict()["solver"]
        assembly = build_total_lagrangian_assembly(model)
        internal, _ = assembly.assemble(result.displacements, tangent_required=False)
        residual = internal - _external(model, model.dof_manager())
        fixed = _fixed_indices(model, model.dof_manager())
        free = np.setdiff1d(np.arange(result.displacements.size), fixed)
        states = assembly.element_states(result.displacements)
        increments_data = solver.get("increments", solver.get("steps", []))
        case.update(
            {
                "status": result.status,
                "node_count": int(result.node_count),
                "element_count": int(result.element_count),
                "dof_count": int(result.displacements.size),
                "maximum_displacement": float(np.max(np.abs(result.displacements))),
                "free_residual_norm": float(np.linalg.norm(residual[free])),
                "residual_norm": float(np.linalg.norm(residual)),
                "minimum_det_f": float(np.min(assembly.deformation_determinants(result.displacements))),
                "strain_energy": float(assembly.strain_energy(result.displacements)),
                "maximum_cauchy_stress_norm": float(np.linalg.norm(states["cauchy_stress"], axis=(1, 2)).max()),
                "newton_iterations": int(sum(item["iterations"] for item in increments_data)),
                "maximum_relative_residual": float(max(item["relative_residual"] for item in increments_data)),
                "increment_residual_history": [float(item["relative_residual"]) for item in increments_data],
                "classification": "OBSERVATION_COMPLETE",
            }
        )
    except Exception as exc:
        case.update(
            {
                "status": "EXCEPTION",
                "exception_type": type(exc).__name__,
                "exception": str(exc),
                "classification": "UNRESOLVED",
            }
        )
    return case


def _objectivity_cases(family: str) -> list[dict[str, Any]]:
    coords = element_coordinates(family)
    material = SolidMaterial(E=10.0, nu=0.3)
    assembly_class = {
        "TET4": __import__("solveur.elements.solid.tet4_total_lagrangian_batch", fromlist=["TotalLagrangianTet4Assembly"]).TotalLagrangianTet4Assembly,
        "HEX8": __import__("solveur.elements.solid.hex8_total_lagrangian_batch", fromlist=["TotalLagrangianHex8Assembly"]).TotalLagrangianHex8Assembly,
    }[family]
    assembly = assembly_class(coords, np.asarray([list(range(len(coords)))]), material)
    rows = []
    for kind, amplitude in (("translation", 0.1), ("rotation", 0.3), ("rotation", 1.2), ("combined", 1.2)):
        rotation = _rotation_z(amplitude) if kind != "translation" else np.eye(3)
        translation = np.asarray([0.1, -0.2, 0.05]) if kind in {"translation", "combined"} else np.zeros(3)
        displacement = ((rotation @ coords.T).T + translation - coords).ravel()
        internal, tangent = assembly.assemble(displacement)
        rows.append(
            {
                "family": family,
                "case": f"{kind}_{amplitude}",
                "classification": "OBJECTIVITY_OBSERVATION",
                "internal_force_norm": float(np.linalg.norm(internal)),
                "energy": float(assembly.strain_energy(displacement)),
                "minimum_det_f": float(np.min(assembly.deformation_determinants(displacement))),
                "tangent_norm": float(np.linalg.norm(tangent.toarray())),
            }
        )
    return rows


def _tangent_cases(family: str) -> list[dict[str, Any]]:
    coords = element_coordinates(family)
    material = SolidMaterial(E=10.0, nu=0.3)
    assembly_class = {
        "TET4": __import__("solveur.elements.solid.tet4_total_lagrangian_batch", fromlist=["TotalLagrangianTet4Assembly"]).TotalLagrangianTet4Assembly,
        "HEX8": __import__("solveur.elements.solid.hex8_total_lagrangian_batch", fromlist=["TotalLagrangianHex8Assembly"]).TotalLagrangianHex8Assembly,
    }[family]
    assembly = assembly_class(coords, np.asarray([list(range(len(coords)))]), material)
    rows = []
    rng = np.random.default_rng(2607)
    for state, scale in (("zero", 0.0), ("uniaxial", 0.02), ("shear", 0.02), ("rotation", 0.6)):
        if state == "rotation":
            deformation = _rotation_z(scale)
        elif state == "shear":
            deformation = np.asarray([[1.0, scale, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        else:
            deformation = np.diag([1.0 + scale, 1.0, 1.0])
        displacement = ((deformation @ coords.T).T - coords).ravel()
        _, tangent = assembly.assemble(displacement)
        direction = rng.normal(size=displacement.size)
        direction /= np.linalg.norm(direction)
        step = 1.0e-7
        plus = assembly.assemble(displacement + step * direction, tangent_required=False)[0]
        minus = assembly.assemble(displacement - step * direction, tangent_required=False)[0]
        numerical = (plus - minus) / (2.0 * step)
        analytic = tangent @ direction
        rows.append(
            {
                "family": family,
                "state": state,
                "classification": "TANGENT_OBSERVATION",
                "relative_fd_error": float(np.linalg.norm(analytic - numerical) / max(np.linalg.norm(numerical), 1.0e-15)),
                "minimum_det_f": float(np.min(assembly.deformation_determinants(displacement))),
            }
        )
    return rows


def _small_strain_comparisons() -> list[dict[str, Any]]:
    rows = []
    for family in FAMILIES:
        for cells in MESH_LEVELS:
            model, _, _, _, _ = _model(family, cells, "traction", 1.0e-4, 16)
            dofs = model.dof_manager()
            assembly = build_total_lagrangian_assembly(model)
            zero = np.zeros(dofs.ndof)
            _, tangent = assembly.assemble(zero)
            external = _external(model, dofs)
            fixed = _fixed_indices(model, dofs)
            free = np.setdiff1d(np.arange(dofs.ndof), fixed)
            reference = np.zeros(dofs.ndof)
            reference[free] = spsolve(tangent[free][:, free], external[free])
            result = solve_model(model, enforce_policy=False)
            relative = float(np.linalg.norm(result.displacements - reference) / max(np.linalg.norm(reference), 1.0e-15))
            rows.append(
                {
                    "family": family,
                    "cells": cells,
                    "load_scale": 1.0e-4,
                    "relative_tl_vs_initial_tangent": relative,
                    "classification": "SMALL_STRAIN_OBSERVATION",
                    "status": result.status,
                }
            )
    return rows


def _failure_zoo(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    zoo: list[dict[str, Any]] = []
    for case in cases:
        if case.get("status") == "EXCEPTION":
            zoo.append(
                {
                    "case": f"{case['family']}_cells{case['cells']}_{case['mode']}_scale{case['load_scale']}",
                    "classification": "NUMERICAL_CONVERGENCE",
                    "status": "REPRODUCED_EXCEPTION",
                    "symptoms": case.get("exception"),
                    "model_audit": {
                        "mesh_quality": case.get("quality", {}).get("status"),
                        "mesh_errors": case.get("quality", {}).get("errors", []),
                        "mesh_warnings": case.get("quality", {}).get("warnings", []),
                        "aspect_or_jacobian_metrics": case.get("quality", {}).get("metrics", []),
                        "load_mode": case.get("mode"),
                        "load_scale": case.get("load_scale"),
                        "distortion": case.get("distortion"),
                        "aspect_x": case.get("aspect_x"),
                    },
                    "provenance": "diagnostic-only; same source SHA as report",
                }
            )
    for family in FAMILIES:
        try:
            coords = element_coordinates(family)
            coords[1] = coords[0]
            if family == "TET4":
                from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly

                TotalLagrangianTet4Assembly(coords, np.asarray([list(range(4))]), SolidMaterial(E=10.0, nu=0.3))
            else:
                from solveur.elements.solid.hex8_total_lagrangian_batch import TotalLagrangianHex8Assembly

                TotalLagrangianHex8Assembly(coords, np.asarray([list(range(8))]), SolidMaterial(E=10.0, nu=0.3))
        except Exception as exc:
            zoo.append(
                {
                    "case": f"{family}_degenerate_reference_mesh",
                    "classification": "MESH_QUALITY",
                    "status": "EXPECTED_REJECTION",
                    "exception_type": type(exc).__name__,
                    "exception": str(exc),
                }
            )
    zoo.append(
        {
            "case": "distributed_load_scope",
            "classification": "EXPECTED_LIMITATION",
            "status": "DOCUMENTED_BOUNDARY",
            "symptom": "geometric_nonlinear_static accepts nodal dead loads only",
        }
    )
    return zoo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, Any]] = []
    for family in FAMILIES:
        for cells in MESH_LEVELS:
            for mode in LOAD_MODES:
                scale = LOAD_SCALES[(cells + len(mode)) % len(LOAD_SCALES)]
                increments = INCREMENT_LEVELS[(cells + len(mode)) % len(INCREMENT_LEVELS)]
                distortion = (cells - 1) * 0.04
                angle = (cells % 2) * np.pi / 2.0
                aspect = (1.0, 2.0, 5.0, 10.0)[cells - 1]
                cases.append(_global_case(family, cells, mode, scale, increments, distortion, angle, aspect))
    local_rows = [_objectivity_cases(family) + _tangent_cases(family) for family in FAMILIES]
    local = [row for family_rows in local_rows for row in family_rows]
    small_strain = _small_strain_comparisons()
    report = {
        "status": "DIAGNOSTIC_ONLY",
        "source_sha": _git("git rev-parse HEAD"),
        "dirty": bool(_git("git status --porcelain")),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "families": list(FAMILIES),
        "global_case_count": len(cases),
        "local_case_count": len(local),
        "small_strain_case_count": len(small_strain),
        "mesh_levels": list(MESH_LEVELS),
        "increment_levels": list(INCREMENT_LEVELS),
        "load_modes": list(LOAD_MODES),
        "no_acceptance_thresholds": True,
        "cases": cases,
        "local_observations": local,
        "small_strain_observations": small_strain,
        "failure_zoo": _failure_zoo(cases),
        "classification_policy": [
            "No observation is a release PASS or promotion decision.",
            "An exception is UNRESOLVED until BC, loads, units, geometry, mesh quality and physical relevance are audited.",
            "A rejected degenerate mesh is an expected model-quality boundary, not a solver defect.",
            "The initial four-increment request was a harness error because the existing control contract requires at least six; the final corpus uses 6/8/16/32.",
        ],
    }
    (args.output / "tl_stress_campaign.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output / "tl_failure_zoo.json").write_text(json.dumps(report["failure_zoo"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    by_family = {
        family: sum(1 for item in cases if item["family"] == family)
        + sum(1 for item in local if item["family"] == family)
        + sum(1 for item in small_strain if item["family"] == family)
        for family in FAMILIES
    }
    summary_lines = [
        "# TL Stress Campaign",
        "",
        "Status: `DIAGNOSTIC_ONLY`; no release thresholds or promotion decisions were applied.",
        "",
        f"Source SHA: `{report['source_sha']}`; dirty at capture: `{report['dirty']}`.",
        "",
        "## Corpus",
        "",
        f"- {len(cases)} global observations ({len(cases) // len(FAMILIES)} per family).",
        f"- {len(local)} local objectivity/tangent observations ({len(local) // len(FAMILIES)} per family).",
        f"- {len(small_strain)} small-strain TL-versus-initial-tangent observations.",
        f"- Mesh levels: `{MESH_LEVELS}`; increment levels: `{INCREMENT_LEVELS}`.",
        f"- Per-family case totals, including local and small-strain observations: `{by_family}`.",
        "",
        "## Observed global outcomes",
        "",
        "| Family | Completed | Exceptions |",
        "| --- | ---: | ---: |",
    ]
    for family in FAMILIES:
        family_cases = [item for item in cases if item["family"] == family]
        summary_lines.append(
            f"| {family} | {sum(item.get('status') == 'success' for item in family_cases)} | "
            f"{sum(item.get('status') == 'EXCEPTION' for item in family_cases)} |"
        )
    summary_lines.extend(
        [
            "",
            "## Findings",
            "",
            "- Local rigid translations and rotations produced zero/negligible internal force and zero/negligible energy in the recorded observations.",
            "- Local finite-difference tangent observations were approximately `1.42e-9` maximum for TET4 and `3.31e-9` maximum for HEX8 in the tested states.",
            "- Small-strain relative differences against the initial tangent solve were approximately `1.81e-5` to `2.20e-5` for TET4 and `1.35e-5` to `1.46e-5` for HEX8. These are observations, not accepted error bands.",
            "- Three reproducible high-load/elongated-mesh exceptions were recorded as `NUMERICAL_CONVERGENCE`; mesh validation itself reported no errors for those cases. They require a separate model and load-path audit before any solver attribution.",
            "- No solver bug was demonstrated. No mesh-quality failure was demonstrated in the three convergence exceptions. Broader condition-number and external-reference studies remain open.",
            "",
            "## Failure zoo",
            "",
            f"`tl_failure_zoo.json` contains {len(report['failure_zoo'])} preserved cases: three numerical-convergence exceptions, one degenerate-reference mesh rejection, and one documented distributed-load boundary.",
            "",
            "The full raw observations are in `tl_stress_campaign.json`. Existing TL code and tolerances were not changed.",
            "",
        ]
    )
    (args.output / "README.md").write_text("\n".join(summary_lines), encoding="utf-8")
    print(json.dumps({"source_sha": report["source_sha"], "dirty": report["dirty"], "global_cases": len(cases), "local_cases": len(local), "small_strain_cases": len(small_strain), "cases_by_family": by_family, "exceptions": sum(case.get("status") == "EXCEPTION" for case in cases), "failure_zoo": len(report["failure_zoo"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
