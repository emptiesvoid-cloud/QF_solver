from __future__ import annotations

import json
from typing import Any, cast

import pytest

from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.verification.j2_multifamily_performance import (
    J2MultiFamilyPerformanceCampaign,
    _j2_cyclic_setup,
)
from solveur.verification.j2_structural import J2StructuralCyclicCampaign


@pytest.mark.parametrize(("order", "family", "nodes_per_element"), [(1, "HEX8", 8), (2, "HEX20", 20)])
def test_structured_hexa_generator_imports_expected_family(
    tmp_path, order: int, family: str, nodes_per_element: int
) -> None:
    pytest.importorskip("gmsh")
    mesh = BenchmarkMeshFactory().box_hexa(
        tmp_path / f"{family.lower()}.msh",
        length=1.0,
        width=0.2,
        height=0.2,
        cells=(6, 2, 2),
        order=order,
        anchors=True,
    )
    setup_path = tmp_path / f"{family.lower()}.setup.json"
    setup_path.write_text(json.dumps(_j2_setup(family)), encoding="utf-8")

    imported = GmshModelImporter().import_model(mesh, setup_path)
    assert imported.report.status == "PASS", imported.report.warnings
    assert imported.report.element_family == family
    assert imported.model.elements
    assert len(imported.model.elements) == 24
    assert imported.model.node_count == (63 if family == "HEX8" else 201)
    assert {element.type for element in imported.model.elements} == {family}
    assert all(len(element.nodes) == nodes_per_element for element in imported.model.elements)
    assert len(imported.model.distributed_loads) == 4
    assert imported.model.analysis.type == "nonlinear_static"


@pytest.mark.parametrize(
    ("dimensions", "cells", "order"),
    [((0.0, 1.0, 1.0), (1, 1, 1), 1), ((1.0, 1.0, 1.0), (1, 0, 1), 1), ((1.0, 1.0, 1.0), (1, 1, 1), 3)],
)
def test_structured_hexa_generator_rejects_invalid_configuration(
    tmp_path, dimensions: tuple[float, float, float], cells: tuple[int, int, int], order: int
) -> None:
    with pytest.raises(ValueError):
        BenchmarkMeshFactory().box_hexa(
            tmp_path / "invalid.msh",
            length=dimensions[0],
            width=dimensions[1],
            height=dimensions[2],
            cells=cells,
            order=order,
        )


@pytest.mark.parametrize("family", J2MultiFamilyPerformanceCampaign.element_types)
def test_multifamily_setup_keeps_common_j2_case(family: str) -> None:
    setup = _j2_cyclic_setup(family)
    baseline = cast(dict[str, Any], J2StructuralCyclicCampaign._setup("TET4"))
    assert setup["analysis"]["load_path"] == baseline["analysis"]["load_path"]
    assert setup["analysis"]["tolerance"] == 1.0e-7
    assert setup["materials"] == baseline["materials"]
    assert setup["groups"][1:] == baseline["groups"][1:]
    assert setup["groups"][0]["actions"][0]["element_type"] == family


def test_tetra_case_import_records_only_known_unused_surface_groups(tmp_path) -> None:
    pytest.importorskip("gmsh")
    mesh = BenchmarkMeshFactory().box_tetra(
        tmp_path / "tet4.msh",
        length=1.0,
        width=0.2,
        height=0.2,
        mesh_size=0.4,
        order=1,
        anchors=True,
        include_anchor_x=False,
    )
    setup_path = tmp_path / "tet4.setup.json"
    setup_path.write_text(json.dumps(_j2_setup("TET4")), encoding="utf-8")
    imported = GmshModelImporter().import_model(mesh, setup_path)
    assert imported.report.status == "WARNING"
    assert imported.report.mesh_status == "PASS"
    assert set(imported.report.warnings) == {
        "Physical group 'y_min' (dimension 2) is unused.",
        "Physical group 'z_min' (dimension 2) is unused.",
    }


def _j2_setup(family: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": "SI"},
        "verification_profile": "engineering",
        "analysis": {"type": "nonlinear_static", "method": "newton_raphson", "load_steps": 1},
        "materials": {
            "j2": {
                "type": "von_mises_elastoplastic_3d",
                "E": 210.0e9,
                "nu": 0.3,
                "yield_stress": 250.0e6,
                "hardening_modulus": 50.0e9,
            }
        },
        "groups": [
            {
                "name": "domain",
                "dimension": 3,
                "actions": [{"type": "elements", "element_type": family, "material": "j2"}],
            },
            {"name": "x_min", "dimension": 2, "actions": [{"type": "fixed_dofs", "dofs": ["UX"]}]},
            {"name": "anchor_origin", "dimension": 0, "actions": [{"type": "fixed_dofs", "dofs": ["UY", "UZ"]}]},
            {"name": "anchor_xy", "dimension": 0, "actions": [{"type": "fixed_dofs", "dofs": ["UZ"]}]},
            {"name": "x_max", "dimension": 2, "actions": [{"type": "surface_traction", "value": [300.0e6, 0.0, 0.0]}]},
        ],
    }
