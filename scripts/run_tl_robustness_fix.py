"""Replay the TL failure zoo with opt-in adaptive load cutback."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

from solveur.core.analyses.geometric_nonlinear import _newton_dead_load  # noqa: E402
from solveur.core.assembly.geometric import build_total_lagrangian_assembly  # noqa: E402
from solveur.core.errors import NumericalConvergenceError  # noqa: E402
from solveur.core.nonlinear.controls import AdaptiveLoadControls  # noqa: E402
from run_tl_failure_isolation import (  # noqa: E402
    BASELINES,
    _external,
    _fd_tangent_error,
    _fixed_indices,
    _model,
    _quality,
    _run_case,
    _state_metrics,
)


OUTPUT = _ROOT / "qualification" / "0_2_6" / "tl_robustness_fix"


def _adaptive_case(definition: dict[str, Any]) -> dict[str, Any]:
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
    initial_increment = 1.0 / definition["increments"]
    controls = AdaptiveLoadControls.from_parameters(
        {
            "initial_load_increment": initial_increment,
            "min_load_increment": 1.0e-4,
            "max_load_increment": initial_increment,
            "cutback_factor": 0.5,
            "growth_factor": 1.0,
            "max_cutbacks": 25,
        },
        load_steps=definition["increments"],
        max_iterations=100,
    )
    try:
        displacement, diagnostics = _newton_dead_load(
            assembly,
            external,
            fixed,
            increments=definition["increments"],
            tolerance=1.0e-8,
            max_iterations=100,
            determinant_assembly=assembly,
            adaptive_controls=controls,
        )
        tangent = assembly.assemble(displacement)[1]
        return {
            "definition": definition,
            "quality": _quality(model),
            "status": "SUCCESS",
            "diagnostics": diagnostics,
            "final_state": _state_metrics(model, assembly, displacement, fixed, external),
            "tangent_fd_relative_error": _fd_tangent_error(assembly, displacement, tangent),
        }
    except NumericalConvergenceError as exc:
        return {
            "definition": definition,
            "quality": _quality(model),
            "status": "FAILURE",
            "failure_reason": exc.reason.value if exc.reason is not None else None,
            "message": str(exc),
            "diagnostics": exc.diagnostics,
        }


def _paired_increment_study() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in ("TET4", "HEX8"):
        for increments in (16, 32):
            definition = {
                "id": f"PAIRED_{family}_{increments}",
                "family": family,
                "cells": 4,
                "mode": "compression",
                "load_scale": 0.2,
                "increments": increments,
                "distortion": 0.12,
                "angle": 0.0,
                "aspect": 6.0,
            }
            result = _run_case(definition)
            rows.append(
                {
                    "id": definition["id"],
                    "family": family,
                    "increments": increments,
                    "status": result["status"],
                    "reason": result.get("failure_reason"),
                    "final_displacement": (result.get("final_state") or {}).get("displacement_norm"),
                    "relative_residual": (result.get("final_state") or {}).get("free_residual_norm"),
                }
            )
    return rows


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TL Newton Robustness Fix",
        "",
        "This report evaluates opt-in adaptive load cutback on the existing TL failure zoo.",
        "The TL formulation, tangent, assembly and convergence tolerance are unchanged.",
        "",
        f"- Source SHA at execution: `{report['source_sha']}`",
        f"- Worktree dirty at execution: `{report['dirty']}`",
        f"- Generated: `{report['timestamp_utc']}`",
        "",
        "## Failure zoo replay",
        "",
        "| Case | Fixed baseline | Adaptive result | Rejected increments | Final reason |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in report["cases"]:
        adaptive = row["adaptive"]
        diagnostics = adaptive.get("diagnostics", {})
        lines.append(
            f"| {row['id']} | {row['baseline']['status']} / {row['baseline'].get('failure_reason', '-') or '-'} "
            f"| {adaptive['status']} | {diagnostics.get('rejected_increments', 0)} "
            f"| {adaptive.get('failure_reason', '-') or '-'} |"
        )
    lines.extend(
        [
            "",
            "## Paired increment study",
            "",
            "| Case | Status | Reason | Displacement norm | Free residual |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for row in report["paired_increment_study"]:
        lines.append(
            f"| {row['id']} | {row['status']} | {row.get('reason', '-') or '-'} "
            f"| {row.get('final_displacement', '-') or '-'} | {row.get('relative_residual', '-') or '-'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Fixed-step failure records are retained as the historical baseline.",
            "- Adaptive cutback is opt-in and reuses the existing Full Newton driver and line search.",
            "- A failed attempt is discarded before retry; reaching a configured limit fails closed.",
            "- Mesh-conditioning failures are not promoted to successful solves by this report.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)

    cases = []
    for definition in BASELINES:
        cases.append(
            {
                "id": definition["id"],
                "baseline": _run_case(definition),
                "adaptive": _adaptive_case(definition),
            }
        )
    report = {
        "status": "ROBUSTNESS_QUALIFICATION_PREPARATION",
        "source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_ROOT, text=True).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=_ROOT, text=True).strip()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "functional_scope_unchanged": True,
        "formulation_changed": False,
        "tangent_changed": False,
        "line_search_added": False,
        "cases": cases,
        "paired_increment_study": _paired_increment_study(),
        "limitations": [
            "CASE_1 and CASE_2 remain mesh-conditioning stress cases if cutback exhaustion is reached.",
            "Adaptive stepping is an opt-in robustness mechanism, not a TL promotion or qualification result.",
            "No new acceptance criterion is introduced by this campaign.",
        ],
    }
    (args.output / "tl_robustness_fix.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "status": report["status"],
        "source_sha": report["source_sha"],
        "dirty": report["dirty"],
        "formulation_changed": report["formulation_changed"],
        "tangent_changed": report["tangent_changed"],
        "line_search_added": report["line_search_added"],
        "cases": [
            {
                "id": row["id"],
                "baseline_status": row["baseline"]["status"],
                "baseline_reason": row["baseline"].get("failure_reason"),
                "baseline_step": row["baseline"].get("newton_step"),
                "adaptive_status": row["adaptive"]["status"],
                "adaptive_reason": row["adaptive"].get("failure_reason"),
                "adaptive_rejected_increments": row["adaptive"].get("diagnostics", {}).get(
                    "rejected_increments", 0
                ),
                "adaptive_accepted_steps": len(
                    row["adaptive"].get("diagnostics", {}).get("increments", [])
                ),
            }
            for row in cases
        ],
        "paired_increment_study": report["paired_increment_study"],
        "limitations": report["limitations"],
    }
    (args.output / "tl_robustness_fix_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output / "tl_robustness_fix.md").write_text(_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "source_sha": report["source_sha"],
                "dirty": report["dirty"],
                "cases": [
                    {
                        "id": row["id"],
                        "baseline": row["baseline"]["status"],
                        "adaptive": row["adaptive"]["status"],
                        "rejected_increments": row["adaptive"].get("diagnostics", {}).get(
                            "rejected_increments", 0
                        ),
                    }
                    for row in cases
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
