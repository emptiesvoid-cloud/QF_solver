"""End-to-end library workflow for the BEAM2 reference example."""

from pathlib import Path

import pytest

from solveur.api import check_mesh, load_model, save_result, save_result_vtu, solve_model


ROOT = Path(__file__).resolve().parents[2]


def test_beam2_json_library_workflow(tmp_path: Path) -> None:
    model = load_model(ROOT / "examples" / "beam2_cantilever.json")
    report = check_mesh(model)
    result = solve_model(model)
    output = tmp_path / "beam2_result.json"
    vtu = tmp_path / "beam2_result.vtu"
    save_result(result, output)
    save_result_vtu(result, model, vtu)
    expected = 1000.0 * 2.0**3 / (3.0 * 210.0e9 * 3.0e-6)
    expected += 1000.0 * 2.0 / ((5.0 / 6.0) * (210.0e9 / 2.6) * 0.01)
    assert report.status == "PASS"
    assert result.status == "PASS"
    assert result.displacements[result.dofs.index(1, "UY")] == pytest.approx(expected, rel=1.0e-12)
    assert result.element_results[0]["type"] == "BEAM2"
    assert output.is_file()
    assert 'type="UInt8" Name="types" format="ascii">3<' in vtu.read_text(encoding="utf-8")
