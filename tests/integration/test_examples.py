import json
import subprocess
import sys
from pathlib import Path

import pytest

from solveur.api import check_mesh, load_model, solve_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = [
    PROJECT_ROOT / "examples" / "tet4_static.json",
    PROJECT_ROOT / "examples" / "tet4_compression.json",
    PROJECT_ROOT / "examples" / "tet4_body_force.json",
    PROJECT_ROOT / "examples" / "tet4_pressure.json",
    PROJECT_ROOT / "examples" / "tet10_static.json",
    PROJECT_ROOT / "examples" / "tet4_orthotropic_static.json",
    PROJECT_ROOT / "examples" / "tet10_orthotropic_static.json",
    PROJECT_ROOT / "examples" / "mitc4_shell_static.json",
    PROJECT_ROOT / "examples" / "mitc4_laminate_static.json",
    PROJECT_ROOT / "examples" / "tet4_nonlinear_static.json",
    PROJECT_ROOT / "examples" / "tet4_elastoplastic_static.json",
    PROJECT_ROOT / "examples" / "tet4_transient_dynamic.json",
    PROJECT_ROOT / "examples" / "tet4_dynamic_free_vibration.json",
    PROJECT_ROOT / "examples" / "tet4_dynamic_sdof_free_vibration.json",
    PROJECT_ROOT / "examples" / "tet4_dynamic_tabulated_load.json",
    PROJECT_ROOT / "examples" / "mitc4_dynamic_multicomponent.json",
]
HARMONIC_EXAMPLES = [
    PROJECT_ROOT / "examples" / "tet4_harmonic_response.json",
    PROJECT_ROOT / "examples" / "tet4_harmonic_sdof_response.json",
]
MODAL_EXAMPLE = PROJECT_ROOT / "examples" / "tet4_modal_unit.json"
PRESSURE_EXAMPLE = PROJECT_ROOT / "examples" / "tet4_pressure.json"


def test_official_examples_solve_through_api():
    for path in EXAMPLES:
        model = load_model(path)
        report = check_mesh(model)
        assert report.status in {"PASS", "WARNING"}, path.name
        result = solve_model(model)
        data = result.to_dict()
        assert data["status"] == "PASS", path.name
        assert data["audit"]["purpose"] == "white_box_solver_audit"
        assert data["audit"]["post_results"], path.name
        assert data["audit"]["equilibrium"]["free_relative_residual"] < 1.0e-6


def test_official_examples_solve_through_cli(tmp_path: Path):
    for path in EXAMPLES:
        stem = path.stem
        result_path = tmp_path / f"{stem}_results.json"
        audit_path = tmp_path / f"{stem}_audit.md"
        completed = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "main_solveur.py"),
                "solve",
                "--input",
                str(path),
                "--output",
                str(result_path),
                "--audit-md",
                str(audit_path),
                "--audit-gate",
                "fail",
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        data = json.loads(result_path.read_text(encoding="utf-8"))
        assert data["status"] == "PASS"
        assert data["audit"]["post_results"]
        assert "Post-traitement par element" in audit_path.read_text(encoding="utf-8")


def test_official_examples_check_mesh_through_cli():
    for path in EXAMPLES:
        completed = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "main_solveur.py"),
                "check-mesh",
                "--input",
                str(path),
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        assert "MESH STATUS:" in completed.stdout


def test_pressure_example_preserves_analytical_resultant_through_api_and_cli(tmp_path: Path):
    result = solve_model(load_model(PRESSURE_EXAMPLE)).to_dict()
    balance = result["audit"]["load_assembly"]
    assert balance["distributed_load_count"] == 1
    assert balance["resultant"] == pytest.approx([-500.0, -500.0, -500.0])
    assert balance["moment_about_origin"] == pytest.approx([0.0, 0.0, 0.0], abs=1.0e-12)

    result_path = tmp_path / "tet4_pressure_result.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "main_solveur.py"),
            "solve",
            "--input",
            str(PRESSURE_EXAMPLE),
            "--output",
            str(result_path),
            "--audit-gate",
            "fail",
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    cli_balance = json.loads(result_path.read_text(encoding="utf-8"))["audit"]["load_assembly"]
    assert cli_balance["resultant"] == pytest.approx([-500.0, -500.0, -500.0])


def test_harmonic_example_solves_through_api_and_cli(tmp_path: Path):
    for path in HARMONIC_EXAMPLES:
        model = load_model(path)
        result = solve_model(model).to_dict()
        assert result["status"] == "PASS"
        assert result["analysis"] == "harmonic_response"
        assert result["frequency_response"]

        result_path = tmp_path / f"{path.stem}_result.json"
        completed = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "main_solveur.py"),
                "solve",
                "--input",
                str(path),
                "--output",
                str(result_path),
                "--audit-gate",
                "fail",
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        assert json.loads(result_path.read_text(encoding="utf-8"))["analysis"] == "harmonic_response"


def test_modal_example_solves_through_api_and_cli(tmp_path: Path):
    model = load_model(MODAL_EXAMPLE)
    result = solve_model(model).to_dict()
    assert result["status"] == "PASS"
    assert result["analysis"] == "modal"
    assert len(result["modes"]) == 3
    assert result["solver"]["max_relative_residual"] < 1.0e-10

    result_path = tmp_path / "modal_result.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "main_solveur.py"),
            "solve",
            "--input",
            str(MODAL_EXAMPLE),
            "--output",
            str(result_path),
            "--audit-gate",
            "fail",
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(result_path.read_text(encoding="utf-8"))["analysis"] == "modal"
