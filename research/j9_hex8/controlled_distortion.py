"""Constant-domain HEX8-SRI bubble-distortion patch diagnostic for J9."""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import platform
import sys
import tempfile
from importlib import metadata
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
import numpy as np
import threadpoolctl

from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.hex8_sri import Hex8SRIElement
from solveur.materials.solid import SolidMaterial


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "research/j9_hex8/contracts/hex8_constant_domain_distortion_contract.json"
NODEID = "tests/verification/test_j9_hex8_controlled_distortion.py::test_j9_hex8_constant_domain_distortion_sweep"
LENGTH_M, WIDTH_M, HEIGHT_M = 20.0, 1.0, 1.0
NX, NY, NZ = 4, 2, 2
YOUNG_MODULUS_PA, POISSON_RATIO, STRAIN = 1.0e6, 0.495, 1.0e-4
DISTORTION_LEVELS = (0.0, 0.05, 0.10, 0.15)
HEX8_EDGES = (
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes().replace(b"\r\n", b"\n"))


def _atomic_json(path: Path, payload: dict[str, Any]) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    _atomic_bytes(path, encoded)
    return sha256_bytes(encoded)


def _atomic_bytes(path: Path, encoded: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _atomic_npz(path: Path, **arrays: np.ndarray) -> str:
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **arrays)
    encoded = buffer.getvalue()
    _atomic_bytes(path, encoded)
    return sha256_bytes(encoded)


def _threadpool_summary() -> list[dict[str, Any]]:
    keep = ("user_api", "internal_api", "num_threads", "version", "prefix")
    return [{key: item[key] for key in keep if key in item} for item in threadpoolctl.threadpool_info()]


def _structured_hex8_mesh() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    nodes: list[list[float]] = []
    ids: dict[tuple[int, int, int], int] = {}
    for k in range(NZ + 1):
        for j in range(NY + 1):
            for i in range(NX + 1):
                ids[i, j, k] = len(nodes)
                nodes.append([LENGTH_M * i / NX, WIDTH_M * j / NY, HEIGHT_M * k / NZ])
    elements: list[list[int]] = []
    for k in range(NZ):
        for j in range(NY):
            for i in range(NX):
                elements.append([
                    ids[i, j, k], ids[i + 1, j, k], ids[i + 1, j + 1, k], ids[i, j + 1, k],
                    ids[i, j, k + 1], ids[i + 1, j, k + 1], ids[i + 1, j + 1, k + 1], ids[i, j + 1, k + 1],
                ])
    ijk = np.asarray([[i, j, k] for k in range(NZ + 1) for j in range(NY + 1) for i in range(NX + 1)], dtype=int)
    return np.asarray(nodes, dtype=np.float64), np.asarray(elements, dtype=np.int64), ijk


def _distort_mesh(base: np.ndarray, ijk: np.ndarray, amplitude: float) -> np.ndarray:
    coordinates = base.copy()
    for node, (i, j, k) in enumerate(ijk):
        if 0 < i < NX and 0 < j < NY and 0 < k < NZ:
            xi, eta, zeta = i / NX, j / NY, k / NZ
            bubble = 64.0 * xi * (1.0 - xi) * eta * (1.0 - eta) * zeta * (1.0 - zeta)
            coordinates[node, 1] += amplitude * HEIGHT_M * bubble
    return coordinates


def _exact_displacements(coordinates: np.ndarray) -> np.ndarray:
    return np.column_stack((
        STRAIN * coordinates[:, 0],
        -POISSON_RATIO * STRAIN * coordinates[:, 1],
        -POISSON_RATIO * STRAIN * coordinates[:, 2],
    )).ravel()


