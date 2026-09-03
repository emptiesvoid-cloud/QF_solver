from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from solveur.core.errors import InfrastructureError, InputValidationError, MeshValidationError
from solveur.mesh.gmsh_reader import GmshNativeReader, _gmsh_module


class _RuntimeMesh:
    def getNodes(self, *args):
        if args:
            return np.asarray([1]), np.asarray([0.0, 0.0, 0.0]), np.asarray([])
        return np.asarray([1, 2, 3, 4]), np.asarray([0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]), np.asarray([])

    def getElements(self, *args):
        if args and args[0] == 0:
            return [], [], [np.asarray([1])]
        if args:
            return [], [np.asarray([1])], []
        return [4], [np.asarray([1])], [np.asarray([1, 2, 3, 4])]

    def getElementProperties(self, _):
        return ("Tetrahedron 4", 3, 1, 4, 0, "")


class _RuntimeGmsh:
    __version__ = "4.12-test"

    def __init__(self, *, fail_open: bool = False):
        self.model = SimpleNamespace(
            mesh=_RuntimeMesh(),
            getPhysicalGroups=lambda: [(3, 1), (0, 2)],
            getPhysicalName=lambda dim, tag: "" if dim == 0 else f"domain_{tag}",
            getEntitiesForPhysicalGroup=lambda dim, tag: [10 if dim == 3 else 20],
        )
        self.option = SimpleNamespace(setNumber=lambda *args: None)
        self.fail_open = fail_open
        self.initialized = False
        self.cleared = 0
        self.finalized = 0

    def isInitialized(self):
        return self.initialized

    def initialize(self, args):
        self.initialized = True

    def open(self, path):
        if self.fail_open:
            raise RuntimeError("synthetic open failure")

    def clear(self):
        self.cleared += 1

    def finalize(self):
        self.finalized += 1


def test_native_reader_runs_full_fake_runtime_and_collects_groups(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "mesh.msh"
    path.write_bytes(b"$MeshFormat\n4.1 0 8\n$EndMeshFormat\n")
    runtime = _RuntimeGmsh()
    monkeypatch.setattr("solveur.mesh.gmsh_reader._gmsh_module", lambda: runtime)
    data = GmshNativeReader().read(path)
    assert data.format_version == "4.1"
    assert data.gmsh_version == "4.12-test"
    assert (3, "domain_1") in data.groups
    assert (0, "physical_0_2") in data.groups
    assert runtime.cleared == 1
    assert runtime.finalized == 1


def test_native_reader_wraps_runtime_errors_and_keeps_external_session(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "mesh.msh"
    path.write_bytes(b"$MeshFormat\n4.1 0 8\n$EndMeshFormat\n")
    runtime = _RuntimeGmsh(fail_open=True)
    runtime.initialized = True
    monkeypatch.setattr("solveur.mesh.gmsh_reader._gmsh_module", lambda: runtime)
    with pytest.raises(InputValidationError, match="Unable to read Gmsh"):
        GmshNativeReader().read(path)
    assert runtime.finalized == 0


@pytest.mark.parametrize("factory, message", [
    (lambda: SimpleNamespace(model=SimpleNamespace(mesh=SimpleNamespace(getNodes=lambda: ([], [], [])))), "no valid nodes"),
    (lambda: SimpleNamespace(model=SimpleNamespace(mesh=SimpleNamespace(getElements=lambda: ([], [], [])))), "no elements"),
])
def test_native_reader_rejects_empty_runtime_blocks(factory, message: str) -> None:
    fake = factory()
    if "nodes" in message:
        with pytest.raises(MeshValidationError, match=message):
            GmshNativeReader._nodes(fake)
    else:
        with pytest.raises(MeshValidationError, match=message):
            GmshNativeReader._cells(fake)


def test_native_reader_rejects_missing_physical_groups() -> None:
    gmsh = SimpleNamespace(model=SimpleNamespace(getPhysicalGroups=lambda: []))
    with pytest.raises(MeshValidationError, match="physical groups"):
        GmshNativeReader._groups(gmsh, {})


def test_native_reader_rejects_duplicate_nodes_and_inconsistent_connectivity() -> None:
    duplicate_nodes = SimpleNamespace(model=SimpleNamespace(mesh=SimpleNamespace(
        getNodes=lambda: ([1, 1], [0.0, 0.0, 0.0, 1.0, 0.0, 0.0], []))))
    with pytest.raises(MeshValidationError, match="duplicate node"):
        GmshNativeReader._nodes(duplicate_nodes)
    bad_cells = SimpleNamespace(model=SimpleNamespace(mesh=SimpleNamespace(
        getElements=lambda: ([4], [np.asarray([1, 2])], [np.asarray([1, 2, 3, 4])]),
        getElementProperties=lambda _: ("Tetrahedron 4", 3, 1, 4, 0, ""),
    )))
    with pytest.raises(MeshValidationError, match="connectivity block"):
        GmshNativeReader._cells(bad_cells)


def test_native_reader_rejects_duplicate_physical_group_names(monkeypatch: pytest.MonkeyPatch) -> None:
    gmsh = SimpleNamespace(
        model=SimpleNamespace(
            getPhysicalGroups=lambda: [(2, 1), (2, 2)],
            getPhysicalName=lambda dim, tag: "same",
            getEntitiesForPhysicalGroup=lambda dim, tag: [],
        )
    )
    with pytest.raises(MeshValidationError, match="Duplicate physical group"):
        GmshNativeReader._groups(gmsh, {})


def test_native_reader_reports_missing_gmsh_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = __import__

    def blocked(name, *args, **kwargs):
        if name == "gmsh":
            raise ImportError("gmsh absent")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", blocked)
    with pytest.raises(InfrastructureError, match="Gmsh support is unavailable"):
        _gmsh_module()
