"""One globally assembled HEX8-SRI replay per exact J7 nodeid."""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from solveur.elements.solid.hex8 import Hex8Element  # noqa: E402
from solveur.elements.solid.hex8_sri import Hex8SRIElement  # noqa: E402
from solveur.materials.solid import SolidMaterial  # noqa: E402


INPUT_PATH = ROOT / "research/j7_static_debt/inputs/hex8_sri_global_cases.json"
CONTRACT_PATH = ROOT / "research/j7_static_debt/contracts/j7_hex8_sri_postcorrection.json"
INPUT_SHA256 = "66193d6d4411caf842544d9dc74c3252f10d4641a6ce1b5b1745d5dd29c19c74"
CONTRACT_SHA256 = "849ff07e94ee7a1ac6eae321269dcac6e03567b91f4684c22a8da9c37b5116d2"
SRI_SOURCE_SHA256 = "e014652e9efc3912046891348d9dfa76adaa1f8ff084db58e84a9b3d151cf9e4"
HISTORICAL_GATES = {
    "energy_identity_relative": 1.0e-10,
    "dof_equilibrium_residual_relative": 1.0e-10,
    "force_resultant_closure_relative": 1.0e-10,
    "moment_balance_force_length_relative": 1.0e-10,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(path: Path) -> str:
    """Hash UTF-8 source/JSON content independently of checkout line endings."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _canonical_source_sha256(path: Path) -> str:
    """Hash repository source bytes with Git's canonical LF line endings."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _write_json_once(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())


def _attempt_output_dir() -> Path:
    if os.environ.get("QF_DEVELOPMENT_AUTONOMOUS") != "1":
        pytest.fail("invoke this FEM test only through the registered J7 development runner", pytrace=False)
    temporary = os.environ.get("TEMP") or os.environ.get("TMP") or os.environ.get("TMPDIR")
    if not temporary:
        pytest.fail("the monitored J7 attempt did not provide a temporary directory", pytrace=False)
    temp_dir = Path(temporary).resolve()
    attempt_dir = temp_dir.parent
    registered_root = (ROOT / ".codex/development-runs/worktrees/j7_static").resolve()
    try:
        attempt_dir.relative_to(registered_root)
    except ValueError:
        pytest.fail("temporary directory is outside the J7 attempt ledger/output namespace", pytrace=False)
    if temp_dir.name != "tmp" or not re.fullmatch(r"attempt-[0-9]{4}", attempt_dir.name):
        pytest.fail("temporary directory does not identify one registered J7 attempt", pytrace=False)
    output = attempt_dir / "output"
    if not output.is_dir():
        pytest.fail("the registered J7 attempt output directory is missing", pytrace=False)
    return output


def _case(case_id: str) -> dict[str, Any]:
    if _canonical_sha256(INPUT_PATH) != INPUT_SHA256:
        raise RuntimeError("J7 HEX8-SRI case input differs from the frozen contract")
    if _canonical_sha256(CONTRACT_PATH) != CONTRACT_SHA256:
        raise RuntimeError("J7 HEX8-SRI execution contract differs from its frozen digest")
    input_data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    for case in input_data["cases"]:
        if case["case_id"] == case_id:
            return case
    raise ValueError(f"case is not declared by the frozen input: {case_id}")


def _mesh(nx: int, *, distortion: str, length: float, width: float, height: float, ny: int, nz: int):
    nodes: list[list[float]] = []
    node_ids: dict[tuple[int, int, int], int] = {}
    for k in range(nz + 1):
        for j in range(ny + 1):
            for i in range(nx + 1):
                x = length * i / nx
                y = width * j / ny
                z = height * k / nz
                if distortion == "near_degenerate_valid":
                    z = 0.04 * z + 0.006 * (x / length) * (y - 0.5 * width)
                elif distortion != "regular":
                    raise ValueError(f"unsupported frozen distortion {distortion!r}")
                node_ids[i, j, k] = len(nodes)
                nodes.append([x, y, z])
    elements: list[list[int]] = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                elements.append([
                    node_ids[i, j, k], node_ids[i + 1, j, k],
                    node_ids[i + 1, j + 1, k], node_ids[i, j + 1, k],
                    node_ids[i, j, k + 1], node_ids[i + 1, j, k + 1],
                    node_ids[i + 1, j + 1, k + 1], node_ids[i, j + 1, k + 1],
                ])
    return np.asarray(nodes, dtype=np.float64), elements


def _local_dofs(connectivity: list[int]) -> np.ndarray:
    return np.asarray([[3 * node, 3 * node + 1, 3 * node + 2] for node in connectivity], dtype=int).ravel()


def _run(case_id: str, nodeid: str) -> None:
    case = _case(case_id)
    input_data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    requested_threads = dict(contract["resources"]["thread_environment"])
    observed_threads = {name: os.environ.get(name) for name in requested_threads}
    if observed_threads != requested_threads:
        raise RuntimeError("J7 HEX8-SRI thread environment differs from the frozen execution contract")
    try:
        from threadpoolctl import threadpool_info
        threadpools = [
            {key: item.get(key) for key in ("user_api", "internal_api", "version", "num_threads")}
            for item in threadpool_info()
        ]
    except ImportError:
        threadpools = []
    if any(int(pool["num_threads"]) > 1 for pool in threadpools if pool.get("num_threads") is not None):
        raise RuntimeError("numerical threadpool exceeds the frozen one-thread setting")
    frozen_gates = {
        name: float(contract["criteria"][name]["limit"])
        for name in HISTORICAL_GATES
    }
    if frozen_gates != HISTORICAL_GATES:
        raise RuntimeError("frozen J7 gate definitions differ from the historical WP13-12 thresholds")
    if case["nodeid"] != nodeid:
        raise RuntimeError("pytest nodeid differs from the frozen J7 case registration")
    solver_source_path = SRC / "solveur/elements/solid/hex8_sri.py"
    if _canonical_source_sha256(solver_source_path) != SRI_SOURCE_SHA256:
        raise RuntimeError("corrected HEX8-SRI source identity is not the registered w0=8 source")

    geometry = input_data["geometry"]
    material = input_data["material"]
    loading = input_data["loading"]
    nodes, elements = _mesh(
        int(case["nx"]),
        distortion=str(case["distortion"]),
        length=float(geometry["length_m"]),
        width=float(geometry["width_m"]),
        height=float(geometry["height_m"]),
        ny=int(geometry["ny"]),
        nz=int(geometry["nz"]),
    )
    ndof = int(3 * len(nodes))
    if len(nodes) != int(case["expected_nodes"]) or len(elements) != int(case["expected_elements"]) or ndof != int(case["expected_total_dofs"]):
        raise RuntimeError("generated mesh size does not match the frozen historical case")

    output_dir = _attempt_output_dir()
    case_dir = output_dir / case_id.lower()
    case_dir.mkdir(exist_ok=False)
    stiffness = np.zeros((ndof, ndof), dtype=np.float64)
    element = Hex8SRIElement(SolidMaterial(E=float(material["young_modulus_pa"]), nu=float(case["poisson_ratio"])))
    determinants: list[float] = []
    for connectivity in elements:
        coordinates = nodes[connectivity]
        dofs = _local_dofs(connectivity)
        stiffness[np.ix_(dofs, dofs)] += element.stiffness(coordinates)
        determinants.extend(
            float(element.jacobian_determinant(coordinates, point))
            for point in Hex8Element.integration_points
        )

    force = np.zeros(ndof, dtype=np.float64)
    length = float(geometry["length_m"])
    end_nodes = np.flatnonzero(np.isclose(nodes[:, 0], length))
    expected_end_count = int(loading["end_face_node_count"])
    if len(end_nodes) != expected_end_count:
        raise RuntimeError("end-face node count differs from the frozen load definition")
    force[3 * end_nodes + 2] = float(loading["total_force_n"][2]) / float(expected_end_count)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    fixed = (3 * fixed_nodes[:, None] + np.arange(3)).reshape(-1)
    if len(fixed_nodes) != int(case["expected_fixed_nodes"]) or fixed.size != int(case["expected_fixed_dofs"]):
        raise RuntimeError("fixed node/DOF mask differs from the frozen historical boundary condition")
    fixed_mask = np.zeros(ndof, dtype=bool)
    fixed_mask[fixed] = True
    free = np.flatnonzero(~fixed_mask)
    if len(free) != int(case["expected_free_dofs"]):
        raise RuntimeError("free DOF count differs from the frozen historical boundary condition")

    displacement = np.zeros(ndof, dtype=np.float64)
    displacement[free] = np.linalg.solve(stiffness[np.ix_(free, free)], force[free])
    raw_residual = stiffness @ displacement - force
    reactions = np.zeros(ndof, dtype=np.float64)
    reactions[fixed] = raw_residual[fixed]
    equilibrium_residual = raw_residual - reactions

    external_rows = force.reshape((-1, 3))
    reaction_rows = reactions.reshape((-1, 3))
    external_force_resultant = np.sum(external_rows, axis=0)
    expected_force_resultant = np.asarray(loading["total_force_n"], dtype=np.float64)
    applied_load_resultant_relative = float(
        np.linalg.norm(external_force_resultant - expected_force_resultant)
        / max(float(np.linalg.norm(expected_force_resultant)), 1.0)
    )
    reaction_force_resultant = np.sum(reaction_rows, axis=0)
    force_closure = external_force_resultant + reaction_force_resultant
    external_moment_terms = np.cross(nodes, external_rows)
    reaction_moment_terms = np.cross(nodes, reaction_rows)
    external_moment = np.sum(external_moment_terms, axis=0)
    reaction_moment = np.sum(reaction_moment_terms, axis=0)
    moment_closure = external_moment + reaction_moment

    strain_energy = float(0.5 * displacement @ stiffness @ displacement)
    external_work = float(0.5 * displacement @ force)
    force_norm = max(float(np.linalg.norm(force)), 1.0)
    energy_rel = abs(strain_energy - external_work) / max(abs(external_work), 1.0)
    dof_residual_rel = float(np.linalg.norm(equilibrium_residual) / force_norm)
    force_closure_rel = float(np.linalg.norm(force_closure) / force_norm)
    moment_closure_rel = float(np.linalg.norm(moment_closure) / max(float(np.linalg.norm(force)) * length, 1.0))
    matrix_symmetry_rel = float(np.linalg.norm(stiffness - stiffness.T) / max(float(np.linalg.norm(stiffness)), 1.0))
    finite = bool(
        np.isfinite(stiffness).all() and np.isfinite(displacement).all() and np.isfinite(force).all()
        and np.isfinite(reactions).all() and np.isfinite(determinants).all()
    )
    criteria = {
        "energy_identity_relative": {"value": energy_rel, "limit": frozen_gates["energy_identity_relative"]},
        "dof_equilibrium_residual_relative": {"value": dof_residual_rel, "limit": frozen_gates["dof_equilibrium_residual_relative"]},
        "force_resultant_closure_relative": {"value": force_closure_rel, "limit": frozen_gates["force_resultant_closure_relative"]},
        "moment_balance_force_length_relative": {"value": moment_closure_rel, "limit": frozen_gates["moment_balance_force_length_relative"]},
        "applied_load_resultant_relative": {
            "value": applied_load_resultant_relative,
            "limit": float(contract["criteria"]["applied_load_resultant_relative"]["limit"]),
        },
        "jacobian_positive": {"value": bool(determinants) and min(determinants) > 0.0, "expected": True},
        "finite": {"value": finite, "expected": True},
        "matrix_symmetry_relative": {
            "value": matrix_symmetry_rel,
            "limit": float(contract["criteria"]["matrix_symmetry_relative"]["limit"]),
        },
    }
    for criterion in criteria.values():
        observed = criterion["value"]
        if isinstance(observed, bool):
            criterion["status"] = "PASS" if observed is criterion["expected"] else "FAIL"
        else:
            criterion["status"] = "PASS" if float(observed) <= float(criterion["limit"]) else "FAIL"

    record = {
        "schema": "qf-j7-hex8-sri-global-result-v1",
        "case_id": case_id,
        "classification": "DEVELOPMENT_GLOBAL_REPLAY_NOT_QUALIFICATION",
        "execution_status": "COMPLETED",
        "scientific_criteria_status": "PASS" if all(row["status"] == "PASS" for row in criteria.values()) else "FAIL",
        "source": {
            "solver_source_sha256": SRI_SOURCE_SHA256,
            "solver_source_worktree_sha256": _sha256(solver_source_path),
            "repository_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "contract_canonical_sha256": CONTRACT_SHA256,
            "input_sha256": INPUT_SHA256,
            "nodeid": nodeid,
        },
        "model": {
            "family": "HEX8-SRI linear small-strain isotropic elasticity",
            "young_modulus_pa": float(material["young_modulus_pa"]),
            "poisson_ratio": float(case["poisson_ratio"]),
            "length_m": length,
            "width_m": float(geometry["width_m"]),
            "height_m": float(geometry["height_m"]),
            "nx": int(case["nx"]),
            "ny": int(geometry["ny"]),
            "nz": int(geometry["nz"]),
            "distortion": case["distortion"],
            "nodes": len(nodes),
            "elements": len(elements),
            "total_dofs": ndof,
            "fixed_nodes": len(fixed_nodes),
            "fixed_dofs": int(fixed.size),
            "end_face_load_nodes": int(len(end_nodes)),
            "total_load_n": [0.0, 0.0, float(np.sum(external_rows[:, 2]))],
        },
        "metrics": {
            "strain_energy_j": strain_energy,
            "external_work_j": external_work,
            "energy_identity_relative": energy_rel,
            "dof_equilibrium_residual_relative": dof_residual_rel,
            "force_resultant_closure_relative": force_closure_rel,
            "moment_balance_force_length_relative": moment_closure_rel,
            "force_resultant_residual_n": force_closure.tolist(),
            "applied_load_resultant_n": external_force_resultant.tolist(),
            "applied_load_resultant_relative": applied_load_resultant_relative,
            "moment_residual_about_origin_nm": moment_closure.tolist(),
            "min_gauss_jacobian_m3": float(min(determinants)),
            "max_gauss_jacobian_m3": float(max(determinants)),
            "matrix_symmetry_relative": matrix_symmetry_rel,
            "max_displacement_m": float(np.max(np.abs(displacement))),
        },
        "criteria": criteria,
        "reference_limit": "No independent displacement reference is established for these exact global configurations.",
        "historical_status_policy": "Pre-correction WP12/WP13-12 FAILs remain unchanged; this execution is not a general HEX8-SRI qualification.",
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "platform": platform.platform(),
            "requested_thread_environment": observed_threads,
            "threadpools": threadpools,
        },
    }
    if not finite:
        raise RuntimeError("nonfinite assembled or solved quantities; result was not treated as completed")
    npz_buffer = io.BytesIO()
    np.savez_compressed(
        npz_buffer,
        coordinates_m=nodes,
        connectivity=np.asarray(elements, dtype=np.int64),
        stiffness_n_per_m=stiffness,
        force_n=force,
        fixed_dof_mask=fixed_mask,
        displacement_m=displacement,
        reactions_n=reactions,
        raw_residual_n=raw_residual,
        equilibrium_residual_n=equilibrium_residual,
        gauss_jacobians_m3=np.asarray(determinants),
        external_moment_terms_nm=external_moment_terms,
        reaction_moment_terms_nm=reaction_moment_terms,
    )
    with (case_dir / "numerical_state.npz").open("xb") as stream:
        stream.write(npz_buffer.getvalue())
        stream.flush()
        os.fsync(stream.fileno())
    record["archive"] = {
        "filename": "numerical_state.npz",
        "sha256": _sha256(case_dir / "numerical_state.npz"),
        "bytes": (case_dir / "numerical_state.npz").stat().st_size,
    }
    _write_json_once(case_dir / "result.json", record)
    assert (case_dir / "result.json").is_file() and (case_dir / "numerical_state.npz").is_file()


def test_j7_hex8_sri_nu04999_nx16_regular() -> None:
    """Replay the pre-correction regular nearly-incompressible global case."""
    _run(
        "J7-HEX8-SRI-REGULAR-NU04999-NX16",
        "tests/verification/test_j7_hex8_sri_postcorrection.py::test_j7_hex8_sri_nu04999_nx16_regular",
    )


def test_j7_hex8_sri_nu0495_nx4_near_degenerate() -> None:
    """Replay the pre-correction valid near-degenerate global case."""
    _run(
        "J7-HEX8-SRI-NEAR-DEGENERATE-NU0495-NX4",
        "tests/verification/test_j7_hex8_sri_postcorrection.py::test_j7_hex8_sri_nu0495_nx4_near_degenerate",
    )
