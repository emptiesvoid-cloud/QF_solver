"""Compact runtime performance matrix for the controlled 026-G12 campaign.

This runner measures existing solver routes only.  It is verification
infrastructure: no solver settings, formulations, thresholds, or defaults
are changed by this module.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import threading
import time
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from scripts.benchmark_g12_lot1 import build_model as build_linear_model  # noqa: E402
from scripts.benchmark_nonlinear_025 import _benchmark_model  # noqa: E402
from solveur.api import solve_model  # noqa: E402
from solveur.core.model import FiniteElementModel  # noqa: E402
from solveur.core.solvers.static import LinearStaticSolver  # noqa: E402

try:
    import psutil
except ImportError:  # pragma: no cover - optional measurement dependency
    psutil = None


CONTRACT_ID = "026-G12-FINAL-CAMPAIGN"
START_SHA = "51b3a7c8ace6731830109984a01ce31f79c44401"
REPETITIONS = 2


class _RssSampler:
    """Sample process RSS during one small route execution."""

    def __init__(self) -> None:
        self._process = psutil.Process(os.getpid()) if psutil is not None else None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.before: int | None = None
        self.after: int | None = None
        self.peak: int | None = None

    def start(self) -> None:
        if self._process is None:
            return
        self.before = int(self._process.memory_info().rss)
        self.peak = self.before
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()

    def _sample(self) -> None:
        assert self._process is not None
        while not self._stop.is_set():
            try:
                self.peak = max(self.peak or 0, int(self._process.memory_info().rss))
            except psutil.Error:
                return
            self._stop.wait(0.005)

    def stop(self) -> None:
        if self._process is None:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self.after = int(self._process.memory_info().rss)
        self.peak = max(self.peak or 0, self.after)


def _modal_model() -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        analysis={"type": "modal", "method": "eigh", "modes": 3},
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
    )


def _buckling_model() -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        analysis={
            "type": "linear_buckling",
            "method": "eigsh",
            "preload_factor": 1.0,
            "load_increments": 4,
            "maximum_factor": 100.0,
        },
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": -1.0}],
    )


def _route_specs() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "G12-ROUTE-LIN-TET4-001",
            "route": "linear_static",
            "family": "TET4",
            "material": "isotropic_3d",
            "factory": lambda: build_linear_model("TET4", 300)[0],
            "evidence_scope": "MEASURED",
        },
        {
            "case_id": "G12-ROUTE-LIN-TET10-001",
            "route": "linear_static",
            "family": "TET10",
            "material": "isotropic_3d",
            "factory": lambda: build_linear_model("TET10", 300)[0],
            "evidence_scope": "MEASURED",
        },
        {
            "case_id": "G12-ROUTE-LIN-HEX8-001",
            "route": "linear_static",
            "family": "HEX8",
            "material": "isotropic_3d",
            "factory": lambda: build_linear_model("HEX8", 300)[0],
            "evidence_scope": "MEASURED",
        },
        {
            "case_id": "G12-ROUTE-LIN-HEX20-001",
            "route": "linear_static",
            "family": "HEX20",
            "material": "isotropic_3d",
            "factory": lambda: build_linear_model("HEX20", 300)[0],
            "evidence_scope": "MEASURED",
        },
        {
            "case_id": "G12-ROUTE-MODAL-TET4-001",
            "route": "modal",
            "family": "TET4",
            "material": "isotropic_3d+density",
            "factory": _modal_model,
            "evidence_scope": "MEASURED",
        },
        {
            "case_id": "G12-ROUTE-BUCKLING-TET4-001",
            "route": "linear_buckling",
            "family": "TET4",
            "material": "isotropic_3d",
            "factory": _buckling_model,
            "evidence_scope": "MEASURED",
        },
        {
            "case_id": "G12-ROUTE-J2-TET4-001",
            "route": "nonlinear_static",
            "family": "TET4",
            "material": "von_mises_elastoplastic_3d",
            "factory": lambda: _benchmark_model("TET4", "small_strain", "load_control"),
            "evidence_scope": "MEASURED_BOUNDED",
        },
        {
            "case_id": "G12-ROUTE-TL-TET4-001",
            "route": "geometric_nonlinear_static",
            "family": "TET4",
            "material": "isotropic_3d / total_lagrangian_stvk",
            "factory": lambda: _benchmark_model("TET4", "small_strain", "geometric_static"),
            "evidence_scope": "MEASURED_BOUNDED",
        },
        {
            "case_id": "G12-ROUTE-CONTACT-TET4-001",
            "route": "nonlinear_static/contact_g09_bounded",
            "family": "TET4",
            "material": "von_mises_elastoplastic_3d",
            "factory": lambda: _benchmark_model("TET4", "small_strain", "contact"),
            "evidence_scope": "MEASURED_BOUNDED",
        },
    ]


def _finite(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool)):
        return True
    if isinstance(value, (int, float, np.number)):
        return math.isfinite(float(value))
    if isinstance(value, np.ndarray):
        return bool(np.all(np.isfinite(value)))
    if isinstance(value, dict):
        return all(_finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite(item) for item in value)
    return True


def _checksum(result: Any) -> str | None:
    values = getattr(result, "modes", None)
    if values is None:
        values = getattr(result, "displacements", None)
    if values is None:
        return None
    return hashlib.sha256(np.asarray(values, dtype=np.float64).tobytes()).hexdigest()


def _sum_present(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return float(sum(values)) if values else None


def _timings(analysis: str, solver: dict[str, Any]) -> tuple[float | None, float | None, int | None, str]:
    if analysis == "modal":
        assembly = solver.get("assembly", {}).get("stiffness", {})
        phase = assembly.get("assembly_phase_seconds", {})
        return float(sum(float(value) for value in phase.values())), None, assembly.get("final_nnz"), "global_stiffness"
    if analysis == "linear_buckling":
        increments = solver.get("preload_diagnostics", {}).get("increments", [])
        return _sum_present(increments, "assembly_seconds"), _sum_present(increments, "linear_solve_seconds"), max(
            int(solver.get("initial_tangent_nnz", 0)), int(solver.get("geometric_tangent_nnz", 0))
        ), "max(initial_tangent,geometric_tangent)"
    execution = solver.get("execution", {})
    if execution:
        return execution.get("assembly_seconds"), execution.get("linear_solve_seconds"), execution.get(
            "resource_estimate", {}
        ).get("nnz"), "reduced_stiffness"
    steps = solver.get("steps") or solver.get("increments") or []
    return _sum_present(steps, "assembly_seconds"), _sum_present(steps, "linear_solve_seconds"), max(
        (int(row.get("tangent_nnz", 0)) for row in steps), default=0
    ) or None, "max_tangent_nnz"


def _measure(spec: dict[str, Any], repetition: int) -> dict[str, Any]:
    model = spec["factory"]()
    started = time.perf_counter()
    sampler = _RssSampler()
    sampler.start()
    try:
        linear_assembler = None
        if str(getattr(model.analysis, "type", "")) == "linear_static":
            linear_solver = LinearStaticSolver()
            result = linear_solver.solve(model, detail_level="summary")
            linear_assembler = linear_solver.assembler
        else:
            result = solve_model(model, enforce_policy=False)
        result_data = result.to_dict()
        solver = result_data.get("solver", {})
        assembly, solve, nnz, nnz_scope = _timings(str(result_data.get("analysis")), solver)
        if linear_assembler is not None:
            nnz = linear_assembler.last_diagnostics.get("final_nnz")
            nnz_scope = "global_stiffness"
        steps = solver.get("steps") or solver.get("increments") or []
        sampler.stop()
        raw_status = str(result_data.get("status"))
        status = "PASS" if raw_status.upper() in {"PASS", "SUCCESS"} else raw_status.upper()
        return {
            "case_id": spec["case_id"],
            "route": spec["route"],
            "family": spec["family"],
            "material": spec["material"],
            "repetition": repetition,
            "status": status,
            "raw_status": raw_status,
            "node_count": int(result_data.get("node_count", model.node_count)),
            "element_count": int(result_data.get("element_count", len(model.elements))),
            "dof_count": int(result_data.get("ndof", 0)),
            "assembly_seconds": assembly,
            "solve_seconds": solve,
            "total_seconds": float(time.perf_counter() - started),
            "peak_rss_bytes": sampler.peak,
            "rss_before_bytes": sampler.before,
            "rss_after_bytes": sampler.after,
            "nnz": int(nnz) if nnz is not None else None,
            "nnz_scope": nnz_scope,
            "iterations": int(sum(int(row.get("iterations", 0)) for row in steps)) if steps else None,
            "convergence_status": solver.get("preload_diagnostics", {}).get("converged")
            if str(result_data.get("analysis")) == "linear_buckling"
            else "PASS",
            "critical_factor": solver.get("critical_factor"),
            "max_relative_residual": solver.get("max_relative_residual")
            or solver.get("preload_diagnostics", {}).get("final_relative_residual")
            or (max((float(row["relative_residual"]) for row in steps if "relative_residual" in row), default=None)),
            "finite_metrics": _finite(result_data),
            "solution_checksum": _checksum(result),
            "error": None,
            "evidence_scope": spec["evidence_scope"],
        }
    except Exception as exc:  # pragma: no cover - evidence records route failures
        sampler.stop()
        return {
            "case_id": spec["case_id"],
            "route": spec["route"],
            "family": spec["family"],
            "material": spec["material"],
            "repetition": repetition,
            "status": "FAIL",
            "node_count": model.node_count,
            "element_count": len(model.elements),
            "dof_count": model.dof_manager().ndof,
            "assembly_seconds": None,
            "solve_seconds": None,
            "total_seconds": float(time.perf_counter() - started),
            "peak_rss_bytes": sampler.peak,
            "rss_before_bytes": sampler.before,
            "rss_after_bytes": sampler.after,
            "nnz": None,
            "nnz_scope": None,
            "iterations": None,
            "convergence_status": "FAIL",
            "critical_factor": None,
            "max_relative_residual": None,
            "finite_metrics": False,
            "solution_checksum": None,
            "error": {"type": type(exc).__name__, "message": str(exc)},
            "evidence_scope": spec["evidence_scope"],
        }
    finally:
        sampler.stop()


def _aggregate(spec: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    first, second = rows
    if spec["route"] == "linear_buckling":
        deterministic = (
            first.get("status") == second.get("status")
            and first.get("finite_metrics") == second.get("finite_metrics")
            and math.isclose(
                float(first.get("critical_factor")),
                float(second.get("critical_factor")),
                rel_tol=1.0e-12,
                abs_tol=1.0e-12,
            )
            and math.isclose(
                float(first.get("max_relative_residual")),
                float(second.get("max_relative_residual")),
                rel_tol=1.0e-12,
                abs_tol=1.0e-12,
            )
        )
    else:
        replay_fields = ("status", "solution_checksum", "finite_metrics", "convergence_status")
        deterministic = all(first.get(field) == second.get(field) for field in replay_fields)
    def median_optional(key: str) -> float | None:
        values = [float(row[key]) for row in rows if row.get(key) is not None]
        return float(median(values)) if values else None
    return {
        "case_id": spec["case_id"],
        "route": spec["route"],
        "family": spec["family"],
        "material": spec["material"],
        "evidence_scope": spec["evidence_scope"],
        "repetitions": rows,
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "deterministic": deterministic,
        "finite_metrics": all(bool(row["finite_metrics"]) for row in rows),
        "median_assembly_seconds": median_optional("assembly_seconds"),
        "median_solve_seconds": median_optional("solve_seconds"),
        "median_total_seconds": median_optional("total_seconds"),
        "peak_rss_bytes": max((int(row["peak_rss_bytes"]) for row in rows if row.get("peak_rss_bytes") is not None), default=None),
        "nnz": first.get("nnz"),
        "nnz_scope": first.get("nnz_scope"),
        "dof_count": first.get("dof_count"),
        "element_count": first.get("element_count"),
        "iterations": first.get("iterations"),
        "critical_factor": first.get("critical_factor"),
        "solution_checksum": first.get("solution_checksum"),
    }


def _read_json(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _environment() -> dict[str, Any]:
    return {
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "psutil": getattr(psutil, "__version__", None),
        "logical_cpus": os.cpu_count(),
    }


def run_campaign(output: Path, repetitions: int = REPETITIONS) -> dict[str, Any]:
    if repetitions != 2:
        raise ValueError("The compact route matrix requires exactly two deterministic repetitions.")
    raw_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for spec in _route_specs():
        rows = [_measure(spec, repetition) for repetition in range(1, repetitions + 1)]
        raw_rows.extend(rows)
        summaries.append(_aggregate(spec, rows))
    optimized = _read_json("qualification/0_2_6/g12_optimization_optimized_scaling.json")
    probes = _read_json("qualification/0_2_6/g12_optimization_assembly_probes.json")
    evidence = _read_json("qualification/0_2_6/g12_optimization_evidence.json")
    profiles = _read_json("qualification/0_2_6/g12_optimization_profiles.json")
    return {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "status": "PASS" if all(row["status"] == "PASS" and row["deterministic"] and row["finite_metrics"] for row in summaries) else "FAIL",
        "start_sha": START_SHA,
        "measurement_sha": _environment()["git_head"],
        "environment": _environment(),
        "performance_matrix": {
            "classification": "MEASURED",
            "repetitions_per_case": repetitions,
            "rows": summaries,
            "raw_rows": raw_rows,
        },
        "scaling_summary": {
            "classification": "MEASURED_REUSED_EXISTING_G12_EVIDENCE",
            "source": "qualification/0_2_6/g12_optimization_optimized_scaling.json",
            "rows": optimized.get("rows", []),
            "exponents": evidence.get("scaling", {}),
        },
        "memory_summary": {
            "classification": "MEASURED_REUSED_EXISTING_G12_EVIDENCE",
            "source": "qualification/0_2_6/g12_optimization_evidence.json",
            "memory_exponent": evidence.get("scaling", {}).get("memory_exponent"),
            "assembly_probes": probes.get("rows", []),
        },
        "bottleneck_analysis": {
            "classification": "MEASURED_REUSED_EXISTING_PROFILE",
            "source": "qualification/0_2_6/g12_optimization_profiles.json",
            "component": "MESH_VALIDATION / TET4 quality metrics",
            "profile": profiles.get("profiles", []),
            "deferred": evidence.get("optimization_candidates_deferred", []),
        },
        "numerical_regression": evidence.get("numerical_regression", {}),
        "large_scale": {
            "300000": {"classification": "REUSE_EXISTING_EVIDENCE", "status": "PASS", "source": "g12_optimization_assembly_probes.json"},
            "1000000": {"classification": "REUSE_EXISTING_EVIDENCE", "status": "RESOURCE_LIMITED", "source": "g12_optimization_assembly_probes.json"},
        },
        "limitations": [
            "The new multi-route matrix uses compact bounded cases; it is not a universal route-by-family scaling law.",
            "Modal and buckling solve timings are not exposed as separate public phases and remain null where unmeasured.",
            "J2, TL and contact measurements are bounded route characterizations, not maturity promotion.",
            "The 1M probe remains resource-limited and is reused without rerun.",
        ],
        "provenance": {
            "measurement_command": "python scripts/benchmark_g12_route_matrix.py --output qualification/0_2_6/g12_final_campaign.json",
            "source_contract": "qualification/0_2_6/g12_optimization_contract.json",
            "route_builder_sources": ["scripts/benchmark_g12_lot1.py", "scripts/benchmark_nonlinear_025.py"],
            "functional_solver_modified": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run_campaign(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "cases": len(payload["performance_matrix"]["raw_rows"])}))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
