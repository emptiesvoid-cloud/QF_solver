"""Synthetic tests for G08 matrix serialization and capture binding."""

import json
from pathlib import Path
import sys
from types import SimpleNamespace
from types import ModuleType

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from research.g08_compare import capture


def _synthetic_scope():
    return {
        "id": "g08-tet10-before-capture-001",
        "source": "a" * 40,
        "source_tree": "b" * 40,
        "solver_tree": "c" * 40,
        "generator_blob": "d" * 40,
        "inputs": "e" * 64,
        "mesh": "f" * 64,
        "nodes": 2,
        "elements": 1,
        "free_dofs": 3,
    }


def _write_bundle(root: Path):
    scope = _synthetic_scope()
    receipt = {"scope": scope["id"], "source": scope["source"], "inputs_sha256": scope["inputs"]}
    root.mkdir()
    k0 = csr_matrix([[4.0, 1.0, 0.0], [1.0, 3.0, 0.0], [0.0, 0.0, 2.0]])
    kg = csr_matrix([[-1.0, 0.0, 0.0], [0.0, -2.0, 0.0], [0.0, 0.0, -3.0]])
    u_pre = np.asarray([0.0, 0.0, 0.0, 1e-4, 2e-4, 3e-4])
    fixed, free = np.asarray([0, 1, 2]), np.asarray([3, 4, 5])
    labels = np.asarray(["0:UX", "0:UY", "0:UZ", "1:UX", "1:UY", "1:UZ"], dtype="U32")
    matrix_path = capture.write_matrix_archive(
        root / "matrices.npz", k0=k0, kg=kg, u_pre=u_pre, fixed=fixed, free=free, labels=labels
    )
    mode_path = root / "mode.npy"
    np.save(mode_path, np.asarray([0.0, 0.0, 0.0, 1.0, 0.0, 0.0]), allow_pickle=False)
    preload = {"converged": True, "increments": []}
    result = {
        "factor": 2.5,
        "residual": 1e-10,
        "mode_sha256": capture.sha256_file(mode_path),
        "diagnostics": {
            "preload_diagnostics": preload,
            "initial_tangent_nnz": 5,
            "geometric_tangent_nnz": 3,
        },
    }
    capture_metadata = {
        "schema": "qf-g08-matrix-capture-v1",
        "scope": scope["id"],
        "source": scope["source"],
        "inputs_sha256": scope["inputs"],
        "mesh_sha256": scope["mesh"],
        "source_tree": scope["source_tree"],
        "solver_tree": scope["solver_tree"],
        "generator_blob": scope["generator_blob"],
        "node_count": 2,
        "element_count": 1,
        "free_dof_count": 3,
        "files": {
            "matrices.npz": {"size_bytes": matrix_path.stat().st_size, "sha256": capture.sha256_file(matrix_path)},
            "mode.npy": {"size_bytes": mode_path.stat().st_size, "sha256": capture.sha256_file(mode_path)},
        },
        "matrices": {"K0": capture._matrix_metadata(k0), "Kg": capture._matrix_metadata(kg)},
        "assembled_full_nnz": {"K0": 5, "Kg": 3},
        "instrumentation": {
            "solve_full_newton_calls": 1,
            "zero_state_K0_calls_after_preload": 1,
            "preload_state_Kg_calls": 1,
            "returned_solver_objects_modified": False,
        },
        "candidate": {"factor": result["factor"], "residual_relative_solver": result["residual"], "mode_sha256": result["mode_sha256"]},
        "preload": {"status": "CONVERGED", "diagnostics": preload, "u_pre_sha256": capture.sha256_bytes(u_pre.tobytes())},
        "first_mode_status": "FIRST_MODE_NOT_ESTABLISHED",
    }
    (root / "capture.json").write_text(json.dumps(capture_metadata), encoding="utf-8")
    (root / "result.json").write_text(json.dumps(result), encoding="utf-8")
    return scope, receipt, result


def test_synthetic_csr_capture_round_trip_and_valid_archive(tmp_path):
    root = tmp_path / "valid"
    scope, receipt, result = _write_bundle(root)
    loaded = capture.read_matrix_archive(root / "matrices.npz")
    np.testing.assert_array_equal(loaded["K0"].toarray(), [[4, 1, 0], [1, 3, 0], [0, 0, 2]])
    np.testing.assert_array_equal(loaded["Kg"].diagonal(), [-1, -2, -3])
    np.testing.assert_array_equal(loaded["free_dof_indices"], [3, 4, 5])
    verdict = capture.validate_capture_bundle(root, scope=scope, receipt=receipt, result=result)
    assert verdict["capture_validation"] == "VALID"
    assert verdict["capture_symmetry_defects"] == {"K0": 0.0, "Kg": 0.0}


@pytest.mark.parametrize(
    ("field", "bad_dtype"),
    [
        ("k0_data", np.complex128),
        ("k0_data", np.float32),
        ("kg_data", np.complex128),
        ("u_pre", np.complex128),
        ("k0_indices", np.float64),
        ("free_dof_indices", np.float32),
    ],
)
def test_matrix_archive_rejects_lossy_dtype_normalization(tmp_path, field, bad_dtype):
    root = tmp_path / f"{field}-{np.dtype(bad_dtype).name}"
    _write_bundle(root)
    with np.load(root / "matrices.npz", allow_pickle=False) as archive:
        arrays = {name: np.array(archive[name], copy=True) for name in archive.files}
    arrays[field] = arrays[field].astype(bad_dtype)
    if np.issubdtype(np.dtype(bad_dtype), np.complexfloating):
        arrays[field] += 1j
    np.savez_compressed(root / "matrices.npz", **arrays)

    with pytest.raises(capture.CaptureError, match="dtype"):
        capture.read_matrix_archive(root / "matrices.npz")


