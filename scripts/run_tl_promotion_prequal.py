"""Run an independent, diagnostic-only TL TET4/HEX8 prequalification campaign.

The campaign deliberately owns a new corpus and output directory.  It does not
change the solver policy, enable rescue controls, close G07, or update shared
qualification registries.
"""

from __future__ import annotations

import argparse
import hashlib
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
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

from run_tl_stress_campaign import (  # noqa: E402
    _external,
    _fixed_indices,
    _model,
    _quality,
)
from solveur.api.public import solve_model  # noqa: E402
from solveur.core.analyses.geometric_nonlinear import _newton_dead_load  # noqa: E402
from solveur.core.assembly.geometric import build_total_lagrangian_assembly  # noqa: E402
from solveur.core.errors import NumericalConvergenceError  # noqa: E402
from solveur.materials.solid import SolidMaterial  # noqa: E402
from solveur.verification.robustness_foundations import element_coordinates  # noqa: E402


OUTPUT = _ROOT / "qualification" / "0_2_6" / "tl_promotion_prequal"
FAMILIES = ("TET4", "HEX8")
MESH_LEVELS = (1, 2, 3, 4)
INCREMENT_LEVELS = (8, 16, 32, 64)
MODES = ("traction", "compression", "shear_y", "bending_z")

# These values intentionally differ from the historical stress/rescue grids.
PRIMARY_CASES = tuple(
    {
        "id": f"TL-PQ-{family}-M{cells}-A6.5-{mode}-D0.07-R0.261799",
        "family": family,
        "cells": cells,
        "mode": mode,
        "load_scale": 0.01 if mode == "bending_z" else 0.0125,
        "increments": 16,
        "distortion": 0.07,
        "angle": np.pi / 12.0,
        "aspect": 6.5,
        "group": "primary_mesh_mode",
    }
    for family in FAMILIES
    for cells in MESH_LEVELS
    for mode in MODES
)

INCREMENT_CASES = tuple(
    {
        "id": f"TL-PQ-{family}-INC{increments}-A6.5-{mode}-D0.07-R0.261799",
        "family": family,
        "cells": 2,
        "mode": mode,
        "load_scale": 0.0125 if mode != "bending_z" else 0.01,
        "increments": increments,
        "distortion": 0.07,
        "angle": np.pi / 12.0,
        "aspect": 6.5,
        "group": "increment_refinement",
    }
    for family in FAMILIES
    for mode in ("traction", "compression")
    for increments in INCREMENT_LEVELS
)

HOLDOUT_CASES = tuple(
    {
        "id": f"TL-PQ-HOLDOUT-{family}-A{aspect:g}-{mode}-D{distortion:g}-R{angle:g}",
        "family": family,
        "cells": cells,
        "mode": mode,
        "load_scale": scale,
        "increments": increments,
        "distortion": distortion,
        "angle": angle,
        "aspect": aspect,
        "group": "holdout",
    }
    for family, cells, mode, scale, increments, distortion, angle, aspect in (
        ("TET4", 1, "compression", 0.009, 8, 0.02, np.pi / 10.0, 4.25),
        ("TET4", 2, "shear_y", 0.011, 16, 0.08, np.pi / 5.0, 7.25),
        ("TET4", 3, "bending_z", 0.008, 32, 0.13, np.pi / 7.0, 9.25),
        ("TET4", 4, "traction", 0.014, 64, 0.05, np.pi / 9.0, 4.75),
        ("HEX8", 1, "compression", 0.009, 8, 0.02, np.pi / 10.0, 4.25),
        ("HEX8", 2, "shear_y", 0.011, 16, 0.08, np.pi / 5.0, 7.25),
        ("HEX8", 3, "bending_z", 0.008, 32, 0.13, np.pi / 7.0, 9.25),
        ("HEX8", 4, "traction", 0.014, 64, 0.05, np.pi / 9.0, 4.75),
    )
)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=_ROOT, text=True).strip()


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, (np.floating, np.integer, np.bool_)):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(_jsonable(value), sort_keys=True).encode("utf-8")).hexdigest()


