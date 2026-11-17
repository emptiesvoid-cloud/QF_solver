"""One-shot child process for checking a pinned archived represented system."""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix

from research.j17.exact_residual import ExactResidualResult, evaluate_exact_residual
from research.j19.checkpoint import write_atomic_json


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fraction(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _result_payload(
    result: ExactResidualResult,
    *,
    case_id: str,
    input_sha256: str,
    elapsed_seconds: float,
) -> dict[str, Any]:
    return {
        "schema": "qfsolver-j21-exact-worker-result-v1",
        "case_id": case_id,
        "input_sha256": input_sha256,
        "record_state": "COMPLETE",
        "exact_status": result.status,
        "reason": result.reason,
        "dimension": result.dimension,
        "stored_entries": result.stored_entries,
        "nonzero_entries": result.nonzero_entries,
        "residual_squared": _fraction(result.residual_squared),
        "reference_squared": _fraction(result.reference_squared),
        "relative_residual_squared": _fraction(result.relative_residual_squared),
        "threshold_binary64": _fraction(result.threshold_binary64),
        "residual_l2_display": result.residual_l2_display,
        "relative_residual_display": result.relative_residual_display,
        "elapsed_seconds": elapsed_seconds,
    }


def evaluate_archive(
    input_path: Path,
    *,
    expected_sha256: str,
    case_id: str,
    tolerance: float,
    max_dimension: int,
    max_nonzero_entries: int,
    max_fraction_bits: int,
    max_elapsed_seconds: float,
) -> dict[str, Any]:
    """Evaluate the unscaled J17/J19 archive solution without resolving it."""
    input_path = Path(input_path)
    actual_sha256 = _sha256(input_path)
    if actual_sha256 != expected_sha256:
        raise ValueError("input SHA-256 mismatch")
    started = time.perf_counter()
    with np.load(input_path, allow_pickle=False) as archive:
        matrix_storage = (
            str(archive["matrix_storage"].item())
            if "matrix_storage" in archive.files
            else "dense"
        )
        shared = {"rhs_real", "rhs_imag", "x_unscaled_real", "x_unscaled_imag"}
        if matrix_storage == "dense":
            matrix_fields = {"impedance_real", "impedance_imag"}
        elif matrix_storage == "csr":
            matrix_fields = {
                "csr_data_real",
                "csr_data_imag",
                "csr_indices",
                "csr_indptr",
                "matrix_shape",
            }
        else:
            raise ValueError("unsupported matrix storage format")
        required = shared | matrix_fields
        missing = sorted(required.difference(archive.files))
        if missing:
            raise ValueError("input archive is missing required arrays")
        rhs_real = np.asarray(archive["rhs_real"])
        rhs_imag = np.asarray(archive["rhs_imag"])
        solution_real = np.asarray(archive["x_unscaled_real"])
        solution_imag = np.asarray(archive["x_unscaled_imag"])
        if matrix_storage == "dense":
            real = np.asarray(archive["impedance_real"])
            imag = np.asarray(archive["impedance_imag"])
        else:
            csr_data_real = np.asarray(archive["csr_data_real"])
            csr_data_imag = np.asarray(archive["csr_data_imag"])
            csr_indices = np.asarray(archive["csr_indices"])
            csr_indptr = np.asarray(archive["csr_indptr"])
            matrix_shape = np.asarray(archive["matrix_shape"])

    if rhs_real.shape != rhs_imag.shape or solution_real.shape != solution_imag.shape:
        raise ValueError("real and imaginary vector arrays must have matching shapes")
    if matrix_storage == "dense":
        if real.shape != imag.shape or real.ndim != 2 or real.shape[0] != real.shape[1]:
            raise ValueError("matrix real and imaginary arrays must have matching square shapes")
        matrix = csr_matrix(real + 1j * imag)
    else:
        if csr_data_real.shape != csr_data_imag.shape:
            raise ValueError("CSR real and imaginary data arrays must have matching shapes")
        if matrix_shape.shape != (2,) or matrix_shape.dtype.kind not in "iu":
            raise ValueError("CSR matrix_shape must contain two integers")
        matrix = csr_matrix(
            (
                csr_data_real + 1j * csr_data_imag,
                csr_indices,
                csr_indptr,
            ),
            shape=(int(matrix_shape[0]), int(matrix_shape[1])),
        )
    rhs = rhs_real + 1j * rhs_imag
    solution = solution_real + 1j * solution_imag
    result = evaluate_exact_residual(
        matrix,
        rhs,
        solution,
        tolerance=tolerance,
        max_dimension=max_dimension,
        max_nonzero_entries=max_nonzero_entries,
        max_fraction_bits=max_fraction_bits,
        max_elapsed_seconds=max_elapsed_seconds,
    )
    return _result_payload(
        result,
        case_id=case_id,
        input_sha256=actual_sha256,
        elapsed_seconds=time.perf_counter() - started,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--tolerance", required=True, type=float)
    parser.add_argument("--max-dimension", required=True, type=int)
    parser.add_argument("--max-nonzero-entries", required=True, type=int)
    parser.add_argument("--max-fraction-bits", required=True, type=int)
    parser.add_argument("--max-elapsed-seconds", required=True, type=float)
    args = parser.parse_args(argv)
    try:
        payload = evaluate_archive(
            args.input,
            expected_sha256=args.expected_sha256,
            case_id=args.case_id,
            tolerance=args.tolerance,
            max_dimension=args.max_dimension,
            max_nonzero_entries=args.max_nonzero_entries,
            max_fraction_bits=args.max_fraction_bits,
            max_elapsed_seconds=args.max_elapsed_seconds,
        )
    except Exception as exc:
        payload = {
            "schema": "qfsolver-j21-exact-worker-result-v1",
            "case_id": args.case_id,
            "input_sha256": args.expected_sha256,
            "record_state": "INCONCLUSIVE",
            "exact_status": "INCONCLUSIVE",
            "reason": "worker exception: " + type(exc).__name__,
        }
        write_atomic_json(args.result, payload)
        return 2
    write_atomic_json(args.result, payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
