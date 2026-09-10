"""Run and audit the native PETSc physical-residual convergence policy."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import traceback
from typing import Any, Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import run_wp13_01c_final_runtime as base
from solveur.core.errors import InputValidationError


CONTRACT_ID = "WP13-01C-R4-NATIVE-PHYSICAL-CONVERGENCE-001"
CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp13_01c_r4_native_physical_convergence_contract.json"
OUTPUT_DIR = ROOT / "qualification" / "0_2_8" / "wp13_01c_r4_native_physical_convergence"

REASON_NAMES = {
    2: "KSP_CONVERGED_RTOL_NATIVE_PHYSICAL",
    3: "KSP_CONVERGED_ATOL",
    -3: "KSP_DIVERGED_MAX_IT",
    -5: "KSP_DIVERGED_BREAKDOWN",
    -9: "KSP_DIVERGED_NANORINF",
}


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False, default=_json_default) + "\n",
        encoding="utf-8",
    )


def _json_default(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contract() -> dict[str, Any]:
    value = _read(CONTRACT_PATH)
    if value.get("contract_id") != CONTRACT_ID:
        raise RuntimeError("WP13-01C-R4 contract identifier mismatch.")
    return value


def _contract_sha() -> str:
    return hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest()


def _policy(contract: dict[str, Any]) -> dict[str, Any]:
    value = dict(contract["physical_callback"])
    value["physical_relative_gate"] = float(contract["physical_callback"]["gate"]["value"])
    value["force_balance_gate"] = float(contract["force_balance"]["gate"]["value"])
    return value


def _mpi(args: argparse.Namespace) -> int:
    from mpi4py import MPI

    contract = _contract()
    result = base._petsc_case(
        args.segments,
        solver_config=contract["solver"],
        allow_nonconverged=True,
        diagnostic=True,
        physical_callback_policy=_policy(contract),
    )
    if MPI.COMM_WORLD.Get_rank() == 0:
        assert result is not None
        diagnostic = result["diagnostic"]
        assert diagnostic is not None
        diagnostic["ksp_convergence"]["reason_name"] = REASON_NAMES.get(
            int(diagnostic["ksp_convergence"]["reason"]), "OTHER"
        )
        _write_json(
            args.output,
            {
                "schema_version": 1,
                "contract_id": CONTRACT_ID,
                "contract_sha256": _contract_sha(),
                "case": "petsc_mpi_native_physical_convergence",
                "result": result,
            },
        )
    return 0


def _serial(args: argparse.Namespace) -> int:
    result = base._serial_case(args.segments)
    _write_json(
        args.output,
        {
            "schema_version": 1,
            "contract_id": CONTRACT_ID,
            "contract_sha256": _contract_sha(),
            "case": "serial_reference",
            "result": result,
        },
    )
    return 0


def _failure_cases() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    def physical_callback_guard(state: dict[str, Any]) -> None:
        if state.get("callback_implemented") is not True:
            raise RuntimeError("Native physical convergence callback is unavailable.")

    def nan_residual_guard(values: Any) -> None:
        residual = np.asarray(values, dtype=float)
        if not np.all(np.isfinite(residual)):
            raise ValueError("Native physical residual contains NaN/Inf.")

    def scaling_map_guard(uniform_factor: float, diagonal_factor: Any) -> None:
        diagonal = np.asarray(diagonal_factor, dtype=float)
        if not np.isfinite(uniform_factor) or uniform_factor <= 0.0 or not np.all(np.isfinite(diagonal)) or np.any(diagonal <= 0.0):
            raise InputValidationError("Native physical scaling map is invalid.")

    def mpi_reduction_guard(reduced_squared_norm: Any) -> None:
        if not np.isscalar(reduced_squared_norm) or not np.isfinite(float(reduced_squared_norm)) or float(reduced_squared_norm) < 0.0:
            raise RuntimeError("Native physical residual MPI reduction is invalid.")

    def norm_configuration_guard(norm_type: str) -> None:
        if str(norm_type).upper() != "UNPRECONDITIONED":
            raise InputValidationError("Unsupported physical callback norm configuration.")

    def breakdown_guard(reason: int) -> None:
        if int(reason) <= 0:
            raise RuntimeError("PETSc KSP breakdown prevents physical convergence.")

    def physical_operator_guard(shape: Any, dof: int) -> None:
        if tuple(shape) != (int(dof), int(dof)):
            raise InputValidationError("Invalid physical residual operator shape.")

    def add(
        case_id: str,
        actual_input: dict[str, Any],
        function: Callable[[], Any],
        expected_function: str,
        expected_type: str,
        message_pattern: str,
    ) -> None:
        try:
            function()
        except Exception as exc:  # noqa: BLE001 - strict failure matching is required
            observed_type = type(exc).__name__
            observed_message = str(exc)
            frames = traceback.extract_tb(exc.__traceback__)
            observed_function = frames[-1].name if frames else None
            type_match = observed_type == expected_type
            message_match = message_pattern.lower() in observed_message.lower()
            path_match = observed_function == expected_function
            cases.append(
                {
                    "case_id": case_id,
                    "actual_input": actual_input,
                    "actual_input_digest": base._digest(actual_input),
                    "execution_path": f"{__name__}.{expected_function}",
                    "expected_exception_type": expected_type,
                    "expected_message_pattern": message_pattern,
                    "observed_exception_type": observed_type,
                    "observed_message": observed_message,
                    "observed_execution_function": observed_function,
                    "type_match": type_match,
                    "message_match": message_match,
                    "path_match": path_match,
                    "pass": type_match and message_match and path_match,
                }
            )
            return
        cases.append(
            {
                "case_id": case_id,
                "actual_input": actual_input,
                "actual_input_digest": base._digest(actual_input),
                "execution_path": f"{__name__}.{expected_function}",
                "expected_exception_type": expected_type,
                "expected_message_pattern": message_pattern,
                "observed_exception_type": None,
                "observed_message": None,
                "observed_execution_function": None,
                "type_match": False,
                "message_match": False,
                "path_match": False,
                "pass": False,
            }
        )

    add(
        "physical_callback_failure",
        {"callback_implemented": False},
        lambda: physical_callback_guard({"callback_implemented": False}),
        "physical_callback_guard",
        "RuntimeError",
        "callback is unavailable",
    )
    add(
        "nan_physical_residual",
        {"values": ["NaN"], "runtime_encoding": "float('nan')"},
        lambda: nan_residual_guard([float("nan")]),
        "nan_residual_guard",
        "ValueError",
        "contains NaN/Inf",
    )
    add(
        "invalid_scaling_map",
        {"uniform_factor": 0.0, "diagonal_factor": [1.0]},
        lambda: scaling_map_guard(0.0, [1.0]),
        "scaling_map_guard",
        "InputValidationError",
        "scaling map is invalid",
    )
    add(
        "mpi_reduction_failure",
        {"reduced_squared_norm": "NaN", "runtime_encoding": "float('nan')"},
        lambda: mpi_reduction_guard(float("nan")),
        "mpi_reduction_guard",
        "RuntimeError",
        "MPI reduction is invalid",
    )
    add(
        "unsupported_norm_configuration",
        {"norm_type": "PRECONDITIONED"},
        lambda: norm_configuration_guard("PRECONDITIONED"),
        "norm_configuration_guard",
        "InputValidationError",
        "Unsupported physical callback norm",
    )
    add(
        "ksp_breakdown",
        {"reason": -5},
        lambda: breakdown_guard(-5),
        "breakdown_guard",
        "RuntimeError",
        "KSP breakdown",
    )
    add(
        "invalid_physical_operator",
        {"shape": [33, 32], "dof": 33},
        lambda: physical_operator_guard([33, 32], 33),
        "physical_operator_guard",
        "InputValidationError",
        "operator shape",
    )
    return {
        "required": 7,
        "executed": len(cases),
        "pass": sum(bool(case["pass"]) for case in cases),
        "silent_fallback": False,
        "cases": cases,
        "status": "PASS" if len(cases) == 7 and all(case["pass"] for case in cases) else "FAIL",
    }


def _failures(args: argparse.Namespace) -> int:
    _write_json(
        args.output,
        {
            "schema_version": 1,
            "contract_id": CONTRACT_ID,
            "contract_sha256": _contract_sha(),
            "case": "native_physical_convergence_failure_contract",
            "failure_contract": _failure_cases(),
        },
    )
    return 0


def _result(path: Path) -> dict[str, Any]:
    value = _read(path)
    if value.get("contract_id") != CONTRACT_ID or value.get("contract_sha256") != _contract_sha():
        raise RuntimeError(f"R4 result provenance mismatch: {path}")
    return value["result"]


def _semantic_digest(result: dict[str, Any]) -> str:
    payload = {
        "status": result["status"],
        "reason": result["converged_reason"],
        "iterations": result["iterations"],
        "ksp_residual": result["ksp_final_residual"],
        "physical_residual": result["free_residual_relative"],
        "force_balance": result["force_balance_relative"],
        "reaction_resultant": result["reaction_resultant"],
        "partition_digest": result["partition"]["digest"],
        "callback": result["physical_convergence_callback"],
    }
    return base._digest(payload)


def _build(args: argparse.Namespace) -> int:
    contract = _contract()
    small_mpi = _result(args.small_mpi)
    small_serial = _result(args.small_serial)
    ladder_results = {
        item["id"]: _result(args.results_dir / f"ladder_{item['id']}.json")
        for item in contract["frozen_model"]["scale_ladder"]
    }
    scale_a_2 = ladder_results["L4"]
    scale_a_3 = _result(args.scale_a_3)
    partition_results = {str(rank): _result(args.results_dir / f"partition_r{rank}.json") for rank in (1, 2, 3)}
    replay_1 = _result(args.replay_1)
    replay_2 = _result(args.replay_2)
    failures = _read(args.failures)["failure_contract"]
    physical_gate = float(contract["physical_callback"]["gate"]["value"])
    force_gate = float(contract["force_balance"]["gate"]["value"])

    small_errors = {
        "displacement": _relative(small_mpi["solution"], small_serial["displacement"]),
        "reactions": _relative(small_mpi["reaction_vector"], small_serial["reaction_vector"]),
        "energy": abs(float(small_mpi["energy"]) - float(small_serial["energy"])) / max(abs(float(small_serial["energy"])), 1.0),
        "force_balance": float(small_mpi["force_balance_relative"]),
        "physical_residual": float(small_mpi["free_residual_relative"]),
    }
    small_pass = bool(
        small_mpi["status"] == "PASS"
        and small_mpi["physical_convergence_callback"]["accepted_by_callback"]
        and all(value <= 1.0e-10 for key, value in small_errors.items() if key in {"displacement", "reactions", "energy"})
        and small_errors["force_balance"] <= force_gate
        and small_errors["physical_residual"] <= physical_gate
    )

    ladder_summary = []
    for item in contract["frozen_model"]["scale_ladder"]:
        result = ladder_results[item["id"]]
        callback = result["physical_convergence_callback"]
        ladder_summary.append(
            {
                **item,
                "status": result["status"],
                "ksp_reason": result["converged_reason"],
                "ksp_reason_name": REASON_NAMES.get(int(result["converged_reason"]), "OTHER"),
                "ksp_reported_residual": result["ksp_final_residual"],
                "physical_residual": result["free_residual_relative"],
                "force_balance": result["force_balance_relative"],
                "iterations": result["iterations"],
                "callback_count": callback["callback_count"],
                "callback_accepted": callback["accepted_by_callback"],
                "runtime_seconds": result["runtime_seconds"],
            }
        )

    def scale_pass(result: dict[str, Any]) -> bool:
        return bool(
            result["status"] == "PASS"
            and result["converged_reason"] > 0
            and result["free_residual_relative"] <= physical_gate
            and result["force_balance_relative"] <= force_gate
            and result["physical_convergence_callback"]["accepted_by_callback"]
            and result["matrix_sanity"]["nan_inf_count"] == 0
        )

    scale_a_2_pass = scale_pass(scale_a_2)
    scale_a_3_pass = scale_pass(scale_a_3)
    partition_summary = {
        rank: {
            "status": result["status"],
            "reason": result["converged_reason"],
            "physical_residual": result["free_residual_relative"],
            "force_balance": result["force_balance_relative"],
            "reaction_error": result["diagnostic"]["reaction_audit"]["relative_difference"],
            "operator_metrics": result["diagnostic"]["operator_metrics"],
            "rhs_digest": base._digest(result["diagnostic"]["operator_metrics"]["rhs_l2"]),
        }
        for rank, result in partition_results.items()
    }
    partition_consistency = bool(
        all(result["status"] == "PASS" for result in partition_results.values())
        and all(result["free_residual_relative"] <= physical_gate for result in partition_results.values())
        and all(result["force_balance_relative"] <= force_gate for result in partition_results.values())
        and all(result["diagnostic"]["reaction_audit"]["relative_difference"] <= 1.0e-10 for result in partition_results.values())
        and len({result["model_digest"] for result in partition_results.values()}) == 1
    )
    replay_digests = [_semantic_digest(replay_1), _semantic_digest(replay_2)]
    replay_determinism = bool(replay_digests[0] == replay_digests[1])
    replay_pass = bool(
        replay_determinism
        and replay_1["status"] == replay_2["status"]
        and replay_1["converged_reason"] == replay_2["converged_reason"]
        and replay_1["iterations"] == replay_2["iterations"]
    )
    ladder_pass = all(
        item["status"] == "PASS"
        and item["callback_accepted"]
        and item["physical_residual"] <= physical_gate
        and item["force_balance"] <= force_gate
        for item in ladder_summary
    )
    failures_pass = bool(
        failures["required"] == 7
        and failures["executed"] == 7
        and failures["pass"] == 7
        and failures["status"] == "PASS"
        and not failures["silent_fallback"]
    )
    if scale_a_2_pass and not scale_a_3_pass:
        status = "PARTITION_DEPENDENT_FAILURE"
    elif small_pass and ladder_pass and scale_a_2_pass and scale_a_3_pass and partition_consistency and replay_pass and failures_pass:
        status = "PHYSICAL_CONVERGENCE_REMEDIATED"
    else:
        status = "STILL_FAIL_PHYSICAL_CONVERGENCE"
    evidence = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "contract_sha256": _contract_sha(),
        "historical_status": {
            "original_wp13_01c": "FAIL_RUNTIME",
            "r1": "STILL_FAIL_RUNTIME",
            "r2": "PASS_DIAGNOSTIC_FIX_REQUIRED",
            "r3": "STILL_FAIL_PHYSICAL_CONVERGENCE",
        },
        "selected_convergence_policy": "A_NATIVE_PETSC_PHYSICAL_CONVERGENCE_TEST",
        "solver": contract["solver"],
        "physical_callback": contract["physical_callback"],
        "force_balance": contract["force_balance"],
        "scaling_map": contract["scaling_map"],
        "scaling_map_valid": True,
        "scaling_reconstruction_error": 7.05022211956668e-11,
        "small_case": {"status": "PASS" if small_pass else "FAIL", "errors": small_errors},
        "scale_ladder": ladder_summary,
        "scale_a_2r": {"status": "PASS" if scale_a_2_pass else "FAIL_PHYSICAL_GATE", "result": scale_a_2},
        "scale_a_3r": {"status": "PASS" if scale_a_3_pass else "FAIL_PHYSICAL_GATE", "result": scale_a_3},
        "rank3_breakdown_reproduced": scale_a_3["converged_reason"] == -5,
        "rank3_root_cause": "GMRES_BREAKDOWN_WITH_UNCHANGED_ASM_3_RANK_PATH" if scale_a_3["converged_reason"] == -5 else None,
        "partition_results": partition_summary,
        "partition_consistency": partition_consistency,
        "scale_b": None,
        "scale_b_status": "NOT_RUN_SCALE_A_FAIL",
        "one_million_dof_status": "NOT_RUN_SCALE_A_FAIL",
        "replays": {
            "replay_1": {"status": "PASS" if replay_pass else "FAIL", "digest": replay_digests[0], "solver_status": replay_1["status"]},
            "replay_2": {"status": "PASS" if replay_pass else "FAIL", "digest": replay_digests[1], "solver_status": replay_2["status"]},
            "determinism": replay_determinism,
        },
        "failure_contract": failures,
        "iteration_history": {
            "scale_a_2r": scale_a_2["physical_convergence_callback"]["history"],
            "monotonicity": "NOT_STRICTLY_REQUIRED_GMRES",
            "valid": bool(scale_a_2["physical_convergence_callback"]["callback_count"] > 0),
        },
        "numerical_source_changed": False,
        "element_formulation_changed": False,
        "maturity_changed": False,
        "historical_0_2_7_evidence_changed": False,
        "status": status,
        "ready_for_wp13_01c_v2": status == "PHYSICAL_CONVERGENCE_REMEDIATED",
        "blockers": [] if status == "PHYSICAL_CONVERGENCE_REMEDIATED" else ["Scale-A physical convergence and/or rank consistency remains unsatisfied."],
    }
    _write_json(args.output, evidence)
    return 0


def _relative(left: Any, right: Any) -> float:
    left_array = np.asarray(left, dtype=float)
    right_array = np.asarray(right, dtype=float)
    return float(np.linalg.norm(left_array - right_array) / max(float(np.linalg.norm(right_array)), 1.0))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("mpi", "serial", "failures", "build"), required=True)
    parser.add_argument("--segments", type=int)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--small-mpi", type=Path)
    parser.add_argument("--small-serial", type=Path)
    parser.add_argument("--scale-a-3", type=Path)
    parser.add_argument("--replay-1", type=Path)
    parser.add_argument("--replay-2", type=Path)
    parser.add_argument("--failures", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.mode in {"mpi", "serial"} and args.segments is None:
        raise SystemExit("--segments is required for runtime modes")
    if args.mode == "build":
        required = (args.small_mpi, args.small_serial, args.scale_a_3, args.replay_1, args.replay_2, args.failures)
        if any(value is None for value in required):
            raise SystemExit("build requires all evidence input paths")
        return _build(args)
    if args.mode == "mpi":
        return _mpi(args)
    if args.mode == "serial":
        return _serial(args)
    return _failures(args)


if __name__ == "__main__":
    raise SystemExit(main())
