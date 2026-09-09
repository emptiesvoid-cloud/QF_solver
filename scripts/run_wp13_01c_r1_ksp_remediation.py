"""Run the prospective WP13-01C-R1 PETSc KSP/preconditioner campaign.

This harness uses the existing rank-local mixed PETSc assembly unchanged.  It
selects an explicit, contract-listed KSP/PC for each process invocation; no
candidate can trigger an automatic fallback to another configuration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import run_wp13_01c_final_runtime as base


CONTRACT_ID = "WP13-01C-R1-KSP-REMEDIATION-001"
CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp13_01c_r1_ksp_remediation_contract.json"
OUTPUT_DIR = ROOT / "qualification" / "0_2_8" / "wp13_01c_r1_ksp_remediation"
ORIGINAL_SCALE_A = ROOT / "qualification" / "0_2_8" / "wp13_01c_petsc_mpi_mixed_runtime" / "scale_a.json"


def _json_default(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False, default=_json_default) + "\n", encoding="utf-8")


def _load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise RuntimeError("WP13-01C-R1 contract identifier mismatch.")
    return contract


def _contract_hash() -> str:
    return hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest()


def _candidate(contract: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    for candidate in contract["solver_candidates"]:
        if candidate["id"] == candidate_id:
            return dict(candidate)
    raise ValueError(f"Candidate '{candidate_id}' is not predeclared by the R1 contract.")


def _relative(left: Any, right: Any) -> float:
    left_array = np.asarray(left, dtype=float)
    right_array = np.asarray(right, dtype=float)
    return float(np.linalg.norm(left_array - right_array) / max(float(np.linalg.norm(right_array)), 1.0))


def _run_mpi(args: argparse.Namespace) -> int:
    from mpi4py import MPI

    contract = _load_contract()
    candidate = _candidate(contract, args.candidate)
    comm = MPI.COMM_WORLD
    result = base._petsc_case(
        args.segments,
        solver_config=candidate,
        allow_nonconverged=True,
    )
    if comm.Get_rank() == 0:
        assert result is not None
        result["candidate_id"] = candidate["id"]
        result["candidate_configuration"] = candidate
        _write_json(
            args.output,
            {
                "schema_version": 1,
                "contract_id": CONTRACT_ID,
                "contract_sha256": _contract_hash(),
                "case": "mpi",
                "candidate_id": candidate["id"],
                "result": result,
            },
        )
    return 0


def _run_serial(args: argparse.Namespace) -> int:
    contract = _load_contract()
    result = base._serial_case(args.segments)
    _write_json(
        args.output,
        {
            "schema_version": 1,
            "contract_id": contract["contract_id"],
            "contract_sha256": _contract_hash(),
            "case": "serial",
            "result": result,
        },
    )
    return 0


def _read_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))["result"]


def _small_non_regression(serial: dict[str, Any], runtime: dict[str, Any], gates: dict[str, Any]) -> dict[str, Any]:
    values = {
        "displacement_relative": _relative(runtime.get("solution", []), serial.get("displacement", [])),
        "reaction_relative": _relative(runtime.get("reaction_vector", []), serial.get("reaction_vector", [])),
        "energy_relative": abs(float(runtime["energy"]) - float(serial["energy"])) / max(abs(float(serial["energy"])), 1.0),
        "force_balance_relative": float(runtime["force_balance_relative"]),
        "free_residual_relative": float(runtime["free_residual_relative"]),
    }
    values["pass"] = bool(
        runtime["converged_reason"] > 0
        and values["displacement_relative"] <= gates["small_displacement_relative_max"]
        and values["reaction_relative"] <= gates["small_reaction_relative_max"]
        and values["energy_relative"] <= gates["small_energy_relative_max"]
        and values["force_balance_relative"] <= gates["small_force_balance_relative_max"]
        and values["free_residual_relative"] <= gates["small_free_residual_relative_max"]
    )
    return values


def _scale_acceptance(runtime: dict[str, Any], gates: dict[str, Any]) -> bool:
    return bool(
        runtime["status"] == "PASS"
        and int(runtime["converged_reason"]) > 0
        and math.isfinite(float(runtime["free_residual_relative"]))
        and math.isfinite(float(runtime["force_balance_relative"]))
        and float(runtime["free_residual_relative"]) <= gates["scale_free_residual_relative_max"]
        and float(runtime["force_balance_relative"]) <= gates["scale_force_balance_relative_max"]
        and not runtime["global_gather_audit"]["global_model_retained_on_any_rank"]
    )


def _build_evidence(args: argparse.Namespace) -> int:
    contract = _load_contract()
    gates = contract["gates"]
    serial = _read_result(args.serial)
    rows: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None
    selected_small: dict[str, Any] | None = None
    selected_scale: dict[str, Any] | None = None
    for candidate in contract["solver_candidates"]:
        candidate_id = candidate["id"]
        small_path = args.results_dir / f"small_{candidate_id}.json"
        scale_path = args.results_dir / f"scale_a_{candidate_id}.json"
        if not small_path.exists():
            rows.append({"candidate_id": candidate_id, "status": "NOT_RUN"})
            continue
        small = _read_result(small_path)
        non_regression = _small_non_regression(serial, small, gates)
        if not scale_path.exists():
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "ksp": candidate["ksp"],
                    "pc": candidate["pc"],
                    "small_non_regression": non_regression,
                    "scale_a": {
                        "status": "NOT_RUN_SMALL_NON_REGRESSION_FAILED"
                        if not non_regression["pass"]
                        else "NOT_RUN",
                    },
                }
            )
            continue
        scale = _read_result(scale_path)
        scale_pass = _scale_acceptance(scale, gates)
        row = {
            "candidate_id": candidate_id,
            "ksp": candidate["ksp"],
            "pc": candidate["pc"],
            "small_non_regression": non_regression,
            "scale_a": {
                "status": scale["status"],
                "converged_reason": scale["converged_reason"],
                "iterations": scale["iterations"],
                "free_residual_relative": scale["free_residual_relative"],
                "force_balance_relative": scale["force_balance_relative"],
                "runtime_seconds": scale["runtime_seconds"],
                "matrix_sanity": scale["matrix_sanity"],
                "pass": scale_pass,
            },
        }
        rows.append(row)
        if selected is None and non_regression["pass"] and scale_pass:
            selected = candidate
            selected_small = small
            selected_scale = scale
    replay_rows: list[dict[str, Any]] = []
    if selected is not None:
        for replay_id in ("replay_1", "replay_2"):
            path = args.results_dir / f"scale_a_{selected['id']}_{replay_id}.json"
            if not path.exists():
                replay_rows.append({"id": replay_id, "status": "NOT_RUN"})
                continue
            replay = _read_result(path)
            assert selected_scale is not None
            row = {
                "id": replay_id,
                "same_iterations": replay["iterations"] == selected_scale["iterations"],
                "same_status": replay["status"] == selected_scale["status"],
                "same_partition": replay["partition"]["digest"] == selected_scale["partition"]["digest"],
                "residual_relative_difference": abs(float(replay["free_residual_relative"]) - float(selected_scale["free_residual_relative"])) / max(abs(float(selected_scale["free_residual_relative"])), 1.0),
                "reaction_resultant_relative_difference": _relative(replay["reaction_resultant"], selected_scale["reaction_resultant"]),
            }
            row["status"] = "PASS" if all(
                [row["same_iterations"], row["same_status"], row["same_partition"], row["residual_relative_difference"] <= gates["replay_relative_max"], row["reaction_resultant_relative_difference"] <= gates["replay_relative_max"]]
            ) else "FAIL"
            replay_rows.append(row)
    replay_pass = len(replay_rows) == 2 and all(row["status"] == "PASS" for row in replay_rows)
    replay_status = (
        "PASS"
        if replay_pass
        else "NOT_RUN_NO_SELECTED_CONFIGURATION"
        if selected is None
        else "FAIL"
    )
    original_failure = json.loads(ORIGINAL_SCALE_A.read_text(encoding="utf-8"))["result"]
    status = "REMEDIATED" if selected is not None and replay_pass else "STILL_FAIL_RUNTIME"
    evidence = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "contract_sha256": _contract_hash(),
        "original_failure_preserved": {
            "path": str(ORIGINAL_SCALE_A.relative_to(ROOT)),
            "status": original_failure["status"],
            "ksp": "CG",
            "pc": "JACOBI",
            "dof": original_failure["ndof"],
            "reason": original_failure["converged_reason"],
        },
        "matrix_diagnosis": next(
            (row["scale_a"]["matrix_sanity"] for row in rows if "matrix_sanity" in row.get("scale_a", {})),
            None,
        ),
        "candidates": rows,
        "selected": selected,
        "selected_small_case": selected_small,
        "selected_scale_a": selected_scale,
        "replays": replay_rows,
        "replay_determinism": replay_status,
        "scale_b": (
            json.loads(args.scale_b.read_text(encoding="utf-8"))["result"]
            if args.scale_b and args.scale_b.exists()
            else {"status": "NOT_RUN_NO_ACCEPTED_SCALE_A" if selected is None else "NOT_RUN"}
        ),
        "one_million_dof_status": "NOT_RUN_NO_ACCEPTED_SCALE_A" if selected is None else "NOT_RUN_RESOURCE_LIMIT",
        "automatic_solver_fallback": False,
        "numerical_source_changed": False,
        "element_formulation_changed": False,
        "maturity_changed": False,
        "historical_0_2_7_evidence_changed": False,
        "status": status,
    }
    _write_json(args.output, evidence)
    return 0 if status == "REMEDIATED" else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("serial", "mpi", "build"), required=True)
    parser.add_argument("--segments", type=int, default=1)
    parser.add_argument("--candidate")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--serial", type=Path)
    parser.add_argument("--results-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--scale-b", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.mode == "serial":
        return _run_serial(args)
    if args.mode == "mpi":
        if args.candidate is None:
            raise SystemExit("--candidate is required for mpi mode")
        return _run_mpi(args)
    if args.serial is None:
        raise SystemExit("--serial is required for build mode")
    return _build_evidence(args)


if __name__ == "__main__":
    raise SystemExit(main())
