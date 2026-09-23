"""Independent NumPy observable recomputation for WP09 TET4 evidence.

This checker imports no production solver, element, contact, material, or
assembly code.  It validates recomputed summaries against the raw serialized
result; it is not an independent FEM/Newton solution.
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


def _states(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [row for values in value.values() if isinstance(values, list) for row in values if isinstance(row, dict)]
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    return []


def _recompute(raw: dict[str, Any]) -> dict[str, float]:
    source = raw["observable_source"]
    displacement = np.asarray(source["displacements"], dtype=float)
    elements = source["element_results"]
    points = [point for element in elements for point in element.get("integration_points", [])]
    states = _states(source.get("material_states"))
    steps = source["solver_steps"]
    energy = sum(float(step.get("incremental_internal_work", 0.0)) for step in steps)
    if not energy:
        energy = sum(float(element.get("strain_energy", 0.0)) for element in elements)
    equilibrium = source["equilibrium"]
    reaction = np.asarray(equilibrium["reaction_resultant"], dtype=float)
    return {
        "selected_displacement": float(np.max(np.abs(displacement))),
        "displacement_norm": float(np.linalg.norm(displacement)),
        "reaction_norm": float(np.linalg.norm(reaction)),
        "energy": energy,
        "von_mises_max": max((float(row["von_mises"]) for row in elements if "von_mises" in row), default=float("nan")),
        "equivalent_plastic_strain_max": max((float(row.get("equivalent_plastic_strain", 0.0)) for row in states), default=0.0),
        "plastic_dissipation_max": max((float(row.get("plastic_dissipation", 0.0)) for row in states), default=0.0),
        "min_det_f": min((float(row["det_f"]) for row in points if "det_f" in row), default=float("nan")),
        "max_local_strain_norm": max((float(row["corotational_strain_norm"]) for row in points if "corotational_strain_norm" in row), default=float("nan")),
    }


def _compare(raw: dict[str, Any]) -> dict[str, Any]:
    declared = raw["metrics"]
    recomputed = _recompute(raw)
    comparisons: dict[str, dict[str, float]] = {}
    failures: list[str] = []
    for field, value in recomputed.items():
        expected = float(declared[field])
        error = abs(expected - value)
        relative = _relative(expected, value)
        comparisons[field] = {"declared": expected, "recomputed": value, "absolute_error": error, "relative_error": relative}
        if not np.isfinite(expected) or not np.isfinite(value) or (relative > 1.0e-12 and error > 1.0e-14):
            failures.append(field)
    return {"status": "PASS" if not failures else "FAIL_CLOSED", "failures": failures, "comparisons": comparisons}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for stage in ("h1", "h2", "h3"):
        path = args.input / f"{stage}_tet4_primary.json"
        if not path.exists():
            rows.append({"source": path.name, "status": "NOT_RUN_OR_MISSING", "sha256": None, "failures": ["missing_raw"]})
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("status") != "PASS":
            rows.append({"source": path.name, "sha256": _sha256(path), "status": "BLOCKED_UPSTREAM_PRIMARY_FAILURE", "failures": [raw.get("failure", raw.get("status"))]})
            continue
        comparison = _compare(raw)
        rows.append({"source": path.name, "sha256": _sha256(path), "family": raw.get("family"), "stage": raw.get("stage"), **comparison})
    status = "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL_CLOSED_OR_INCOMPLETE"
    summary = {
        "status": status,
        "classification": "INDEPENDENT_OBSERVABLE_RECOMPUTATION_NOT_GLOBAL_FEM_SOLVE",
        "production_imports": [],
        "rows": rows,
        "limitations": [
            "recomputes derived observables from serialized production result arrays",
            "does not independently solve the FEM/Newton problem",
            "does not independently validate equilibrium vectors generated by production audit",
        ],
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "rows": [{"source": row["source"], "status": row["status"], "failures": row["failures"]} for row in rows]}, indent=2))
    return 0 if status == "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
