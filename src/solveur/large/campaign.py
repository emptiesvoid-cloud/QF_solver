"""Multi-scale qualification campaign for large structured TET4 models."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from solveur.core.errors import SolverError
from solveur.io.evidence_verifier import EvidenceBundleVerifier
from solveur.io.manifest import write_json_file
from solveur.large.evidence import write_large_manifest
from solveur.large.qualification import qualify_large_tet4_pipeline
from solveur.large.readiness import check_large_readiness, write_large_readiness_report
from solveur.large.runtime import write_runtime_environment

DEFAULT_LARGE_CAMPAIGN_TARGETS = (100_000, 1_000_000, 3_000_000)


def run_large_scale_campaign(
    output_dir: str | Path,
    *,
    targets: Sequence[int] = DEFAULT_LARGE_CAMPAIGN_TARGETS,
    solver_backend: str = "petsc",
    preconditioner: str | None = None,
    chunk_size: int = 4096,
    memory_budget_bytes: int | None = None,
    execute: bool = False,
    stop_on_failure: bool = True,
) -> dict[str, Any]:
    """Plan or execute an ordered large-scale campaign and aggregate evidence."""
    normalized_targets = _validated_targets(targets)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    runtime = write_runtime_environment(
        root,
        {
            "kind": "large_scale_campaign",
            "targets": list(normalized_targets),
            "backend": solver_backend,
            "execute": bool(execute),
            "chunk_size": int(chunk_size),
        },
    )
    stages: list[dict[str, Any]] = []
    halted = False
    for target in normalized_targets:
        stage_dir = root / f"dofs_{target}"
        stage_dir.mkdir(parents=True, exist_ok=True)
        readiness = check_large_readiness(
            stage_dir,
            target_dofs=target,
            solver_backend=solver_backend,
            chunk_size=chunk_size,
            memory_budget_bytes=memory_budget_bytes,
        )
        readiness_paths = write_large_readiness_report(readiness, stage_dir)
        stage = _planned_stage(target, stage_dir, readiness, readiness_paths)
        if halted:
            stage["status"] = "NOT_RUN"
            stage["reason"] = "campaign stopped after previous failure"
        elif readiness["status"] == "FAIL":
            stage["status"] = "BLOCKED"
            stage["reason"] = "readiness failed"
            halted = bool(execute and stop_on_failure)
        elif execute:
            stage = _execute_stage(
                stage,
                solver_backend=solver_backend,
                preconditioner=preconditioner,
                chunk_size=chunk_size,
                memory_budget_bytes=memory_budget_bytes,
            )
            halted = bool(stage["status"] != "PASS" and stop_on_failure)
        stages.append(stage)
    status = _campaign_status(stages, execute)
    summary: dict[str, Any] = {
        "campaign_schema_version": 1,
        "status": status,
        "mode": "execute" if execute else "plan_only",
        "backend": solver_backend,
        "preconditioner": preconditioner or ("gamg" if solver_backend == "petsc" else "jacobi"),
        "chunk_size": int(chunk_size),
        "memory_budget_bytes": int(memory_budget_bytes) if memory_budget_bytes is not None else None,
        "targets": list(normalized_targets),
        "runtime_environment": runtime.name,
        "scaling_interpretation": "size_scaling_single_configuration",
        "strong_scaling_measured": False,
        "weak_scaling_measured": False,
        "stages": stages,
        "scaling": _scaling_records(stages),
        "manifest": str(root / "evidence_manifest.json"),
    }
    json_path = root / "large_campaign.json"
    markdown_path = root / "large_campaign.md"
    summary["json_report"] = str(json_path)
    summary["markdown_report"] = str(markdown_path)
    write_json_file(json_path, summary)
    markdown_path.write_text(_markdown(summary), encoding="utf-8")
    manifest = write_large_manifest(
        root,
        {
            "kind": "large_scale_campaign",
            "mode": summary["mode"],
            "backend": solver_backend,
            "targets": list(normalized_targets),
            "status": status,
        },
    )
    evidence = EvidenceBundleVerifier().verify(manifest)
    return {**summary, "evidence_verification": evidence.to_dict()}


def _validated_targets(targets: Sequence[int]) -> tuple[int, ...]:
    values = tuple(int(value) for value in targets)
    if not values:
        raise ValueError("Large campaign requires at least one target dof count.")
    if any(value <= 0 for value in values):
        raise ValueError("Large campaign targets must be positive.")
    if any(right <= left for left, right in zip(values, values[1:])):
        raise ValueError("Large campaign targets must be strictly increasing and unique.")
    return values


def _planned_stage(
    target: int,
    stage_dir: Path,
    readiness: dict[str, Any],
    readiness_paths: dict[str, Path],
) -> dict[str, Any]:
    sizing = readiness["sizing"]
    return {
        "target_dofs": int(target),
        "actual_dofs": int(sizing["ndof"]),
        "node_count": int(sizing["node_count"]),
        "element_count": int(sizing["element_count"]),
        "dimensions": readiness["dimensions"],
        "status": "READY" if readiness["status"] != "FAIL" else "BLOCKED",
        "reason": "not executed" if readiness["status"] != "FAIL" else "readiness failed",
        "readiness_status": readiness["status"],
        "readiness_checks": readiness["checks"],
        "readiness_reports": {name: str(path) for name, path in readiness_paths.items()},
        "estimated_memory_bytes": {
            "model_arrays": int(sizing["model_arrays_bytes"]),
            "petsc_rule_of_thumb": int(sizing["petsc_rule_of_thumb_bytes"]),
            "scipy_upper_bound": int(sizing["scipy_sparse_upper_bound_bytes"]),
        },
        "output_dir": str(stage_dir),
        "qualification_summary": "",
        "metrics": {},
    }


def _execute_stage(
    stage: dict[str, Any],
    *,
    solver_backend: str,
    preconditioner: str | None,
    chunk_size: int,
    memory_budget_bytes: int | None,
) -> dict[str, Any]:
    try:
        result = qualify_large_tet4_pipeline(
            stage["output_dir"],
            target_dofs=stage["target_dofs"],
            solver_backend=solver_backend,
            preconditioner=preconditioner,
            chunk_size=chunk_size,
            memory_budget_bytes=memory_budget_bytes,
        )
    except (SolverError, ImportError, OSError, ValueError) as exc:
        return {**stage, "status": "FAIL", "reason": f"{type(exc).__name__}: {exc}"}
    benchmark = dict(result.get("benchmark", {}))
    solver = dict(benchmark.get("solver", {}))
    memory = dict(benchmark.get("memory_telemetry", {}))
    pipeline_time = float(benchmark.get("solve_pipeline_time_seconds", 0.0))
    element_count = int(result.get("element_count", stage["element_count"]))
    metrics = {
        "load_time_seconds": benchmark.get("load_time_seconds"),
        "assembly_time_seconds": benchmark.get("assembly_time_seconds"),
        "solve_time_seconds": benchmark.get("solve_time_seconds"),
        "pipeline_time_seconds": pipeline_time,
        "iterations": solver.get("iterations"),
        "residual_norm": solver.get("residual_norm"),
        "process_peak_rss_bytes": memory.get("process_peak_rss_bytes"),
        "python_peak_bytes": memory.get("python_tracemalloc_peak_bytes"),
        "elements_per_second": element_count / pipeline_time if pipeline_time > 0.0 else None,
        "dofs_per_second": int(result.get("actual_dofs", stage["actual_dofs"])) / pipeline_time
        if pipeline_time > 0.0
        else None,
    }
    return {
        **stage,
        "status": "PASS" if result.get("status") == "PASS" else "FAIL",
        "reason": "executed" if result.get("status") == "PASS" else "qualification pipeline failed",
        "actual_dofs": int(result.get("actual_dofs", stage["actual_dofs"])),
        "node_count": int(result.get("node_count", stage["node_count"])),
        "element_count": element_count,
        "qualification_summary": str(result.get("summary_path", "")),
        "metrics": metrics,
    }


def _campaign_status(stages: list[dict[str, Any]], execute: bool) -> str:
    statuses = {str(stage["status"]) for stage in stages}
    if not execute:
        return "BLOCKED" if "BLOCKED" in statuses else "PLANNED"
    if statuses == {"PASS"}:
        return "PASS"
    if "PASS" in statuses:
        return "PARTIAL"
    return "BLOCKED" if "BLOCKED" in statuses else "FAIL"


def _scaling_records(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    executed = [stage for stage in stages if stage["status"] == "PASS" and stage["metrics"]]
    records: list[dict[str, Any]] = []
    for previous, current in zip(executed, executed[1:]):
        previous_time = float(previous["metrics"]["pipeline_time_seconds"])
        current_time = float(current["metrics"]["pipeline_time_seconds"])
        records.append(
            {
                "from_dofs": previous["actual_dofs"],
                "to_dofs": current["actual_dofs"],
                "dof_ratio": current["actual_dofs"] / previous["actual_dofs"],
                "pipeline_time_ratio": current_time / previous_time if previous_time > 0.0 else None,
                "throughput_ratio": _ratio(
                    current["metrics"].get("dofs_per_second"),
                    previous["metrics"].get("dofs_per_second"),
                ),
            }
        )
    return records


def _ratio(numerator: object, denominator: object) -> float | None:
    if numerator is None or denominator is None or float(denominator) == 0.0:
        return None
    return float(numerator) / float(denominator)


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Campagne grands modeles TET4",
        "",
        f"Statut: **{summary['status']}**",
        "",
        f"- Mode: `{summary['mode']}`",
        f"- Backend: `{summary['backend']}`",
        f"- Preconditionneur: `{summary['preconditioner']}`",
        f"- Taille de bloc: {summary['chunk_size']}",
        f"- Budget mémoire explicite [octets]: {summary.get('memory_budget_bytes') or 'non fourni'}",
        "- Interpretation: campagne de taille sur une configuration; ce rapport ne revendique pas une scalabilite forte/faible.",
        "",
        "| Cible DDL | DDL estimes/reels | Elements | Statut | Temps pipeline [s] | Iterations | Residu | Pic RSS [octets] |",
        "| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for stage in summary["stages"]:
        metrics = stage["metrics"]
        lines.append(
            "| {target} | {actual} | {elements} | {status} | {time} | {iterations} | {residual} | {rss} |".format(
                target=stage["target_dofs"],
                actual=stage["actual_dofs"],
                elements=stage["element_count"],
                status=stage["status"],
                time=_display(metrics.get("pipeline_time_seconds")),
                iterations=_display(metrics.get("iterations")),
                residual=_display(metrics.get("residual_norm")),
                rss=_display(metrics.get("process_peak_rss_bytes")),
            )
        )
    lines.extend(["", "## Limites", ""])
    if summary["mode"] == "plan_only":
        lines.append("Aucun calcul n'a ete execute. Les tailles et memoires sont des estimations de readiness.")
    lines.append("La scalabilite forte/faible exige plusieurs nombres de rangs MPI et reste a mesurer separement.")
    lines.append("")
    return "\n".join(lines)


def _display(value: object) -> str:
    if value is None:
        return "non execute"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)
