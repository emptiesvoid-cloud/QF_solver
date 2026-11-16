"""One controlled geometry-map HEX8-SRI contrast against the frozen J7 state."""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
import threadpoolctl

from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.hex8_sri import Hex8SRIElement
from solveur.materials.solid import SolidMaterial

from research.j8_hex8.diagnostics import (
    CONTRACT_PATH,
    INPUT_ROOT,
    _attempt_output_dir,
    _git_text,
    _write_json_atomic,
    backward_error_inf,
    canonical_sha256,
    energy_diagnostics,
    global_balances,
    partitioned_residuals,
    sha256,
)


ROOT = Path(__file__).resolve().parents[2]
GEOMETRY_CONTRACT_PATH = ROOT / "research/j8_hex8/contracts/j8_hex8_geometry_contrast_contract.json"
EXECUTION_MANIFEST_PATH = ROOT / "research/j8_hex8/contracts/execution_manifest.json"
NODEID = "tests/verification/test_j8_hex8_conditioning.py::test_j8_geometry_only_regular_nu0495_nx4_contrast"
RESULT_FILE = INPUT_ROOT / "near_degenerate_nu0495_nx4_result.json"
STATE_FILE = INPUT_ROOT / "near_degenerate_nu0495_nx4_state.npz"
CASE_INPUT_FILE = INPUT_ROOT / "j7_hex8_sri_global_cases.json"


