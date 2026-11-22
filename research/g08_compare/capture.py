"""Development-only G08 matrix capture and archive validation helpers."""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import numpy as np
from scipy.sparse import csr_matrix

HERE = Path(__file__).resolve().parent
CAPTURE_CONTRACT = HERE / "first-mode-capture-contract-2026-11-22.json"
CAPTURE_SCOPE_IDS = {
    "g08-tet10-before-capture-001",
    "g08-tet10-after-capture-001",
}
_DOFS = ("UX", "UY", "UZ")


class CaptureError(ValueError):
    """A capture did not match its frozen source, input, or archive contract."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_capture_contract() -> dict[str, Any]:
    try:
        value = json.loads(CAPTURE_CONTRACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CaptureError("G08 matrix-capture contract is unreadable") from exc
    if (
        value.get("schema") != "qf-g08-first-mode-capture-contract-v1"
        or value.get("status") != "DEVELOPMENT_AUTONOMOUS_AUTHORIZED"
        or value.get("authorization", {}).get("attempts_per_source") != 1
        or value.get("authorization", {}).get("automatic_retry") is not False
    ):
        raise CaptureError("G08 matrix-capture contract is not a fresh one-attempt authorization")
    return value


def _matrix_digest(matrix: csr_matrix) -> str:
    value = matrix.tocsr(copy=True)
    digest = hashlib.sha256()
    for part in (np.asarray(value.shape, dtype="<i8"), value.indptr, value.indices, value.data):
        array = np.ascontiguousarray(part)
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(np.asarray(array.shape, dtype="<i8").tobytes())
        digest.update(array.tobytes())
    return digest.hexdigest()


def _symmetry_defect(matrix: csr_matrix) -> float:
    difference = (matrix - matrix.T).tocsr()
    numerator = float(np.max(np.abs(difference.data))) if difference.nnz else 0.0
    scale = float(np.max(np.abs(matrix.data))) if matrix.nnz else 0.0
    return numerator / max(scale, np.finfo(float).tiny)


def _matrix_metadata(matrix: csr_matrix) -> dict[str, Any]:
    return {
        "shape": [int(item) for item in matrix.shape],
        "nnz": int(matrix.nnz),
        "dtype": matrix.dtype.str,
        "sha256_canonical_csr": _matrix_digest(matrix),
        "symmetry_defect_relative_max_entry": _symmetry_defect(matrix),
        "finite": bool(np.isfinite(matrix.data).all()),
    }


def _dof_map(model: Any) -> tuple[np.ndarray, np.ndarray, list[str]]:
    dofs = model.dof_manager()
    indexed = sorted(
        (int(dofs.index(node, component)), node, component)
        for node in range(int(np.asarray(model.nodes).shape[0]))
        for component in _DOFS
    )
    if [item[0] for item in indexed] != list(range(int(dofs.ndof))):
        raise CaptureError("model degree-of-freedom indexing is not a complete 3-DOF node map")
    labels = [f"{node}:{component}" for _, node, component in indexed]
    fixed = np.unique(
        [dofs.index(condition.node, name) for condition in model.fixed_dofs for name in condition.dofs]
    ).astype(np.int64)
    free = np.setdiff1d(np.arange(int(dofs.ndof), dtype=np.int64), fixed)
    return fixed, free, labels


def write_matrix_archive(
    path: Path,
    *,
    k0: csr_matrix,
    kg: csr_matrix,
    u_pre: np.ndarray,
    fixed: np.ndarray,
    free: np.ndarray,
    labels: list[str] | np.ndarray,
) -> Path:
    """Serialize the exact captured CSR arrays and their DOF correspondence."""
    k0_csr, kg_csr = k0.tocsr(copy=True), kg.tocsr(copy=True)
    np.savez_compressed(
        path,
        k0_data=k0_csr.data,
        k0_indices=k0_csr.indices.astype(np.int64, copy=False),
        k0_indptr=k0_csr.indptr.astype(np.int64, copy=False),
        k0_shape=np.asarray(k0_csr.shape, dtype=np.int64),
        kg_data=kg_csr.data,
        kg_indices=kg_csr.indices.astype(np.int64, copy=False),
        kg_indptr=kg_csr.indptr.astype(np.int64, copy=False),
        kg_shape=np.asarray(kg_csr.shape, dtype=np.int64),
        u_pre=np.asarray(u_pre, dtype=np.float64),
        fixed_dof_indices=np.asarray(fixed, dtype=np.int64),
        free_dof_indices=np.asarray(free, dtype=np.int64),
        dof_labels=np.asarray(labels, dtype="U32"),
    )
    return path


def read_matrix_archive(path: Path) -> dict[str, Any]:
    """Read captured CSR matrices and vectors without permitting pickle data."""
    with np.load(path, allow_pickle=False) as arrays:
        required = {
            "k0_data", "k0_indices", "k0_indptr", "k0_shape", "kg_data", "kg_indices",
            "kg_indptr", "kg_shape", "u_pre", "fixed_dof_indices", "free_dof_indices", "dof_labels",
        }
        if set(arrays.files) != required:
            raise CaptureError("matrices.npz has missing or unexpected arrays")
        return {
            "K0": _load_csr(arrays, "k0"),
            "Kg": _load_csr(arrays, "kg"),
            "u_pre": np.asarray(arrays["u_pre"], dtype=np.float64),
            "fixed_dof_indices": np.asarray(arrays["fixed_dof_indices"], dtype=np.int64),
            "free_dof_indices": np.asarray(arrays["free_dof_indices"], dtype=np.int64),
            "dof_labels": np.asarray(arrays["dof_labels"]),
        }


class _SolverObserver:
    """Observe the exact buckling calls while preserving all returned objects."""

    def __init__(self, model: Any):
        self.model = model
        self.preload_returned = False
        self.preload_calls = 0
        self.k0_calls = 0
        self.kg_calls = 0
        self.u_pre: np.ndarray | None = None
        self.preload_diagnostics: dict[str, Any] | None = None
        self.full_k0: csr_matrix | None = None
        self.full_kg: csr_matrix | None = None
        self.solve_result: Any = None
        self._assembly_restore: tuple[Any, Any, Any] | None = None

    @contextmanager
    def installed(self):
        from solveur.core.analyses import buckling

        original_newton = buckling.solve_full_newton
        original_builder = buckling.build_total_lagrangian_assembly

        def observe_newton(*args: Any, **kwargs: Any):
            self.preload_calls += 1
            result = original_newton(*args, **kwargs)
            displacement, diagnostics = result
            self.u_pre = np.array(displacement, dtype=np.float64, copy=True)
            self.preload_diagnostics = deepcopy(diagnostics)
            self.preload_returned = True
            return result

        def observe_builder(model: Any):
            assembly = original_builder(model)
            if model is not self.model:
                return assembly
            original_assemble = assembly.assemble
            original_geometric = assembly.geometric_tangent

            def observe_assemble(displacement: np.ndarray, *args: Any, **kwargs: Any):
                result = original_assemble(displacement, *args, **kwargs)
                if self.preload_returned and self.full_k0 is None:
                    value = np.asarray(displacement, dtype=np.float64)
                    if value.shape == (int(assembly.ndof),) and np.count_nonzero(value) == 0:
                        tangent = result[1]
                        if tangent is None:
                            raise CaptureError("zero-state assembly did not return K0")
                        self.k0_calls += 1
                        self.full_k0 = csr_matrix(tangent, dtype=np.float64, copy=True)
                return result

            def observe_geometric(displacement: np.ndarray):
                result = original_geometric(displacement)
                if self.preload_returned and self.full_kg is None:
                    value = np.asarray(displacement, dtype=np.float64)
                    if self.u_pre is None or not np.array_equal(value, self.u_pre):
                        raise CaptureError("Kg was not evaluated at the captured converged preload state")
                    self.kg_calls += 1
                    self.full_kg = csr_matrix(result, dtype=np.float64, copy=True)
                return result

            assembly.assemble = observe_assemble
            assembly.geometric_tangent = observe_geometric
            self._assembly_restore = (assembly, original_assemble, original_geometric)
            return assembly

        buckling.solve_full_newton = observe_newton
        buckling.build_total_lagrangian_assembly = observe_builder
        try:
            yield self
        finally:
            buckling.solve_full_newton = original_newton
            buckling.build_total_lagrangian_assembly = original_builder
            if self._assembly_restore is not None:
                assembly, original_assemble, original_geometric = self._assembly_restore
                assembly.assemble = original_assemble
                assembly.geometric_tangent = original_geometric

    def call_solver(self, solve: Any, model: Any):
        result = solve(model)
        self.solve_result = result
        return result

    def matrices(self, free: np.ndarray) -> tuple[csr_matrix, csr_matrix]:
        if (
            self.preload_calls != 1
            or self.k0_calls != 1
            or self.kg_calls != 1
            or self.u_pre is None
            or self.full_k0 is None
            or self.full_kg is None
        ):
            raise CaptureError("instrumentation did not observe exactly one preload, K0, and Kg call")
        return (
            self.full_k0[free, :][:, free].tocsr(),
            self.full_kg[free, :][:, free].tocsr(),
        )


def capture_case(model: Any, receipt: Mapping[str, Any], output: Path, solve: Any) -> dict[str, Any]:
    """Run the existing public solve once and archive the observed matrices."""
    from research.g08_compare.case import solve_one

    scope_id = str(receipt["scope"])
    scope = _scope(scope_id)
    fixed, free, labels = _dof_map(model)
    if len(free) != int(scope["free_dofs"]) or len(fixed) + len(free) != len(labels):
        raise CaptureError("captured free/fixed degree-of-freedom map differs from the registered scope")
    output.mkdir(parents=True, exist_ok=True)
    observer = _SolverObserver(model)
    with observer.installed():
        result_payload = solve_one(model, receipt, output, lambda current: observer.call_solver(solve, current))
    if observer.solve_result is None or observer.u_pre is None or observer.preload_diagnostics is None:
        raise CaptureError("public solver did not complete the registered G08 preload and spectral path")
    k0, kg = observer.matrices(free)
    if not np.isfinite(k0.data).all() or not np.isfinite(kg.data).all() or not np.isfinite(observer.u_pre).all():
        raise CaptureError("captured preload vector or reduced matrices contain non-finite values")
    matrix_path = output / "matrices.npz"
    write_matrix_archive(
        matrix_path,
        k0=k0,
        kg=kg,
        u_pre=observer.u_pre,
        fixed=fixed,
        free=free,
        labels=labels,
    )
    mode_path = output / "mode.npy"
    mode = np.load(mode_path, allow_pickle=False)
    result = observer.solve_result
    diagnostics = result.solver
    if result_payload.get("solver_status") != "PASS":
        raise CaptureError("matrix capture requires a completed candidate solve")
    contract = load_capture_contract()
    case_key = "before" if "before" in scope_id else "after"
    case_contract = contract["cases"][case_key]
    capture_metadata = {
        "schema": "qf-g08-matrix-capture-v1",
        "scope": scope_id,
        "source": scope["source"],
        "source_tree": scope["source_tree"],
        "solver_tree": scope["solver_tree"],
        "generator_blob": scope["generator_blob"],
        "inputs_sha256": scope["inputs"],
        "mesh_sha256": scope["mesh"],
        "compatibility": receipt["compatibility"],
        "node_count": int(scope["nodes"]),
        "element_count": int(scope["elements"]),
        "full_dof_count": len(labels),
        "fixed_dof_count": int(fixed.size),
        "free_dof_count": int(free.size),
        "dof_order": "index order from model.dof_manager(); labels are node-index:UX|UY|UZ",
        "units": contract["model_and_sign_convention"]["units"],
        "sign_convention": contract["model_and_sign_convention"]["pencil"],
        "assembled_full_nnz": {
            "K0": int(observer.full_k0.nnz),
            "Kg": int(observer.full_kg.nnz),
        },
        "preload": {
            "status": "CONVERGED" if observer.preload_diagnostics.get("converged") is True else "NON_CONVERGED",
            "diagnostics": observer.preload_diagnostics,
            "u_pre_sha256": sha256_bytes(np.ascontiguousarray(observer.u_pre).tobytes()),
            "u_pre_shape": list(observer.u_pre.shape),
        },
        "matrices": {"K0": _matrix_metadata(k0), "Kg": _matrix_metadata(kg)},
        "candidate": {
            "factor": float(diagnostics["critical_factor"]),
            "residual_relative_solver": float(diagnostics["critical_mode_residual_relative"]),
            "bracket": diagnostics["critical_bracket"],
            "mode_sha256": sha256_file(mode_path),
            "mode_shape": list(mode.shape),
            "mode_norm": float(np.linalg.norm(mode)),
            "first_mode_status": "FIRST_MODE_NOT_ESTABLISHED",
            "historical_reference": case_contract["historical_candidate"],
        },
        "instrumentation": {
            "method": "temporary observers around existing buckling module calls",
            "solve_full_newton_calls": observer.preload_calls,
            "zero_state_K0_calls_after_preload": observer.k0_calls,
            "preload_state_Kg_calls": observer.kg_calls,
            "returned_solver_objects_modified": False,
            "production_solver_source_modified": False,
        },
        "runtime": {
            "python": sys.version,
            "numpy": np.__version__,
            "scipy": __import__("scipy").__version__,
            "elapsed_capture_includes_solve": True,
        },
        "files": {
            "matrices.npz": {"size_bytes": matrix_path.stat().st_size, "sha256": sha256_file(matrix_path)},
            "mode.npy": {"size_bytes": mode_path.stat().st_size, "sha256": sha256_file(mode_path)},
        },
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "first_mode_status": "FIRST_MODE_NOT_ESTABLISHED",
    }
    (output / "capture.json").write_text(
        json.dumps(capture_metadata, sort_keys=True, indent=2, allow_nan=False), encoding="utf-8"
    )
    return capture_metadata


def _scope(scope_id: str) -> dict[str, Any]:
    from research.g08_compare.controlled import scope_for

    return scope_for(scope_id)


def _load_csr(archive: Any, prefix: str) -> csr_matrix:
    shape = tuple(int(value) for value in archive[f"{prefix}_shape"])
    return csr_matrix(
        (
            np.asarray(archive[f"{prefix}_data"], dtype=np.float64),
            np.asarray(archive[f"{prefix}_indices"], dtype=np.int64),
            np.asarray(archive[f"{prefix}_indptr"], dtype=np.int64),
        ),
        shape=shape,
    )


def validate_capture_bundle(
    result_root: Path,
    *,
    scope: Mapping[str, Any],
    receipt: Mapping[str, Any],
    result: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate capture identity, hashes, CSR structure, and finite DOF data."""
    metadata_path, matrix_path, mode_path = (
        result_root / "capture.json",
        result_root / "matrices.npz",
        result_root / "mode.npy",
    )
    if not all(path.is_file() for path in (metadata_path, matrix_path, mode_path)):
        raise CaptureError("capture.json, matrices.npz, or mode.npy is missing")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    identity = {
        "scope": scope["id"],
        "source": scope["source"],
        "inputs_sha256": scope["inputs"],
        "mesh_sha256": scope["mesh"],
    }
    if metadata.get("schema") != "qf-g08-matrix-capture-v1" or any(metadata.get(k) != v for k, v in identity.items()):
        raise CaptureError("capture identity differs from the registered source and input")
    if any(
        metadata.get(metadata_key) != scope.get(scope_key)
        for metadata_key, scope_key in (
            ("source_tree", "source_tree"),
            ("solver_tree", "solver_tree"),
            ("generator_blob", "generator_blob"),
        )
    ):
        raise CaptureError("capture source tree or module identity differs from the registered scope")
    if (
        receipt.get("scope") != scope["id"]
        or receipt.get("source") != scope["source"]
        or receipt.get("inputs_sha256") != scope["inputs"]
        or metadata.get("free_dof_count") != int(scope["free_dofs"])
        or metadata.get("node_count") != int(scope["nodes"])
        or metadata.get("element_count") != int(scope["elements"])
    ):
        raise CaptureError("captured model or degree-of-freedom count differs from the registered receipt")
    for name, path in (("matrices.npz", matrix_path), ("mode.npy", mode_path)):
        expected = metadata.get("files", {}).get(name, {})
        if expected.get("size_bytes") != path.stat().st_size or expected.get("sha256") != sha256_file(path):
            raise CaptureError(f"captured file identity mismatch: {name}")
    try:
        values = read_matrix_archive(matrix_path)
        k0, kg = values["K0"], values["Kg"]
        u_pre = values["u_pre"]
        fixed, free, labels = values["fixed_dof_indices"], values["free_dof_indices"], values["dof_labels"]
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        if isinstance(exc, CaptureError):
            raise
        raise CaptureError("matrices.npz cannot be loaded without pickle") from exc
    ndof = int(scope["nodes"]) * 3
    expected_labels = np.asarray(
        [f"{index // 3}:{_DOFS[index % 3]}" for index in range(ndof)], dtype="U32"
    )
    expected_free = np.setdiff1d(np.arange(ndof, dtype=np.int64), fixed)
    if (
        k0.shape != (int(scope["free_dofs"]),) * 2
        or kg.shape != k0.shape
        or u_pre.shape != (ndof,)
        or labels.shape != (ndof,)
        or not np.isfinite(u_pre).all()
        or not np.isfinite(k0.data).all()
        or not np.isfinite(kg.data).all()
        or fixed.size + free.size != ndof
        or len(np.unique(np.concatenate((fixed, free)))) != ndof
        or not np.array_equal(np.sort(np.concatenate((fixed, free))), np.arange(ndof, dtype=np.int64))
        or labels.dtype.kind != "U"
        or not np.array_equal(labels, expected_labels)
        or not np.array_equal(fixed, np.unique(fixed))
        or not np.array_equal(free, expected_free)
        or np.any(free < 0)
        or np.any(free >= ndof)
    ):
        raise CaptureError("captured CSR matrices or DOF correspondence has an invalid shape or value")
    for name, matrix in (("K0", k0), ("Kg", kg)):
        recorded = metadata.get("matrices", {}).get(name, {})
        if (
            recorded.get("sha256_canonical_csr") != _matrix_digest(matrix)
            or recorded.get("shape") != list(matrix.shape)
            or recorded.get("nnz") != int(matrix.nnz)
            or recorded.get("finite") is not True
        ):
            raise CaptureError(f"captured {name} metadata differs from its CSR entries")
    if (
        metadata.get("instrumentation", {}).get("solve_full_newton_calls") != 1
        or metadata.get("instrumentation", {}).get("zero_state_K0_calls_after_preload") != 1
        or metadata.get("instrumentation", {}).get("preload_state_Kg_calls") != 1
        or metadata.get("instrumentation", {}).get("returned_solver_objects_modified") is not False
        or metadata.get("first_mode_status") != "FIRST_MODE_NOT_ESTABLISHED"
        or metadata.get("candidate", {}).get("factor") != result.get("factor")
        or metadata.get("candidate", {}).get("residual_relative_solver") != result.get("residual")
        or metadata.get("candidate", {}).get("mode_sha256") != result.get("mode_sha256")
        or metadata.get("preload", {}).get("status") != "CONVERGED"
        or metadata.get("preload", {}).get("diagnostics") != result.get("diagnostics", {}).get("preload_diagnostics")
        or metadata.get("assembled_full_nnz", {}).get("K0") != result.get("diagnostics", {}).get("initial_tangent_nnz")
        or metadata.get("assembled_full_nnz", {}).get("Kg") != result.get("diagnostics", {}).get("geometric_tangent_nnz")
    ):
        raise CaptureError("capture call counts or solve/preload result binding is invalid")
    return {
        "capture_validation": "VALID",
        "capture_files": ["capture.json", "matrices.npz", "mode.npy"],
        "captured_k0_shape": list(k0.shape),
        "captured_kg_shape": list(kg.shape),
        "captured_k0_sha256": metadata["matrices"]["K0"]["sha256_canonical_csr"],
        "captured_kg_sha256": metadata["matrices"]["Kg"]["sha256_canonical_csr"],
        "captured_u_pre_sha256": metadata["preload"]["u_pre_sha256"],
        "capture_symmetry_defects": {
            "K0": metadata["matrices"]["K0"]["symmetry_defect_relative_max_entry"],
            "Kg": metadata["matrices"]["Kg"]["symmetry_defect_relative_max_entry"],
        },
        "first_mode_status": "FIRST_MODE_NOT_ESTABLISHED",
    }
