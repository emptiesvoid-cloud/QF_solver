"""Replay the full TL boundary corpus with one opt-in adaptive policy."""

from __future__ import annotations

import argparse
import hashlib
import json
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

from run_tl_boundary_study import _case_corpus  # noqa: E402
from run_tl_failure_isolation import (  # noqa: E402
    _external,
    _fixed_indices,
    _model,
    _state_metrics,
)
from solveur.core.analyses.geometric_nonlinear import _newton_dead_load  # noqa: E402
from solveur.core.assembly.geometric import build_total_lagrangian_assembly  # noqa: E402
from solveur.core.errors import NumericalConvergenceError  # noqa: E402
from solveur.core.nonlinear.controls import AdaptiveLoadControls  # noqa: E402
from tl_robustness_rnd_support import LightRecordingAssembly, git_dirty, git_head  # noqa: E402


OUTPUT = _ROOT / "qualification" / "0_2_6" / "tl_robustness_rnd" / "adaptive_growth_150.json"
TOLERANCE = 1.0e-8
MAX_ITERATIONS = 100
POLICY = {
    "initial_load_increment": "1/increments",
    "min_load_increment": 1.0e-4,
    "max_load_increment": 1.0,
    "cutback_factor": 0.5,
    "growth_factor": 1.5,
    "grow_below_iterations": 25,
    "shrink_above_iterations": 50,
    "max_cutbacks": 25,
}
STATE_METRICS = (
    "displacement_norm",
    "displacement_max",
    "free_residual_norm",
    "reaction_norm",
    "strain_energy",
    "det_f_min",
    "det_f_max",
)


def _controls(increments: int) -> AdaptiveLoadControls:
    return AdaptiveLoadControls.from_parameters(
        {key: value for key, value in POLICY.items() if key != "initial_load_increment"}
        | {"initial_load_increment": 1.0 / increments},
        load_steps=increments,
        max_iterations=MAX_ITERATIONS,
    )


def _compact_diagnostics(diagnostics: dict[str, Any]) -> dict[str, Any]:
    increments = diagnostics.get("increments", [])
    rows = increments if isinstance(increments, list) else []
    return {
        "accepted_steps": len(rows),
        "newton_iterations": int(diagnostics.get("newton_iterations", 0)),
        "final_relative_residual": diagnostics.get("final_relative_residual"),
        "rejected_increments": int(diagnostics.get("rejected_increments", 0)),
        "load_factor": rows[-1].get("load_factor") if rows else diagnostics.get("base_load_factor"),
        "iteration_history": [int(row.get("iterations", 0)) for row in rows],
        "load_history": [float(row.get("load_factor", 0.0)) for row in rows],
    }


def _safe_state(
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


def _run(definition: dict[str, Any]) -> dict[str, Any]:
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
    recorder = LightRecordingAssembly(assembly)
    try:
        displacement, diagnostics = _newton_dead_load(
            recorder,
            external,
            fixed,
            increments=definition["increments"],
            tolerance=TOLERANCE,
            max_iterations=MAX_ITERATIONS,
            determinant_assembly=assembly,
            adaptive_controls=_controls(definition["increments"]),
        )
        status = "SUCCESS"
        failure_reason = None
    except NumericalConvergenceError as exc:
        displacement = recorder.last_successful_displacement
        if displacement is None:
            displacement = np.zeros(assembly.ndof, dtype=float)
        diagnostics = exc.diagnostics
        status = "FAILURE"
        failure_reason = exc.reason.value if exc.reason is not None else type(exc).__name__
    state = _safe_state(model, assembly, displacement, fixed, external)
    return {
        "id": definition["id"],
        "definition": definition,
        "status": status,
        "failure_reason": failure_reason,
        "diagnostics": _compact_diagnostics(diagnostics),
        "final_state": state,
        "displacement_sha256": hashlib.sha256(np.asarray(displacement).tobytes()).hexdigest(),
        "assembly_call_count": len(recorder.calls),
    }


def _comparison(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    candidate_state = candidate.get("final_state", {})
    baseline_state = baseline.get("adaptive_state", {})
    differences = {
        metric: (
            None
            if metric not in candidate_state or metric not in baseline_state
            else float(candidate_state[metric]) - float(baseline_state[metric])
        )
        for metric in STATE_METRICS
    }
    baseline_status = baseline["adaptive_status"]
    candidate_status = candidate["status"]
    return {
        "id": candidate["id"],
        "baseline_status": baseline_status,
        "candidate_status": candidate_status,
        "recovered": baseline_status == "FAILURE" and candidate_status == "SUCCESS",
        "regressed": baseline_status == "SUCCESS" and candidate_status != "SUCCESS",
        "state_differences_candidate_minus_baseline": differences,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=_ROOT / "qualification" / "0_2_6" / "tl_boundary_study" / "tl_boundary_study_summary.json",
    )
    args = parser.parse_args(argv)
    baseline_payload = json.loads(args.baseline.read_text(encoding="utf-8"))
    baseline = {row["id"]: row for row in baseline_payload["physical_cases"]}
    corpus = _case_corpus()
    results: list[dict[str, Any]] = []
    for index, definition in enumerate(corpus, start=1):
        print(f"[{index}/{len(corpus)}] {definition['id']}", flush=True)
        results.append(_run(definition))
    comparisons = [_comparison(row, baseline[row["id"]]) for row in results]
    report = {
        "status": "DIAGNOSTIC_ONLY",
        "source_sha": git_head(),
        "dirty_at_start": git_dirty(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "policy": POLICY,
        "corpus_count": len(corpus),
        "results": results,
        "comparisons": comparisons,
        "candidate_successes": sum(row["status"] == "SUCCESS" for row in results),
        "baseline_adaptive_successes": sum(row["adaptive_status"] == "SUCCESS" for row in baseline.values()),
        "recoveries": sum(item["recovered"] for item in comparisons),
        "regressions": sum(item["regressed"] for item in comparisons),
        "status_changes": sum(item["baseline_status"] != item["candidate_status"] for item in comparisons),
        "persistent_failure_ids": [
            row["id"] for row in comparisons if row["baseline_status"] == "FAILURE" and row["candidate_status"] == "FAILURE"
        ],
        "baseline_source_sha": baseline_payload.get("source_sha"),
        "no_new_thresholds": True,
        "formulation_changed": False,
        "tangent_changed": False,
        "default_path_changed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "source_sha",
                    "dirty_at_start",
                    "corpus_count",
                    "candidate_successes",
                    "baseline_adaptive_successes",
                    "recoveries",
                    "regressions",
                    "status_changes",
                )
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
