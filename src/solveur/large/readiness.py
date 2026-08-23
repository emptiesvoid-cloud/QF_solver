"""Readiness checks for large-scale TET4 qualification runs."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path
from typing import Any

from solveur.large.generator import recommended_block_for_dofs


SCIPY_DEFAULT_MAX_DOFS = 200_000
MULTI_MILLION_DOF_GATE = 2_000_000


def check_large_readiness(
    output_dir: str | Path,
    *,
    target_dofs: int = 1_000_000,
    nx: int | None = None,
    ny: int | None = None,
    nz: int | None = None,
    solver_backend: str = "petsc",
    chunk_size: int = 4096,
    scipy_max_dofs: int = SCIPY_DEFAULT_MAX_DOFS,
    memory_budget_bytes: int | None = None,
) -> dict[str, Any]:
    """Return a machine-readable readiness report for a generated large TET4 run."""
    dimensions = _dimensions(target_dofs, nx, ny, nz)
    sizing = estimate_structured_tet4_size(*dimensions)
    checks = [
        _dependency_check("h5py", required=True),
        _dependency_check("mpi4py", required=solver_backend == "petsc"),
        _dependency_check("petsc4py", required=solver_backend == "petsc"),
        _backend_scale_check(solver_backend, sizing["ndof"], scipy_max_dofs),
        _disk_check(output_dir, sizing["recommended_free_disk_bytes"]),
        _chunk_check(chunk_size),
        _multi_million_gate_check(
            target_dofs,
            solver_backend,
            sizing,
            memory_budget_bytes,
        ),
    ]
    status = _overall_status(checks)
    report = {
        "status": status,
        "target_dofs": int(target_dofs),
        "backend": solver_backend,
        "memory_budget_bytes": int(memory_budget_bytes) if memory_budget_bytes is not None else None,
        "dimensions": {"nx": dimensions[0], "ny": dimensions[1], "nz": dimensions[2]},
        "sizing": sizing,
        "checks": checks,
    }
    return report


def estimate_structured_tet4_size(nx: int, ny: int, nz: int) -> dict[str, Any]:
    """Estimate model size and backend memory scale for a generated TET4 block."""
    if min(nx, ny, nz) <= 0:
        raise ValueError("Block dimensions nx, ny and nz must be positive.")
    node_count = (nx + 1) * (ny + 1) * (nz + 1)
    element_count = 6 * nx * ny * nz
    ndof = 3 * node_count
    model_arrays = 8 * (3 * node_count + 4 * element_count + element_count + ndof)
    displacement = 8 * ndof
    chunk_triplets = 24 * 144 * min(element_count, max(1, 4096))
    scipy_upper = model_arrays + displacement + 24 * 144 * element_count
    petsc_rule_of_thumb = model_arrays + displacement + 16 * 120 * ndof
    return {
        "node_count": int(node_count),
        "element_count": int(element_count),
        "ndof": int(ndof),
        "model_arrays_bytes": int(model_arrays),
        "displacement_bytes": int(displacement),
        "scipy_sparse_upper_bound_bytes": int(scipy_upper),
        "petsc_rule_of_thumb_bytes": int(petsc_rule_of_thumb),
        "chunk_triplet_bytes_at_default_chunk": int(chunk_triplets),
        "recommended_free_disk_bytes": int(4 * (model_arrays + displacement)),
    }


def write_large_readiness_report(report: dict[str, Any], output_dir: str | Path) -> dict[str, Path]:
    """Write JSON and Markdown readiness reports."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "large_readiness.json"
    md_path = root / "large_readiness.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def _dimensions(target_dofs: int, nx: int | None, ny: int | None, nz: int | None) -> tuple[int, int, int]:
    values = (nx, ny, nz)
    if all(value is None for value in values):
        return recommended_block_for_dofs(target_dofs)
    if any(value is None for value in values):
        raise ValueError("Provide all of nx, ny and nz, or none of them.")
    return int(nx), int(ny), int(nz)


def _dependency_check(name: str, *, required: bool) -> dict[str, str]:
    available = importlib.util.find_spec(name) is not None
    if available:
        return {"id": f"DEP-{name.upper()}", "status": "PASS", "detail": f"{name} available"}
    if not required:
        return {"id": f"DEP-{name.upper()}", "status": "PASS", "detail": f"{name} not required for selected backend"}
    return {"id": f"DEP-{name.upper()}", "status": "FAIL", "detail": f"{name} not installed"}


