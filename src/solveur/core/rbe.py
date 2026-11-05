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
    try:
        coordinates = np.asarray(nodes, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise InputValidationError("RBE2 requires finite 3D node coordinates.") from exc
    if coordinates.ndim != 2 or coordinates.shape[1] != 3 or not np.all(np.isfinite(coordinates)):
        raise InputValidationError("RBE2 requires finite 3D node coordinates.")
    _node(definition.master, coordinates, "RBE2 master")
    if not definition.slaves:
        raise InputValidationError("RBE2 must contain at least one slave node.")
    if len(set(definition.slaves)) != len(definition.slaves):
        raise InputValidationError("RBE2 slave nodes must be unique.")
    constraints: list[LinearConstraint] = []
    for slave in definition.slaves:
        _node(slave, coordinates, "RBE2 slave")
        if slave == definition.master:
            raise InputValidationError("RBE2 master cannot also be a slave.")
        offset = coordinates[slave] - coordinates[definition.master]
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
    raw_weights = [weight for _, weight in definition.independents]
    weights = _normalized_weights(raw_weights)
    coordinates: np.ndarray | None = None
    if nodes is not None:
        try:
            coordinates = np.asarray(nodes, dtype=np.float64)
        except (TypeError, ValueError, OverflowError) as exc:
            raise InputValidationError("RBE3 requires finite 3D node coordinates when coordinates are supplied.") from exc
        if coordinates.ndim != 2 or coordinates.shape[1] != 3 or not np.all(np.isfinite(coordinates)):
            raise InputValidationError("RBE3 requires finite 3D node coordinates when coordinates are supplied.")
        _node(definition.reference, coordinates, "RBE3 reference")
        for node, _ in definition.independents:
            _node(node, coordinates, "RBE3 independent")
            if node == definition.reference:
                raise InputValidationError("RBE3 independent nodes must differ from the reference.")
    if not definition.dofs or any(name not in DOF_ORDER for name in definition.dofs):
        raise InputValidationError("RBE3 must use one or more valid generalized DOFs.")
    mode = definition.mode.lower()
    if mode == "weighted":
        return _weighted_constraints(definition, weights)
    if mode != "rigid_body_projection":
        raise InputValidationError("RBE3 mode must be 'rigid_body_projection' or 'weighted'.")
    if any(float(weight) <= 0.0 for weight in raw_weights):
        raise InputValidationError("RBE3 rigid_body_projection requires strictly positive weights.")
    if coordinates is None:
        raise InputValidationError("RBE3 rigid_body_projection requires node coordinates.")
    if tuple(definition.dofs) != DOF_ORDER:
        raise InputValidationError("RBE3 rigid_body_projection requires all six reference DOFs.")
    return _rigid_body_projection_constraints(coordinates, definition, weights)


def _weighted_constraints(definition: Rbe3Definition, weights: np.ndarray) -> list[LinearConstraint]:
    """Build legacy per-component weighted equations with normalized weights."""
    return [
        LinearConstraint(
            (ConstraintTerm(definition.reference, name, 1.0),)
            + tuple(ConstraintTerm(node, name, -float(weight)) for (node, _), weight in zip(definition.independents, weights)),
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
    coordinates = np.asarray(nodes, dtype=np.float64)
    if coordinates.ndim != 2 or coordinates.shape[1] != 3 or not np.all(np.isfinite(coordinates)):
        raise InputValidationError("RBE3 rigid_body_projection requires finite 3D node coordinates.")
    independent_nodes = np.asarray([node for node, _ in definition.independents], dtype=int)
    independent_coordinates = coordinates[independent_nodes]
    reference_coordinate = coordinates[definition.reference]
    centroid = np.average(independent_coordinates, axis=0, weights=weights)
    centered = independent_coordinates - centroid
    length_scale = float(np.max(np.abs(centered), initial=0.0))
    if not np.isfinite(length_scale) or length_scale <= 0.0:
        raise InputValidationError(
            "RBE3 rigid_body_projection independent nodes must span six rigid-body coordinates."
        )
    if not np.isfinite(1.0 / length_scale):
        raise InputValidationError("RBE3 geometry scale is outside the representable numeric range.")

    # Centering removes translation/rotation correlation; scaling the rotation
    # columns makes the rank test independent of the model's length unit.  The
    # SVD solves the original weighted least-squares projection without forming
    # the squared-condition-number normal equations A.T W A.
    scaled_blocks = [_rigid_motion_block(offset / length_scale) for offset in centered]
    interpolation = np.vstack(scaled_blocks)
    metric = np.repeat(weights, 3)
    sqrt_metric = np.sqrt(metric)
    weighted_interpolation = sqrt_metric[:, None] * interpolation
    try:
        left, singular_values, right = np.linalg.svd(weighted_interpolation, full_matrices=False)
    except np.linalg.LinAlgError as exc:
        raise InputValidationError("RBE3 weighted projection could not be factorized numerically.") from exc
    if singular_values.size < 6 or singular_values[0] == 0.0 or singular_values[-1] <= singular_values[0] * 1.0e-12:
        raise InputValidationError(
            "RBE3 rigid_body_projection independent nodes must span six rigid-body coordinates."
        )

    weighted_pseudoinverse = (right.T / singular_values) @ left.T
    centered_projector = weighted_pseudoinverse * sqrt_metric[None, :]
    centered_projector[3:, :] /= length_scale

    # Convert the fitted translation at the weighted centroid to the requested
    # reference node: t_ref = t_centroid + theta x (x_ref - centroid).
    reference_offset = reference_coordinate - centroid
    if not np.all(np.isfinite(reference_offset)):
        raise InputValidationError("RBE3 reference offset is outside the representable numeric range.")
    shift = np.array(
        [
            [1.0, 0.0, 0.0, 0.0, reference_offset[2], -reference_offset[1]],
            [0.0, 1.0, 0.0, -reference_offset[2], 0.0, reference_offset[0]],
            [0.0, 0.0, 1.0, reference_offset[1], -reference_offset[0], 0.0],
            [0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    projector = shift @ centered_projector
    if not np.all(np.isfinite(projector)):
        raise InputValidationError("RBE3 projection is outside the representable numeric range.")
    constraints: list[LinearConstraint] = []
    for component, name in enumerate(DOF_ORDER):
        terms = [ConstraintTerm(definition.reference, name, 1.0)]
        for index, (node, _) in enumerate(definition.independents):
            for local, dof in enumerate(TRANSLATION_DOFS):
                coefficient = -float(projector[component, 3 * index + local])
                if coefficient != 0.0:
                    terms.append(ConstraintTerm(node, dof, coefficient))
        constraints.append(LinearConstraint(tuple(terms), name=f"{definition.name or 'rbe3'}:{name}"))
    return constraints


def _normalized_weights(values: list[float] | tuple[float, ...]) -> np.ndarray:
    """Normalize weights without making their common scale part of the contract."""
    try:
        weights = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise InputValidationError("RBE3 weights must be finite numbers.") from exc
    if not np.all(np.isfinite(weights)):
        raise InputValidationError("RBE3 weights must be finite numbers.")
    scale = float(np.max(np.abs(weights), initial=0.0))
    if scale == 0.0:
        raise InputValidationError("RBE3 weights must have a non-zero sum.")
    scaled = weights / scale
    total = float(np.sum(scaled))
    total_magnitude = float(np.sum(np.abs(scaled)))
    if not np.isfinite(total) or abs(total) <= 1.0e-14 * total_magnitude:
        raise InputValidationError("RBE3 weights must have a numerically non-zero sum.")
    normalized = scaled / total
    if not np.all(np.isfinite(normalized)):
        raise InputValidationError("RBE3 normalized weights must be finite.")
    return normalized


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
    return tuple(term for index, term in enumerate(terms) if index == 0 or term.coefficient != 0.0)


def _node(node: int, nodes: np.ndarray, label: str) -> None:
    if not isinstance(node, int) or not 0 <= node < len(nodes):
        raise InputValidationError(f"{label} must reference an existing node.")


def _name(name: str, slave: int, component: int) -> str:
    return f"{name or 'rbe2'}:slave_{slave}:{TRANSLATION_DOFS[component]}"
