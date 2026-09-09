"""Diagnose physical residuals for the frozen WP13-01C Scale-A PETSc run."""

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
from solveur.core.assembly.assembler import GlobalAssembler


CONTRACT_ID = "WP13-01C-R2-PHYSICAL-RESIDUAL-DIAGNOSTIC-001"
CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp13_01c_r2_physical_residual_diagnostic_contract.json"
OUTPUT_DIR = ROOT / "qualification" / "0_2_8" / "wp13_01c_r2_physical_residual_diagnostic"
ORIGINAL_SCALE = ROOT / "qualification" / "0_2_8" / "wp13_01c_petsc_mpi_mixed_runtime" / "scale_a.json"
R1_EVIDENCE = ROOT / "qualification" / "0_2_8" / "wp13_01c_r1_ksp_remediation" / "evidence.json"


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
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False, default=_json_default) + "\n", encoding="utf-8")


def _contract() -> dict[str, Any]:
    value = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if value.get("contract_id") != CONTRACT_ID:
        raise RuntimeError("WP13-01C-R2 contract identifier mismatch.")
    return value


def _contract_hash() -> str:
    return hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest()


def _relative(left: float, right: float) -> float:
    return abs(float(left) - float(right)) / max(abs(float(right)), 1.0)


def _mpi(args: argparse.Namespace) -> int:
    from mpi4py import MPI

    contract = _contract()
    result = base._petsc_case(
        args.segments,
        solver_config=contract["diagnostic_solver"],
        allow_nonconverged=True,
        diagnostic=True,
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
                "contract_sha256": _contract_hash(),
                "case": "petsc_mpi_diagnostic",
                "result": result,
            },
        )
    return 0


def _serial_operator(args: argparse.Namespace) -> int:
    model = base._full_model(args.segments)
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    stiffness = assembler.assemble_stiffness(model, dofs).tocsr()
    loads = np.asarray(assembler.assemble_loads(model, dofs), dtype=float)
    diagonal = np.asarray(stiffness.diagonal(), dtype=float)
    row_sum = np.asarray(stiffness.sum(axis=1), dtype=float).reshape(-1)
    indices = np.arange(dofs.ndof, dtype=float) + 1.0
    metrics = {
        "shape": [dofs.ndof, dofs.ndof],
        "nnz": int(stiffness.nnz),
        "frobenius_norm": float(math.sqrt(float(stiffness.multiply(stiffness).sum()))),
        "trace": float(np.sum(diagonal)),
        "row_sum_l2": float(np.linalg.norm(row_sum)),
        "row_sum_weighted": float(np.dot(indices, row_sum)),
        "diagonal_weighted": float(np.dot(indices, diagonal)),
        "rhs_l2": float(np.linalg.norm(loads)),
        "rhs_sum": float(np.sum(loads)),
        "rhs_weighted": float(np.dot(indices, loads)),
    }
    fixed = base._fixed_dofs(args.segments)
    _write_json(
        args.output,
        {
            "schema_version": 1,
            "contract_id": CONTRACT_ID,
            "contract_sha256": _contract_hash(),
            "case": "serial_operator_diagnostic",
            "operator_metrics": metrics,
            "bc": {"fixed_dof_count": int(fixed.size), "prescribed_values": "all_zero"},
        },
    )
    return 0


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _operator_comparison(serial: dict[str, Any], petsc: dict[str, Any], gate: float) -> dict[str, Any]:
    serial_metrics = serial["operator_metrics"]
    petsc_metrics = petsc["result"]["diagnostic"]["operator_metrics"]
    operator_keys = ("frobenius_norm", "trace", "row_sum_l2", "row_sum_weighted", "diagonal_weighted")
    rhs_keys = ("rhs_l2", "rhs_sum", "rhs_weighted")
    operator_errors = {key: _relative(petsc_metrics[key], serial_metrics[key]) for key in operator_keys}
    rhs_errors = {key: _relative(petsc_metrics[key], serial_metrics[key]) for key in rhs_keys}
    return {
        "operator_errors": operator_errors,
        "rhs_errors": rhs_errors,
        "operator_equivalence": all(value <= gate for value in operator_errors.values()),
        "rhs_equivalence": all(value <= gate for value in rhs_errors.values()),
        "serial_nnz": serial_metrics["nnz"],
        "petsc_nnz": int(sum(item["nz_used"] for item in petsc["result"]["preallocation_runtime"]["mat_info_local"]["by_rank"])),
    }


