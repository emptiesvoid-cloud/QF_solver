"""Controlled assembly-only probes for the 026-G12 optimization lot."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from scripts.benchmark_g12_lot1 import build_model  # noqa: E402
from solveur.core.assembly.assembler import GlobalAssembler  # noqa: E402
from solveur.core.solvers.static import LinearStaticSolver  # noqa: E402

try:
    import psutil
except ImportError:  # pragma: no cover - optional measurement dependency
    psutil = None


CONTRACT_ID = "026-G12-OPTIMIZATION"
DEFAULT_TIMEOUT = 300.0
DEFAULT_MAX_RSS = 4 * 1024**3


class _TimingAssembler(GlobalAssembler):
    """Capture existing stiffness diagnostics without changing assembly."""

    def __init__(self) -> None:
        super().__init__()
        self.phase_seconds: dict[str, float] = {}
        self.stiffness_diagnostics: dict[str, Any] = {}

    def prepare_plan(self, model: Any, dofs: Any) -> Any:
        started = time.perf_counter()
        plan = super().prepare_plan(model, dofs)
        self.phase_seconds["assembly_plan"] = time.perf_counter() - started
        return plan

    def assemble_stiffness(self, model: Any, dofs: Any, *, plan: Any = None) -> Any:
        started = time.perf_counter()
        matrix = super().assemble_stiffness(model, dofs, plan=plan)
        self.phase_seconds["stiffness_assembly_route"] = time.perf_counter() - started
        self.stiffness_diagnostics = dict(self.last_diagnostics)
        return matrix


def _csr_storage_bytes(matrix: Any) -> int | None:
    if matrix is None or not all(hasattr(matrix, name) for name in ("data", "indices", "indptr")):
        return None
    return int(matrix.data.nbytes + matrix.indices.nbytes + matrix.indptr.nbytes)


def _assembly_only_case(factory: Callable[[], tuple[Any, dict[str, Any]]], label: str) -> dict[str, Any]:
    """Measure validation and stiffness assembly without loads or solve."""
    wall_started = time.perf_counter()
    model, topology = factory()
    validation_started = time.perf_counter()
    validation = LinearStaticSolver().validator.validate(model)
    validation_seconds = time.perf_counter() - validation_started
    if validation.status == "FAIL":
        return {
            "label": label,
            "status": "FAIL",
            "error_type": "MeshValidationError",
            "error": "; ".join(validation.errors),
            "mesh_validation_seconds": validation_seconds,
            "topology": topology,
        }
    dofs = model.dof_manager()
    assembler = _TimingAssembler()
    plan_started = time.perf_counter()
    plan = assembler.prepare_plan(model, dofs)
    plan_seconds = time.perf_counter() - plan_started
    assembly_started = time.perf_counter()
    stiffness = assembler.assemble_stiffness(model, dofs, plan=plan)
    assembly_seconds = time.perf_counter() - assembly_started
    phases = assembler.stiffness_diagnostics.get("assembly_phase_seconds", {})
    return {
        "label": label,
        "status": "PASS",
        "total_dofs": int(dofs.ndof),
        "node_count": model.node_count,
        "element_count": len(model.elements),
        "global_stiffness_nnz": int(stiffness.nnz),
        "global_matrix_storage_bytes": _csr_storage_bytes(stiffness),
        "mesh_validation_seconds": validation_seconds,
        "assembly_plan_seconds": plan_seconds,
        "assembly_seconds": assembly_seconds,
        "element_kernel_seconds": float(phases.get("element_kernel", 0.0)),
        "sparse_conversion_seconds": float(phases.get("chunk_sparse_conversion", 0.0)),
        "sparse_finalize_seconds": float(phases.get("sparse_finalize", 0.0)),
        "linear_solve_seconds": None,
        "wall_total_seconds": time.perf_counter() - wall_started,
        "finite_metrics": bool(np.all(np.isfinite(stiffness.data))),
        "topology": topology,
        "phase_notes": {"solve": "NOT_RUN", "loads": "NOT_RUN"},
    }


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _environment() -> dict[str, Any]:
    import scipy

    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "psutil": getattr(psutil, "__version__", None),
        "logical_cpus": os.cpu_count(),
        "ram_bytes": int(psutil.virtual_memory().total) if psutil is not None else None,
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    }


def _child(args: argparse.Namespace) -> int:
    try:
        report = _assembly_only_case(
            lambda: build_model(args.family, args.target),
            f"assembly-only {args.family} target {args.target}",
        )
    except Exception as exc:  # pragma: no cover - surfaced in parent evidence
        report = {
            "label": f"assembly-only {args.family} target {args.target}",
            "status": "FAIL",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    _write(args.output, report)
    print(json.dumps({"status": report.get("status"), "target": args.target}))
    return 0 if report.get("status") == "PASS" else 1


def _spawn(command: list[str], output: Path, timeout: float, max_rss: int) -> tuple[dict[str, Any] | None, str, int | None, str]:
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    child = psutil.Process(process.pid) if psutil is not None else None
    peak = 0
    started = time.perf_counter()
    while process.poll() is None:
        if child is not None:
            try:
                peak = max(peak, int(child.memory_info().rss))
            except psutil.Error:
                pass
        if peak >= max_rss:
            process.kill()
            stdout, stderr = process.communicate()
            return None, "RESOURCE_LIMITED", peak or None, stderr.strip() or stdout.strip() or f"RSS limit reached at {peak} bytes"
        if time.perf_counter() - started >= timeout:
            process.kill()
            stdout, stderr = process.communicate()
            return None, "RESOURCE_LIMITED", peak or None, stderr.strip() or stdout.strip() or f"timeout after {timeout:.1f} seconds"
        time.sleep(0.05)
    stdout, stderr = process.communicate()
    if output.is_file():
        try:
            return json.loads(output.read_text(encoding="utf-8")), ("PASS" if process.returncode == 0 else "FAIL"), peak or None, stderr.strip() or stdout.strip()
        except json.JSONDecodeError as exc:
            return None, "FAIL", peak or None, f"invalid child JSON: {exc}"
    return None, "FAIL", peak or None, stderr.strip() or stdout.strip()


def run_assembly_driver(output: Path, targets: tuple[int, ...], timeout: float, max_rss: int) -> dict[str, Any]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="qf_g12_assembly_") as temporary:
        for target in targets:
            child_output = Path(temporary) / f"assembly_TET4_{target}.json"
            command = [sys.executable, str(Path(__file__).resolve()), "--mode", "assembly-case", "--family", "TET4", "--target", str(target), "--output", str(child_output)]
            report, status, peak, detail = _spawn(command, child_output, timeout, max_rss)
            if report is None:
                rows.append({"family": "TET4", "target_dofs": target, "status": status, "timeout_seconds": timeout, "case_peak_rss_bytes": peak, "max_rss_bytes": max_rss, "reason": detail or "assembly child did not produce a report"})
            else:
                report.update({"family": "TET4", "target_dofs": target, "case_peak_rss_bytes": peak, "case_peak_rss_scope": "parent sampler over isolated assembly-only child"})
                rows.append(report)
            if status == "RESOURCE_LIMITED":
                break
    completed = [row for row in rows if row.get("status") == "PASS"]
    return {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "environment": _environment(),
        "status": "PASS_WITH_RESOURCE_LIMIT" if len(completed) < len(rows) else "PASS",
        "route": "linear_static",
        "probe": "assembly_only",
        "timeout_seconds": timeout,
        "max_rss_bytes": max_rss,
        "rows": rows,
        "resource_policy": {"stop_after_first_limit": True, "timeout_seconds": timeout, "max_rss_bytes": max_rss},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("assembly-case", "assembly-driver"), required=True)
    parser.add_argument("--family", default="TET4")
    parser.add_argument("--target", type=int, default=3000)
    parser.add_argument("--targets", nargs="+", type=int, default=[300000, 1000000])
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--max-rss-gb", type=float, default=4.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "assembly-case":
        return _child(args)
    _write(args.output, run_assembly_driver(args.output, tuple(args.targets), args.timeout, int(args.max_rss_gb * 1024**3)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
