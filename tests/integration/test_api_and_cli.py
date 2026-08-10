import json
import subprocess
import sys
from pathlib import Path

from solveur.api import (
    check_mesh,
    inspect_model,
    load_model,
    save_audit_markdown,
    save_result,
    save_result_vtu,
    solve_model,
)
from tests.helpers.cli import run_solver_cli
from tests.helpers.models import (
    write_arc_length_model,
    write_iterative_model,
    write_low_quality_model,
    write_modal_model,
    write_model,
    write_nonlinear_model,
    write_shell_model,
    write_tet10_modal_model,
    write_tet10_model,
    write_tet10_nonlinear_model,
)


def test_public_api_load_check_solve_save(tmp_path: Path):
    model_path = tmp_path / "model.json"
    result_path = tmp_path / "result.json"
    audit_md_path = tmp_path / "audit.md"
    write_model(model_path)
    model = load_model(model_path)
    assert check_mesh(model).status == "PASS"
    result = solve_model(model)
    save_result(result, result_path)
    save_audit_markdown(result, audit_md_path)
    assert json.loads(result_path.read_text(encoding="utf-8"))["status"] == "PASS"
    text = audit_md_path.read_text(encoding="utf-8")
    assert "## Solveur numerique" in text
    assert "### Historique des residus" in text
    assert "## Controles automatiques" in text
    assert "## Equilibre" in text


def test_cli_tet10_mechanical_verification_writes_report(tmp_path: Path):
    report_path = tmp_path / "tet10_verification.json"
    completed = run_solver_cli("verify-tet10", "--json-report", str(report_path))
    assert completed.returncode == 0, completed.stderr
    assert "GLOBAL STATUS: PASS" in completed.stdout
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert len(report["checks"]) == 8


def test_public_api_saves_inspection_markdown(tmp_path: Path):
    model_path = tmp_path / "model.json"
    audit_md_path = tmp_path / "inspection.md"
    write_model(model_path)
    audit = inspect_model(load_model(model_path))
    save_audit_markdown(audit, audit_md_path)
    text = audit_md_path.read_text(encoding="utf-8")
    assert "# Audit boite blanche du solveur" in text
    assert "Pas de bilan d'equilibre" in text


def test_public_api_inspection_can_include_local_matrix_values(tmp_path: Path):
    model_path = tmp_path / "model.json"
    write_model(model_path)
    audit = inspect_model(load_model(model_path), detail="values")
    data = audit.to_dict()
    element = data["element_audits"][0]
    assert len(element["local_dofs"]) == 12
    assert element["local_dofs"][0] == {"local_index": 0, "node": 0, "dof": "UX", "global_index": 0}
    assert len(element["assembly_entries"]) > 0
    assert "values" in element["matrices"][0]
    assert len(element["matrices"][0]["values"]) == 12


def test_cli_check_mesh_and_solve(tmp_path: Path):
    model_path = tmp_path / "model.json"
    result_path = tmp_path / "result.json"
    audit_md_path = tmp_path / "solve_audit.md"
    write_model(model_path)
    check = run_solver_cli("check-mesh", "--input", model_path)
    assert check.returncode == 0
    assert "MESH STATUS: PASS" in check.stdout
    solve = run_solver_cli("solve", "--input", model_path, "--output", result_path, "--audit-md", audit_md_path)
    assert solve.returncode == 0
    assert result_path.exists()
    data = json.loads(result_path.read_text(encoding="utf-8"))
    assert data["audit"]["purpose"] == "white_box_solver_audit"
    assert data["audit"]["equilibrium"]["free_residual_norm"] < 1.0e-8
    audit_text = audit_md_path.read_text(encoding="utf-8")
    assert "equilibrium:free_relative_residual" in audit_text
    assert "## Equilibre" in audit_text
    assert "Norme residu libre" in audit_text
    assert "## Bilan des chargements" in audit_text


