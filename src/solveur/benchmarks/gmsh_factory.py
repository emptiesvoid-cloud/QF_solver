"""Deterministic Gmsh mesh generators used by controlled benchmarks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from solveur.core.errors import InfrastructureError, MeshValidationError


class BenchmarkMeshFactory:
    """Generate small reviewable MSH 4.1 meshes with named physical groups."""

    def box_tetra(
        self,
        path: str | Path,
        *,
        length: float,
        width: float,
        height: float,
        mesh_size: float,
        order: int = 1,
        anchors: bool = False,
        binary: bool = False,
    ) -> Path:
        gmsh = _gmsh()
        target = _target(path)
        gmsh.initialize(["qf_solver_benchmark", "-nopopup"])
        try:
            _options(gmsh)
            gmsh.model.add("qf_solver_box")
            volume = gmsh.model.occ.addBox(0.0, 0.0, 0.0, length, width, height)
            gmsh.model.occ.synchronize()
            surfaces = [tag for dim, tag in gmsh.model.getBoundary([(3, volume)], oriented=False) if dim == 2]
            x_min = min(surfaces, key=lambda tag: gmsh.model.occ.getCenterOfMass(2, tag)[0])
            x_max = max(surfaces, key=lambda tag: gmsh.model.occ.getCenterOfMass(2, tag)[0])
            y_min = min(surfaces, key=lambda tag: gmsh.model.occ.getCenterOfMass(2, tag)[1])
            z_min = min(surfaces, key=lambda tag: gmsh.model.occ.getCenterOfMass(2, tag)[2])
            _physical(gmsh, 3, [volume], "domain")
            _physical(gmsh, 2, [x_min], "x_min")
            _physical(gmsh, 2, [x_max], "x_max")
            _physical(gmsh, 2, [y_min], "y_min")
            _physical(gmsh, 2, [z_min], "z_min")
            if anchors:
                points = [tag for _, tag in gmsh.model.getEntities(0)]
                _physical(gmsh, 0, [_nearest_point(gmsh, points, (0.0, 0.0, 0.0))], "anchor_origin")
                _physical(gmsh, 0, [_nearest_point(gmsh, points, (length, 0.0, 0.0))], "anchor_x")
                _physical(gmsh, 0, [_nearest_point(gmsh, points, (0.0, width, 0.0))], "anchor_xy")
            gmsh.option.setNumber("Mesh.MeshSizeMin", mesh_size)
            gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size)
            gmsh.model.mesh.generate(3)
            if order == 2:
                gmsh.model.mesh.setOrder(2)
                gmsh.model.mesh.optimize("HighOrder")
            elif order != 1:
                raise ValueError("Benchmark tetrahedral order must be 1 or 2.")
            _write(gmsh, target, binary=binary)
            return target
        finally:
            gmsh.finalize()

    def quarter_cylinder_tet10(
        self,
        path: str | Path,
        *,
        inner_radius: float,
        outer_radius: float,
        height: float,
        mesh_size: float,
        binary: bool = False,
    ) -> Path:
        gmsh = _gmsh()
        target = _target(path)
        gmsh.initialize(["qf_solver_benchmark", "-nopopup"])
        try:
            _options(gmsh)
            gmsh.model.add("qf_solver_lame")
            outer = gmsh.model.occ.addCylinder(0.0, 0.0, 0.0, 0.0, 0.0, height, outer_radius)
            inner = gmsh.model.occ.addCylinder(0.0, 0.0, 0.0, 0.0, 0.0, height, inner_radius)
            annulus, _ = gmsh.model.occ.cut([(3, outer)], [(3, inner)])
            box = gmsh.model.occ.addBox(0.0, 0.0, 0.0, outer_radius, outer_radius, height)
            quarter, _ = gmsh.model.occ.intersect(annulus, [(3, box)])
            gmsh.model.occ.synchronize()
            volumes = [tag for dim, tag in quarter if dim == 3]
            if len(volumes) != 1:
                raise MeshValidationError(f"Quarter-cylinder construction produced {len(volumes)} volumes.")
            volume = volumes[0]
            surfaces = [tag for dim, tag in gmsh.model.getBoundary([(3, volume)], oriented=False) if dim == 2]
            # OCC bounding boxes include a geometry tolerance around exact planes.
            tolerance = 1.0e-6 * max(outer_radius, height, 1.0)
            x_symmetry: list[int] = []
            y_symmetry: list[int] = []
            axial: list[int] = []
            curved: list[int] = []
            for tag in surfaces:
                xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.getBoundingBox(2, tag)
                if abs(xmin) <= tolerance and abs(xmax) <= tolerance:
                    x_symmetry.append(tag)
                elif abs(ymin) <= tolerance and abs(ymax) <= tolerance:
                    y_symmetry.append(tag)
                elif abs(zmax - zmin) <= tolerance:
                    axial.append(tag)
                else:
                    curved.append(tag)
            if len(curved) != 2 or not x_symmetry or not y_symmetry or len(axial) != 2:
                raise MeshValidationError("Unable to classify quarter-cylinder physical surfaces.")
            inner_surface = min(curved, key=lambda tag: gmsh.model.occ.getMass(2, tag))
            _physical(gmsh, 3, [volume], "domain")
            _physical(gmsh, 2, [inner_surface], "inner_pressure")
            _physical(gmsh, 2, x_symmetry, "symmetry_x")
            _physical(gmsh, 2, y_symmetry, "symmetry_y")
            _physical(gmsh, 2, axial, "plane_strain_z")
            gmsh.option.setNumber("Mesh.MeshSizeMin", mesh_size)
            gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size)
            gmsh.model.mesh.generate(3)
            gmsh.model.mesh.setOrder(2)
            gmsh.model.mesh.optimize("HighOrder")
            _write(gmsh, target, binary=binary)
            return target
        finally:
            gmsh.finalize()

    def cylinder_tetra(
        self,
        path: str | Path,
        *,
        length: float,
        radius: float,
        mesh_size: float,
        order: int = 1,
        binary: bool = False,
    ) -> Path:
        """Generate a first- or second-order tetrahedral circular shaft along X."""
        gmsh = _gmsh()
        target = _target(path)
        gmsh.initialize(["qf_solver_benchmark", "-nopopup"])
        try:
            _options(gmsh)
            gmsh.model.add("qf_solver_circular_shaft")
            volume = gmsh.model.occ.addCylinder(0.0, 0.0, 0.0, length, 0.0, 0.0, radius)
            gmsh.model.occ.synchronize()
            surfaces = [tag for dim, tag in gmsh.model.getBoundary([(3, volume)], oriented=False) if dim == 2]
            tolerance = 1.0e-7 * max(length, radius, 1.0)
            end_surfaces: dict[str, list[int]] = {"x_min": [], "x_max": []}
            for tag in surfaces:
                xmin, _, _, xmax, _, _ = gmsh.model.getBoundingBox(2, tag)
                if abs(xmin) <= tolerance and abs(xmax) <= tolerance:
                    end_surfaces["x_min"].append(tag)
                elif abs(xmin - length) <= tolerance and abs(xmax - length) <= tolerance:
                    end_surfaces["x_max"].append(tag)
            if len(end_surfaces["x_min"]) != 1 or len(end_surfaces["x_max"]) != 1:
                raise MeshValidationError("Unable to identify circular-shaft end surfaces.")
            _physical(gmsh, 3, [volume], "domain")
            _physical(gmsh, 2, end_surfaces["x_min"], "x_min")
            _physical(gmsh, 2, end_surfaces["x_max"], "x_max")
            gmsh.option.setNumber("Mesh.MeshSizeMin", mesh_size)
            gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size)
            gmsh.model.mesh.generate(3)
            if order == 2:
                gmsh.model.mesh.setOrder(2)
                gmsh.model.mesh.optimize("HighOrder")
            elif order != 1:
                raise ValueError("Benchmark tetrahedral order must be 1 or 2.")
            _write(gmsh, target, binary=binary)
            return target
        finally:
            gmsh.finalize()

    def discrete_mitc4(
        self,
        path: str | Path,
        *,
        nodes: np.ndarray,
        quads: np.ndarray,
        line_groups: dict[str, list[tuple[int, int]]] | None = None,
        point_groups: dict[str, list[int]] | None = None,
        binary: bool = False,
    ) -> Path:
        gmsh = _gmsh()
        target = _target(path)
        coordinates = np.asarray(nodes, dtype=float)
        connectivity = np.asarray(quads, dtype=np.int64)
        if coordinates.ndim != 2 or coordinates.shape[1] != 3:
            raise ValueError("MITC4 benchmark nodes must have shape (n, 3).")
        if connectivity.ndim != 2 or connectivity.shape[1] != 4:
            raise ValueError("MITC4 benchmark quads must have shape (m, 4).")
        gmsh.initialize(["qf_solver_benchmark", "-nopopup"])
        try:
            _options(gmsh)
            gmsh.model.add("qf_solver_shell")
            surface_entity = gmsh.model.addDiscreteEntity(2, 1)
            node_tags = np.arange(1, coordinates.shape[0] + 1, dtype=np.int64)
            gmsh.model.mesh.addNodes(2, surface_entity, node_tags.tolist(), coordinates.reshape(-1).tolist())
            element_tags = np.arange(1, connectivity.shape[0] + 1, dtype=np.int64)
            gmsh.model.mesh.addElementsByType(
                surface_entity,
                3,
                element_tags.tolist(),
                (connectivity + 1).reshape(-1).tolist(),
            )
            _physical(gmsh, 2, [surface_entity], "shell")
            next_entity = 100
            next_element = int(element_tags[-1]) + 1 if element_tags.size else 1
            for name, edges in sorted((line_groups or {}).items()):
                entity = gmsh.model.addDiscreteEntity(1, next_entity)
                tags = list(range(next_element, next_element + len(edges)))
                gmsh.model.mesh.addElementsByType(
                    entity,
                    1,
                    tags,
                    [node + 1 for edge in edges for node in edge],
                )
                _physical(gmsh, 1, [entity], name)
                next_entity += 1
                next_element += len(edges)
            for name, points in sorted((point_groups or {}).items()):
                entity = gmsh.model.addDiscreteEntity(0, next_entity)
                tags = list(range(next_element, next_element + len(points)))
                gmsh.model.mesh.addElementsByType(entity, 15, tags, [node + 1 for node in points])
                _physical(gmsh, 0, [entity], name)
                next_entity += 1
                next_element += len(points)
            _write(gmsh, target, binary=binary)
            return target
        finally:
            gmsh.finalize()

    def discrete_wedge6_prism(
        self,
        path: str | Path,
        *,
        length: float,
        width: float,
        height: float,
        binary: bool = False,
    ) -> Path:
        """Generate one native Gmsh Prism 6 with all named boundary faces.

        The mesh is deliberately discrete: its node and face order is explicit,
        which makes it suitable for importer and load-mapping evidence.
        """
        gmsh = _gmsh()
        target = _target(path)
        if min(length, width, height) <= 0.0:
            raise ValueError("WEDGE6 benchmark dimensions must be positive.")
        coordinates = np.asarray(
            (
                (0.0, 0.0, 0.0),
                (length, 0.0, 0.0),
                (0.0, width, 0.0),
                (0.0, 0.0, height),
                (length, 0.0, height),
                (0.0, width, height),
            ),
            dtype=float,
        )
        faces = (
            ("tri_bottom", 2, (0, 2, 1)),
            ("tri_top", 2, (3, 4, 5)),
            ("quad_side_12", 3, (0, 1, 4, 3)),
            ("quad_side_23", 3, (1, 2, 5, 4)),
            ("quad_side_31", 3, (2, 0, 3, 5)),
        )
        gmsh.initialize(["qf_solver_benchmark", "-nopopup"])
        try:
            _options(gmsh)
            gmsh.model.add("qf_solver_wedge6")
            volume_entity = gmsh.model.addDiscreteEntity(3, 1)
            node_tags = np.arange(1, 7, dtype=np.int64)
            gmsh.model.mesh.addNodes(3, volume_entity, node_tags.tolist(), coordinates.reshape(-1).tolist())
            gmsh.model.mesh.addElementsByType(volume_entity, 6, [1], node_tags.tolist())
            _physical(gmsh, 3, [volume_entity], "domain")
            for offset, (name, element_type, connectivity) in enumerate(faces, start=10):
                entity = gmsh.model.addDiscreteEntity(2, offset)
                gmsh.model.mesh.addElementsByType(entity, element_type, [100 + offset], [node + 1 for node in connectivity])
                _physical(gmsh, 2, [entity], name)
            point_entity = gmsh.model.addDiscreteEntity(0, 20)
            gmsh.model.mesh.addElementsByType(point_entity, 15, [200], [5])
            _physical(gmsh, 0, [point_entity], "loaded_node")
            _write(gmsh, target, binary=binary)
            return target
        finally:
            gmsh.finalize()


def _gmsh() -> Any:
    try:
        import gmsh
    except (ImportError, OSError) as exc:
        raise InfrastructureError("Meshed benchmarks require the optional QF_solver [mesh] dependencies.") from exc
    return gmsh


def _target(path: str | Path) -> Path:
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _options(gmsh: Any) -> None:
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("General.NumThreads", 1)
    gmsh.option.setNumber("Mesh.MaxNumThreads1D", 1)
    gmsh.option.setNumber("Mesh.MaxNumThreads2D", 1)
    gmsh.option.setNumber("Mesh.MaxNumThreads3D", 1)
    gmsh.option.setNumber("Mesh.MshFileVersion", 4.1)
    gmsh.option.setNumber("Mesh.Binary", 0)


def _physical(gmsh: Any, dimension: int, entities: list[int], name: str) -> int:
    tag = int(gmsh.model.addPhysicalGroup(dimension, entities))
    gmsh.model.setPhysicalName(dimension, tag, name)
    return tag


def _write(gmsh: Any, path: Path, *, binary: bool = False) -> None:
    gmsh.option.setNumber("Mesh.Binary", 1 if binary else 0)
    gmsh.write(str(path))
    if not path.is_file() or path.stat().st_size == 0:
        raise MeshValidationError(f"Gmsh did not write benchmark mesh {path}.")


def _nearest_point(gmsh: Any, points: list[int], target: tuple[float, float, float]) -> int:
    target_vector = np.asarray(target, dtype=float)
    return min(
        points,
        # ``occ.getCenterOfMass`` is not reliable for zero-dimensional OCC
        # entities after synchronization on all supported Gmsh platforms.
        # ``model.getValue`` returns the actual geometric point coordinates.
        key=lambda tag: float(np.linalg.norm(np.asarray(gmsh.model.getValue(0, tag, [])) - target_vector)),
    )
