"""Independently recompute HEX20 study observables from raw JSON evidence.

This script intentionally uses only the Python standard library and NumPy. It
does not import QF Solver production elements, materials, assembly or solver
modules. It validates serialization, finiteness and reported-observable
recomputations; it is not an independent FEM/Newton solve.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _finite(value: Any) -> bool:
    try:
        return bool(np.isfinite(np.asarray(value, dtype=float)).all())
    except (TypeError, ValueError):
        return False


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _recompute(raw: dict[str, Any]) -> tuple[dict[str, float], list[str]]:
    result = raw.get("observable_source", raw.get("result", {}))
    displacement_rows = result.get("displacements", [])
    displacement_values = [
        float(value)
        for row in displacement_rows
        for value in dict(row.get("dofs", {})).values()
    ]
    steps = list(result.get("solver_steps", result.get("solver", {}).get("steps", [])))
    element_results = list(result.get("element_results", []))
    serialized_states = result.get("material_states", [])
    if isinstance(serialized_states, dict):
        states = [state for values in serialized_states.values() for state in values]
    else:
        states = [
            state
            for element in serialized_states
            for state in element.get("integration_points", [])
        ]
    equilibrium = dict(result.get("equilibrium", result.get("audit", {}).get("equilibrium", {})))
    reaction = np.asarray(equilibrium.get("reaction_resultant", []), dtype=float)
    point_rows = [
        point
        for element in element_results
        for point in element.get("integration_points", [])
    ]
    values = {
        "selected_displacement": max((abs(value) for value in displacement_values), default=0.0),
        "displacement_norm": float(np.linalg.norm(displacement_values)),
        "reaction_norm": float(np.linalg.norm(reaction)),
        "energy": float(sum(float(step.get("incremental_internal_work", 0.0)) for step in steps)),
        "von_mises_max": max(
            (float(element.get("von_mises", 0.0)) for element in element_results),
            default=0.0,
        ),
        "equivalent_plastic_strain_max": max(
            (float(state.get("equivalent_plastic_strain", 0.0)) for state in states),
            default=0.0,
        ),
        "plastic_dissipation_max": max(
            (float(state.get("plastic_dissipation", 0.0)) for state in states),
            default=0.0,
        ),
        "min_det_f": min(
            (float(point["det_f"]) for point in point_rows if "det_f" in point),
            default=float("nan"),
        ),
        "max_local_strain_norm": max(
            (
                float(point["corotational_strain_norm"])
                for point in point_rows
                if "corotational_strain_norm" in point
            ),
            default=float("nan"),
        ),
        "free_relative_residual": float(equilibrium.get("free_relative_residual", float("nan"))),
        "force_balance_relative_error": float(
            equilibrium.get("force_balance_relative_error", float("nan"))
        ),
        "moment_balance_relative_error": float(
            equilibrium.get("moment_balance_relative_error", float("nan"))
        ),
    }
    errors = [name for name, value in values.items() if not _finite(value)]
    if not displacement_values:
        errors.append("missing:displacements")
    if not steps:
        errors.append("missing:solver_steps")
    return values, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    input_dir = args.input.resolve()
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for path in sorted(
        input_dir / f"h{number}_hex20.json"
        for number in (1, 2, 3)
        if (input_dir / f"h{number}_hex20.json").exists()
    ):
        raw = json.loads(path.read_text(encoding="utf-8"))
        recomputed, errors = _recompute(raw)
        declared = dict(raw.get("metrics", {}))
        declared_equilibrium = dict(declared.get("equilibrium", {}))
        comparisons = {
            name: {
                "declared": float(declared.get(name, declared_equilibrium.get(name, float("nan")))),
                "recomputed": float(value),
                "absolute_error": abs(
                    float(declared.get(name, declared_equilibrium.get(name, float("nan"))))
                    - float(value)
                ),
            }
            for name, value in recomputed.items()
        }
        mismatches = [
            name
            for name, values in comparisons.items()
            if not _finite(values["declared"])
            or values["absolute_error"] > 1.0e-12 * max(abs(values["recomputed"]), 1.0)
        ]
        rows.append(
            {
                "source": path.name,
                "source_sha256": _sha256(path),
                "family": raw.get("family"),
                "cells": raw.get("cells"),
                "status": "PASS" if not errors and not mismatches else "FAIL_CLOSED",
                "errors": errors,
                "mismatches": mismatches,
                "comparisons": comparisons,
            }
        )
    status = "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL_CLOSED"
    summary = {
        "status": status,
        "classification": "INDEPENDENT_OBSERVABLE_RECOMPUTATION_NOT_GLOBAL_FEM_SOLVE",
        "source_scope": "HEX20",
        "rows": rows,
        "production_imports": [],
        "limitations": [
            "recomputes observables from raw result JSON",
            "does not solve FEM/Newton independently",
        ],
    }
    (output_dir / "summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2, allow_nan=False), encoding="utf-8"
    )
    lines = [
        "# WP09 HEX20 independent observable recomputation",
        "",
        f"Status: `{status}`",
        "",
        "This is an independent observable recomputation from raw evidence, not an independent global FEM/Newton solve.",
        "",
        "| Raw result | Status | Max comparison error |",
        "|---|---|---:|",
    ]
    for row in rows:
        maximum = max(
            (item["absolute_error"] for item in row["comparisons"].values()),
            default=float("nan"),
        )
        lines.append(f"| {row['source']} | {row['status']} | {maximum:.3e} |")
    (output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if status == "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
