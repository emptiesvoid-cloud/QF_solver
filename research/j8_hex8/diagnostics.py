"""Independent analysis and bounded resolution studies on archived HEX8-SRI matrices."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

import mpmath as mp
import numpy as np
import scipy
import threadpoolctl
from scipy.linalg import cho_factor, cho_solve, solve as scipy_solve


ROOT = Path(__file__).resolve().parents[2]
INPUT_ROOT = ROOT / "research/j8_hex8/inputs"
CONTRACT_PATH = ROOT / "research/j8_hex8/contracts/j8_hex8_conditioning_contract.json"
EXECUTION_MANIFEST_PATH = ROOT / "research/j8_hex8/contracts/execution_manifest.json"
CASE_FILES = {
    "regular": ("regular_nu04999_nx16_result.json", "regular_nu04999_nx16_state.npz"),
    "near_degenerate": (
        "near_degenerate_nu0495_nx4_result.json",
        "near_degenerate_nu0495_nx4_state.npz",
    ),
}
CASE_IDS = {
    "regular": "j8_hex8_regular_nu04999_nx16",
    "near_degenerate": "j8_hex8_near_degenerate_nu0495_nx4",
}
NODEIDS = {
    "regular": "tests/verification/test_j8_hex8_conditioning.py::test_j8_regular_nu04999_recalculation_and_methods",
    "near_degenerate": "tests/verification/test_j8_hex8_conditioning.py::test_j8_near_degenerate_nu0495_recalculation_and_methods",
}
FLOAT64_U = float(np.finfo(np.float64).eps / 2.0)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def gamma(k: int) -> float:
    product = k * FLOAT64_U
    if product >= 1.0:
        raise ValueError("gamma(k) is undefined for k*u >= 1")
    return product / (1.0 - product)


def compensated_matvec(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
    """Compute each row dot product with rounded binary64 products and math.fsum."""
    a = np.asarray(matrix, dtype=np.float64)
    x = np.asarray(vector, dtype=np.float64)
    if a.ndim != 2 or x.shape != (a.shape[1],):
        raise ValueError("matrix/vector dimensions do not agree")
    return np.fromiter(
        (math.fsum(float(value) * float(component) for value, component in zip(row, x)) for row in a),
        dtype=np.float64,
        count=a.shape[0],
    )


def partitioned_residuals(
    stiffness: np.ndarray,
    force: np.ndarray,
    displacement: np.ndarray,
    fixed_mask: np.ndarray,
) -> dict[str, np.ndarray]:
    """Return residuals/reactions using the full nonzero prescribed-value partition."""
    k = np.asarray(stiffness, dtype=np.float64)
    f = np.asarray(force, dtype=np.float64)
    u = np.asarray(displacement, dtype=np.float64)
    fixed = np.asarray(fixed_mask, dtype=bool)
    if k.ndim != 2 or k.shape[0] != k.shape[1]:
        raise ValueError("stiffness must be square")
    if f.shape != (k.shape[0],) or u.shape != f.shape or fixed.shape != f.shape:
        raise ValueError("force, displacement, and fixed mask must match stiffness size")
    raw = compensated_matvec(k, u) - f
    reactions = np.zeros_like(raw)
    reactions[fixed] = raw[fixed]
    equilibrium = raw - reactions
    free = ~fixed
    # These are the partitioned equations, including K_fc*u_c for nonzero supports.
    effective_rhs = f[free] - compensated_matvec(k[np.ix_(free, fixed)], u[fixed])
    return {
        "raw_residual": raw,
        "reactions": reactions,
        "equilibrium_residual": equilibrium,
        "free_matrix": k[np.ix_(free, free)],
        "effective_free_rhs": effective_rhs,
        "free_displacement": u[free],
        "free_mask": free,
        "fixed_values": u[fixed],
    }


def _sum_components(values: np.ndarray) -> np.ndarray:
    rows = np.asarray(values, dtype=np.float64).reshape((-1, 3))
    return np.array([math.fsum(float(value) for value in rows[:, axis]) for axis in range(3)])


def _moment_sum(coordinates: np.ndarray, vectors: np.ndarray, origin: np.ndarray) -> np.ndarray:
    xyz = np.asarray(coordinates, dtype=np.float64)
    force_rows = np.asarray(vectors, dtype=np.float64).reshape((-1, 3))
    relative = xyz - np.asarray(origin, dtype=np.float64)
    components = [[], [], []]
    for point, load in zip(relative, force_rows):
        components[0].append(float(point[1]) * float(load[2]) - float(point[2]) * float(load[1]))
        components[1].append(float(point[2]) * float(load[0]) - float(point[0]) * float(load[2]))
        components[2].append(float(point[0]) * float(load[1]) - float(point[1]) * float(load[0]))
    return np.array([math.fsum(component) for component in components])


def global_balances(
    coordinates_m: np.ndarray,
    force_n: np.ndarray,
    reactions_n: np.ndarray,
    reference_length_m: float,
) -> dict[str, Any]:
    coordinates = np.asarray(coordinates_m, dtype=np.float64)
    force = np.asarray(force_n, dtype=np.float64)
    reactions = np.asarray(reactions_n, dtype=np.float64)
    external = _sum_components(force)
    support = _sum_components(reactions)
    closure = external + support
    centroid = np.array(
        [math.fsum(float(value) for value in coordinates[:, axis]) / len(coordinates) for axis in range(3)]
    )
    moment_external_origin = _moment_sum(coordinates, force, np.zeros(3))
    moment_reaction_origin = _moment_sum(coordinates, reactions, np.zeros(3))
    moment_external_centroid = _moment_sum(coordinates, force, centroid)
    moment_reaction_centroid = _moment_sum(coordinates, reactions, centroid)
    moment_origin = moment_external_origin + moment_reaction_origin
    moment_centroid = moment_external_centroid + moment_reaction_centroid
    force_scale = float(np.linalg.norm(force))  # frozen J7 used the assembled nodal vector norm
    moment_scale_terms = []
    for point, load, reaction in zip(coordinates - centroid, force.reshape((-1, 3)), reactions.reshape((-1, 3))):
        radius = math.sqrt(math.fsum(float(value) ** 2 for value in point))
        moment_scale_terms.append(radius * math.sqrt(math.fsum(float(value) ** 2 for value in load)))
        moment_scale_terms.append(radius * math.sqrt(math.fsum(float(value) ** 2 for value in reaction)))
    contribution_scale = math.fsum(moment_scale_terms)
    return {
        "external_resultant_n": external.tolist(),
        "reaction_resultant_n": support.tolist(),
        "force_closure_n": closure.tolist(),
        "force_closure_norm_n": float(np.linalg.norm(closure)),
        "j7_force_closure_relative": float(np.linalg.norm(closure) / max(force_scale, 1.0)),
        "moment_origin_external_nm": moment_external_origin.tolist(),
        "moment_origin_reaction_nm": moment_reaction_origin.tolist(),
        "moment_closure_origin_nm": moment_origin.tolist(),
        "moment_closure_origin_norm_nm": float(np.linalg.norm(moment_origin)),
        "moment_centroid_external_nm": moment_external_centroid.tolist(),
        "moment_centroid_reaction_nm": moment_reaction_centroid.tolist(),
        "moment_closure_centroid_nm": moment_centroid.tolist(),
        "moment_closure_centroid_norm_nm": float(np.linalg.norm(moment_centroid)),
        "j7_moment_force_length_relative": float(
            np.linalg.norm(moment_origin) / max(force_scale * reference_length_m, 1.0)
        ),
        "moment_contribution_scale_centroid_nm": contribution_scale,
        "moment_contribution_scaled_indicator": (
            float(np.linalg.norm(moment_centroid) / contribution_scale) if contribution_scale else 0.0
        ),
        "centroid_m": centroid.tolist(),
        "origin_transport_residual_nm": (
            moment_centroid - (moment_origin - np.cross(centroid, closure))
        ).tolist(),
    }


def energy_diagnostics(
    stiffness: np.ndarray,
    force: np.ndarray,
    displacement: np.ndarray,
    ku_compensated: np.ndarray,
) -> dict[str, float | bool]:
    u = np.asarray(displacement, dtype=np.float64)
    f = np.asarray(force, dtype=np.float64)
    ku = np.asarray(ku_compensated, dtype=np.float64)
    strain_energy_j = 0.5 * math.fsum(float(ui) * float(ki) for ui, ki in zip(u, ku))
    external_work_j = 0.5 * math.fsum(float(ui) * float(fi) for ui, fi in zip(u, f))
    delta_j = strain_energy_j - external_work_j
    relative_scale = max(abs(strain_energy_j), abs(external_work_j))
    delta_from_residual_j = 0.5 * math.fsum(
        float(ui) * float(ki - fi) for ui, ki, fi in zip(u, ku, f)
    )
    n = len(u)
    row_absolute_sums = [
        math.fsum(abs(float(a) * float(component)) for a, component in zip(row, u))
        for row in np.asarray(stiffness, dtype=np.float64)
    ]
    strain_terms = [abs(float(ui) * float(ki)) for ui, ki in zip(u, ku)]
    work_terms = [abs(float(ui) * float(fi)) for ui, fi in zip(u, f)]
    strain_evaluation_bound_j = 0.5 * 4.0 * (
        gamma(n + 1) * math.fsum(abs(float(ui)) * row_sum for ui, row_sum in zip(u, row_absolute_sums))
        + gamma(n + 2) * math.fsum(strain_terms)
    )
    work_evaluation_bound_j = 0.5 * 4.0 * gamma(n + 2) * math.fsum(work_terms)
    comparison_bound_j = strain_evaluation_bound_j + work_evaluation_bound_j
    legacy_si = abs(delta_j) / max(abs(external_work_j), 1.0)
    strain_energy_nmm = strain_energy_j * 1000.0
    external_work_nmm = external_work_j * 1000.0
    delta_nmm = delta_j * 1000.0
    legacy_nmm = abs(delta_nmm) / max(abs(external_work_nmm), 1.0)
    return {
        "strain_energy_j": strain_energy_j,
        "external_work_j": external_work_j,
        "energy_delta_j": delta_j,
        "energy_delta_from_residual_identity_j": delta_from_residual_j,
        "energy_identity_evaluation_bound_j": comparison_bound_j,
        "strain_energy_evaluation_bound_j": strain_evaluation_bound_j,
        "external_work_evaluation_bound_j": work_evaluation_bound_j,
        "legacy_metric_si": legacy_si,
        "strain_energy_nmm": strain_energy_nmm,
        "external_work_nmm": external_work_nmm,
        "legacy_metric_nmm": legacy_nmm,
        "legacy_metric_nmm_to_si_ratio": legacy_nmm / legacy_si if legacy_si else 1.0,
        "prospective_unit_covariant_indicator": abs(delta_j) / relative_scale if relative_scale else 0.0,
    }


def backward_error_inf(matrix: np.ndarray, vector: np.ndarray, rhs: np.ndarray) -> dict[str, float]:
    a = np.asarray(matrix, dtype=np.float64)
    x = np.asarray(vector, dtype=np.float64)
    b = np.asarray(rhs, dtype=np.float64)
    residual = compensated_matvec(a, x) - b
    a_inf = max(math.fsum(abs(float(value)) for value in row) for row in a)
    denominator = a_inf * float(np.max(np.abs(x))) + float(np.max(np.abs(b)))
    eta = float(np.max(np.abs(residual)) / denominator) if denominator else 0.0
    limit = 20.0 * gamma(a.shape[0] + 1)
    return {
        "residual_inf": float(np.max(np.abs(residual))),
        "backward_error_inf": eta,
        "indicator_limit": limit,
        "within_backward_error_indicator": eta <= limit,
    }


def _git_text(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _assert_execution_inputs(case_key: str, nodeid: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Path]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(EXECUTION_MANIFEST_PATH.read_text(encoding="utf-8"))
    if canonical_sha256(CONTRACT_PATH) != manifest["contract_canonical_lf_sha256"]:
        raise RuntimeError("J8 contract digest differs from the frozen execution manifest")
    registration_path = ROOT / "research/j8_hex8/execution_scope_registration.json"
    if canonical_sha256(registration_path) != manifest["scope_registration_canonical_lf_sha256"]:
        raise RuntimeError("J8 scope registration differs from the frozen execution manifest")
    if nodeid != NODEIDS[case_key] or nodeid != manifest["cases"][case_key]["nodeid"]:
        raise RuntimeError("pytest nodeid differs from the registered contract/manifest")
    source_head = manifest["analysis_source_commit"]
    # Successful --is-ancestor emits no text; a failed relation raises above.
    _git_text("merge-base", "--is-ancestor", source_head, "HEAD")
    changed = _git_text("diff", "--name-only", f"{source_head}..HEAD").splitlines()
    if changed != ["research/j8_hex8/contracts/execution_manifest.json"]:
        raise RuntimeError("execution HEAD must differ from the frozen analysis source only by its manifest")
    if _git_text("rev-parse", f"{source_head}:src/solveur") != manifest["solver_source_tree_sha1"]:
        raise RuntimeError("solver source tree differs from the frozen J7 system source")
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
    for package, expected in manifest["dependency_versions"].items():
        if importlib.metadata.version(package) != expected:
            raise RuntimeError(f"frozen J8 dependency version differs: {package}")
    for variable, expected in manifest["thread_environment"].items():
        if os.environ.get(variable) != expected:
            raise RuntimeError(f"J8 numerical thread limit differs: {variable}")

    result_name, state_name = CASE_FILES[case_key]
    result_path = INPUT_ROOT / result_name
    state_path = INPUT_ROOT / state_name
    input_record = manifest["cases"][case_key]
    if sha256(result_path) != input_record["result_sha256"]:
        raise RuntimeError("J7 result JSON changed after its checksum was frozen")
    if sha256(state_path) != input_record["state_npz_sha256"]:
        raise RuntimeError("J7 state archive changed after its checksum was frozen")
    output_dir = _attempt_output_dir()
    return contract, manifest, json.loads(result_path.read_text(encoding="utf-8")), state_path


def _attempt_output_dir() -> Path:
    if os.environ.get("QF_DEVELOPMENT_AUTONOMOUS") != "1":
        raise RuntimeError("invoke J8 diagnostic nodes only through the registered development runner")
    temporary = os.environ.get("TEMP") or os.environ.get("TMP") or os.environ.get("TMPDIR")
    if not temporary:
        raise RuntimeError("registered J8 attempt did not provide a temporary directory")
    temp_dir = Path(temporary).resolve()
    attempt_dir = temp_dir.parent
    registered_root = (ROOT / ".codex/development-runs/worktrees/j8_hex8").resolve()
    attempt_dir.relative_to(registered_root)
    if temp_dir.name != "tmp" or not attempt_dir.name.startswith("attempt-"):
        raise RuntimeError("temporary directory does not identify a registered J8 attempt")
    output = attempt_dir / "output"
    if not output.is_dir():
        raise RuntimeError("registered J8 attempt output directory is missing")
    return output


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
        temp_path = Path(stream.name)
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp_path, path)


def _write_solutions_atomic(path: Path, vectors: dict[str, np.ndarray]) -> str:
    buffer = __import__("io").BytesIO()
    np.savez_compressed(buffer, **vectors)
    encoded = buffer.getvalue()
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
        temp_path = Path(stream.name)
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp_path, path)
    return hashlib.sha256(encoded).hexdigest()


def _state_metrics(
    stiffness: np.ndarray,
    force: np.ndarray,
    displacement: np.ndarray,
    fixed_mask: np.ndarray,
    coordinates: np.ndarray,
    reference_length_m: float,
) -> dict[str, Any]:
    partition = partitioned_residuals(stiffness, force, displacement, fixed_mask)
    balances = global_balances(coordinates, force, partition["reactions"], reference_length_m)
    energy = energy_diagnostics(stiffness, force, displacement, compensated_matvec(stiffness, displacement))
    energy["prescribed_support_values_are_zero"] = bool(np.all(partition["fixed_values"] == 0.0))
    backward = backward_error_inf(
        partition["free_matrix"], partition["free_displacement"], partition["effective_free_rhs"]
    )
    return {
        "free_residual_norm_n": float(np.linalg.norm(partition["equilibrium_residual"][partition["free_mask"]])),
        "free_residual_relative_to_force_norm": float(
            np.linalg.norm(partition["equilibrium_residual"][partition["free_mask"]])
            / max(float(np.linalg.norm(force)), 1.0)
        ),
        "max_prescribed_displacement_m": float(np.max(np.abs(partition["fixed_values"]))),
        "backward_error": backward,
        "balances": balances,
        "energy": energy,
        "raw_residual_n": partition["raw_residual"],
        "reactions_n": partition["reactions"],
        "equilibrium_residual_n": partition["equilibrium_residual"],
    }


def _roundoff_comparison(
    stiffness: np.ndarray,
    force: np.ndarray,
    displacement: np.ndarray,
    independently_recomputed: dict[str, Any],
    archived: dict[str, np.ndarray],
) -> dict[str, Any]:
    n = stiffness.shape[0]
    ku = compensated_matvec(stiffness, displacement)
    terms = np.abs(stiffness * displacement[np.newaxis, :])
    absolute_dot_sums = np.fromiter(
        (math.fsum(float(value) for value in row) for row in terms), dtype=np.float64, count=n
    )
    envelope = 4.0 * gamma(n + 2) * (absolute_dot_sums + np.abs(force))
    archived_raw = archived["raw_residual_n"]
    archive_delta = np.abs(independently_recomputed["raw_residual_n"] - archived_raw)
    reaction_delta = np.abs(independently_recomputed["reactions_n"] - archived["reactions_n"])
    equilibrium_delta = np.abs(
        independently_recomputed["equilibrium_residual_n"] - archived["equilibrium_residual_n"]
    )
    ratios = np.divide(archive_delta, envelope, out=np.zeros_like(archive_delta), where=envelope > 0.0)
    return {
        "gamma_factor": 4,
        "gamma_k": n + 2,
        "max_componentwise_archived_raw_residual_difference_n": float(np.max(archive_delta)),
        "max_componentwise_roundoff_envelope_n": float(np.max(envelope)),
        "max_component_error_to_envelope_ratio": float(np.max(ratios)),
        "archived_raw_residual_within_envelope": bool(np.all(archive_delta <= envelope)),
        "max_componentwise_archived_reaction_difference_n": float(np.max(reaction_delta)),
        "archived_reactions_within_roundoff_envelope": bool(np.all(reaction_delta <= envelope)),
        "max_componentwise_archived_equilibrium_residual_difference_n": float(np.max(equilibrium_delta)),
        "archived_equilibrium_residual_within_roundoff_envelope": bool(np.all(equilibrium_delta <= envelope)),
        "archived_reaction_difference_norm_n": float(
            np.linalg.norm(reaction_delta)
        ),
        "archived_equilibrium_residual_difference_norm_n": float(
            np.linalg.norm(equilibrium_delta)
        ),
        "compensated_Ku_norm_n": float(np.linalg.norm(ku)),
    }


def _method_entry(
    name: str,
    x_free: np.ndarray,
    free_matrix: np.ndarray,
    effective_rhs: np.ndarray,
    reference_free: np.ndarray,
    build_full: Callable[[np.ndarray], np.ndarray],
    stiffness: np.ndarray,
    force: np.ndarray,
    fixed_mask: np.ndarray,
    coordinates: np.ndarray,
    length_m: float,
    elapsed: float,
    extra: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], np.ndarray]:
    full = build_full(np.asarray(x_free, dtype=np.float64))
    metrics = _state_metrics(stiffness, force, full, fixed_mask, coordinates, length_m)
    backward = backward_error_inf(free_matrix, np.asarray(x_free, dtype=np.float64), effective_rhs)
    entry: dict[str, Any] = {
        "status": "COMPLETED",
        "elapsed_seconds": float(elapsed),
        "relative_displacement_change_from_archived": float(
            np.linalg.norm(np.asarray(x_free) - reference_free) / max(float(np.linalg.norm(reference_free)), np.finfo(float).tiny)
        ),
        "free_residual_norm_n": metrics["free_residual_norm_n"],
        "backward_error": backward,
        "force_closure_n": metrics["balances"]["force_closure_n"],
        "force_closure_norm_n": metrics["balances"]["force_closure_norm_n"],
        "moment_closure_origin_nm": metrics["balances"]["moment_closure_origin_nm"],
        "moment_closure_origin_norm_nm": metrics["balances"]["moment_closure_origin_norm_nm"],
        "energy": metrics["energy"],
    }
    if extra:
        entry.update(extra)
    return entry, full


def _high_precision_solve(matrix: np.ndarray, rhs: np.ndarray, dps: int) -> tuple[np.ndarray, dict[str, Any], float]:
    started = time.perf_counter()
    with mp.workdps(dps):
        a_mp = mp.matrix([[mp.mpf(float(value)) for value in row] for row in matrix])
        b_mp = mp.matrix([mp.mpf(float(value)) for value in rhs])
        x_mp = mp.lu_solve(a_mp, b_mp)
        residual_mp = [
            mp.fsum(a_mp[i, j] * x_mp[j] for j in range(a_mp.cols)) - b_mp[i]
            for i in range(a_mp.rows)
        ]
        residual_inf = max(abs(value) for value in residual_mp)
        a_inf = max(mp.fsum(abs(a_mp[i, j]) for j in range(a_mp.cols)) for i in range(a_mp.rows))
        x_inf = max(abs(value) for value in x_mp)
        b_inf = max(abs(value) for value in b_mp)
        denominator = a_inf * x_inf + b_inf
        eta = residual_inf / denominator if denominator else mp.mpf("0")
        x_float = np.array([float(value) for value in x_mp], dtype=np.float64)
        high_precision_metrics = {
            "decimal_digits": int(dps),
            "residual_inf_as_mp": mp.nstr(residual_inf, n=20),
            "backward_error_inf_as_mp": mp.nstr(eta, n=20),
            "relative_change_from_archived_is_computed_after_float_conversion": True,
        }
    return x_float, high_precision_metrics, time.perf_counter() - started


def run_case(case_key: str, nodeid: str) -> dict[str, Any]:
    if case_key not in CASE_FILES:
        raise ValueError(f"unknown J8 case: {case_key}")
    contract, manifest, archived_result, state_path = _assert_execution_inputs(case_key, nodeid)
    result_name, _ = CASE_FILES[case_key]
    result_path = INPUT_ROOT / result_name
    archive_expected = contract["inputs"][case_key]["npz_sha256"]
    if sha256(state_path) != archive_expected or archived_result["archive"]["sha256"] != archive_expected:
        raise RuntimeError("J7 state hash is inconsistent across the contract and result JSON")

    with np.load(state_path, allow_pickle=False) as data:
        state = {key: data[key] for key in data.files}
    required = {
        "coordinates_m", "connectivity", "stiffness_n_per_m", "force_n", "fixed_dof_mask",
        "displacement_m", "reactions_n", "raw_residual_n", "equilibrium_residual_n",
        "gauss_jacobians_m3",
    }
    if not required.issubset(state):
        raise RuntimeError("J7 numerical archive is missing one or more required state arrays")
    stiffness = np.asarray(state["stiffness_n_per_m"], dtype=np.float64)
    force = np.asarray(state["force_n"], dtype=np.float64)
    displacement = np.asarray(state["displacement_m"], dtype=np.float64)
    fixed = np.asarray(state["fixed_dof_mask"], dtype=bool)
    coordinates = np.asarray(state["coordinates_m"], dtype=np.float64)
    dimensions = contract["inputs"][case_key]["dimensions"]
    if stiffness.shape != (dimensions["dofs"], dimensions["dofs"]):
        raise RuntimeError("archived stiffness shape differs from the frozen contract")
    if int(np.count_nonzero(~fixed)) != dimensions["free_dofs"] or len(coordinates) != dimensions["nodes"]:
        raise RuntimeError("archived mask/coordinate dimensions differ from the frozen contract")
    if not all(np.all(np.isfinite(state[key])) for key in required):
        raise RuntimeError("archived numerical arrays contain nonfinite values")
    if np.any(state["gauss_jacobians_m3"] <= 0.0):
        raise RuntimeError("archived J7 state contains a nonpositive Gauss-point Jacobian")
    symmetry = float(np.linalg.norm(stiffness - stiffness.T) / max(float(np.linalg.norm(stiffness)), 1.0))
    if symmetry > 1.0e-12:
        raise RuntimeError("archived stiffness symmetry exceeds the frozen structural check")

    partition = partitioned_residuals(stiffness, force, displacement, fixed)
    recon = _state_metrics(stiffness, force, displacement, fixed, coordinates, 20.0)
    applied_load = _sum_components(force.reshape((-1, 3)))
    expected_load = np.asarray(archived_result["model"]["total_load_n"], dtype=np.float64)
    applied_load_relative = float(
        np.linalg.norm(applied_load - expected_load) / max(float(np.linalg.norm(expected_load)), 1.0)
    )
    archived_arrays = {
        "raw_residual_n": state["raw_residual_n"],
        "reactions_n": state["reactions_n"],
        "equilibrium_residual_n": state["equilibrium_residual_n"],
    }
    reconstruction = _roundoff_comparison(stiffness, force, displacement, recon, archived_arrays)
    reconstruction["applied_load_resultant_n"] = applied_load.tolist()
    reconstruction["expected_load_resultant_n"] = expected_load.tolist()
    reconstruction["applied_load_resultant_relative"] = applied_load_relative
    reconstruction["applied_load_within_frozen_1e_minus_14_indicator"] = applied_load_relative <= 1.0e-14
    archived_metric = archived_result["metrics"]
    reconstruction["runner_energy_delta_difference_j"] = float(
        recon["energy"]["energy_delta_j"]
        - (archived_metric["strain_energy_j"] - archived_metric["external_work_j"])
    )
    reconstruction["runner_force_closure_difference_n"] = (
        np.asarray(recon["balances"]["force_closure_n"])
        - np.asarray(archived_metric["force_resultant_residual_n"])
    ).tolist()
    reconstruction["runner_moment_closure_origin_difference_nm"] = (
        np.asarray(recon["balances"]["moment_closure_origin_nm"])
        - np.asarray(archived_metric["moment_residual_about_origin_nm"])
    ).tolist()
    strain_energy_difference = abs(recon["energy"]["strain_energy_j"] - archived_metric["strain_energy_j"])
    work_difference = abs(recon["energy"]["external_work_j"] - archived_metric["external_work_j"])
    reconstruction["runner_strain_energy_difference_j"] = strain_energy_difference
    reconstruction["runner_strain_energy_evaluation_bound_j"] = recon["energy"]["strain_energy_evaluation_bound_j"]
    reconstruction["runner_strain_energy_within_roundoff_envelope"] = (
        strain_energy_difference <= recon["energy"]["strain_energy_evaluation_bound_j"]
    )
    reconstruction["runner_external_work_difference_j"] = work_difference
    reconstruction["runner_external_work_evaluation_bound_j"] = recon["energy"]["external_work_evaluation_bound_j"]
    reconstruction["runner_external_work_within_roundoff_envelope"] = (
        work_difference <= recon["energy"]["external_work_evaluation_bound_j"]
    )

    free_matrix = partition["free_matrix"]
    rhs = partition["effective_free_rhs"]
    reference_free = partition["free_displacement"]
    eigenvalues = np.linalg.eigvalsh(free_matrix)
    free_matrix_positive_definite = bool(eigenvalues[0] > 0.0)
    initial = {
        "schema": "qf-j8-hex8-diagnostic-result-v1",
        "classification": "DEVELOPMENT_DIAGNOSTIC_NOT_QUALIFICATION",
        "case_key": case_key,
        "case_id": archived_result["case_id"],
        "nodeid": nodeid,
        "source": {
            "repository_head": _git_text("rev-parse", "HEAD"),
            "analysis_source_commit": manifest["analysis_source_commit"],
            "solver_source_tree_sha1": manifest["solver_source_tree_sha1"],
            "contract_canonical_lf_sha256": manifest["contract_canonical_lf_sha256"],
            "result_sha256": sha256(result_path),
            "state_npz_sha256": sha256(state_path),
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "mpmath": mp.__version__,
            "numpy_longdouble_mantissa_bits": int(np.finfo(np.longdouble).nmant + 1),
            "threadpool_info": threadpoolctl.threadpool_info(),
            "thread_environment": {key: os.environ.get(key) for key in manifest["thread_environment"]},
        },
        "execution_status": "RECONSTRUCTION_COMPLETE_METHODS_PENDING",
        "classification_note": "No element assembly or load integration was rerun; all methods use the archived binary64 matrix and load vector.",
        "model": archived_result["model"],
        "independent_reconstruction": {
            "stiffness_symmetry_relative": symmetry,
            "free_dofs": int(np.count_nonzero(~fixed)),
            "fixed_dofs": int(np.count_nonzero(fixed)),
            "archived_raw_residual_vs_compensated_sums": reconstruction,
            "free_residual_norm_n": recon["free_residual_norm_n"],
            "free_residual_relative_to_force_norm": recon["free_residual_relative_to_force_norm"],
            "max_prescribed_displacement_m": recon["max_prescribed_displacement_m"],
            "condition_2_estimate": (
                float(eigenvalues[-1] / eigenvalues[0]) if free_matrix_positive_definite else None
            ),
            "lambda_min_n_per_m": float(eigenvalues[0]),
            "lambda_max_n_per_m": float(eigenvalues[-1]),
            "free_matrix_positive_definite": free_matrix_positive_definite,
            "balances": recon["balances"],
            "energy": recon["energy"],
        },
        "methods": {},
        "criteria_status": {
            "input_integrity": "PASS",
            "finite_and_shape_checks": "PASS",
            "applied_load_resultant": (
                "WITHIN_FROZEN_J7_INDICATOR" if applied_load_relative <= 1.0e-14 else "EXCEEDS_FROZEN_J7_INDICATOR"
            ),
            "residual_reconstruction": (
                "WITHIN_ROUNDOFF_ENVELOPE" if reconstruction["archived_raw_residual_within_envelope"] else "EXCEEDS_ROUNDOFF_ENVELOPE"
            ),
            "free_matrix_positive_definite": "PASS" if free_matrix_positive_definite else "FAIL",
            "solver_method_backward_error": "PENDING",
            "physical_accuracy": "NOT_ESTABLISHED",
        },
        "limits": contract["limitations"],
    }
    output_dir = _attempt_output_dir() / CASE_IDS[case_key]
    output_dir.mkdir(exist_ok=False)
    checkpoint_path = output_dir / "checkpoint.json"
    solutions_path = output_dir / "method_solutions.npz"
    reconstruction_path = output_dir / "reconstructed_state.npz"
    result_path_out = output_dir / "diagnostic_result.json"
    solution_vectors = {"archived_displacement_m": displacement}
    reconstruction_arrays_sha256 = _write_solutions_atomic(
        reconstruction_path,
        {
            "compensated_Ku_n": compensated_matvec(stiffness, displacement),
            "recomputed_raw_residual_n": recon["raw_residual_n"],
            "recomputed_reactions_n": recon["reactions_n"],
            "recomputed_equilibrium_residual_n": recon["equilibrium_residual_n"],
        },
    )
    initial["reconstruction_arrays_sha256"] = reconstruction_arrays_sha256
    _write_json_atomic(checkpoint_path, initial)
    if not free_matrix_positive_definite:
        initial["execution_status"] = "ABORTED_FREE_MATRIX_NOT_POSITIVE_DEFINITE"
        _write_json_atomic(checkpoint_path, initial)
        raise RuntimeError("frozen J7 free matrix is not positive definite; declared solve methods are inapplicable")

    def build_full(free_values: np.ndarray) -> np.ndarray:
        full = np.zeros_like(displacement)
        full[fixed] = displacement[fixed]
        full[~fixed] = free_values
        return full

    methods: dict[str, tuple[Callable[[], tuple[np.ndarray, float, dict[str, Any] | None]], bool]] = {}

    def numpy_direct() -> tuple[np.ndarray, float, dict[str, Any] | None]:
        start = time.perf_counter()
        return np.linalg.solve(free_matrix, rhs), time.perf_counter() - start, None

    def scipy_cholesky_solve() -> tuple[np.ndarray, float, dict[str, Any] | None]:
        start = time.perf_counter()
        return scipy_solve(free_matrix, rhs, assume_a="pos", check_finite=True), time.perf_counter() - start, None

    def diagonal_scaled() -> tuple[np.ndarray, float, dict[str, Any] | None]:
        start = time.perf_counter()
        diagonal = np.diag(free_matrix)
        if np.any(diagonal <= 0.0):
            raise ValueError("diagonal scaling requires positive diagonal entries")
        scale = 1.0 / np.sqrt(diagonal)
        scaled_matrix = scale[:, None] * free_matrix * scale[None, :]
        scaled_rhs = scale * rhs
        y = scipy_solve(scaled_matrix, scaled_rhs, assume_a="pos", check_finite=True)
        scaled_eigenvalues = np.linalg.eigvalsh(scaled_matrix)
        return scale * y, time.perf_counter() - start, {
            "scaled_condition_2": float(scaled_eigenvalues[-1] / scaled_eigenvalues[0]),
            "scale_min": float(np.min(scale)),
            "scale_max": float(np.max(scale)),
        }

    def scalar_scaled(alpha: float) -> Callable[[], tuple[np.ndarray, float, dict[str, Any] | None]]:
        def solve_scaled() -> tuple[np.ndarray, float, dict[str, Any] | None]:
            start = time.perf_counter()
            answer = scipy_solve(alpha * free_matrix, alpha * rhs, assume_a="pos", check_finite=True)
            return answer, time.perf_counter() - start, {"equation_scale_alpha": alpha}
        return solve_scaled

    def length_unit_conversion() -> tuple[np.ndarray, float, dict[str, Any] | None]:
        start = time.perf_counter()
        # x_mm = 1000*x_m, so K in N/mm is K_N_per_m/1000 while f remains in N.
        converted = scipy_solve(free_matrix / 1000.0, rhs, assume_a="pos", check_finite=True)
        return converted / 1000.0, time.perf_counter() - start, {
            "solved_displacement_unit": "mm",
            "converted_displacement_unit": "m",
            "stiffness_unit": "N/mm",
            "load_unit": "N",
        }

    def refined_solve() -> tuple[np.ndarray, float, dict[str, Any] | None]:
        start = time.perf_counter()
        factor = cho_factor(free_matrix, lower=True, check_finite=True)
        answer = scipy_solve(free_matrix, rhs, assume_a="pos", check_finite=True)
        steps = []
        previous = math.inf
        limit = 20.0 * gamma(len(rhs) + 1)
        for index in range(1, 4):
            backward = backward_error_inf(free_matrix, answer, rhs)
            steps.append({"iteration": index - 1, **backward})
            if backward["backward_error_inf"] <= limit:
                break
            if backward["backward_error_inf"] >= previous * 0.9:
                break
            previous = backward["backward_error_inf"]
            residual = rhs - compensated_matvec(free_matrix, answer)
            correction = cho_solve(factor, residual, check_finite=True)
            answer = answer + correction
        steps.append({"iteration": len(steps), **backward_error_inf(free_matrix, answer, rhs)})
        return answer, time.perf_counter() - start, {"refinement_steps": steps, "maximum_corrections": 3}

    methods["numpy_direct"] = (numpy_direct, False)
    methods["scipy_positive_definite"] = (scipy_cholesky_solve, False)
    methods["symmetric_diagonal_scaling"] = (diagonal_scaled, False)
    methods["scalar_equation_scale_1e-6"] = (scalar_scaled(1.0e-6), False)
    methods["scalar_equation_scale_1e6"] = (scalar_scaled(1.0e6), False)
    methods["physical_length_unit_m_to_mm"] = (length_unit_conversion, False)
    methods["iterative_refinement"] = (refined_solve, False)
    if case_key == "near_degenerate":
        methods["mpmath_80_decimal_digits"] = (
            lambda: (np.empty(0), 0.0, None),
            True,
        )

    method_errors = []
    for name, (method, high_precision) in methods.items():
        checkpoint = dict(initial)
        checkpoint["execution_status"] = f"METHOD_{name.upper()}_STARTED"
        checkpoint["methods"] = dict(initial["methods"])
        _write_json_atomic(checkpoint_path, checkpoint)
        started = time.perf_counter()
        try:
            if high_precision:
                x_free, high_metadata, elapsed = _high_precision_solve(free_matrix, rhs, 80)
                extra = {"high_precision_reference": high_metadata}
            else:
                x_free, elapsed, extra = method()
            entry, full = _method_entry(
                name, x_free, free_matrix, rhs, reference_free, build_full,
                stiffness, force, fixed, coordinates, 20.0, elapsed, extra,
            )
            entry["backward_error_status"] = (
                "WITHIN_BACKWARD_ERROR_INDICATOR"
                if entry["backward_error"]["within_backward_error_indicator"]
                else "EXCEEDS_BACKWARD_ERROR_INDICATOR"
            )
            if not np.all(np.isfinite(full)):
                raise FloatingPointError("method returned a nonfinite displacement")
            solution_vectors[name + "_displacement_m"] = full
            entry["solution_archive_sha256"] = _write_solutions_atomic(solutions_path, solution_vectors)
            checkpoint["methods"][name] = entry
            checkpoint["execution_status"] = f"METHOD_{name.upper()}_COMPLETE"
            checkpoint["solution_archive_sha256"] = entry["solution_archive_sha256"]
            checkpoint["elapsed_method_call_seconds"] = float(time.perf_counter() - started)
            _write_json_atomic(checkpoint_path, checkpoint)
        except Exception as exc:  # preserve the phase checkpoint before surfacing a method failure
            method_errors.append(name)
            checkpoint["methods"][name] = {
                "status": "FAILED",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "elapsed_method_call_seconds": float(time.perf_counter() - started),
            }
            checkpoint["execution_status"] = f"METHOD_{name.upper()}_FAILED"
            _write_json_atomic(checkpoint_path, checkpoint)

    final = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    final["execution_status"] = "COMPLETED" if not method_errors else "METHOD_FAILURES_RECORDED"
    final["failed_methods"] = method_errors
    final["source"]["state_npz_sha256"] = sha256(state_path)
    final["result_file_sha256"] = sha256(result_path)
    final["criteria_status"]["solver_method_backward_error"] = (
        "REPORTED_PER_METHOD_NO_PHYSICAL_QUALIFICATION"
    )
    final["output"] = {
        "reconstructed_state_npz": reconstruction_path.name,
        "reconstructed_state_sha256": reconstruction_arrays_sha256,
        "method_solutions_npz": solutions_path.name if solutions_path.exists() else None,
        "method_solutions_sha256": sha256(solutions_path) if solutions_path.exists() else None,
        "checkpoint_sha256": sha256(checkpoint_path),
    }
    _write_json_atomic(result_path_out, final)
    print(json.dumps({"case_key": case_key, "execution_status": final["execution_status"], "methods": list(final["methods"])}))
    if method_errors:
        raise RuntimeError("one or more resolution methods failed; see the durable diagnostic checkpoint")
    return final
