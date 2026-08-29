"""Diagnostic rescue campaign for the three persistent HEX8 TL cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from run_tl_failure_isolation import _external, _fixed_indices, _model  # noqa: E402
from run_tl_robustness_rnd import _safe_state_metrics  # noqa: E402
from solveur.core.analyses.geometric_nonlinear import _newton_dead_load  # noqa: E402
from solveur.core.assembly.geometric import build_total_lagrangian_assembly  # noqa: E402
from solveur.core.errors import NumericalConvergenceError  # noqa: E402
from solveur.core.nonlinear.controls import AdaptiveLoadControls  # noqa: E402
from tl_robustness_rnd_support import git_dirty, git_head  # noqa: E402


OUTPUT = ROOT / "qualification" / "0_2_6" / "tl_final_rescue"
TOLERANCE = 1.0e-8
DEFAULT_MAX_ITERATIONS = 100
BASELINES = (
    {
        "id": "HEX8_m4_a10_compression_l0.2_n8_d0.12",
        "family": "HEX8",
        "cells": 4,
        "mode": "compression",
        "aspect": 10.0,
        "load_scale": 0.2,
        "increments": 8,
        "distortion": 0.12,
        "angle": 0.0,
    },
    {
        "id": "HEX8_m4_a10_compression_l0.2_n16_d0.12",
        "family": "HEX8",
        "cells": 4,
        "mode": "compression",
        "aspect": 10.0,
        "load_scale": 0.2,
        "increments": 16,
        "distortion": 0.12,
        "angle": 0.0,
    },
    {
        "id": "HEX8_m4_a10_compression_l0.2_n32_d0.12",
        "family": "HEX8",
        "cells": 4,
        "mode": "compression",
        "aspect": 10.0,
        "load_scale": 0.2,
        "increments": 32,
        "distortion": 0.12,
        "angle": 0.0,
    },
)
STATE_METRICS = (
    "displacement_norm",
    "displacement_max",
    "free_residual_norm",
    "reaction_norm",
    "strain_energy",
    "det_f_min",
    "det_f_max",
    "tangent_condition_number",
    "tangent_min_eigenvalue",
    "tangent_max_eigenvalue",
)


class RecordingAssembly:
    """Delegate assembly while retaining compact attempt diagnostics."""

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
            previous = self.calls[-1]
            call["displacement_increment_norm"] = float(
                np.linalg.norm(values - previous["_displacement"])
            )
        else:
            call["displacement_increment_norm"] = None
        try:
            internal, tangent = self.assembly.assemble(
                values, tangent_required=tangent_required
            )
        except Exception as exc:
            call.update(
                {"exception_type": type(exc).__name__, "exception": str(exc)}
            )
            call["_displacement"] = values
            self.calls.append(call)
            raise
        call.update(
            {
                "status": "SUCCESS",
                "internal_force_norm": float(np.linalg.norm(internal)),
                "tangent_nnz": int(tangent.nnz) if tangent is not None else 0,
                "_displacement": values,
            }
        )
        self.calls.append(call)
        self.last_successful_displacement = values.copy()
        return internal, tangent


def _controls(definition: dict[str, Any], overrides: dict[str, Any]) -> AdaptiveLoadControls:
    increments = int(definition["increments"])
    parameters: dict[str, Any] = {
        "initial_load_increment": 1.0 / increments,
        "min_load_increment": 1.0e-4,
        "max_load_increment": 1.0 / increments,
        "cutback_factor": 0.25,
        "growth_factor": 1.0,
        "max_cutbacks": 25,
    }
    parameters.update(overrides)
    return AdaptiveLoadControls.from_parameters(
        parameters,
        load_steps=increments,
        max_iterations=int(overrides.get("max_iterations", DEFAULT_MAX_ITERATIONS)),
    )


def _finite_difference_tangent_error(
    assembly: Any, displacement: np.ndarray, tangent: Any
) -> float | None:
    try:
        direction = np.random.default_rng(260625).normal(size=displacement.size)
        direction /= np.linalg.norm(direction)
        step = 1.0e-7
        plus = assembly.assemble(
            displacement + step * direction, tangent_required=False
        )[0]
        minus = assembly.assemble(
            displacement - step * direction, tangent_required=False
        )[0]
        numerical = (plus - minus) / (2.0 * step)
        matrix = tangent.toarray() if hasattr(tangent, "toarray") else np.asarray(tangent)
        analytic = matrix @ direction
        return float(
            np.linalg.norm(analytic - numerical)
            / max(np.linalg.norm(numerical), 1.0e-15)
        )
    except Exception:
        return None


def _compact_call(call: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in call.items()
        if key != "_displacement"
    }


def _increment_history(diagnostics: dict[str, Any]) -> list[dict[str, Any]]:
    rows = diagnostics.get("increments", [])
    if not isinstance(rows, list):
        return []
    keys = (
        "increment",
        "load_factor",
        "load_increment",
        "iterations",
        "relative_residual",
        "residual_initial",
        "residual_final",
        "minimum_det_f",
        "load_step_cutbacks",
        "state_committed",
    )
    return [{key: row.get(key) for key in keys} for row in rows if isinstance(row, dict)]


def _run(definition: dict[str, Any], policy: dict[str, Any], max_iterations: int) -> dict[str, Any]:
    started = time.perf_counter()
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
    controls = _controls(definition, {**policy, "max_iterations": max_iterations})
    status = "FAILURE"
    failure_reason: str | None = None
    diagnostics: dict[str, Any] = {}
    try:
        displacement, diagnostics = _newton_dead_load(
            recorder,
            external,
            fixed,
            increments=int(definition["increments"]),
            tolerance=TOLERANCE,
            max_iterations=max_iterations,
            determinant_assembly=assembly,
            adaptive_controls=controls,
        )
        status = "SUCCESS"
    except NumericalConvergenceError as exc:
        failure_reason = exc.reason.value if exc.reason is not None else type(exc).__name__
        diagnostics = dict(exc.diagnostics)
        displacement = recorder.last_successful_displacement
        if displacement is None:
            displacement = np.zeros(assembly.ndof, dtype=float)

    state = _safe_state_metrics(model, assembly, displacement, fixed, external)
    last_tangent = None
    for call in reversed(recorder.calls):
        if call.get("tangent_required") and call.get("status") == "SUCCESS":
            last_tangent = call
            break
    tangent_fd = (
        _finite_difference_tangent_error(
            assembly, last_tangent["_displacement"], assembly.assemble(
                last_tangent["_displacement"], tangent_required=True
            )[1],
        )
        if last_tangent is not None
        else None
    )
    return {
        "id": definition["id"],
        "definition": definition,
        "status": status,
        "failure_reason": failure_reason,
        "policy": policy,
        "max_iterations": max_iterations,
        "tolerance": TOLERANCE,
        "diagnostics": {
            "converged": diagnostics.get("converged", status == "SUCCESS"),
            "newton_iterations": diagnostics.get("newton_iterations"),
            "rejected_increments": diagnostics.get("rejected_increments", 0),
            "final_relative_residual": diagnostics.get("final_relative_residual"),
            "step": diagnostics.get("step"),
            "iterations": diagnostics.get("iterations"),
            "relative_residual": diagnostics.get("relative_residual"),
            "residual_history_tail": list(diagnostics.get("residual_history", []))[-25:],
            "increment_history": _increment_history(diagnostics),
            "rejection_log": diagnostics.get("rejection_log", []),
        },
        "final_state": {key: state.get(key) for key in STATE_METRICS},
        "tangent_fd_relative_error": tangent_fd,
        "last_attempt": _compact_call(recorder.calls[-1]) if recorder.calls else None,
        "assembly_call_count": len(recorder.calls),
        "failed_assembly_calls": sum(call["status"] == "EXCEPTION" for call in recorder.calls),
        "assembly_history_tail": [_compact_call(call) for call in recorder.calls[-25:]],
        "elapsed_seconds": time.perf_counter() - started,
    }


def _base_for(definition: dict[str, Any], **updates: Any) -> dict[str, Any]:
    result = dict(definition)
    result.update(updates)
    result["id"] = (
        f"{result['family']}_m{result['cells']}_a{result['aspect']:g}_"
        f"{result['mode']}_l{result['load_scale']:g}_n{result['increments']}"
        f"_d{result['distortion']:g}"
    )
    return result


def _increment_cases() -> list[dict[str, Any]]:
    cases = []
    for definition in BASELINES:
        for increments in (32, 64, 128, 256):
            cases.append(_base_for(definition, increments=increments))
    return cases


def _frontier_cases() -> list[dict[str, Any]]:
    base = BASELINES[1]
    cases: list[dict[str, Any]] = []
    for aspect in (9.0, 9.5, 10.0):
        cases.append(_base_for(base, aspect=aspect))
    for distortion in (0.10, 0.12, 0.14):
        if distortion != 0.12:
            cases.append(_base_for(base, distortion=distortion))
    for load in (0.175, 0.20, 0.225):
        if load != 0.20:
            cases.append(_base_for(base, load_scale=load))
    cases.extend(
        [
            _base_for(base, cells=3),
            _base_for(base, cells=5),
        ]
    )
    return cases


def _control_configs() -> list[tuple[str, dict[str, Any], int]]:
    configs: list[tuple[str, dict[str, Any], int]] = []
    for cutback in (0.20, 0.25, 0.35, 0.50):
        configs.append(
            (
                f"cutback_{cutback:g}",
                {"cutback_factor": cutback, "min_load_increment": 1.0e-6, "max_cutbacks": 64},
                100,
            )
        )
    for max_cutbacks in (32, 64, 128):
        configs.append(
            (
                f"max_cutbacks_{max_cutbacks}",
                {"cutback_factor": 0.25, "min_load_increment": 1.0e-6, "max_cutbacks": max_cutbacks},
                100,
            )
        )
    for max_iterations in (100, 200, 400):
        configs.append(
            (
                f"max_iterations_{max_iterations}",
                {"cutback_factor": 0.25, "min_load_increment": 1.0e-6, "max_cutbacks": 64},
                max_iterations,
            )
        )
    return configs


def _run_stage(stage: str, selected_ids: set[str] | None) -> dict[str, Any]:
    if stage == "increments":
        cases = _increment_cases()
        runs = [_run(case, {"cutback_factor": 0.25, "min_load_increment": 1.0e-4, "max_cutbacks": 25}, 100) for case in cases]
    elif stage == "frontier":
        cases = _frontier_cases()
        runs = [_run(case, {"cutback_factor": 0.25, "min_load_increment": 1.0e-4, "max_cutbacks": 25}, 100) for case in cases]
    elif stage == "controls":
        cases = [_base_for(definition, increments=128) for definition in BASELINES]
        runs = []
        for case in cases:
            for name, policy, max_iterations in _control_configs():
                print(f"{case['id']} {name}", flush=True)
                run = _run(case, policy, max_iterations)
                run["configuration_name"] = name
                runs.append(run)
    else:
        raise ValueError(f"Unsupported stage: {stage}")
    if selected_ids is not None:
        runs = [run for run in runs if run["id"] in selected_ids]
    return {
        "status": "DIAGNOSTIC_ONLY",
        "stage": stage,
        "source_sha": git_head(),
        "dirty_at_start": git_dirty(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "tolerance": TOLERANCE,
        "runs": runs,
        "successes": sum(run["status"] == "SUCCESS" for run in runs),
        "failures": sum(run["status"] == "FAILURE" for run in runs),
        "formulation_changed": False,
        "tangent_changed": False,
        "default_path_changed": False,
        "no_new_thresholds": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("increments", "frontier", "controls"))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--case-id", action="append", dest="case_ids")
    args = parser.parse_args(argv)
    output = args.output or OUTPUT / f"{args.stage}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    selected = set(args.case_ids) if args.case_ids else None
    report = _run_stage(args.stage, selected)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print(
        json.dumps(
            {
                "stage": report["stage"],
                "source_sha": report["source_sha"],
                "dirty_at_start": report["dirty_at_start"],
                "runs": len(report["runs"]),
                "successes": report["successes"],
                "failures": report["failures"],
                "artifact_sha256": digest,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
