"""Screen existing adaptive-load controls for the TL HEX8 rescue cases.

This diagnostic harness changes no solver source.  It only varies controls
already accepted by :class:`AdaptiveLoadControls` and writes raw outputs under
an ignored directory so a later evidence report can select a candidate.
"""

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
from tl_robustness_rnd_support import LightRecordingAssembly, git_dirty, git_head  # noqa: E402


TOLERANCE = 1.0e-8
OUTPUT = ROOT / ".tmp_tl_rescue_optimization"
CASES: tuple[dict[str, Any], ...] = (
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


def _controls(definition: dict[str, Any], policy: dict[str, Any]) -> AdaptiveLoadControls:
    increments = int(definition["increments"])
    maximum_iterations = int(policy["max_iterations"])
    parameters: dict[str, Any] = {
        "initial_load_increment": 1.0 / increments,
        "max_load_increment": 1.0 / increments,
        "min_load_increment": policy["min_load_increment"],
        "cutback_factor": policy["cutback_factor"],
        "growth_factor": policy["growth_factor"],
        "grow_below_iterations": policy["grow_below_iterations"],
        "shrink_above_iterations": policy["shrink_above_iterations"],
        "max_cutbacks": policy["max_cutbacks"],
    }
    return AdaptiveLoadControls.from_parameters(
        parameters, load_steps=increments, max_iterations=maximum_iterations
    )


def _state_summary(
    model: Any,
    assembly: Any,
    displacement: np.ndarray,
    fixed: np.ndarray,
    external: np.ndarray,
    loaded_nodes: np.ndarray,
) -> dict[str, Any]:
    state = _safe_state_metrics(model, assembly, displacement, fixed, external)
    internal, _ = assembly.assemble(displacement)
    displacement_matrix = np.asarray(displacement, dtype=float).reshape((-1, 3))
    fixed_x = fixed[fixed % 3 == 0]
    state.update(
        {
            "loaded_mean_displacement": np.mean(
                displacement_matrix[loaded_nodes], axis=0
            ).tolist(),
            "loaded_mean_ux": float(np.mean(displacement_matrix[loaded_nodes, 0])),
            "fixed_reaction_resultant_x": float(
                np.sum(internal[fixed_x] - external[fixed_x])
            ),
            "displacement_sha256": hashlib.sha256(
                np.asarray(displacement, dtype=float).tobytes()
            ).hexdigest(),
        }
    )
    return state


def _compact_increments(diagnostics: dict[str, Any]) -> dict[str, Any]:
    increments = diagnostics.get("increments", [])
    rows = increments if isinstance(increments, list) else []
    iteration_values = [int(row.get("iterations", 0)) for row in rows if isinstance(row, dict)]
    return {
        "accepted_steps": len(rows),
        "newton_iterations": int(diagnostics.get("newton_iterations", 0)),
        "rejected_increments": int(diagnostics.get("rejected_increments", 0)),
        "final_relative_residual": diagnostics.get("final_relative_residual"),
        "iterations_min": min(iteration_values) if iteration_values else None,
        "iterations_max": max(iteration_values) if iteration_values else None,
        "iterations_mean": float(np.mean(iteration_values)) if iteration_values else None,
        "last_load_factor": rows[-1].get("load_factor") if rows else None,
        "last_load_increment": rows[-1].get("load_increment") if rows else None,
    }


def _run_case(definition: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    model, _, _, _, loaded_nodes = _model(
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
    recorder = LightRecordingAssembly(assembly)
    diagnostics: dict[str, Any] = {}
    status = "FAILURE"
    failure_reason: str | None = None
    try:
        displacement, diagnostics = _newton_dead_load(
            recorder,
            external,
            fixed,
            increments=int(definition["increments"]),
            tolerance=TOLERANCE,
            max_iterations=int(policy["max_iterations"]),
            determinant_assembly=assembly,
            adaptive_controls=_controls(definition, policy),
        )
        status = "SUCCESS"
    except NumericalConvergenceError as error:
        failure_reason = error.reason.value if error.reason is not None else type(error).__name__
        diagnostics = dict(error.diagnostics)
        displacement = recorder.last_successful_displacement
        if displacement is None:
            displacement = np.zeros(assembly.ndof, dtype=float)
    return {
        "id": definition["id"],
        "definition": definition,
        "policy": policy,
        "status": status,
        "failure_reason": failure_reason,
        "elapsed_seconds": time.perf_counter() - started,
        "assembly_calls": len(recorder.calls),
        "failed_assembly_calls": sum(
            call.get("status") == "EXCEPTION" for call in recorder.calls
        ),
        "diagnostics": _compact_increments(diagnostics),
        "final_state": _state_summary(
            model, assembly, displacement, fixed, external, loaded_nodes
        ),
        "rejection_log": diagnostics.get("rejection_log", []),
    }


def _policy_from_args(args: argparse.Namespace) -> dict[str, Any]:
    maximum_iterations = int(args.max_iterations)
    return {
        "initial_load_increment": "1/increments",
        "max_load_increment": "1/increments",
        "min_load_increment": float(args.min_load_increment),
        "cutback_factor": float(args.cutback_factor),
        "growth_factor": float(args.growth_factor),
        "grow_below_iterations": int(
            args.grow_below_iterations
            if args.grow_below_iterations is not None
            else max(2, maximum_iterations // 4)
        ),
        "shrink_above_iterations": int(
            args.shrink_above_iterations
            if args.shrink_above_iterations is not None
            else max(3, maximum_iterations // 2)
        ),
        "max_cutbacks": int(args.max_cutbacks),
        "max_iterations": maximum_iterations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy-name", required=True)
    parser.add_argument("--case-id", action="append", dest="case_ids")
    parser.add_argument("--max-iterations", type=int, default=200)
    parser.add_argument("--min-load-increment", type=float, default=1.0e-6)
    parser.add_argument("--cutback-factor", type=float, default=0.25)
    parser.add_argument("--max-cutbacks", type=int, default=64)
    parser.add_argument("--growth-factor", type=float, default=1.0)
    parser.add_argument("--grow-below-iterations", type=int)
    parser.add_argument("--shrink-above-iterations", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    selected = set(args.case_ids) if args.case_ids else None
    cases = [case for case in CASES if selected is None or case["id"] in selected]
    if not cases:
        raise ValueError("No configured rescue case matches --case-id.")
    policy = _policy_from_args(args)
    output = args.output or OUTPUT / f"{args.policy_name}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "study_id": "TL-RESCUE-OPTIMIZATION-026",
        "status": "DIAGNOSTIC_ONLY",
        "source_sha": git_head(),
        "dirty_at_start": git_dirty(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "policy_name": args.policy_name,
        "policy": policy,
        "tolerance": TOLERANCE,
        "runs": [],
        "formulation_changed": False,
        "tangent_changed": False,
        "default_path_changed": False,
    }
    for case in cases:
        print(f"{args.policy_name}: {case['id']}", flush=True)
        report["runs"].append(_run_case(case, policy))
    report["successes"] = sum(run["status"] == "SUCCESS" for run in report["runs"])
    report["failures"] = len(report["runs"]) - report["successes"]
    report["elapsed_seconds"] = sum(run["elapsed_seconds"] for run in report["runs"])
    report["assembly_calls"] = sum(run["assembly_calls"] for run in report["runs"])
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("policy_name", "source_sha", "dirty_at_start", "successes", "failures", "elapsed_seconds", "assembly_calls")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
