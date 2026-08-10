from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from solveur.api.public import solve_model
from solveur.verification.orthotropic_complex_mesh import (
    OrthotropicComplexCase,
    OrthotropicComplexMeshFactory,
)
from solveur.verification.orthotropic_external import (
    code_aster_orthotropic_commands,
    write_calculix_orthotropic_input,
)


ROOT = Path(__file__).resolve().parents[2]


def _case(path: Path) -> OrthotropicComplexCase:
    return OrthotropicComplexCase(
        identifier="TEST-ORTHO",
        nodes=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]),
        elements=np.array([[0, 1, 2, 3]], dtype=np.int64),
        fixed_nodes=np.array([0, 2, 3]),
        loaded_nodes=np.array([1]),
        load_component=0,
        total_load=100.0,
        angle_deg=30.0,
        mesh_path=path,
    )


def test_calculix_deck_contains_oriented_engineering_constants(tmp_path: Path) -> None:
    text = write_calculix_orthotropic_input(tmp_path / "case.inp", _case(tmp_path / "case.msh")).read_text(
        encoding="ascii"
    )
    assert "*ELEMENT,TYPE=C3D4" in text
    assert "*ELASTIC,TYPE=ENGINEERING CONSTANTS" in text
    assert "*SOLID SECTION,ELSET=EALL,MATERIAL=ORTHO,ORIENTATION=MAT_ORIENTATION" in text
    assert "3,30" in text


def test_code_aster_commands_contain_orthotropy_and_euler_orientation(tmp_path: Path) -> None:
    text = code_aster_orthotropic_commands(_case(tmp_path / "case.msh"))
    assert "ELAS_ORTH" in text
    assert "E_L=1.35e11" in text
    assert "ANGL_EULER=(30" in text
    assert "CARA_ELEM=orientation" in text
    assert 'GROUP_NO="LOADED", FX=100' in text


@pytest.mark.skipif(importlib.util.find_spec("gmsh") is None, reason="gmsh is optional")
def test_complex_meshes_are_positive_and_solvable(tmp_path: Path) -> None:
    factory = OrthotropicComplexMeshFactory()
    cases = (
        factory.perforated_coupon(tmp_path / "coupon.msh", mesh_size=0.55),
        factory.l_bracket(tmp_path / "bracket.msh", mesh_size=0.50),
    )
    for case in cases:
        determinants = [
            np.linalg.det((case.nodes[element[1:]] - case.nodes[element[0]]).T) for element in case.elements
        ]
        assert min(determinants) > 0.0
        assert case.fixed_nodes.size >= 4
        assert case.loaded_nodes.size >= 4
        result = solve_model(case.qf_model())
        assert result.status == "PASS"
        assert np.all(np.isfinite(result.displacements))


def test_controlled_external_evidence_is_complete() -> None:
    reference = ROOT / "qualification" / "vnv" / "external" / "orthotropic_solids" / "reference"
    summary = json.loads((reference / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((reference / "vnv_manifest.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert summary["covered_specifications"] == ["SPEC-COMP-SOLID-007"]
    assert len(summary["cases"]) == 2
    assert all(check["status"] == "PASS" for check in summary["checks"])
    for entry in manifest["files"]:
        artifact = reference / entry["path"]
        assert artifact.is_file(), entry["path"]
        assert artifact.stat().st_size == entry["size_bytes"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == entry["sha256"]
