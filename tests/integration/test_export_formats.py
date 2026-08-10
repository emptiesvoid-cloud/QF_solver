import csv
import json
import subprocess
import sys
from pathlib import Path

from solveur.api import load_model, save_result_csv, save_result_vtu, solve_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TET4_EXAMPLE = PROJECT_ROOT / "examples" / "tet4_static.json"
DYNAMIC_EXAMPLE = PROJECT_ROOT / "examples" / "tet4_transient_dynamic.json"
HARMONIC_EXAMPLE = PROJECT_ROOT / "examples" / "tet4_harmonic_response.json"


def test_api_exports_static_result_to_csv_and_vtu(tmp_path: Path):
    model = load_model(TET4_EXAMPLE)
    result = solve_model(model)
    csv_paths = save_result_csv(result, tmp_path / "csv", model)
    vtu_path = tmp_path / "result.vtu"
    save_result_vtu(result, model, vtu_path)

    nodal_rows = list(csv.DictReader(csv_paths["nodal_displacements"].open(encoding="utf-8")))
    nodal_result_rows = list(csv.DictReader(csv_paths["nodal_results"].open(encoding="utf-8")))
    element_rows = list(csv.DictReader(csv_paths["element_results"].open(encoding="utf-8")))
    check_rows = list(csv.DictReader(csv_paths["audit_checks"].open(encoding="utf-8")))
    post_rows = list(csv.DictReader(csv_paths["post_results"].open(encoding="utf-8")))

    assert len(nodal_rows) == 4
    assert {"node", "x", "y", "z", "UX", "UY", "UZ", "translation_magnitude"} <= set(nodal_rows[0])
    assert len(nodal_result_rows) == 4
    assert float(nodal_result_rows[0]["von_mises"]) > 0.0
    assert "principal_stress_0" in nodal_result_rows[0]
    assert len(element_rows) == 1
    assert float(element_rows[0]["von_mises"]) > 0.0
    assert "integration_points" in element_rows[0]
    assert any(row["name"] == "post:0:TET4:von_mises_nonnegative" for row in check_rows)
    assert post_rows[0]["calculation_frame"] == "global"
    assert "calculation_displacement_0" in post_rows[0]

    text = vtu_path.read_text(encoding="utf-8")
    assert '<VTKFile type="UnstructuredGrid"' in text
    assert 'Name="Displacement"' in text
    assert 'Name="VonMises"' in text
    assert 'Name="PrincipalStress"' in text
    assert 'Name="HydrostaticPressure"' in text
    assert 'Name="NodalVonMises"' in text
    assert 'Name="NodalPrincipalStress"' in text
    assert '<DataArray type="UInt8" Name="types" format="ascii">10</DataArray>' in text


def test_cli_exports_static_result_to_csv_and_vtu(tmp_path: Path):
    result_path = tmp_path / "result.json"
    csv_dir = tmp_path / "csv"
    vtu_path = tmp_path / "result.vtu"
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "main_solveur.py"),
            "solve",
            "--input",
            str(TET4_EXAMPLE),
            "--output",
            str(result_path),
            "--csv-dir",
            str(csv_dir),
            "--vtu",
            str(vtu_path),
            "--audit-gate",
            "fail",
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "csv directory:" in completed.stdout
    assert "vtu:" in completed.stdout
    data = json.loads(result_path.read_text(encoding="utf-8"))
    assert data["status"] == "PASS"
    assert (csv_dir / "nodal_displacements.csv").exists()
    assert (csv_dir / "nodal_results.csv").exists()
    assert (csv_dir / "element_results.csv").exists()
    assert (csv_dir / "audit_checks.csv").exists()
    assert vtu_path.exists()


def test_api_exports_dynamic_time_history_to_csv(tmp_path: Path):
    model = load_model(DYNAMIC_EXAMPLE)
    result = solve_model(model)
    csv_paths = save_result_csv(result, tmp_path / "csv", model)
    rows = list(csv.DictReader(csv_paths["time_history"].open(encoding="utf-8")))

    assert len(rows) == result.solver["step_count"]
    assert {"step", "time", "total_energy", "relative_energy_drift", "dynamic_residual_norm"} <= set(rows[0])
    assert float(rows[-1]["total_energy"]) >= 0.0


def test_api_exports_harmonic_frequency_response_to_csv(tmp_path: Path):
    model = load_model(HARMONIC_EXAMPLE)
    result = solve_model(model)
    csv_paths = save_result_csv(result, tmp_path / "csv", model)
    rows = list(csv.DictReader(csv_paths["frequency_response"].open(encoding="utf-8")))

    assert result.to_dict()["analysis"] == "harmonic_response"
    assert len(rows) == len(result.frequencies_hz) * result.node_count * 3
    assert {"frequency_hz", "node", "dof", "real", "imag", "amplitude", "phase_degrees"} <= set(rows[0])
    assert max(float(row["amplitude"]) for row in rows) > 0.0
