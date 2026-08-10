import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.api import (
    benchmark_large_model,
    check_large_readiness,
    collect_large_runtime_environment,
    convert_model_to_large,
    generate_large_tet4_block,
    inspect_large_model,
    load_large_model,
    load_model,
    qualify_large_tet4_pipeline,
    recommended_large_block,
    save_large_readiness,
    save_large_runtime_environment,
    solve_large_model,
    solve_model,
    verify_evidence,
    verify_large_qualification,
)
from solveur.large.model import LargeModel


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TET4_EXAMPLE = PROJECT_ROOT / "examples" / "tet4_static.json"


def test_convert_model_to_large_hdf5_and_npz_roundtrip(tmp_path: Path):
    h5_path = tmp_path / "model.h5"
    npz_path = tmp_path / "model.npz"
    large = convert_model_to_large(TET4_EXAMPLE, h5_path)
    assert h5_path.exists()
    assert large.node_count == 4
    assert large.element_count == 1

    loaded_h5 = load_large_model(h5_path)
    assert np.allclose(loaded_h5.nodes, large.nodes)
    assert np.array_equal(loaded_h5.tet4, large.tet4)

    convert_model_to_large(TET4_EXAMPLE, npz_path)
    loaded_npz = load_large_model(npz_path)
    assert np.allclose(loaded_npz.nodes, large.nodes)
    assert np.array_equal(loaded_npz.tet4, large.tet4)


def test_generate_large_tet4_block_and_recommended_dimensions(tmp_path: Path):
    dims = recommended_large_block(200)
    assert 3 * (dims[0] + 1) * (dims[1] + 1) * (dims[2] + 1) >= 200
    path = tmp_path / "generated.h5"
    model = generate_large_tet4_block(path, nx=2, ny=1, nz=1, total_load=12.0)
    loaded = load_large_model(path)
    assert model.node_count == 12
    assert model.element_count == 12
    assert loaded.ndof == 36
    assert np.isclose(np.sum(loaded.load_values), 12.0)
    assert inspect_large_model(loaded).status == "PASS"


def test_large_readiness_reports_dependencies_and_sizing(tmp_path: Path):
    report = check_large_readiness(tmp_path, target_dofs=1_000_000, solver_backend="petsc")
    paths = save_large_readiness(report, tmp_path)
    assert report["sizing"]["ndof"] >= 1_000_000
    assert report["dimensions"] == {"nx": 69, "ny": 69, "nz": 69}
    assert paths["json"].exists()
    assert paths["markdown"].exists()
    statuses = {item["id"]: item["status"] for item in report["checks"]}
    if importlib.util.find_spec("petsc4py") is None or importlib.util.find_spec("mpi4py") is None:
        assert report["status"] == "FAIL"
        assert "FAIL" in {statuses["DEP-PETSC4PY"], statuses["DEP-MPI4PY"]}


def test_large_readiness_matrix_free_accepts_1m_without_petsc(tmp_path: Path):
    report = check_large_readiness(tmp_path, target_dofs=1_000_000, solver_backend="matrix_free")
    assert report["status"] == "PASS"
    assert report["sizing"]["ndof"] >= 1_000_000
    statuses = {item["id"]: item["status"] for item in report["checks"]}
    assert statuses["BACKEND-SCALE"] == "PASS"
    assert statuses["DEP-PETSC4PY"] == "PASS"


def test_large_runtime_environment_report_api(tmp_path: Path):
    report = collect_large_runtime_environment({"kind": "unit_test"})
    assert report["solver"]["version"]
    assert report["python"]["executable"]
    assert report["packages"]["numpy"]["available"] is True
    assert "OMP_NUM_THREADS" in report["environment"]

    path = save_large_runtime_environment(tmp_path, {"kind": "unit_test"})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["metadata"]["kind"] == "unit_test"
    assert data["packages"]["scipy"]["available"] is True


