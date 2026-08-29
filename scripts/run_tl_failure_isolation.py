"""Isolate the three reproducible TL convergence cases without solver changes."""

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

from solveur.core.analyses.geometric_nonlinear import _newton_dead_load  # noqa: E402
from solveur.core.assembly.geometric import build_total_lagrangian_assembly  # noqa: E402
from solveur.core.errors import NumericalConvergenceError  # noqa: E402
from run_tl_stress_campaign import (  # noqa: E402
    _external,
    _fixed_indices,
    _model,
    _quality,
)


OUTPUT = _ROOT / "qualification" / "0_2_6" / "tl_failure_isolation"
BASELINES = (
    {
        "id": "CASE_1",
        "family": "TET4",
        "cells": 4,
        "mode": "compression",
        "load_scale": 0.2,
        "increments": 32,
        "distortion": 0.12,
        "angle": 0.0,
        "aspect": 10.0,
    },
    {
        "id": "CASE_2",
        "family": "HEX8",
        "cells": 4,
        "mode": "compression",
        "load_scale": 0.2,
        "increments": 32,
        "distortion": 0.12,
        "angle": 0.0,
        "aspect": 10.0,
    },
    {
        "id": "CASE_3",
        "family": "HEX8",
        "cells": 4,
        "mode": "bending_z",
        "load_scale": 0.2,
        "increments": 8,
        "distortion": 0.12,
        "angle": 0.0,
        "aspect": 10.0,
    },
)


class RecordingAssembly:
    """Observe assembly calls while delegating all numerical work unchanged."""

    def __init__(self, assembly: Any):
        self.assembly = assembly
        self.ndof = assembly.ndof
        self.calls: list[dict[str, Any]] = []
        self.previous_displacement: np.ndarray | None = None

    def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
        values = np.asarray(displacement, dtype=float).copy()
        call: dict[str, Any] = {
            "displacement_norm": float(np.linalg.norm(values)),
            "displacement_max": float(np.max(np.abs(values))) if values.size else 0.0,
            "displacement_sha256": hashlib.sha256(values.tobytes()).hexdigest(),
            "tangent_required": tangent_required,
        }
        if self.previous_displacement is not None:
            call["displacement_increment_norm"] = float(
                np.linalg.norm(values - self.previous_displacement)
            )
        else:
            call["displacement_increment_norm"] = None
        self.previous_displacement = values.copy()
        try:
            internal, tangent = self.assembly.assemble(values, tangent_required=tangent_required)
        except Exception as exc:
            call.update({"status": "EXCEPTION", "exception_type": type(exc).__name__, "exception": str(exc)})
            self.calls.append(call)
            raise
        call.update(
            {
                "status": "SUCCESS",
                "internal_force_norm": float(np.linalg.norm(internal)),
                "tangent_nnz": int(tangent.nnz) if tangent is not None else 0,
                "displacement": values,
                "internal": np.asarray(internal, dtype=float).copy(),
                "tangent": tangent,
            }
        )
        self.calls.append(call)
        return internal, tangent


