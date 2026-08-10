"""Optional native Gmsh reader for MSH 4.1 meshes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np

from solveur.core.errors import InfrastructureError, InputValidationError, MeshValidationError
from solveur.mesh.gmsh_types import GmshCell, GmshMeshData, GmshPhysicalGroup


class GmshNativeReader:
    """Extract nodes, cells and physical groups through the official Gmsh API."""

    def read(self, path: str | Path) -> GmshMeshData:
        source = Path(path).resolve()
        if not source.is_file():
            raise InputValidationError(f"Gmsh mesh does not exist: {source}")
        format_version, binary = _msh_header(source)
        if format_version != "4.1":
            raise InputValidationError(
                f"Unsupported Gmsh MSH version {format_version!r}; QF_solver requires MSH 4.1."
            )
        gmsh = _gmsh_module()
        owned_session = not bool(gmsh.isInitialized())
        try:
            if owned_session:
                gmsh.initialize(["qf_solver_gmsh_import", "-nopopup"])
            else:
                gmsh.clear()
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.open(str(source))
            nodes = self._nodes(gmsh)
            cells = self._cells(gmsh)
            groups = self._groups(gmsh, cells)
            return GmshMeshData(
                path=source,
                format_version=format_version,
                binary=binary,
                gmsh_version=str(getattr(gmsh, "__version__", "unknown")),
                nodes=nodes,
                cells=cells,
                groups=groups,
            )
        except (InputValidationError, MeshValidationError):
            raise
        except Exception as exc:
            raise InputValidationError(f"Unable to read Gmsh mesh {source}: {exc}") from exc
        finally:
            try:
                gmsh.clear()
            finally:
                if owned_session:
                    gmsh.finalize()

    @staticmethod
    def _nodes(gmsh: Any) -> dict[int, tuple[float, float, float]]:
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        tags = np.asarray(node_tags, dtype=np.int64)
        points = np.asarray(coordinates, dtype=float).reshape((-1, 3))
        if tags.size != points.shape[0] or tags.size == 0:
            raise MeshValidationError("Gmsh mesh has no valid nodes.")
        if len(set(int(tag) for tag in tags)) != tags.size:
            raise MeshValidationError("Gmsh mesh contains duplicate node tags.")
        return {
            int(tag): tuple(float(value) for value in point)
            for tag, point in sorted(zip(tags, points), key=lambda item: int(item[0]))
        }

    @staticmethod
    def _cells(gmsh: Any) -> dict[int, GmshCell]:
        element_types, element_tags, element_nodes = gmsh.model.mesh.getElements()
        cells: dict[int, GmshCell] = {}
        for gmsh_type, tags, flattened_nodes in zip(element_types, element_tags, element_nodes):
            name, dimension, order, node_count, _, _ = gmsh.model.mesh.getElementProperties(int(gmsh_type))
            native_tags = np.asarray(tags, dtype=np.int64)
            connectivity = np.asarray(flattened_nodes, dtype=np.int64).reshape((-1, int(node_count)))
            if native_tags.size != connectivity.shape[0]:
                raise MeshValidationError(f"Invalid connectivity block for Gmsh element type {gmsh_type}.")
            for tag, row in zip(native_tags, connectivity):
                identifier = int(tag)
                if identifier in cells:
                    raise MeshValidationError(f"Duplicate Gmsh element tag {identifier}.")
                cells[identifier] = GmshCell(
                    tag=identifier,
                    gmsh_type=int(gmsh_type),
                    dimension=int(dimension),
                    order=int(order),
                    name=str(name),
                    nodes=tuple(int(value) for value in row),
                )
        if not cells:
            raise MeshValidationError("Gmsh mesh has no elements.")
        return cells

    @staticmethod
    def _groups(gmsh: Any, cells: dict[int, GmshCell]) -> dict[tuple[int, str], GmshPhysicalGroup]:
        groups: dict[tuple[int, str], GmshPhysicalGroup] = {}
        for dimension, tag in gmsh.model.getPhysicalGroups():
            dim = int(dimension)
            physical_tag = int(tag)
            name = str(gmsh.model.getPhysicalName(dim, physical_tag)).strip()
            if not name:
                name = f"physical_{dim}_{physical_tag}"
            key = (dim, name)
            if key in groups:
                raise MeshValidationError(f"Duplicate physical group name {name!r} in dimension {dim}.")
            cell_tags: set[int] = set()
            for entity_tag in gmsh.model.getEntitiesForPhysicalGroup(dim, physical_tag):
                _, entity_elements, _ = gmsh.model.mesh.getElements(dim, int(entity_tag))
                for block in entity_elements:
                    cell_tags.update(int(value) for value in block)
            node_tags = {
                node
                for cell_tag in cell_tags
                for node in cells.get(cell_tag, GmshCell(0, 0, 0, 0, "", ())).nodes
            }
            groups[key] = GmshPhysicalGroup(
                name=name,
                dimension=dim,
                tag=physical_tag,
                cell_tags=tuple(sorted(cell_tags)),
                node_tags=tuple(sorted(node_tags)),
            )
        if not groups:
            raise MeshValidationError("Gmsh mesh has no physical groups.")
        return groups


def _msh_header(path: Path) -> tuple[str, bool]:
    header = path.read_bytes()[:256]
    match = re.search(rb"\$MeshFormat\s+([0-9.]+)\s+([01])\s+([0-9]+)", header)
    if match is None:
        raise InputValidationError(f"File is not a readable Gmsh MSH mesh: {path}")
    return match.group(1).decode("ascii"), match.group(2) == b"1"


def _gmsh_module() -> Any:
    try:
        import gmsh
    except (ImportError, OSError) as exc:
        raise InfrastructureError(
            "Gmsh support is unavailable; install QF_solver with 'python -m pip install -e .[mesh]'."
        ) from exc
    return gmsh