def _backend_scale_check(backend: str, ndof: int, scipy_max_dofs: int) -> dict[str, str]:
    if backend == "petsc":
        return {"id": "BACKEND-SCALE", "status": "PASS", "detail": "PETSc selected for scalable solve"}
    if backend == "matrix_free":
        return {"id": "BACKEND-SCALE", "status": "PASS", "detail": "matrix_free selected for generated structured block"}
    if backend != "scipy":
        return {"id": "BACKEND-SCALE", "status": "FAIL", "detail": f"unsupported backend {backend!r}"}
    if ndof > scipy_max_dofs:
        return {
            "id": "BACKEND-SCALE",
            "status": "FAIL",
            "detail": f"SciPy backend limited to {scipy_max_dofs} dofs for large mode; requested {ndof}",
        }
    return {"id": "BACKEND-SCALE", "status": "PASS", "detail": f"SciPy allowed for ndof={ndof}"}


def _disk_check(output_dir: str | Path, required_bytes: int) -> dict[str, str]:
    root = Path(output_dir)
    probe = root
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    if not probe.exists():
        return {
            "id": "DISK-FREE",
            "status": "FAIL",
            "detail": f"no existing parent found for output directory {root}",
        }
    usage = shutil.disk_usage(probe)
    if usage.free < required_bytes:
        return {
            "id": "DISK-FREE",
            "status": "FAIL",
            "detail": f"free={usage.free} bytes, recommended={required_bytes} bytes",
        }
    return {"id": "DISK-FREE", "status": "PASS", "detail": f"free={usage.free} bytes"}


def _chunk_check(chunk_size: int) -> dict[str, str]:
    if chunk_size <= 0:
        return {"id": "CHUNK-SIZE", "status": "FAIL", "detail": "chunk_size must be positive"}
    if chunk_size > 100_000:
        return {"id": "CHUNK-SIZE", "status": "WARNING", "detail": f"large chunk_size={chunk_size}"}
    return {"id": "CHUNK-SIZE", "status": "PASS", "detail": f"chunk_size={chunk_size}"}


def _multi_million_gate_check(
    target_dofs: int,
    backend: str,
    sizing: dict[str, Any],
    memory_budget_bytes: int | None,
) -> dict[str, str]:
    """Guard campaigns whose target is in the multi-million-DOF range."""
    if target_dofs < MULTI_MILLION_DOF_GATE:
        return {
            "id": "MULTI-MILLION-GATE",
            "status": "PASS",
            "detail": f"not applicable below {MULTI_MILLION_DOF_GATE} target dofs",
        }
    if backend not in {"petsc", "matrix_free"}:
        return {
            "id": "MULTI-MILLION-GATE",
            "status": "FAIL",
            "detail": "multi-million-DOF campaigns require PETSc or matrix_free",
        }
    required = int(sizing["petsc_rule_of_thumb_bytes"])
    if memory_budget_bytes is None:
        return {
            "id": "MULTI-MILLION-GATE",
            "status": "WARNING",
            "detail": f"explicit memory budget required; indicative requirement={required} bytes",
        }
    if memory_budget_bytes < required:
        return {
            "id": "MULTI-MILLION-GATE",
            "status": "FAIL",
            "detail": f"memory budget={memory_budget_bytes} bytes below indicative requirement={required} bytes",
        }
    return {
        "id": "MULTI-MILLION-GATE",
        "status": "PASS",
        "detail": f"backend={backend}, budget={memory_budget_bytes} bytes, indicative requirement={required} bytes",
    }


def _overall_status(checks: list[dict[str, str]]) -> str:
    statuses = {item["status"] for item in checks}
    if "FAIL" in statuses:
        return "FAIL"
    if "WARNING" in statuses:
        return "WARNING"
    return "PASS"


def _markdown(report: dict[str, Any]) -> str:
    sizing = report["sizing"]
    lines = [
        "# Readiness grand modele",
        "",
        f"Statut: **{report['status']}**",
        "",
        f"- Backend: `{report['backend']}`",
        f"- DDL cible: {report['target_dofs']}",
        f"- Budget mémoire explicite: {report.get('memory_budget_bytes') or 'non fourni'} octets",
        f"- DDL estime: {sizing['ndof']}",
        f"- Noeuds estimes: {sizing['node_count']}",
        f"- Elements estimes: {sizing['element_count']}",
        f"- Memoire PETSc indicative: {sizing['petsc_rule_of_thumb_bytes']} octets",
        f"- Borne haute SciPy indicative: {sizing['scipy_sparse_upper_bound_bytes']} octets",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {item['id']}: **{item['status']}** - {item['detail']}" for item in report["checks"])
    lines.append("")
    return "\n".join(lines)
