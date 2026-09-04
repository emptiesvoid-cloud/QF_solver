"""Dependency-free contract checks for the optional Gmsh import boundary."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from solveur.core.errors import InputValidationError, MeshValidationError
from solveur.mesh.gmsh_importer import (
    GmshModelImporter,
    _cell_family,
    _dimension,
    _finite_float,
    _oriented_connectivities,
    _positive_float,
    _edge_targets,
    _surface_targets,
    _solid_face_map,
    _vector,
    _validate_setup,
)
from solveur.mesh.gmsh_reader import GmshNativeReader, _msh_header
from solveur.mesh.gmsh_types import GmshCell, GmshMeshData, GmshPhysicalGroup


@pytest.mark.parametrize("value", ["bad", -1, 4, None])
def test_gmsh_dimension_rejects_invalid_values(value: object) -> None:
    with pytest.raises(InputValidationError, match="integer from 0 to 3"):
        _dimension(value, "dimension")


@pytest.mark.parametrize("value", ["bad", float("nan"), float("inf")])
def test_gmsh_finite_and_positive_scalars_reject_invalid_values(value: object) -> None:
    with pytest.raises(InputValidationError, match="finite"):
        _finite_float(value, "value")
    with pytest.raises(InputValidationError):
        _positive_float(value, "value")


def test_gmsh_vector_requires_three_finite_components() -> None:
    assert _vector([1, 2, 3]) == (1.0, 2.0, 3.0)
    for value in (None, [1, 2], [1, 2, float("nan")]):
        with pytest.raises(InputValidationError):
            _vector(value)


@pytest.mark.parametrize(
    "cell, family",
    [
        (GmshCell(1, 1, 3, 1, "Tetrahedron 4", (1, 2, 3, 4)), "TET4"),
        (GmshCell(1, 1, 3, 2, "Tetrahedron 10", tuple(range(1, 11))), "TET10"),
        (GmshCell(1, 1, 3, 1, "Hexahedron 8", tuple(range(1, 9))), "HEX8"),
        (GmshCell(1, 17, 3, 2, "Hexahedron 20", tuple(range(1, 21))), "HEX20"),
        (GmshCell(1, 1, 2, 1, "Triangle 3", (1, 2, 3)), "MITC3"),
        (GmshCell(1, 1, 2, 1, "Quadrangle 4", (1, 2, 3, 4)), "MITC4"),
        (GmshCell(1, 1, 1, 1, "Line 2", (1, 2)), None),
    ],
)
def test_gmsh_cell_family_mapping_is_explicit(cell: GmshCell, family: str | None) -> None:
    assert _cell_family(cell) == family


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"unknown": 1}, "Unknown Gmsh companion"),
        ({"mesh_scale_to_m": 0.0}, "strictly positive"),
        ({"materials": {}}, "materials"),
        ({"groups": []}, "groups"),
        ({"groups": ["bad"]}, "must be an object"),
        ({"groups": [{"name": "x", "dimension": 2, "actions": []}]}, "requires actions"),
        ({"groups": [{"name": "x", "dimension": 2, "actions": [{"type": "nope"}]}]}, "Unsupported"),
    ],
)
def test_gmsh_companion_setup_rejects_invalid_contracts(changes: dict[str, object], message: str) -> None:
    setup = {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "materials": {"m": {"type": "isotropic_3d", "E": 1.0, "nu": 0.3}},
        "groups": [{"name": "domain", "dimension": 3, "actions": [{"type": "elements", "element_type": "TET4", "material": "m"}]}],
    }
    setup.update(changes)
    with pytest.raises(InputValidationError, match=message):
        _validate_setup(setup)


def test_gmsh_setup_accepts_minimal_normalized_definition_and_rejects_duplicate_groups() -> None:
    setup = {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "materials": {"m": {"type": "isotropic_3d", "E": 1.0, "nu": 0.3}},
        "groups": [{"name": "domain", "dimension": 3, "actions": [{"type": "elements", "element_type": "TET4", "material": "m"}]}],
    }
    normalized, warnings = _validate_setup(setup)
    assert normalized["mesh_scale_to_m"] == 1.0
    assert warnings == []
    duplicate = {**setup, "groups": setup["groups"] * 2}
    with pytest.raises(InputValidationError, match="Duplicate"):
        _validate_setup(duplicate)


def test_gmsh_native_header_and_missing_file_contracts(tmp_path: Path) -> None:
    bad = tmp_path / "bad.msh"
    bad.write_bytes(b"not gmsh")
    with pytest.raises(InputValidationError, match="not a readable"):
        _msh_header(bad)
    bad.write_bytes(b"$MeshFormat\n2.2 0 8\n$EndMeshFormat\n")
    assert _msh_header(bad) == ("2.2", False)
    with pytest.raises(InputValidationError, match="does not exist"):
        GmshNativeReader().read(tmp_path / "missing.msh")


class _FakeGmshMesh:
    def getNodes(self, *args):
        return np.asarray([2, 1]), np.asarray([1.0, 0.0, 0.0, 0.0, 0.0, 0.0]), np.asarray([])

    def getElements(self, *args):
        return [4], [np.asarray([2])], [np.asarray([2, 1, 1, 2])]

    def getElementProperties(self, _):
        return ("Tetrahedron 4", 3, 1, 4, 0, "")


def test_gmsh_native_reader_rejects_duplicate_nodes_and_bad_connectivity() -> None:
    fake = SimpleNamespace(model=SimpleNamespace(mesh=_FakeGmshMesh()))
    assert GmshNativeReader._nodes(fake) == {1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0)}
    with pytest.raises(MeshValidationError, match="Duplicate Gmsh element tag"):
        GmshNativeReader._cells(SimpleNamespace(model=SimpleNamespace(mesh=SimpleNamespace(
            getElements=lambda: ([4, 4], [np.asarray([1]), np.asarray([1])], [np.asarray([1, 2, 3, 4]), np.asarray([1, 2, 3, 4])]),
            getElementProperties=lambda _: ("Tetrahedron 4", 3, 1, 4, 0, ""),
        ))))


def test_gmsh_orientation_and_face_maps_cover_tet_path() -> None:
    nodes = {1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0), 3: (0.0, 1.0, 0.0), 4: (0.0, 0.0, 1.0)}
    cells = {1: GmshCell(1, 4, 3, 1, "Tetrahedron 4", (1, 3, 2, 4))}
    mesh = GmshMeshData(Path("mesh.msh"), "4.1", False, "test", nodes, cells, {})
    with pytest.raises(MeshValidationError, match="inverted"):
        _oriented_connectivities(mesh, {1: "m"}, {1: "TET4"}, False)
    repaired, count = _oriented_connectivities(mesh, {1: "m"}, {1: "TET4"}, True)
    assert count == 1
    assert repaired[1] == (1, 2, 3, 4)
    faces = _solid_face_map({1: "TET4"}, repaired, {1: 0})
    assert len(faces) == 4


def test_gmsh_importer_reads_setup_errors_before_touching_optional_dependency(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(InputValidationError, match="does not exist"):
        GmshModelImporter().import_model("missing.msh", missing)


def test_gmsh_surface_and_edge_target_mapping_covers_shell_and_solid_boundaries() -> None:
    shell_mesh = GmshMeshData(
        Path("shell.msh"), "4.1", False, "test",
        {1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0), 3: (1.0, 1.0, 0.0), 4: (0.0, 1.0, 0.0)},
        {1: GmshCell(1, 1, 2, 1, "Quadrangle 4", (1, 2, 3, 4)), 2: GmshCell(2, 1, 1, 1, "Line 2", (1, 2))},
        {},
    )
    shell_group = GmshPhysicalGroup("surface", 2, 1, (1,), (1, 2, 3, 4))
    assert _surface_targets(shell_mesh, shell_group, {1: "MITC4"}, {}, {1: 0}) == [(0, None)]
    assert _edge_targets(shell_mesh, GmshPhysicalGroup("edge", 1, 2, (2,), (1, 2)), {frozenset({1, 2}): [(0, 0)]}) == [(0, 0)]

    solid_mesh = GmshMeshData(
        Path("solid.msh"), "4.1", False, "test",
        {1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0), 3: (0.0, 1.0, 0.0), 4: (0.0, 0.0, 1.0)},
        {
            1: GmshCell(1, 1, 3, 1, "Tetrahedron 4", (1, 2, 3, 4)),
            2: GmshCell(2, 1, 2, 1, "Triangle 3", (2, 3, 4)),
        },
        {},
    )
    solid_group = GmshPhysicalGroup("face", 2, 3, (2,), (2, 3, 4))
    assert _surface_targets(solid_mesh, solid_group, {1: "TET4"}, {frozenset({2, 3, 4}): [(0, 0)]}, {1: 0}) == [(0, 0)]


def test_gmsh_boundary_target_mapping_rejects_empty_groups() -> None:
    mesh = GmshMeshData(Path("mesh.msh"), "4.1", False, "test", {}, {}, {})
    group = GmshPhysicalGroup("empty", 2, 1, (), ())
    with pytest.raises(MeshValidationError, match="no shell elements"):
        _surface_targets(mesh, group, {1: "MITC4"}, {}, {})
    with pytest.raises(MeshValidationError, match="no boundary edges"):
        _edge_targets(mesh, GmshPhysicalGroup("empty", 1, 1, (), ()), {})
