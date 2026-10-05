"""Reproducibly characterize the bounded dense QEP backend for WP05."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
from typing import Any

import numpy as np
import psutil
import scipy
from threadpoolctl import threadpool_info, threadpool_limits


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_11" / "wp05_gyroscopic_contract.json"
def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fixture(size: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build deterministic dense SPD M/K and skew G with distinct frequencies."""

    mass = np.diag(1.0 + 0.001 * np.arange(size, dtype=float))
    frequency_sq = 20.0 + 0.25 * np.arange(size, dtype=float)
    stiffness = np.diag(mass.diagonal() * frequency_sq)
    gyro = np.zeros((size, size), dtype=float)
    index = np.arange(size - 1)
    coupling = 0.05 * (1.0 + (index % 7) / 7.0)
    gyro[index, index + 1] = coupling
    gyro[index + 1, index] = -coupling
    return mass, stiffness, gyro


def _worker(size: int, seed: int) -> int:
    del seed  # The fixture is formula-based; the fixed seed remains recorded for schema stability.
    sys.path.insert(0, str(ROOT / "src"))
    import psutil as worker_psutil

    from solveur.core.analyses.qep import QuadraticEigenSolver

    mass, stiffness, gyro = _fixture(size)
    baseline_rss = worker_psutil.Process().memory_info().rss
    started = time.perf_counter()
    try:
        with threadpool_limits(limits=1):
            result = QuadraticEigenSolver().solve(
                mass,
                stiffness,
                gyro,
                25.0,
                length_reference=1.0,
                dof_names=tuple("RY" for _ in range(size)),
            )
    except Exception as exc:  # Evidence records preserve real failure classification.
        payload = {
            "status": "FAIL",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "baseline_rss_bytes": int(baseline_rss),
            "wall_seconds": time.perf_counter() - started,
        }
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        return 2
    payload = {
        "status": "PASS",
        "physical_dofs": size,
        "linearized_dimension": int(2 * size),
        "baseline_rss_bytes": int(baseline_rss),
        "wall_seconds": time.perf_counter() - started,
        "maximum_qep_residual": float(np.max(result.residuals)),
        "maximum_mass_normalization_error": float(result.diagnostics["maximum_mass_normalization_error"]),
        "maximum_eigenvalue_condition": float(result.diagnostics["maximum_generalized_eigenvalue_condition"]),
        "conjugate_spectrum_mismatch": float(result.diagnostics["normalized_conjugate_spectrum_mismatch"]),
        "threadpools": threadpool_info(),
    }
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