def _state_metrics(model: Any, assembly: Any, displacement: np.ndarray) -> dict[str, Any]:
    dofs = model.dof_manager()
    fixed = _fixed_indices(model, dofs)
    external = _external(model, dofs)
    internal, tangent = assembly.assemble(displacement)
    free = np.setdiff1d(np.arange(dofs.ndof), fixed)
    residual = external - internal
    reduced = tangent[free][:, free].toarray()
    eigenvalues = np.linalg.eigvalsh(0.5 * (reduced + reduced.T))
    determinants = assembly.deformation_determinants(displacement)
    return {
        "displacement_norm": float(np.linalg.norm(displacement)),
        "displacement_max": float(np.max(np.abs(displacement))),
        "displacement_sha256": _digest(np.asarray(displacement, dtype=float).tolist()),
        "free_residual_norm": float(np.linalg.norm(residual[free])),
        "total_residual_norm": float(np.linalg.norm(residual)),
        "reaction_norm": float(np.linalg.norm(residual[fixed])),
        "strain_energy": float(assembly.strain_energy(displacement)),
        "det_f_min": float(np.min(determinants)),
        "det_f_max": float(np.max(determinants)),
        "tangent_condition_number": float(np.linalg.cond(reduced)),
        "tangent_min_eigenvalue": float(np.min(eigenvalues)),
        "tangent_max_eigenvalue": float(np.max(eigenvalues)),
    }