def test_large_scipy_solve_matches_standard_solver_and_writes_file_backed_outputs(tmp_path: Path):
    h5_path = tmp_path / "model.h5"
    output = tmp_path / "large_results"
    convert_model_to_large(TET4_EXAMPLE, h5_path)
    large_model = load_large_model(h5_path)

    large_result = solve_large_model(large_model, output, solver_backend="scipy", preconditioner="jacobi")
    standard = solve_model(load_model(TET4_EXAMPLE))

    assert large_result.status == "PASS"
    assert (output / "summary.json").exists()
    assert (output / "audit_large.json").exists()
    assert (output / "displacements.h5").exists()
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["backend"] == "scipy"
    assert summary["ndof"] == standard.dofs.ndof

    displacement = _read_large_displacement(output / "displacements.h5")
    assert np.allclose(displacement.ravel(), standard.displacements, rtol=1.0e-8, atol=1.0e-12)
    audit = inspect_large_model(large_model)
    assert audit.status == "PASS"
    assert audit.details["tet4_quality"]["invalid_volume_count"] == 0


def test_matrix_free_solve_matches_scipy_on_generated_block(tmp_path: Path):
    model_path = tmp_path / "generated.h5"
    generate_large_tet4_block(model_path, nx=1, ny=1, nz=1)
    model = load_large_model(model_path)
    scipy = solve_large_model(model, tmp_path / "scipy", solver_backend="scipy")
    matrix_free = solve_large_model(model, tmp_path / "matrix_free", solver_backend="matrix_free")
    assert scipy.status == "PASS"
    assert matrix_free.status == "PASS"
    assert matrix_free.backend == "matrix_free"
    assert matrix_free.summary["matrix_free_operator_memory_bytes"] > 0
    scipy_u = _read_large_displacement(tmp_path / "scipy" / "displacements.h5")
    matrix_free_u = _read_large_displacement(tmp_path / "matrix_free" / "displacements.h5")
    assert np.allclose(matrix_free_u, scipy_u, rtol=1.0e-7, atol=1.0e-12)


def test_benchmark_large_writes_reproducible_evidence(tmp_path: Path):
    model_path = tmp_path / "generated.h5"
    output = tmp_path / "evidence_large"
    generate_large_tet4_block(model_path, nx=1, ny=1, nz=1)
    benchmark = benchmark_large_model(model_path, output, solver_backend="scipy")
    assert benchmark["status"] == "PASS"
    assert (output / "benchmark_large.json").exists()
    assert (output / "benchmark_large.md").exists()
    assert (output / "summary.json").exists()
    assert (output / "audit_large.json").exists()
    assert (output / "input_fingerprint.json").exists()
    assert (output / "runtime_environment.json").exists()
    assert (output / "evidence_manifest.json").exists()
    assert benchmark["memory_telemetry"]["python_tracemalloc_peak_bytes"] > 0
    assert benchmark["runtime_environment"] == "runtime_environment.json"
    assert benchmark["artifact_policy"]["file_backed_displacements"] is True
    assert benchmark["artifact_policy"]["monolithic_displacements_in_json"] is False
    runtime = json.loads((output / "runtime_environment.json").read_text(encoding="utf-8"))
    assert runtime["metadata"]["kind"] == "large_benchmark"
    assert runtime["packages"]["numpy"]["available"] is True
    report = verify_evidence(output)
    assert report.status == "PASS"
    manifest = json.loads((output / "evidence_manifest.json").read_text(encoding="utf-8"))
    roles = {item["role"] for item in manifest["files"]}
    assert "input_fingerprint" in roles
    assert "runtime_environment" in roles


