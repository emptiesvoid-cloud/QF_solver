"""Run the prospective WP13-08 MITC4 modal diagnostic campaign.

This runner deliberately leaves the modal solver and the historical WP04
evidence untouched.  It collects the historical route, recomputes residuals
from assembled reduced K/M and the returned eigenpairs, and compares those
observations with a separate direct SciPy generalized eigensolve.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import linear_sum_assignment
from scipy.sparse import csr_matrix

from solveur.api import solve_model
from solveur.core.analyses.dynamic_reduction import DynamicDofReducer
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.verification.mitc4_modal import Mitc4ModalCantileverStudy, _cantilever_shape


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = PROJECT_ROOT / "qualification/0_2_8/wp13_08_mitc4_modal_diagnostic_contract.json"
HISTORICAL_PATH = PROJECT_ROOT / "qualification/0_2_8/wp04_mitc_vnv.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "qualification/0_2_8/wp13_08_mitc4_modal_diagnostic"
HISTORICAL_RESIDUAL = 2.6317020430528298e-08
FROZEN_GATE = 1.0e-08
MESHES = ((4, 1), (8, 2), (12, 3), (16, 4), (24, 6))
REPLAY_MESHES = ((4, 1), (8, 2), (16, 4))


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=PROJECT_ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _semantic_digest(value: Any) -> str:
    return _sha256_bytes(_canonical_json(value).encode("utf-8"))


def _array_digest(value: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(repr(array.shape).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _sparse_digest(value: object) -> str:
    matrix = csr_matrix(value)
    digest = hashlib.sha256()
    digest.update(str(matrix.dtype).encode("ascii"))
    digest.update(repr(matrix.shape).encode("ascii"))
    for array in (matrix.data, matrix.indices, matrix.indptr):
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(repr(array.shape).encode("ascii"))
        digest.update(np.ascontiguousarray(array).tobytes(order="C"))
    return digest.hexdigest()


def _dense(value: object) -> np.ndarray:
    if hasattr(value, "toarray"):
        return np.asarray(value.toarray(), dtype=float)
    return np.asarray(value, dtype=float)


def _canonicalize_columns(vectors: np.ndarray) -> np.ndarray:
    result = np.asarray(vectors, dtype=float).copy()
    for index in range(result.shape[1]):
        pivot = int(np.argmax(np.abs(result[:, index])))
        if result[pivot, index] < 0.0:
            result[:, index] *= -1.0
    return result


def _relative_residual(
    stiffness: np.ndarray, mass: np.ndarray, value: float, vector: np.ndarray
) -> tuple[float, float, float, float]:
    k_vector = stiffness @ vector
    m_vector = mass @ vector
    residual = k_vector - float(value) * m_vector
    numerator = float(np.linalg.norm(residual))
    denominator = max(
        float(np.linalg.norm(k_vector)),
        abs(float(value)) * float(np.linalg.norm(m_vector)),
        1.0,
    )
    homogeneous_denominator = max(
        float(np.linalg.norm(k_vector)), abs(float(value)) * float(np.linalg.norm(m_vector))
    )
    scale_invariant = numerator / homogeneous_denominator if homogeneous_denominator > 0.0 else 0.0
    return numerator / denominator, numerator, denominator, scale_invariant


def _mac(first: np.ndarray, second: np.ndarray) -> float:
    numerator = float(np.dot(first, second)) ** 2
    denominator = max(float(np.dot(first, first) * np.dot(second, second)), 1.0e-30)
    return numerator / denominator


def _mass_mac_matrix(first: np.ndarray, second: np.ndarray, mass: np.ndarray) -> np.ndarray:
    first_mass = first.T @ mass @ second
    first_norm = np.diag(first.T @ mass @ first)
    second_norm = np.diag(second.T @ mass @ second)
    denominator = np.maximum(first_norm[:, None] * second_norm[None, :], 1.0e-30)
    return np.square(first_mass) / denominator


def _study_point(
    study: Mitc4ModalCantileverStudy,
    nx: int,
    ny: int,
    reference_frequency: float,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    model, nodes = study.build_model(nx, ny)
    result = solve_model(model, enforce_policy=False)

    assembler = GlobalAssembler()
    dofs = model.dof_manager()
    stiffness, mass, stiffness_audit, mass_audit = assembler.assemble_stiffness_and_mass(model, dofs)
    fixed = assembler.fixed_indices(model, dofs)
    reducer = DynamicDofReducer.from_system(model, dofs, mass, stiffness, fixed)
    reduced_stiffness = _dense(reducer.stiffness)
    reduced_mass = _dense(reducer.mass)

    runtime_values = np.asarray(result.eigenvalues, dtype=float)
    runtime_vectors = np.column_stack(
        [reducer.reduce_state(np.asarray(result.modes[:, index], dtype=float)) for index in range(runtime_values.size)]
    )
    runtime_vectors = _canonicalize_columns(runtime_vectors)

    oracle_count = min(runtime_values.size + 4, reduced_stiffness.shape[0])
    oracle_values, oracle_vectors = eigh(
        reduced_stiffness,
        reduced_mass,
        subset_by_index=(0, oracle_count - 1),
        check_finite=True,
    )
    oracle_values = np.asarray(oracle_values[: runtime_values.size], dtype=float)
    oracle_vectors = _canonicalize_columns(np.asarray(oracle_vectors[:, : runtime_values.size], dtype=float))
    mac_matrix = _mass_mac_matrix(runtime_vectors, oracle_vectors, reduced_mass)
    row_indices, column_indices = linear_sum_assignment(-mac_matrix)
    assignment = sorted(zip(row_indices.tolist(), column_indices.tolist()))

    independent_residuals = []
    independent_numerators = []
    independent_denominators = []
    independent_scale_invariant = []
    oracle_residuals = []
    oracle_numerators = []
    oracle_denominators = []
    oracle_scale_invariant = []
    for index, value in enumerate(runtime_values):
        residual, numerator, denominator, scale_invariant = _relative_residual(
            reduced_stiffness, reduced_mass, float(value), runtime_vectors[:, index]
        )
        independent_residuals.append(residual)
        independent_numerators.append(numerator)
        independent_denominators.append(denominator)
        independent_scale_invariant.append(scale_invariant)
        oracle_index = next(column for row, column in assignment if row == index)
        residual, numerator, denominator, scale_invariant = _relative_residual(
            reduced_stiffness, reduced_mass, float(oracle_values[oracle_index]), oracle_vectors[:, oracle_index]
        )
        oracle_residuals.append(residual)
        oracle_numerators.append(numerator)
        oracle_denominators.append(denominator)
        oracle_scale_invariant.append(scale_invariant)

    gramian = runtime_vectors.T @ reduced_mass @ runtime_vectors
    off_diagonal = gramian - np.diag(np.diag(gramian))
    normalization_error = float(np.max(np.abs(np.diag(gramian) - 1.0), initial=0.0))
    orthogonality_error = float(np.linalg.norm(off_diagonal) / max(float(np.linalg.norm(gramian)), 1.0))

    uz = np.asarray([result.dofs.index(node, "UZ") for node in range(nodes.shape[0])], dtype=int)
    reference_shape = _cantilever_shape(nodes[:, 0] / study.length)
    first_mode_shape = np.asarray(result.modes[uz, 0], dtype=float)
    low_values = np.asarray(oracle_values, dtype=float)
    gaps = np.diff(low_values) / np.maximum(np.abs(low_values[:-1]), 1.0e-30)
    runtime_reported = [float(value) for value in result.solver.get("relative_residuals", [])]
    runtime_recomputed = [float(value) for value in independent_residuals]
    mode_diffs = np.abs(runtime_values - oracle_values)
    mode_frequency_diffs = np.abs(
        np.sqrt(runtime_values) / (2.0 * math.pi) - np.sqrt(oracle_values) / (2.0 * math.pi)
    )
    point = {
        "mesh": [int(nx), int(ny)],
        "element_count": int(nx * ny),
        "node_count": int(nodes.shape[0]),
        "reduced_dof_count": int(reduced_stiffness.shape[0]),
        "runtime_method": str(result.method),
        "runtime_eigenvalues": runtime_values.tolist(),
        "oracle_eigenvalues": oracle_values.tolist(),
        "runtime_frequencies_hz": (np.sqrt(runtime_values) / (2.0 * math.pi)).tolist(),
        "oracle_frequencies_hz": (np.sqrt(oracle_values) / (2.0 * math.pi)).tolist(),
        "runtime_residuals_reported": runtime_reported,
        "independent_residuals": runtime_recomputed,
        "independent_residual_numerators": independent_numerators,
        "independent_residual_denominators": independent_denominators,
        "independent_scale_invariant_residuals": independent_scale_invariant,
        "oracle_residuals": oracle_residuals,
        "oracle_residual_numerators": oracle_numerators,
        "oracle_residual_denominators": oracle_denominators,
        "oracle_scale_invariant_residuals": oracle_scale_invariant,
        "runtime_reported_vs_recomputed_max_abs": float(
            np.max(np.abs(np.asarray(runtime_reported) - np.asarray(runtime_recomputed)), initial=0.0)
        ),
        "runtime_vs_oracle_eigenvalue_max_abs": float(np.max(mode_diffs, initial=0.0)),
        "runtime_vs_oracle_frequency_max_abs_hz": float(np.max(mode_frequency_diffs, initial=0.0)),
        "mass_gramian": gramian.tolist(),
        "mass_orthogonality_error": orthogonality_error,
        "normalization_error": normalization_error,
        "mode_matching_assignment_zero_based": assignment,
        "mode_matching_mac_matrix": mac_matrix.tolist(),
        "matched_mass_mac_min": float(min(mac_matrix[row, column] for row, column in assignment)),
        "first_frequency_reference_hz": float(reference_frequency),
        "first_frequency_error": abs(float(np.sqrt(runtime_values[0]) / (2.0 * math.pi)) - reference_frequency)
        / reference_frequency,
        "first_mode_shape_mac": _mac(first_mode_shape, reference_shape),
        "lowest_oracle_eigenvalues": low_values.tolist(),
        "unexpected_rigid_modes": bool(np.any(low_values <= 1.0e-12)),
        "minimum_positive_mode_gap_relative": float(np.min(gaps, initial=np.inf)) if gaps.size else None,
        "duplicate_mode_diagnostic": bool(np.any(gaps <= 1.0e-10)),
        "solver_diagnostics": {
            "arpack": result.solver.get("arpack"),
            "dense_conversion_used": result.solver.get("dense_conversion_used"),
            "backend": result.solver.get("backend"),
            "dynamic_reduction": result.solver.get("dynamic_reduction"),
            "eigenpair_refinement": result.solver.get("eigenpair_refinement"),
            "modal_masses": result.solver.get("modal_masses"),
            "modal_stiffnesses": result.solver.get("modal_stiffnesses"),
        },
        "assembly_diagnostics": {"stiffness": stiffness_audit, "mass": mass_audit},
        "matrix_digests": {
            "global_stiffness": _sparse_digest(stiffness),
            "global_mass": _sparse_digest(mass),
            "reduced_stiffness": _array_digest(reduced_stiffness),
            "reduced_mass": _array_digest(reduced_mass),
        },
    }
    arrays = {
        f"m{nx}x{ny}_nodes": np.asarray(nodes, dtype=float),
        f"m{nx}x{ny}_runtime_modes": runtime_vectors,
        f"m{nx}x{ny}_oracle_modes": oracle_vectors,
        f"m{nx}x{ny}_runtime_eigenvalues": runtime_values,
        f"m{nx}x{ny}_oracle_eigenvalues": oracle_values,
        f"m{nx}x{ny}_runtime_frequencies": np.sqrt(runtime_values) / (2.0 * math.pi),
        f"m{nx}x{ny}_oracle_frequencies": np.sqrt(oracle_values) / (2.0 * math.pi),
        f"m{nx}x{ny}_mass_gramian": gramian,
    }
    return _jsonable(point), arrays


def _collect_campaign(meshes: tuple[tuple[int, int], ...]) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    study = Mitc4ModalCantileverStudy(meshes=meshes)
    reference = float(study.analytical_frequency_hz)
    points: list[dict[str, Any]] = []
    arrays: dict[str, np.ndarray] = {}
    for nx, ny in meshes:
        point, point_arrays = _study_point(study, nx, ny, reference)
        points.append(point)
        arrays.update(point_arrays)
    for previous, current in zip(points, points[1:]):
        current["adjacent_frequency_increment"] = abs(
            float(current["runtime_frequencies_hz"][0]) - float(previous["runtime_frequencies_hz"][0])
        ) / max(abs(float(current["runtime_frequencies_hz"][0])), 1.0e-30)
    return {
        "reference_frequency_hz": reference,
        "points": points,
        "max_runtime_residual": max(max(point["runtime_residuals_reported"]) for point in points),
        "max_independent_residual": max(max(point["independent_residuals"]) for point in points),
        "max_oracle_residual": max(max(point["oracle_residuals"]) for point in points),
        "max_mass_orthogonality_error": max(point["mass_orthogonality_error"] for point in points),
        "max_normalization_error": max(point["normalization_error"] for point in points),
        "max_runtime_oracle_frequency_difference_hz": max(
            point["runtime_vs_oracle_frequency_max_abs_hz"] for point in points
        ),
    }, arrays


def _compare_replays(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    fields = [
        "runtime_eigenvalues",
        "oracle_eigenvalues",
        "runtime_frequencies_hz",
        "oracle_frequencies_hz",
        "runtime_residuals_reported",
        "independent_residuals",
        "oracle_residuals",
        "mass_gramian",
        "mass_orthogonality_error",
        "normalization_error",
        "mode_matching_assignment_zero_based",
        "mode_matching_mac_matrix",
        "first_mode_shape_mac",
    ]
    point_results = []
    for point_a, point_b in zip(first["points"], second["points"]):
        differences: dict[str, float] = {}
        identical = True
        for field in fields:
            left = np.asarray(point_a[field])
            right = np.asarray(point_b[field])
            if left.dtype.kind in "OUS" or right.dtype.kind in "OUS":
                same = _canonical_json(point_a[field]) == _canonical_json(point_b[field])
                difference = 0.0 if same else float("inf")
            else:
                difference = float(np.max(np.abs(left - right), initial=0.0))
                same = bool(np.allclose(left, right, rtol=0.0, atol=1.0e-12))
            differences[field] = difference
            identical = identical and same
        point_results.append({"mesh": point_a["mesh"], "pass": identical, "max_abs_differences": differences})
    digest_a = _semantic_digest(first)
    digest_b = _semantic_digest(second)
    return {
        "points": point_results,
        "semantic_digest_first": digest_a,
        "semantic_digest_second": digest_b,
        "semantic_digest_equal": digest_a == digest_b,
        "pass": all(item["pass"] for item in point_results) and digest_a == digest_b,
    }


def _classify_root_cause(campaign: dict[str, Any], historical_reproduced: bool) -> tuple[str, str]:
    if not historical_reproduced:
        return "OTHER", "The declared historical maximum was not reproduced; no root-cause classification is permitted."
    max_runtime = float(campaign["max_runtime_residual"])
    max_independent = float(campaign["max_independent_residual"])
    max_oracle = float(campaign["max_oracle_residual"])
    runtime_independent_gap = max(
        float(point["runtime_reported_vs_recomputed_max_abs"])
        for point in campaign["points"]
    )
    if max_independent <= FROZEN_GATE and max_runtime > FROZEN_GATE:
        return (
            "POSTPROCESSING",
            "The frozen runtime metric exceeds the gate but the independently recomputed eigenpair residual is within it; the discrepancy is in diagnostic/post-processing semantics, not a passing gate substitution.",
        )
    if max_independent > FROZEN_GATE and max_oracle <= FROZEN_GATE and runtime_independent_gap <= 1.0e-12:
        return (
            "NUMERICAL_PRECISION",
            "The runtime and independent residuals agree above the frozen gate, while the separate dense eigensolve produces a lower residual; this is consistent with conditioning/finite-precision behavior of the historical production eigenpair path.",
        )
    if max_independent > FROZEN_GATE and max_oracle > FROZEN_GATE:
        return (
            "FORMULATION_LIMITATION",
            "Both the production eigenpair and the independent dense eigensolve remain above the frozen residual gate; no normalization or tolerance relaxation can legitimately close the route.",
        )
    return "OTHER", "The diagnostic observations do not isolate a single allowed root-cause class."


def run(output: Path) -> dict[str, Any]:
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"Output directory must be new or empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["status"] != "PREDECLARED_NOT_EXECUTED" or not contract["contract_created_before_campaign"]:
        raise RuntimeError("WP13-08 contract is not in the required predeclared state.")
    contract_sha = _sha256_file(CONTRACT_PATH)
    repo_sha = _git("rev-parse", "HEAD")
    source_status = _git("status", "--short", "--", "src", "tests", "qualification/0_2_8/wp04_mitc_vnv.json")
    if source_status:
        raise RuntimeError(f"Numerical or historical source is dirty before campaign: {source_status}")

    environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
    }
    try:
        import scipy

        environment["scipy"] = scipy.__version__
    except Exception:
        environment["scipy"] = "unknown"

    campaign, campaign_arrays = _collect_campaign(MESHES)
    replay_one, replay_one_arrays = _collect_campaign(REPLAY_MESHES)
    replay_two, replay_two_arrays = _collect_campaign(REPLAY_MESHES)
    replay = _compare_replays(replay_one, replay_two)

    baseline_max = float(campaign["max_runtime_residual"])
    baseline_locations = [
        (point["mesh"], index + 1, value)
        for point in campaign["points"]
        for index, value in enumerate(point["runtime_residuals_reported"])
    ]
    baseline_mesh, baseline_mode, _ = max(baseline_locations, key=lambda item: item[2])
    reproduction = math.isclose(
        baseline_max,
        HISTORICAL_RESIDUAL,
        rel_tol=float(contract["historical_reference"]["reproduction_check"]["relative_tolerance"]),
        abs_tol=float(contract["historical_reference"]["reproduction_check"]["absolute_tolerance"]),
    )
    root_cause, root_cause_evidence = _classify_root_cause(campaign, reproduction)
    gate_values = {
        "historical_residual": HISTORICAL_RESIDUAL,
        "frozen_gate": FROZEN_GATE,
        "baseline_runtime_max_residual": baseline_max,
        "baseline_independent_max_residual": float(campaign["max_independent_residual"]),
        "baseline_oracle_max_residual": float(campaign["max_oracle_residual"]),
    }
    all_independent_pass = float(campaign["max_independent_residual"]) <= FROZEN_GATE
    all_orthogonality_pass = float(campaign["max_mass_orthogonality_error"]) <= 1.0e-08
    all_mode_pass = all(
        point["first_frequency_error"] <= 0.02
        and point["first_mode_shape_mac"] >= 0.999
        for point in campaign["points"]
    )
    refinement_increments = [
        point["adjacent_frequency_increment"]
        for point in campaign["points"][1:]
        if "adjacent_frequency_increment" in point
    ]
    refinement_pass = bool(refinement_increments) and max(refinement_increments) <= 0.02
    promotion_candidate = bool(
        all_independent_pass
        and all_orthogonality_pass
        and all_mode_pass
        and refinement_pass
        and replay["pass"]
    )

    arrays: dict[str, np.ndarray] = {}
    arrays.update({f"main_{key}": value for key, value in campaign_arrays.items()})
    arrays.update({f"replay1_{key}": value for key, value in replay_one_arrays.items()})
    arrays.update({f"replay2_{key}": value for key, value in replay_two_arrays.items()})
    npz_path = output / "wp13_08_mitc4_modal_diagnostic_arrays.npz"
    np.savez_compressed(npz_path, **arrays)
    evidence = {
        "schema_version": 1,
        "contract_id": contract["contract_id"],
        "contract_sha": contract_sha,
        "repo_sha": repo_sha,
        "environment": environment,
        "historical_reference": {
            **contract["historical_reference"],
            "historical_file_sha256": _sha256_file(HISTORICAL_PATH),
        },
        "benchmark_inputs": contract["scope"],
        "solver_parameters": contract["eigensolver_diagnostic"],
        "campaign": campaign,
        "independent_oracle": contract["oracle"],
        "gate_decisions": {
            "residual_gate": bool(float(campaign["max_independent_residual"]) <= FROZEN_GATE),
            "orthogonality_gate": all_orthogonality_pass,
            "frequency_and_mode_gate": all_mode_pass,
            "refinement_characterization": refinement_pass,
            "replay_gate": bool(replay["pass"]),
        },
        "historical_failure_reproduced": reproduction,
        "baseline_max_residual": baseline_max,
        "baseline_mode_index": {"mesh": baseline_mesh, "mode_index_one_based": int(baseline_mode)},
        "root_cause": {"classification": root_cause, "evidence": root_cause_evidence},
        "runtime_vs_independent": {
            "max_reported_recomputed_absolute_difference": max(
                point["runtime_reported_vs_recomputed_max_abs"] for point in campaign["points"]
            ),
            "reported_metric_not_used_as_independent_result": True,
        },
        "refinement_characterization": {
            "status": "CHARACTERIZATION_ONLY",
            "increments": refinement_increments,
            "max_increment": max(refinement_increments, default=None),
        },
        "replays": {
            "count": 2,
            "mesh_levels": [list(mesh) for mesh in REPLAY_MESHES],
            "comparison": replay,
        },
        "arrays": {
            "path": npz_path.name,
            "sha256": _sha256_file(npz_path),
            "keys": sorted(arrays),
            "array_count": len(arrays),
        },
        "integrity": {
            "historical_evidence_unchanged": True,
            "historical_0_2_7_evidence_unchanged": True,
            "numerical_source_changed": False,
            "formulation_changed": False,
            "gate_changed": False,
            "maturity_changed": False,
            "full_test_suite": "DEFERRED_TO_WP13_FINAL_GATE",
        },
        "decision": {
            "technical_decision": "PROMOTION_CANDIDATE" if promotion_candidate else "KEEP_EXPERIMENTAL",
            "promotion_candidate": promotion_candidate,
            "owner_gate_required": True,
            "claim_candidate": (
                "Bounded MITC4 modal slender-cantilever diagnostic candidate only; no general shell modal claim."
                if promotion_candidate
                else "MITC4 remains EXPERIMENTAL; the frozen residual gate remains unmet in the declared slender-cantilever diagnostic."
            ),
        },
    }
    evidence_path = output / "wp13_08_mitc4_modal_diagnostic_evidence.json"
    evidence_path.write_text(json.dumps(_jsonable(evidence), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "contract_id": contract["contract_id"],
        "contract_sha": contract_sha,
        "repo_sha": repo_sha,
        "evidence_file": evidence_path.name,
        "evidence_sha256": _sha256_file(evidence_path),
        "arrays_file": npz_path.name,
        "arrays_sha256": _sha256_file(npz_path),
        "technical_decision": evidence["decision"]["technical_decision"],
        "historical_evidence_immutable": True,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    evidence = run(args.output)
    print(json.dumps({
        "status": evidence["decision"]["technical_decision"],
        "historical_failure_reproduced": evidence["historical_failure_reproduced"],
        "baseline_max_residual": evidence["baseline_max_residual"],
        "independent_max_residual": evidence["campaign"]["max_independent_residual"],
        "root_cause": evidence["root_cause"]["classification"],
        "replay_pass": evidence["replays"]["comparison"]["pass"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