def _run_global(definition: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {"definition": definition, "classification": "UNRESOLVED"}
    try:
        model, _, _, _, _ = _model(
            definition["family"],
            definition["cells"],
            definition["mode"],
            definition["load_scale"],
            definition["increments"],
            distortion=definition["distortion"],
            angle=definition["angle"],
            aspect=definition["aspect"],
        )
        dofs = model.dof_manager()
        assembly = build_total_lagrangian_assembly(model)
        initial, initial_tangent = assembly.assemble(np.zeros(dofs.ndof))
        fixed = _fixed_indices(model, dofs)
        external = _external(model, dofs)
        free = np.setdiff1d(np.arange(dofs.ndof), fixed)
        reduced = initial_tangent[free][:, free].toarray()
        record.update(
            {
                "status": "STARTED",
                "quality": _quality(model),
                "node_count": int(dofs.ndof // 3),
                "element_count": len(model.elements),
                "dof_count": int(dofs.ndof),
                "initial_tangent_condition_number": float(np.linalg.cond(reduced)),
                "initial_tangent_min_eigenvalue": float(np.min(np.linalg.eigvalsh(0.5 * (reduced + reduced.T)))),
            }
        )
        displacement, diagnostics = _newton_dead_load(
            assembly,
            external,
            fixed,
            increments=definition["increments"],
            tolerance=1.0e-8,
            max_iterations=100,
            determinant_assembly=assembly,
        )
        record.update(
            {
                "status": "SUCCESS",
                "classification": "OBSERVATION_COMPLETE",
                "diagnostics": _jsonable(diagnostics),
                "final_state": _state_metrics(model, assembly, displacement),
            }
        )
    except NumericalConvergenceError as exc:
        record.update(
            {
                "status": "FAILURE",
                "classification": "NUMERICAL_CONVERGENCE",
                "failure_reason": exc.reason.value if exc.reason is not None else None,
                "message": str(exc),
                "diagnostics": _jsonable(exc.diagnostics),
            }
        )
    except Exception as exc:
        record.update(
            {
                "status": "EXCEPTION",
                "classification": "UNRESOLVED",
                "exception_type": type(exc).__name__,
                "exception": str(exc),
            }
        )
    return record


def _assembly_for_family(family: str) -> Any:
    module = (
        "solveur.elements.solid.tet4_total_lagrangian_batch"
        if family == "TET4"
        else "solveur.elements.solid.hex8_total_lagrangian_batch"
    )
    name = "TotalLagrangianTet4Assembly" if family == "TET4" else "TotalLagrangianHex8Assembly"
    return getattr(__import__(module, fromlist=[name]), name)


def _objectivity() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        coords = element_coordinates(family)
        assembly = _assembly_for_family(family)(
            coords,
            np.asarray([list(range(len(coords)))]),
            SolidMaterial(E=10.0, nu=0.3),
        )
        for kind, amplitude in (
            ("translation", 0.35),
            ("rotation", np.pi / 8.0),
            ("rotation", np.pi / 3.0),
            ("rotation", 1.25),
            ("combined", np.pi / 3.0),
        ):
            rotation = np.asarray(
                [[np.cos(amplitude), -np.sin(amplitude), 0.0], [np.sin(amplitude), np.cos(amplitude), 0.0], [0.0, 0.0, 1.0]]
                if kind != "translation"
                else np.eye(3),
                dtype=float,
            )
            translation = np.asarray([0.17, -0.11, 0.09]) if kind in {"translation", "combined"} else np.zeros(3)
            displacement = ((rotation @ coords.T).T + translation - coords).ravel()
            internal, _ = assembly.assemble(displacement)
            rows.append(
                {
                    "family": family,
                    "case": f"{kind}_{amplitude:.8g}",
                    "classification": "OBJECTIVITY_OBSERVATION",
                    "internal_force_norm": float(np.linalg.norm(internal)),
                    "energy": float(assembly.strain_energy(displacement)),
                    "det_f_min": float(np.min(assembly.deformation_determinants(displacement))),
                }
            )
    return rows


def _tangent_fd() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        coords = element_coordinates(family)
        assembly = _assembly_for_family(family)(
            coords,
            np.asarray([list(range(len(coords)))]),
            SolidMaterial(E=10.0, nu=0.3),
        )
        rng = np.random.default_rng(260830 + len(coords))
        for state, scale in (("identity", 0.0), ("tension", 0.01), ("compression", -0.01), ("shear", 0.015), ("biaxial", 0.008), ("rotation", 0.75)):
            if state == "shear":
                deformation = np.asarray([[1.0, scale, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
            elif state == "rotation":
                deformation = np.asarray(
                    [[np.cos(scale), -np.sin(scale), 0.0], [np.sin(scale), np.cos(scale), 0.0], [0.0, 0.0, 1.0]]
                )
            elif state == "biaxial":
                deformation = np.diag([1.0 + scale, 1.0 - scale / 2.0, 1.0])
            else:
                deformation = np.diag([1.0 + scale, 1.0, 1.0])
            displacement = ((deformation @ coords.T).T - coords).ravel()
            _, tangent = assembly.assemble(displacement)
            for direction_index in range(3):
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
                        "direction": direction_index,
                        "fd_step": step,
                        "relative_error": float(np.linalg.norm(analytic - numerical) / max(np.linalg.norm(numerical), 1.0e-15)),
                        "det_f_min": float(np.min(assembly.deformation_determinants(displacement))),
                        "classification": "TANGENT_FD_OBSERVATION",
                    }
                )
    return rows


def _small_strain() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for definition in PRIMARY_CASES:
        if definition["mode"] != "traction" or definition["cells"] not in MESH_LEVELS:
            continue
        small = dict(definition)
        small["load_scale"] = 1.0e-5
        small["increments"] = 8
        model, _, _, _, _ = _model(
            small["family"], small["cells"], small["mode"], small["load_scale"], small["increments"],
            distortion=small["distortion"], angle=small["angle"], aspect=small["aspect"],
        )
        dofs = model.dof_manager()
        assembly = build_total_lagrangian_assembly(model)
        _, tangent = assembly.assemble(np.zeros(dofs.ndof))
        fixed = _fixed_indices(model, dofs)
        free = np.setdiff1d(np.arange(dofs.ndof), fixed)
        external = _external(model, dofs)
        linear = np.zeros(dofs.ndof)
        linear[free] = spsolve(tangent[free][:, free], external[free])
        result = solve_model(model, enforce_policy=False)
        difference = result.displacements - linear
        rows.append(
            {
                "family": small["family"],
                "mesh_level": small["cells"],
                "load_scale": small["load_scale"],
                "relative_difference": float(np.linalg.norm(difference) / max(np.linalg.norm(linear), 1.0e-15)),
                "status": result.status,
                "classification": "SMALL_STRAIN_OBSERVATION",
            }
        )
    return rows


def _reproducibility(definitions: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for definition in definitions:
        first = _run_global(definition)
        second = _run_global(definition)
        first_state = first.get("final_state", {})
        second_state = second.get("final_state", {})
        rows.append(
            {
                "case_id": definition["id"],
                "first_status": first.get("status"),
                "second_status": second.get("status"),
                "same_status": first.get("status") == second.get("status"),
                "same_displacement_digest": first_state.get("displacement_sha256") == second_state.get("displacement_sha256"),
                "first_digest": first_state.get("displacement_sha256"),
                "second_digest": second_state.get("displacement_sha256"),
                "classification": "REPRODUCIBILITY_OBSERVATION",
            }
        )
    return rows


def _successive_refinement(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        definition = row["definition"]
        if row.get("status") != "SUCCESS":
            continue
        grouped.setdefault((definition["family"], definition["mode"]), []).append(row)
    studies: list[dict[str, Any]] = []
    for (family, mode), group in sorted(grouped.items()):
        ordered = sorted(group, key=lambda item: item["definition"][key])
        previous: dict[str, float] | None = None
        for row in ordered:
            state = row["final_state"]
            values = {
                "displacement_max": float(state["displacement_max"]),
                "reaction_norm": float(state["reaction_norm"]),
                "strain_energy": float(state["strain_energy"]),
            }
            change = {
                name: None if previous is None else abs(value - previous[name]) / max(abs(value), abs(previous[name]), 1.0e-15)
                for name, value in values.items()
            }
            studies.append(
                {
                    "family": family,
                    "mode": mode,
                    key: row["definition"][key],
                    "case_id": row["definition"]["id"],
                    "values": values,
                    "relative_change_from_previous": change,
                    "classification": "OBSERVED_TREND_ONLY",
                }
            )
            previous = values
    return studies


def _plot(results: dict[str, Any], output: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    for family in FAMILIES:
        rows = [item for item in results["global_results"] if item["definition"]["family"] == family and item.get("status") == "SUCCESS"]
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        axes[0].scatter(
            [item["definition"]["cells"] for item in rows],
            [item["final_state"]["displacement_max"] for item in rows],
            c=[item["definition"]["load_scale"] for item in rows],
        )
        axes[0].set(xlabel="mesh level", ylabel="max displacement", title=f"{family}: mesh observations")
        inc = [item for item in results["global_results"] if item["definition"]["family"] == family and item["definition"]["group"] == "increment_refinement" and item.get("status") == "SUCCESS"]
        axes[1].plot([item["definition"]["increments"] for item in inc], [item["final_state"]["displacement_max"] for item in inc], "o-")
        axes[1].set(xlabel="load increments", ylabel="max displacement", title=f"{family}: increment observations")
        fig.tight_layout()
        fig.savefig(output / f"{family.lower()}_mesh_increment_observations.png", dpi=140)
        plt.close(fig)

    rows = results["tangent_fd"]
    fig, ax = plt.subplots(figsize=(8, 4))
    for family in FAMILIES:
        family_rows = [item for item in rows if item["family"] == family]
        ax.semilogy(range(len(family_rows)), [item["relative_error"] for item in family_rows], ".-", label=family)
    ax.set(xlabel="state/direction observation", ylabel="relative FD error", title="TL tangent finite-difference observations")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "tangent_fd_observations.png", dpi=140)
    plt.close(fig)


def _historical_ids() -> set[str]:
    ids: set[str] = set()
    for path in (
        _ROOT / "qualification" / "0_2_6" / "case_registry.json",
        _ROOT / "qualification" / "0_2_6" / "g05_deep_case_registry.json",
    ):
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data.get("cases", data if isinstance(data, list) else []):
            if isinstance(item, dict) and item.get("case_id"):
                ids.add(str(item["case_id"]))
    return ids


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--skip-repeat", action="store_true", help="Skip the extra deterministic replay to shorten diagnostics.")
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)

    definitions = PRIMARY_CASES + INCREMENT_CASES + HOLDOUT_CASES
    ids = {item["id"] for item in definitions}
    historical = _historical_ids()
    overlap = sorted(ids & historical)
    if overlap:
        raise RuntimeError(f"Independent TL corpus overlaps controlled registry IDs: {overlap}")

    global_results = [_run_global(item) for item in definitions]
    repeats = [] if args.skip_repeat else _reproducibility(HOLDOUT_CASES)
    objectivity = _objectivity()
    tangent_fd = _tangent_fd()
    small_strain = _small_strain()
    report: dict[str, Any] = {
        "status": "DIAGNOSTIC_ONLY",
        "source_sha": _git("rev-parse", "HEAD"),
        "dirty": bool(_git("status", "--porcelain")),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "solver_version": "0.2.6a0",
        "families": list(FAMILIES),
        "mesh_levels": list(MESH_LEVELS),
        "increment_levels": list(INCREMENT_LEVELS),
        "corpus": {
            "total": len(definitions),
            "primary": len(PRIMARY_CASES),
            "increment_refinement": len(INCREMENT_CASES),
            "holdouts": len(HOLDOUT_CASES),
            "historical_id_overlap": overlap,
        },
        "controls": {
            "default_path": "fixed_full_newton",
            "bounded_growth_1p02": "not enabled",
            "tolerance": 1.0e-8,
            "max_iterations": 100,
            "acceptance_policy": "DIAGNOSTIC_ONLY; no numeric qualification band applied",
        },
        "global_results": global_results,
        "objectivity": objectivity,
        "tangent_fd": tangent_fd,
        "small_strain": small_strain,
        "reproducibility": repeats,
        "mesh_refinement": _successive_refinement(
            [item for item in global_results if item["definition"]["group"] == "primary_mesh_mode"],
            "cells",
        ),
        "increment_refinement": _successive_refinement(
            [item for item in global_results if item["definition"]["group"] == "increment_refinement"],
            "increments",
        ),
        "external_correlations": {
            "status": "EXISTING_BOUNDED_ONLY",
            "new_run": "SKIPPED_NOT_COMPARABLE",
            "reason": "This corpus uses new geometries/loads; no apples-to-apples external deck was identified in this diagnostic run.",
        },
        "classifications": [
            "No result is a release PASS or G07 closure.",
            "Failures remain recorded until model, BC, load, mesh and physical relevance audits support attribution.",
            "Owner-approved mesh and conditioning policies are bounded policies, not universal cutoffs.",
        ],
    }
    report["artifact_digest"] = _digest(report)
    json_text = json.dumps(_jsonable(report), indent=2, sort_keys=True) + "\n"
    (args.output / "tl_promotion_prequal.json").write_text(json_text, encoding="utf-8")
    (args.output / "tl_promotion_failure_zoo.json").write_text(
        json.dumps(
            [item for item in global_results if item.get("status") in {"FAILURE", "EXCEPTION"}],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    _plot(report, args.output)

    success = sum(item.get("status") == "SUCCESS" for item in global_results)
    failures = len(global_results) - success
    summary = [
        "# TL Promotion Prequalification",
        "",
        "Status: `DIAGNOSTIC_ONLY`; no release threshold or promotion decision was applied.",
        "",
        f"Source SHA: `{report['source_sha']}`; dirty at capture: `{report['dirty']}`.",
        f"Independent corpus: `{len(definitions)}` cases ({len(PRIMARY_CASES)} primary, {len(INCREMENT_CASES)} increment, {len(HOLDOUT_CASES)} holdouts).",
        f"Global outcomes: `{success}` success, `{failures}` failure/exception.",
        f"Mesh levels: `{MESH_LEVELS}`; increment levels: `{INCREMENT_LEVELS}`.",
        f"Objectivity observations: `{len(objectivity)}`; tangent-FD observations: `{len(tangent_fd)}`; small-strain observations: `{len(small_strain)}`.",
        f"Repeat observations: `{len(repeats)}`; historical corpus overlap: `{overlap or 'none'}`.",
        "",
        "## Interpretation",
        "",
        "- Fixed Full Newton is the default diagnostic path; bounded growth/rescue controls were not enabled.",
        "- Mesh and conditioning values are recorded as observations only; no universal cutoff is inferred.",
        "- New external correlations were skipped because an apples-to-apples controlled deck was not established in this run.",
        "- See `tl_promotion_prequal.json` for full diagnostics and `tl_promotion_failure_zoo.json` for preserved failures.",
        "",
    ]
    (args.output / "README.md").write_text("\n".join(summary), encoding="utf-8")
    print(json.dumps({"source_sha": report["source_sha"], "dirty": report["dirty"], "total": len(definitions), "success": success, "failures": failures, "holdouts": len(HOLDOUT_CASES)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
