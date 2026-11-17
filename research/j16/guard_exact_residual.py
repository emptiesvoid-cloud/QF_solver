"""High-precision residual evaluation for archived J16 harmonic systems.

This script post-processes the exact binary64 matrix, right-hand side, and
solution vectors archived by the J16 guard-resolution experiment. It does not
assemble a model or call a solver.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import mpmath as mp
import numpy as np
import psutil


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = PROJECT_ROOT / "research/j16/contracts/guard_exact_residual_002.json"
INPUT_ROOT = PROJECT_ROOT / "research/j16/results/diagnostic-2026-11-17/guard_resolution_001"
OUTPUT_ROOT = PROJECT_ROOT / "research/j16/results/diagnostic-2026-11-17/guard_exact_residual_002"
VARIANTS = {
    "spsolve_unscaled": "unscaled",
    "spsolve_row_column_equilibrated": "scaled",
    "splu_two_refinements": "refined",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _exact_mpf(value: float | np.floating[Any]) -> mp.mpf:
    numerator, denominator = float(value).as_integer_ratio()
    return mp.mpf(numerator) / denominator


def _exact_complex(real: float | np.floating[Any], imag: float | np.floating[Any]) -> mp.mpc:
    return mp.mpc(_exact_mpf(real), _exact_mpf(imag))


def high_precision_residual_metrics(
    matrix_real: np.ndarray,
    matrix_imag: np.ndarray,
    rhs_real: np.ndarray,
    rhs_imag: np.ndarray,
    solution_real: np.ndarray,
    solution_imag: np.ndarray,
    *,
    decimal_digits: int,
) -> dict[str, mp.mpf]:
    """Evaluate residual norms from exact binary64 inputs at ``decimal_digits``.

    The returned values concern the represented matrix problem only. They do
    not bound model or assembly error and do not change a QF route status.
    """
    real = np.asarray(matrix_real, dtype=np.float64)
    imag = np.asarray(matrix_imag, dtype=np.float64)
    b_real = np.asarray(rhs_real, dtype=np.float64)
    b_imag = np.asarray(rhs_imag, dtype=np.float64)
    x_real = np.asarray(solution_real, dtype=np.float64)
    x_imag = np.asarray(solution_imag, dtype=np.float64)
    if real.ndim != 2 or real.shape[0] != real.shape[1] or imag.shape != real.shape:
        raise ValueError("matrix real/imaginary arrays must be square and have matching shapes")
    size = real.shape[0]
    if any(values.shape != (size,) for values in (b_real, b_imag, x_real, x_imag)):
        raise ValueError("right-hand side and solution arrays must match the matrix dimension")
    if not all(np.all(np.isfinite(values)) for values in (real, imag, b_real, b_imag, x_real, x_imag)):
        raise ValueError("matrix, right-hand side, and solution must contain only finite values")

    with mp.workdps(decimal_digits):
        x = [_exact_complex(x_real[j], x_imag[j]) for j in range(size)]
        b = [_exact_complex(b_real[i], b_imag[i]) for i in range(size)]
        ax: list[mp.mpc] = []
        matrix_inf_norm = mp.mpf("0")
        for i in range(size):
            entries = [
                _exact_complex(real[i, j], imag[i, j])
                for j in range(size)
                if real[i, j] != 0.0 or imag[i, j] != 0.0
            ]
            columns = [
                j for j in range(size) if real[i, j] != 0.0 or imag[i, j] != 0.0
            ]
            ax.append(mp.fsum(coefficient * x[j] for coefficient, j in zip(entries, columns, strict=True)))
            matrix_inf_norm = max(matrix_inf_norm, mp.fsum(abs(value) for value in entries))

        residual = [ax[i] - b[i] for i in range(size)]
        residual_l2 = mp.sqrt(mp.fsum(abs(value) ** 2 for value in residual))
        rhs_l2 = mp.sqrt(mp.fsum(abs(value) ** 2 for value in b))
        ax_l2 = mp.sqrt(mp.fsum(abs(value) ** 2 for value in ax))
        rhs_inf = max((abs(value) for value in b), default=mp.mpf("0"))
        solution_inf = max((abs(value) for value in x), default=mp.mpf("0"))
        residual_inf = max((abs(value) for value in residual), default=mp.mpf("0"))
        denominator = max(rhs_l2, ax_l2)
        backward_denominator = matrix_inf_norm * solution_inf + rhs_inf
        return {
            "residual_l2": +residual_l2,
            "relative_residual_l2": +(residual_l2 / denominator if denominator else mp.mpf("0")),
            "backward_error_eta_inf": +(
                residual_inf / backward_denominator if backward_denominator else mp.mpf("0")
            ),
            "matrix_inf_norm": +matrix_inf_norm,
            "rhs_l2": +rhs_l2,
            "ax_l2": +ax_l2,
        }


def _load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "J16-GUARD-EXACT-RESIDUAL-002":
        raise ValueError("unexpected high-precision residual contract")
    if contract.get("state") != "FROZEN_BEFORE_EXECUTION":
        raise ValueError("high-precision residual contract is not frozen")
    for rel, expected in contract["source_sha256"].items():
        actual = _sha256(PROJECT_ROOT / rel)
        if actual != expected:
            raise ValueError(f"source SHA mismatch for {rel}: {actual} != {expected}")
    return contract


def _verify_archived_inputs(contract: dict[str, Any]) -> list[dict[str, Any]]:
    manifest_path = INPUT_ROOT / "artifact_manifest.json"
    manifest_sha = _sha256(manifest_path)
    if manifest_sha != contract["inputs"]["artifact_manifest_sha256"]:
        raise ValueError(f"guard-resolution manifest SHA mismatch: {manifest_sha}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verified = []
    for item in manifest["artifacts"]:
        path = INPUT_ROOT / item["path"]
        actual = _sha256(path)
        if actual != item["sha256_raw"] or path.stat().st_size != item["bytes"]:
            raise ValueError(f"archived input integrity mismatch: {item['path']}")
        verified.append({"path": item["path"], "sha256": actual, "bytes": path.stat().st_size})
    summary = json.loads((INPUT_ROOT / "guard_resolution_summary.json").read_text(encoding="utf-8"))
    if summary.get("contract_id") != "J16-NAFEMS13H-GUARD-SCALE-REFINEMENT-001":
        raise ValueError("unexpected archived guard-resolution source contract")
    return verified


def _mp_text(value: mp.mpf, digits: int = 60) -> str:
    return mp.nstr(value, n=digits, strip_zeros=False)


def run_postprocess() -> dict[str, Any]:
    started = time.perf_counter()
    process = psutil.Process()
    peak_rss = [process.memory_info().rss]
    stop_monitor = threading.Event()

    def sample_rss() -> None:
        while not stop_monitor.wait(0.1):
            try:
                peak_rss[0] = max(peak_rss[0], process.memory_info().rss)
            except psutil.Error:
                return

    monitor = threading.Thread(target=sample_rss, name="j16-rss-monitor", daemon=True)
    monitor.start()
    contract = _load_contract()
    verified_inputs = _verify_archived_inputs(contract)
    source_summary = json.loads((INPUT_ROOT / "guard_resolution_summary.json").read_text(encoding="utf-8"))
    records = []
    for item in source_summary["frequencies"]:
        npz_path = INPUT_ROOT / item["matrix_archive"]
        with np.load(npz_path, allow_pickle=False) as archive:
            matrix_real = archive["impedance_real"]
            matrix_imag = archive["impedance_imag"]
            rhs_real = archive["rhs_real"]
            rhs_imag = archive["rhs_imag"]
            per_variant = []
            for variant, suffix in VARIANTS.items():
                metrics_by_precision = {}
                for digits in contract["method"]["decimal_precisions"]:
                    metrics_by_precision[digits] = high_precision_residual_metrics(
                        matrix_real,
                        matrix_imag,
                        rhs_real,
                        rhs_imag,
                        archive[f"x_{suffix}_real"],
                        archive[f"x_{suffix}_imag"],
                        decimal_digits=digits,
                    )
                low = metrics_by_precision[contract["method"]["decimal_precisions"][0]]
                high = metrics_by_precision[contract["method"]["decimal_precisions"][1]]
                with mp.workdps(contract["method"]["decimal_precisions"][1]):
                    stability = abs(low["relative_residual_l2"] - high["relative_residual_l2"]) / max(
                        abs(high["relative_residual_l2"]), mp.mpf("1e-100")
                    )
                guard = item["variants"][variant]["guard_recheck"]
                per_variant.append(
                    {
                        "variant": variant,
                        "guard_recheck_outcome": guard["outcome"],
                        "guard_upper_bound": guard["diagnostics"]["relative_residual_upper_bound"],
                        "high_precision_relative_residual_l2": _mp_text(high["relative_residual_l2"]),
                        "high_precision_backward_error_eta_inf": _mp_text(high["backward_error_eta_inf"]),
                        "high_precision_residual_l2": _mp_text(high["residual_l2"]),
                        "precision_stability_relative_difference": _mp_text(stability),
                        "precision_stability_pass": stability <= mp.mpf(contract["method"]["maximum_precision_stability_relative_difference"]),
                        "solution_difference_inf_vs_unscaled": item["variants"][variant]["relative_solution_difference_inf_vs_unscaled"],
                    }
                )
            records.append(
                {
                    "frequency_hz": item["frequency_hz"],
                    "condition_number_2": item["condition_number_2"],
                    "historical_qf_status": item["historical_qf_status"],
                    "historical_guard_upper_bound": item["historical_guard_upper_bound"],
                    "variants": per_variant,
                    "input_matrix_archive": item["matrix_archive"],
                }
            )

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    source_identity = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    result = {
        "schema": "qfsolver-j16-high-precision-residual-postprocess-v1",
        "classification": "ARCHIVED_MATRIX_POSTPROCESSING_NO_SOLVE_OR_FEM_ASSEMBLY",
        "contract_id": contract["contract_id"],
        "contract_sha256": _sha256(CONTRACT_PATH),
        "source_git_commit": source_identity,
        "source_file_sha256": contract["source_sha256"],
        "source_guard_experiment_contract_id": source_summary["contract_id"],
        "source_guard_experiment_contract_sha256": source_summary["contract_sha256"],
        "input_artifact_manifest_sha256": contract["inputs"]["artifact_manifest_sha256"],
        "verified_archived_input_count": len(verified_inputs),
        "verified_archived_input_bytes": sum(item["bytes"] for item in verified_inputs),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "mpmath": mp.__version__,
        },
        "resources_observed": {},
        "method": contract["method"],
        "records": records,
        "interpretation_limit": contract["method"]["interpretation_limit"],
        "status_policy": "All original and prior diagnostic guard rejections remain unchanged; this post-processing is not a QF route acceptance.",
    }
    output_path = OUTPUT_ROOT / "guard_exact_residual_summary.json"
    temporary_path = output_path.with_suffix(".json.tmp")
    temporary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary_path.replace(output_path)
    stop_monitor.set()
    monitor.join(timeout=2.0)
    result["resources_observed"] = {
        "elapsed_seconds": time.perf_counter() - started,
        "peak_rss_bytes_sampled": peak_rss[0],
        "sampling_interval_seconds": 0.1,
        "rss_limit_semantics": "sampled soft monitor; not an OS memory quota",
    }
    temporary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary_path.replace(output_path)
    return result


if __name__ == "__main__":
    payload = run_postprocess()
    print(json.dumps({
        "contract_id": payload["contract_id"],
        "frequencies": len(payload["records"]),
        "verified_archived_inputs": payload["verified_archived_input_count"],
        "output": "research/j16/results/diagnostic-2026-11-17/guard_exact_residual_002/guard_exact_residual_summary.json",
    }, indent=2))