def _solve_level(base: np.ndarray, elements: np.ndarray, ijk: np.ndarray, amplitude: float) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    coordinates = _distort_mesh(base, ijk, amplitude)
    ndof = 3 * len(coordinates)
    stiffness = np.zeros((ndof, ndof), dtype=np.float64)
    element = Hex8SRIElement(SolidMaterial(E=YOUNG_MODULUS_PA, nu=POISSON_RATIO))
    jacobians: list[float] = []
    for connectivity in elements:
        local_dofs = np.asarray([[3 * int(node) + axis for axis in range(3)] for node in connectivity]).ravel()
        local_coordinates = coordinates[connectivity]
        stiffness[np.ix_(local_dofs, local_dofs)] += element.stiffness(local_coordinates)
        jacobians.extend(float(element.jacobian_determinant(local_coordinates, point)) for point in Hex8Element.integration_points)

    # A node is on the outer boundary if any coordinate index lies at either end.
    fixed_nodes = (
        (ijk[:, 0] == 0) | (ijk[:, 0] == NX)
        | (ijk[:, 1] == 0) | (ijk[:, 1] == NY)
        | (ijk[:, 2] == 0) | (ijk[:, 2] == NZ)
    )
    fixed = np.repeat(fixed_nodes, 3)
    free = ~fixed
    prescribed = _exact_displacements(coordinates)
    displacement = prescribed.copy()
    kff = stiffness[np.ix_(free, free)]
    kfc = stiffness[np.ix_(free, fixed)]
    displacement[free] = np.linalg.solve(kff, -kfc @ prescribed[fixed])
    residual = stiffness @ displacement
    reactions = np.zeros_like(residual)
    reactions[fixed] = residual[fixed]
    jacobian_array = np.asarray(jacobians, dtype=np.float64)
    boundary_coordinates_equal = bool(np.array_equal(coordinates[fixed_nodes], base[fixed_nodes]))
    boundary_error = float(np.max(np.abs(displacement[fixed] - prescribed[fixed])))
    free_residual_norm = float(np.linalg.norm(residual[free]))
    free_residual_scale = max(float(np.linalg.norm(stiffness[np.ix_(free, fixed)] @ prescribed[fixed])), 1.0)
    exact = prescribed
    free_exact_scale = max(float(np.linalg.norm(exact[free])), np.finfo(float).tiny)
    displacement_error = float(np.linalg.norm(displacement[free] - exact[free]))
    volume = LENGTH_M * WIDTH_M * HEIGHT_M
    exact_energy = 0.5 * YOUNG_MODULUS_PA * STRAIN**2 * volume
    energy = 0.5 * float(displacement @ (stiffness @ displacement))
    left_nodes = np.flatnonzero(ijk[:, 0] == 0)
    right_nodes = np.flatnonzero(ijk[:, 0] == NX)
    left_force = math.fsum(float(reactions[3 * int(node)]) for node in left_nodes)
    right_force = math.fsum(float(reactions[3 * int(node)]) for node in right_nodes)
    expected_axial_force = YOUNG_MODULUS_PA * STRAIN * WIDTH_M * HEIGHT_M
    condition = float(np.linalg.cond(kff))
    result = {
        "distortion_amplitude_fraction_of_height": amplitude,
        "maximum_node_shift_m": float(np.max(np.linalg.norm(coordinates - base, axis=1))),
        "same_outer_boundary_coordinates": boundary_coordinates_equal,
        "same_connectivity": True,
        "node_count": int(len(coordinates)),
        "element_count": int(len(elements)),
        "free_dof_count": int(np.count_nonzero(free)),
        "minimum_gauss_jacobian_m3": float(np.min(jacobian_array)),
        "maximum_gauss_jacobian_m3": float(np.max(jacobian_array)),
        "total_gauss_volume_m3": float(np.sum(jacobian_array)),
        "condition_2_free_stiffness_estimate": condition,
        "free_residual_norm_n": free_residual_norm,
        "free_residual_relative_indicator": free_residual_norm / free_residual_scale,
        "free_displacement_error_l2_m": displacement_error,
        "free_displacement_error_relative_to_exact_l2": displacement_error / free_exact_scale,
        "maximum_prescribed_boundary_difference_m": boundary_error,
        "energy_j": energy,
        "energy_reference_j": exact_energy,
        "energy_relative_difference": (energy - exact_energy) / exact_energy,
        "left_end_reaction_x_n": left_force,
        "right_end_reaction_x_n": right_force,
        "continuum_axial_force_reference_n": expected_axial_force,
        "left_reaction_relative_difference": (left_force + expected_axial_force) / expected_axial_force,
        "right_reaction_relative_difference": (right_force - expected_axial_force) / expected_axial_force,
        "finite": bool(np.isfinite(stiffness).all() and np.isfinite(displacement).all() and np.isfinite(residual).all()),
    }
    arrays = {
        "coordinates_m": coordinates,
        "connectivity_hex8": elements,
        "stiffness_n_per_m": stiffness,
        "displacement_m": displacement.reshape((-1, 3)),
        "reference_displacement_m": exact.reshape((-1, 3)),
        "reactions_n": reactions.reshape((-1, 3)),
        "gauss_jacobians_m3": jacobian_array,
    }
    return result, arrays


