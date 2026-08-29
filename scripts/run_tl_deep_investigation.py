"""Run the diagnostic-only Total-Lagrangian TET4/HEX8 investigation.

This runner deliberately reuses existing verification builders.  Its outputs
are observations, not release qualification evidence, and it never changes
solver tolerances or solver implementation.
"""

# The runner pins imports to this checkout so it cannot silently use another
# installed clone; the deliberate path insertion is therefore before imports.
# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_LOCAL_ROOT = Path(__file__).resolve().parents[1]
if str(_LOCAL_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_LOCAL_ROOT / "src"))

from solveur.verification.robustness_geometric import (
    run_finite_kinematic_limit_recovery_benchmark,
    run_large_rotation_geometric_benchmark,
    run_large_rotation_mesh_sensitivity_benchmark,
    run_multi_element_load_step_sensitivity,
)  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "qualification" / "0_2_6" / "tl_deep_investigation"
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _run(name: str, function: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return {"name": name, "status": "COMPLETED", "result": function()}
    except Exception as exc:  # diagnostic corpus must preserve failures
        return {
            "name": name,
            "status": "EXCEPTION",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
        }


def _failure_zoo(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    zoo: list[dict[str, Any]] = []
    for item in results:
        result = item.get("result", {})
        for row in result.get("rows", []):
            if row.get("status") in {"FAIL", "EXCEPTION"}:
                zoo.append(
                    {
                        "case": f"{item['name']}:{row.get('element', 'unknown')}",
                        "classification": "UNRESOLVED",
                        "symptoms": row,
                        "provenance": "diagnostic-only; source SHA recorded at report level",
                    }
                )
    zoo.append(
        {
            "case": "invalid_current_configuration",
            "classification": "EXPECTED_LIMITATION",
            "symptoms": "Existing TL assembly rejects current det(F) <= 1e-10.",
            "provenance": "existing unit contract; intentionally retained as a diagnostic boundary",
        }
    )
    zoo.append(
        {
            "case": "unsupported_distributed_load",
            "classification": "EXPECTED_LIMITATION",
            "symptoms": "Public geometric nonlinear scope accepts nodal dead loads only.",
            "provenance": "existing public API contract; no workaround applied",
        }
    )
    return zoo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    results = [
        _run("large_rotation", lambda: run_large_rotation_geometric_benchmark(("TET4", "HEX8"))),
        _run(
            "large_rotation_mesh_sensitivity",
            lambda: run_large_rotation_mesh_sensitivity_benchmark(
                ("TET4", "HEX8"), (1, 2), load_increments=30, load_scale=1.0
            ),
        ),
        _run("load_step_sensitivity", lambda: run_multi_element_load_step_sensitivity(("TET4", "HEX8"))),
        _run("finite_kinematic_limit_diagnostic", lambda: run_finite_kinematic_limit_recovery_benchmark(("TET4", "HEX8"))),
    ]
    report = {
        "status": "DIAGNOSTIC_ONLY",
        "source_sha": _git_sha(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "solver_scope": "Total-Lagrangian elastic TET4/HEX8; finite-kinematic J2 retained as research diagnostic",
        "families": ["TET4", "HEX8"],
        "no_release_thresholds": True,
        "results": results,
        "failure_zoo": _failure_zoo(results),
        "classification_policy": [
            "An exception is preserved for manual model/mesh/BC audit; it is not called a solver bug automatically.",
            "Existing PASS/FAIL labels are observations from existing harnesses, not release decisions.",
            "No source solver module, tolerance, or formulation is changed by this runner.",
        ],
    }
    (args.output / "tl_investigation_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output / "tl_failure_zoo.json").write_text(json.dumps(report["failure_zoo"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"source_sha": report["source_sha"], "dirty": report["dirty"], "results": [(item["name"], item["status"]) for item in results], "failure_zoo": len(report["failure_zoo"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
