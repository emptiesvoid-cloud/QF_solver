"""Independent analytical checks for the controlled 0.2.6 G06 corpus.

The reference in this module is deliberately limited to a constrained
single-free-degree-of-freedom solid element.  Its stiffness is obtained from
independent shape-function derivatives and Gauss integration, rather than
from the production element classes.
"""

from __future__ import annotations

from typing import Any

import numpy as np


_DOF_INDEX = {"UX": 0, "UY": 1, "UZ": 2}
_TET10_POINTS = (
    (0.5854101966249685, 0.1381966011250105, 0.1381966011250105, 0.1381966011250105),
    (0.1381966011250105, 0.5854101966249685, 0.1381966011250105, 0.1381966011250105),
    (0.1381966011250105, 0.1381966011250105, 0.5854101966249685, 0.1381966011250105),
    (0.1381966011250105, 0.1381966011250105, 0.1381966011250105, 0.5854101966249685),
)
_TET10_WEIGHT = 1.0 / 24.0
_GAUSS_ABSCISSA = float(np.sqrt(3.0 / 5.0))
_GAUSS_1D = ((_GAUSS_ABSCISSA, 5.0 / 9.0), (0.0, 8.0 / 9.0), (-_GAUSS_ABSCISSA, 5.0 / 9.0))
_HEX8_SIGNS = np.asarray(
    (
        (-1.0, -1.0, -1.0),
        (1.0, -1.0, -1.0),
        (1.0, 1.0, -1.0),
        (-1.0, 1.0, -1.0),
        (-1.0, -1.0, 1.0),
        (1.0, -1.0, 1.0),
        (1.0, 1.0, 1.0),
        (-1.0, 1.0, 1.0),
    ),
    dtype=float,
)
_HEX20_EDGE_DATA = (
    (0, (1, 2), (-1.0, -1.0)),
    (1, (0, 2), (-1.0, -1.0)),
    (2, (0, 1), (-1.0, -1.0)),
    (1, (0, 2), (1.0, -1.0)),
    (2, (0, 1), (1.0, -1.0)),
    (0, (1, 2), (1.0, -1.0)),
    (2, (0, 1), (1.0, 1.0)),
    (2, (0, 1), (-1.0, 1.0)),
    (0, (1, 2), (-1.0, 1.0)),
    (1, (0, 2), (-1.0, 1.0)),
    (1, (0, 2), (1.0, 1.0)),
    (0, (1, 2), (1.0, 1.0)),
)


def evaluate_free_dof_oracle(
    model: dict[str, Any], result: dict[str, Any], configuration: dict[str, Any]
) -> dict[str, Any]:
    """Compare one solved free displacement with an independent closed form."""

    if configuration.get("type") != "constrained_free_dof":
        raise ValueError("Unsupported G06 analytical oracle type.")
    family = str(configuration.get("element_family", "")).upper()
    node = int(configuration.get("free_node", 1))
    dof = str(configuration.get("free_dof", "UX")).upper()
    force = _load_value(model, node, dof)
    stiffness = _free_dof_stiffness(model, family, node, dof)
    expected = force / stiffness
    actual = _displacement_value(result, node, dof)
    relative_error = abs(actual - expected) / max(abs(expected), np.finfo(float).tiny)
    tolerance = float(configuration.get("relative_tolerance", 1.0e-10))
    return {
        "oracle": "constrained_free_dof",
        "element_family": family,
        "free_node": node,
        "free_dof": dof,
        "force": float(force),
        "effective_stiffness": float(stiffness),
        "reference_displacement": float(expected),
        "actual_displacement": float(actual),
        "relative_error": float(relative_error),
        "relative_tolerance": tolerance,
        "status": "PASS" if relative_error <= tolerance else "FAIL",
    }


def _load_value(model: dict[str, Any], node: int, dof: str) -> float:
    values = [
        float(item["value"])
        for item in model.get("loads", [])
        if int(item.get("node", -1)) == node and str(item.get("dof", "")).upper() == dof
    ]
    if len(values) != 1 or values[0] == 0.0:
        raise ValueError("The analytical oracle requires one non-zero free-DOF load.")
    return values[0]


def _displacement_value(result: dict[str, Any], node: int, dof: str) -> float:
    for item in result.get("displacements", []):
        if int(item.get("node", -1)) == node:
            values = item.get("dofs", {})
            return float(values[dof])
    raise ValueError("The solver result does not contain the analytical free displacement.")


