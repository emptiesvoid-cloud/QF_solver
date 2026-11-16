"""Controlled interior-mesh distortion replay for the J7 near-degenerate HEX8-SRI case."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import platform
import tempfile
from importlib import metadata
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
import numpy as np
import scipy
from scipy.linalg import solve as symmetric_solve
import threadpoolctl

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
import sys

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from solveur.elements.solid.hex8 import Hex8Element  # noqa: E402
from solveur.elements.solid.hex8_sri import Hex8SRIElement  # noqa: E402
from solveur.materials.solid import SolidMaterial  # noqa: E402

CONTRACT_PATH = ROOT / "research/j10_hex8/contracts/hex8_j7_distortion_corrective_contract.json"
INPUT_STATE_PATH = ROOT / "research/j8_hex8/inputs/near_degenerate_nu0495_nx4_state.npz"
CASE_SPEC_PATH = ROOT / "research/j8_hex8/inputs/j7_hex8_sri_global_cases.json"
HISTORICAL_RESULT_PATH = ROOT / "research/j8_hex8/inputs/near_degenerate_nu0495_nx4_result.json"
PREFLIGHT_RESULT_PATH = ROOT / "research/j10_hex8/geometry_preflight_result.json"
NODEID = "tests/verification/test_j10_hex8_j7_geometry.py::test_j10_hex8_j7_domain_preserving_distortion"
ALPHA_LEVELS = (0.0, 0.05, 0.10, 0.15)
LENGTH_M = 20.0
LOCAL_THICKNESS_M = 0.04
DEFORMATION_DISPLAY_SCALE = 10.0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(bytes((13, 10)), bytes((10,)))).hexdigest()


def _atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _atomic_json(path: Path, payload: dict[str, Any]) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    _atomic_bytes(path, encoded)
    return hashlib.sha256(encoded).hexdigest()


def _atomic_npz(path: Path, **arrays: np.ndarray) -> str:
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **arrays)
    encoded = buffer.getvalue()
    _atomic_bytes(path, encoded)
    return hashlib.sha256(encoded).hexdigest()


def _attempt_output_dir() -> tuple[Path, dict[str, Any]]:
    if os.environ.get("QF_DEVELOPMENT_AUTONOMOUS") != "1":
        raise RuntimeError("J10 HEX8 outputs require the registered development launcher")
    temp = Path(os.environ["TMP"]).resolve(strict=True)
    attempt_dir = temp.parent
    run_path = attempt_dir / "run.json"
    if not run_path.is_file():
        raise RuntimeError("The development runner attempt record is missing")
    run = json.loads(run_path.read_text(encoding="utf-8"))
    if run.get("state") != "RUNNING" or run.get("worktree_id") != "j10" or run.get("target") != [NODEID]:
        raise RuntimeError("The development runner does not identify this exact J10 HEX8 node")
    expected = (ROOT / ".codex/development-runs/worktrees/j10").resolve()
    try:
        attempt_dir.resolve().relative_to(expected)
    except ValueError as exc:
        raise RuntimeError("The J10 HEX8 output directory is outside its registered attempt namespace") from exc
    output = attempt_dir / "output" / "j10_hex8_j7_geometry"
    output.mkdir(parents=True, exist_ok=False)
    return output, run


def _warped_coordinates(coordinates: np.ndarray, interior_nodes: np.ndarray, alpha: float) -> np.ndarray:
    warped = np.asarray(coordinates, dtype=np.float64).copy()
    x = warped[interior_nodes, 0]
    warped[interior_nodes, 2] += alpha * LOCAL_THICKNESS_M * np.sin(np.pi * x / LENGTH_M)
    return warped


def _assemble_stiffness(coordinates: np.ndarray, connectivity: np.ndarray, material: SolidMaterial) -> tuple[np.ndarray, np.ndarray]:
    stiffness = np.zeros((3 * len(coordinates), 3 * len(coordinates)), dtype=np.float64)
    element = Hex8SRIElement(material)
    determinants: list[float] = []
    for row in connectivity:
        element_coordinates = coordinates[row]
        local_dofs = np.asarray([[3 * int(node) + component for component in range(3)] for node in row]).ravel()
        stiffness[np.ix_(local_dofs, local_dofs)] += element.stiffness(element_coordinates)
        determinants.extend(
            float(Hex8Element.jacobian_determinant(element_coordinates, point))
            for point in Hex8Element.integration_points
        )
    return stiffness, np.asarray(determinants, dtype=np.float64)


def _force_moment(coordinates: np.ndarray, vector: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rows = np.asarray(vector, dtype=np.float64).reshape((-1, 3))
    return np.sum(rows, axis=0), np.sum(np.cross(coordinates, rows), axis=0)


def run_diagnostic() -> dict[str, Any]:
    output_dir, run = _attempt_output_dir()
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    contract_sha = _canonical_sha256(CONTRACT_PATH)
    for item in contract["source_identity"]:
        if _canonical_sha256(ROOT / item["path"]) != item["canonical_sha256"]:
            raise RuntimeError(f"J10 HEX8 source differs from frozen identity: {item['path']}")
    if _sha256(INPUT_STATE_PATH) != contract["inputs"]["j7_state_sha256_raw"]:
        raise RuntimeError("Archived J7 numeric state differs from frozen J10 input identity")
    if _canonical_sha256(CASE_SPEC_PATH) != contract["inputs"]["j7_case_spec_sha256_canonical"]:
        raise RuntimeError("Archived J7 case definition differs from frozen J10 input identity")
    if _sha256(HISTORICAL_RESULT_PATH) != contract["inputs"]["historical_result_sha256_raw"]:
        raise RuntimeError("Archived J7 near-degenerate result differs from frozen J10 input identity")
    if _sha256(PREFLIGHT_RESULT_PATH) != contract["inputs"]["geometry_preflight_result_sha256_raw"]:
        raise RuntimeError("J10 geometry-only preflight result differs from frozen FEM contract")
    preflight = json.loads(PREFLIGHT_RESULT_PATH.read_text(encoding="utf-8"))
    if preflight.get("preflight_status") != "PASS_GEOMETRY_ONLY":
        raise RuntimeError("The J10 interior-distortion candidates did not pass the prior geometry-only preflight")

    with np.load(INPUT_STATE_PATH, allow_pickle=False) as archive:
        original = {key: np.asarray(archive[key]) for key in archive.files}
    case_spec = json.loads(CASE_SPEC_PATH.read_text(encoding="utf-8"))
    case = next(item for item in case_spec["cases"] if item["case_id"] == "J7-HEX8-SRI-NEAR-DEGENERATE-NU0495-NX4")
    material = SolidMaterial(E=float(case_spec["material"]["young_modulus_pa"]), nu=float(case["poisson_ratio"]))
    coordinates = np.asarray(original["coordinates_m"], dtype=np.float64)
    connectivity = np.asarray(original["connectivity"], dtype=np.int64)
    force = np.asarray(original["force_n"], dtype=np.float64)
    fixed_mask = np.asarray(original["fixed_dof_mask"], dtype=bool)
    if coordinates.shape != (45, 3) or connectivity.shape != (16, 8) or force.shape != (135,) or fixed_mask.shape != (135,):
        raise RuntimeError("Archived J7 mesh or vectors differ from the registered 4x2x2 model")

    interior = (
        (coordinates[:, 0] > 0.0)
        & (coordinates[:, 0] < LENGTH_M)
        & np.isclose(coordinates[:, 1], 0.5, rtol=0.0, atol=1.0e-12)
        & np.isclose(coordinates[:, 2], 0.02, rtol=0.0, atol=1.0e-12)
    )
    interior_nodes = np.flatnonzero(interior)
    if interior_nodes.size != 3 or interior_nodes.tolist() != preflight["mesh"]["interior_node_ids"]:
        raise RuntimeError("J10 interior logical-node set differs from the geometry-preflight contract")
    fixed = np.flatnonzero(fixed_mask)
    free = np.flatnonzero(~fixed_mask)
    if len(fixed) != 27 or len(free) != 108:
        raise RuntimeError("J10 fixed/free DOF map differs from the archived J7 case")
    external_force, external_moment = _force_moment(coordinates, force)
    expected_force = np.asarray((0.0, 0.0, -1.0), dtype=np.float64)
    if not np.allclose(external_force, expected_force, rtol=0.0, atol=1.0e-14):
        raise RuntimeError("Archived J7 force resultant differs from the frozen -1 N vertical load")

    boundary_nodes = np.flatnonzero(~interior)
    boundary_coordinates = coordinates[boundary_nodes].copy()
    original_stiffness = np.asarray(original["stiffness_n_per_m"], dtype=np.float64)
    archived_displacement = np.asarray(original["displacement_m"], dtype=np.float64)
    historical_result = json.loads(HISTORICAL_RESULT_PATH.read_text(encoding="utf-8"))
    historical_status = historical_result["scientific_criteria_status"]

    rows: list[dict[str, Any]] = []
    arrays: dict[str, np.ndarray] = {
        "original_coordinates_m": coordinates,
        "connectivity_hex8": connectivity,
        "force_n": force,
        "fixed_dof_mask": fixed_mask,
        "archived_j7_stiffness_n_per_m": original_stiffness,
        "archived_j7_displacement_m": archived_displacement,
    }
    for index, alpha in enumerate(ALPHA_LEVELS):
        warped = _warped_coordinates(coordinates, interior_nodes, alpha)
        if not np.array_equal(warped[boundary_nodes], boundary_coordinates):
            raise RuntimeError("The transformation changed at least one exterior node coordinate")
        stiffness, determinants = _assemble_stiffness(warped, connectivity, material)
        if not np.isfinite(determinants).all() or np.min(determinants) <= 0.0:
            raise RuntimeError(f"Alpha={alpha:g} has a non-positive or non-finite Gauss Jacobian")
        reduced = stiffness[np.ix_(free, free)]
        reduced_force = force[free]
        displacement = np.zeros_like(force)
        displacement[free] = np.linalg.solve(reduced, reduced_force)
        independent_displacement = np.zeros_like(force)
        independent_displacement[free] = symmetric_solve(reduced, reduced_force, assume_a="sym", check_finite=False)
        raw_residual = stiffness @ displacement - force
        reactions = np.zeros_like(force)
        reactions[fixed] = raw_residual[fixed]
        equilibrium_residual = raw_residual - reactions
        reaction_force, reaction_moment = _force_moment(warped, reactions)
        force_closure = external_force + reaction_force
        moment_closure = external_moment + reaction_moment
        strain_energy = float(0.5 * displacement @ stiffness @ displacement)
        external_work = float(0.5 * displacement @ force)
        energy_relative = abs(strain_energy - external_work) / max(abs(strain_energy), abs(external_work), np.finfo(float).tiny)
        historical_energy_metric = abs(strain_energy - external_work) / max(abs(external_work), 1.0)
        free_residual = raw_residual[free]
        residual_scale = np.linalg.norm(stiffness, ord="fro") * np.linalg.norm(displacement) + np.linalg.norm(force)
        backward_error = float(np.linalg.norm(free_residual) / max(float(residual_scale), np.finfo(float).tiny))
        force_scale = max(float(np.linalg.norm(force)), 1.0)
        moment_scale = max(float(np.linalg.norm(force)) * LENGTH_M, 1.0)
        symmetry = float(np.linalg.norm(stiffness - stiffness.T, ord="fro") / max(np.linalg.norm(stiffness, ord="fro"), 1.0))
        solver_delta = float(np.linalg.norm(independent_displacement - displacement) / max(np.linalg.norm(displacement), np.finfo(float).tiny))
        archived_matrix_delta = float(np.linalg.norm(stiffness - original_stiffness, ord="fro") / max(np.linalg.norm(original_stiffness, ord="fro"), np.finfo(float).tiny))
        archived_solution_delta = float(np.linalg.norm(displacement - archived_displacement) / max(np.linalg.norm(archived_displacement), np.finfo(float).tiny))
        row = {
            "alpha": alpha,
            "maximum_interior_shift_m": float(np.max(np.abs(warped[interior_nodes, 2] - coordinates[interior_nodes, 2]))),
            "exterior_node_coordinates_unchanged": True,
            "minimum_gauss_jacobian_m3": float(np.min(determinants)),
            "maximum_gauss_jacobian_m3": float(np.max(determinants)),
            "integrated_volume_m3": float(np.sum(determinants)),
            "condition_number_2_estimate": float(np.linalg.cond(reduced)),
            "matrix_symmetry_relative_frobenius": symmetry,
            "free_residual_l2_n": float(np.linalg.norm(free_residual)),
            "free_residual_relative_to_force": float(np.linalg.norm(free_residual) / force_scale),
            "free_residual_backward_error": backward_error,
            "force_resultant_n": external_force.tolist(),
            "reaction_resultant_n": reaction_force.tolist(),
            "force_closure_residual_n": force_closure.tolist(),
            "force_closure_relative": float(np.linalg.norm(force_closure) / force_scale),
            "external_moment_about_origin_nm": external_moment.tolist(),
            "reaction_moment_about_origin_nm": reaction_moment.tolist(),
            "moment_closure_residual_nm": moment_closure.tolist(),
            "moment_closure_relative_to_force_length": float(np.linalg.norm(moment_closure) / moment_scale),
            "strain_energy_j": strain_energy,
            "external_work_j": external_work,
            "energy_identity_relative_symmetric_scale": energy_relative,
            "historical_energy_metric_relative_to_max_work_1j": historical_energy_metric,
            "maximum_displacement_m": float(np.max(np.abs(displacement))),
            "tip_face_center_uz_m": float(displacement[3 * int(np.flatnonzero(np.isclose(warped[:, 0], LENGTH_M) & np.isclose(warped[:, 1], 0.5) & np.isclose(warped[:, 2], 0.02))[0]) + 2]),
            "second_symmetric_solver_displacement_relative_difference": solver_delta,
            "relative_matrix_difference_from_archived_j7_alpha0": archived_matrix_delta,
            "relative_displacement_difference_from_archived_j7_alpha0": archived_solution_delta,
        }
        if alpha == 0.0 and (archived_matrix_delta > 1.0e-12 or archived_solution_delta > 1.0e-10):
            raise RuntimeError("Alpha=0 does not reproduce the archived J7 matrix/solution closely enough")
        rows.append(row)
        arrays[f"coordinates_alpha_{index}"] = warped
        arrays[f"gauss_jacobians_alpha_{index}_m3"] = determinants
        arrays[f"stiffness_alpha_{index}_n_per_m"] = stiffness
        arrays[f"displacement_alpha_{index}_m"] = displacement
        arrays[f"second_solver_displacement_alpha_{index}_m"] = independent_displacement
        arrays[f"reactions_alpha_{index}_n"] = reactions
        arrays[f"free_residual_alpha_{index}_n"] = free_residual

    result_payload: dict[str, Any] = {
        "schema": "qf-j10-hex8-j7-distortion-result-v1",
        "classification": "DEVELOPMENT_EXPLORATORY_NOT_QUALIFICATION",
        "execution_status": "COMPLETED_EXPLORATORY",
        "contract_id": contract["contract_id"],
        "attempt_id": contract["execution"]["attempt_id"],
        "development_attempt_number": run["attempt"],
        "historical_j7_status": historical_status,
        "nodeid": NODEID,
        "source_head": run["identity"]["head"],
        "source_fingerprint": run["source_fingerprint"],
        "contract_sha256": contract_sha,
        "input_sha256": {
            "j7_state_npz": _sha256(INPUT_STATE_PATH),
            "j7_case_spec_canonical": _canonical_sha256(CASE_SPEC_PATH),
            "j7_result": _sha256(HISTORICAL_RESULT_PATH),
            "geometry_preflight_result": _sha256(PREFLIGHT_RESULT_PATH),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "matplotlib": metadata.version("matplotlib"),
            "threadpools": [
                {key: item.get(key) for key in ("user_api", "internal_api", "version", "num_threads")}
                for item in threadpoolctl.threadpool_info()
            ],
        },
        "model": {
            "element": "HEX8-SRI; current corrected element source matches J7 canonical source e014652e…",
            "geometry": "archived J7 near-degenerate 4×2×2 mesh; x=20 m, y nominal 1 m, transformed z extent [-0.003, 0.043] m; exterior node coordinates held fixed",
            "material": {"young_modulus_pa": float(case_spec["material"]["young_modulus_pa"]), "poisson_ratio": float(case["poisson_ratio"])},
            "loads": "archived J7 nodal force vector reused bit-for-bit; total (0,0,-1) N on x=L face nodes",
            "supports": "archived J7 fixed-DOF mask reused bit-for-bit; all translations fixed on x=0 face",
            "mesh_distortion": "z shift of only the three interior nodes: delta_z = alpha * 0.04 m * sin(pi*x/20 m)",
            "thickness_scaling_note": "0.04 m is the vertical top-to-bottom difference at fixed x,y; 0.046 m is the overall z bounding-box extent due to boundary skew.",
        },
        "reference": {
            "type": "archived J7 alpha=0 state plus linear-system equilibrium and a second symmetric direct solver",
            "limits": "The alpha=0 replay is not an independent continuum oracle. The second solver uses the same assembled K and force vector. No external or continuum displacement reference is available for the J7 near-degenerate cantilever.",
            "J7_historical_failures": "preserved unchanged; new criteria below are indicators only",
        },
        "levels": rows,
        "criteria": {
            "formal_acceptance_thresholds": "none; residuals, force/moment closure, energy, conditioning and displacement differences are descriptive",
            "completion_invariants": "positive finite Gauss Jacobians; unchanged exterior coordinates and archived load/support vectors; finite matrices/solutions; alpha=0 matrix and state reproducibility",
        },
        "interpretation": "The one-factor sweep changes only interior mesh coordinates on the same near-degenerate J7 body. It measures sensitivity for this discretized linear model; it cannot attribute the historical J7 global closure FAIL to geometry alone or establish physical accuracy.",
        "limits": [
            "No continuum/external displacement reference exists for this exact J7 model.",
            "Linear small-strain response is a diagnostic; the archived displacement is large relative to the 0.04 m local thickness scale.",
            "The distortion levels test this 4×2×2 mesh only and do not generalize to all HEX8-SRI meshes.",
        ],
    }
    result_payload["state_npz"] = {
        "path": "hex8_j7_distortion_states.npz",
        "sha256": _atomic_npz(output_dir / "hex8_j7_distortion_states.npz", **arrays),
    }
    csv_path = output_dir / "hex8_j7_distortion_metrics.csv"
    with tempfile.NamedTemporaryFile(mode="w", dir=output_dir, prefix=csv_path.name + ".", suffix=".tmp", delete=False, newline="", encoding="utf-8") as stream:
        temporary_csv = Path(stream.name)
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary_csv, csv_path)
    result_payload["metrics_csv"] = {"path": csv_path.name, "sha256": _sha256(csv_path)}
    figures = _write_figures(output_dir, coordinates, connectivity, interior_nodes, rows, arrays)
    result_payload["figures"] = figures
    result_sha = _atomic_json(output_dir / "result.json", result_payload)
    _atomic_json(output_dir / "result.sha256.json", {"sha256": result_sha})
    return result_payload


def _write_figures(
    output_dir: Path,
    coordinates: np.ndarray,
    connectivity: np.ndarray,
    interior_nodes: np.ndarray,
    rows: list[dict[str, Any]],
    arrays: dict[str, np.ndarray],
) -> dict[str, str]:
    mesh_path = output_dir / "site_hex8_j7_distortion.png"
    figure = plt.figure(figsize=(11, 7))
    for index, row in enumerate(rows):
        axis = figure.add_subplot(2, 2, index + 1, projection="3d")
        xyz = np.asarray(arrays[f"coordinates_alpha_{index}"])
        displacement = np.asarray(arrays[f"displacement_alpha_{index}_m"]).reshape((-1, 3))
        shown = xyz + DEFORMATION_DISPLAY_SCALE * displacement
        _draw_hex_mesh(axis, shown, connectivity)
        axis.scatter(*shown[interior_nodes].T, color="#ab483c", s=12)
        axis.set_box_aspect((20.0, 1.0, 0.2))
        axis.set_title(f"α={row['alpha']:.2f}; déformée ×{DEFORMATION_DISPLAY_SCALE:g}; 16 HEX8")
        axis.set(xlabel="x [m]", ylabel="y [m]", zlabel="z [m]")
    figure.suptitle("HEX8-SRI J7 : distorsion des trois nœuds intérieurs, enveloppe extérieure fixe")
    figure.tight_layout()
    figure.savefig(mesh_path, dpi=160)
    plt.close(figure)

    metrics_path = output_dir / "hex8_j7_distortion_indicators.png"
    figure, axes = plt.subplots(1, 2, figsize=(10, 4))
    alphas = [row["alpha"] for row in rows]
    axes[0].plot(alphas, [row["condition_number_2_estimate"] for row in rows], marker="o")
    axes[0].set(xlabel="Amplitude relative α [–]", ylabel="Estimation κ₂(Kff) [–]", title="Conditionnement")
    axes[1].semilogy(alphas, [max(row["free_residual_relative_to_force"], np.finfo(float).tiny) for row in rows], marker="o", label="résidu libre / ||F||")
    axes[1].semilogy(alphas, [max(row["force_closure_relative"], np.finfo(float).tiny) for row in rows], marker="s", label="fermeture force / ||F||")
    axes[1].set(xlabel="Amplitude relative α [–]", ylabel="Indicateur relatif [–]", title="Équilibre linéaire")
    axes[1].legend(fontsize=8)
    for axis in axes:
        axis.grid(True, alpha=0.25)
    figure.tight_layout()
    figure.savefig(metrics_path, dpi=160)
    plt.close(figure)
    return {path.name: _sha256(path) for path in (mesh_path, metrics_path)}


def _draw_hex_mesh(axis: Any, coordinates: np.ndarray, connectivity: np.ndarray) -> None:
    local_edges = ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7))
    for row in connectivity:
        for left, right in local_edges:
            axis.plot(*coordinates[[int(row[left]), int(row[right])]].T, color="#54756b", linewidth=0.7, alpha=0.65)