def test_qualify_large_pipeline_small_case(tmp_path: Path):
    output = tmp_path / "large_qualification"
    summary = qualify_large_tet4_pipeline(output, target_dofs=24, nx=1, ny=1, nz=1, solver_backend="scipy")
    assert summary["status"] == "PASS"
    assert summary["actual_dofs"] >= 24
    assert (output / "qualification_model.h5").exists()
    assert (output / "large_qualification_summary.json").exists()
    assert (output / "large_qualification_summary.md").exists()
    assert (output / "runtime_environment.json").exists()
    assert (output / "benchmark" / "runtime_environment.json").exists()
    assert (output / "evidence_manifest.json").exists()
    assert verify_evidence(output / "benchmark").status == "PASS"
    assert verify_evidence(output).status == "PASS"
    assert summary["qualification_evidence_verification"]["status"] == "PASS"
    assert {item["status"] for item in summary["checks"]} == {"PASS"}
    verification = verify_large_qualification(output, target_dofs=24)
    assert verification.status == "PASS"
    assert {item["status"] for item in verification.checks} == {"PASS"}
    assert "RUNTIME-BENCHMARK-PYTHON" in {item["id"] for item in verification.checks}


def test_verify_large_qualification_detects_tampered_displacements(tmp_path: Path):
    output = tmp_path / "large_qualification"
    qualify_large_tet4_pipeline(output, target_dofs=24, nx=1, ny=1, nz=1, solver_backend="scipy")
    displacement = output / "benchmark" / "displacements.h5"
    displacement.unlink()
    verification = verify_large_qualification(output, target_dofs=24)
    assert verification.status == "FAIL"
    assert "DISPLACEMENTS-FILE" in {item["id"] for item in verification.checks if item["status"] == "FAIL"}


def test_large_solve_does_not_use_dense_sparse_conversion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    h5_path = tmp_path / "model.h5"
    convert_model_to_large(TET4_EXAMPLE, h5_path)
    large_model = load_large_model(h5_path)

    def fail_toarray(_: object) -> np.ndarray:
        raise AssertionError("large-scale solve must not call sparse.toarray()")

    monkeypatch.setattr(csr_matrix, "toarray", fail_toarray)
    result = solve_large_model(large_model, tmp_path / "out", solver_backend="scipy")
    assert result.status == "PASS"


def test_large_scipy_backend_refuses_oversized_model(tmp_path: Path):
    nodes = np.zeros((70_000, 3), dtype=float)
    nodes[1] = [1.0, 0.0, 0.0]
    nodes[2] = [0.0, 1.0, 0.0]
    nodes[3] = [0.0, 0.0, 1.0]
    model = LargeModel(
        nodes=nodes,
        tet4=np.asarray([[0, 1, 2, 3]], dtype=np.int64),
        material_ids=np.zeros(1, dtype=np.int64),
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
        material_names=("steel",),
        fixed_nodes=np.asarray([0, 0, 0, 2, 2, 2, 3, 3, 3], dtype=np.int64),
        fixed_components=np.asarray([0, 1, 2, 0, 1, 2, 0, 1, 2], dtype=np.int8),
        load_nodes=np.asarray([1], dtype=np.int64),
        load_components=np.asarray([0], dtype=np.int8),
        load_values=np.asarray([1.0], dtype=float),
        analysis={"type": "linear_static", "method": "cg"},
    )
    with pytest.raises(ValueError, match="SciPy large backend is intentionally limited"):
        solve_large_model(model, tmp_path / "oversized", solver_backend="scipy")