def _free_dof_stiffness(model: dict[str, Any], family: str, node: int, dof: str) -> float:
    elements = model.get("elements", [])
    if len(elements) != 1:
        raise ValueError("The constrained free-DOF oracle requires exactly one element.")
    element = elements[0]
    if str(element.get("type", "")).upper() != family:
        raise ValueError(f"Analytical family {family!r} does not match the model element.")
    nodes = np.asarray(model["nodes"], dtype=float)[np.asarray(element["nodes"], dtype=int)]
    material = model["materials"][element["material"]]
    young = float(material["E"])
    poisson = float(material["nu"])
    if not np.isfinite(young) or young <= 0.0 or not -1.0 < poisson < 0.5:
        raise ValueError("Analytical oracle requires a valid isotropic elastic material.")
    elasticity = _elasticity_matrix(young, poisson)
    local_node = int(node)
    if local_node < 0 or local_node >= len(nodes):
        raise ValueError("Analytical free node is outside the element.")
    axis = _DOF_INDEX[dof]
    total = 0.0
    for point, weight in _integration_rule(family):
        derivatives = _shape_derivatives(family, point)
        jacobian = derivatives.T @ nodes
        determinant = float(np.linalg.det(jacobian))
        if determinant <= 0.0:
            raise ValueError("Analytical oracle encountered a non-positive Jacobian.")
        gradients = derivatives @ np.linalg.inv(jacobian).T
        column = np.zeros(6, dtype=float)
        gx, gy, gz = gradients[local_node]
        if axis == 0:
            column[[0, 3, 5]] = gx, gy, gz
        elif axis == 1:
            column[[1, 3, 4]] = gy, gx, gz
        else:
            column[[2, 4, 5]] = gz, gy, gx
        total += float(weight) * determinant * float(column @ elasticity @ column)
    if not np.isfinite(total) or total <= 0.0:
        raise ValueError("Analytical effective stiffness is not positive and finite.")
    return total


def _elasticity_matrix(young: float, poisson: float) -> np.ndarray:
    shear = young / (2.0 * (1.0 + poisson))
    first = young * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
    diagonal = first + 2.0 * shear
    matrix = np.array(
        ((diagonal, first, first, 0.0, 0.0, 0.0),
         (first, diagonal, first, 0.0, 0.0, 0.0),
         (first, first, diagonal, 0.0, 0.0, 0.0),
         (0.0, 0.0, 0.0, shear, 0.0, 0.0),
         (0.0, 0.0, 0.0, 0.0, shear, 0.0),
         (0.0, 0.0, 0.0, 0.0, 0.0, shear)), dtype=float)
    return matrix


def _integration_rule(family: str) -> tuple[tuple[tuple[float, ...], float], ...]:
    if family == "TET4":
        return (((0.25, 0.25, 0.25, 0.25), 1.0 / 6.0),)
    if family == "TET10":
        return tuple((point, _TET10_WEIGHT) for point in _TET10_POINTS)
    return tuple(
        ((xi, eta, zeta), wx * wy * wz)
        for xi, wx in _GAUSS_1D
        for eta, wy in _GAUSS_1D
        for zeta, wz in _GAUSS_1D
    )


def _shape_derivatives(family: str, point: tuple[float, ...]) -> np.ndarray:
    if family == "TET4":
        return np.asarray(((-1.0, -1.0, -1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))
    if family == "TET10":
        l1, l2, l3, l4 = point
        barycentric_gradients = np.asarray(((-1.0, -1.0, -1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))
        return np.asarray(
            ((4.0 * l1 - 1.0) * barycentric_gradients[0],
             (4.0 * l2 - 1.0) * barycentric_gradients[1],
             (4.0 * l3 - 1.0) * barycentric_gradients[2],
             (4.0 * l4 - 1.0) * barycentric_gradients[3],
             4.0 * (l1 * barycentric_gradients[1] + l2 * barycentric_gradients[0]),
             4.0 * (l2 * barycentric_gradients[2] + l3 * barycentric_gradients[1]),
             4.0 * (l3 * barycentric_gradients[0] + l1 * barycentric_gradients[2]),
             4.0 * (l1 * barycentric_gradients[3] + l4 * barycentric_gradients[0]),
             4.0 * (l2 * barycentric_gradients[3] + l4 * barycentric_gradients[1]),
             4.0 * (l3 * barycentric_gradients[3] + l4 * barycentric_gradients[2])))
    values = np.asarray(point, dtype=float)
    if family == "HEX8":
        derivatives = np.zeros((8, 3), dtype=float)
        for index, signs in enumerate(_HEX8_SIGNS):
            factors = 1.0 + signs * values
            for axis in range(3):
                derivatives[index, axis] = 0.125 * signs[axis] * float(np.prod(np.delete(factors, axis)))
        return derivatives
    if family == "HEX20":
        return _hex20_shape_derivatives(values)
    raise ValueError(f"Unsupported analytical element family {family!r}.")


def _hex20_shape_derivatives(values: np.ndarray) -> np.ndarray:
    derivatives = np.zeros((20, 3), dtype=float)
    for index, signs in enumerate(_HEX8_SIGNS):
        factors = 1.0 + signs * values
        product = float(np.prod(factors))
        linear = float(signs @ values) - 2.0
        for axis in range(3):
            derivatives[index, axis] = 0.125 * signs[axis] * (float(np.prod(np.delete(factors, axis))) * linear + product)
    for index, (free_axis, fixed_axes, fixed_signs) in enumerate(_HEX20_EDGE_DATA, start=8):
        free_value = values[free_axis]
        fixed_factors = {axis: 1.0 + sign * values[axis] for axis, sign in zip(fixed_axes, fixed_signs)}
        derivatives[index, free_axis] = -0.5 * float(np.prod(tuple(fixed_factors.values()))) * free_value
        for axis, sign in zip(fixed_axes, fixed_signs):
            other = float(np.prod([fixed_factors[item] for item in fixed_axes if item != axis]))
            derivatives[index, axis] = 0.25 * sign * other * (1.0 - free_value**2)
    return derivatives
