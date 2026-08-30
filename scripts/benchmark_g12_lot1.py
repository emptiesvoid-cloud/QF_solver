"""Controlled 026-G12 lot-1 finite-element scaling benchmark.

This runner is verification infrastructure only.  It calls the existing
linear-static route and never changes solver settings or implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import threading
import time
import tracemalloc
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from solveur.core.model import FiniteElementModel
from solveur.core.solvers.static import LinearStaticSolver

try:
    import psutil
except ImportError:  # pragma: no cover - optional measurement dependency
    psutil = None


BASELINE_SHA = "f776bc8f0cdd56d326392efb7db8b5899a04dcdd"
CONTRACT_ID = "026-G12-LOT1"
MATERIAL = {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}
THREAD_KEYS = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS")
LOW_ORDER_TARGETS = (1_000, 3_000, 10_000, 30_000, 100_000, 300_000)
HIGH_ORDER_TARGETS = (1_000, 3_000, 10_000, 30_000)


class _RssSampler:
    def __init__(self) -> None:
        self._process = psutil.Process(os.getpid()) if psutil is not None else None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.peak = 0
        self.start = 0

    def start_sampling(self) -> None:
        if self._process is None:
            return
        self.start = int(self._process.memory_info().rss)
        self.peak = self.start
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()

    def _sample(self) -> None:
        assert self._process is not None
        while not self._stop.is_set():
            self.peak = max(self.peak, int(self._process.memory_info().rss))
            self._stop.wait(0.005)

    def stop_sampling(self) -> None:
        if self._process is None:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self.peak = max(self.peak, int(self._process.memory_info().rss))


def _grid_nodes(nx: int, ny: int, nz: int) -> np.ndarray:
    axes = np.meshgrid(
        np.linspace(0.0, 1.0, nx + 1),
        np.linspace(0.0, 1.0, ny + 1),
        np.linspace(0.0, 1.0, nz + 1),
        indexing="ij",
    )
    return np.stack(axes, axis=-1).reshape((-1, 3))


def _grid_node_id(i: int, j: int, k: int, ny: int, nz: int) -> int:
    return (i * (ny + 1) + j) * (nz + 1) + k


def _hex8_cells(nx: int, ny: int, nz: int) -> list[list[int]]:
    cells: list[list[int]] = []
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                def c(di: int, dj: int, dk: int) -> int:
                    return _grid_node_id(i + di, j + dj, k + dk, ny, nz)

                cells.append([c(0, 0, 0), c(1, 0, 0), c(1, 1, 0), c(0, 1, 0), c(0, 0, 1), c(1, 0, 1), c(1, 1, 1), c(0, 1, 1)])
    return cells


def _tet4_cells(nx: int, ny: int, nz: int) -> list[list[int]]:
    cells: list[list[int]] = []
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                def c(di: int, dj: int, dk: int) -> int:
                    return _grid_node_id(i + di, j + dj, k + dk, ny, nz)

                cube = [c(0, 0, 0), c(1, 0, 0), c(0, 1, 0), c(1, 1, 0), c(0, 0, 1), c(1, 0, 1), c(0, 1, 1), c(1, 1, 1)]
                cells.extend([[cube[q] for q in tet] for tet in ((0, 1, 3, 7), (0, 3, 2, 7), (0, 2, 6, 7), (0, 6, 4, 7), (0, 4, 5, 7), (0, 5, 1, 7))])
    return cells


def _connected_model(family: str, target_dofs: int) -> tuple[FiniteElementModel, dict[str, Any]]:
    cells_per_axis = max(1, int(np.ceil((target_dofs / 3.0) ** (1.0 / 3.0))) - 1)
    while 3 * (cells_per_axis + 1) ** 3 < target_dofs:
        cells_per_axis += 1
    nodes = _grid_nodes(cells_per_axis, cells_per_axis, cells_per_axis)
    if family == "TET4":
        connectivity = _tet4_cells(cells_per_axis, cells_per_axis, cells_per_axis)
    elif family == "HEX8":
        connectivity = _hex8_cells(cells_per_axis, cells_per_axis, cells_per_axis)
    else:
        raise ValueError(f"connected builder does not support {family}")
    elements = [{"type": family, "nodes": row, "material": "solid"} for row in connectivity]
    fixed_nodes = [index for index, point in enumerate(nodes) if np.isclose(point[0], 0.0)]
    loaded_nodes = [index for index, point in enumerate(nodes) if np.isclose(point[0], 1.0)]
    fixed = [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes]
    loads = [{"node": node, "dof": "UX", "value": 1.0 / len(loaded_nodes)} for node in loaded_nodes]
    model = _make_model(nodes, elements, fixed, loads)
    return model, {"topology": "connected_structured_block", "cells_per_axis": cells_per_axis}


def _tet10_reference() -> np.ndarray:
    corners = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    edges = ((0, 1), (1, 2), (0, 2), (0, 3), (1, 3), (2, 3))
    return np.vstack([corners, [(corners[a] + corners[b]) / 2.0 for a, b in edges]])


def _hex20_reference() -> np.ndarray:
    corners = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0]])
    edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
    return np.vstack([corners, [(corners[a] + corners[b]) / 2.0 for a, b in edges]])


def _independent_high_order_model(family: str, target_dofs: int) -> tuple[FiniteElementModel, dict[str, Any]]:
    reference = _tet10_reference() if family == "TET10" else _hex20_reference()
    nodes_per_element = reference.shape[0]
    count = max(1, int(np.ceil(target_dofs / (3 * nodes_per_element))))
    nodes: list[list[float]] = []
    elements: list[dict[str, Any]] = []
    fixed: list[dict[str, Any]] = []
    loads: list[dict[str, Any]] = []
    for element_index in range(count):
        offset = np.array([2.0 * element_index, 0.0, 0.0])
        first = len(nodes)
        nodes.extend((reference + offset).tolist())
        connectivity = list(range(first, first + nodes_per_element))
        elements.append({"type": family, "nodes": connectivity, "material": "solid"})
        free_node = first + 1
        for node in connectivity:
            dofs = ["UY", "UZ"] if node == free_node else ["UX", "UY", "UZ"]
            fixed.append({"node": node, "dofs": dofs})
        loads.append({"node": free_node, "dof": "UX", "value": 1.0})
    model = _make_model(np.asarray(nodes), elements, fixed, loads)
    return model, {"topology": "independent_element_fanout", "element_count": count}


def _make_model(nodes: np.ndarray, elements: list[dict[str, Any]], fixed: list[dict[str, Any]], loads: list[dict[str, Any]]) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=np.asarray(nodes, dtype=float).tolist(),
        elements=elements,
        materials={"solid": MATERIAL},
        fixed_dofs=fixed,
        loads=loads,
        analysis={
            "type": "linear_static",
            "method": "cg",
            "parameters": {"assume_spd": True, "rtol": 1.0e-10, "atol": 0.0, "maxiter": 10000, "preconditioner": "jacobi", "backend": "scipy", "assembly_chunk_size": 256},
        },
    )


def build_model(family: str, target_dofs: int) -> tuple[FiniteElementModel, dict[str, Any]]:
    if family in {"TET4", "HEX8"}:
        return _connected_model(family, target_dofs)
    if family in {"TET10", "HEX20"}:
        return _independent_high_order_model(family, target_dofs)
    raise ValueError(f"unknown family {family}")


def _solution_checksum(values: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(values, dtype=np.float64).tobytes()).hexdigest()


def run_case(family: str, target_dofs: int, repetitions: int = 3) -> dict[str, Any]:
    measurements: list[dict[str, Any]] = []
    warmup_model, _ = build_model(family, target_dofs)
    LinearStaticSolver().solve(warmup_model, detail_level="summary")
    for repetition in range(repetitions):
        model, topology = build_model(family, target_dofs)
        sampler = _RssSampler()
        tracemalloc.start()
        sampler.start_sampling()
        started = time.perf_counter()
        result = LinearStaticSolver().solve(model, detail_level="summary")
        elapsed = time.perf_counter() - started
        sampler.stop_sampling()
        _, trace_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        execution = result.solver.get("execution", {})
        displacement = np.asarray(result.displacements, dtype=float)
        solver_info = result.solver
        fixed_count = len(LinearStaticSolver().assembler.fixed_indices(model, result.dofs))
        measurements.append({
            "repetition": repetition + 1,
            "total_dofs": int(result.ndof),
            "free_dofs": int(result.ndof - fixed_count),
            "node_count": int(result.node_count),
            "element_count": int(result.element_count),
            "nnz": int(solver_info.get("selection", {}).get("resource_estimate", {}).get("nnz", 0)),
            "assembly_seconds": float(execution.get("assembly_seconds", 0.0)),
            "linear_solve_seconds": float(execution.get("linear_solve_seconds", 0.0)),
            "total_seconds": float(execution.get("total_seconds", elapsed)),
            "peak_rss_bytes": sampler.peak or None,
            "rss_delta_bytes": (sampler.peak - sampler.start) if sampler.peak else None,
            "tracemalloc_peak_bytes": int(trace_peak),
            "solution_norm": float(np.linalg.norm(displacement)),
            "solution_checksum": _solution_checksum(displacement),
            "relative_residual_norm": float(solver_info.get("relative_residual_norm", np.nan)),
            "status": result.status,
        })
    checksums = {row["solution_checksum"] for row in measurements}
    residuals = [row["relative_residual_norm"] for row in measurements]
    finite = all(np.isfinite(row["relative_residual_norm"]) and np.isfinite(row["solution_norm"]) for row in measurements)
    return {
        "family": family,
        "target_dofs": target_dofs,
        "topology": topology,
        "measured_repetitions": measurements,
        "deterministic": len(checksums) == 1,
        "finite_metrics": finite,
        "max_relative_residual_norm": max(residuals),
    }


def _environment() -> dict[str, Any]:
    import scipy

    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "psutil": getattr(psutil, "__version__", None),
        "cpu": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "ram_bytes": int(psutil.virtual_memory().total) if psutil is not None else None,
        "thread_environment": {key: os.environ.get(key) for key in THREAD_KEYS},
        "git_head": BASELINE_SHA,
    }


def _slope(rows: list[dict[str, Any]], key: str) -> float | None:
    usable = [(np.log(row["actual_dofs"]), np.log(row[key])) for row in rows if row.get(key, 0.0) and row[key] > 0.0]
    if len(usable) < 3:
        return None
    return float(np.polyfit([pair[0] for pair in usable], [pair[1] for pair in usable], 1)[0])


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary_rows: list[dict[str, Any]] = []
    for row in rows:
        measurements = row["measured_repetitions"]
        summary_row = dict(row)
        summary_row["actual_dofs"] = int(measurements[0]["total_dofs"])
        summary_row["repetition_statistics"] = {}
        for key in ("assembly_seconds", "linear_solve_seconds", "total_seconds", "peak_rss_bytes", "tracemalloc_peak_bytes"):
            values = np.asarray([measurement[key] for measurement in measurements], dtype=float)
            summary_row[key] = float(np.mean(values))
            summary_row["repetition_statistics"][key] = {
                "mean": float(np.mean(values)),
                "median": float(np.median(values)),
                "population_stddev": float(np.std(values)),
            }
        summary_rows.append(summary_row)
    return {
        "rows": summary_rows,
        "assembly_exponent": _slope(summary_rows, "assembly_seconds"),
        "solve_exponent": _slope(summary_rows, "linear_solve_seconds"),
        "total_exponent": _slope(summary_rows, "total_seconds"),
        "memory_exponent": _slope(summary_rows, "peak_rss_bytes"),
    }


def run_campaign(
    *,
    low_order_targets: tuple[int, ...] = LOW_ORDER_TARGETS,
    high_order_targets: tuple[int, ...] = HIGH_ORDER_TARGETS,
    repetitions: int = 3,
    output: Path | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    if resume and output is not None and output.is_file():
        existing = json.loads(output.read_text(encoding="utf-8"))
        cases = list(existing.get("cases", []))
    existing_keys = {(row["family"], row["target_dofs"]) for row in cases}
    summary: dict[str, Any] = {"schema_version": 1, "contract_id": CONTRACT_ID, "environment": _environment(), "cases": cases, "status": "RUNNING"}
    summary["requested_targets"] = {
        "low_order": list(low_order_targets),
        "high_order": list(high_order_targets),
        "measured_repetitions": repetitions,
    }

    def persist() -> None:
        summary["by_family"] = {family: _summarize([row for row in cases if row["family"] == family]) for family in ("TET4", "HEX8", "TET10", "HEX20")}
        summary["high_order_ratios"] = {
            "TET10_over_TET4_at_nearest_targets": _ratios(summary["by_family"]["TET10"]["rows"], summary["by_family"]["TET4"]["rows"]),
            "HEX20_over_HEX8_at_nearest_targets": _ratios(summary["by_family"]["HEX20"]["rows"], summary["by_family"]["HEX8"]["rows"]),
        }
        summary["numerical_regression"] = {
            "all_pass": bool(cases) and all(row["deterministic"] and row["finite_metrics"] for row in cases),
            "max_residual": max((row["max_relative_residual_norm"] for row in cases), default=None),
        }
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    interrupted = False
    for family, targets in (("TET4", low_order_targets), ("HEX8", low_order_targets), ("TET10", high_order_targets), ("HEX20", high_order_targets)):
        for target in targets:
            if (family, target) in existing_keys:
                continue
            try:
                cases.append(run_case(family, target, repetitions))
            except KeyboardInterrupt:
                summary["status"] = "RESOURCE_LIMIT_REACHED"
                summary["stopped_before"] = {"family": family, "target_dofs": target, "reason": "manual stop at contract timeout/resource policy"}
                interrupted = True
                break
            persist()
        if interrupted:
            break
    if not interrupted:
        summary["status"] = "COMPLETE"
    persist()
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def annotate_resource_limit(output: Path, *, family: str, target_dofs: int, reason: str) -> dict[str, Any]:
    """Record a bounded campaign stop without changing measured rows."""
    report = json.loads(output.read_text(encoding="utf-8"))
    report["status"] = "COMPLETE_WITH_RESOURCE_LIMIT"
    report["resource_limit_observation"] = {
        "family": family,
        "target_dofs": target_dofs,
        "reason": reason,
        "measured_rows_unchanged": True,
    }
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _ratios(high: list[dict[str, Any]], low: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ratios = []
    for high_row in high:
        low_row = min(low, key=lambda row: abs(row["target_dofs"] - high_row["target_dofs"]))
        high_time = np.mean([r["total_seconds"] for r in high_row["measured_repetitions"]])
        low_time = np.mean([r["total_seconds"] for r in low_row["measured_repetitions"]])
        ratios.append({"high_order_target_dofs": high_row["target_dofs"], "low_order_target_dofs": low_row["target_dofs"], "total_time_ratio": float(high_time / low_time)})
    return ratios


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("qualification/0_2_6/g12_lot1_evidence.json"))
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--targets", nargs="+", type=int, default=None, help="override both low/high target lists for a smoke run")
    parser.add_argument("--low-targets", nargs="+", type=int, default=None)
    parser.add_argument("--high-targets", nargs="+", type=int, default=None)
    parser.add_argument("--resume", action="store_true", help="resume an existing evidence file without repeating completed cases")
    parser.add_argument("--annotate-resource-limit", action="store_true")
    parser.add_argument("--limit-family", default=None)
    parser.add_argument("--limit-target", type=int, default=None)
    parser.add_argument("--limit-reason", default="contract timeout/resource policy reached")
    args = parser.parse_args()
    if args.annotate_resource_limit:
        if args.limit_family is None or args.limit_target is None:
            parser.error("--annotate-resource-limit requires --limit-family and --limit-target")
        print(json.dumps(annotate_resource_limit(args.output, family=args.limit_family, target_dofs=args.limit_target, reason=args.limit_reason), indent=2))
        return 0
    targets = tuple(args.targets) if args.targets else None
    report = run_campaign(
        low_order_targets=targets or tuple(args.low_targets or LOW_ORDER_TARGETS),
        high_order_targets=targets or tuple(args.high_targets or HIGH_ORDER_TARGETS),
        repetitions=args.repetitions,
        output=args.output,
        resume=args.resume,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