def test_contact_examples_run_through_the_public_api_and_qf_cli(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    for name, expected_state in (("frictionless_contact_plane.json", None), ("frictional_contact_plane.json", "slip")):
        model_path = root / "examples" / name
        result_path = tmp_path / f"{model_path.stem}.json"
        model = load_model(model_path)
        assert check_mesh(model).status == "PASS"
        result = solve_model(model)
        contact = result.solver["contact"]["contacts"][0]
        assert contact["gap"] == 0.0
        assert contact["active"] is True
        if expected_state is not None:
            assert contact["tangential_state"] == expected_state
        completed = subprocess.run(
            [sys.executable, "qf_solver.py", "solve", "--input", str(model_path), "--output", str(result_path)],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        saved = json.loads(result_path.read_text(encoding="utf-8"))
        saved_contact = saved["solver"]["contact"]["contacts"][0]
        assert saved_contact["active"] is True
        if expected_state is not None:
            assert saved_contact["tangential_state"] == expected_state


def test_rbe2_example_runs_through_api_cli_audit_and_vtu_export(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    model_path = root / "examples" / "rbe2_rigid_arm.json"
    result_path = tmp_path / "rbe2_result.json"
    audit_path = tmp_path / "rbe2_audit.md"
    vtu_path = tmp_path / "rbe2.vtu"
    model = load_model(model_path)
    result = solve_model(model)

    save_result(result, result_path)
    save_audit_markdown(result, audit_path)
    save_result_vtu(result, model, vtu_path)
    completed = run_solver_cli("solve", "--input", model_path, "--output", result_path)

    assert check_mesh(model).status == "WARNING"
    assert completed.returncode == 0, completed.stderr
    data = json.loads(result_path.read_text(encoding="utf-8"))
    assert data["audit"]["equilibrium"]["moment_balance_relative_error"] <= 1.0e-12
    assert 'NumberOfCells="0"' in vtu_path.read_text(encoding="utf-8")
    assert "## Equilibre" in audit_path.read_text(encoding="utf-8")


def test_cli_inspect_writes_white_box_audit(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    model_path = tmp_path / "model.json"
    audit_path = tmp_path / "audit.json"
    markdown_path = tmp_path / "audit.md"
    write_model(model_path)
    inspect = subprocess.run(
        [
            sys.executable,
            "main_solveur.py",
            "inspect",
            "--input",
            str(model_path),
            "--output",
            str(audit_path),
            "--markdown",
            str(markdown_path),
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert inspect.returncode == 0
    assert "AUDIT STATUS: PASS" in inspect.stdout
    data = json.loads(audit_path.read_text(encoding="utf-8"))
    assert data["purpose"] == "white_box_solver_audit"
    assert data["boundary"]["free_dof_count"] == 3
    assert data["equilibrium"] == {}
    assert data["element_audits"][0]["geometry"]["corner_quality"] > 0.0
    assert data["element_audits"][0]["matrices"][0]["shape"] == [12, 12]
    assert {matrix["name"] for matrix in data["matrices"]} == {"stiffness", "reduced_stiffness"}
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "## Controles automatiques" in markdown
    assert "## Matrices globales" in markdown
    assert "## Elements" in markdown


def test_cli_inspect_detail_values_writes_assembly_trace(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    model_path = tmp_path / "model.json"
    audit_path = tmp_path / "audit_values.json"
    write_model(model_path)
    inspect = subprocess.run(
        [
            sys.executable,
            "main_solveur.py",
            "inspect",
            "--input",
            str(model_path),
            "--output",
            str(audit_path),
            "--detail",
            "values",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert inspect.returncode == 0
    data = json.loads(audit_path.read_text(encoding="utf-8"))
    element = data["element_audits"][0]
    assert element["assembly_entries"][0]["global_row"] >= 0
    assert "values" in element["matrices"][0]


def test_cli_inspect_invalid_official_example_writes_partial_audit(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    invalid_path = root / "examples" / "invalid_inverted_tet4.json"
    audit_path = tmp_path / "invalid_audit.json"
    markdown_path = tmp_path / "invalid_audit.md"
    inspect = subprocess.run(
        [
            sys.executable,
            "main_solveur.py",
            "inspect",
            "--input",
            str(invalid_path),
            "--output",
            str(audit_path),
            "--markdown",
            str(markdown_path),
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert inspect.returncode == 2
    assert "AUDIT STATUS: FAIL" in inspect.stdout
    data = json.loads(audit_path.read_text(encoding="utf-8"))
    assert data["purpose"] == "white_box_solver_audit"
    assert data["mesh_status"] == "FAIL"
    assert "volume" in data["mesh_errors"][0]
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "| Statut maillage | FAIL |" in markdown


def test_cli_audit_gate_passes_clean_model(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    model_path = tmp_path / "model.json"
    write_model(model_path)
    inspect = subprocess.run(
        [
            sys.executable,
            "main_solveur.py",
            "inspect",
            "--input",
            str(model_path),
            "--audit-gate",
            "fail",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert inspect.returncode == 0
    assert "AUDIT GATE: PASS" in inspect.stdout


def test_cli_audit_gate_fails_on_warning(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    model_path = tmp_path / "low_quality.json"
    write_low_quality_model(model_path)
    inspect = subprocess.run(
        [
            sys.executable,
            "main_solveur.py",
            "inspect",
            "--input",
            str(model_path),
            "--audit-gate",
            "warning",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert inspect.returncode == 2
    assert "AUDIT GATE: FAIL" in inspect.stdout
    assert "WARNING=" in inspect.stdout


def test_cli_iterative_preconditioned_solve(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    model_path = tmp_path / "iterative.json"
    result_path = tmp_path / "iterative_result.json"
    write_iterative_model(model_path)
    solve = subprocess.run(
        [sys.executable, "main_solveur.py", "solve", "--input", str(model_path), "--output", str(result_path)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert solve.returncode == 0
    data = json.loads(result_path.read_text(encoding="utf-8"))
    assert data["method"] == "bicgstab"
    assert data["solver"]["preconditioner"] == "jacobi"
    assert data["solver"]["residual_history"]


def test_cli_methods_and_modal_solve(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    model_path = tmp_path / "modal.json"
    result_path = tmp_path / "modal_result.json"
    write_modal_model(model_path)
    methods = subprocess.run(
        [sys.executable, "main_solveur.py", "methods"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert methods.returncode == 0
    assert "nonlinear_static" in methods.stdout
    solve = subprocess.run(
        [sys.executable, "main_solveur.py", "solve", "--input", str(model_path), "--output", str(result_path)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert solve.returncode == 0
    assert json.loads(result_path.read_text(encoding="utf-8"))["analysis"] == "modal"


def test_cli_tet10_static_outputs_stress(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    model_path = tmp_path / "tet10.json"
    result_path = tmp_path / "tet10_result.json"
    write_tet10_model(model_path)
    solve = subprocess.run(
        [sys.executable, "main_solveur.py", "solve", "--input", str(model_path), "--output", str(result_path)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert solve.returncode == 0
    data = json.loads(result_path.read_text(encoding="utf-8"))
    assert data["element_results"][0]["type"] == "TET10"
    assert data["element_results"][0]["von_mises"] > 0.0


def test_cli_tet10_modal_solve(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    model_path = tmp_path / "tet10_modal.json"
    result_path = tmp_path / "tet10_modal_result.json"
    write_tet10_modal_model(model_path)
    solve = subprocess.run(
        [sys.executable, "main_solveur.py", "solve", "--input", str(model_path), "--output", str(result_path)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert solve.returncode == 0
    data = json.loads(result_path.read_text(encoding="utf-8"))
    assert data["analysis"] == "modal"
    assert len(data["modes"]) == 3


def test_cli_tet10_nonlinear_solve(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    model_path = tmp_path / "tet10_nonlinear.json"
    result_path = tmp_path / "tet10_nonlinear_result.json"
    write_tet10_nonlinear_model(model_path)
    solve = subprocess.run(
        [sys.executable, "main_solveur.py", "solve", "--input", str(model_path), "--output", str(result_path)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert solve.returncode == 0
    data = json.loads(result_path.read_text(encoding="utf-8"))
    assert data["analysis"] == "nonlinear_static"
    assert data["element_results"][0]["type"] == "TET10"
    assert data["solver"]["steps"][-1]["relative_residual"] < 1.0e-9


def test_cli_nonlinear_solve(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    model_path = tmp_path / "nonlinear.json"
    result_path = tmp_path / "nonlinear_result.json"
    write_nonlinear_model(model_path)
    solve = subprocess.run(
        [sys.executable, "main_solveur.py", "solve", "--input", str(model_path), "--output", str(result_path)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert solve.returncode == 0
    data = json.loads(result_path.read_text(encoding="utf-8"))
    assert data["analysis"] == "nonlinear_static"
    assert data["solver"]["steps"][-1]["relative_residual"] < 1.0e-9


def test_cli_arc_length_solve(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    model_path = tmp_path / "arc_length.json"
    result_path = tmp_path / "arc_length_result.json"
    write_arc_length_model(model_path)
    solve = subprocess.run(
        [sys.executable, "main_solveur.py", "solve", "--input", str(model_path), "--output", str(result_path)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert solve.returncode == 0
    data = json.loads(result_path.read_text(encoding="utf-8"))
    assert data["method"] == "arc_length"
    assert data["solver"]["arc_length"] is True


def test_cli_shell_solve_outputs_resultants(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    model_path = tmp_path / "shell.json"
    result_path = tmp_path / "shell_result.json"
    write_shell_model(model_path)
    solve = subprocess.run(
        [sys.executable, "main_solveur.py", "solve", "--input", str(model_path), "--output", str(result_path)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert solve.returncode == 0
    data = json.loads(result_path.read_text(encoding="utf-8"))
    assert data["element_results"][0]["type"] == "MITC4"
    assert "membrane_force" in data["element_results"][0]