def _assert_frozen_inputs(nodeid: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    contract = json.loads(GEOMETRY_CONTRACT_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(EXECUTION_MANIFEST_PATH.read_text(encoding="utf-8"))
    if nodeid != NODEID or manifest["geometry_case"]["nodeid"] != nodeid:
        raise RuntimeError("geometry contrast nodeid differs from its frozen registration")
    if canonical_sha256(GEOMETRY_CONTRACT_PATH) != manifest["geometry_contract_canonical_lf_sha256"]:
        raise RuntimeError("geometry contrast contract differs from the frozen execution manifest")
    if canonical_sha256(CONTRACT_PATH) != manifest["contract_canonical_lf_sha256"]:
        raise RuntimeError("J8 matrix-analysis contract differs from the frozen execution manifest")
    registration = ROOT / "research/j8_hex8/execution_scope_registration.json"
    if canonical_sha256(registration) != manifest["scope_registration_canonical_lf_sha256"]:
        raise RuntimeError("J8 scope registration differs from the frozen execution manifest")
    source_head = manifest["analysis_source_commit"]
    _git_text("merge-base", "--is-ancestor", source_head, "HEAD")
    changed = _git_text("diff", "--name-only", f"{source_head}..HEAD").splitlines()
    if changed != ["research/j8_hex8/contracts/execution_manifest.json"]:
        raise RuntimeError("execution HEAD must differ from the frozen source only by its manifest")
    if _git_text("rev-parse", f"{source_head}:src/solveur") != manifest["solver_source_tree_sha1"]:
        raise RuntimeError("solver source tree differs from the frozen J7 source")
    for entry in manifest["analysis_source_files"]:
        path = (ROOT / entry["path"]).resolve()
        path.relative_to(ROOT.resolve())
        if canonical_sha256(path) != entry["canonical_lf_sha256"]:
            raise RuntimeError(f"frozen J8 analysis source changed: {entry['path']}")
    for entry in manifest["input_files"]:
        path = (ROOT / entry["path"]).resolve()
        path.relative_to(ROOT.resolve())
        if sha256(path) != entry["sha256"]:
            raise RuntimeError(f"frozen J7 source input changed: {entry['path']}")
    if canonical_sha256(ROOT / "src/solveur/elements/solid/hex8_sri.py") != contract["baseline"]["hex8_sri_canonical_sha256"]:
        raise RuntimeError("corrected HEX8-SRI element source SHA differs from the geometry contract")
    for package, expected in manifest["dependency_versions"].items():
        from importlib import metadata

        if metadata.version(package) != expected:
            raise RuntimeError(f"frozen J8 dependency version differs: {package}")
    for variable, expected in manifest["thread_environment"].items():
        if os.environ.get(variable) != expected:
            raise RuntimeError(f"J8 numerical thread limit differs: {variable}")
    if not threadpoolctl.threadpool_info() or any(pool.get("num_threads") != 1 for pool in threadpoolctl.threadpool_info()):
        raise RuntimeError("J8 numerical thread pools are not all limited to one thread")
    for path, key in ((RESULT_FILE, "j7_comparison_result_sha256"), (STATE_FILE, "j7_comparison_state_sha256")):
        if sha256(path) != contract["baseline"][key]:
            raise RuntimeError(f"archived J7 comparison input changed: {path.name}")
    if sha256(CASE_INPUT_FILE) != contract["input"]["case_input_sha256"]:
        raise RuntimeError("J7 global case input differs from the geometry contract")
    return contract, manifest, json.loads(CASE_INPUT_FILE.read_text(encoding="utf-8"))


def _mesh(nx: int, length: float, width: float, height: float, ny: int, nz: int) -> tuple[np.ndarray, np.ndarray]:
    nodes: list[list[float]] = []
    ids: dict[tuple[int, int, int], int] = {}
    for k in range(nz + 1):
        for j in range(ny + 1):
            for i in range(nx + 1):
                ids[i, j, k] = len(nodes)
                nodes.append([length * i / nx, width * j / ny, height * k / nz])
    elements: list[list[int]] = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                elements.append([
                    ids[i, j, k], ids[i + 1, j, k], ids[i + 1, j + 1, k], ids[i, j + 1, k],
                    ids[i, j, k + 1], ids[i + 1, j, k + 1], ids[i + 1, j + 1, k + 1], ids[i, j + 1, k + 1],
                ])
    return np.asarray(nodes, dtype=np.float64), np.asarray(elements, dtype=np.int64)


def _atomic_npz(path: Path, values: dict[str, np.ndarray]) -> str:
    import io

    buffer = io.BytesIO()
    np.savez_compressed(buffer, **values)
    encoded = buffer.getvalue()
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
        temp_path = Path(stream.name)
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp_path, path)
    return hashlib.sha256(encoded).hexdigest()


def _update_checkpoint(path: Path, payload: dict[str, Any], stage: str, **fields: Any) -> None:
    payload.update(fields)
    payload["stage"] = stage
    payload["updated_unix_seconds"] = time.time()
    _write_json_atomic(path, payload)


def run_geometry_contrast(nodeid: str) -> dict[str, Any]:
    contract, manifest, case_input = _assert_frozen_inputs(nodeid)
    model_input = next(
        item for item in case_input["cases"]
        if item["case_id"] == "J7-HEX8-SRI-NEAR-DEGENERATE-NU0495-NX4"
    )
    model = case_input["geometry"]
    material = case_input["material"]
    loading = case_input["loading"]
    if float(model_input["poisson_ratio"]) != 0.495 or int(model_input["nx"]) != 4:
        raise RuntimeError("J7 archived comparison model differs from the declared controlled pair")

    output_dir = _attempt_output_dir() / "j8_geometry_only_regular_nu0495_nx4"
    output_dir.mkdir(exist_ok=False)
    checkpoint_path = output_dir / "checkpoint.json"
    result_path = output_dir / "geometry_contrast_result.json"
    state_path = output_dir / "geometry_contrast_state.npz"
    matrix_state_path = output_dir / "matrix_assembled_state.npz"
    checkpoint: dict[str, Any] = {
        "schema": "qf-j8-hex8-geometry-checkpoint-v1",
        "classification": "DEVELOPMENT_DIAGNOSTIC_NOT_QUALIFICATION",
        "nodeid": nodeid,
        "source_head": _git_text("rev-parse", "HEAD"),
        "analysis_source_commit": manifest["analysis_source_commit"],
        "contract_canonical_lf_sha256": manifest["geometry_contract_canonical_lf_sha256"],
        "j7_comparison_result_sha256": sha256(RESULT_FILE),
        "j7_comparison_state_sha256": sha256(STATE_FILE),
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "threadpool_info": threadpoolctl.threadpool_info(),
            "thread_environment": {key: os.environ.get(key) for key in manifest["thread_environment"]},
        },
        "case": contract["controlled_contrast"],
        "stage": "VALIDATED_INPUTS",
    }
    _write_json_atomic(checkpoint_path, checkpoint)
    nx, ny, nz = 4, int(model["ny"]), int(model["nz"])
    coordinates, connectivity = _mesh(
        nx,
        float(model["length_m"]),
        float(model["width_m"]),
        float(model["height_m"]),
        ny,
        nz,
    )
    _update_checkpoint(
        checkpoint_path,
        checkpoint,
        "MESH_GENERATED",
        node_count=int(len(coordinates)),
        element_count=int(len(connectivity)),
        coordinate_min_m=coordinates.min(axis=0).tolist(),
        coordinate_max_m=coordinates.max(axis=0).tolist(),
    )

    ndof = 3 * len(coordinates)
    if len(coordinates) != 45 or len(connectivity) != 16:
        raise RuntimeError("generated control mesh differs from the declared 45-node/16-element case")
    stiffness = np.zeros((ndof, ndof), dtype=np.float64)
    element = Hex8SRIElement(
        SolidMaterial(E=float(material["young_modulus_pa"]), nu=float(model_input["poisson_ratio"]))
    )
    jacobians: list[float] = []
    for conn in connectivity:
        local_dofs = np.asarray([[3 * n, 3 * n + 1, 3 * n + 2] for n in conn], dtype=np.int64).ravel()
        element_coordinates = coordinates[conn]
        stiffness[np.ix_(local_dofs, local_dofs)] += element.stiffness(element_coordinates)
        jacobians.extend(
            float(element.jacobian_determinant(element_coordinates, point))
            for point in Hex8Element.integration_points
        )
    jacobian_array = np.asarray(jacobians, dtype=np.float64)
    matrix_finite = bool(np.isfinite(stiffness).all())
    jacobians_finite = bool(np.isfinite(jacobian_array).all())
    matrix_symmetry_relative = (
        float(np.linalg.norm(stiffness - stiffness.T) / max(float(np.linalg.norm(stiffness)), 1.0))
        if matrix_finite else None
    )
    _update_checkpoint(
        checkpoint_path,
        checkpoint,
        "MATRIX_ASSEMBLED",
        matrix_shape=list(stiffness.shape),
        stiffness_finite=matrix_finite,
        stiffness_symmetry_relative=matrix_symmetry_relative,
        gauss_jacobians_finite=jacobians_finite,
        gauss_jacobian_min_m3=float(np.min(jacobian_array)) if jacobians_finite else None,
        gauss_jacobian_max_m3=float(np.max(jacobian_array)) if jacobians_finite else None,
    )

    force = np.zeros(ndof, dtype=np.float64)
    end_nodes = np.flatnonzero(np.isclose(coordinates[:, 0], float(model["length_m"])))
    if len(end_nodes) != int(loading["end_face_node_count"]):
        raise RuntimeError("control-model end-face node count differs from the J7 load definition")
    force[3 * end_nodes + 2] = float(loading["total_force_n"][2]) / int(loading["end_face_node_count"])
    fixed_nodes = np.flatnonzero(np.isclose(coordinates[:, 0], 0.0))
    if len(fixed_nodes) != int(model_input["expected_fixed_nodes"]):
        raise RuntimeError("control-model fixed node count differs from the archived J7 model")
    fixed_mask = np.zeros(ndof, dtype=bool)
    fixed_mask[(3 * fixed_nodes[:, None] + np.arange(3)).ravel()] = True
    free = ~fixed_mask
    matrix_state_hash = _atomic_npz(
        matrix_state_path,
        {
            "coordinates_m": coordinates,
            "connectivity": connectivity,
            "stiffness_n_per_m": stiffness,
            "force_n": force,
            "fixed_dof_mask": fixed_mask,
            "gauss_jacobians_m3": jacobian_array,
        },
    )
    _update_checkpoint(
        checkpoint_path,
        checkpoint,
        "MATRIX_AND_LOAD_ASSEMBLED",
        matrix_state_path=matrix_state_path.name,
        matrix_state_sha256=matrix_state_hash,
        force_nodes=int(len(end_nodes)),
        fixed_nodes=int(len(fixed_nodes)),
    )
    if not matrix_finite or not jacobians_finite:
        _update_checkpoint(
            checkpoint_path,
            checkpoint,
            "ABORTED_NONFINITE_ASSEMBLY",
            stiffness_finite=matrix_finite,
            gauss_jacobians_finite=jacobians_finite,
        )
        raise RuntimeError("geometry contrast produced nonfinite stiffness or Gauss Jacobians")
    eigenvalues = np.linalg.eigvalsh(stiffness[np.ix_(free, free)])
    matrix_positive = bool(eigenvalues[0] > 0.0)
    if not matrix_positive:
        _update_checkpoint(
            checkpoint_path,
            checkpoint,
            "ABORTED_FREE_MATRIX_NOT_POSITIVE_DEFINITE",
            lambda_min_n_per_m=float(eigenvalues[0]),
        )
        raise RuntimeError("regular geometry free matrix is not positive definite")
    displacement = np.zeros(ndof, dtype=np.float64)
    displacement[free] = np.linalg.solve(stiffness[np.ix_(free, free)], force[free])
    partition = partitioned_residuals(stiffness, force, displacement, fixed_mask)
    balances = global_balances(coordinates, force, partition["reactions"], float(model["length_m"]))
    energy = energy_diagnostics(
        stiffness,
        force,
        displacement,
        np.asarray([math.fsum(float(value) * float(component) for value, component in zip(row, displacement)) for row in stiffness]),
    )
    backward = backward_error_inf(partition["free_matrix"], partition["free_displacement"], partition["effective_free_rhs"])
    expected_load = np.asarray(loading["total_force_n"], dtype=np.float64)
    applied_load = force.reshape((-1, 3)).sum(axis=0)
    applied_load_relative = float(
        np.linalg.norm(applied_load - expected_load) / max(float(np.linalg.norm(expected_load)), 1.0)
    )

    with np.load(STATE_FILE, allow_pickle=False) as data:
        archived_near = {key: data[key] for key in data.files}
    archived_near_displacement = np.asarray(archived_near["displacement_m"], dtype=np.float64)
    displacement_difference = displacement - archived_near_displacement
    near_eigenvalues = np.linalg.eigvalsh(
        archived_near["stiffness_n_per_m"][np.ix_(~archived_near["fixed_dof_mask"], ~archived_near["fixed_dof_mask"])]
    )
    near_bounds = {
        "coordinate_min_m": archived_near["coordinates_m"].min(axis=0).tolist(),
        "coordinate_max_m": archived_near["coordinates_m"].max(axis=0).tolist(),
        "z_extent_m": float(np.ptp(archived_near["coordinates_m"][:, 2])),
        "jacobian_min_m3": float(np.min(archived_near["gauss_jacobians_m3"])),
        "jacobian_max_m3": float(np.max(archived_near["gauss_jacobians_m3"])),
        "condition_2_estimate": float(near_eigenvalues[-1] / near_eigenvalues[0]) if near_eigenvalues[0] > 0.0 else None,
    }
    symmetry = float(np.linalg.norm(stiffness - stiffness.T) / max(float(np.linalg.norm(stiffness)), 1.0))
    finite = all(
        np.isfinite(array).all()
        for array in (stiffness, force, displacement, np.asarray(jacobians, dtype=np.float64))
    )
    result = {
        "schema": "qf-j8-hex8-geometry-contrast-result-v1",
        "classification": "DEVELOPMENT_DIAGNOSTIC_NOT_QUALIFICATION",
        "execution_status": "COMPLETED_EXPLORATORY",
        "scientific_status": "NO_ACCEPTANCE_THRESHOLD_FOR_RESIDUAL_ENERGY_OR_MOMENT",
        "source": {
            "repository_head": _git_text("rev-parse", "HEAD"),
            "analysis_source_commit": manifest["analysis_source_commit"],
            "solver_source_tree_sha1": manifest["solver_source_tree_sha1"],
            "geometry_contract_canonical_lf_sha256": manifest["geometry_contract_canonical_lf_sha256"],
            "case_input_sha256": sha256(CASE_INPUT_FILE),
            "j7_near_result_sha256": sha256(RESULT_FILE),
            "j7_near_state_sha256": sha256(STATE_FILE),
        },
        "comparison_scope": {
            "only_declared_coordinate_map_changes": True,
            "same_nu_mesh_counts_material_load_distribution_and_fixed_dofs": True,
            "new_regular_geometry": {
                "coordinate_min_m": coordinates.min(axis=0).tolist(),
                "coordinate_max_m": coordinates.max(axis=0).tolist(),
                "z_extent_m": float(np.ptp(coordinates[:, 2])),
            },
            "archived_near_degenerate_geometry": near_bounds,
        },
        "regular_case": {
            "case_id": "J8-HEX8-SRI-GEOMETRY-ONLY-CONTROL-NU0495-NX4",
            "model": {
                "young_modulus_pa": float(material["young_modulus_pa"]),
                "poisson_ratio": float(model_input["poisson_ratio"]),
                "length_m": float(model["length_m"]),
                "width_input_m": float(model["width_m"]),
                "height_input_m": float(model["height_m"]),
                "nx": nx,
                "ny": ny,
                "nz": nz,
                "nodes": int(len(coordinates)),
                "elements": int(len(connectivity)),
                "fixed_dofs": int(np.count_nonzero(fixed_mask)),
                "loaded_end_nodes": int(len(end_nodes)),
                "load_total_n": applied_load.tolist(),
            },
            "stiffness_symmetry_relative": symmetry,
            "free_matrix_positive_definite": matrix_positive,
            "lambda_min_n_per_m": float(eigenvalues[0]),
            "lambda_max_n_per_m": float(eigenvalues[-1]),
            "condition_2_estimate": float(eigenvalues[-1] / eigenvalues[0]),
            "gauss_jacobian_min_m3": float(min(jacobians)),
            "gauss_jacobian_max_m3": float(max(jacobians)),
            "applied_load_resultant_relative": applied_load_relative,
            "free_residual_norm_n": float(np.linalg.norm(partition["equilibrium_residual"][free])),
            "free_residual_relative_to_force_norm": float(np.linalg.norm(partition["equilibrium_residual"][free]) / max(np.linalg.norm(force), 1.0)),
            "backward_error": backward,
            "force_balance": balances,
            "energy": energy,
            "max_displacement_m": float(np.max(np.abs(displacement))),
            "index_corresponding_displacement_difference_norm_m": float(np.linalg.norm(displacement_difference)),
            "index_corresponding_displacement_difference_relative": float(
                np.linalg.norm(displacement_difference)
                / max(float(np.linalg.norm(archived_near_displacement)), np.finfo(float).tiny)
            ),
            "displacement_difference_interpretation": "descriptive only; corresponding node indices have different physical coordinates",
            "finite": bool(finite),
        },
        "geometry_conditioning_comparison": {
            "regular_condition_2_estimate": float(eigenvalues[-1] / eigenvalues[0]),
            "near_degenerate_condition_2_estimate": near_bounds["condition_2_estimate"],
            "condition_ratio_near_over_regular": (
                float(near_bounds["condition_2_estimate"] / (eigenvalues[-1] / eigenvalues[0]))
                if near_bounds["condition_2_estimate"] is not None else None
            ),
            "interpretation_limit": "difference supports a geometry-map contribution for this matched mesh/material/load, but not a pure element-distortion effect or a general formulation conclusion",
        },
        "structural_checks": {
            "all_finite": bool(finite),
            "all_gauss_jacobians_positive": bool(np.isfinite(jacobians).all() and min(jacobians) > 0.0),
            "matrix_symmetry_le_1e_minus_12": bool(symmetry <= 1.0e-12),
            "free_matrix_positive_definite": matrix_positive,
            "applied_load_relative_le_1e_minus_14": bool(applied_load_relative <= 1.0e-14),
        },
        "limits": contract["limits"],
    }
    state_hash = _atomic_npz(
        state_path,
        {
            "coordinates_m": coordinates,
            "connectivity": connectivity,
            "stiffness_n_per_m": stiffness,
            "force_n": force,
            "fixed_dof_mask": fixed_mask,
            "displacement_m": displacement,
            "reactions_n": partition["reactions"],
            "raw_residual_n": partition["raw_residual"],
            "equilibrium_residual_n": partition["equilibrium_residual"],
            "gauss_jacobians_m3": np.asarray(jacobians),
        },
    )
    result["output"] = {
        "matrix_assembled_state_npz": matrix_state_path.name,
        "matrix_assembled_state_sha256": matrix_state_hash,
        "state_npz": state_path.name,
        "state_sha256": state_hash,
    }
    _write_json_atomic(result_path, result)
    result_hash = sha256(result_path)
    _update_checkpoint(
        checkpoint_path,
        checkpoint,
        "COMPLETED",
        result_path=result_path.name,
        result_sha256=result_hash,
        state_path=state_path.name,
        state_sha256=state_hash,
    )
    print(json.dumps({"case_id": result["regular_case"]["case_id"], "execution_status": result["execution_status"]}))
    return result
