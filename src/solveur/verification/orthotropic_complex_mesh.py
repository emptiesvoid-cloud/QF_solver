"""Deterministic complex TET4 meshes for orthotropic cross-code V&V."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from solveur.core.errors import InfrastructureError, MeshValidationError
from solveur.core.model import FiniteElementModel


@dataclass(frozen=True)
class OrthotropicComplexCase:
    """One same-mesh structural case shared by QF_solver and external solvers."""

    identifier: str
    nodes: np.ndarray
    elements: np.ndarray
    fixed_nodes: np.ndarray
    loaded_nodes: np.ndarray
    load_component: int
    total_load: float
    angle_deg: float
    mesh_path: Path

    def qf_model(self) -> FiniteElementModel:
        component = ("UX", "UY", "UZ")[self.load_component]
        orientation = _z_orientation(self.angle_deg)
        material = {
            "type": "orthotropic_3d",
            "E1": 135.0e9,
            "E2": 10.0e9,
            "E3": 8.0e9,
            "nu12": 0.28,
            "nu13": 0.22,
            "nu23": 0.35,
            "G12": 5.2e9,
            "G13": 4.1e9,
            "G23": 3.3e9,
            "density": 1580.0,
            "orientation": orientation.tolist(),
        }
        nodal_load = self.total_load / self.loaded_nodes.size
        return FiniteElementModel.from_raw(
            nodes=self.nodes.tolist(),
            elements=[{"type": "TET4", "nodes": row.tolist(), "material": "ORTHO"} for row in self.elements],
            materials={"ORTHO": material},
            fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in self.fixed_nodes],
            loads=[{"node": int(node), "dof": component, "value": nodal_load} for node in self.loaded_nodes],
            analysis={"type": "linear_static", "method": "direct"},
            verification_profile="engineering",
        )


class OrthotropicComplexMeshFactory:
    """Build perforated and re-entrant solid geometries with physical surfaces."""

    def perforated_coupon(self, path: str | Path, mesh_size: float = 0.30) -> OrthotropicComplexCase:
        gmsh = _gmsh()
        target = _target(path)
        gmsh.initialize(["qf_orthotropic_coupon", "-nopopup"])
        try:
            _configure(gmsh, mesh_size)
            gmsh.model.add("orthotropic_perforated_coupon")
            body = gmsh.model.occ.addBox(0.0, -1.0, -0.20, 4.0, 2.0, 0.40)
            hole = gmsh.model.occ.addCylinder(2.0, 0.0, -0.30, 0.0, 0.0, 0.60, 0.35)
            cut, _ = gmsh.model.occ.cut([(3, body)], [(3, hole)])
            gmsh.model.occ.synchronize()
            volume = _single_volume(cut, "perforated coupon")
            fixed_surface = _planar_surface(gmsh, volume, axis=0, value=0.0)
            loaded_surface = _planar_surface(gmsh, volume, axis=0, value=4.0)
            _physical(gmsh, 3, [volume], "domain")
            _physical(gmsh, 2, [fixed_surface], "fixed")
            _physical(gmsh, 2, [loaded_surface], "loaded")
            gmsh.model.mesh.generate(3)
            gmsh.write(str(target))
            nodes, elements = _extract_tet4(gmsh)
            fixed = _surface_nodes(gmsh, fixed_surface)
            loaded = _surface_nodes(gmsh, loaded_surface)
            return OrthotropicComplexCase(
                "VNV-ORTHO-PERFORATED-001",
                nodes,
                elements,
                fixed,
                loaded,
                0,
                10_000.0,
                30.0,
                target,
            )
        finally:
            gmsh.finalize()

    def l_bracket(self, path: str | Path, mesh_size: float = 0.28) -> OrthotropicComplexCase:
        gmsh = _gmsh()
        target = _target(path)
        gmsh.initialize(["qf_orthotropic_l_bracket", "-nopopup"])
        try:
            _configure(gmsh, mesh_size)
            gmsh.model.add("orthotropic_l_bracket")
            horizontal = gmsh.model.occ.addBox(0.0, 0.0, -0.20, 3.2, 0.75, 0.40)
            vertical = gmsh.model.occ.addBox(0.0, 0.0, -0.20, 0.75, 2.6, 0.40)
            fused, _ = gmsh.model.occ.fuse([(3, horizontal)], [(3, vertical)])
            gmsh.model.occ.synchronize()
            volume = _single_volume(fused, "L bracket")
            fixed_surface = _planar_surface(gmsh, volume, axis=1, value=2.6)
            loaded_surface = _planar_surface(gmsh, volume, axis=0, value=3.2)
            _physical(gmsh, 3, [volume], "domain")
            _physical(gmsh, 2, [fixed_surface], "fixed")
            _physical(gmsh, 2, [loaded_surface], "loaded")
            gmsh.model.mesh.generate(3)
            gmsh.write(str(target))
            nodes, elements = _extract_tet4(gmsh)
            fixed = _surface_nodes(gmsh, fixed_surface)
            loaded = _surface_nodes(gmsh, loaded_surface)
            return OrthotropicComplexCase(
                "VNV-ORTHO-LBRACKET-002",
                nodes,
                elements,
                fixed,
                loaded,
                1,
                -5_000.0,
                25.0,
                target,
            )
        finally:
            gmsh.finalize()

    def edge_notched_coupon(self, path: str | Path, mesh_size: float = 0.20) -> OrthotropicComplexCase:
        """Build a coupon with a finite-radius semicircular edge notch."""
        return self._coupon_with_holes(
            path,
            mesh_size,
            model_name="orthotropic_edge_notched_coupon",
            identifier="VNV-ORTHO-EDGE-NOTCH-003",
            holes=((2.0, 1.0, 0.35),),
            angle_deg=35.0,
        )

    def double_hole_coupon(self, path: str | Path, mesh_size: float = 0.20) -> OrthotropicComplexCase:
        """Build a coupon with two finite holes and a loaded ligament."""
        return self._coupon_with_holes(
            path,
            mesh_size,
            model_name="orthotropic_double_hole_coupon",
            identifier="VNV-ORTHO-DOUBLE-HOLE-004",
            holes=((1.45, 0.0, 0.28), (2.55, 0.0, 0.28)),
            angle_deg=40.0,
        )

    @staticmethod
    def _coupon_with_holes(
        path: str | Path,
        mesh_size: float,
        *,
        model_name: str,
        identifier: str,
        holes: tuple[tuple[float, float, float], ...],
        angle_deg: float,
    ) -> OrthotropicComplexCase:
        gmsh = _gmsh()
        target = _target(path)
        gmsh.initialize([f"qf_{model_name}", "-nopopup"])
        try:
            _configure(gmsh, mesh_size)
            gmsh.model.add(model_name)
            body = gmsh.model.occ.addBox(0.0, -1.0, -0.20, 4.0, 2.0, 0.40)
            tools = [
                (
                    3,
                    gmsh.model.occ.addCylinder(
                        center_x,
                        center_y,
                        -0.30,
                        0.0,
                        0.0,
                        0.60,
                        radius,
                    ),
                )
                for center_x, center_y, radius in holes
            ]
            cut, _ = gmsh.model.occ.cut([(3, body)], tools)
            gmsh.model.occ.synchronize()
            volume = _single_volume(cut, model_name)
            fixed_surface = _planar_surface(gmsh, volume, axis=0, value=0.0)
            loaded_surface = _planar_surface(gmsh, volume, axis=0, value=4.0)
            _physical(gmsh, 3, [volume], "domain")
            _physical(gmsh, 2, [fixed_surface], "fixed")
            _physical(gmsh, 2, [loaded_surface], "loaded")
            gmsh.model.mesh.generate(3)
            gmsh.write(str(target))
            nodes, elements = _extract_tet4(gmsh)
            return OrthotropicComplexCase(
                identifier,
                nodes,
                elements,
                _surface_nodes(gmsh, fixed_surface),
                _surface_nodes(gmsh, loaded_surface),
                0,
                10_000.0,
                angle_deg,
                target,
            )
        finally:
            gmsh.finalize()


def _extract_tet4(gmsh: Any) -> tuple[np.ndarray, np.ndarray]:
    tags, coordinates, _ = gmsh.model.mesh.getNodes()
    order = np.argsort(tags)
    sorted_tags = np.asarray(tags, dtype=np.int64)[order]
    nodes = np.asarray(coordinates, dtype=float).reshape(-1, 3)[order]
    tag_to_index = {int(tag): index for index, tag in enumerate(sorted_tags)}
    types, _, connectivities = gmsh.model.mesh.getElements(3)
    rows: list[list[int]] = []
    for element_type, connectivity in zip(types, connectivities, strict=True):
        if int(element_type) != 4:
            raise MeshValidationError(f"Expected only first-order tetrahedra, got Gmsh type {element_type}.")
        raw = np.asarray(connectivity, dtype=np.int64).reshape(-1, 4)
        rows.extend([[tag_to_index[int(tag)] for tag in row] for row in raw])
    elements = np.asarray(rows, dtype=np.int64)
    for row in elements:
        jacobian = (nodes[row[1:]] - nodes[row[0]]).T
        if np.linalg.det(jacobian) < 0.0:
            row[1], row[2] = row[2], row[1]
    if elements.size == 0:
        raise MeshValidationError("Gmsh produced no TET4 element.")
    return nodes, elements


def _surface_nodes(gmsh: Any, surface: int) -> np.ndarray:
    tags, _, _ = gmsh.model.mesh.getNodes(2, surface, includeBoundary=True)
    all_tags, _, _ = gmsh.model.mesh.getNodes()
    mapping = {int(tag): index for index, tag in enumerate(sorted(int(tag) for tag in all_tags))}
    return np.asarray(sorted({mapping[int(tag)] for tag in tags}), dtype=np.int64)


def _planar_surface(gmsh: Any, volume: int, *, axis: int, value: float) -> int:
    tolerance = 1.0e-6 * max(abs(value), 1.0)
    matches = []
    for dimension, tag in gmsh.model.getBoundary([(3, volume)], oriented=False):
        if dimension != 2:
            continue
        box = gmsh.model.getBoundingBox(2, tag)
        minimum, maximum = box[axis], box[axis + 3]
        if abs(minimum - value) <= tolerance and abs(maximum - value) <= tolerance:
            matches.append(tag)
    if len(matches) != 1:
        raise MeshValidationError(f"Expected one surface at axis {axis}={value}, found {len(matches)}.")
    return int(matches[0])


def _single_volume(entities: list[tuple[int, int]], name: str) -> int:
    volumes = [tag for dimension, tag in entities if dimension == 3]
    if len(volumes) != 1:
        raise MeshValidationError(f"The {name} construction produced {len(volumes)} volumes.")
    return int(volumes[0])


def _z_orientation(angle_deg: float) -> np.ndarray:
    angle = np.deg2rad(angle_deg)
    cosine, sine = float(np.cos(angle)), float(np.sin(angle))
    return np.array([[cosine, -sine, 0.0], [sine, cosine, 0.0], [0.0, 0.0, 1.0]])


def _gmsh() -> Any:
    try:
        import gmsh
    except (ImportError, OSError) as exc:
        raise InfrastructureError("Orthotropic complex V&V requires the optional [mesh] dependency.") from exc
    return gmsh


def _configure(gmsh: Any, mesh_size: float) -> None:
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("General.NumThreads", 1)
    gmsh.option.setNumber("Mesh.MaxNumThreads3D", 1)
    gmsh.option.setNumber("Mesh.MeshSizeMin", mesh_size)
    gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size)
    gmsh.option.setNumber("Mesh.MshFileVersion", 4.1)
    gmsh.option.setNumber("Mesh.Binary", 0)


def _physical(gmsh: Any, dimension: int, entities: list[int], name: str) -> None:
    tag = gmsh.model.addPhysicalGroup(dimension, entities)
    gmsh.model.setPhysicalName(dimension, tag, name)


def _target(path: str | Path) -> Path:
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    return target