def _attempt_output_dir() -> tuple[Path, dict[str, Any]]:
    if os.environ.get("QF_DEVELOPMENT_AUTONOMOUS") != "1":
        raise RuntimeError("J9 mechanics outputs require the registered development launcher")
    temp = Path(os.environ["TMP"]).resolve(strict=True)
    attempt_dir = temp.parent
    run_path = attempt_dir / "run.json"
    if not run_path.is_file():
        raise RuntimeError("The development runner attempt record is missing")
    run = json.loads(run_path.read_text(encoding="utf-8"))
    if run.get("state") != "RUNNING" or run.get("worktree_id") != "j9" or run.get("target") != [NODEID]:
        raise RuntimeError("The development runner does not identify this exact J9 HEX8 node")
    output = attempt_dir / "output" / "j9_hex8_constant_domain"
    output.mkdir(parents=True, exist_ok=False)
    return output, run


def run_controlled_distortion() -> dict[str, Any]:
    output_dir, run = _attempt_output_dir()
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    contract_hash = sha256_file(CONTRACT_PATH)
    source_file = ROOT / "src/solveur/elements/solid/hex8_sri.py"
    if canonical_sha256(source_file) != contract["source_identity"]["hex8_sri_canonical_sha256"]:
        raise RuntimeError("The corrected HEX8-SRI source differs from the frozen J9 contract")
    for source in contract["source_identity"]["analysis_files"]:
        if sha256_file(ROOT / source["path"]) != source["sha256"]:
            raise RuntimeError(f"The HEX8 diagnostic source differs from its frozen contract: {source['path']}")
    base, elements, ijk = _structured_hex8_mesh()
    levels: list[dict[str, Any]] = []
    states: list[dict[str, np.ndarray]] = []
    for amplitude in DISTORTION_LEVELS:
        row, state = _solve_level(base, elements, ijk, amplitude)
        levels.append(row)
        states.append(state)
    structural = {
        "all_finite": all(row["finite"] for row in levels),
        "all_gauss_jacobians_positive": all(row["minimum_gauss_jacobian_m3"] > 0.0 for row in levels),
        "outer_boundary_and_topology_unchanged": all(row["same_outer_boundary_coordinates"] and row["same_connectivity"] for row in levels),
        "boundary_values_prescribed_exactly": all(row["maximum_prescribed_boundary_difference_m"] == 0.0 for row in levels),
        "all_levels_have_interior_free_dofs": all(row["free_dof_count"] > 0 for row in levels),
    }
    summary: dict[str, Any] = {
        "schema": "qf-j9-hex8-controlled-distortion-result-v1",
        "classification": "DEVELOPMENT_EXPLORATORY_NOT_QUALIFICATION",
        "execution_status": "COMPLETED_EXPLORATORY",
        "nodeid": NODEID,
        "source_head": run["identity"]["head"],
        "source_fingerprint": run["source_fingerprint"],
        "contract_sha256": contract_hash,
        "source_identity": contract["source_identity"],
        "model": {
            "geometry_m": [LENGTH_M, WIDTH_M, HEIGHT_M],
            "mesh_divisions": [NX, NY, NZ],
            "material": {"young_modulus_pa": YOUNG_MODULUS_PA, "poisson_ratio": POISSON_RATIO},
            "affine_strain": [STRAIN, -POISSON_RATIO * STRAIN, -POISSON_RATIO * STRAIN],
            "boundary_condition": "all outer-boundary nodes prescribed the exact affine uniaxial-strain field; interior nodes free",
            "external_nodal_load": "none; loading is prescribed displacement on the external boundary",
            "continuum_reference": "homogeneous uniaxial stress, sigma_xx=E*epsilon_x, sigma_yy=sigma_zz=0",
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "matplotlib": metadata.version("matplotlib"),
            "threadpools": _threadpool_summary(),
        },
        "levels": levels,
        "structural_checks": structural,
        "interpretation": "Errors and condition estimates are descriptive. The affine patch is a local constant-strain check and does not validate general HEX8-SRI behavior or retroactively alter J7 FAILs.",
    }
    mesh_hash = _atomic_npz(
        output_dir / "hex8_distortion_states.npz",
        base_coordinates_m=base,
        ijk=ijk,
        distortion_amplitudes=np.asarray(DISTORTION_LEVELS),
        coordinates_m=np.asarray([state["coordinates_m"] for state in states]),
        connectivity_hex8=elements,
        stiffness_n_per_m=np.asarray([state["stiffness_n_per_m"] for state in states]),
        displacement_m=np.asarray([state["displacement_m"] for state in states]),
        reference_displacement_m=np.asarray([state["reference_displacement_m"] for state in states]),
        reactions_n=np.asarray([state["reactions_n"] for state in states]),
        gauss_jacobians_m3=np.asarray([state["gauss_jacobians_m3"] for state in states]),
    )
    summary["state_npz"] = {"path": "hex8_distortion_states.npz", "sha256": mesh_hash}
    figure_path = output_dir / "hex8_distortion_study.png"
    _plot(summary, states, figure_path)
    summary["figure"] = {"path": figure_path.name, "sha256": sha256_file(figure_path)}
    summary_hash = _atomic_json(output_dir / "result.json", summary)
    _atomic_json(output_dir / "result.sha256.json", {"sha256": summary_hash})
    return summary


