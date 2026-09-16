"""Run a sequential diagnostic replay for the WP05-D stress-window candidate.

The original WP05-C/D contract and its raw evidence are never overwritten.
This runner executes only the Owner-requested HEX20 H1/H2/H3 diagnostic replay
and records the candidate post-processing observable separately from the
historical point-membership observable.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from time import perf_counter, process_time
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_wp05_structural_qualification import (  # noqa: E402
    _model,
    _observables,
    _policy_digest,
    _sha256,
    _write_json,
)
from scripts.wp05_cd_structural_harness import (  # noqa: E402
    CONTRACT_JSON,
    MESH_LEVELS,
    StructuralBenchmarkContract,
    build_mesh,
    check_load_conservation,
    mesh_quality,
)
from scripts.wp05_stress_window_candidate import (  # noqa: E402
    ExactReferenceWindowCandidate,
    clipped_reference_window_sigma_xx_hex20,
)
from solveur.core.assembly.geometric import build_total_lagrangian_assembly  # noqa: E402
from solveur.core.analyses.geometric_nonlinear import _newton_dead_load  # noqa: E402
from solveur.core.nonlinear.robustness import NonlinearRobustnessOptions  # noqa: E402


DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_9" / "wp05d_stress_window_replay"
LEVELS = tuple(level.name for level in MESH_LEVELS)


def _run_case(level: str, output: Path) -> dict[str, Any]:
    contract = StructuralBenchmarkContract()
    mesh = build_mesh("HEX20", level, contract)
    case_dir = output / "HEX20" / level
    case_dir.mkdir(parents=True, exist_ok=True)
    result_path = case_dir / "result.json"
    raw_path = case_dir / "raw.npz"
    started = perf_counter()
    cpu_started = process_time()
    payload: dict[str, Any] = {
        "status": "RUNNING",
        "run_kind": "DIAGNOSTIC_REPLAY",
        "formal_claim": False,
        "source_sha": _git_sha(),
        "branch_at_capture": _git_branch(),
        "historical_contract_sha256": _sha256(CONTRACT_JSON),
        "candidate_contract_sha256": _candidate_contract_sha(),
        "governing_policy_digest": _policy_digest(contract),
        "family": "HEX20",
        "mesh_level": level,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "node_count": mesh.nodes,
        "element_count": mesh.elements,
        "dof_count": mesh.dofs,
        "mesh_quality": mesh_quality(mesh),
        "load_check": check_load_conservation(mesh, contract),
        "solver_route": "geometric_nonlinear_static / MINRES + Jacobi / canonical line search / floor-aware termination",
        "solver_parameters": {
            "load_increments": 12,
            "tolerance": 1.0e-10,
            "max_iterations": 40,
            "linear_solver": "minres",
            "linear_preconditioner": "jacobi",
            "linear_rtol": 1.0e-11,
            "linear_atol": 1.0e-14,
            "linear_maxiter": 10_000,
            "linear_direct_fallback": False,
        },
    }
    _write_json(result_path, payload)
    try:
        model, _, loads, fixed_nodes = _model("HEX20", level, contract)
        assembly = build_total_lagrangian_assembly(model)
        fixed = np.concatenate([3 * fixed_nodes + component for component in range(3)]).astype(int)
        options = NonlinearRobustnessOptions(
            linear_solver="minres",
            linear_preconditioner="jacobi",
            linear_rtol=1.0e-11,
            linear_atol=1.0e-14,
            linear_maxiter=10_000,
            linear_residual_tolerance=1.0e-10,
            linear_backward_error_tolerance=1.0e-10,
            linear_direct_fallback=False,
            line_search="existing",
            floor_aware_termination=True,
        )
        options.validate()
        displacement, diagnostics = _newton_dead_load(
            assembly,
            loads.reshape(-1),
            fixed,
            increments=12,
            tolerance=1.0e-10,
            max_iterations=40,
            determinant_assembly=assembly,
            robustness_options=options,
        )
        historical_observables, arrays = _observables(model, mesh, loads, fixed_nodes, displacement)
        candidate_observables = clipped_reference_window_sigma_xx_hex20(
            mesh,
            displacement,
            assembly._kernels[0].material,
            contract,
            ExactReferenceWindowCandidate(),
        )
        np.savez_compressed(raw_path, **arrays)
        payload.update(
            {
                "status": "PASS",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "wall_time_s": perf_counter() - started,
                "cpu_time_s": process_time() - cpu_started,
                "historical_point_membership_observables": historical_observables,
                "candidate_observables": candidate_observables,
                "solver_diagnostics": diagnostics,
                "raw_npz": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
                "raw_sha256": _sha256(raw_path),
                "accepted_load_factors": [
                    item.get("load_factor")
                    for item in diagnostics.get("increments", [])
                    if isinstance(item, dict)
                ],
                "newton_iterations": sum(
                    int(item.get("iterations", 0))
                    for item in diagnostics.get("increments", [])
                    if isinstance(item, dict)
                ),
                "fallback_count": sum(
                    int(item.get("fallback_count", 0))
                    for item in diagnostics.get("increments", [])
                    if isinstance(item, dict)
                ),
            }
        )
    except Exception as exc:
        payload.update(
            {
                "status": "FAILED",
                "terminal_classification": type(exc).__name__,
                "error": str(exc),
                "wall_time_s": perf_counter() - started,
                "cpu_time_s": process_time() - cpu_started,
            }
        )
    _write_json(result_path, payload)
    print(f"{level}: {payload['status']}", flush=True)
    return payload


def _git_sha() -> str:
    import subprocess

    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _git_branch() -> str:
    import subprocess

    return subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()


def _candidate_contract_sha() -> str:
    return _sha256(ROOT / "qualification" / "0_2_9" / "wp05_cd_stress_window_remediation_candidate.json")


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "status": "PASS" if all(item.get("status") == "PASS" for item in results) else "FAIL_CLOSED",
        "run_kind": "DIAGNOSTIC_REPLAY",
        "formal_claim": False,
        "family": "HEX20",
        "levels": results,
        "h2_to_h3_candidate_delta": None,
        "next_step": "OWNER_AUTHORIZATION_REQUIRED_BEFORE_FORMAL_REQUALIFICATION",
    }
    passed = {item.get("mesh_level"): item for item in results if item.get("status") == "PASS"}
    if "H2" in passed and "H3" in passed:
        h2 = passed["H2"]["candidate_observables"]["representative_sigma_xx"]
        h3 = passed["H3"]["candidate_observables"]["representative_sigma_xx"]
        summary["h2_to_h3_candidate_delta"] = abs(h3 - h2) / abs(h3)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty replay output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    results = [_run_case(level, output) for level in LEVELS]
    summary = _summary(results)
    _write_json(output / "replay_summary.json", summary)
    print(json.dumps({"status": summary["status"], "h2_to_h3_candidate_delta": summary["h2_to_h3_candidate_delta"]}, sort_keys=True), flush=True)
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
