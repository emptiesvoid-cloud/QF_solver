"""Validate archived NAFEMS identities and compare J22 supervisor output to J19."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import psutil
import scipy
from scipy.sparse import csr_matrix

from research.j19.checkpoint import write_atomic_json


ROOT = Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative_path(path: Path, root: Path = ROOT) -> str:
    return Path(path).resolve().relative_to(root.resolve()).as_posix()


def _matrix_csr_sha256(matrix: csr_matrix) -> str:
    digest = hashlib.sha256()
    digest.update(np.asarray(matrix.shape, dtype=np.int64).tobytes())
    digest.update(str(matrix.indptr.dtype).encode("ascii"))
    digest.update(str(matrix.indices.dtype).encode("ascii"))
    digest.update(str(matrix.data.dtype).encode("ascii"))
    digest.update(np.ascontiguousarray(matrix.indptr).view(np.uint8).tobytes())
    digest.update(np.ascontiguousarray(matrix.indices).view(np.uint8).tobytes())
    digest.update(np.ascontiguousarray(matrix.data).view(np.uint8).tobytes())
    return digest.hexdigest()


def _vector_sha256(vector: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(vector).view(np.uint8).tobytes()).hexdigest()


def _load_j19(j19_path: Path) -> dict[str, Any]:
    return json.loads(Path(j19_path).read_text(encoding="utf-8"))


def _verify_preflight(contract: dict[str, Any], contract_path: Path, j19: dict[str, Any]) -> list[dict[str, Any]]:
    for relative, expected in contract["source_hashes"].items():
        if sha256_file(ROOT / relative) != expected:
            raise ValueError(f"source SHA-256 mismatch: {relative}")
    for group in ("j21_preparation_contract", "j19_contract", "j19_result"):
        record = contract["historical_sources"][group]
        if sha256_file(ROOT / record["path"]) != record["sha256"]:
            raise ValueError(f"historical source SHA-256 mismatch: {record['path']}")
    if sha256_file(contract_path) != contract["contract_sha256"]:
        raise ValueError("frozen contract SHA-256 mismatch")
    if j19.get("contract_id") != "J19-NAFEMS13H-ARCHIVED-REPLAY-003" or j19.get("run_state") != "COMPLETE":
        raise ValueError("J19 source result has an unexpected identity or state")

    j19_by_frequency = {float(row["frequency_hz"]): row for row in j19["results"]}
    identities: list[dict[str, Any]] = []
    for case in contract["cases"]:
        input_path = ROOT / case["input_path"]
        if sha256_file(input_path) != case["input_sha256"]:
            raise ValueError(f"archive SHA-256 mismatch: {case['input_path']}")
        with np.load(input_path, allow_pickle=False) as archive:
            matrix_values = np.asarray(archive["impedance_real"], dtype=np.float64) + 1j * np.asarray(
                archive["impedance_imag"], dtype=np.float64
            )
            rhs = np.asarray(archive["rhs_real"], dtype=np.float64) + 1j * np.asarray(
                archive["rhs_imag"], dtype=np.float64
            )
            x_unscaled = np.asarray(archive["x_unscaled_real"], dtype=np.float64) + 1j * np.asarray(
                archive["x_unscaled_imag"], dtype=np.float64
            )
        matrix = csr_matrix(matrix_values, dtype=np.complex128)
        matrix_hash = _matrix_csr_sha256(matrix)
        rhs_hash = _vector_sha256(rhs)
        x_hash = _vector_sha256(x_unscaled)
        if (
            list(matrix.shape) != case["matrix_shape"]
            or int(matrix.nnz) != case["stored_entries"]
            or matrix_hash != case["matrix_csr_sha256"]
            or rhs_hash != case["rhs_values_sha256"]
            or x_hash != case["archived_x_unscaled_sha256"]
        ):
            raise ValueError(f"array fingerprint mismatch: {case['case_id']}")
        old = j19_by_frequency.get(float(case["frequency_hz"]))
        if old is None:
            raise ValueError(f"J19 result is missing frequency {case['frequency_hz']}")
        exact = old["exact_represented_system"]
        solved_vector = np.asarray(old["solution_real"], dtype=np.float64) + 1j * np.asarray(
            old["solution_imag"], dtype=np.float64
        )
        solved_vector_hash = _vector_sha256(solved_vector)
        if (
            old["input_sha256"] != case["input_sha256"]
            or old["current_guard_outcome"] != case["historical_guard_outcome"]
            or exact["status"] != case["historical_exact_outcome"]
            or old["matrix_csr_sha256"] != matrix_hash
            or old["rhs_values_sha256"] != rhs_hash
            or old["solution_values_sha256"] != solved_vector_hash
            or exact["relative_residual_display_only"] != case["j19_exact_relative_residual"]
        ):
            raise ValueError(f"J19 provenance mismatch: {case['case_id']}")
        identities.append({
            "case_id": case["case_id"],
            "frequency_hz": case["frequency_hz"],
            "input_path": case["input_path"],
            "input_sha256": case["input_sha256"],
            "matrix_shape": list(matrix.shape),
            "stored_entries": int(matrix.nnz),
            "matrix_csr_sha256": matrix_hash,
            "rhs_values_sha256": rhs_hash,
            "evaluated_archived_x_unscaled_sha256": x_hash,
            "j19_recomputed_solution_sha256": solved_vector_hash,
            "j19_relative_solution_difference_inf_vs_unscaled": old[
                "relative_solution_difference_inf_vs_archived_unscaled"
            ],
            "historical_guard_outcome": old["current_guard_outcome"],
            "historical_exact_outcome": exact["status"],
            "historical_exact_relative_residual": exact["relative_residual_display_only"],
            "historical_guard_upper_bound": old["current_guard_diagnostics"]["relative_residual_upper_bound"],
        })
    return identities


def _preflight_payload(contract: dict[str, Any], identities: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "qfsolver-j22-nafems-preflight-v1",
        "contract_id": contract["contract_id"],
        "contract_sha256": contract["contract_sha256"],
        "source_code_commit": contract["baseline"]["source_code_commit"],
        "state": "PREFLIGHT_PASS_NO_EVALUATION_STARTED",
        "classification": "ARCHIVE_POSTPROCESSING_ONLY_NO_ASSEMBLY_OR_SOLVE",
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "psutil": psutil.__version__,
            "available_memory_bytes": psutil.virtual_memory().available,
        },
        "identities": identities,
    }


def _comparison_payload(
    contract: dict[str, Any],
    identities: list[dict[str, Any]],
    j19: dict[str, Any],
    run: dict[str, Any],
) -> dict[str, Any]:
    if run.get("contract_id") != contract["contract_id"] or run.get("contract_sha256") != contract["contract_sha256"]:
        raise ValueError("supervisor journal does not match the frozen J22 contract")
    if run.get("run_status") != "COMPLETE":
        raise ValueError(f"supervisor run did not complete: {run.get('run_status')}")
    identity_by_case = {item["case_id"]: item for item in identities}
    j19_by_frequency = {float(row["frequency_hz"]): row for row in j19["results"]}
    output_cases: list[dict[str, Any]] = []
    for case in contract["cases"]:
        supervisor_case = next((item for item in run["cases"] if item["case_id"] == case["case_id"]), None)
        if supervisor_case is None:
            raise ValueError(f"supervisor journal is missing {case['case_id']}")
        old = j19_by_frequency[float(case["frequency_hz"])]
        exact_result = supervisor_case.get("exact_result", {})
        identity = identity_by_case[case["case_id"]]
        new_relative = exact_result.get("relative_residual_display")
        old_relative = old["exact_represented_system"]["relative_residual_display_only"]
        relative_delta = None if new_relative is None else str(abs(Decimal(new_relative) - Decimal(old_relative)))
        output_cases.append({
            **identity,
            "supervisor_status": supervisor_case["supervisor_status"],
            "prospective_exact_status": supervisor_case["exact_status"],
            "prospective_reason": supervisor_case["reason"],
            "prospective_relative_residual_display": new_relative,
            "historical_j19_relative_residual_display": old_relative,
            "absolute_relative_residual_display_difference": relative_delta,
            "prospective_matrix_dimension": exact_result.get("dimension"),
            "prospective_stored_entries": exact_result.get("stored_entries"),
            "matrix_fingerprint_matches_j19": identity["matrix_csr_sha256"] == old["matrix_csr_sha256"],
            "rhs_fingerprint_matches_j19": identity["rhs_values_sha256"] == old["rhs_values_sha256"],
            "archived_vector_used": "x_unscaled_real + 1j*x_unscaled_imag",
            "j19_vector_used": "new sparse direct solution stored in replay.json",
            "wall_seconds_supervisor": supervisor_case.get("elapsed_seconds"),
            "exact_worker_seconds": exact_result.get("elapsed_seconds"),
            "sampled_peak_rss_bytes": supervisor_case.get("peak_rss_bytes_sampled"),
            "termination_confirmed": supervisor_case.get("termination_confirmed"),
        })
    return {
        "schema": "qfsolver-j22-nafems-j19-comparison-v1",
        "contract_id": contract["contract_id"],
        "contract_sha256": contract["contract_sha256"],
        "j19_result_sha256": contract["historical_sources"]["j19_result"]["sha256"],
        "supervisor_run_status": run["run_status"],
        "classification": "SUPERVISED_EXACT_RESIDUAL_OF_ARCHIVED_UNSCALED_VECTORS; NO_FEM_ASSEMBLY_OR_HARMONIC_SOLVE",
        "historical_guard_statuses_unchanged": True,
        "cases": output_cases,
        "interpretation": "Exact residual statuses apply to the archived binary matrix, RHS, and x_unscaled vector. J19's exact check used its newly recomputed direct solution; the tiny vector differences are explicitly recorded. Neither run validates the physical model or matrix assembly.",
    }


def _write_manifest(output: Path, contract: dict[str, Any]) -> None:
    files = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            files[path.relative_to(output).as_posix()] = {
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
    write_atomic_json(output / "artifact_manifest.json", {
        "schema": "qfsolver-j22-nafems-artifact-manifest-v1",
        "contract_id": contract["contract_id"],
        "contract_path": _relative_path(ROOT / "research/j22/contracts/nafems13h_supervised_recheck_001.json"),
        "contract_sha256": contract["contract_sha256"],
        "files": files,
        "limitations": [
            "Archived represented-system residual check only; no FEM assembly or harmonic solve.",
            "J19 used a recomputed solution vector; this run evaluates archived x_unscaled.",
            "RSS is sampled and soft, and Windows process supervision was tested only on this host.",
        ],
    })


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--j19-result", type=Path, required=True)
    parser.add_argument("--stage", choices=("preflight", "compare", "manifest"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run", type=Path)
    args = parser.parse_args(argv)
    contract_path = args.contract if args.contract.is_absolute() else ROOT / args.contract
    j19_path = args.j19_result if args.j19_result.is_absolute() else ROOT / args.j19_result
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    target = output / {
        "preflight": "preflight.json",
        "compare": "comparison.json",
        "manifest": "artifact_manifest.json",
    }[args.stage]
    if target.exists():
        raise FileExistsError(f"refusing to overwrite prior J22 artifact: {target.name}")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["contract_sha256"] = sha256_file(contract_path)
    j19 = _load_j19(j19_path)
    if args.stage == "preflight":
        identities = _verify_preflight(contract, contract_path, j19)
        write_atomic_json(output / "preflight.json", _preflight_payload(contract, identities))
    elif args.stage == "compare":
        if args.run is None:
            parser.error("--run is required for compare stage")
        identities = _verify_preflight(contract, contract_path, j19)
        run_path = args.run if args.run.is_absolute() else ROOT / args.run
        run = json.loads(run_path.read_text(encoding="utf-8"))
        write_atomic_json(output / "comparison.json", _comparison_payload(contract, identities, j19, run))
    else:
        _write_manifest(output, contract)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
