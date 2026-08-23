"""Compare two archived assembly-scaling reports without exposing host data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def compare_reports(
    baseline_path: Path,
    candidate_path: Path,
    output: Path | None = None,
) -> dict[str, object]:
    """Compare numerical invariants and median timings by assembled DDL size."""
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    base_rows = {int(row["dofs"]): row for row in baseline["sizes"]}
    candidate_rows = {int(row["dofs"]): row for row in candidate["sizes"]}
    if set(base_rows) != set(candidate_rows):
        raise ValueError("baseline and candidate must contain the same DDL sizes")

    rows: list[dict[str, object]] = []
    for dofs in sorted(base_rows):
        before = base_rows[dofs]
        after = candidate_rows[dofs]
        if before["nnz"] != after["nnz"] or before["elements"] != after["elements"]:
            raise ValueError(f"assembly invariant changed at {dofs} DDL")
        before_time = float(before["assembly_seconds"])
        after_time = float(after["assembly_seconds"])
        phase_before = before["assembly_diagnostics"]["assembly_phase_seconds"]
        phase_after = after["assembly_diagnostics"]["assembly_phase_seconds"]
        common_phases = sorted(set(phase_before) & set(phase_after))
        rows.append(
            {
                "dofs": dofs,
                "elements": int(after["elements"]),
                "nnz": int(after["nnz"]),
                "baseline_seconds": before_time,
                "candidate_seconds": after_time,
                "relative_time_change": (after_time - before_time) / before_time,
                "phase_relative_changes": {
                    name: (float(phase_after[name]) - float(phase_before[name])) / float(phase_before[name])
                    for name in common_phases
                    if float(phase_before[name]) > 0.0
                },
                "candidate_conversion_method": after["assembly_diagnostics"].get("sparse_conversion_method"),
            }
        )
    relative_changes = [float(row["relative_time_change"]) for row in rows]
    result = {
        "schema_version": 1,
        "campaign": "qf-solver-tet4-assembly-scaling-comparison-0.2.2-alpha",
        "environment": "local reproducibility comparison; host identity intentionally omitted",
        "baseline": baseline_path.name,
        "candidate": candidate_path.name,
        "numerical_identity": "PASS",
        "max_absolute_relative_time_change": max(abs(value) for value in relative_changes),
        "median_relative_time_change": sorted(relative_changes)[len(relative_changes) // 2],
        "performance_interpretation": (
            "material_improvement"
            if sorted(relative_changes)[len(relative_changes) // 2] <= -0.05
            else "no_material_change"
        ),
        "sizes": rows,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(compare_reports(args.baseline, args.candidate, args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
