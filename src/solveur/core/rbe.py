"""Kinematic RBE-style links expressed as transparent linear MPC equations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from solveur.core.constraints import ConstraintTerm, LinearConstraint
from solveur.core.dofs import DOF_ORDER, TRANSLATION_DOFS
from solveur.core.errors import InputValidationError


@dataclass(frozen=True)
class Rbe2Definition:
    """Rigid master/slave kinematic link about a master-node reference point."""

    master: int
    slaves: tuple[int, ...]
    tie_rotations: bool = False
    name: str = ""


@dataclass(frozen=True)
class Rbe3Definition:
    """Weighted distribution link without an artificial stiffness."""

    reference: int
    independents: tuple[tuple[int, float], ...]
    dofs: tuple[str, ...] = DOF_ORDER
    mode: str = "rigid_body_projection"
    name: str = ""


def rbe2_constraints(nodes: np.ndarray, definition: Rbe2Definition) -> list[LinearConstraint]:
    """Return ``u_slave=u_master+theta_master x r`` equations in global axes."""
    _node(definition.master, nodes, "RBE2 master")
    if not definition.slaves:
        raise InputValidationError("RBE2 must contain at least one slave node.")
    if len(set(definition.slaves)) != len(definition.slaves):
        raise InputValidationError("RBE2 slave nodes must be unique.")
    constraints: list[LinearConstraint] = []
    for slave in definition.slaves:
        _node(slave, nodes, "RBE2 slave")
        if slave == definition.master:
            raise InputValidationError("RBE2 master cannot also be a slave.")
        offset = np.asarray(nodes[slave], dtype=float) - np.asarray(nodes[definition.master], dtype=float)
        terms = _rigid_translation_terms(definition.master, slave, offset)
        for component, row in enumerate(terms):
            constraints.append(LinearConstraint(tuple(row), name=_name(definition.name, slave, component)))
        if definition.tie_rotations:
            for name in DOF_ORDER[3:]:
                constraints.append(
                    LinearConstraint(
                        (ConstraintTerm(slave, name, 1.0), ConstraintTerm(definition.master, name, -1.0)),
                        name=f"{definition.name or 'rbe2'}:slave_{slave}:{name}",
                    )
                )
    return constraints


def rbe3_constraints(nodes: np.ndarray | None, definition: Rbe3Definition) -> list[LinearConstraint]:
    """Return either a rigid-body projector or an explicit scalar weighting."""
    if not definition.independents:
        raise InputValidationError("RBE3 must contain at least one independent node.")
    if len({node for node, _ in definition.independents}) != len(definition.independents):
        raise InputValidationError("RBE3 independent nodes must be unique.")
    weights = np.asarray([weight for _, weight in definition.independents], dtype=float)
    if not np.all(np.isfinite(weights)) or abs(float(np.sum(weights))) <= 1.0e-14:
        raise InputValidationError("RBE3 weights must be finite with a non-zero sum.")
    if not definition.dofs or any(name not in DOF_ORDER for name in definition.dofs):
        raise InputValidationError("RBE3 must use one or more valid generalized DOFs.")
    mode = definition.mode.lower()
    if mode == "weighted":
        return _weighted_constraints(definition, weights)
    if mode != "rigid_body_projection":
        raise InputValidationError("RBE3 mode must be 'rigid_body_projection' or 'weighted'.")
    if nodes is None:
        raise InputValidationError("RBE3 rigid_body_projection requires node coordinates.")
    if tuple(definition.dofs) != DOF_ORDER:
        raise InputValidationError("RBE3 rigid_body_projection requires all six reference DOFs.")
    _node(definition.reference, nodes, "RBE3 reference")
    for node, _ in definition.independents:
        _node(node, nodes, "RBE3 independent")
        if node == definition.reference:
            raise InputValidationError("RBE3 independent nodes must differ from the reference.")
    if np.any(weights <= 0.0):
        raise InputValidationError("RBE3 rigid_body_projection requires strictly positive weights.")
    return _rigid_body_projection_constraints(nodes, definition, weights)


def _weighted_constraints(definition: Rbe3Definition, weights: np.ndarray) -> list[LinearConstraint]:
    """Build legacy per-component weighted equations with normalized weights."""
    normalized = weights / np.sum(weights)
    return [
        LinearConstraint(
            (ConstraintTerm(definition.reference, name, 1.0),)
            + tuple(ConstraintTerm(node, name, -float(weight)) for (node, _), weight in zip(definition.independents, normalized)),
            name=f"{definition.name or 'rbe3'}:{name}",
        )
        for name in definition.dofs
    ]


def _rigid_body_projection_constraints(
    nodes: np.ndarray,
    definition: Rbe3Definition,
    weights: np.ndarray,
) -> list[LinearConstraint]:
    """Project independent translations onto six reference rigid-body coordinates."""
    blocks = [_rigid_motion_block(np.asarray(nodes[node]) - np.asarray(nodes[definition.reference])) for node, _ in definition.independents]
    interpolation = np.vstack(blocks)
    metric = np.repeat(weights, 3)
    normal = interpolation.T @ (metric[:, None] * interpolation)
    scale = max(float(np.linalg.norm(normal, ord=2)), 1.0)
    if np.linalg.matrix_rank(normal, tol=scale * 1.0e-12) != 6:
        raise InputValidationError(
            "RBE3 rigid_body_projection independent nodes must span six rigid-body coordinates."
        )
    projector = np.linalg.solve(normal, interpolation.T * metric)
    constraints: list[LinearConstraint] = []
    for component, name in enumerate(DOF_ORDER):
        terms = [ConstraintTerm(definition.reference, name, 1.0)]
        for index, (node, _) in enumerate(definition.independents):
            for local, dof in enumerate(TRANSLATION_DOFS):
                coefficient = -float(projector[component, 3 * index + local])
                if abs(coefficient) > 1.0e-15:
                    terms.append(ConstraintTerm(node, dof, coefficient))
        constraints.append(LinearConstraint(tuple(terms), name=f"{definition.name or 'rbe3'}:{name}"))
    return constraints


def _rigid_motion_block(offset: np.ndarray) -> np.ndarray:
    """Map reference translations/rotations to a point translation at ``offset``."""
    x, y, z = (float(value) for value in offset)
    return np.array(
        [
            [1.0, 0.0, 0.0, 0.0, z, -y],
            [0.0, 1.0, 0.0, -z, 0.0, x],
            [0.0, 0.0, 1.0, y, -x, 0.0],
        ]
    )


def _rigid_translation_terms(master: int, slave: int, offset: np.ndarray) -> tuple[tuple[ConstraintTerm, ...], ...]:
    rx, ry, rz = (float(value) for value in offset)
    return (
        _nonzero_terms((
            ConstraintTerm(slave, "UX", 1.0), ConstraintTerm(master, "UX", -1.0),
            ConstraintTerm(master, "RY", -rz), ConstraintTerm(master, "RZ", ry),
        )),
        _nonzero_terms((
            ConstraintTerm(slave, "UY", 1.0), ConstraintTerm(master, "UY", -1.0),
            ConstraintTerm(master, "RX", rz), ConstraintTerm(master, "RZ", -rx),
        )),
        _nonzero_terms((
            ConstraintTerm(slave, "UZ", 1.0), ConstraintTerm(master, "UZ", -1.0),
            ConstraintTerm(master, "RX", -ry), ConstraintTerm(master, "RY", rx),
        )),
    )


def _nonzero_terms(terms: tuple[ConstraintTerm, ...]) -> tuple[ConstraintTerm, ...]:
    return tuple(term for index, term in enumerate(terms) if index == 0 or abs(term.coefficient) > 1.0e-15)


def _node(node: int, nodes: np.ndarray, label: str) -> None:
    if not isinstance(node, int) or not 0 <= node < len(nodes):
        raise InputValidationError(f"{label} must reference an existing node.")


def _name(name: str, slave: int, component: int) -> str:
    return f"{name or 'rbe2'}:slave_{slave}:{TRANSLATION_DOFS[component]}"