def _state_metrics(
    model: Any,
    assembly: Any,
    displacement: np.ndarray,
    fixed: np.ndarray,
    external: np.ndarray,
) -> dict[str, Any]:
    dofs = model.dof_manager()
    internal, tangent = assembly.assemble(displacement)
    free = np.setdiff1d(np.arange(dofs.ndof), fixed)
    residual = external - internal
    reduced = tangent[free][:, free].toarray()
    eigenvalues = np.linalg.eigvalsh(0.5 * (reduced + reduced.T))
    determinants = assembly.deformation_determinants(displacement)
    return {
        "displacement_norm": float(np.linalg.norm(displacement)),
        "displacement_max": float(np.max(np.abs(displacement))),
        "displacement_sha256": hashlib.sha256(np.asarray(displacement).tobytes()).hexdigest(),
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


def _fd_tangent_error(assembly: Any, displacement: np.ndarray, tangent: Any) -> float:
    direction = np.random.default_rng(260625).normal(size=displacement.size)
    direction /= np.linalg.norm(direction)
    step = 1.0e-7
    plus = assembly.assemble(displacement + step * direction, tangent_required=False)[0]
    minus = assembly.assemble(displacement - step * direction, tangent_required=False)[0]
    numerical = (plus - minus) / (2.0 * step)
    tangent_matrix = tangent.toarray() if hasattr(tangent, "toarray") else np.asarray(tangent, dtype=float)
    if tangent_matrix.shape != (displacement.size, displacement.size):
        raise ValueError("Diagnostic tangent has an unexpected shape.")
    analytic = tangent_matrix @ direction
    return float(np.linalg.norm(analytic - numerical) / max(np.linalg.norm(numerical), 1.0e-15))


def _run_case(definition: dict[str, Any]) -> dict[str, Any]:
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
    fixed = _fixed_indices(model, dofs)
    external = _external(model, dofs)
    assembly = build_total_lagrangian_assembly(model)
    recorder = RecordingAssembly(assembly)
    record: dict[str, Any] = {"definition": definition, "quality": _quality(model)}
    try:
        displacement, diagnostics = _newton_dead_load(
            recorder,
            external,
            fixed,
            increments=definition["increments"],
            tolerance=1.0e-8,
            max_iterations=100,
            determinant_assembly=assembly,
        )
        record.update({"status": "SUCCESS", "diagnostics": diagnostics})
        final_state = _state_metrics(model, assembly, displacement, fixed, external)
        record["final_state"] = final_state
        tangent_call = [item for item in recorder.calls if item.get("tangent") is not None][-1]
        record["tangent_fd_relative_error"] = _fd_tangent_error(
            assembly, displacement, tangent_call["tangent"]
        )
    except NumericalConvergenceError as exc:
        record.update(
            {
                "status": "FAILURE",
                "failure_reason": exc.reason.value if exc.reason is not None else None,
                "message": str(exc),
                "diagnostics": exc.diagnostics,
            }
        )
        successful_calls = [item for item in recorder.calls if item["status"] == "SUCCESS"]
        failed_calls = [item for item in recorder.calls if item["status"] == "EXCEPTION"]
        tangent_calls = [item for item in successful_calls if item.get("tangent") is not None]
        if tangent_calls:
            last = tangent_calls[-1]
            record["last_iterate_state"] = _state_metrics(model, assembly, last["displacement"], fixed, external)
            record["tangent_fd_relative_error"] = _fd_tangent_error(
                assembly, last["displacement"], last["tangent"]
            )
            record["state_before_attempt"] = {
                key: last[key]
                for key in ("displacement_norm", "displacement_max", "displacement_sha256")
            }
        if failed_calls:
            failed = failed_calls[-1]
            record["state_after_attempt"] = {
                key: failed[key]
                for key in ("displacement_norm", "displacement_max", "displacement_sha256")
            }
            record["assembly_exception"] = {
                key: failed[key] for key in ("exception_type", "exception")
            }
        elif successful_calls:
            final_call = successful_calls[-1]
            record["state_after_attempt"] = {
                key: final_call[key]
                for key in ("displacement_norm", "displacement_max", "displacement_sha256")
            }
    record["assembly_call_count"] = len(recorder.calls)
    record["successful_assembly_calls"] = sum(item["status"] == "SUCCESS" for item in recorder.calls)
    record["failed_assembly_calls"] = sum(item["status"] == "EXCEPTION" for item in recorder.calls)
    record["assembly_history"] = [
        {
            key: item.get(key)
            for key in (
                "status",
                "tangent_required",
                "displacement_norm",
                "displacement_max",
                "displacement_increment_norm",
                "internal_force_norm",
                "tangent_nnz",
                "exception_type",
                "exception",
            )
        }
        for item in recorder.calls
    ]
    record["newton_residual_history"] = record.get("diagnostics", {}).get("residual_history", [])
    record["newton_step"] = record.get("diagnostics", {}).get("step")
    record["newton_iteration"] = record.get("diagnostics", {}).get("iterations")
    return record


def _last_converged_prefix(definition: dict[str, Any], failing_step: int) -> dict[str, Any] | None:
    """Replay only the load path through the increment before a failure."""

    if failing_step <= 1:
        return None
    prefix = dict(definition)
    prefix["variant"] = "prefix_before_failure"
    prefix["load_scale"] = definition["load_scale"] * (failing_step - 1) / definition["increments"]
    prefix["increments"] = failing_step - 1
    try:
        model, _, _, _, _ = _model(
            prefix["family"],
            prefix["cells"],
            prefix["mode"],
            prefix["load_scale"],
            prefix["increments"],
            distortion=prefix["distortion"],
            angle=prefix["angle"],
            aspect=prefix["aspect"],
        )
        dofs = model.dof_manager()
        fixed = _fixed_indices(model, dofs)
        external = _external(model, dofs)
        assembly = build_total_lagrangian_assembly(model)
        recorder = RecordingAssembly(assembly)
        displacement, diagnostics = _newton_dead_load(
            recorder,
            external,
            fixed,
            increments=prefix["increments"],
            tolerance=1.0e-8,
            max_iterations=100,
            determinant_assembly=assembly,
        )
        tangent_call = [item for item in recorder.calls if item.get("tangent") is not None][-1]
        return {
            "definition": prefix,
            "status": "SUCCESS",
            "diagnostics": diagnostics,
            "state": _state_metrics(model, assembly, displacement, fixed, external),
            "tangent_fd_relative_error": _fd_tangent_error(
                assembly, displacement, tangent_call["tangent"]
            ),
            "assembly_call_count": len(recorder.calls),
        }
    except Exception as exc:
        return {
            "definition": prefix,
            "status": "FAILURE",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
        }


def _variations(definition: dict[str, Any]) -> list[dict[str, Any]]:
    variations = []
    for multiplier in (2, 4):
        item = dict(definition)
        item["variant"] = f"increments_{multiplier}x"
        item["increments"] = definition["increments"] * multiplier
        variations.append(item)
    item = dict(definition)
    item["variant"] = "load_minus_10pct"
    item["load_scale"] = definition["load_scale"] * 0.9
    variations.append(item)
    for aspect in (8.0, 6.0):
        item = dict(definition)
        item["variant"] = f"aspect_{int(aspect)}"
        item["aspect"] = aspect
        variations.append(item)
    item = dict(definition)
    item["variant"] = "neighbor_mesh_cells_3"
    item["cells"] = 3
    variations.append(item)
    item = dict(definition)
    item["variant"] = "minimal_geometry_perturbation"
    item["distortion"] = definition["distortion"] + 1.0e-3
    variations.append(item)
    item = dict(definition)
    item["variant"] = "rotated_90deg"
    item["angle"] = np.pi / 2.0
    variations.append(item)
    return variations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    observations: list[dict[str, Any]] = []
    for baseline in BASELINES:
        baseline_record = _run_case(baseline)
        if baseline_record["status"] == "FAILURE" and baseline_record.get("newton_step"):
            prefix = _last_converged_prefix(baseline, int(baseline_record["newton_step"]))
            if prefix is not None and prefix.get("status") == "SUCCESS":
                baseline_record["last_converged_state"] = prefix["state"]
                baseline_record["last_converged_prefix"] = prefix
        observations.append({"kind": "baseline", **baseline_record})
        for variation in _variations(baseline):
            observations.append({"kind": "controlled_variation", **_run_case(variation)})
    report = {
        "status": "DIAGNOSTIC_ONLY",
        "source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_ROOT, text=True).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=_ROOT, text=True).strip()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "no_solver_change": True,
        "baseline_count": len(BASELINES),
        "variation_count": len(observations) - len(BASELINES),
        "observations": observations,
        "classification_policy": [
            "A convergence failure is not called a solver bug by this campaign.",
            "The three baseline failures are retained even when a controlled variation succeeds.",
            "The shared production solve_full_newton driver and existing assembly are delegated to unchanged.",
        ],
    }
    (args.output / "tl_failure_isolation.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = []
    for item in observations:
        definition = item["definition"]
        summary.append(
            {
                "id": definition["id"],
                "variant": definition.get("variant", "baseline"),
                "status": item["status"],
                "reason": item.get("failure_reason"),
                "step": item.get("newton_step"),
                "iteration": item.get("newton_iteration"),
                "message": item.get("message"),
                "tangent_fd": item.get("tangent_fd_relative_error"),
                "det_f_min": (item.get("last_converged_state") or item.get("last_iterate_state") or item.get("final_state") or {}).get("det_f_min"),
                "condition": (item.get("last_converged_state") or item.get("last_iterate_state") or item.get("final_state") or {}).get("tangent_condition_number"),
            }
        )
    (args.output / "tl_failure_isolation_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"source_sha": report["source_sha"], "dirty": report["dirty"], "observations": len(observations), "failures": sum(item["status"] == "FAILURE" for item in observations)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
