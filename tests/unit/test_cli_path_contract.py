from pathlib import Path

from solveur.cli.mesh import _default_report_path


def test_mesh_import_default_report_path_preserves_output_stem() -> None:
    assert _default_report_path("results/model.json") == Path("results/model.import_report.json")
