"""Independent observable recomputation for WP09 TET10 R2 evidence.

This module intentionally uses only JSON, the Python standard library, and
NumPy.  It does not import production elements, materials, assembly, or
solver routines and is not an independent global FEM/Newton solve.
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


def _relative(left: float, right: float) -> float:
    return abs(left - right) / max(abs(left), abs(right), 1.0e-14)


def _finite(value: Any) -> bool:
    try:
        return bool(np.isfinite(np.asarray(value, dtype=float)).all())
    except (TypeError, ValueError):
        return False


def _states(material_states: Any) -> list[dict[str, Any]]:
    if isinstance(material_states, dict):
        return [state for values in material_states.values() if isinstance(values, list) for state in values if isinstance(state, dict)]
    if isinstance(material_states, list):
        return [state for state in material_states if isinstance(state, dict)]
    return []


def _recompute(raw: dict[str, Any]) -> dict[str, float]:
    source = raw["observable_source"]
    serialized_displacements = source["displacements"]
    if serialized_displacements and isinstance(serialized_displacements[0], dict):
        displacement_values = [
            float(value)
            for row in serialized_displacements
            for value in dict(row.get("dofs", {})).values()
        ]
        displacements = np.asarray(displacement_values, dtype=float)
    else:
        displacements = np.asarray(serialized_displacements, dtype=float)
    steps = source["solver_steps"]
    element_results = source["element_results"]
    point_rows = [point for element in element_results for point in element.get("integration_points", [])]
    det_values = [float(point["det_f"]) for point in point_rows if "det_f" in point]
    strain_values = [float(point["corotational_strain_norm"]) for point in point_rows if "corotational_strain_norm" in point]
    stress_values = [float(element.get("von_mises", 0.0)) for element in element_results if "von_mises" in element]
    states = _states(source.get("material_states"))
    peeq_values = [float(state.get("equivalent_plastic_strain", 0.0)) for state in states]
    dissipation_values = [float(state.get("plastic_dissipation", 0.0)) for state in states]
    energy = sum(float(step.get("incremental_internal_work", 0.0)) for step in steps)
    if not energy:
        energy = sum(float(element.get("strain_energy", 0.0)) for element in element_results)
    equilibrium = source["equilibrium"]
    reaction = np.asarray(equilibrium.get("reaction_resultant", []), dtype=float)
    return {
        "selected_displacement": float(np.max(np.abs(displacements))),
        "displacement_norm": float(np.linalg.norm(displacements)),
        "reaction_norm": float(np.linalg.norm(reaction)),
        "energy": float(energy),
        "von_mises_max": max(stress_values, default=0.0),
        "equivalent_plastic_strain_max": max(peeq_values, default=0.0),
        "plastic_dissipation_max": max(dissipation_values, default=0.0),
        "min_det_f": min(det_values, default=float("nan")),
        "max_local_strain_norm": max(strain_values, default=float("nan")),
        "free_relative_residual": float(equilibrium["free_relative_residual"]),
        "force_balance_relative_error": float(equilibrium["force_balance_relative_error"]),
        "moment_balance_relative_error": float(equilibrium["moment_balance_relative_error"]),
    }


def _compare(raw: dict[str, Any]) -> dict[str, Any]:
    declared = raw["metrics"]
    declared_equilibrium = declared.get("equilibrium", {})
    recomputed = _recompute(raw)
    fields = tuple(recomputed)
    comparisons: dict[str, dict[str, float]] = {}
    errors: list[str] = []
    for field in fields:
        declared_value = declared.get(field, declared_equilibrium.get(field, float("nan")))
        left = float(declared_value)
        right = float(recomputed[field])
        absolute_error = abs(left - right)
        relative_error = _relative(left, right)
        comparisons[field] = {"declared": left, "recomputed": right, "absolute_error": absolute_error, "relative_error": relative_error}
        if not _finite(left) or not _finite(right) or (relative_error > 1.0e-12 and absolute_error > 1.0e-14):
            errors.append(field)
    return {"status": "PASS" if not errors else "FAIL_CLOSED", "errors": errors, "comparisons": comparisons}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for stage in ("h1_tet10.json", "h2_tet10.json", "h3_tet10.json"):
        source = args.input / stage
        if not source.exists():
            rows.append({"source": stage, "status": "FAIL_CLOSED_MISSING", "errors": ["missing_raw"]})
            continue
        raw = json.loads(source.read_text(encoding="utf-8"))
        metrics = raw.get("metrics", {})
        production_status = metrics.get("status") if isinstance(metrics, dict) else None
        comparison = _compare(raw) if production_status == "PASS" else {"status": "FAIL_CLOSED", "errors": ["production_not_pass"]}
        rows.append({
            "source": stage,
            "source_sha256": _sha256(source),
            "family": raw.get("family"),
            "cells": raw.get("cells"),
            "status": comparison["status"],
            "errors": comparison.get("errors", []),
            "comparisons": comparison.get("comparisons", {}),
        })
    status = "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION" if all(row["status"] == "PASS" for row in rows) else "FAIL_CLOSED"
    summary = {
        "status": status,
        "classification": "INDEPENDENT_OBSERVABLE_RECOMPUTATION_NOT_GLOBAL_FEM_SOLVE",
        "source_scope": "TET10",
        "rows": rows,
        "production_imports": [],
        "limitations": ["recomputes observables from raw result JSON", "does not solve FEM/Newton independently"],
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [
        "# WP09 TET10 independent observable recomputation",
        "",
        f"Status: `{status}`",
        "",
        "This is an independent observable recomputation from raw JSON. It is not an independent global FEM/Newton solve.",
        "",
        "| Source | Status | Errors |",
        "|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row['source']} | `{row['status']}` | `{', '.join(row.get('errors', [])) or 'none'}` |")
    (args.output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "rows": [{"source": row["source"], "status": row["status"], "errors": row.get("errors", [])} for row in rows]}, indent=2))
    return 0 if status == "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
