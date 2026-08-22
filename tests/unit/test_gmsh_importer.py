from __future__ import annotations

from pathlib import Path

import pytest

from solveur.core.errors import InfrastructureError, InputValidationError, MeshValidationError
from solveur.io.json_reader import JsonModelReader
from solveur.io.model_writer import JsonModelWriter
from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.mesh.gmsh_importer import GmshModelImporter, _portable_input_path
from solveur.mesh.gmsh_reader import GmshNativeReader
from solveur.mesh.gmsh_types import GmshCell, GmshMeshData, GmshPhysicalGroup


def test_tet4_groups_map_material_constraints_and_pressure(tmp_path: Path) -> None:
    mesh = _tet4_mesh()
    setup = _tet_setup("TET4")
    setup["groups"].append(
        {
            "name": "loaded",
            "dimension": 2,
            "actions": [{"type": "pressure", "value": 12.0}],
        }
    )
    imported = GmshModelImporter().from_data(mesh, setup)
    assert imported.report.status == "PASS"
    assert imported.report.element_family == "TET4"
    assert imported.report.action_counts == {"elements": 1, "fixed_dofs": 3, "pressure": 1}
    assert imported.model.elements[0].nodes == (0, 1, 2, 3)
    pressure = imported.model.distributed_loads[0]
    assert pressure.element == 0
    assert pressure.face == 0
    assert pressure.value == 12.0

    path = tmp_path / "imported.json"
    JsonModelWriter().write(imported.model, path)
    reloaded = JsonModelReader().read(path)
    assert reloaded.nodes.tolist() == imported.model.nodes.tolist()
    assert reloaded.distributed_loads == imported.model.distributed_loads


def test_gmsh_import_provenance_never_exposes_an_absolute_workstation_path(tmp_path: Path) -> None:
    assert _portable_input_path(tmp_path / "private" / "model.msh") == "model.msh"
    assert _portable_input_path("relative/model.setup.json") == "relative/model.setup.json"
    assert _portable_input_path("<memory>") == "<memory>"


def test_inverted_tet4_requires_explicit_repair() -> None:
    mesh = _tet4_mesh(connectivity=(1, 3, 2, 4), include_loaded=False)
    with pytest.raises(MeshValidationError, match="inverted"):
        GmshModelImporter().from_data(mesh, _tet_setup("TET4"))
    imported = GmshModelImporter().from_data(
        mesh,
        _tet_setup("TET4"),
        repair_tetra_orientation=True,
    )
    assert imported.report.orientation_repairs == 1
    assert imported.model.elements[0].nodes == (0, 1, 2, 3)


def test_tet10_repair_permutes_corner_and_midside_nodes() -> None:
    nodes = {
        1: (0.0, 0.0, 0.0),
        2: (1.0, 0.0, 0.0),
        3: (0.0, 1.0, 0.0),
        4: (0.0, 0.0, 1.0),
        5: (0.5, 0.0, 0.0),
        6: (0.5, 0.5, 0.0),
        7: (0.0, 0.5, 0.0),
        8: (0.0, 0.0, 0.5),
        9: (0.5, 0.0, 0.5),
        10: (0.0, 0.5, 0.5),
    }
    # Native Gmsh TET10 ordering stores edges (2, 3) and (3, 1) last.
    cells = {1: GmshCell(1, 11, 3, 2, "Tetrahedron 10", (1, 3, 2, 4, 7, 6, 5, 8, 9, 10))}
    cells.update(_point_cells((1, 2, 3), first_tag=20))
    groups = {
        (3, "domain"): GmshPhysicalGroup("domain", 3, 1, (1,), tuple(nodes)),
        (0, "fixed"): GmshPhysicalGroup("fixed", 0, 2, (20, 21, 22), (1, 2, 3)),
    }
    mesh = GmshMeshData(Path("tet10.msh"), "4.1", False, "test", nodes, cells, groups)
    imported = GmshModelImporter().from_data(mesh, _tet_setup("TET10"), repair_tetra_orientation=True)
    assert imported.report.orientation_repairs == 1
    assert imported.model.elements[0].nodes == (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)