def _build(args: argparse.Namespace) -> int:
    contract = _contract()
    root = args.results_dir
    ladder: list[dict[str, Any]] = []
    for item in contract["ladder"]:
        payload = _read(root / f"ladder_{item['id']}.json")["result"]
        diag = payload["diagnostic"]
        assert diag is not None
        ladder.append(
            {
                **item,
                "ksp_reason": diag["ksp_convergence"]["reason"],
                "ksp_reason_name": diag["ksp_convergence"]["reason_name"],
                "ksp_final_residual": diag["ksp_convergence"]["final_reported_residual"],
                "true_relative_residual": diag["physical_residual"]["true_relative_residual"],
                "force_balance_relative": payload["force_balance_relative"],
                "reaction_direct_distributed_relative": diag["reaction_audit"]["relative_difference"],
                "scaled_to_physical_reconstruction_relative": diag["physical_residual"]["scaled_to_physical_reconstruction_relative"],
            }
        )
    partitions = {
        str(rank): _read(root / f"partition_r{rank}.json")["result"]
        for rank in contract["partition_dependence"]["ranks"]
    }
    serial_operator = _read(root / "operator_serial.json")
    operator_petsc_1 = _read(root / "operator_petsc_r1.json")
    operator_petsc_2 = _read(root / "operator_petsc_r2.json")
    operator_comparison = {
        "rank_1": _operator_comparison(serial_operator, operator_petsc_1, contract["diagnostic_gates"]["operator_scalar_relative_max"]),
        "rank_2": _operator_comparison(serial_operator, operator_petsc_2, contract["diagnostic_gates"]["operator_scalar_relative_max"]),
    }
    scale_a_payload = _read(root / "ladder_L4.json")["result"]
    scale_diag = scale_a_payload["diagnostic"]
    assert scale_diag is not None
    first_failure = next(
        (
            item["id"]
            for item in ladder
            if item["true_relative_residual"] > contract["diagnostic_gates"]["physical_reference_residual_relative_max"]
            or item["force_balance_relative"] > contract["diagnostic_gates"]["physical_reference_force_balance_relative_max"]
        ),
        "NONE",
    )
    assembly_pass = all(
        item["status"] == "PASS" for item in scale_diag["assembly_conservation"].values()
    ) and scale_diag["dropped_element_contributions"] == 0 and scale_diag["duplicate_element_contributions"] == 0
    reconstruction_difference_l2 = (
        scale_diag["physical_residual"]["free_dof_residual_l2"]
        * scale_diag["physical_residual"]["scaled_to_physical_reconstruction_relative"]
    )
    reconstruction_load_relative = reconstruction_difference_l2 / max(
        scale_diag["operator_metrics"]["rhs_l2"], 1.0
    )
    reconciliation_pass = (
        reconstruction_load_relative
        <= contract["diagnostic_gates"]["scaled_to_physical_residual_reconstruction_relative_max"]
    )
    distributed_integrity_pass = bool(
        assembly_pass
        and scale_diag["load_audit"]["difference"] == 0.0
        and scale_diag["bc_audit"]["row_difference"] == 0
        and scale_diag["bc_audit"]["rhs_difference"] == 0.0
        and scale_diag["reaction_audit"]["relative_difference"]
        <= contract["diagnostic_gates"]["reaction_direct_distributed_relative_max"]
        and scale_diag["solution_synchronization"]["owned_scatter_max_difference"] == 0.0
        and not scale_diag["solution_synchronization"]["stale_ghost_values_found"]
    )
    partition_reference = partitions["1"]["diagnostic"]
    assert partition_reference is not None
    partition_errors = {
        rank: {
            "operator_frobenius_relative": _relative(
                payload["diagnostic"]["operator_metrics"]["frobenius_norm"],
                partition_reference["operator_metrics"]["frobenius_norm"],
            ),
            "rhs_relative": _relative(
                payload["diagnostic"]["operator_metrics"]["rhs_l2"],
                partition_reference["operator_metrics"]["rhs_l2"],
            ),
            "true_residual": payload["diagnostic"]["physical_residual"]["true_relative_residual"],
            "reaction_resultant": payload["diagnostic"]["reaction_audit"]["distributed_resultant"],
        }
        for rank, payload in partitions.items()
    }
    root_cause = "KSP_NORM_MISMATCH" if reconciliation_pass and distributed_integrity_pass else "UNKNOWN"
    evidence = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "contract_sha256": _contract_hash(),
        "original_wp13_01c": _read(ORIGINAL_SCALE)["result"],
        "r1_status": _read(R1_EVIDENCE)["status"],
        "scale_a": scale_a_payload,
        "ladder": ladder,
        "first_failure_scale": first_failure,
        "partition_dependence": partition_errors,
        "operator_comparison": operator_comparison,
        "root_cause": root_cause,
        "root_cause_evidence": {
            "ksp_norm_is_scaled_constrained": scale_diag["ksp_convergence"]["norm_type"],
            "physical_residual_is_original_k_u_minus_f": True,
            "scaled_to_physical_reconstruction_relative_to_free_residual": scale_diag["physical_residual"]["scaled_to_physical_reconstruction_relative"],
            "scaled_to_physical_reconstruction_relative_to_load": reconstruction_load_relative,
            "distributed_integrity_pass": distributed_integrity_pass,
            "physical_gate_failed": scale_diag["physical_residual"]["true_relative_residual"]
            > contract["diagnostic_gates"]["physical_reference_residual_relative_max"],
        },
        "fix_required": True,
        "fix_scope": "WP13-01C-R3: predeclare a physical-residual-aware convergence policy or mapped scaled tolerance; retain the same FEM model and gates.",
        "numerical_source_changed": False,
        "element_formulation_changed": False,
        "maturity_changed": False,
        "historical_0_2_7_evidence_changed": False,
        "status": "PASS_DIAGNOSTIC_FIX_REQUIRED" if root_cause == "KSP_NORM_MISMATCH" else "DIAGNOSTIC_INCONCLUSIVE",
    }
    _write_json(args.output, evidence)
    return 0 if evidence["status"] == "PASS_DIAGNOSTIC_FIX_REQUIRED" else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("mpi", "serial-operator", "build"), required=True)
    parser.add_argument("--segments", type=int)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.mode in {"mpi", "serial-operator"} and args.segments is None:
        raise SystemExit("--segments is required for runtime diagnostic modes")
    if args.mode == "mpi":
        return _mpi(args)
    if args.mode == "serial-operator":
        return _serial_operator(args)
    return _build(args)


if __name__ == "__main__":
    raise SystemExit(main())
