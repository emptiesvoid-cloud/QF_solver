from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from solveur.api import import_gmsh_model, load_model, solve_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("binary", [False, True])
def test_native_gmsh_41_imports_ascii_and_binary(tmp_path: Path, binary: bool) -> None:
    mesh = tmp_path / ("box_binary.msh" if binary else "box_ascii.msh")
    setup = tmp_path / "box.setup.json"
    _write_box_mesh(mesh, binary=binary)
    _write_setup(setup)
    imported = import_gmsh_model(mesh, setup)
    assert imported.report.msh_version == "4.1"
    assert imported.report.solver_name == "QF_solver"
    assert imported.report.solver_version == "0.2.1a0"
    assert imported.report.binary is binary
    assert imported.report.element_family == "TET4"
    assert imported.model.node_count > 8
    assert len(imported.model.elements) > 8
    result = solve_model(imported.model)
    assert result.status == "PASS"


def test_cli_import_mesh_writes_loadable_model_and_report(tmp_path: Path) -> None:
    mesh = tmp_path / "box.msh"
    setup = tmp_path / "box.setup.json"
    output = tmp_path / "box.json"
    report = tmp_path / "box.import.json"
    _write_box_mesh(mesh, binary=False)
    _write_setup(setup)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "solveur.cli.main",
            "import-mesh",
            "--mesh",
            str(mesh),
            "--setup",
            str(setup),
            "--output",
            str(output),
            "--report",
            str(report),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "GMSH IMPORT" in completed.stdout
    assert report.is_file()
    assert load_model(output).node_count > 8
    report_data = json.loads(report.read_text(encoding="utf-8"))
    assert report_data["source_sha256"]
    assert report_data["action_counts"]["pressure"] > 0


def _write_box_mesh(path: Path, *, binary: bool) -> None:
    gmsh = pytest.importorskip("gmsh")
    gmsh.initialize(["qf_solver_test", "-nopopup"])
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("qf_solver_box")
        volume = gmsh.model.occ.addBox(0.0, 0.0, 0.0, 1.0, 0.4, 0.3)
        gmsh.model.occ.synchronize()
        boundary = gmsh.model.getBoundary([(3, volume)], oriented=False, recursive=False)
        surfaces = [tag for dimension, tag in boundary if dimension == 2]
        fixed = min(surfaces, key=lambda tag: gmsh.model.occ.getCenterOfMass(2, tag)[0])
        loaded = max(surfaces, key=lambda tag: gmsh.model.occ.getCenterOfMass(2, tag)[0])
        domain_group = gmsh.model.addPhysicalGroup(3, [volume])
        fixed_group = gmsh.model.addPhysicalGroup(2, [fixed])
        loaded_group = gmsh.model.addPhysicalGroup(2, [loaded])
        gmsh.model.setPhysicalName(3, domain_group, "domain")
        gmsh.model.setPhysicalName(2, fixed_group, "fixed")
        gmsh.model.setPhysicalName(2, loaded_group, "loaded")
        gmsh.option.setNumber("Mesh.MeshSizeMin", 0.18)
        gmsh.option.setNumber("Mesh.MeshSizeMax", 0.18)
        gmsh.model.mesh.generate(3)
        gmsh.option.setNumber("Mesh.MshFileVersion", 4.1)
        gmsh.option.setNumber("Mesh.Binary", 1 if binary else 0)
        gmsh.write(str(path))
    finally:
        gmsh.finalize()


def _write_setup(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "mesh_scale_to_m": 1.0,
                "units": {"system": "SI"},
                "verification_profile": "engineering",
                "analysis": {"type": "linear_static", "method": "direct"},
                "materials": {
                    "steel": {"type": "isotropic_3d", "E": 210000000000.0, "nu": 0.3, "density": 7800.0}
                },
                "groups": [
                    {
                        "name": "domain",
                        "dimension": 3,
                        "actions": [{"type": "elements", "element_type": "TET4", "material": "steel"}],
                    },
                    {
                        "name": "fixed",
                        "dimension": 2,
                        "actions": [{"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ"]}],
                    },
                    {
                        "name": "loaded",
                        "dimension": 2,
                        "actions": [{"type": "pressure", "value": 1000.0}],
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
