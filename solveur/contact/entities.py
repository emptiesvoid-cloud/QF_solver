"""Input entities for bounded node-to-triangle contact."""

from __future__ import annotations

from dataclasses import dataclass

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

    def geometry(self, nodes: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
        """Return frozen normal, barycentric weights and gap of the selected face."""
        selected = self.face_geometry(nodes)
        return selected.normal, selected.barycentric, selected.gap

    @property
    def faces(self) -> tuple[tuple[int, int, int], ...]:
        """Return one legacy face or the explicitly supplied master surface."""
        return self.master_faces if self.master_faces is not None else (self.master_nodes,)

    @property
    def referenced_master_nodes(self) -> tuple[int, ...]:
        """Return every master node needed in the global displacement map."""
        return tuple(sorted({node for face in self.faces for node in face}))

    def face_geometry(self, nodes: np.ndarray) -> ContactFaceGeometry:
        """Select the nearest compatible triangle on the supplied geometry.

        The caller supplies either the initial coordinates or one bounded
        updated configuration. This entity does not itself implement large
        sliding, topology changes, or a general surface-to-surface search.
        """
        _check_node(self.slave_node, nodes, "contact slave")
        slave = np.asarray(nodes[self.slave_node], dtype=float)
        compatible: list[ContactFaceGeometry] = []
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
            barycentric = _barycentric(slave - gap * normal, master)
            if np.min(barycentric) >= -1.0e-8 and np.max(barycentric) <= 1.0 + 1.0e-8:
                compatible.append(ContactFaceGeometry(face, normal, barycentric, gap, face_index))
        if not compatible:
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


def _check_node(node: int, nodes: np.ndarray, label: str) -> None:
    if not isinstance(node, int) or not 0 <= node < len(nodes):
        raise InputValidationError(f"{label} must reference an existing node.")
