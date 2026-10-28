"""Capture and independent oracles for the prospective HEX20 patch diagnostic."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from scipy.sparse import csr_matrix

DIAGNOSTIC_SCOPE_ID = "wp12_hex20_affine_diagnostic"
DIAGNOSTIC_NODEID = "tests/unit/test_wp12b_hex20_affine_diagnostic.py::test_wp12b_hex20_affine_patch_archives_residual"
FACE_PLANES = ((2, -1), (2, 1), (1, -1), (0, 1), (1, 1), (0, -1))
DOF_COMPONENTS = ("UX", "UY", "UZ")
ATTEMPT_ID_RE = re.compile(r"dev-[a-z0-9][a-z0-9-]{7,48}-attempt-[1-9][0-9]*\Z")
SHA256_RE = re.compile(r"[a-f0-9]{64}\Z")
MANIFEST_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}\Z")


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float):
        return value if np.isfinite(value) else {"non_finite": str(value)}
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return repr(value)


def _atomic_json_no_overwrite(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(_json_safe(payload), sort_keys=True, indent=2, allow_nan=False).encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _source_identity(paths: list[Path], repo_root: Path) -> dict[str, Any]:
    hashes = {
        str(path.resolve().relative_to(repo_root.resolve())): hashlib.sha256(path.resolve().read_bytes()).hexdigest()
        for path in paths
    }
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unavailable"
    return {"git_head": commit, "sha256": hashes}


def _model_identity(model: Any, case_parameters: dict[str, Any]) -> dict[str, Any]:
    def entity_data(entity: Any) -> Any:
        if is_dataclass(entity):
            return {field.name: getattr(entity, field.name) for field in fields(entity)}
        if isinstance(entity, (list, tuple)):
            return [entity_data(item) for item in entity]
        if isinstance(entity, dict):
            return {key: entity_data(item) for key, item in entity.items()}
        return entity

    data = {
        "nodes": np.asarray(model.nodes, dtype=np.float64).tolist(),
        "elements": [
            {"type": item.type, "nodes": list(item.nodes), "material": item.material} for item in model.elements
        ],
        "materials": entity_data(model.materials),
        "fixed_dofs": entity_data(model.fixed_dofs),
        "nodal_loads": entity_data(model.loads),
        "distributed_loads": entity_data(model.distributed_loads),
        "case_parameters": case_parameters,
    }
    canonical = json.dumps(_json_safe(data), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return {"sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(), **data}


@dataclass(frozen=True)
class ControllerBinding:
    """Exact controller identity that must be present before the solve starts."""

    worktree_id: str
    attempt_id: str
    manifest_id: str
    manifest_sha256: str
    selected_dofs: int
    evidence_root: Path
    run_json_path: Path


def require_diagnostic_binding(
    environ: Mapping[str, str] | None = None,
) -> ControllerBinding:
    """Fail closed unless the future controller passes the full run/manifest binding."""
    env = os.environ if environ is None else environ
    expected = {
        "QF_DEVELOPMENT_AUTONOMOUS": "1",
        "QF_DEV_WORKTREE_ID": DIAGNOSTIC_SCOPE_ID,
        "QF_DEV_SELECTED_DOFS": "60",
    }
    for key, value in expected.items():
        if env.get(key) != value:
            raise RuntimeError(f"Controller value {key} must equal {value!r}.")

    attempt_id = env.get("QF_DEV_ATTEMPT_ID", "")
    manifest_id = env.get("QF_DEV_MANIFEST_ID", "")
    manifest_sha256 = env.get("QF_DEV_MANIFEST_SHA256", "")
    if not ATTEMPT_ID_RE.fullmatch(attempt_id):
        raise RuntimeError("Controller must pass a canonical QF_DEV_ATTEMPT_ID.")
    if not MANIFEST_ID_RE.fullmatch(manifest_id):
        raise RuntimeError("Controller must pass the validated QF_DEV_MANIFEST_ID.")
    if not SHA256_RE.fullmatch(manifest_sha256):
        raise RuntimeError("Controller must pass the validated QF_DEV_MANIFEST_SHA256.")

    root_value = env.get("QF_DEV_EVIDENCE_ROOT", "")
    if not root_value:
        raise RuntimeError("Controller did not assign an evidence root.")
    root = Path(root_value).expanduser().resolve()
    if not root.is_dir():
        raise RuntimeError(f"Controller evidence root does not exist: {root}")
    run_json_value = env.get("QF_DEV_RUN_JSON_PATH", "")
    if not run_json_value:
        raise RuntimeError("Controller did not pass the active run.json path.")
    run_json_path = Path(run_json_value).expanduser().resolve(strict=True)
    if not run_json_path.is_file():
        raise RuntimeError("Controller run.json path is not a file.")
    try:
        run_json_path.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("Controller run.json is outside this scope's evidence root.") from exc
    try:
        run_record = json.loads(
            run_json_path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON token {value}")),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"Controller run.json is unreadable: {exc}") from exc
    if not isinstance(run_record, dict):
        raise RuntimeError("Controller run.json must contain a JSON object.")
    run_identity = run_record.get("identity")
    execution_manifest = run_record.get("execution_manifest")
    case_selection = run_record.get("wp12_case_selection")
    if not isinstance(run_identity, dict):
        run_identity = {}
    if not isinstance(execution_manifest, dict):
        execution_manifest = {}
    if not isinstance(case_selection, dict):
        case_selection = {}
    attempt_number = run_record.get("attempt")
    series_id = run_record.get("series_id")
    if (
        run_record.get("controller_attempt_id") != attempt_id
        or run_record.get("state") != "RUNNING"
        or run_record.get("worktree_id") != DIAGNOSTIC_SCOPE_ID
        or run_identity.get("head") is None
        or execution_manifest.get("authorization_id") != manifest_id
        or execution_manifest.get("sha256") != manifest_sha256
        or f"{series_id}-attempt-{attempt_number}" != attempt_id
        or run_record.get("target") not in (DIAGNOSTIC_NODEID, [DIAGNOSTIC_NODEID])
        or case_selection.get("selected_dofs") != 60
    ):
        raise RuntimeError("Controller run.json does not bind this attempt, manifest, nodeid and 60-DOF selection.")
    return ControllerBinding(
        worktree_id=DIAGNOSTIC_SCOPE_ID,
        attempt_id=attempt_id,
        manifest_id=manifest_id,
        manifest_sha256=manifest_sha256,
        selected_dofs=60,
        evidence_root=root,
        run_json_path=run_json_path,
    )


def capture_solver_assembly(solver: Any, monkeypatch: Any) -> dict[str, Any]:
    """Spy on the single normal assembly path without changing returned values."""
    from solveur.loads.integration import DistributedLoadIntegrator

    capture: dict[str, Any] = {
        "stiffness_calls": 0,
        "load_calls": 0,
        "fixed_index_calls": 0,
        "face_integrations": [],
    }
    original_stiffness = solver.assembler.assemble_stiffness
    original_loads = solver.assembler.assemble_loads
    original_fixed_indices = solver.assembler.fixed_indices

    def assemble_stiffness(model: Any, dofs: Any, *, plan: Any = None) -> csr_matrix:
        matrix = original_stiffness(model, dofs, plan=plan)
        capture["stiffness_calls"] += 1
        capture["stiffness"] = matrix.copy().tocsr()
        return matrix

    def assemble_loads(model: Any, dofs: Any) -> np.ndarray:
        vector = original_loads(model, dofs)
        capture["load_calls"] += 1
        capture["loads"] = np.asarray(vector, dtype=np.float64).copy()
        return vector

    def fixed_indices(model: Any, dofs: Any) -> np.ndarray:
        indices = original_fixed_indices(model, dofs)
        capture["fixed_index_calls"] += 1
        capture["fixed_indices"] = np.asarray(indices, dtype=np.int64).copy()
        return indices

    solver.assembler.assemble_stiffness = assemble_stiffness
    solver.assembler.assemble_loads = assemble_loads
    solver.assembler.fixed_indices = fixed_indices

    original_integrate = DistributedLoadIntegrator.integrate_sparse

    def integrate_sparse(
        integrator: DistributedLoadIntegrator,
        model: Any,
        dofs: Any,
        load: Any,
        index: int,
    ) -> Any:
        integrated = original_integrate(integrator, model, dofs, load, index)
        capture["face_integrations"].append(
            {
                "index": int(index),
                "face": int(load.face),
                "indices": np.asarray(integrated.indices, dtype=np.int64).copy(),
                "values": np.asarray(integrated.values, dtype=np.float64).copy(),
                "details": dict(integrated.details),
            }
        )
        return integrated

    monkeypatch.setattr(DistributedLoadIntegrator, "integrate_sparse", integrate_sparse)
    return capture


def independent_face_load(
    nodes: np.ndarray,
    face: int,
    stress: np.ndarray,
) -> dict[str, Any]:
    """Integrate a planar QUAD8 traction from geometry, not production topology/code."""
    coordinates = np.asarray(nodes, dtype=np.float64)
    axis, sign = FACE_PLANES[face]
    plane_value = float(np.max(coordinates[:, axis]) if sign > 0 else np.min(coordinates[:, axis]))
    face_mask = np.isclose(coordinates[:, axis], plane_value, rtol=0.0, atol=1.0e-14)
    face_nodes = np.flatnonzero(face_mask)
    tangential_axes = [index for index in range(3) if index != axis]
    side_lengths = [float(np.ptp(coordinates[face_nodes, tangent_axis])) for tangent_axis in tangential_axes]
    area = float(np.prod(side_lengths))
    normal = np.zeros(3, dtype=np.float64)
    normal[axis] = float(sign)
    traction = np.asarray(stress, dtype=np.float64) @ normal
    nodal = np.zeros((coordinates.shape[0], 3), dtype=np.float64)
    corner_nodes: list[int] = []
    midside_nodes: list[int] = []
    for node in face_nodes:
        is_corner = all(
            np.isclose(
                coordinates[node, tangent_axis],
                np.min(coordinates[face_nodes, tangent_axis])
                if np.isclose(coordinates[node, tangent_axis], np.min(coordinates[face_nodes, tangent_axis]))
                else np.max(coordinates[face_nodes, tangent_axis]),
                rtol=0.0,
                atol=1.0e-14,
            )
            for tangent_axis in tangential_axes
        )
        coefficient = -area / 12.0 if is_corner else area / 3.0
        nodal[node] = coefficient * traction
        (corner_nodes if is_corner else midside_nodes).append(int(node))
    vector = nodal.ravel()
    resultant = nodal.sum(axis=0)
    moment = np.sum(np.cross(coordinates, nodal), axis=0)
    return {
        "face": face,
        "plane_axis": axis,
        "plane_value_m": plane_value,
        "normal": normal,
        "area_m2": area,
        "traction_Pa": traction,
        "corner_nodes": corner_nodes,
        "midside_nodes": midside_nodes,
        "nodal_forces_N": nodal,
        "vector_N": vector,
        "resultant_N": resultant,
        "moment_about_origin_Nm": moment,
    }


def full_sparse_vector(indices: np.ndarray, values: np.ndarray, size: int) -> np.ndarray:
    vector = np.zeros(size, dtype=np.float64)
    np.add.at(vector, np.asarray(indices, dtype=np.int64), np.asarray(values, dtype=np.float64))
    return vector


def affine_vector(nodes: np.ndarray, strain_xx: float) -> np.ndarray:
    coordinates = np.asarray(nodes, dtype=np.float64)
    return np.column_stack(
        (strain_xx * coordinates[:, 0], np.zeros(coordinates.shape[0]), np.zeros(coordinates.shape[0]))
    ).ravel()


def residual_metrics(
    stiffness: csr_matrix,
    loads: np.ndarray,
    affine: np.ndarray,
    calculated: np.ndarray | None,
    fixed_indices: np.ndarray,
) -> dict[str, Any]:
    matrix = stiffness.tocsr()
    force = np.asarray(loads, dtype=np.float64)
    u_affine = np.asarray(affine, dtype=np.float64)
    fixed = np.asarray(fixed_indices, dtype=np.int64)
    free = np.setdiff1d(np.arange(force.size, dtype=np.int64), fixed, assume_unique=True)
    ku_affine = np.asarray(matrix @ u_affine).ravel()
    r_affine = ku_affine - force
    free_matrix = matrix[free, :]
    denominator = float(np.max(np.asarray(np.abs(free_matrix).sum(axis=1)).ravel())) * float(
        np.max(np.abs(u_affine))
    ) + float(np.max(np.abs(force[free])))
    eta_inf = float(np.max(np.abs(r_affine[free]))) / denominator if denominator else 0.0
    calculated_metrics: dict[str, Any] | None = None
    if calculated is not None:
        u_calculated = np.asarray(calculated, dtype=np.float64)
        ku_calculated = np.asarray(matrix @ u_calculated).ravel()
        r_calculated = ku_calculated - force
        difference = u_calculated - u_affine
        calculated_metrics = {
            "u_calculated_m": u_calculated,
            "u_difference_from_affine_m": difference,
            "u_difference_by_dof": [
                {
                    "dof_index": int(index),
                    "node": int(index // 3),
                    "component": DOF_COMPONENTS[int(index % 3)],
                    "u_affine_m": float(u_affine[index]),
                    "u_calculated_m": float(u_calculated[index]),
                    "difference_m": float(difference[index]),
                }
                for index in range(force.size)
            ],
            "Ku_calculated_N": ku_calculated,
            "r_calculated_N": r_calculated,
            "r_calculated_free_N": r_calculated[free],
            "r_calculated_fixed_N": r_calculated[fixed],
            "r_calculated_free_norm_inf_N": float(np.max(np.abs(r_calculated[free]))),
            "r_calculated_free_norm_2_N": float(np.linalg.norm(r_calculated[free])),
        }
    return {
        "free_indices": free,
        "fixed_indices": fixed,
        "u_affine_m": u_affine,
        "Ku_affine_N": ku_affine,
        "r_affine_N": r_affine,
        "r_affine_free_N": r_affine[free],
        "r_affine_fixed_N": r_affine[fixed],
        "r_affine_free_norm_inf_N": float(np.max(np.abs(r_affine[free]))),
        "r_affine_free_norm_2_N": float(np.linalg.norm(r_affine[free])),
        "r_affine_eta_inf": eta_inf,
        "calculated": calculated_metrics,
    }


def csr_archive(matrix: csr_matrix) -> dict[str, Any]:
    canonical = matrix.tocsr(copy=True)
    canonical.sum_duplicates()
    canonical.sort_indices()
    digest = hashlib.sha256()
    digest.update(np.asarray(canonical.shape, dtype=np.int64).tobytes())
    for values in (canonical.indptr, canonical.indices, canonical.data):
        digest.update(np.ascontiguousarray(values).tobytes())
    return {
        "shape": list(canonical.shape),
        "nnz": int(canonical.nnz),
        "indptr": canonical.indptr,
        "indices": canonical.indices,
        "data": canonical.data,
        "sha256_canonical_csr": digest.hexdigest(),
        "canonicalization": "CSR copy, sum_duplicates, sort_indices; SHA256(shape:int64||indptr||indices||data)",
    }


def write_diagnostic_sidecar(
    *,
    binding: ControllerBinding,
    nodeid: str,
    model: Any,
    case_parameters: dict[str, Any],
    source_paths: list[Path],
    repo_root: Path,
    capture: dict[str, Any],
    result: Any | None,
    solve_seconds: float,
    exception: Exception | None,
    affine_data: dict[str, Any] | None,
    independent_faces: list[dict[str, Any]],
) -> tuple[Path, str]:
    """Archive all available raw and derived observations atomically before assertions."""
    matrix = capture.get("stiffness")
    loads = capture.get("loads")
    fixed = capture.get("fixed_indices")
    calculated = None if result is None else np.asarray(result.displacements, dtype=np.float64)
    residuals = None
    if matrix is not None and loads is not None and fixed is not None and affine_data is not None:
        residuals = residual_metrics(matrix, loads, affine_data["u_affine_m"], calculated, fixed)
    stiffness_oracle = None
    if residuals is not None and affine_data is not None:
        expected_boundary = np.asarray(affine_data["all_six_analytic_boundary_loads_N"], dtype=np.float64)
        stiffness_difference = np.asarray(residuals["Ku_affine_N"], dtype=np.float64) - expected_boundary
        stiffness_free = residuals["free_indices"]
        free_matrix = matrix[stiffness_free, :]
        stiffness_denominator = float(np.max(np.asarray(np.abs(free_matrix).sum(axis=1)).ravel())) * float(
            np.max(np.abs(np.asarray(affine_data["u_affine_m"], dtype=np.float64)))
        ) + float(np.max(np.abs(expected_boundary[stiffness_free])))
        stiffness_eta_inf = (
            float(np.max(np.abs(stiffness_difference[stiffness_free]))) / stiffness_denominator
            if stiffness_denominator
            else 0.0
        )
        stiffness_oracle = {
            "expected_all_face_boundary_vector_N": expected_boundary,
            "Ku_affine_minus_all_face_boundary_N": stiffness_difference,
            "free_indices": residuals["free_indices"],
            "fixed_indices": residuals["fixed_indices"],
            "difference_free_N": stiffness_difference[residuals["free_indices"]],
            "difference_fixed_N": stiffness_difference[residuals["fixed_indices"]],
            "difference_norm_inf_N": float(np.max(np.abs(stiffness_difference))),
            "difference_free_norm_inf_N": float(np.max(np.abs(stiffness_difference[residuals["free_indices"]]))),
            "free_backward_error_eta_inf": stiffness_eta_inf,
            "interpretation": "Independent continuum-traction/QUAD8 nodal-force oracle for K @ u_affine.",
        }

    face_records = []
    for actual, expected in zip(capture.get("face_integrations", []), independent_faces, strict=False):
        actual_vector = full_sparse_vector(actual["indices"], actual["values"], 60)
        expected_vector = np.asarray(expected["vector_N"], dtype=np.float64)
        face_records.append(
            {
                "face": actual["face"],
                "load_index": actual["index"],
                "production_sparse": {"indices": actual["indices"], "values_N": actual["values"]},
                "production_dense_N": actual_vector,
                "production_details": actual["details"],
                "independent_oracle": expected,
                "production_minus_oracle_N": actual_vector - expected_vector,
                "difference_norm_inf_N": float(np.max(np.abs(actual_vector - expected_vector))),
            }
        )

    record = {
        "schema": "qfsolver-wp12b-hex20-affine-diagnostic-v1",
        "stage": "PRE_ASSERTION_DIAGNOSTIC_CAPTURE",
        "controller": {
            "worktree_id": binding.worktree_id,
            "selected_dofs": binding.selected_dofs,
            "controller_attempt_id": binding.attempt_id,
            "manifest_id": binding.manifest_id,
            "manifest_sha256": binding.manifest_sha256,
            "evidence_root": str(binding.evidence_root),
            "run_json_path": str(binding.run_json_path),
            "run_json_link_contract": (
                "The official runner must record this exact attempt ID and manifest identity in run.json, "
                "then add this sidecar path and SHA-256 to the final run.json."
            ),
        },
        "identity": {
            "nodeid": nodeid,
            "sources": _source_identity(source_paths, repo_root),
            "model": _model_identity(model, case_parameters),
        },
        "units": case_parameters["units"],
        "model": {
            "nodes_m": np.asarray(model.nodes, dtype=np.float64),
            "elements": [
                {"type": item.type, "nodes": list(item.nodes), "material": item.material} for item in model.elements
            ],
            "fixed_dofs_declared": [{"node": item.node, "dofs": list(item.dofs)} for item in model.fixed_dofs],
            "selected_dofs": 60,
            "global_dof_order": [
                {
                    "dof_index": 3 * node + component_index,
                    "node": node,
                    "component": component,
                }
                for node in range(20)
                for component_index, component in enumerate(DOF_COMPONENTS)
            ],
            "fixed_indices_captured": fixed,
            "free_indices": None if residuals is None else residuals["free_indices"],
            "parameters": case_parameters,
        },
        "assembly": {
            "stiffness_call_count": capture["stiffness_calls"],
            "load_call_count": capture["load_calls"],
            "fixed_index_call_count": capture["fixed_index_calls"],
            "K_csr": None if matrix is None else csr_archive(matrix),
            "F_N": loads,
            "face_contributions": face_records,
            "F_minus_sum_of_production_faces_N": (
                None
                if loads is None
                else np.asarray(loads, dtype=np.float64)
                - sum((row["production_dense_N"] for row in face_records), start=np.zeros(60))
            ),
        },
        "affine_oracle": affine_data,
        "stiffness_oracle": stiffness_oracle,
        "residuals": residuals,
        "result": {
            "status": None if result is None else result.status,
            "displacements_m": calculated,
            "reactions_N": None if result is None else result.audit.equilibrium.get("reactions"),
            "equilibrium": None if result is None else result.audit.equilibrium,
            "energy": (
                None
                if result is None
                else {
                    "strain_energy_J": result.audit.equilibrium.get("secant_internal_energy"),
                    "external_work_J": result.audit.equilibrium.get("external_work_at_final_load"),
                    "linear_energy_identity_relative_error": result.audit.equilibrium.get(
                        "linear_energy_identity_relative_error"
                    ),
                }
            ),
            "mesh": (
                None
                if result is None
                else {
                    "node_count": result.node_count,
                    "element_count": result.element_count,
                    "mesh_status": result.audit.mesh_status,
                    "mesh_details": result.audit.mesh_details,
                    "element_quality": result.audit.diagnostic.get("element_quality", {}),
                }
            ),
            "solver": None if result is None else result.solver,
        },
        "attempt": {
            "solve_invocations": 1,
            "solve_wall_seconds": float(solve_seconds),
            "exception_type": None if exception is None else type(exception).__name__,
            "exception_message": None if exception is None else str(exception),
        },
        "diagnostic_criteria": {
            "proposed_owner_limits": {
                "free_affine_backward_error_eta_inf_max": 1.0e-10,
                "face_nodal_force_rtol": 1.0e-12,
                "face_nodal_force_atol_N": 1.0e-6,
            },
            "independent_stiffness_oracle": "archived for review; no acceptance threshold assigned",
            "historical_r4_displacement_acceptance": {
                "rtol": 1.0e-10,
                "atol_m": 1.0e-13,
            },
            "status": "OWNER_DECISION_PENDING; no execution authorization",
        },
    }
    directory = binding.evidence_root / "wp12b_hex20_affine_diagnostic"
    path = directory / f"{binding.attempt_id}.json"
    _atomic_json_no_overwrite(path, record)
    sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    return path, sha256
