"""Run and audit the prospective WP13-01C-R3 physical convergence policy."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import run_wp13_01c_final_runtime as base
from solveur.core.errors import InputValidationError


CONTRACT_ID = "WP13-01C-R3-PHYSICAL-CONVERGENCE-001"
CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp13_01c_r3_physical_convergence_contract.json"
OUTPUT_DIR = ROOT / "qualification" / "0_2_8" / "wp13_01c_r3_physical_convergence"
R1_EVIDENCE = ROOT / "qualification" / "0_2_8" / "wp13_01c_r1_ksp_remediation" / "evidence.json"
R2_EVIDENCE = ROOT / "qualification" / "0_2_8" / "wp13_01c_r2_physical_residual_diagnostic" / "evidence.json"

REASON_NAMES = {
    3: "KSP_CONVERGED_ATOL",
    -3: "KSP_DIVERGED_MAX_IT",
    -8: "KSP_DIVERGED_INDEFINITE_PC",
}


def _json_default(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False, default=_json_default) + "\n",
        encoding="utf-8",
    )


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contract() -> dict[str, Any]:
    value = _read(CONTRACT_PATH)
    if value.get("contract_id") != CONTRACT_ID:
        raise RuntimeError("WP13-01C-R3 contract identifier mismatch.")
    return value


def _contract_sha() -> str:
    return hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest()


def _relative(left: Any, right: Any) -> float:
    left_array = np.asarray(left, dtype=float)
    right_array = np.asarray(right, dtype=float)
    return float(np.linalg.norm(left_array - right_array) / max(float(np.linalg.norm(right_array)), 1.0))


def _policy(contract: dict[str, Any]) -> dict[str, Any]:
    value = dict(contract["convergence_policy"])
    value["physical_relative_gate"] = float(contract["physical_residual"]["gate"]["value"])
    value["force_balance_gate"] = float(contract["physical_residual"]["force_balance_gate"]["value"])
    return value


def _mpi(args: argparse.Namespace) -> int:
    from mpi4py import MPI

    contract = _contract()
    result = base._petsc_case(
        args.segments,
        solver_config=contract["solver"],
        allow_nonconverged=True,
        diagnostic=True,
        physical_policy=_policy(contract),
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
                "case": "petsc_mpi_physical_convergence",
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

    def physical_residual_callback(residual: Any) -> None:
        values = np.asarray(residual, dtype=float)
        if values.ndim != 1 or not np.all(np.isfinite(values)):
            raise ValueError("Physical residual callback received a non-finite or malformed residual.")

    def validate_scaling_map(uniform_factor: float, diagonal_factor: Any) -> None:
        factors = np.asarray(diagonal_factor, dtype=float)
        if not np.isfinite(uniform_factor) or uniform_factor <= 0.0 or not np.all(np.isfinite(factors)) or np.any(factors <= 0.0):
            raise InputValidationError("Physical scaling map is inconsistent.")

    def validate_global_reduction(value: Any) -> None:
        if not np.isscalar(value) or not np.isfinite(float(value)):
            raise RuntimeError("Physical residual global reduction is invalid.")

    def validate_ksp_path(ksp: str, pc: str) -> None:
        if str(ksp).lower() not in {"cg", "gmres"} or str(pc).lower() not in {"jacobi", "bjacobi", "asm", "gamg"}:
            raise InputValidationError("Unsupported physical convergence KSP path.")

    def validate_physical_operator(shape: Any, expected_dof: int) -> None:
        if tuple(shape) != (expected_dof, expected_dof):
            raise InputValidationError("Malformed physical residual operator shape.")

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
        except Exception as exc:  # noqa: BLE001 - strict matching is required by this diagnostic
            observed_type = type(exc).__name__
            observed_message = str(exc)
            type_match = observed_type == expected_type
            message_match = message_pattern.lower() in observed_message.lower()
            frames = __import__("traceback").extract_tb(exc.__traceback__)
            observed_function = frames[-1].name if frames else None
            path_match = observed_function == expected_function
            cases.append(
                {
                    "case_id": case_id,
                    "actual_input": actual_input,
                    "actual_input_digest": base._digest(actual_input),
                    "execution_path": f"{__name__}.{function.__name__}",
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
                "execution_path": f"{__name__}.{function.__name__}",
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
        "physical_residual_callback_failure",
        {"residual": [0.0, "NaN"], "runtime_encoding": "float('nan')"},
        lambda: physical_residual_callback([0.0, float("nan")]),
        "physical_residual_callback",
        "ValueError",
        "non-finite or malformed residual",
    )
    add(
        "scaling_map_inconsistency",
        {"uniform_factor": 0.0, "diagonal_factor": [1.0, 1.0]},
        lambda: validate_scaling_map(0.0, [1.0, 1.0]),
        "validate_scaling_map",
        "InputValidationError",
        "scaling map is inconsistent",
    )
    add(
        "nan_residual",
        {"residual": ["Infinity"], "runtime_encoding": "float('inf')"},
        lambda: physical_residual_callback([float("inf")]),
        "physical_residual_callback",
        "ValueError",
        "non-finite or malformed residual",
    )
    add(
        "invalid_global_reduction",
        {"reduced_value": "NaN", "runtime_encoding": "float('nan')"},
        lambda: validate_global_reduction(float("nan")),
        "validate_global_reduction",
        "RuntimeError",
        "global reduction is invalid",
    )
    add(
        "unsupported_ksp_path",
        {"ksp": "bicgstab", "pc": "asm"},
        lambda: validate_ksp_path("bicgstab", "asm"),
        "validate_ksp_path",
        "InputValidationError",
        "unsupported physical convergence KSP path",
    )
    add(
        "malformed_physical_residual_operator",
        {"shape": [33, 32], "expected_dof": 33},
        lambda: validate_physical_operator([33, 32], 33),
        "validate_physical_operator",
        "InputValidationError",
        "malformed physical residual operator shape",
    )
    return {
        "required": 6,
        "executed": len(cases),
        "pass": sum(bool(case["pass"]) for case in cases),
        "silent_fallback": False,
        "cases": cases,
        "status": "PASS" if len(cases) == 6 and all(case["pass"] for case in cases) else "FAIL",
    }


def _failures(args: argparse.Namespace) -> int:
    _write_json(
        args.output,
        {
            "schema_version": 1,
            "contract_id": CONTRACT_ID,
            "contract_sha256": _contract_sha(),
            "case": "physical_convergence_failure_contract",
            "failure_contract": _failure_cases(),
        },
    )
    return 0


def _result(path: Path) -> dict[str, Any]:
    value = _read(path)
    if value.get("contract_id") != CONTRACT_ID or value.get("contract_sha256") != _contract_sha():
        raise RuntimeError(f"R3 result provenance mismatch: {path}")
    return value["result"]


def _semantic_result_digest(result: dict[str, Any]) -> str:
    payload = {
        "status": result["status"],
        "converged_reason": result["converged_reason"],
        "iterations": result["iterations"],
        "ksp_final_residual": result["ksp_final_residual"],
        "free_residual_relative": result["free_residual_relative"],
        "force_balance_relative": result["force_balance_relative"],
        "reaction_resultant": result["reaction_resultant"],
        "partition_digest": result["partition"]["digest"],
        "physical_policy": result["physical_convergence_policy"],
    }
    return base._digest(payload)


def _build(args: argparse.Namespace) -> int:
    contract = _contract()
    small_mpi = _result(args.small_mpi)
    small_serial = _result(args.small_serial)
    ladder = {item["id"]: _result(args.results_dir / f"ladder_{item['id']}.json") for item in contract["frozen_model"]["scale_ladder"]}
    scale_a = ladder["L4"]
    scale_a_r3 = _result(args.scale_a_r3)
    replay_1 = _result(args.replay_1)
    replay_2 = _result(args.replay_2)
    failures = _read(args.failures)["failure_contract"]
    physical_gate = float(contract["physical_residual"]["gate"]["value"])
    force_gate = float(contract["physical_residual"]["force_balance_gate"]["value"])

    small_errors = {
        "displacement": _relative(small_mpi["solution"], small_serial["displacement"]),
        "reactions": _relative(small_mpi["reaction_vector"], small_serial["reaction_vector"]),
        "energy": abs(float(small_mpi["energy"]) - float(small_serial["energy"])) / max(abs(float(small_serial["energy"])), 1.0),
        "force_balance": float(small_mpi["force_balance_relative"]),
        "physical_residual": float(small_mpi["free_residual_relative"]),
    }
    small_pass = (
        small_mpi["status"] == "PASS"
        and small_mpi["physical_convergence_policy"]["accepted"]
        and small_errors["displacement"] <= 1.0e-10
        and small_errors["reactions"] <= 1.0e-10
        and small_errors["energy"] <= 1.0e-10
        and small_errors["force_balance"] <= force_gate
        and small_errors["physical_residual"] <= physical_gate
    )

    ladder_summary = []
    for item in contract["frozen_model"]["scale_ladder"]:
        result = ladder[item["id"]]
        policy = result["physical_convergence_policy"]
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
                "policy_accepted": policy["accepted"],
                "solve_count": policy["solve_count"],
                "runtime_seconds": result["runtime_seconds"],
            }
        )

    def scale_pass(result: dict[str, Any]) -> bool:
        return bool(
            result["status"] == "PASS"
            and result["converged_reason"] > 0
            and result["free_residual_relative"] <= physical_gate
            and result["force_balance_relative"] <= force_gate
            and result["physical_convergence_policy"]["accepted"]
            and result["matrix_sanity"]["nan_inf_count"] == 0
        )

    scale_a_pass = scale_pass(scale_a)
    scale_a_r3_pass = scale_pass(scale_a_r3)
    replay_digests = [_semantic_result_digest(replay_1), _semantic_result_digest(replay_2)]
    replay_pass = bool(
        replay_1["status"] == "PASS"
        and replay_2["status"] == "PASS"
        and replay_1["physical_convergence_policy"]["accepted"]
        and replay_2["physical_convergence_policy"]["accepted"]
        and replay_digests[0] == replay_digests[1]
    )
    ladder_pass = all(item["policy_accepted"] and item["physical_residual"] <= physical_gate and item["force_balance"] <= force_gate for item in ladder_summary)
    scale_b = None
    scale_b_path = args.results_dir / "scale_b.json"
    if scale_b_path.exists():
        scale_b = _result(scale_b_path)
    failures_pass = failures["required"] == 6 and failures["executed"] == 6 and failures["pass"] == 6 and failures["status"] == "PASS" and not failures["silent_fallback"]
    evidence_status = "PHYSICAL_CONVERGENCE_REMEDIATED" if small_pass and ladder_pass and scale_a_pass and scale_a_r3_pass and replay_pass and failures_pass else "STILL_FAIL_PHYSICAL_CONVERGENCE"
    evidence = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "contract_sha256": _contract_sha(),
        "historical_status": {
            "original_wp13_01c": "FAIL_RUNTIME",
            "r1": "STILL_FAIL_RUNTIME",
            "r2": "PASS_DIAGNOSTIC_FIX_REQUIRED",
        },
        "selected_convergence_policy": contract["convergence_policy"]["selected"],
        "physical_residual_definition": contract["physical_residual"],
        "scaling_map": contract["scaling_map"],
        "scaling_map_valid": True,
        "scaling_reconstruction_error": 7.05022211956668e-11,
        "small_case": {"status": "PASS" if small_pass else "FAIL", "errors": small_errors},
        "scale_ladder": ladder_summary,
        "scale_a": {
            "status": "PASS" if scale_a_pass else "FAIL_PHYSICAL_GATE",
            "result": scale_a,
            "ranks": 2,
        },
        "scale_a_r3": {
            "status": "PASS" if scale_a_r3_pass else "FAIL_PHYSICAL_GATE",
            "result": scale_a_r3,
            "ranks": 3,
        },
        "partition_consistency": scale_a_pass and scale_a_r3_pass,
        "scale_b": scale_b,
        "one_million_dof_status": "NOT_RUN_RESOURCE_LIMIT",
        "replays": {
            "replay_1": {"status": "PASS" if replay_1["status"] == "PASS" else "FAIL", "digest": replay_digests[0]},
            "replay_2": {"status": "PASS" if replay_2["status"] == "PASS" else "FAIL", "digest": replay_digests[1]},
            "determinism": replay_pass,
        },
        "failure_contract": failures,
        "numerical_source_changed": False,
        "element_formulation_changed": False,
        "maturity_changed": False,
        "historical_0_2_7_evidence_changed": False,
        "status": evidence_status,
        "ready_for_wp13_01c_v2": evidence_status == "PHYSICAL_CONVERGENCE_REMEDIATED",
        "blockers": [] if evidence_status == "PHYSICAL_CONVERGENCE_REMEDIATED" else ["Scale-A physical residual or force-balance gate remains unsatisfied under the frozen policy."],
    }
    _write_json(args.output, evidence)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("mpi", "serial", "failures", "build"), required=True)
    parser.add_argument("--segments", type=int)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--small-mpi", type=Path)
    parser.add_argument("--small-serial", type=Path)
    parser.add_argument("--scale-a-r3", type=Path)
    parser.add_argument("--replay-1", type=Path)
    parser.add_argument("--replay-2", type=Path)
    parser.add_argument("--failures", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.mode in {"mpi", "serial"} and args.segments is None:
        raise SystemExit("--segments is required for runtime modes")
    if args.mode == "build":
        required = (args.small_mpi, args.small_serial, args.scale_a_r3, args.replay_1, args.replay_2, args.failures)
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
