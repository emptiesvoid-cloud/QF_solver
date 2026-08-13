"""Analyze PETSc preconditioner tuning runs across several model topologies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from solveur.io.evidence_verifier import EvidenceBundleVerifier
from solveur.io.manifest import sha256, write_json_file
from solveur.large.evidence import write_large_manifest
from solveur.large.optimization import _binary_relative_error

PETSC_TUNING_PRESETS: dict[str, dict[str, Any]] = {
    "gamg-default": {"preconditioner": "gamg", "petsc_options": {}},
    "gamg-threshold-001": {
        "preconditioner": "gamg",
        "petsc_options": {"pc_gamg_threshold": 0.01},
    },
    "gamg-threshold-005": {
        "preconditioner": "gamg",
        "petsc_options": {"pc_gamg_threshold": 0.05},
    },
    "hypre-default": {"preconditioner": "hypre", "petsc_options": {}},
    "hypre-hmis-exti": {
        "preconditioner": "hypre",
        "petsc_options": {
            "pc_hypre_boomeramg_strong_threshold": 0.5,
            "pc_hypre_boomeramg_coarsen_type": "HMIS",
            "pc_hypre_boomeramg_interp_type": "ext+i",
        },
    },
}


def analyze_petsc_tuning(
    benchmark_paths: Sequence[str | Path],
    output_dir: str | Path,
    *,
    topologies: Sequence[str],
    presets: Sequence[str],
    displacement_tolerance: float = 1.0e-8,
) -> dict[str, Any]:
    """Compare independently executed PETSc tuning runs."""
    paths = tuple(Path(path) for path in benchmark_paths)
    topology_names = tuple(str(value).strip() for value in topologies)
    preset_names = tuple(str(value).strip().lower() for value in presets)
    if not paths or len(paths) != len(topology_names) or len(paths) != len(preset_names):
        raise ValueError("Inputs, topologies and presets must be non-empty and have the same length.")
    if not 0.0 < displacement_tolerance < 1.0:
        raise ValueError("Displacement tolerance must be in (0, 1).")
    unknown = sorted(set(preset_names) - set(PETSC_TUNING_PRESETS))
    if unknown:
        raise ValueError(f"Unknown PETSc tuning presets: {', '.join(unknown)}")
    records = [
        _tuning_record(path, topology, preset)
        for path, topology, preset in zip(paths, topology_names, preset_names, strict=True)
    ]
    topology_order = tuple(dict.fromkeys(topology_names))
    for topology in topology_order:
        _add_displacement_errors(records, topology)
    best = {topology: _best_record(records, topology, displacement_tolerance) for topology in topology_order}
    accepted = all(
        record["status"] == "PASS"
        and record["evidence_status"] == "PASS"
        and record["relative_displacement_error"] <= displacement_tolerance
        for record in records
    )
    default_change = _default_change_recommended(records, topology_order, best)
    summary = {
        "tuning_schema_version": 1,
        "status": "PASS" if accepted else "FAIL",
        "kind": "petsc_multi_topology_tuning",
        "displacement_tolerance": float(displacement_tolerance),
        "topologies": list(topology_order),
        "presets": {name: PETSC_TUNING_PRESETS[name] for name in dict.fromkeys(preset_names)},
        "runs": records,
        "best_by_topology": best,
        "default_policy_change_recommended": default_change,
        "conclusion": _conclusion(best, default_change),
    }
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    write_json_file(root / "petsc_tuning_comparison.json", summary)
    (root / "petsc_tuning_comparison.md").write_text(_tuning_markdown(summary), encoding="utf-8")
    manifest = write_large_manifest(root, {"kind": summary["kind"], "status": summary["status"]})
    return {**summary, "evidence_manifest": str(manifest)}


def _tuning_record(path: Path, topology: str, preset: str) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    solver = dict(data.get("solver", {}))
    memory = dict(data.get("memory_telemetry", {}))
    evidence_path = path.parent / "evidence_manifest.json"
    evidence_status = EvidenceBundleVerifier().verify(evidence_path).status if evidence_path.is_file() else "MISSING"
    return {
        "topology": topology,
        "preset": preset,
        "configuration": PETSC_TUNING_PRESETS[preset],
        "benchmark": str(path),
        "benchmark_sha256": sha256(path),
        "evidence_status": evidence_status,
        "status": str(data.get("status", "FAIL")),
        "dofs": int(data.get("ndof", 0)),
        "elements": int(data.get("element_count", 0)),
        "ranks": int(dict(data.get("mpi", {})).get("size", 1)),
        "pipeline_time_seconds": float(data.get("solve_pipeline_time_seconds", 0.0)),
        "assembly_time_seconds": float(data.get("assembly_time_seconds", 0.0)),
        "solve_time_seconds": float(data.get("solve_time_seconds", 0.0)),
        "ksp_setup_time_seconds": solver.get("setup_time_seconds"),
        "ksp_iteration_time_seconds": solver.get("iteration_time_seconds"),
        "iterations": solver.get("iterations"),
        "residual_norm": solver.get("residual_norm"),
        "peak_rss_per_rank_bytes": memory.get("process_peak_rss_bytes"),
        "relative_displacement_error": None,
    }


def _add_displacement_errors(records: list[dict[str, Any]], topology: str) -> None:
    selected = [record for record in records if record["topology"] == topology]
    reference = next((record for record in selected if record["preset"] == "gamg-default"), selected[0])
    reference_path = Path(reference["benchmark"]).parent / "displacements.bin"
    for record in selected:
        candidate = Path(record["benchmark"]).parent / "displacements.bin"
        record["relative_displacement_error"] = _binary_relative_error(reference_path, candidate)


def _best_record(records: list[dict[str, Any]], topology: str, tolerance: float) -> dict[str, Any]:
    candidates = [
        record
        for record in records
        if record["topology"] == topology
        and record["status"] == "PASS"
        and record["relative_displacement_error"] <= tolerance
    ]
    if not candidates:
        return {"preset": None, "pipeline_time_seconds": None, "speedup_vs_gamg_default": None}
    best = min(candidates, key=lambda record: record["pipeline_time_seconds"])
    default = next((record for record in candidates if record["preset"] == "gamg-default"), None)
    speedup = default["pipeline_time_seconds"] / best["pipeline_time_seconds"] if default is not None else None
    return {
        "preset": best["preset"],
        "pipeline_time_seconds": best["pipeline_time_seconds"],
        "speedup_vs_gamg_default": speedup,
    }


def _default_change_recommended(
    records: list[dict[str, Any]], topologies: tuple[str, ...], best: dict[str, dict[str, Any]]
) -> bool:
    presets = {best[topology]["preset"] for topology in topologies}
    if len(presets) != 1 or None in presets or presets == {"gamg-default"}:
        return False
    candidate = next(iter(presets))
    for topology in topologies:
        default = next(
            record for record in records if record["topology"] == topology and record["preset"] == "gamg-default"
        )
        tuned = next(record for record in records if record["topology"] == topology and record["preset"] == candidate)
        if tuned["pipeline_time_seconds"] > 0.9 * default["pipeline_time_seconds"]:
            return False
        default_memory = default.get("peak_rss_per_rank_bytes")
        tuned_memory = tuned.get("peak_rss_per_rank_bytes")
        if default_memory and tuned_memory and tuned_memory > 1.2 * default_memory:
            return False
    return True


def _conclusion(best: dict[str, dict[str, Any]], default_change: bool) -> str:
    winners = ", ".join(f"{topology}={data['preset']}" for topology, data in best.items())
    if default_change:
        return f"A common preset improves every topology by at least 10% without excessive memory: {winners}."
    return f"No robust global default change is justified; retain gamg-default. Best observed presets: {winners}."


def _tuning_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Reglages PETSc multi-topologie",
        "",
        f"Statut: **{summary['status']}**",
        "",
        "| Topologie | Preset | Pipeline [s] | Setup [s] | Iterations [s] | Iter. | Pic RSS/rang | Ecart u |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for run in summary["runs"]:
        lines.append(
            f"| {run['topology']} | {run['preset']} | {_display(run['pipeline_time_seconds'])} | "
            f"{_display(run['ksp_setup_time_seconds'])} | {_display(run['ksp_iteration_time_seconds'])} | "
            f"{_display(run['iterations'])} | {_display(run['peak_rss_per_rank_bytes'])} | "
            f"{_display(run['relative_displacement_error'])} |"
        )
    lines.extend(["", "## Decision", "", summary["conclusion"], ""])
    return "\n".join(lines)


def _display(value: object) -> str:
    if value is None:
        return ""
    return f"{value:.6g}" if isinstance(value, float) else str(value)
