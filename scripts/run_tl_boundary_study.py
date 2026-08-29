"""Measure the diagnostic TL robustness boundary for TET4 and HEX8."""

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

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

from run_tl_failure_isolation import (  # noqa: E402
    _external,
    _fixed_indices,
    _model,
    _state_metrics,
)
from tl_boundary_reporting import (  # noqa: E402
    aspect_outcomes,
    aspect_summary,
    conditioning_summary,
    cutback_effect,
    jsonable,
    markdown,
    physical_rows,
    reproducibility,
    zone_summary,
)
from solveur.core.analyses.geometric_nonlinear import _newton_dead_load  # noqa: E402
from solveur.core.assembly.geometric import build_total_lagrangian_assembly  # noqa: E402
from solveur.core.errors import NumericalConvergenceError  # noqa: E402
from solveur.core.nonlinear.controls import AdaptiveLoadControls  # noqa: E402
from solveur.elements.solid.hex8 import Hex8Element  # noqa: E402
from solveur.mesh.quality import MeshQuality  # noqa: E402
from solveur.mesh.validation import MeshValidator  # noqa: E402


OUTPUT = _ROOT / "qualification" / "0_2_6" / "tl_boundary_study"
FAMILIES = ("TET4", "HEX8")
MESH_LEVELS = (1, 2, 3, 4)
ASPECT_RATIOS = (4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0)
MESH_GRID_ASPECTS = (4.0, 7.0, 10.0)
MODES = ("compression", "bending_z", "traction")
LOAD_LEVELS = (0.05, 0.1, 0.2)
INCREMENT_LEVELS = (8, 16, 32)
DISTORTION_LEVELS = (0.0, 0.06, 0.12, 0.18)
BASE_LOAD = 0.2
BASE_INCREMENTS = 16
TOLERANCE = 1.0e-8
MAX_ITERATIONS = 100
_HEX8_EDGES = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 0),
    (4, 5),
    (5, 6),
    (6, 7),
    (7, 4),
    (0, 4),
    (1, 5),
    (2, 6),
    (3, 7),
)


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_ROOT, text=True).strip()


def _git_dirty() -> bool:
    return bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=_ROOT, text=True).strip())


def _case_id(
    family: str,
    cells: int,
    aspect: float,
    mode: str,
    load: float,
    increments: int,
    distortion: float,
) -> str:
    return (
        f"{family}_m{cells}_a{aspect:g}_{mode}_l{load:g}_n{increments}"
        f"_d{distortion:g}"
    )


def _definition(
    family: str,
    cells: int,
    aspect: float,
    mode: str,
    load: float = BASE_LOAD,
    increments: int = BASE_INCREMENTS,
    distortion: float = 0.12,
    *,
    group: str,
) -> dict[str, Any]:
    return {
        "id": _case_id(family, cells, aspect, mode, load, increments, distortion),
        "family": family,
        "cells": cells,
        "mesh_level": cells,
        "aspect": aspect,
        "mode": mode,
        "load_scale": load,
        "increments": increments,
        "distortion": distortion,
        "angle": 0.0,
        "group": group,
    }


def _case_corpus() -> list[dict[str, Any]]:
    definitions: dict[tuple[Any, ...], dict[str, Any]] = {}

    def add(item: dict[str, Any]) -> None:
        key = (
            item["family"],
            item["cells"],
            item["aspect"],
            item["mode"],
            item["load_scale"],
            item["increments"],
            item["distortion"],
            item["angle"],
        )
        if key not in definitions:
            definitions[key] = item

    for family in FAMILIES:
        for cells in MESH_LEVELS:
            for aspect in MESH_GRID_ASPECTS:
                for mode in MODES:
                    add(_definition(family, cells, aspect, mode, group="mesh_grid"))
        for aspect in ASPECT_RATIOS:
            for mode in MODES:
                add(_definition(family, 4, aspect, mode, group="aspect_sweep"))
        for load in LOAD_LEVELS:
            for mode in MODES:
                add(_definition(family, 4, 6.0, mode, load=load, group="load_sweep"))
        for aspect in (6.0, 8.0, 10.0):
            for increments in INCREMENT_LEVELS:
                for mode in ("compression", "bending_z"):
                    add(
                        _definition(
                            family,
                            4,
                            aspect,
                            mode,
                            increments=increments,
                            group="increment_sweep",
                        )
                    )
        for distortion in DISTORTION_LEVELS:
            for mode in MODES:
                add(
                    _definition(
                        family,
                        4,
                        6.0,
                        mode,
                        distortion=distortion,
                        group="distortion_sweep",
                    )
                )
    return list(definitions.values())


