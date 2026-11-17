from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import splu, spsolve

from research.j15.harmonic_resonance import (
    _build_reduced_system,
    _center_node,
    _system_at_frequency,
)
from solveur.core.errors import NumericalConvergenceError
from solveur.core.solvers.linear import LinearSystemSolver
from solveur.verification.external_correlation import load_abaqus_nafems_13h_reference


FREQUENCIES_HZ = (2.30, 2.375818178440047, 2.417, 2.418, 2.45)
GUARD_LIMIT = 1.0e-7
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = PROJECT_ROOT / "research/j16/contracts/nafems_13h_guard_resolution_001.json"
DEFAULT_INPUT_ROOT = PROJECT_ROOT / "research/j15/results/diagnostic-2026-11-17/nafems_13h_resonance/raw/frequency_checkpoints"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "research/j16/results/diagnostic-2026-11-17/guard_resolution_001"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_identity() -> dict[str, str]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, check=True, text=True
    ).stdout.strip()
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=PROJECT_ROOT, capture_output=True, check=True, text=True
    ).stdout.strip()
    return {"commit": commit, "branch": branch}


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    temporary = path.with_name(f".{path.stem}.tmp.npz")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _verify_archived_inputs(checkpoint_root: Path) -> tuple[str, int, str]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "J16-NAFEMS13H-GUARD-SCALE-REFINEMENT-001" or contract.get("state") != "FROZEN_BEFORE_EXECUTION":
        raise ValueError("the J16 guard-resolution contract is missing or not frozen")
    for relative_path, expected_sha256 in contract.get("source_sha256", {}).items():
        source_path = (PROJECT_ROOT / relative_path).resolve(strict=True)
        if not source_path.is_relative_to(PROJECT_ROOT.resolve()) or _sha256(source_path) != expected_sha256:
            raise ValueError(f"a source file differs from the frozen contract: {relative_path}")
    manifest_path = checkpoint_root.parents[1] / "postprocess_001" / "input_artifact_manifest.json"
    expected_manifest_sha = contract["inputs"]["j15_input_manifest_sha256"]
    if _sha256(manifest_path) != expected_manifest_sha:
        raise ValueError("the J15 input artifact manifest does not match the frozen J16 contract")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_run = manifest.get("source_run", {})
    if (
        source_run.get("commit") != contract["inputs"]["j15_source_commit"]
        or source_run.get("runner_state") != "PYTEST_FAILED"
        or source_run.get("attempt_id") != "J15-NAFEMS13H-RES-001"
        or source_run.get("contract_id") != "J15-MITC4-NAFEMS13H-RESONANCE-001"
        or manifest.get("frequency_artifact_count") != 304
    ):
        raise ValueError("the archived source run identity or historical status changed")
    entries = {entry["path"]: entry for entry in manifest.get("frequency_artifacts", [])}
    required_names = []
    for frequency in FREQUENCIES_HZ:
        key = f"frequency_{frequency:.9f}".replace(".", "p")
        required_names.extend((f"{key}.json", f"{key}.npz"))
    for name in required_names:
        entry = entries.get(name)
        path = checkpoint_root / name
        if entry is None or not path.is_file():
            raise ValueError(f"archived J15 input is missing from the manifest or disk: {name}")
        if path.stat().st_size != entry["bytes"] or _sha256(path) != entry["sha256_raw"]:
            raise ValueError(f"archived J15 input failed its frozen SHA-256 check: {name}")
    return expected_manifest_sha, len(required_names), _sha256(CONTRACT_PATH)


def _eta_inf(matrix: csr_matrix, rhs: np.ndarray, solution: np.ndarray) -> float:
    residual = matrix @ solution - rhs
    denominator = (
        float(np.max(np.asarray(np.abs(matrix).sum(axis=1)).ravel(), initial=0.0))
        * float(np.max(np.abs(solution), initial=0.0))
        + float(np.max(np.abs(rhs), initial=0.0))
    )
    return float(np.max(np.abs(residual), initial=0.0) / denominator) if denominator > 0.0 else math.inf


def _guard_check(matrix: csr_matrix, rhs: np.ndarray, solution: np.ndarray) -> dict[str, Any]:
    try:
        residual, relative = LinearSystemSolver._validated_residual_metrics(
            matrix,
            rhs,
            solution,
            "direct_frequency",
            {"residual_failure_tolerance": GUARD_LIMIT},
        )
        return {
            "outcome": "WITHIN_GUARD",
            "residual_norm": residual,
            "relative_residual": relative,
            "limit": GUARD_LIMIT,
        }
    except NumericalConvergenceError as exc:
        return {
            "outcome": "GUARD_REJECTED",
            "message": str(exc),
            "diagnostics": getattr(exc, "diagnostics", {}),
        }