def _identity_for_size(source_sha: str, size: int, seed: int, contract: dict[str, Any]) -> Any:
    sys.path.insert(0, str(ROOT / "src"))
    from solveur.verification.v2.execution_identity import ExecutionIdentity, InputFileIdentity

    fixture_spec = {
        "kind": "formula-generated-spd-skew-dense-qep-v1",
        "physical_dofs": size,
        "mass_diagonal": "1 + 0.001*i",
        "frequency_squared_diagonal": "20 + 0.25*i",
        "gyro_upper_neighbour": "0.05*(1 + (i mod 7)/7)",
        "gyro_lower_neighbour": "negative transpose",
        "seed_recorded_no_random_draws": seed,
        "signed_speed_rad_s": 25.0,
    }
    fixture_bytes = json.dumps(fixture_spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    inputs = (
        InputFileIdentity.from_bytes(
            logical_role="generated_matrix_fixture_spec",
            logical_id=f"wp05/dense-qep/physical-dof-{size}/fixture-v1.json",
            content=fixture_bytes,
            provenance="GENERATED",
            availability_status="AVAILABLE_AND_REPRODUCIBLE",
            public_identifier=f"wp05/dense-qep/physical-dof-{size}/fixture-v1.json",
        ),
        InputFileIdentity.from_bytes(
            logical_role="solver_source",
            logical_id="src/solveur/core/analyses/qep.py",
            content=(ROOT / "src" / "solveur" / "core" / "analyses" / "qep.py").read_bytes(),
            provenance="REPOSITORY",
            availability_status="AVAILABLE_AND_REPRODUCIBLE",
            public_identifier="src/solveur/core/analyses/qep.py",
        ),
        InputFileIdentity.from_bytes(
            logical_role="characterization_runner",
            logical_id="scripts/characterize_rotating_qep_dense.py",
            content=Path(__file__).read_bytes(),
            provenance="REPOSITORY",
            availability_status="AVAILABLE_AND_REPRODUCIBLE",
            public_identifier="scripts/characterize_rotating_qep_dense.py",
        ),
    )
    contract_file = InputFileIdentity.from_bytes(
        logical_role="frozen_wp05_contract",
        logical_id="qualification/0_2_11/wp05_gyroscopic_contract.json",
        content=CONTRACT_PATH.read_bytes(),
        provenance="REPOSITORY",
        availability_status="AVAILABLE_AND_REPRODUCIBLE",
        public_identifier="qualification/0_2_11/wp05_gyroscopic_contract.json",
    )
    return ExecutionIdentity(
        source_sha=source_sha,
        case_contract_version="0.2.11-wp05-dense-qep-v1",
        units_resolved=True,
        case_definition={"case_id": f"WP05-DENSE-{size}", "schema_version": 2, "fixture": fixture_spec},
        model_input={"kind": "synthetic_matrix_pencil", "physical_dofs": size},
        input_files=inputs,
        mesh={"kind": "not_applicable_synthetic_matrix", "physical_dofs": size},
        material_data={},
        boundary_conditions={},
        loads={},
        solver_configuration={"backend": "scipy.linalg.eig(A,B)", "driver": "dense_qep", "blas_threads": 1},
        resolved_overrides={},
        reference_identity={
            "id": "QF0211-WP05-DENSE-SOLVER-INVARIANT-v1",
            "role": "numerical gates only; not an external physical oracle",
        },
        reference_files=(contract_file,),
        tolerance_policy=dict(contract["frozen_tolerances"]),
        metric_definitions={
            "wall_seconds": "elapsed wall time for one complete QuadraticEigenSolver.solve call",
            "peak_rss_bytes": "Windows peak_wset high-water mark when available; otherwise maximum 10 ms sampled RSS",
            "qep_residual": "contract-defined original-polynomial relative residual",
        },
        software_versions={
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        numerical_environment={
            "os": platform.system(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count() or 1,
            "dtype": "float64",
            "blas_threads": 1,
        },
        rotation_configuration={"synthetic_qep_speed_rad_s": 25.0, "physical_rotor_claim": False},
    )


def _run_one(size: int, repetition: int, seed: int, timeout_seconds: int) -> dict[str, Any]:
    env = os.environ.copy()
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
        env[name] = "1"
    command = [sys.executable, str(Path(__file__).resolve()), "--worker-size", str(size), "--seed", str(seed)]
    process = subprocess.Popen(command, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    child = psutil.Process(process.pid)
    peak_rss = 0
    started = time.monotonic()
    while process.poll() is None:
        try:
            memory = child.memory_info()
            peak_rss = max(peak_rss, int(getattr(memory, "peak_wset", memory.rss)))
        except psutil.Error:
            pass
        if time.monotonic() - started > timeout_seconds:
            process.kill()
            stdout, stderr = process.communicate()
            return {
                "repetition": repetition,
                "status": "TIMEOUT",
                "peak_rss_bytes": peak_rss,
                "stdout": stdout,
                "stderr": stderr[-4000:],
            }
        time.sleep(0.01)
    stdout, stderr = process.communicate()
    try:
        worker_result = json.loads(stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {
            "repetition": repetition,
            "status": "WORKER_PROTOCOL_FAILURE",
            "peak_rss_bytes": peak_rss,
            "stdout": stdout[-4000:],
            "stderr": stderr[-4000:],
            "return_code": process.returncode,
        }
    return {
        "repetition": repetition,
        **worker_result,
        "peak_rss_bytes": peak_rss,
        "stderr": stderr[-4000:] if stderr else "",
        "return_code": process.returncode,
    }


def _run_suite(source_sha: str, output: Path, timeout_seconds: int) -> None:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != source_sha or status:
        raise ValueError(f"Dense evidence requires clean HEAD={source_sha}; found HEAD={head}, dirty={bool(status)}.")
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    policy = contract["dense_characterization"]
    resource_policy = policy["resource_estimation"]
    target_sizes = tuple(int(value) for value in policy["target_physical_dof_sizes"])
    repetitions = int(policy["repetitions_per_completed_size"])
    safety_factor = float(resource_policy["safety_factor"])
    stop_memory_fraction = float(resource_policy["maximum_projected_fraction_of_available_memory"])
    bound_reduction_fraction = float(resource_policy["reduce_supported_bound_if_peak_fraction_exceeds"])
    if len(target_sizes) < int(policy["minimum_completed_sizes"]) or repetitions < 1:
        raise ValueError("Frozen dense-characterization targets/repetitions do not satisfy the contract minimum.")
    available_bytes = int(psutil.virtual_memory().available)
    total_bytes = int(psutil.virtual_memory().total)
    executions: list[dict[str, Any]] = []
    completed_peaks: list[tuple[int, int]] = []
    skipped_sizes: list[dict[str, Any]] = []
    stop_reason = "all_contract_targets_completed"

    for size_index, size in enumerate(target_sizes):
        if size_index and executions:
            previous_size, previous_peak = completed_peaks[-1]
            previous_linearized = 2 * previous_size
            target_linearized = 2 * size
            previous_baseline = max(
                int(run.get("baseline_rss_bytes", 0)) for run in executions[-1]["repetitions"]
            )
            measured_increment = max(
                (
                    int(run.get("peak_rss_bytes", 0)) - int(run.get("baseline_rss_bytes", 0))
                    for run in executions[-1]["repetitions"]
                ),
                default=max(0, previous_peak - previous_baseline),
            )
            projected_peak = previous_baseline + int(
                safety_factor
                * measured_increment
                * (target_linearized / previous_linearized) ** 2
            )
            if projected_peak > stop_memory_fraction * int(psutil.virtual_memory().available):
                skipped_sizes.append(
                    {
                        "physical_dofs": size,
                        "status": "SKIPPED_RESOURCE_LIMIT",
                        "projected_peak_rss_bytes": projected_peak,
                        "available_memory_before_projection_bytes": int(psutil.virtual_memory().available),
                    }
                )
                stop_reason = "next_target_projected_over_70_percent_available_memory"
                break
            if executions[-1]["result_status"] != "PASS":
                skipped_sizes.append({"physical_dofs": size, "status": "SKIPPED_PREVIOUS_SIZE_FAILED"})
                stop_reason = "preceding_size_failed"
                break

        seed = 20261105 + size
        identity = _identity_for_size(source_sha, size, seed, contract)
        runs = [_run_one(size, repetition, seed, timeout_seconds) for repetition in range(1, repetitions + 1)]
        successful = [run for run in runs if run.get("status") == "PASS" and run.get("return_code") == 0]
        status = "PASS" if len(successful) == repetitions else "FAIL"
        peaks = [int(run.get("peak_rss_bytes", 0)) for run in successful]
        times = [float(run["wall_seconds"]) for run in successful]
        record = {
            "record_schema": "qf.wp05.dense-characterization.v1",
            "schema_version": 2,
            "work_package": "WP05",
            "case_id": f"WP05-DENSE-{size}",
            "source_sha": source_sha,
            "execution_key": identity.execution_key(),
            "execution_identity": identity.to_dict(),
            "evidence_availability": "AVAILABLE_AND_REPRODUCIBLE",
            "result_status": status,
            "maturity": "EXPERIMENTAL",
            "maturity_promotion": "NONE",
            "physical_dofs": size,
            "linearized_dimension": 2 * size,
            "seed": seed,
            "repetitions_required": repetitions,
            "repetitions": runs,
            "rss_measurement": {
                "method": "Windows peak_wset high-water mark when available; otherwise maximum sampled RSS",
                "sample_interval_ms": 10,
            },
            "summary": {
                "wall_seconds_median": statistics.median(times) if times else None,
                "wall_seconds_min": min(times) if times else None,
                "wall_seconds_max": max(times) if times else None,
                "wall_seconds_population_stdev": statistics.pstdev(times) if len(times) > 1 else 0.0,
                "peak_rss_bytes_max": max(peaks) if peaks else None,
                "maximum_qep_residual": max(
                    (float(run["maximum_qep_residual"]) for run in successful), default=None
                ),
                "available_memory_at_start_bytes": available_bytes,
                "total_physical_memory_bytes": total_bytes,
                "blas_lapack": successful[0]["threadpools"] if successful else None,
            },
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        record["record_sha256"] = _digest(
            json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        )
        executions.append(record)
        if peaks:
            completed_peaks.append((size, max(peaks)))
        if status != "PASS":
            skipped_sizes.extend(
                {"physical_dofs": later, "status": "SKIPPED_PREVIOUS_SIZE_FAILED"}
                for later in target_sizes[size_index + 1 :]
            )
            stop_reason = "preceding_size_failed"
            break

    successful_records = [record for record in executions if record["result_status"] == "PASS"]
    if len(successful_records) < 3:
        bound: int | None = None
        bound_reason = "fewer_than_three_target_sizes_completed"
    else:
        bound_index = len(successful_records) - 1
        latest = successful_records[-1]
        max_peak = latest["summary"]["peak_rss_bytes_max"]
        if max_peak is not None and max_peak > bound_reduction_fraction * available_bytes:
            bound_index = max(0, bound_index - 1)
            bound_reason = "largest_successful_size_exceeded_50_percent_available_memory; reduced_one_target_tier"
        else:
            bound_reason = "largest_successful_target_size; no extrapolation"
        bound = successful_records[bound_index]["physical_dofs"]

    result = {
        "record_schema": "qf.wp05.dense-characterization-suite.v1",
        "schema_version": 2,
        "work_package": "WP05",
        "source_sha": source_sha,
        "contract_path": "qualification/0_2_11/wp05_gyroscopic_contract.json",
        "contract_sha256": _digest(CONTRACT_PATH.read_bytes()),
        "target_physical_dof_sizes": list(target_sizes),
        "repetitions_per_size": repetitions,
        "resource_policy": {
            "safety_factor": safety_factor,
            "projected_rss_threshold_fraction": stop_memory_fraction,
            "supported_bound_reduction_threshold_fraction": bound_reduction_fraction,
            "fallback_rss_sample_interval_ms": 10,
        },
        "executions": executions,
        "skipped_sizes": skipped_sizes,
        "stop_reason": stop_reason,
        "supported_physical_dof_bound": bound,
        "supported_bound_reason": bound_reason,
        "overall_status": "PASS" if len(successful_records) >= 3 else "FAIL",
        "maturity_promotion": "NONE",
    }
    result["suite_sha256"] = _digest(
        json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("overall_status", "supported_physical_dof_bound", "stop_reason", "suite_sha256")}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--worker-size", type=int)
    parser.add_argument("--seed", type=int, default=20261105)
    args = parser.parse_args()
    if args.worker_size is not None:
        return _worker(args.worker_size, args.seed)
    if not args.source_sha or args.output is None:
        parser.error("--source-sha and --output are required outside worker mode")
    if len(args.source_sha) != 40 or any(character not in "0123456789abcdef" for character in args.source_sha):
        parser.error("--source-sha must be a lowercase full Git SHA")
    _run_suite(args.source_sha, args.output, args.timeout_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