class _RecordingAssembly:
    """Record solver-visible states without changing the delegated assembly."""

    def __init__(self, assembly: Any) -> None:
        self.assembly = assembly
        self.ndof = assembly.ndof
        self.calls: list[dict[str, Any]] = []
        self.last_successful_displacement: np.ndarray | None = None

    def assemble(
        self, displacement: np.ndarray, *, tangent_required: bool = True
    ) -> tuple[np.ndarray, Any]:
        values = np.asarray(displacement, dtype=float).copy()
        call: dict[str, Any] = {
            "displacement_norm": float(np.linalg.norm(values)),
            "displacement_max": float(np.max(np.abs(values))) if values.size else 0.0,
            "displacement_sha256": hashlib.sha256(values.tobytes()).hexdigest(),
            "tangent_required": tangent_required,
            "status": "EXCEPTION",
        }
        if self.calls:
            call["displacement_increment_norm"] = float(
                np.linalg.norm(values - self.calls[-1]["displacement"])
            )
        else:
            call["displacement_increment_norm"] = None
        try:
            internal, tangent = self.assembly.assemble(values, tangent_required=tangent_required)
        except Exception as exc:
            call.update({"exception_type": type(exc).__name__, "exception": str(exc)})
            self.calls.append({**call, "displacement": values})
            raise
        call.update(
            {
                "status": "SUCCESS",
                "internal_force_norm": float(np.linalg.norm(internal)),
                "tangent_nnz": int(tangent.nnz) if tangent is not None else 0,
                "displacement": values,
            }
        )
        self.calls.append(call)
        self.last_successful_displacement = values.copy()
        return internal, tangent


def _mesh_quality(model: Any) -> dict[str, Any]:
    validation = MeshValidator().validate(model)
    metrics: list[dict[str, float]] = []
    for element in model.elements:
        coords = model.nodes[list(element.nodes)]
        if element.type == "TET4":
            metrics.append({key: float(value) for key, value in MeshQuality.tet_metrics(coords).items()})
            continue
        jacobians = [float(np.linalg.det(Hex8Element.jacobian(coords, point))) for point in Hex8Element.integration_points]
        edges = [float(np.linalg.norm(coords[first] - coords[second])) for first, second in _HEX8_EDGES]
        jacobian_min = min(jacobians)
        jacobian_max = max(jacobians)
        edge_min = min(edges)
        edge_max = max(edges)
        metrics.append(
            {
                "jacobian_min": jacobian_min,
                "jacobian_max": jacobian_max,
                "jacobian_ratio": jacobian_min / jacobian_max if jacobian_max else float("nan"),
                "edge_length_min": edge_min,
                "edge_length_max": edge_max,
                "edge_aspect_ratio": edge_max / edge_min if edge_min else float("inf"),
            }
        )
    numeric_keys = sorted({key for item in metrics for key in item})
    summary: dict[str, float] = {}
    for key in numeric_keys:
        values = [item[key] for item in metrics if np.isfinite(item[key])]
        if values:
            summary[f"{key}_min"] = float(min(values))
            summary[f"{key}_max"] = float(max(values))
            summary[f"{key}_mean"] = float(np.mean(values))
    return {
        "status": validation.status,
        "errors": list(validation.errors),
        "warnings": list(validation.warnings),
        "element_metrics": metrics,
        "summary": summary,
    }


def _initial_tangent_metrics(assembly: Any, fixed: np.ndarray) -> dict[str, float | None]:
    try:
        zero = np.zeros(assembly.ndof, dtype=float)
        _, tangent = assembly.assemble(zero)
        free = np.setdiff1d(np.arange(assembly.ndof), fixed)
        reduced = tangent[free][:, free].toarray()
        symmetric = 0.5 * (reduced + reduced.T)
        eigenvalues = np.linalg.eigvalsh(symmetric)
        return {
            "condition_number": float(np.linalg.cond(reduced)),
            "minimum_eigenvalue": float(np.min(eigenvalues)),
            "maximum_eigenvalue": float(np.max(eigenvalues)),
        }
    except Exception as exc:
        return {"condition_number": None, "minimum_eigenvalue": None, "maximum_eigenvalue": None, "error": str(exc)}


