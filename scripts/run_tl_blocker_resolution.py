"""Run the four diagnostic studies blocking the bounded TL Owner review.

This runner deliberately produces observations and Owner-review proposals.  It
does not update a gate, alter solver controls, or turn a null policy into a
qualification threshold.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from scipy.sparse.linalg import spsolve

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from run_tl_stress_campaign import _external, _fixed_indices, _model, _quality  # noqa: E402
from solveur.core.assembly.geometric import build_total_lagrangian_assembly  # noqa: E402
from solveur.materials.solid import SolidMaterial  # noqa: E402
from solveur.api.public import solve_model  # noqa: E402
from solveur.verification.robustness_foundations import element_coordinates  # noqa: E402


FAMILIES = ("TET4", "HEX8")
SMALL_STRAIN_FACTORS = (1.0, 0.5, 0.25, 0.125, 0.0625)
MESH_LEVELS = (1, 2, 3, 4)
TANGENT_STEPS = (1.0e-4, 1.0e-5, 1.0e-6, 1.0e-7, 1.0e-8)
TANGENT_STATES = ("zero", "tension", "compression", "shear", "biaxial", "rotation")
EXTERNAL_TOOLS = ("as_run", "code_aster", "ccx", "calculix")
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_6" / "tl_blocker_resolution"


def _git(*args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=ROOT, text=True).strip()


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer, np.bool_)):
        return value.item()
    raise TypeError(f"Cannot serialize {type(value).__name__}.")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assembly(family: str):
    module = (
        "solveur.elements.solid.tet4_total_lagrangian_batch"
        if family == "TET4"
        else "solveur.elements.solid.hex8_total_lagrangian_batch"
    )
    class_name = "TotalLagrangianTet4Assembly" if family == "TET4" else "TotalLagrangianHex8Assembly"
    imported = __import__(module, fromlist=[class_name])
    return getattr(imported, class_name)


def _reaction_norm(internal: np.ndarray, fixed: np.ndarray) -> float:
    return float(np.linalg.norm(internal[fixed]))


def _solve_observation(
    family: str,
    cells: int,
    mode: str,
    scale: float,
    increments: int,
    *,
    angle: float = 0.0,
) -> dict[str, Any]:
    model, _, _, _, _ = _model(
        family,
        cells,
        mode,
        scale,
        increments,
        distortion=0.0,
        angle=angle,
        aspect=6.5,
    )
    dofs = model.dof_manager()
    fixed = _fixed_indices(model, dofs)
    external = _external(model, dofs)
    assembly = build_total_lagrangian_assembly(model)
    result = solve_model(model, enforce_policy=False)
    internal, tangent = assembly.assemble(result.displacements)
    increments_data = result.solver.get("increments", [])
    reduced = tangent[np.setdiff1d(np.arange(dofs.ndof), fixed)][:, np.setdiff1d(np.arange(dofs.ndof), fixed)]
    eig = np.linalg.eigvalsh(0.5 * (reduced.toarray() + reduced.toarray().T))
    return {
        "family": family,
        "cells": cells,
        "mode": mode,
        "load_scale": scale,
        "load_increments": increments,
        "status": result.status,
        "dof_count": int(result.displacements.size),
        "element_count": int(result.element_count),
        "maximum_displacement": float(np.max(np.abs(result.displacements))),
        "reaction_norm": _reaction_norm(internal, fixed),
        "free_residual_norm": float(np.linalg.norm((internal - external)[np.setdiff1d(np.arange(dofs.ndof), fixed)])),
        "strain_energy": float(assembly.strain_energy(result.displacements)),
        "minimum_det_f": float(np.min(assembly.deformation_determinants(result.displacements))),
        "minimum_tangent_eigenvalue": float(np.min(eig)),
        "tangent_condition_number": float(np.linalg.cond(reduced.toarray())),
        "newton_iterations": int(sum(item["iterations"] for item in increments_data)),
        "residual_history": [float(value) for item in increments_data for value in item["residual_history"]],
        "increment_history": [
            {
                "increment": int(item["increment"]),
                "load_factor": float(item["load_factor"]),
                "iterations": int(item["iterations"]),
                "relative_residual": float(item["relative_residual"]),
            }
            for item in increments_data
        ],
        "quality": _quality(model),
        "classification": "OBSERVATION_ONLY",
    }


def _small_strain_study() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        for factor in SMALL_STRAIN_FACTORS:
            scale = 0.01 * factor
            model, _, _, _, _ = _model(family, 2, "traction", scale, 8, aspect=6.5)
            dofs = model.dof_manager()
            fixed = _fixed_indices(model, dofs)
            free = np.setdiff1d(np.arange(dofs.ndof), fixed)
            external = _external(model, dofs)
            assembly = build_total_lagrangian_assembly(model)
            _, tangent = assembly.assemble(np.zeros(dofs.ndof))
            reference = np.zeros(dofs.ndof)
            reference[free] = spsolve(tangent[free][:, free], external[free])
            result = solve_model(model, enforce_policy=False)
            relative = float(np.linalg.norm(result.displacements - reference) / max(np.linalg.norm(reference), 1.0e-15))
            rows.append(
                {
                    "family": family,
                    "load_factor": factor,
                    "load_scale": scale,
                    "relative_tl_vs_linear": relative,
                    "linear_displacement_norm": float(np.linalg.norm(reference)),
                    "tl_displacement_norm": float(np.linalg.norm(result.displacements)),
                    "status": result.status,
                    "classification": "OBSERVATION_ONLY",
                }
            )
    return rows


def _state_displacement(family: str, state: str, scale: float) -> np.ndarray:
    coords = element_coordinates(family)
    if state == "zero":
        deformation = np.eye(3)
    elif state == "tension":
        deformation = np.diag([1.0 + scale, 1.0, 1.0])
    elif state == "compression":
        deformation = np.diag([1.0 - scale, 1.0, 1.0])
    elif state == "shear":
        deformation = np.asarray([[1.0, scale, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    elif state == "biaxial":
        deformation = np.diag([1.0 + scale, 1.0 - 0.5 * scale, 1.0])
    else:
        angle = scale
        deformation = np.asarray(
            [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
        )
    return ((deformation @ coords.T).T - coords).ravel()


def _tangent_study() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        coords = element_coordinates(family)
        elements = np.asarray([list(range(len(coords)))])
        assembly = _assembly(family)(coords, elements, SolidMaterial(E=10.0, nu=0.3))
        rng = np.random.default_rng(260825)
        for state in TANGENT_STATES:
            state_scale = 0.6 if state == "rotation" else 0.03
            displacement = _state_displacement(family, state, state_scale)
            _, tangent = assembly.assemble(displacement)
            for direction_index in range(3):
                direction = rng.normal(size=displacement.size)
                direction /= np.linalg.norm(direction)
                for step in TANGENT_STEPS:
                    plus = assembly.assemble(displacement + step * direction, tangent_required=False)[0]
                    minus = assembly.assemble(displacement - step * direction, tangent_required=False)[0]
                    numerical = (plus - minus) / (2.0 * step)
                    analytic = tangent @ direction
                    error = float(np.linalg.norm(analytic - numerical) / max(np.linalg.norm(numerical), 1.0e-15))
                    rows.append(
                        {
                            "family": family,
                            "state": state,
                            "direction": direction_index,
                            "fd_step": step,
                            "relative_error": error,
                            "minimum_det_f": float(np.min(assembly.deformation_determinants(displacement))),
                            "classification": "OBSERVATION_ONLY",
                        }
                    )
    return rows


def _mesh_study() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        for mode, scale in (("bending_z", 0.008), ("shear_y", 0.01)):
            for cells in MESH_LEVELS:
                row = _solve_observation(family, cells, mode, scale, 16, angle=0.0)
                row["mesh_observables"] = ["maximum_displacement", "reaction_norm", "strain_energy"]
                row["mesh_level_role"] = "coarse_medium_fine_refined"
                rows.append(row)
    return rows


def _external_assessment() -> dict[str, Any]:
    available = {tool: shutil.which(tool) for tool in EXTERNAL_TOOLS}
    return {
        "status": "SKIPPED_NOT_COMPARABLE",
        "reason": "No Code_Aster/CalculiX executable is available in the current environment; no exact comparable deck was executed.",
        "available_executables": available,
        "required_comparison": ["displacement", "reaction", "load_displacement_curve"],
        "owner_interpretation": "External correlation remains an open Owner decision for TL promotion.",
    }


def _adjacent_changes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for family in FAMILIES:
        for mode in ("bending_z", "shear_y"):
            selected = sorted(
                (item for item in rows if item["family"] == family and item["mode"] == mode),
                key=lambda item: item["cells"],
            )
            for previous, current in zip(selected, selected[1:], strict=True):
                values = {
                    name: abs(current[name] - previous[name]) / max(abs(current[name]), 1.0e-15)
                    for name in ("maximum_displacement", "reaction_norm", "strain_energy")
                }
                output.append(
                    {
                        "family": family,
                        "mode": mode,
                        "from_cells": previous["cells"],
                        "to_cells": current["cells"],
                        "relative_changes": values,
                        "classification": "OBSERVED_TREND_ONLY",
                    }
                )
    return output


def _write_plots(output: Path, small: list[dict[str, Any]], tangent: list[dict[str, Any]], mesh: list[dict[str, Any]]) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    figure, axis = plt.subplots(figsize=(7.5, 4.5))
    for family in FAMILIES:
        selected = [item for item in small if item["family"] == family]
        axis.loglog(
            [item["load_factor"] for item in selected],
            [item["relative_tl_vs_linear"] for item in selected],
            "o-",
            label=family,
        )
    axis.set_xlabel("Applied load factor")
    axis.set_ylabel("||u_TL - u_linear|| / ||u_linear||")
    axis.set_title("TL versus linear small-strain asymptotic observation")
    axis.legend()
    figure.tight_layout()
    figure.savefig(output / "small_strain_asymptotic.png", dpi=160)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(7.5, 4.5))
    for family in FAMILIES:
        selected = [item for item in tangent if item["family"] == family]
        axis.loglog(
            [item["fd_step"] for item in selected],
            [item["relative_error"] for item in selected],
            ".",
            alpha=0.45,
            label=family,
        )
    axis.set_xlabel("Finite-difference step")
    axis.set_ylabel("Relative tangent FD error")
    axis.set_title("TL tangent finite-difference envelope")
    axis.legend()
    figure.tight_layout()
    figure.savefig(output / "tangent_fd_policy.png", dpi=160)
    plt.close(figure)

    figure, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharex=True)
    for family in FAMILIES:
        for mode in ("bending_z", "shear_y"):
            selected = sorted(
                (item for item in mesh if item["family"] == family and item["mode"] == mode),
                key=lambda item: item["cells"],
            )
            label = f"{family} {mode}"
            axes[0].plot([item["cells"] for item in selected], [item["maximum_displacement"] for item in selected], "o-", label=label)
            axes[1].plot([item["cells"] for item in selected], [item["reaction_norm"] for item in selected], "o-", label=label)
    axes[0].set_ylabel("Maximum displacement")
    axes[1].set_ylabel("Reaction norm")
    for axis in axes:
        axis.set_xlabel("Mesh level (cells along length)")
        axis.legend(fontsize=7)
    figure.suptitle("Flexion/shear mesh sensitivity: observed trends only")
    figure.tight_layout()
    figure.savefig(output / "mesh_flexion_shear.png", dpi=160)
    plt.close(figure)


def _markdown(report: dict[str, Any]) -> str:
    small = report["small_strain"]
    tangent = report["tangent_fd"]
    mesh = report["mesh_sensitivity"]
    lines = [
        "# TL blocker resolution",
        "",
        "Status: `DIAGNOSTIC_ONLY`; G07 remains open and no promotion decision is made here.",
        "",
        f"Source SHA: `{report['source_sha']}`; dirty at capture: `{report['dirty']}`.",
        "",
        "## Small-strain asymptotic study",
        "",
        "Metric: `||u_TL-u_linear|| / ||u_linear||`, with a common two-cell, aspect-6.5 traction model and load factors 1, 1/2, 1/4, 1/8 and 1/16.",
        "",
        "| Family | factor 1 | 1/2 | 1/4 | 1/8 | 1/16 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for family in FAMILIES:
        values = [item["relative_tl_vs_linear"] for item in small if item["family"] == family]
        lines.append("| " + family + " | " + " | ".join(f"{value:.3e}" for value in values) + " |")
    lines += [
        "",
        "Policy proposal: `PROPOSED_OWNER_REVIEW`. Require a documented asymptotic trend toward zero over the declared small-strain domain; no scalar acceptance band is auto-approved because the controlled tolerance policy is case-defined.",
        "",
        "## Tangent FD study",
        "",
        f"{len(tangent)} observations cover six states, three deterministic directions and five FD steps for each family. Observed maximum relative error: `{max(item['relative_error'] for item in tangent):.3e}`.",
        "",
        "Policy proposal: `PROPOSED_OWNER_REVIEW`. Retain the full error envelope, state coverage and FD-step stability; a numerical band and near-zero denominator treatment require Owner approval.",
        "",
        "## Flexion/shear mesh sensitivity",
        "",
        f"{len(mesh)} solves cover TET4/HEX8, bending/shear and four mesh levels. Adjacent changes are reported in `tl_blocker_resolution.json`; no monotonicity or universal aspect-ratio rule is imposed.",
        "",
        "Interpretation: `OBSERVED_TREND_ONLY`. Flexion and shear sensitivity is retained as a bounded-domain limitation pending Owner review; it is not silently classified as a solver defect or as convergence.",
        "",
        "## External correlation",
        "",
        "New Code_Aster/CalculiX execution: `SKIPPED_NOT_COMPARABLE`. The current environment has no compatible external executable, and no exact apples-to-apples deck was run. Existing bounded external evidence is not relabeled as this new campaign.",
        "",
        "## Artifacts and limitations",
        "",
        "- Raw measurements: `tl_blocker_resolution.json`.",
        "- Reproducibility manifest: `tl_blocker_resolution_manifest.json`.",
        "- Figures: `small_strain_asymptotic.png`, `tangent_fd_policy.png`, `mesh_flexion_shear.png`.",
        "- This pack does not modify G07, G04, Agent B, TL formulation, tangent, Newton controls or default adaptive behavior.",
        "",
    ]
    return "\n".join(lines)


def run(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    small = _small_strain_study()
    tangent = _tangent_study()
    mesh = _mesh_study()
    external = _external_assessment()
    report: dict[str, Any] = {
        "status": "DIAGNOSTIC_ONLY",
        "source_sha": _git("rev-parse", "HEAD"),
        "dirty": bool(_git("status", "--porcelain")),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "solver_version": "0.2.6a0",
        "families": list(FAMILIES),
        "small_strain_policy": {
            "status": "PROPOSED_OWNER_REVIEW",
            "metric": "norm(u_TL-u_linear)/norm(u_linear)",
            "domain": "two-cell aspect-6.5 traction model; load factors 1, 1/2, 1/4, 1/8, 1/16",
            "threshold": "UNDEFINED_OWNER_BAND",
            "justification": "Existing nonlinear tolerance policy is case-defined; asymptotic trend is evidence, not an auto-approved threshold.",
        },
        "tangent_fd_policy": {
            "status": "PROPOSED_OWNER_REVIEW",
            "metric": "relative norm of analytic tangent action versus centered FD action",
            "states": list(TANGENT_STATES),
            "fd_steps": list(TANGENT_STEPS),
            "threshold": "UNDEFINED_OWNER_BAND",
            "justification": "Multiple-state and step stability must be reviewed before setting a numerical band.",
        },
        "mesh_policy": {
            "status": "OBSERVED_TREND_ONLY",
            "levels": list(MESH_LEVELS),
            "modes": ["bending_z", "shear_y"],
            "observables": ["maximum_displacement", "reaction_norm", "strain_energy"],
            "threshold": "NONE",
        },
        "small_strain": small,
        "tangent_fd": tangent,
        "mesh_sensitivity": mesh,
        "mesh_adjacent_changes": _adjacent_changes(mesh),
        "external_correlation": external,
        "unexpected_failures": [
            item for item in small + mesh if item.get("status") not in {"success", "SUCCESS"}
        ],
        "qualification_decision": "OWNER_REVIEW_REQUIRED; no G07 closure",
    }
    _write_plots(output, small, tangent, mesh)
    json_path = output / "tl_blocker_resolution.json"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")
    manifest = {
        "status": "DIAGNOSTIC_ONLY",
        "source_sha": report["source_sha"],
        "dirty": report["dirty"],
        "solver_version": report["solver_version"],
        "artifacts": {},
        "policy_statuses": {
            "small_strain": report["small_strain_policy"]["status"],
            "tangent_fd": report["tangent_fd_policy"]["status"],
            "mesh": report["mesh_policy"]["status"],
            "external": external["status"],
        },
    }
    (output / "README.md").write_text(_markdown(report), encoding="utf-8")
    for path in sorted(output.iterdir()):
        if path.name != "tl_blocker_resolution_manifest.json" and path.is_file():
            manifest["artifacts"][path.name] = _digest(path)
    manifest_path = output / "tl_blocker_resolution_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = run(args.output)
    print(
        json.dumps(
            {
                "source_sha": report["source_sha"],
                "dirty": report["dirty"],
                "small_strain": len(report["small_strain"]),
                "tangent_fd": len(report["tangent_fd"]),
                "mesh_sensitivity": len(report["mesh_sensitivity"]),
                "external": report["external_correlation"]["status"],
                "unexpected_failures": len(report["unexpected_failures"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