def test_mitc4_line_groups_map_edge_traction() -> None:
    nodes = {1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0), 3: (1.0, 1.0, 0.0), 4: (0.0, 1.0, 0.0)}
    cells = {
        1: GmshCell(1, 3, 2, 1, "Quadrangle 4", (1, 2, 3, 4)),
        10: GmshCell(10, 1, 1, 1, "Line 2", (1, 2)),
        11: GmshCell(11, 1, 1, 1, "Line 2", (3, 4)),
    }
    groups = {
        (2, "shell"): GmshPhysicalGroup("shell", 2, 1, (1,), (1, 2, 3, 4)),
        (1, "fixed"): GmshPhysicalGroup("fixed", 1, 2, (10,), (1, 2)),
        (1, "loaded_edge"): GmshPhysicalGroup("loaded_edge", 1, 3, (11,), (3, 4)),
    }
    mesh = GmshMeshData(Path("shell.msh"), "4.1", False, "test", nodes, cells, groups)
    setup = {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "materials": {"skin": {"type": "shell_isotropic", "E": 2.1e11, "nu": 0.3, "t": 0.01}},
        "groups": [
            {"name": "shell", "dimension": 2, "actions": [{"type": "elements", "element_type": "MITC4", "material": "skin"}]},
            {"name": "fixed", "dimension": 1, "actions": [{"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}]},
            {"name": "loaded_edge", "dimension": 1, "actions": [{"type": "edge_traction", "value": [0.0, 0.0, -2.0]}]},
        ],
    }
    imported = GmshModelImporter().from_data(mesh, setup)
    edge_load = imported.model.distributed_loads[0]
    assert edge_load.element == 0
    assert edge_load.edge == 2
    assert edge_load.value == (0.0, 0.0, -2.0)


def test_mitc3_surface_and_line_groups_map_to_triangle_shell() -> None:
    nodes = {1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0), 3: (0.0, 1.0, 0.0)}
    cells = {
        1: GmshCell(1, 2, 2, 1, "Triangle 3", (1, 2, 3)),
        10: GmshCell(10, 1, 1, 1, "Line 2", (1, 2)),
        11: GmshCell(11, 1, 1, 1, "Line 2", (2, 3)),
    }
    groups = {
        (2, "shell"): GmshPhysicalGroup("shell", 2, 1, (1,), (1, 2, 3)),
        (1, "fixed"): GmshPhysicalGroup("fixed", 1, 2, (10,), (1, 2)),
        (1, "loaded_edge"): GmshPhysicalGroup("loaded_edge", 1, 3, (11,), (2, 3)),
    }
    mesh = GmshMeshData(Path("tri3.msh"), "4.1", False, "test", nodes, cells, groups)
    setup = {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "materials": {
            "skin": {
                "type": "shell_isotropic",
                "E": 2.1e11,
                "nu": 0.3,
                "t": 0.01,
            }
        },
        "groups": [
            {
                "name": "shell",
                "dimension": 2,
                "actions": [{"type": "elements", "element_type": "MITC3", "material": "skin"}],
            },
            {
                "name": "fixed",
                "dimension": 1,
                "actions": [
                    {"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}
                ],
            },
            {
                "name": "loaded_edge",
                "dimension": 1,
                "actions": [{"type": "edge_traction", "value": [0.0, 0.0, -2.0]}],
            },
        ],
    }
    imported = GmshModelImporter().from_data(mesh, setup)
    assert imported.report.element_family == "MITC3"
    assert imported.model.elements[0].type == "MITC3"
    edge_load = imported.model.distributed_loads[0]
    assert edge_load.element == 0
    assert edge_load.edge == 1


def test_mixed_mitc3_mitc4_shell_import_preserves_family_and_interface_orientation() -> None:
    nodes = {
        1: (0.0, 0.0, 0.0),
        2: (1.0, 0.0, 0.0),
        3: (1.0, 1.0, 0.0),
        4: (0.0, 1.0, 0.0),
        5: (2.0, 0.0, 0.0),
        6: (2.0, 1.0, 0.0),
    }
    cells = {
        1: GmshCell(1, 3, 2, 1, "Quadrangle 4", (1, 2, 3, 4)),
        2: GmshCell(2, 2, 2, 1, "Triangle 3", (2, 5, 3)),
        3: GmshCell(3, 2, 2, 1, "Triangle 3", (5, 6, 3)),
        10: GmshCell(10, 1, 1, 1, "Line 2", (1, 4)),
    }
    groups = {
        (2, "quads"): GmshPhysicalGroup("quads", 2, 1, (1,), (1, 2, 3, 4)),
        (2, "triangles"): GmshPhysicalGroup("triangles", 2, 2, (2, 3), (2, 3, 5, 6)),
        (1, "fixed"): GmshPhysicalGroup("fixed", 1, 3, (10,), (1, 4)),
    }
    mesh = GmshMeshData(Path("mixed_shell.msh"), "4.1", False, "test", nodes, cells, groups)
    material = {"type": "shell_isotropic", "E": 2.1e11, "nu": 0.3, "t": 0.01}
    setup = {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "materials": {"skin": material},
        "groups": [
            {
                "name": "quads",
                "dimension": 2,
                "actions": [{"type": "elements", "element_type": "MITC4", "material": "skin"}],
            },
            {
                "name": "triangles",
                "dimension": 2,
                "actions": [{"type": "elements", "element_type": "MITC3", "material": "skin"}],
            },
            {
                "name": "fixed",
                "dimension": 1,
                "actions": [
                    {"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}
                ],
            },
        ],
    }
    imported = GmshModelImporter().from_data(mesh, setup)
    assert imported.report.element_family == "MITC3+MITC4"
    assert [element.type for element in imported.model.elements] == ["MITC4", "MITC3", "MITC3"]
    assert imported.report.orientation_repairs == 0


def test_missing_physical_group_is_rejected() -> None:
    setup = _tet_setup("TET4")
    setup["groups"][0]["name"] = "missing"
    with pytest.raises(MeshValidationError, match="does not exist"):
        GmshModelImporter().from_data(_tet4_mesh(), setup)


def test_native_reader_reports_missing_gmsh_dependency(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mesh = tmp_path / "minimal.msh"
    mesh.write_text("$MeshFormat\n4.1 0 8\n$EndMeshFormat\n", encoding="ascii")

    def unavailable() -> object:
        raise InfrastructureError("gmsh unavailable")

    monkeypatch.setattr("solveur.mesh.gmsh_reader._gmsh_module", unavailable)
    with pytest.raises(InfrastructureError, match="unavailable"):
        GmshNativeReader().read(mesh)


def test_native_reader_rejects_corrupted_msh_header(tmp_path: Path) -> None:
    mesh = tmp_path / "corrupted.msh"
    mesh.write_bytes(b"not a gmsh file")
    with pytest.raises(InputValidationError, match="readable Gmsh"):
        GmshNativeReader().read(mesh)


def test_native_reader_preserves_distinct_point_group_nodes(tmp_path: Path) -> None:
    pytest.importorskip("gmsh")
    mesh_path = BenchmarkMeshFactory().box_tetra(
        tmp_path / "anchored_box.msh",
        length=2.0,
        width=1.0,
        height=0.2,
        mesh_size=0.34,
        anchors=True,
    )

    mesh = GmshNativeReader().read(mesh_path)
    anchor_coordinates = {
        name: mesh.nodes[group.node_tags[0]]
        for (dimension, name), group in mesh.groups.items()
        if dimension == 0 and name in {"anchor_origin", "anchor_x", "anchor_xy"}
    }

    assert set(anchor_coordinates) == {"anchor_origin", "anchor_x", "anchor_xy"}
    assert len(set(anchor_coordinates.values())) == 3
    assert anchor_coordinates["anchor_origin"] == (0.0, 0.0, 0.0)
    assert anchor_coordinates["anchor_x"] == (2.0, 0.0, 0.0)
    assert anchor_coordinates["anchor_xy"] == (0.0, 1.0, 0.0)


def _tet_setup(family: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": "SI"},
        "verification_profile": "engineering",
        "analysis": {"type": "linear_static", "method": "direct"},
        "materials": {"steel": {"type": "isotropic_3d", "E": 2.1e11, "nu": 0.3, "density": 7800.0}},
        "groups": [
            {"name": "domain", "dimension": 3, "actions": [{"type": "elements", "element_type": family, "material": "steel"}]},
            {"name": "fixed", "dimension": 0, "actions": [{"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ"]}]},
        ],
    }


def _tet4_mesh(
    connectivity: tuple[int, ...] = (1, 2, 3, 4),
    *,
    include_loaded: bool = True,
) -> GmshMeshData:
    nodes = {1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0), 3: (0.0, 1.0, 0.0), 4: (0.0, 0.0, 1.0)}
    cells = {1: GmshCell(1, 4, 3, 1, "Tetrahedron 4", connectivity)}
    cells.update(_point_cells((1, 2, 3), first_tag=20))
    groups = {
        (3, "domain"): GmshPhysicalGroup("domain", 3, 1, (1,), (1, 2, 3, 4)),
        (0, "fixed"): GmshPhysicalGroup("fixed", 0, 2, (20, 21, 22), (1, 2, 3)),
    }
    if include_loaded:
        cells[10] = GmshCell(10, 2, 2, 1, "Triangle 3", (2, 3, 4))
        groups[(2, "loaded")] = GmshPhysicalGroup("loaded", 2, 3, (10,), (2, 3, 4))
    return GmshMeshData(Path("tet4.msh"), "4.1", False, "test", nodes, cells, groups)


def _point_cells(nodes: tuple[int, ...], *, first_tag: int) -> dict[int, GmshCell]:
    return {
        first_tag + index: GmshCell(first_tag + index, 15, 0, 0, "Point", (node,))
        for index, node in enumerate(nodes)
    }