def _safe_state_metrics(
    model: Any,
    assembly: Any,
    displacement: np.ndarray,
    fixed: np.ndarray,
    external: np.ndarray,
) -> dict[str, Any]:
    try:
        return _state_metrics(model, assembly, displacement, fixed, external)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _adaptive_controls(increments: int) -> AdaptiveLoadControls:
    initial = 1.0 / increments
    return AdaptiveLoadControls.from_parameters(
        {
            "initial_load_increment": initial,
            "min_load_increment": 1.0e-4,
            "max_load_increment": initial,
            "cutback_factor": 0.5,
            "growth_factor": 1.0,
            "max_cutbacks": 8,
        },
        load_steps=increments,
        max_iterations=MAX_ITERATIONS,
    )


def _diagnostic_summary(diagnostics: dict[str, Any]) -> dict[str, Any]:
    increments = diagnostics.get("increments")
    increment_rows = increments if isinstance(increments, list) else []
    residual_history = diagnostics.get("residual_history")
    if not isinstance(residual_history, (list, tuple)):
        residual_history = [value for item in increment_rows for value in item.get("residual_history", [])]
    accepted_iterations = sum(int(item.get("iterations", 0)) for item in increment_rows)
    return {
        "accepted_steps": len(increment_rows),
        "newton_iterations": int(diagnostics.get("newton_iterations", accepted_iterations)),
        "final_relative_residual": diagnostics.get("final_relative_residual"),
        "maximum_relative_residual": max(
            (float(item["relative_residual"]) for item in increment_rows if item.get("relative_residual") is not None),
            default=None,
        ),
        "residual_history": [float(value) for value in residual_history],
        "last_step": diagnostics.get("step", increment_rows[-1].get("increment") if increment_rows else None),
        "load_factor": increment_rows[-1].get("load_factor") if increment_rows else diagnostics.get("base_load_factor"),
        "rejected_increments": int(diagnostics.get("rejected_increments", 0)),
        "rejection_log": diagnostics.get("rejection_log", []),
    }


