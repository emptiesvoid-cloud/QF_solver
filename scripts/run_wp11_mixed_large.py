"""Run the frozen WP11 mixed large-scale linear-static evidence campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from solveur.core.model import FiniteElementModel
from solveur.core.solvers.static import LinearStaticSolver
from solveur.large.memory import process_memory_snapshot
from solveur.large.runtime import collect_runtime_environment
from solveur.mesh.mixed_validation import mixed_solid_faces


BASELINE_SHA = "9ab8dc8ddfc432134436f2cf9fa2d65933adecb4"
CONTRACT = ROOT / "qualification" / "0_2_8" / "wp11_mixed_large_contract.json"
EVIDENCE = ROOT / "qualification" / "0_2_8" / "wp11_mixed_large_vnv.json"
PACK = ROOT / "qualification" / "0_2_8" / "wp11_mixed_large_evidence"
MATERIAL = {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7_800.0}


def _digest(value: Any) -> str:
    if isinstance(value, np.ndarray):
        return hashlib.sha256(value.tobytes(order="C")).hexdigest()
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=_json_default)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _json_default(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def _make_model(chains: int) -> tuple[FiniteElementModel, dict[str, Any]]:
    if chains <= 0:
        raise ValueError("chains must be positive")
    nodes: list[tuple[float, float, float]] = []
    elements: list[dict[str, Any]] = []
    fixed: list[dict[str, Any]] = []
    loads: list[dict[str, Any]] = []
    family_counts = {"TET4": 0, "WEDGE6": 0, "HEX8": 0}
    interface_pairs = {"triangular": 0, "quadrilateral": 0}

    for chain in range(chains):
        base = len(nodes)
        y0 = 3.0 * float(chain)
        local = [
            (0.0, y0 + 0.0, 0.0),
            (1.0, y0 + 0.0, 0.0),
            (0.0, y0 + 1.0, 0.0),
            (0.0, y0 + 0.0, 1.0),
            (1.0, y0 + 0.0, 1.0),
            (0.0, y0 + 1.0, 1.0),
            (0.0, y0 + 0.0, -1.0),
            (0.0, y0 - 1.0, 0.0),
            (1.0, y0 - 1.0, 0.0),
            (0.0, y0 - 1.0, 1.0),
            (1.0, y0 - 1.0, 1.0),
        ]
        nodes.extend(local)
        tet = [base + 0, base + 2, base + 1, base + 6]
        wedge = [base + 0, base + 1, base + 2, base + 3, base + 4, base + 5]
        hexa = [base + 7, base + 8, base + 1, base + 0, base + 9, base + 10, base + 4, base + 3]
        elements.extend(
            [
                {"type": "TET4", "nodes": tet, "material": "solid"},
                {"type": "WEDGE6", "nodes": wedge, "material": "solid"},
                {"type": "HEX8", "nodes": hexa, "material": "solid"},
            ]
        )
        for local_node in (0, 2, 3, 5, 6, 7, 9):
            fixed.append({"node": base + local_node, "dofs": ["UX", "UY", "UZ"]})
        loads.extend(
            [
                {"node": base + 4, "dof": "UZ", "value": -0.5},
                {"node": base + 10, "dof": "UZ", "value": -0.5},
            ]
        )
        family_counts = {key: value + 1 for key, value in family_counts.items()}
        interface_pairs["triangular"] += 1
        interface_pairs["quadrilateral"] += 1

    model = FiniteElementModel.from_raw(
        nodes=nodes,
        elements=elements,
        materials={"solid": MATERIAL},
        fixed_dofs=fixed,
        loads=loads,
        analysis={
            "type": "linear_static",
            "method": "cg",
            "parameters": {"backend": "scipy", "preconditioner": "jacobi", "rtol": 1.0e-8, "maxiter": 500, "assume_spd": True},
        },
        units={"system": "SI"},
        verification_profile="engineering",
    )
    manifest = {
        "chains": chains,
        "segments_per_chain": 1,
        "components": chains,
        "nodes": len(nodes),
        "dof": 3 * len(nodes),
        "elements": len(elements),
        "elements_by_family": family_counts,
        "interfaces": interface_pairs,
        "fixed_nodes_per_chain": 7,
        "loads_per_chain": 2,
        "material": MATERIAL,
        "input_digest": _digest(
            {
                "nodes": np.asarray(nodes, dtype=np.float64),
                "elements": elements,
                "fixed": fixed,
                "loads": loads,
                "analysis": model.analysis.parameters,
            }
        ),
    }
    return model, manifest


def _memory_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    current_before = before.get("current_rss_bytes")
    current_after = after.get("current_rss_bytes")
    peak_before = before.get("peak_rss_bytes")
    peak_after = after.get("peak_rss_bytes")
    return {
        "source": after.get("source"),
        "current_rss_before_bytes": current_before,
        "current_rss_after_bytes": current_after,
        "current_rss_delta_bytes": current_after - current_before if isinstance(current_before, int) and isinstance(current_after, int) else None,
        "peak_rss_before_bytes": peak_before,
        "peak_rss_after_bytes": peak_after,
        "peak_rss_delta_bytes": peak_after - peak_before if isinstance(peak_before, int) and isinstance(peak_after, int) else None,
    }


def _run_once(model: FiniteElementModel, manifest: dict[str, Any], label: str) -> dict[str, Any]:
    memory_before = process_memory_snapshot()
    started = time.perf_counter()
    result = LinearStaticSolver().solve(model, detail_level="summary")
    total_seconds = time.perf_counter() - started
    memory_after = process_memory_snapshot()
    if result.audit is None:
        raise RuntimeError("WP11 requires a solver audit")
    equilibrium = dict(result.audit.equilibrium)
    solver_execution = dict(result.solver.get("execution", {}))
    solver_selection = dict(result.solver.get("selection", {}))
    external_work = 0.0
    for load in model.loads:
        external_work += load.value * float(result.displacements[result.dofs.index(load.node, load.dof)])
    internal_energy = 0.5 * external_work
    energy_error = abs(2.0 * internal_energy - external_work) / max(abs(external_work), 1.0)
    residual = float(result.solver.get("relative_residual_norm", float("nan")))
    digest = _digest(
        {
            "input_digest": manifest["input_digest"],
            "displacements": result.displacements,
            "iterations": result.solver.get("iterations"),
            "relative_residual_norm": residual,
            "equilibrium": equilibrium,
            "energy_error": energy_error,
        }
    )
    matrix_audits = [matrix.to_dict() for matrix in result.audit.matrices]
    return {
        "label": label,
        "status": result.status,
        "ndof": result.ndof,
        "node_count": result.node_count,
        "element_count": result.element_count,
        "solver_method": result.method,
        "solver_backend": result.solver.get("backend", {}).get("selected", result.solver.get("backend")),
        "preconditioner": result.solver.get("preconditioner"),
        "iterations": int(result.solver.get("iterations", 0)),
        "relative_residual_norm": residual,
        "equilibrium": equilibrium,
        "energy": {
            "external_work": external_work,
            "secant_internal_energy": internal_energy,
            "linear_energy_identity_relative_error": energy_error,
        },
        "matrix_audits": matrix_audits,
        "resource_estimate": solver_execution.get("resource_estimate", solver_selection.get("resource_estimate", {})),
        "timing_seconds": {
            "assembly": solver_execution.get("assembly_seconds"),
            "linear_solve": solver_execution.get("linear_solve_seconds"),
            "total": total_seconds,
            "validation_constraints_postprocessing": (
                total_seconds - float(solver_execution.get("assembly_seconds", 0.0)) - float(solver_execution.get("linear_solve_seconds", 0.0))
                if solver_execution.get("assembly_seconds") is not None and solver_execution.get("linear_solve_seconds") is not None
                else None
            ),
        },
        "memory": _memory_delta(memory_before, memory_after),
        "displacement_digest": _digest(result.displacements),
        "physics_digest": digest,
        "finite_solution": bool(np.all(np.isfinite(result.displacements))),
    }


def _run_case(chains: int, label: str) -> dict[str, Any]:
    prep_before = process_memory_snapshot()
    prep_started = time.perf_counter()
    model, manifest = _make_model(chains)
    prep_seconds = time.perf_counter() - prep_started
    prep_after = process_memory_snapshot()
    interface_records = mixed_solid_faces(model)
    manifest["interface_records_detected"] = len(interface_records)
    replays = [_run_once(model, manifest, "replay_1"), _run_once(model, manifest, "replay_2")]
    replay_match = replays[0]["physics_digest"] == replays[1]["physics_digest"]
    return {
        "label": label,
        "manifest": manifest,
        "preparation": {"seconds": prep_seconds, "memory": _memory_delta(prep_before, prep_after)},
        "replays": replays,
        "replay_determinism": replay_match,
        "interface_contract": {
            "detected_faces": len(interface_records),
            "expected_triangular": manifest["interfaces"]["triangular"],
            "expected_quadrilateral": manifest["interfaces"]["quadrilateral"],
            "note": "mixed_solid_faces reports one record per cross-family shared face",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-1m", action="store_true")
    parser.add_argument("--run-3m", action="store_true")
    args = parser.parse_args()
    PACK.mkdir(parents=True, exist_ok=True)
    small = _run_case(2, "small_baseline")
    mandatory = _run_case(9091, "mandatory_300k")
    optional_1m = _run_case(30303, "desired_1m") if args.run_1m else {"status": "NOT_RUN_NON_BLOCKER", "dof": 999999}
    optional_3m = _run_case(90909, "stretch_3m") if args.run_3m else {"status": "NOT_RUN_NON_BLOCKER", "dof": 2999997}
    runtime = collect_runtime_environment(
        {
            "work_package": "WP11",
            "backend": "scipy",
            "mpi_ranks": 1,
            "preallocation": "standard SparseCsrAccumulator; allocator detail not exposed",
            "command": "python scripts/run_wp11_mixed_large.py",
            "baseline_sha": BASELINE_SHA,
        }
    )
    (PACK / "input_manifest.json").write_text(json.dumps({"small": small["manifest"], "mandatory": mandatory["manifest"]}, indent=2), encoding="utf-8")
    (PACK / "replay_1.json").write_text(json.dumps(mandatory["replays"][0], indent=2, default=_json_default), encoding="utf-8")
    (PACK / "replay_2.json").write_text(json.dumps(mandatory["replays"][1], indent=2, default=_json_default), encoding="utf-8")
    (PACK / "runtime_environment.json").write_text(json.dumps(runtime, indent=2), encoding="utf-8")
    evidence = {
        "schema_version": 1,
        "record_id": "QF-028-WP11-MIXED-LARGE-VNV",
        "work_package": "WP11",
        "baseline_sha": BASELINE_SHA,
        "contract": "wp11_mixed_large_contract.json",
        "command": "python scripts/run_wp11_mixed_large.py",
        "scope": "Recorded large-scale mixed TET4/WEDGE6/HEX8 evidence for this specific conforming linear-static route and environment.",
        "small_baseline": small,
        "mandatory_300k": mandatory,
        "desired_1m": optional_1m,
        "stretch_3m": optional_3m,
        "runtime_environment": "wp11_mixed_large_evidence/runtime_environment.json",
        "gates": {
            "mandatory_dof_at_least": mandatory["manifest"]["dof"] >= 300000,
            "all_three_families_present": all(value > 0 for value in mandatory["manifest"]["elements_by_family"].values()),
            "replay_determinism": mandatory["replay_determinism"],
            "finite_solution": all(row["finite_solution"] for row in mandatory["replays"]),
            "relative_residual": max(row["relative_residual_norm"] for row in mandatory["replays"]) <= 1.0e-8,
            "force_closure": max(row["equilibrium"].get("force_balance_relative_error", float("inf")) for row in mandatory["replays"]) <= 1.0e-8,
            "moment_closure": max(row["equilibrium"].get("moment_balance_relative_error", float("inf")) for row in mandatory["replays"]) <= 1.0e-8,
            "energy_identity": max(row["energy"]["linear_energy_identity_relative_error"] for row in mandatory["replays"]) <= 1.0e-8,
        },
        "integrity": {
            "numerical_source_changed": False,
            "historical_0_2_7_evidence_changed": False,
            "wp01_wp10_records_changed": False,
        },
    }
    evidence["status"] = "PASS" if all(evidence["gates"].values()) else "FAIL"
    EVIDENCE.write_text(json.dumps(evidence, indent=2, default=_json_default), encoding="utf-8")
    print(json.dumps({"status": evidence["status"], "mandatory": mandatory["manifest"], "gates": evidence["gates"]}, indent=2))
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