def run_guard_resolution_experiment(
    output_dir: str | Path = DEFAULT_OUTPUT_ROOT,
    checkpoint_dir: str | Path = DEFAULT_INPUT_ROOT,
) -> dict[str, Any]:
    """Compare direct, diagonally scaled, and refined solves on the archived QF 8x8 model."""
    output = Path(output_dir)
    checkpoint_root = Path(checkpoint_dir)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite guard diagnostic output: {output}")
    input_manifest_sha256, verified_input_count, contract_sha256 = _verify_archived_inputs(checkpoint_root)
    output.mkdir(parents=True, exist_ok=False)
    reference = load_abaqus_nafems_13h_reference()
    (
        model,
        dofs,
        reducer,
        stiffness,
        mass,
        damping,
        loads_reduced,
        loads_full,
        _alpha,
        beta,
    ) = _build_reduced_system(reference, FREQUENCIES_HZ[0])
    center_index = dofs.index(_center_node(model.nodes), "UZ")
    results: list[dict[str, Any]] = []

    for index, frequency in enumerate(FREQUENCIES_HZ):
        impedance_dense, rhs = _system_at_frequency(stiffness, mass, damping, loads_reduced, frequency)
        impedance = csr_matrix(impedance_dense)
        x_direct = np.asarray(spsolve(impedance, rhs), dtype=complex)

        row_norm = np.asarray(np.abs(impedance).sum(axis=1)).ravel()
        row_scale = 1.0 / np.maximum(row_norm, np.finfo(float).tiny)
        row_scaled = diags(row_scale) @ impedance
        column_norm = np.asarray(np.abs(row_scaled).sum(axis=0)).ravel()
        column_scale = 1.0 / np.maximum(column_norm, np.finfo(float).tiny)
        equilibrated = (row_scaled @ diags(column_scale)).tocsr()
        y_scaled = np.asarray(spsolve(equilibrated, row_scale * rhs), dtype=complex)
        x_scaled = column_scale * y_scaled

        factorization = splu(impedance.tocsc())
        x_refined = x_direct.copy()
        refinement_records: list[dict[str, float]] = []
        for iteration in range(1, 3):
            correction_rhs = rhs - impedance @ x_refined
            correction = factorization.solve(correction_rhs)
            x_refined = x_refined + correction
            refinement_records.append(
                {
                    "iteration": iteration,
                    "correction_norm_inf": float(np.max(np.abs(correction), initial=0.0)),
                    "computed_relative_residual_l2": float(
                        np.linalg.norm(impedance @ x_refined - rhs)
                        / max(np.linalg.norm(rhs), np.linalg.norm(impedance @ x_refined))
                    ),
                }
            )

        variants = {"spsolve_unscaled": x_direct, "spsolve_row_column_equilibrated": x_scaled, "splu_two_refinements": x_refined}
        variant_records: dict[str, Any] = {}
        for name, solution in variants.items():
            residual = impedance @ solution - rhs
            relative = float(np.linalg.norm(residual) / max(np.linalg.norm(rhs), np.linalg.norm(impedance @ solution)))
            expanded = reducer.expand_complex_state(
                solution,
                loads_full,
                stiffness_factor=1.0 + 1j * 2.0 * math.pi * frequency * beta,
            )
            center = complex(expanded[center_index])
            variant_records[name] = {
                "guard_recheck": _guard_check(impedance, rhs, solution),
                "relative_residual_l2": relative,
                "backward_error_eta_inf": _eta_inf(impedance, rhs, solution),
                "center_uz_amplitude_mm": float(abs(center) * 1000.0),
                "center_uz_phase_degrees": float(np.degrees(np.angle(center))),
                "relative_solution_difference_inf_vs_unscaled": float(
                    np.max(np.abs(solution - x_direct), initial=0.0)
                    / max(np.max(np.abs(x_direct), initial=0.0), np.finfo(float).tiny)
                ),
            }

        checkpoint_key = f"frequency_{frequency:.9f}".replace(".", "p")
        checkpoint_path = checkpoint_root / f"{checkpoint_key}.json"
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        archived_frequency = float(checkpoint.get("frequency_hz", math.nan))
        if abs(archived_frequency - frequency) > 1.0e-12 or checkpoint.get("qf_route_status") != "QF_GUARD_REJECTED":
            raise ValueError(f"the selected J15 checkpoint status or frequency changed: {checkpoint_key}")
        archived_vector_path = checkpoint_root / f"{checkpoint_key}.npz"
        with np.load(archived_vector_path) as archived:
            archived_reduced = archived["diagnostic_reduced_response_real"] + 1j * archived[
                "diagnostic_reduced_response_imag"
            ]
        archive_relative_difference = float(
            np.max(np.abs(x_direct - archived_reduced), initial=0.0)
            / max(np.max(np.abs(archived_reduced), initial=0.0), np.finfo(float).tiny)
        )
        frequency_record = {
                "frequency_hz": frequency,
                "historical_checkpoint_status": checkpoint["checkpoint_stage"],
                "condition_number_2": float(np.linalg.cond(impedance_dense, p=2)),
                "historical_qf_status": checkpoint["qf_route_status"],
                "historical_guard_upper_bound": checkpoint["qf_route_details"]["diagnostics"][
                    "relative_residual_upper_bound"
                ],
                "unscaled_vs_archived_j15_reduced_vector_relative_inf": archive_relative_difference,
                "row_scale_min_max": [float(np.min(row_scale)), float(np.max(row_scale))],
                "column_scale_min_max": [float(np.min(column_scale)), float(np.max(column_scale))],
                "variants": variant_records,
                "iterative_refinement": refinement_records,
                "matrix_archive": f"guard_{checkpoint_key}.npz",
            }
        matrix_arrays = {
            "impedance_real": impedance_dense.real,
            "impedance_imag": impedance_dense.imag,
            "rhs_real": rhs.real,
            "rhs_imag": rhs.imag,
            "x_unscaled_real": x_direct.real,
            "x_unscaled_imag": x_direct.imag,
            "x_scaled_real": x_scaled.real,
            "x_scaled_imag": x_scaled.imag,
            "x_refined_real": x_refined.real,
            "x_refined_imag": x_refined.imag,
        }
        _atomic_npz(output / frequency_record["matrix_archive"], **matrix_arrays)
        _atomic_json(output / f"guard_{checkpoint_key}.json", frequency_record)
        results.append(frequency_record)

    summary = {
        "schema": "qfsolver-j16-guard-resolution-experiment-v1",
        "classification": "BOUNDED_SOLVER_DIAGNOSTIC_ON_QF_ASSEMBLED_8X8_SYSTEM",
        "contract_id": "J16-NAFEMS13H-GUARD-SCALE-REFINEMENT-001",
        "series_id": "dev-j16-nafems13h-guard-scale-001",
        "attempt_id": "J16-NAFEMS13H-GUARD-SCALE-001",
        "source_run_status": "J15_PYTEST_FAILED; all historical QF points remain rejected",
        "contract_sha256": contract_sha256,
        "source_git": _git_identity(),
        "model": "NAFEMS 13H MITC4 8x8; same frozen geometry, material, supports, pressure, and Rayleigh damping as J15",
        "methods": [
            "SciPy spsolve on the unscaled reduced QF impedance",
            "SciPy spsolve after one-pass row and column infinity-sum equilibration; solution mapped back to the original variables",
            "SciPy SuperLU with two correction steps using residuals computed in complex128",
        ],
        "guard_threshold": GUARD_LIMIT,
        "j15_input_manifest_sha256": input_manifest_sha256,
        "j15_input_artifacts_verified": verified_input_count,
        "frequencies": results,
        "interpretation_limit": (
            "The guard recheck uses the original unscaled QF matrix and unchanged threshold. These methods compare "
            "solution paths for the same assembled systems; they do not independently verify assembly or mechanics."
        ),
        "frequency_checkpoint_count": len(results),
    }
    summary_path = output / "guard_resolution_summary.json"
    _atomic_json(summary_path, summary)
    artifacts = []
    for path in sorted(item for item in output.iterdir() if item.is_file() and item.name != "artifact_manifest.json"):
        artifacts.append({"path": path.name, "bytes": path.stat().st_size, "sha256_raw": hashlib.sha256(path.read_bytes()).hexdigest()})
    _atomic_json(output / "artifact_manifest.json", {"artifacts": artifacts})
    return summary
