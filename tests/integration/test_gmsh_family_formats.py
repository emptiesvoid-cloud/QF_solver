from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from solveur.api import import_gmsh_model, solve_model
from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("binary", [False, True])
def test_native_gmsh_imports_tet10_ascii_and_binary(tmp_path: Path, binary: bool) -> None:
    pytest.importorskip("gmsh")
    mesh = BenchmarkMeshFactory().box_tetra(
        tmp_path / f"tet10_{'binary' if binary else 'ascii'}.msh",
        length=1.0,
        width=0.4,
        height=0.3,
        mesh_size=0.24,
        order=2,
        binary=binary,
    )
    setup = tmp_path / "tet10.setup.json"
    _write_json(setup, _solid_setup("TET10"))
    imported = import_gmsh_model(mesh, setup)
    assert imported.report.binary is binary
    assert imported.report.element_family == "TET10"
    assert imported.report.orientation_repairs == 0
    assert solve_model(imported.model).status == "PASS"


@pytest.mark.parametrize("binary", [False, True])
def test_native_gmsh_imports_mitc4_ascii_and_binary(tmp_path: Path, binary: bool) -> None:
    pytest.importorskip("gmsh")
    nodes = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]])
    mesh = BenchmarkMeshFactory().discrete_mitc4(
        tmp_path / f"mitc4_{'binary' if binary else 'ascii'}.msh",
        nodes=nodes,
        quads=np.asarray([[0, 1, 2, 3]], dtype=int),
        line_groups={"fixed": [(3, 0)], "loaded": [(1, 2)]},
        binary=binary,
    )
    setup = tmp_path / "mitc4.setup.json"
    _write_json(setup, _shell_setup())
    imported = import_gmsh_model(mesh, setup)
    assert imported.report.binary is binary
    assert imported.report.element_family == "MITC4"
    assert len(imported.model.distributed_loads) == 1
    assert solve_model(imported.model).status == "PASS"


def test_cli_imports_binary_tet10(tmp_path: Path) -> None:
    pytest.importorskip("gmsh")
    mesh = BenchmarkMeshFactory().box_tetra(
        tmp_path / "tet10_binary.msh",
        length=1.0,
        width=0.4,
        height=0.3,
        mesh_size=0.28,
        order=2,
        binary=True,
    )
    setup = tmp_path / "tet10.setup.json"
    output = tmp_path / "tet10.json"
    report = tmp_path / "tet10.report.json"
    _write_json(setup, _solid_setup("TET10"))
    completed = subprocess.run(
        [
            sys.executable,
            "qf_solver.py",
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
    assert json.loads(report.read_text(encoding="utf-8"))["binary"] is True


def _solid_setup(family: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": "SI"},
        "verification_profile": "engineering",
        "analysis": {"type": "linear_static", "method": "direct"},
        "materials": {"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
        "groups": [
            {
                "name": "domain",
                "dimension": 3,
                "actions": [{"type": "elements", "element_type": family, "material": "steel"}],
            },
            {"name": "x_min", "dimension": 2, "actions": [{"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ"]}]},
            {"name": "x_max", "dimension": 2, "actions": [{"type": "pressure", "value": 1000.0}]},
        ],
    }


def _shell_setup() -> dict[str, object]:
    return {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": "SI"},
        "verification_profile": "engineering",
        "analysis": {"type": "linear_static", "method": "direct"},
        "materials": {"skin": {"type": "shell_isotropic", "E": 70.0e9, "nu": 0.3, "t": 0.01}},
        "groups": [
            {
                "name": "shell",
                "dimension": 2,
                "actions": [{"type": "elements", "element_type": "MITC4", "material": "skin"}],
            },
            {
                "name": "fixed",
                "dimension": 1,
                "actions": [{"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}],
            },
            {
                "name": "loaded",
                "dimension": 1,
                "actions": [{"type": "edge_traction", "value": [0.0, 0.0, -100.0]}],
            },
        ],
    }


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