@pytest.mark.parametrize("dtype", [np.complex128, np.float32])
def test_mode_reader_rejects_lossy_dtype_normalization(tmp_path, dtype):
    mode_path = tmp_path / "mode.npy"
    mode = np.asarray([1.0, 2.0], dtype=dtype)
    if np.issubdtype(np.dtype(dtype), np.complexfloating):
        mode += 3j
    np.save(mode_path, mode, allow_pickle=False)

    with pytest.raises(capture.CaptureError, match="binary64"):
        capture.read_mode_vector(mode_path)


@pytest.mark.parametrize("mutation", ["missing", "incomplete", "altered", "identity"])
def test_capture_validator_rejects_invalid_synthetic_archives(tmp_path, mutation):
    root = tmp_path / mutation
    scope, receipt, result = _write_bundle(root)
    if mutation == "missing":
        (root / "matrices.npz").unlink()
    elif mutation == "incomplete":
        np.savez_compressed(root / "matrices.npz", unexpected=np.asarray([1.0]))
    elif mutation == "altered":
        arrays = dict(np.load(root / "matrices.npz", allow_pickle=False))
        arrays["k0_data"] = arrays["k0_data"].copy()
        arrays["k0_data"][0] += 1.0
        np.savez_compressed(root / "matrices.npz", **arrays)
    else:
        receipt = {**receipt, "inputs_sha256": "0" * 64}
    with pytest.raises(capture.CaptureError):
        capture.validate_capture_bundle(root, scope=scope, receipt=receipt, result=result)


def test_synthetic_instrumentation_preserves_solver_return_and_reduces_matrices(tmp_path, monkeypatch):
    scope = {**_synthetic_scope(), "nodes": 2, "elements": 1, "free_dofs": 3}
    monkeypatch.setattr(capture, "_scope", lambda _scope_id: scope)
    buckling = ModuleType("buckling")
    analyses = ModuleType("solveur.core.analyses")
    analyses.buckling = buckling
    core = ModuleType("solveur.core")
    core.analyses = analyses
    solveur = ModuleType("solveur")
    solveur.core = core
    monkeypatch.setitem(sys.modules, "solveur", solveur)
    monkeypatch.setitem(sys.modules, "solveur.core", core)
    monkeypatch.setitem(sys.modules, "solveur.core.analyses", analyses)

    class Dofs:
        ndof = 6

        @staticmethod
        def index(node, component):
            return 3 * node + {"UX": 0, "UY": 1, "UZ": 2}[component]

    model = SimpleNamespace(
        nodes=np.zeros((2, 3)),
        dof_manager=lambda: Dofs(),
        fixed_dofs=[SimpleNamespace(node=0, dofs=("UX", "UY", "UZ"))],
    )
    k0_full = csr_matrix(np.diag([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]))
    kg_full = csr_matrix(np.diag([0.0, 0.0, 0.0, -1.0, -2.0, -3.0]))
    u_pre = np.asarray([0.0, 0.0, 0.0, 1e-4, 2e-4, 3e-4])
    preload = {"converged": True, "increments": [{"load_factor": value, "relative_residual": 1e-12} for value in (0.25, 0.5, 0.75, 1.0)]}

    class Assembly:
        ndof = 6

        @staticmethod
        def assemble(displacement):
            return np.zeros(6), k0_full

        @staticmethod
        def geometric_tangent(displacement):
            return kg_full

    buckling.build_total_lagrangian_assembly = lambda _model: Assembly()
    buckling.solve_full_newton = lambda *args, **kwargs: (u_pre, preload)

    def public_solve(_model):
        assembly = buckling.build_total_lagrangian_assembly(_model)
        displacement, _diagnostics = buckling.solve_full_newton(assembly, np.zeros(6), np.arange(3), increments=4, tolerance=1e-8, max_iterations=30)
        _internal, _tangent = assembly.assemble(np.zeros(6))
        assembly.geometric_tangent(displacement)
        diagnostics = {
            "critical_factor": 10.0,
            "critical_mode_residual_relative": 1e-10,
            "critical_bracket": {"lower": 9.0, "upper": 11.0, "method": "synthetic"},
            "backend": "synthetic",
            "preload_diagnostics": preload,
        }
        return SimpleNamespace(status="PASS", solver=diagnostics, displacements=np.asarray([0, 0, 0, 1, 0, 0], dtype=float))

    receipt = {
        "scope": scope["id"], "source": scope["source"], "inputs_sha256": scope["inputs"],
        "nodes": 2, "resultant_ux": -1.0, "compatibility": "SUPPORTED_ROUTE",
    }
    payload = capture.capture_case(model, receipt, tmp_path / "live", public_solve)
    capture_metadata = json.loads((tmp_path / "live" / "capture.json").read_text(encoding="utf-8"))
    assert payload["candidate"]["factor"] == 10.0
    assert capture_metadata["instrumentation"]["returned_solver_objects_modified"] is False
    assert capture_metadata["instrumentation"]["solve_full_newton_calls"] == 1
    matrix_data = capture.read_matrix_archive(tmp_path / "live" / "matrices.npz")
    np.testing.assert_array_equal(matrix_data["K0"].toarray(), np.diag([4.0, 5.0, 6.0]))
    np.testing.assert_array_equal(matrix_data["Kg"].diagonal(), [-1.0, -2.0, -3.0])
