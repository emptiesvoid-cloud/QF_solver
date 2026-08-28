"""Input entities for bounded node-to-triangle contact."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from solveur.core.errors import InputValidationError


@dataclass(frozen=True)
class ContactFaceGeometry:
    """Frozen geometry of the selected face in a bounded master surface."""

    master_nodes: tuple[int, int, int]
    normal: np.ndarray
    barycentric: np.ndarray
    gap: float
    face_index: int
    projection_clamped: bool = False
    closest_distance: float = 0.0
    projection_mode: str = "exact_node_to_triangle"


@dataclass(frozen=True)
class FrictionlessContact:
    """One slave node and one compatible, ordered triangular master face.

    ``friction_coefficient=0`` selects the frictionless formulation.  A
    positive coefficient requires ``tangential_stiffness`` and activates the
    regularized Coulomb extension in the static contact solver.
    """

    slave_node: int
    master_nodes: tuple[int, int, int]
    name: str = ""
    gap_tolerance: float = 1.0e-10
    friction_coefficient: float = 0.0
    tangential_stiffness: float | None = None
    master_faces: tuple[tuple[int, int, int], ...] | None = None
    slave_patch_nodes: tuple[int, ...] | None = None

    @property
    def slave_nodes(self) -> tuple[int, ...]:
        """Return the slave nodes represented by this contact surface patch.

        ``slave_patch_nodes`` is optional so the historical single-node input
        remains unchanged.  Each patch node is assembled as one node-to-
        faceted-surface contribution; this is a bounded surface discretization,
        not a mortar or segment-to-segment formulation.
        """
        if self.slave_patch_nodes is None:
            return (self.slave_node,)
        return tuple(self.slave_patch_nodes)

    def expanded_slave_contacts(self) -> tuple["FrictionlessContact", ...]:
        """Expand a slave patch into stateless point-to-surface contacts."""
        nodes = self.slave_nodes
        if not nodes:
            raise InputValidationError("A contact slave surface must contain at least one node.")
        if len(set(nodes)) != len(nodes):
            raise InputValidationError("A contact slave surface must not repeat slave nodes.")
        if self.slave_patch_nodes is None:
            return (self,)
        return tuple(replace(self, slave_node=node, slave_patch_nodes=None) for node in nodes)

    def geometry(
        self, nodes: np.ndarray, *, allow_clamped_projection: bool = False
    ) -> tuple[np.ndarray, np.ndarray, float]:
        """Return frozen normal, barycentric weights and gap of the selected face."""
        selected = self.face_geometry(nodes, allow_clamped_projection=allow_clamped_projection)
        return selected.normal, selected.barycentric, selected.gap

    @property
    def faces(self) -> tuple[tuple[int, int, int], ...]:
        """Return one legacy face or the explicitly supplied master surface."""
        return self.master_faces if self.master_faces is not None else (self.master_nodes,)

    @property
    def referenced_master_nodes(self) -> tuple[int, ...]:
        """Return every master node needed in the global displacement map."""
        return tuple(sorted({node for face in self.faces for node in face}))

    def face_geometry(
        self, nodes: np.ndarray, *, allow_clamped_projection: bool = False
    ) -> ContactFaceGeometry:
        """Select the nearest compatible triangle on the supplied geometry.

        The caller supplies either the initial coordinates or one bounded
        updated configuration. When ``allow_clamped_projection`` is enabled,
        a finite-sliding penalty path may retain the closest point on a face
        while the slave crosses an edge. This remains a node-to-triangle
        surface approximation; it is not a general surface-to-surface search.
        """
        _check_node(self.slave_node, nodes, "contact slave")
        slave = np.asarray(nodes[self.slave_node], dtype=float)
        compatible: list[ContactFaceGeometry] = []
        clamped: list[ContactFaceGeometry] = []
        for face_index, face in enumerate(self.faces):
            if len(set(face)) != 3 or self.slave_node in face:
                raise InputValidationError("Contact master nodes must be unique and differ from the slave node.")
            for node in face:
                _check_node(node, nodes, "contact master")
            master = np.asarray(nodes[list(face)], dtype=float)
            normal_raw = np.cross(master[1] - master[0], master[2] - master[0])
            magnitude = float(np.linalg.norm(normal_raw))
            if not np.isfinite(magnitude) or magnitude <= 1.0e-14:
                raise InputValidationError("Contact master triangle has a zero or non-finite area.")
            normal = normal_raw / magnitude
            gap = float(normal @ (slave - master[0]))
            projected = slave - gap * normal
            barycentric = _barycentric(projected, master)
            if np.min(barycentric) >= -1.0e-8 and np.max(barycentric) <= 1.0 + 1.0e-8:
                compatible.append(
                    ContactFaceGeometry(
                        face,
                        normal,
                        barycentric,
                        gap,
                        face_index,
                        closest_distance=abs(gap),
                        projection_mode="exact_node_to_triangle",
                    )
                )
            elif allow_clamped_projection:
                clamped_barycentric = _closest_point_barycentric(projected, master)
                closest_point = clamped_barycentric @ master
                clamped.append(
                    ContactFaceGeometry(
                        face,
                        normal,
                        clamped_barycentric,
                        gap,
                        face_index,
                        projection_clamped=True,
                        closest_distance=float(np.linalg.norm(slave - closest_point)),
                        projection_mode="bounded_closest_point_node_to_triangle",
                    )
                )
        if not compatible:
            if allow_clamped_projection and clamped:
                return min(
                    clamped,
                    key=lambda item: (
                        item.closest_distance,
                        abs(item.gap),
                        item.face_index,
                    ),
                )
            label = "master triangle" if len(self.faces) == 1 else "master surface"
            raise InputValidationError(f"Contact slave projection lies outside the compatible {label}.")
        return min(compatible, key=lambda item: (abs(item.gap), item.face_index))


def _barycentric(point: np.ndarray, triangle: np.ndarray) -> np.ndarray:
    origin = triangle[0]
    edge_1 = triangle[1] - origin
    edge_2 = triangle[2] - origin
    relative = point - origin
    gram = np.array([[edge_1 @ edge_1, edge_1 @ edge_2], [edge_1 @ edge_2, edge_2 @ edge_2]])
    rhs = np.array([relative @ edge_1, relative @ edge_2])
    try:
        xi_eta = np.linalg.solve(gram, rhs)
    except np.linalg.LinAlgError as exc:
        raise InputValidationError("Contact master triangle is degenerate.") from exc
    return np.array([1.0 - xi_eta[0] - xi_eta[1], xi_eta[0], xi_eta[1]])


def _closest_point_barycentric(point: np.ndarray, triangle: np.ndarray) -> np.ndarray:
    """Return barycentrics of the closest point on a non-degenerate triangle."""

    a, b, c = np.asarray(triangle, dtype=float)
    ab = b - a
    ac = c - a
    ap = np.asarray(point, dtype=float) - a
    d1 = float(ab @ ap)
    d2 = float(ac @ ap)
    if d1 <= 0.0 and d2 <= 0.0:
        return np.array([1.0, 0.0, 0.0])

    bp = np.asarray(point, dtype=float) - b
    d3 = float(ab @ bp)
    d4 = float(ac @ bp)
    if d3 >= 0.0 and d4 <= d3:
        return np.array([0.0, 1.0, 0.0])

    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        denominator = d1 - d3
        if denominator <= 1.0e-30:
            return np.array([1.0, 0.0, 0.0])
        v = d1 / denominator
        return np.array([1.0 - v, v, 0.0])

    cp = np.asarray(point, dtype=float) - c
    d5 = float(ab @ cp)
    d6 = float(ac @ cp)
    if d6 >= 0.0 and d5 <= d6:
        return np.array([0.0, 0.0, 1.0])

    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        denominator = d2 - d6
        if denominator <= 1.0e-30:
            return np.array([1.0, 0.0, 0.0])
        w = d2 / denominator
        return np.array([1.0 - w, 0.0, w])

    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        denominator = (d4 - d3) + (d5 - d6)
        if denominator <= 1.0e-30:
            return np.array([0.0, 1.0, 0.0])
        w = (d4 - d3) / denominator
        return np.array([0.0, 1.0 - w, w])

    denominator = va + vb + vc
    if denominator <= 1.0e-30:
        raise InputValidationError("Contact master triangle is degenerate.")
    v = vb / denominator
    w = vc / denominator
    return np.array([1.0 - v - w, v, w])


def _check_node(node: int, nodes: np.ndarray, label: str) -> None:
    if not isinstance(node, int) or not 0 <= node < len(nodes):
        raise InputValidationError(f"{label} must reference an existing node.")