def _run_variant(definition: dict[str, Any], adaptive: bool) -> dict[str, Any]:
    model: Any | None = None
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
        quality = _mesh_quality(model)
        dofs = model.dof_manager()
        fixed = _fixed_indices(model, dofs)
        external = _external(model, dofs)
        assembly = build_total_lagrangian_assembly(model)
        initial_tangent = _initial_tangent_metrics(assembly, fixed)
        recorder = _RecordingAssembly(assembly)
        controls = _adaptive_controls(definition["increments"]) if adaptive else None
        try:
            displacement, diagnostics = _newton_dead_load(
                recorder,
                external,
                fixed,
                increments=definition["increments"],
                tolerance=TOLERANCE,
                max_iterations=MAX_ITERATIONS,
                determinant_assembly=assembly,
                adaptive_controls=controls,
            )
            status = "SUCCESS"
            failure_reason = None
            last_displacement = displacement
        except NumericalConvergenceError as exc:
            status = "FAILURE"
            failure_reason = exc.reason.value if exc.reason is not None else type(exc).__name__
            diagnostics = exc.diagnostics
            last_displacement = recorder.last_successful_displacement
            if last_displacement is None:
                last_displacement = np.zeros(assembly.ndof, dtype=float)
        final_state = _safe_state_metrics(model, assembly, last_displacement, fixed, external)
        return {
            "id": definition["id"],
            "variant": "adaptive" if adaptive else "fixed",
            "definition": definition,
            "status": status,
            "failure_reason": failure_reason,
            "quality": quality,
            "initial_tangent": initial_tangent,
            "diagnostics": _diagnostic_summary(diagnostics),
            "final_state": final_state,
            "assembly_call_count": len(recorder.calls),
            "successful_assembly_calls": sum(item["status"] == "SUCCESS" for item in recorder.calls),
            "failed_assembly_calls": sum(item["status"] == "EXCEPTION" for item in recorder.calls),
            "assembly_history": [
                {key: value for key, value in item.items() if key != "displacement"}
                for item in recorder.calls
            ],
        }
    except Exception as exc:
        return {
            "id": definition["id"],
            "variant": "adaptive" if adaptive else "fixed",
            "definition": definition,
            "status": "EXCEPTION",
            "failure_reason": type(exc).__name__,
            "message": str(exc),
            "classification": "MODEL_INVALID",
            "quality": None,
            "initial_tangent": None,
            "diagnostics": {},
            "final_state": {},
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)

    corpus = _case_corpus()
    results: list[dict[str, Any]] = []
    for index, definition in enumerate(corpus, start=1):
        print(f"[{index}/{len(corpus)}] {definition['id']}", flush=True)
        results.append(_run_variant(definition, adaptive=False))
        results.append(_run_variant(definition, adaptive=True))
    physical_cases = physical_rows(results)
    repeat_definitions = [
        _definition(family, 4, 6.0, "compression", group="reproducibility")
        for family in FAMILIES
    ]
    report = {
        "status": "DIAGNOSTIC_ONLY",
        "source_sha": _git_head(),
        "dirty": _git_dirty(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "families": list(FAMILIES),
        "mesh_levels": list(MESH_LEVELS),
        "aspect_ratios_tested": list(ASPECT_RATIOS),
        "modes": list(MODES),
        "load_levels": list(LOAD_LEVELS),
        "increment_levels": list(INCREMENT_LEVELS),
        "distortion_levels": list(DISTORTION_LEVELS),
        "fixed_step_policy": {"tolerance": TOLERANCE, "max_iterations": MAX_ITERATIONS},
        "adaptive_policy": {
            "opt_in": True,
            "minimum_increment": 1.0e-4,
            "cutback_factor": 0.5,
            "maximum_cutbacks": 8,
            "growth_factor": 1.0,
        },
        "corpus_count": len(corpus),
        "results": results,
        "physical_cases": physical_cases,
        "zone_summary": zone_summary(physical_cases),
        "aspect_outcomes": aspect_outcomes(physical_cases),
        "conditioning_correlation": conditioning_summary(physical_cases),
        "aspect_ratio_correlation": aspect_summary(physical_cases),
        "cutback_effect": cutback_effect(physical_cases),
        "reproducibility": reproducibility(repeat_definitions, _run_variant),
        "case2_preserved": any(
            row["family"] == "HEX8"
            and row["mesh_level"] == 4
            and row["aspect"] == 10.0
            and row["mode"] == "compression"
            and row["fixed_status"] == "FAILURE"
            for row in physical_cases
        ),
        "no_solver_change": True,
        "no_new_thresholds": True,
        "candidate_mesh_policy": "PROPOSED_OWNER_REVIEW",
        "candidate_conditioning_policy": "PROPOSED_OWNER_REVIEW",
        "classification_policy": {
            "stable": "fixed and adaptive succeed without adaptive rejection",
            "degraded": "at least one path succeeds, with failure or cutback sensitivity",
            "out_of_recommended_scope": "both paths fail in the tested domain",
        },
    }
    json_report = jsonable(report)
    (args.output / "tl_boundary_study.json").write_text(
        json.dumps(json_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = {
        key: json_report[key]
        for key in (
            "status",
            "source_sha",
            "dirty",
            "families",
            "mesh_levels",
            "aspect_ratios_tested",
            "load_levels",
            "increment_levels",
            "distortion_levels",
            "corpus_count",
            "physical_cases",
            "zone_summary",
            "aspect_outcomes",
            "conditioning_correlation",
            "aspect_ratio_correlation",
            "cutback_effect",
            "reproducibility",
            "case2_preserved",
            "candidate_mesh_policy",
            "candidate_conditioning_policy",
        )
    }
    (args.output / "tl_boundary_study_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output / "tl_boundary_study.md").write_text(markdown(json_report), encoding="utf-8")
    print(
        json.dumps(
            {
                "source_sha": json_report["source_sha"],
                "dirty": json_report["dirty"],
                "corpus_count": json_report["corpus_count"],
                "fixed_successes": json_report["cutback_effect"]["fixed_successes"],
                "adaptive_successes": json_report["cutback_effect"]["adaptive_successes"],
                "recovered_by_cutback": json_report["cutback_effect"]["recovered_by_cutback"],
                "failed_in_both_modes": json_report["cutback_effect"]["failed_in_both_modes"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
