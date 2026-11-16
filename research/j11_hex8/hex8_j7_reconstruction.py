"""J11 reconstruction of archived J7 HEX8-SRI systems through global QF assembly."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import tempfile
from importlib import metadata
from pathlib import Path
from typing import Any

import mpmath
import numpy as np
import scipy
from scipy.linalg import solve as scipy_solve

from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.hex8_sri import Hex8SRIElement
from solveur.materials.solid import SolidMaterial


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "research/j11_hex8/contracts/hex8_j7_reconstruction_contract_corrective_v2.json"
INPUT_PATH = ROOT / "research/j10/results/diagnostic-2026-11-16/hex8_j7_distortion/hex8_j7_distortion_states.npz"
J10_RESULT_PATH = ROOT / "research/j10/results/diagnostic-2026-11-16/hex8_j7_distortion/result.json"
NODEID = "tests/verification/test_j11_hex8_j7_reconstruction.py::test_j11_hex8_global_and_independent_reconstruction_corrective_v2"
ALPHAS = (0.0, 0.05, 0.10, 0.15)
LENGTH_M = 20.0
LOCAL_THICKNESS_M = 0.04
YOUNG_MODULUS_PA = 1.0e6
POISSON_RATIO = 0.495


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> str:
    encoded = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    return hashlib.sha256(encoded).hexdigest()


def _attempt_output_dir() -> tuple[Path, dict[str, Any]]:
    if os.environ.get("QF_DEVELOPMENT_AUTONOMOUS") != "1":
        raise RuntimeError("J11 HEX8 outputs require the registered development launcher")
    temporary = Path(os.environ["TMP"]).resolve(strict=True)
    attempt_dir = temporary.parent
    record_path = attempt_dir / "run.json"
    if not record_path.is_file():
        raise RuntimeError("The development runner attempt record is missing")
    run = json.loads(record_path.read_text(encoding="utf-8"))
    if run.get("state") != "RUNNING" or run.get("worktree_id") != "j11" or run.get("target") != [NODEID]:
        raise RuntimeError("The development runner does not identify this exact J11 HEX8 node")
    try:
        attempt_dir.resolve().relative_to((ROOT / ".codex/development-runs/worktrees/j11").resolve())
    except ValueError as exc:
        raise RuntimeError("J11 output directory is outside its registered attempt namespace") from exc
    output = attempt_dir / "output" / "j11_hex8_reconstruction_corrective_v2"
    output.mkdir(parents=True, exist_ok=False)
    return output, run


def _force_moment(coordinates: np.ndarray, vector: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rows = np.asarray(vector, dtype=np.float64).reshape((-1, 3))
    force = np.asarray([math.fsum(float(value) for value in rows[:, component]) for component in range(3)])
    moments = np.cross(coordinates, rows)
    moment = np.asarray([math.fsum(float(value) for value in moments[:, component]) for component in range(3)])
    return force, moment


def _residual_metrics(
    coordinates: np.ndarray,
    stiffness: np.ndarray,
    force: np.ndarray,
    displacement: np.ndarray,
    fixed: np.ndarray,
    free: np.ndarray,
) -> dict[str, Any]:
    residual = stiffness @ displacement - force
    reactions = np.zeros_like(force)
    reactions[fixed] = residual[fixed]
    external_force, external_moment = _force_moment(coordinates, force)
    reaction_force, reaction_moment = _force_moment(coordinates, reactions)
    free_residual = residual[free]
    free_residual_norm = float(np.linalg.norm(free_residual))
    force_scale = max(float(np.linalg.norm(force)), 1.0)
    moment_scale = max(float(np.linalg.norm(external_force)) * LENGTH_M, 1.0)
    backward_scale = float(np.linalg.norm(stiffness[np.ix_(free, free)], ord="fro")) * float(np.linalg.norm(displacement[free])) + float(np.linalg.norm(force[free]))
    return {
        "free_residual_l2_n": free_residual_norm,
        "free_residual_relative_to_force": free_residual_norm / force_scale,
        "free_residual_backward_error": free_residual_norm / max(backward_scale, np.finfo(float).tiny),
        "reaction_resultant_n": reaction_force.tolist(),
        "reaction_moment_about_origin_nm": reaction_moment.tolist(),
        "external_resultant_n": external_force.tolist(),
        "external_moment_about_origin_nm": external_moment.tolist(),
        "force_closure_residual_n": (external_force + reaction_force).tolist(),
        "force_closure_relative": float(np.linalg.norm(external_force + reaction_force) / force_scale),
        "moment_closure_residual_nm": (external_moment + reaction_moment).tolist(),
        "moment_closure_relative": float(np.linalg.norm(external_moment + reaction_moment) / moment_scale),
        "reactions_n": reactions,
        "free_residual_n": free_residual,
    }


def _mpmath_solve(matrix: np.ndarray, rhs: np.ndarray, *, digits: int = 80) -> list[Any]:
    mpmath.mp.dps = digits
    matrix_mp = mpmath.matrix([[mpmath.mpf(float(value)) for value in row] for row in matrix])
    rhs_mp = mpmath.matrix([mpmath.mpf(float(value)) for value in rhs])
    solution_mp = mpmath.lu_solve(matrix_mp, rhs_mp)
    return [solution_mp[index] for index in range(len(rhs))]


def _assemble_hex8_sri_global_stiffness(
    coordinates: np.ndarray,
    connectivity: np.ndarray,
    material: SolidMaterial,
) -> tuple[np.ndarray, np.ndarray]:
    """Scatter the research-only QF HEX8-SRI element matrices into a global K."""
    stiffness = np.zeros((3 * len(coordinates), 3 * len(coordinates)), dtype=np.float64)
    element = Hex8SRIElement(material)
    gauss_determinants: list[float] = []
    for nodes in connectivity:
        element_coordinates = coordinates[nodes]
        element.validate_geometry(element_coordinates)
        local_dofs = np.asarray(
            [[3 * int(node) + component for component in range(3)] for node in nodes],
            dtype=np.int64,
        ).ravel()
        stiffness[np.ix_(local_dofs, local_dofs)] += element.stiffness(element_coordinates)
        gauss_determinants.extend(
            float(Hex8Element.jacobian_determinant(element_coordinates, point))
            for point in Hex8Element.integration_points
        )
    return stiffness, np.asarray(gauss_determinants, dtype=np.float64)


def _warp(coordinates: np.ndarray, alpha: float) -> np.ndarray:
    warped = np.asarray(coordinates, dtype=np.float64).copy()
    interior = (
        (coordinates[:, 0] > 0.0)
        & (coordinates[:, 0] < LENGTH_M)
        & np.isclose(coordinates[:, 1], 0.5, rtol=0.0, atol=1.0e-12)
        & np.isclose(coordinates[:, 2], 0.02, rtol=0.0, atol=1.0e-12)
    )
    warped[interior, 2] += alpha * LOCAL_THICKNESS_M * np.sin(np.pi * warped[interior, 0] / LENGTH_M)
    return warped


def _mpmath_residual_and_closure(
    coordinates: np.ndarray,
    full_stiffness: np.ndarray,
    force: np.ndarray,
    displacement: list[Any] | np.ndarray,
    fixed: np.ndarray,
    free: np.ndarray,
    *,
    digits: int = 80,
) -> dict[str, Any]:
    """Evaluate residuals and support wrench using the same float-input matrix at high precision."""
    mpmath.mp.dps = digits
    coordinates_mp = [[mpmath.mpf(float(v)) for v in row] for row in coordinates]
    stiffness_mp = [[mpmath.mpf(float(v)) for v in row] for row in full_stiffness]
    force_mp = [mpmath.mpf(float(v)) for v in force]
    displacement_mp = [
        value if isinstance(value, mpmath.mpf) else mpmath.mpf(float(value))
        for value in displacement
    ]
    residual_mp = [
        sum(stiffness_mp[row][column] * displacement_mp[column] for column in range(len(force_mp))) - force_mp[row]
        for row in range(len(force_mp))
    ]
    fixed_set = set(map(int, fixed))
    reaction_mp = [residual_mp[index] if index in fixed_set else mpmath.mpf("0") for index in range(len(force_mp))]
    external_force = [sum(force_mp[3 * node + axis] for node in range(len(coordinates))) for axis in range(3)]
    reaction_force = [sum(reaction_mp[3 * node + axis] for node in range(len(coordinates))) for axis in range(3)]
    external_moment = [mpmath.mpf("0") for _ in range(3)]
    reaction_moment = [mpmath.mpf("0") for _ in range(3)]
    for node, xyz in enumerate(coordinates_mp):
        external = force_mp[3 * node : 3 * node + 3]
        reaction = reaction_mp[3 * node : 3 * node + 3]
        for axis, (left, right) in enumerate(((1, 2), (2, 0), (0, 1))):
            external_moment[axis] += xyz[left] * external[right] - xyz[right] * external[left]
            reaction_moment[axis] += xyz[left] * reaction[right] - xyz[right] * reaction[left]
    free_residual_mp = [residual_mp[index] for index in free]
    free_norm = mpmath.sqrt(sum(value * value for value in free_residual_mp))
    force_closure = [external_force[i] + reaction_force[i] for i in range(3)]
    moment_closure = [external_moment[i] + reaction_moment[i] for i in range(3)]
    force_norm = mpmath.sqrt(sum(value * value for value in external_force))
    moment_norm = mpmath.sqrt(sum(value * value for value in external_moment))
    length_scale = mpmath.mpf(str(LENGTH_M))
    return {
        "free_residual_l2_n": float(free_norm),
        "free_residual_relative_to_force": float(free_norm / max(force_norm, mpmath.mpf(1))),
        "force_closure_residual_n": [float(value) for value in force_closure],
        "force_closure_relative": float(
            mpmath.sqrt(sum(value * value for value in force_closure)) / max(force_norm, mpmath.mpf(1))
        ),
        "moment_closure_residual_nm": [float(value) for value in moment_closure],
        "moment_closure_relative": float(
            mpmath.sqrt(sum(value * value for value in moment_closure))
            / max(force_norm * length_scale, moment_norm, mpmath.mpf(1))
        ),
        "precision_decimal_digits": digits,
        "input_numbers": "Archived float64 matrix, load, coordinates and state are converted to multiprecision; an mpmath solution remains at the declared precision.",
    }


def _environment() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "mpmath": metadata.version("mpmath"),
    }


def run_diagnostic() -> dict[str, Any]:
    output_dir, run = _attempt_output_dir()
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    contract_sha = _canonical_sha256(CONTRACT_PATH)
    for item in contract["source_identity"]:
        if _canonical_sha256(ROOT / item["path"]) != item["canonical_sha256"]:
            raise RuntimeError(f"J11 HEX8 source differs from the frozen contract: {item['path']}")
    if _sha256(INPUT_PATH) != contract["inputs"]["j10_state_npz_sha256_raw"]:
        raise RuntimeError("Archived J10 HEX8 states do not match the frozen J11 input digest")
    if _sha256(J10_RESULT_PATH) != contract["inputs"]["j10_result_json_sha256_raw"]:
        raise RuntimeError("Archived J10 HEX8 result does not match the frozen J11 input digest")

    with np.load(INPUT_PATH, allow_pickle=False) as archive:
        original = {name: np.asarray(archive[name]) for name in archive.files}
    j10_result = json.loads(J10_RESULT_PATH.read_text(encoding="utf-8"))
    if j10_result.get("execution_status") != "COMPLETED_EXPLORATORY" or j10_result.get("historical_j7_status") != "FAIL":
        raise RuntimeError("J11 requires the unchanged exploratory J10 archive and historical J7 FAIL")
    coordinates0 = np.asarray(original["original_coordinates_m"], dtype=np.float64)
    connectivity = np.asarray(original["connectivity_hex8"], dtype=np.int64)
    force = np.asarray(original["force_n"], dtype=np.float64)
    fixed_mask = np.asarray(original["fixed_dof_mask"], dtype=bool)
    archived_displacement0 = np.asarray(original["archived_j7_displacement_m"], dtype=np.float64)
    if coordinates0.shape != (45, 3) or connectivity.shape != (16, 8) or force.shape != (135,) or fixed_mask.shape != (135,):
        raise RuntimeError("J11 input is not the archived J7 4x2x2 HEX8-SRI near-degenerate case")
    fixed = np.flatnonzero(fixed_mask)
    free = np.flatnonzero(~fixed_mask)
    if len(fixed) != 27 or len(free) != 108:
        raise RuntimeError("J11 fixed/free DOF map differs from the exact archived J7 system")
    external_force, _ = _force_moment(coordinates0, force)
    if not np.allclose(external_force, (0.0, 0.0, -1.0), rtol=0.0, atol=1.0e-14):
        raise RuntimeError("J11 archived J7 nodal force resultant differs from its frozen -1 N input")
    material = SolidMaterial(E=YOUNG_MODULUS_PA, nu=POISSON_RATIO)

    levels: list[dict[str, Any]] = []
    arrays: dict[str, np.ndarray] = {"coordinates_alpha_0_m": coordinates0, "force_n": force, "fixed_dof_mask": fixed_mask}
    for index, alpha in enumerate(ALPHAS):
        coordinates = _warp(coordinates0, alpha)
        global_stiffness, gauss_determinants = _assemble_hex8_sri_global_stiffness(
            coordinates, connectivity, material
        )
        if not np.all(np.isfinite(gauss_determinants)) or np.any(gauss_determinants <= 0.0):
            raise RuntimeError(f"J11 SRI kernel has a non-positive or non-finite Gauss Jacobian at alpha={alpha:g}")
        expected_stiffness = np.asarray(original[f"stiffness_alpha_{index}_n_per_m"], dtype=np.float64)
        matrix_delta = float(
            np.linalg.norm(global_stiffness - expected_stiffness, ord="fro")
            / max(float(np.linalg.norm(expected_stiffness, ord="fro")), np.finfo(float).tiny)
        )
        # This bound checks that the QF research-kernel scatter reproduces J10's frozen global matrix.
        if matrix_delta > 1.0e-12:
            raise RuntimeError(f"QF HEX8-SRI global scatter differs from archived J10 matrix at alpha={alpha:g}")

        matrix_ff = global_stiffness[np.ix_(free, free)]
        force_f = force[free]
        direct = np.zeros_like(force)
        direct[free] = np.linalg.solve(matrix_ff, force_f)
        scaled_diag = 1.0 / np.sqrt(np.maximum(np.abs(np.diag(matrix_ff)), np.finfo(float).tiny))
        scaled_matrix = scaled_diag[:, None] * matrix_ff * scaled_diag[None, :]
        scaled_rhs = scaled_diag * force_f
        scaled = np.zeros_like(force)
        scaled[free] = scaled_diag * np.linalg.solve(scaled_matrix, scaled_rhs)
        scipy_direct = np.zeros_like(force)
        scipy_direct[free] = scipy_solve(matrix_ff, force_f, assume_a="sym", check_finite=True)
        metrics_direct = _residual_metrics(coordinates, global_stiffness, force, direct, fixed, free)
        metrics_scaled = _residual_metrics(coordinates, global_stiffness, force, scaled, fixed, free)
        metrics_scipy = _residual_metrics(coordinates, global_stiffness, force, scipy_direct, fixed, free)
        condition_raw = float(np.linalg.cond(matrix_ff))
        condition_scaled = float(np.linalg.cond(scaled_matrix))
        scaled_rel = float(np.linalg.norm(scaled[free] - direct[free]) / max(np.linalg.norm(direct[free]), np.finfo(float).tiny))
        scipy_rel = float(np.linalg.norm(scipy_direct[free] - direct[free]) / max(np.linalg.norm(direct[free]), np.finfo(float).tiny))

        high_precision_solve: dict[str, Any] | None = None
        mp_solution: np.ndarray | None = None
        if alpha == 0.0:
            mp_solution_free = _mpmath_solve(matrix_ff, force_f, digits=80)
            mp_solution_mp = [mpmath.mpf("0") for _ in range(len(force))]
            for dof_index, value in zip(free, mp_solution_free, strict=True):
                mp_solution_mp[int(dof_index)] = value
            mp_solution = np.asarray([float(value) for value in mp_solution_mp], dtype=np.float64)
            high_precision_solve = _mpmath_residual_and_closure(
                coordinates, global_stiffness, force, mp_solution_mp, fixed, free
            )
            direct_mp = [mpmath.mpf(float(value)) for value in direct[free]]
            solution_norm = mpmath.sqrt(sum(value * value for value in mp_solution_free))
            difference_norm = mpmath.sqrt(
                sum((left - right) * (left - right) for left, right in zip(mp_solution_free, direct_mp, strict=True))
            )
            high_precision_solve["relative_displacement_difference_to_numpy_direct"] = float(
                difference_norm / max(solution_norm, mpmath.mpf("1e-100"))
            )
        archived_state_delta = None
        j10_state_delta = None
        archived_matrix_delta0 = None
        if alpha == 0.0:
            archived_state_delta = float(
                np.linalg.norm(direct - archived_displacement0)
                / max(float(np.linalg.norm(archived_displacement0)), np.finfo(float).tiny)
            )
            j10_state = np.asarray(original["displacement_alpha_0_m"], dtype=np.float64)
            j10_state_delta = float(
                np.linalg.norm(direct - j10_state)
                / max(float(np.linalg.norm(j10_state)), np.finfo(float).tiny)
            )
            archived_matrix_delta0 = matrix_delta
        level = {
            "alpha": alpha,
            "qf_sri_kernel_global_assembly_status": "COMPLETED",
            "same_matrix_solve_status": "COMPLETED",
            "node_count": int(len(coordinates)),
            "element_count": int(len(connectivity)),
            "positive_gauss_jacobian_count": int(np.count_nonzero(gauss_determinants > 0.0)),
            "free_dof_count": int(len(free)),
            "global_vs_archived_j10_matrix_relative_frobenius": matrix_delta,
            "archived_j7_alpha0_matrix_reproduction_relative": archived_matrix_delta0,
            "archived_j7_alpha0_displacement_reproduction_relative": archived_state_delta,
            "j10_alpha0_displacement_reproduction_relative": j10_state_delta,
            "condition_number_2_raw": condition_raw,
            "condition_number_2_diagonally_scaled": condition_scaled,
            "condition_number_reduction_factor": condition_raw / condition_scaled,
            "qf_sri_global_matrix_numpy_direct": {key: value for key, value in metrics_direct.items() if key not in {"reactions_n", "free_residual_n"}},
            "numpy_diagonally_scaled_same_global_matrix": {key: value for key, value in metrics_scaled.items() if key not in {"reactions_n", "free_residual_n"}},
            "scipy_symmetric_same_global_matrix": {key: value for key, value in metrics_scipy.items() if key not in {"reactions_n", "free_residual_n"}},
            "scaled_vs_numpy_relative_displacement": scaled_rel,
            "scipy_vs_numpy_relative_displacement": scipy_rel,
            "mpmath_80_digit_same_matrix_solve_alpha0": high_precision_solve,
            "maximum_absolute_displacement_m": float(np.max(np.abs(direct))),
            "maximum_displacement_to_local_thickness_ratio": float(np.max(np.abs(direct)) / LOCAL_THICKNESS_M),
        }
        levels.append(level)
        arrays[f"coordinates_alpha_{index}_m"] = coordinates
        arrays[f"global_stiffness_alpha_{index}_n_per_m"] = global_stiffness
        arrays[f"qf_sri_kernel_numpy_direct_displacement_alpha_{index}_m"] = direct
        arrays[f"scaled_displacement_alpha_{index}_m"] = scaled
        arrays[f"scipy_displacement_alpha_{index}_m"] = scipy_direct
        arrays[f"qf_sri_numpy_direct_reactions_alpha_{index}_n"] = metrics_direct["reactions_n"]
        arrays[f"qf_sri_numpy_direct_free_residual_alpha_{index}_n"] = metrics_direct["free_residual_n"]
        if mp_solution is not None:
            arrays[f"mpmath_displacement_alpha_{index}_m"] = mp_solution

    csv_path = output_dir / "hex8_global_reconstruction.csv"
    columns = [
        "alpha", "matrix_relative_delta", "condition_raw", "condition_scaled", "qf_sri_kernel_free_residual_n",
        "force_closure_relative", "moment_closure_relative", "scaled_free_residual_n",
        "scipy_free_residual_n", "scaled_vs_numpy_relative_displacement",
        "scipy_vs_numpy_relative_displacement", "j10_alpha0_state_difference_relative", "mpmath80_free_residual_n",
        "mpmath80_force_closure_relative", "mpmath80_moment_closure_relative", "maximum_displacement_m",
    ]
    with tempfile.NamedTemporaryFile(mode="w", dir=output_dir, prefix=csv_path.name + ".", suffix=".tmp", delete=False, newline="", encoding="utf-8") as stream:
        temporary = Path(stream.name)
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for level in levels:
            writer.writerow(
                {
                    "alpha": level["alpha"],
                    "matrix_relative_delta": level["global_vs_archived_j10_matrix_relative_frobenius"],
                    "condition_raw": level["condition_number_2_raw"],
                    "condition_scaled": level["condition_number_2_diagonally_scaled"],
                    "qf_sri_kernel_free_residual_n": level["qf_sri_global_matrix_numpy_direct"]["free_residual_l2_n"],
                    "force_closure_relative": level["qf_sri_global_matrix_numpy_direct"]["force_closure_relative"],
                    "moment_closure_relative": level["qf_sri_global_matrix_numpy_direct"]["moment_closure_relative"],
                    "scaled_free_residual_n": level["numpy_diagonally_scaled_same_global_matrix"]["free_residual_l2_n"],
                    "scipy_free_residual_n": level["scipy_symmetric_same_global_matrix"]["free_residual_l2_n"],
                    "scaled_vs_numpy_relative_displacement": level["scaled_vs_numpy_relative_displacement"],
                    "scipy_vs_numpy_relative_displacement": level["scipy_vs_numpy_relative_displacement"],
                    "j10_alpha0_state_difference_relative": level["j10_alpha0_displacement_reproduction_relative"],
                    "mpmath80_free_residual_n": (
                        level["mpmath_80_digit_same_matrix_solve_alpha0"]["free_residual_l2_n"]
                        if level["alpha"] == 0.0 else None
                    ),
                    "mpmath80_force_closure_relative": (
                        level["mpmath_80_digit_same_matrix_solve_alpha0"]["force_closure_relative"]
                        if level["alpha"] == 0.0 else None
                    ),
                    "mpmath80_moment_closure_relative": (
                        level["mpmath_80_digit_same_matrix_solve_alpha0"]["moment_closure_relative"]
                        if level["alpha"] == 0.0 else None
                    ),
                    "maximum_displacement_m": level["maximum_absolute_displacement_m"],
                }
            )
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, csv_path)
    npz_path = output_dir / "hex8_global_reconstruction_states.npz"
    buffer = tempfile.SpooledTemporaryFile()
    np.savez_compressed(buffer, **arrays)
    buffer.seek(0)
    encoded_npz = buffer.read()
    npz_path.write_bytes(encoded_npz)
    result_payload: dict[str, Any] = {
        "schema": "qf-j11-hex8-sri-global-reconstruction-v2",
        "classification": "DEVELOPMENT_EXPLORATORY_NOT_QUALIFICATION",
        "execution_status": "COMPLETED_EXPLORATORY",
        "contract_id": contract["contract_id"],
        "contract_sha256": contract_sha,
        "nodeid": NODEID,
        "source_head": run["identity"]["head"],
        "source_fingerprint": run["source_fingerprint"],
        "input_sha256": contract["inputs"],
        "same_system_definition": {
            "geometry": "archived J7 near-degenerate 4x2x2 HEX8-SRI case; alpha only moves the same three interior nodes as J10",
            "element": "research-only QF Hex8SRIElement; HEX8-SRI is not registered as a public/global element type",
            "young_modulus_pa": YOUNG_MODULUS_PA,
            "poisson_ratio": POISSON_RATIO,
            "force_and_fixed_dof_inputs": "archived J7 arrays reused bit-for-bit",
            "global_assembly": "each research-only QF HEX8-SRI local stiffness is scattered into a dense global matrix using the J10 assembly route; no production AnalysisRouter/GlobalAssembler claim is made",
            "reference_basis": "NumPy direct, scaled NumPy, SciPy symmetric direct and alpha=0 mpmath use the exact same QF-kernel global matrix, archived force vector and fixed/free map",
        },
        "results": levels,
        "interpretation": {
            "same_matrix_solvers": "NumPy direct, diagonal scaling, SciPy symmetric solve and mpmath act on identical QF research-kernel global matrices; this isolates algebraic route/precision only for this finite system.",
            "production_route": "None: Hex8SRIElement remains research-only and unregistered; this diagnostic reproduces the J10 local-kernel-to-global-matrix route.",
            "mechanical_reference": "none; a second solve of the same matrix is not an independent continuum or formulation reference",
            "historical_status": "J7 regular and near-degenerate FAIL results remain unchanged; J10 alpha-sweep verdicts remain unchanged",
            "classification": "diagnostic only",
        },
        "artifacts": {
            csv_path.name: _sha256(csv_path),
            npz_path.name: hashlib.sha256(encoded_npz).hexdigest(),
        },
        "environment": _environment(),
    }
    _atomic_json(output_dir / "result.json", result_payload)
    return result_payload
