from __future__ import annotations

from pathlib import Path

from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.mesh.gmsh_types import GmshCell, GmshMeshData, GmshPhysicalGroup


def test_gmsh_hex8_and_quad4_faces_use_the_standard_import_path() -> None:
    nodes = {
        1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0), 3: (1.0, 1.0, 0.0), 4: (0.0, 1.0, 0.0),
        5: (0.0, 0.0, 1.0), 6: (1.0, 0.0, 1.0), 7: (1.0, 1.0, 1.0), 8: (0.0, 1.0, 1.0),
    }
    cells = {
        1: GmshCell(1, 5, 3, 1, "Hexahedron 8", tuple(range(1, 9))),
        2: GmshCell(2, 3, 2, 1, "Quadrangle 4", (1, 4, 3, 2)),
        3: GmshCell(3, 3, 2, 1, "Quadrangle 4", (5, 6, 7, 8)),
    }
    groups = {
        (3, "domain"): GmshPhysicalGroup("domain", 3, 1, (1,), tuple(nodes)),
        (2, "fixed"): GmshPhysicalGroup("fixed", 2, 2, (2,), (1, 2, 3, 4)),
        (2, "top"): GmshPhysicalGroup("top", 2, 3, (3,), (5, 6, 7, 8)),
    }
    mesh = GmshMeshData(Path("hex8.msh"), "4.1", False, "test", nodes, cells, groups)
    setup = {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "materials": {"solid": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
        "groups": [
            {"name": "domain", "dimension": 3, "actions": [{"type": "elements", "element_type": "HEX8", "material": "solid"}]},
            {"name": "fixed", "dimension": 2, "actions": [{"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ"]}]},
            {"name": "top", "dimension": 2, "actions": [{"type": "pressure", "value": 2.0}]},
        ],
    }
    imported = GmshModelImporter().from_data(mesh, setup)
    assert imported.report.status == "PASS"
    assert imported.report.element_family == "HEX8"
    assert imported.model.elements[0].type == "HEX8"
    assert imported.model.distributed_loads[0].type == "pressure"
    assert imported.model.distributed_loads[0].face == 1