def _plot(summary: dict[str, Any], states: list[dict[str, np.ndarray]], path: Path) -> None:
    figure = plt.figure(figsize=(11, 7))
    mesh_axes = [figure.add_subplot(2, 2, 1, projection="3d"), figure.add_subplot(2, 2, 2, projection="3d")]
    for axis, index in zip(mesh_axes, (0, len(states) - 1), strict=True):
        coordinates = states[index]["coordinates_m"]
        connectivity = states[index]["connectivity_hex8"]
        for conn in connectivity:
            for left, right in HEX8_EDGES:
                axis.plot(*coordinates[[conn[left], conn[right]]].T, color="#356782", linewidth=0.55, alpha=0.65)
        axis.set(xlabel="x [m]", ylabel="y [m]", zlabel="z [m]", title=f"Bulle α={summary['levels'][index]['distortion_amplitude_fraction_of_height']:.2f}")
        axis.set_box_aspect((LENGTH_M, WIDTH_M, HEIGHT_M))
    amplitudes = [row["distortion_amplitude_fraction_of_height"] for row in summary["levels"]]
    errors = [row["free_displacement_error_relative_to_exact_l2"] for row in summary["levels"]]
    conditions = [row["condition_2_free_stiffness_estimate"] for row in summary["levels"]]
    ax_error = figure.add_subplot(2, 2, 3)
    ax_error.plot(amplitudes, errors, "o-")
    ax_error.set(xlabel="Amplitude de distorsion / hauteur", ylabel="Erreur relative L2 [–]", title="Déplacement intérieur vs champ affine")
    ax_error.grid(True, alpha=0.3)
    ax_cond = figure.add_subplot(2, 2, 4)
    ax_cond.plot(amplitudes, conditions, "s-", color="#b24e22")
    ax_cond.set(xlabel="Amplitude de distorsion / hauteur", ylabel="κ₂ estimé [–]", title="Conditionnement de Kff")
    ax_cond.grid(True, alpha=0.3)
    figure.suptitle("HEX8-SRI : géométrie extérieure constante, distorsion intérieure")
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
