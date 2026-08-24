from __future__ import annotations

from pathlib import Path

from solveur.api import solve_model
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.mesh.gmsh_types import GmshCell, GmshMeshData, GmshPhysicalGroup


def test_gmsh_hex20_and_quad8_faces_use_the_standard_import_path() -> None:
    corners = {
        1: (0.0, 0.0, 0.0),
        2: (1.0, 0.0, 0.0),
        3: (1.0, 1.0, 0.0),
        4: (0.0, 1.0, 0.0),
        5: (0.0, 0.0, 1.0),
        6: (1.0, 0.0, 1.0),
        7: (1.0, 1.0, 1.0),
        8: (0.0, 1.0, 1.0),
    }
    edge_pairs = ((1, 2), (1, 4), (1, 5), (2, 3), (2, 6), (3, 4), (3, 7), (4, 8), (5, 6), (5, 8), (6, 7), (7, 8))
    nodes = dict(corners)
    for index, (first, second) in enumerate(edge_pairs, start=9):
        nodes[index] = tuple((a + b) / 2.0 for a, b in zip(nodes[first], nodes[second]))
    cells = {
        1: GmshCell(1, 17, 3, 2, "Hexahedron 20", tuple(range(1, 21))),
        2: GmshCell(2, 16, 2, 2, "Quadrangle 8", (5, 6, 7, 8, 17, 19, 20, 18)),
        3: GmshCell(3, 16, 2, 2, "Quadrangle 8", (1, 4, 3, 2, 10, 14, 12, 9)),
    }
    groups = {
        (3, "domain"): GmshPhysicalGroup("domain", 3, 1, (1,), tuple(nodes)),
        (2, "fixed"): GmshPhysicalGroup("fixed", 2, 2, (3,), (1, 2, 3, 4, 9, 10, 12, 14)),
        (2, "top"): GmshPhysicalGroup("top", 2, 3, (2,), (5, 6, 7, 8, 17, 18, 19, 20)),
    }
    mesh = GmshMeshData(Path("hex20.msh"), "4.1", False, "test", nodes, cells, groups)
    setup = {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "materials": {"solid": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
        "groups": [
            {"name": "domain", "dimension": 3, "actions": [{"type": "elements", "element_type": "HEX20", "material": "solid"}]},
            {"name": "fixed", "dimension": 2, "actions": [{"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ"]}]},
            {"name": "top", "dimension": 2, "actions": [{"type": "pressure", "value": 2.0}]},
        ],
    }
    imported = GmshModelImporter().from_data(mesh, setup)
    assert imported.report.status == "PASS"
    assert imported.report.element_family == "HEX20"
    assert imported.model.elements[0].type == "HEX20"
    assert imported.model.distributed_loads[0].face == 1
    assert solve_model(imported.model).status == "PASS"
