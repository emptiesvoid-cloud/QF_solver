"""Large-scale TET4 qualification pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from solveur.io.evidence_verifier import EvidenceBundleVerifier
from solveur.large.benchmark import benchmark_large_model
from solveur.large.evidence import write_large_manifest
from solveur.large.generator import generate_tet4_block, recommended_block_for_dofs
from solveur.large.readiness import check_large_readiness, write_large_readiness_report
from solveur.large.runtime import write_runtime_environment


def qualify_large_tet4_pipeline(
    output_dir: str | Path,
    *,
    target_dofs: int = 1_000_000,
    nx: int | None = None,
    ny: int | None = None,
    nz: int | None = None,
    solver_backend: str = "petsc",
    preconditioner: str | None = None,
    chunk_size: int = 4096,
    length: float = 1.0,
    height: float = 1.0,
    depth: float = 1.0,
    young: float = 210.0e9,
    poisson: float = 0.3,
    density: float = 7800.0,
    total_load: float = 1000.0,
) -> dict[str, Any]:
    """Generate, solve, audit, benchmark and verify a large TET4 qualification case."""
    if target_dofs <= 0:
        raise ValueError("target_dofs must be positive.")
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    dimensions = _dimensions(target_dofs, nx, ny, nz)
    runtime_path = write_runtime_environment(
        root,
        {
            "kind": "large_tet4_qualification",
            "target_dofs": int(target_dofs),
            "dimensions": {"nx": dimensions[0], "ny": dimensions[1], "nz": dimensions[2]},
            "backend": solver_backend,
            "chunk_size": int(chunk_size),
        },
    )
    readiness = check_large_readiness(
        root,
        target_dofs=target_dofs,
        nx=dimensions[0],
        ny=dimensions[1],
        nz=dimensions[2],
        solver_backend=solver_backend,
        chunk_size=chunk_size,
    )
    readiness_paths = write_large_readiness_report(readiness, root)
    if readiness["status"] == "FAIL":
        summary = _readiness_failed_summary(
            root,
            target_dofs,
            dimensions,
            solver_backend,
            readiness,
            readiness_paths,
            runtime_path,
        )
        return summary
    model_path = root / "qualification_model.h5"
    model = generate_tet4_block(
        model_path,
        nx=dimensions[0],
        ny=dimensions[1],
        nz=dimensions[2],
        length=length,
        height=height,
        depth=depth,
        young=young,
        poisson=poisson,
        density=density,
        total_load=total_load,
    )
    benchmark_dir = root / "benchmark"
    benchmark = benchmark_large_model(
        model_path,
        benchmark_dir,
        solver_backend=solver_backend,
        preconditioner=preconditioner,
        chunk_size=chunk_size,
    )
    checks = _checks(target_dofs, model.ndof, benchmark, readiness)
    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    summary = {
        "status": status,
        "target_dofs": int(target_dofs),
        "actual_dofs": int(model.ndof),
        "dimensions": {"nx": dimensions[0], "ny": dimensions[1], "nz": dimensions[2]},
        "node_count": model.node_count,
        "element_count": model.element_count,
        "backend": benchmark.get("backend", solver_backend),
        "readiness": readiness,
        "readiness_report": {name: str(path) for name, path in readiness_paths.items()},
        "runtime_environment": runtime_path.name,
        "model_path": str(model_path),
        "benchmark_dir": str(benchmark_dir),
        "benchmark_summary": str(benchmark_dir / "benchmark_large.json"),
        "evidence_manifest": benchmark.get("evidence_manifest", ""),
        "qualification_manifest": str(root / "evidence_manifest.json"),
        "checks": checks,
        "benchmark": benchmark,
    }
    summary_path = root / "large_qualification_summary.json"
    markdown_path = root / "large_qualification_summary.md"
    summary["summary_path"] = str(summary_path)
    summary["markdown_path"] = str(markdown_path)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    markdown_path.write_text(_markdown(summary), encoding="utf-8")
    manifest_path = write_large_manifest(
        root,
        {
            "kind": "large_tet4_qualification",
            "target_dofs": int(target_dofs),
            "actual_dofs": int(model.ndof),
            "backend": benchmark.get("backend", solver_backend),
        },
    )
    verification = EvidenceBundleVerifier().verify(manifest_path)
    return {**summary, "qualification_evidence_verification": verification.to_dict()}


def _dimensions(target_dofs: int, nx: int | None, ny: int | None, nz: int | None) -> tuple[int, int, int]:
    values = (nx, ny, nz)
    if all(value is None for value in values):
        return recommended_block_for_dofs(target_dofs)
    if any(value is None for value in values):
        raise ValueError("Provide all of nx, ny and nz, or none of them.")
    dims = int(nx), int(ny), int(nz)
    if min(dims) <= 0:
        raise ValueError("Block dimensions nx, ny and nz must be positive.")
    return dims


def _readiness_failed_summary(
    root: Path,
    target_dofs: int,
    dimensions: tuple[int, int, int],
    solver_backend: str,
    readiness: dict[str, Any],
    readiness_paths: dict[str, Path],
    runtime_path: Path,
) -> dict[str, Any]:
    summary_path = root / "large_qualification_summary.json"
    markdown_path = root / "large_qualification_summary.md"
    checks = [
        _check("LRG-READINESS-PASS", False, f"readiness={readiness['status']}"),
        *_readiness_checks(readiness),
    ]
    summary: dict[str, Any] = {
        "status": "FAIL",
        "stage": "readiness",
        "target_dofs": int(target_dofs),
        "actual_dofs": int(readiness["sizing"]["ndof"]),
        "dimensions": {"nx": dimensions[0], "ny": dimensions[1], "nz": dimensions[2]},
        "node_count": int(readiness["sizing"]["node_count"]),
        "element_count": int(readiness["sizing"]["element_count"]),
        "backend": solver_backend,
        "readiness": readiness,
        "readiness_report": {name: str(path) for name, path in readiness_paths.items()},
        "runtime_environment": runtime_path.name,
        "model_path": "",
        "benchmark_dir": "",
        "benchmark_summary": "",
        "evidence_manifest": "",
        "qualification_manifest": str(root / "evidence_manifest.json"),
        "checks": checks,
        "summary_path": str(summary_path),
        "markdown_path": str(markdown_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    markdown_path.write_text(_markdown(summary), encoding="utf-8")
    manifest_path = write_large_manifest(
        root,
        {
            "kind": "large_tet4_qualification_readiness_failure",
            "target_dofs": int(target_dofs),
            "actual_dofs": int(readiness["sizing"]["ndof"]),
            "backend": solver_backend,
        },
    )
    verification = EvidenceBundleVerifier().verify(manifest_path)
    return {**summary, "qualification_evidence_verification": verification.to_dict()}


def _checks(
    target_dofs: int,
    actual_dofs: int,
    benchmark: dict[str, Any],
    readiness: dict[str, Any],
) -> list[dict[str, Any]]:
    evidence = dict(benchmark.get("evidence_verification", {}))
    policy = dict(benchmark.get("artifact_policy", {}))
    return [
        _check("LRG-READINESS-PASS", readiness["status"] in {"PASS", "WARNING"}, f"readiness={readiness['status']}"),
        *_readiness_checks(readiness),
        _check(
            "LRG-TARGET-DOFS",
            actual_dofs >= target_dofs,
            f"actual_dofs={actual_dofs}, target_dofs={target_dofs}",
        ),
        _check("LRG-BENCHMARK-PASS", benchmark.get("status") == "PASS", f"status={benchmark.get('status')}"),
        _check("LRG-AUDIT-PASS", benchmark.get("audit_status") == "PASS", f"audit={benchmark.get('audit_status')}"),
        _check("LRG-EVIDENCE-PASS", evidence.get("status") == "PASS", f"evidence={evidence.get('status')}"),
        _check(
            "LRG-FILE-BACKED-DISPLACEMENTS",
            bool(policy.get("file_backed_displacements")),
            str(policy.get("displacement_output", "")),
        ),
        _check(
            "LRG-NO-DISPLACEMENT-JSON",
            not bool(policy.get("monolithic_displacements_in_json")),
            f"offenders={policy.get('offending_json_files', [])}",
        ),
    ]


def _readiness_checks(readiness: dict[str, Any]) -> list[dict[str, str]]:
    return [
        _check(f"READINESS-{item['id']}", item["status"] != "FAIL", item["detail"])
        for item in readiness.get("checks", [])
    ]


def _check(identifier: str, condition: bool, detail: str) -> dict[str, str]:
    return {"id": identifier, "status": "PASS" if condition else "FAIL", "detail": detail}


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Qualification grand modele TET4",
        "",
        f"Statut: **{summary['status']}**",
        "",
        f"- Backend: `{summary['backend']}`",
        f"- DDL cible: {summary['target_dofs']}",
        f"- DDL obtenu: {summary['actual_dofs']}",
        f"- Noeuds: {summary['node_count']}",
        f"- Elements: {summary['element_count']}",
        f"- Environnement runtime: `{summary.get('runtime_environment', '')}`",
        f"- Modele: `{summary['model_path']}`",
        f"- Benchmark: `{summary['benchmark_summary']}`",
        f"- Manifest preuve: `{summary['evidence_manifest']}`",
        f"- Manifest qualification: `{summary['qualification_manifest']}`",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {item['id']}: **{item['status']}** - {item['detail']}" for item in summary["checks"])
    lines.append("")
    return "\n".join(lines)