def test_cli_convert_inspect_and_solve_large_with_scipy_backend(tmp_path: Path):
    h5_path = tmp_path / "model.h5"
    audit_path = tmp_path / "audit_large.json"
    output = tmp_path / "large_cli"
    convert = subprocess.run(
        [sys.executable, "main_solveur.py", "convert-model", "--input", str(TET4_EXAMPLE), "--output", str(h5_path)],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert convert.returncode == 0, convert.stdout + convert.stderr
    assert "CONVERT MODEL STATUS: PASS" in convert.stdout

    inspect = subprocess.run(
        [sys.executable, "main_solveur.py", "inspect-large", "--input", str(h5_path), "--output", str(audit_path)],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert inspect.returncode == 0, inspect.stdout + inspect.stderr
    assert json.loads(audit_path.read_text(encoding="utf-8"))["status"] == "PASS"

    solve = subprocess.run(
        [
            sys.executable,
            "main_solveur.py",
            "solve-large",
            "--input",
            str(h5_path),
            "--output",
            str(output),
            "--solver-backend",
            "scipy",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert solve.returncode == 0, solve.stdout + solve.stderr
    assert "SOLVE LARGE STATUS: PASS" in solve.stdout
    assert (output / "summary.json").exists()


def test_cli_generate_and_benchmark_large(tmp_path: Path):
    model_path = tmp_path / "block.h5"
    output = tmp_path / "benchmark"
    generate = subprocess.run(
        [
            sys.executable,
            "main_solveur.py",
            "generate-large-tet4-block",
            "--output",
            str(model_path),
            "--nx",
            "1",
            "--ny",
            "1",
            "--nz",
            "1",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert generate.returncode == 0, generate.stdout + generate.stderr
    assert "GENERATE LARGE STATUS: PASS" in generate.stdout
    benchmark = subprocess.run(
        [
            sys.executable,
            "main_solveur.py",
            "benchmark-large",
            "--input",
            str(model_path),
            "--output",
            str(output),
            "--solver-backend",
            "scipy",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert benchmark.returncode == 0, benchmark.stdout + benchmark.stderr
    assert "BENCHMARK LARGE STATUS: PASS" in benchmark.stdout
    assert verify_evidence(output).status == "PASS"


def test_cli_large_campaign_plan_only(tmp_path: Path):
    output = tmp_path / "large_campaign"
    completed = subprocess.run(
        [
            sys.executable,
            "qf_solver.py",
            "large-campaign",
            "--output",
            str(output),
            "--targets",
            "24",
            "81",
            "--solver-backend",
            "matrix_free",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "LARGE CAMPAIGN STATUS: PLANNED" in completed.stdout
    assert (output / "large_campaign.json").is_file()
    assert (output / "large_campaign.md").is_file()
    assert verify_evidence(output).status == "PASS"


def test_cli_large_readiness_small_scipy_case(tmp_path: Path):
    completed = subprocess.run(
        [
            sys.executable,
            "main_solveur.py",
            "large-readiness",
            "--output",
            str(tmp_path / "readiness"),
            "--target-dofs",
            "24",
            "--nx",
            "1",
            "--ny",
            "1",
            "--nz",
            "1",
            "--solver-backend",
            "scipy",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "LARGE READINESS STATUS: PASS" in completed.stdout
    assert (tmp_path / "readiness" / "large_readiness.json").exists()


def test_cli_qualify_large_small_case(tmp_path: Path):
    output = tmp_path / "qualify_large"
    completed = subprocess.run(
        [
            sys.executable,
            "main_solveur.py",
            "qualify-large",
            "--output",
            str(output),
            "--target-dofs",
            "24",
            "--nx",
            "1",
            "--ny",
            "1",
            "--nz",
            "1",
            "--solver-backend",
            "scipy",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "QUALIFY LARGE STATUS: PASS" in completed.stdout
    assert (output / "large_qualification_summary.json").exists()
    assert verify_evidence(output / "benchmark").status == "PASS"
    assert verify_evidence(output).status == "PASS"


def test_cli_qualify_large_matrix_free_small_case(tmp_path: Path):
    output = tmp_path / "qualify_large_matrix_free"
    completed = subprocess.run(
        [
            sys.executable,
            "main_solveur.py",
            "qualify-large",
            "--output",
            str(output),
            "--target-dofs",
            "24",
            "--nx",
            "1",
            "--ny",
            "1",
            "--nz",
            "1",
            "--solver-backend",
            "matrix_free",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "QUALIFY LARGE STATUS: PASS" in completed.stdout
    assert verify_large_qualification(output, target_dofs=24).status == "PASS"


def test_cli_verify_large_small_case(tmp_path: Path):
    output = tmp_path / "qualify_large"
    report = tmp_path / "verify_large.json"
    markdown = tmp_path / "verify_large.md"
    qualify_large_tet4_pipeline(output, target_dofs=24, nx=1, ny=1, nz=1, solver_backend="scipy")
    completed = subprocess.run(
        [
            sys.executable,
            "main_solveur.py",
            "verify-large",
            "--input",
            str(output),
            "--target-dofs",
            "24",
            "--json-report",
            str(report),
            "--markdown",
            str(markdown),
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "VERIFY LARGE STATUS: PASS" in completed.stdout
    assert json.loads(report.read_text(encoding="utf-8"))["status"] == "PASS"
    assert markdown.exists()


def test_qualify_large_petsc_missing_fails_at_readiness(tmp_path: Path):
    if importlib.util.find_spec("petsc4py") is not None and importlib.util.find_spec("mpi4py") is not None:
        pytest.skip("PETSc dependencies are installed in this environment.")
    output = tmp_path / "missing_petsc"
    summary = qualify_large_tet4_pipeline(output, target_dofs=1_000_000, solver_backend="petsc")
    assert summary["status"] == "FAIL"
    assert summary["stage"] == "readiness"
    assert (output / "large_readiness.json").exists()
    assert (output / "runtime_environment.json").exists()
    assert (output / "evidence_manifest.json").exists()
    assert verify_evidence(output).status == "PASS"
    assert not (output / "qualification_model.h5").exists()


def test_large_mode_rejects_unsupported_element(tmp_path: Path):
    unsupported = tmp_path / "shell.json"
    unsupported.write_text(
        json.dumps(
            {
                "analysis": "linear_static",
                "nodes": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
                "elements": [{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "skin"}],
                "materials": {"skin": {"type": "shell_isotropic", "E": 1000.0, "nu": 0.25, "t": 0.1}},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="supports only TET4"):
        convert_model_to_large(unsupported, tmp_path / "bad.h5")


def test_large_conversion_rejects_distributed_loads_instead_of_dropping_them(tmp_path: Path):
    with pytest.raises(ValueError, match="does not support distributed loads"):
        convert_model_to_large(PROJECT_ROOT / "examples" / "tet4_pressure.json", tmp_path / "bad.h5")


def test_large_hdf5_corruption_fails_clearly(tmp_path: Path):
    corrupted = tmp_path / "corrupted.h5"
    corrupted.write_text("not an hdf5 file", encoding="utf-8")
    with pytest.raises(Exception):
        load_large_model(corrupted)


def test_petsc_backend_reports_missing_optional_dependencies(tmp_path: Path):
    if importlib.util.find_spec("petsc4py") is not None and importlib.util.find_spec("mpi4py") is not None:
        pytest.skip("PETSc dependencies are installed in this environment.")
    h5_path = tmp_path / "model.h5"
    convert_model_to_large(TET4_EXAMPLE, h5_path)
    completed = subprocess.run(
        [
            sys.executable,
            "main_solveur.py",
            "solve-large",
            "--input",
            str(h5_path),
            "--output",
            str(tmp_path / "petsc_output"),
            "--solver-backend",
            "petsc",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "optional dependency" in completed.stderr or "optional dependency" in completed.stdout


@pytest.mark.large
def test_manual_qualify_large_1m_pipeline(tmp_path: Path):
    if os.environ.get("QF_SOLVER_RUN_LARGE_1M") != "1":
        pytest.skip("Set QF_SOLVER_RUN_LARGE_1M=1 to run the manual 1M ddl qualification benchmark.")
    backend = os.environ.get("QF_SOLVER_LARGE_BACKEND", "petsc")
    summary = qualify_large_tet4_pipeline(tmp_path / "manual_1m", target_dofs=1_000_000, solver_backend=backend)
    assert summary["status"] == "PASS"
    assert summary["actual_dofs"] >= 1_000_000
    assert verify_evidence(Path(summary["benchmark_dir"])).status == "PASS"
    assert verify_evidence(tmp_path / "manual_1m").status == "PASS"
    assert verify_large_qualification(tmp_path / "manual_1m", target_dofs=1_000_000).status == "PASS"


def _read_large_displacement(path: Path) -> np.ndarray:
    import h5py

    with h5py.File(path, "r") as handle:
        return np.asarray(handle["displacements"], dtype=float)
