"""Deterministic quadrature and sampling rules on the reference tetrahedron."""

from __future__ import annotations

from functools import lru_cache

import numpy as np


@lru_cache(maxsize=None)
def tetra_duffy_rule(order: int = 5) -> tuple[tuple[tuple[float, float, float, float], float], ...]:
    """Return a tensor Gauss rule mapped from the unit cube to a tetrahedron."""
    if order < 1:
        raise ValueError("Tetrahedron quadrature order must be positive.")
    abscissas, weights = np.polynomial.legendre.leggauss(order)
    unit_points = 0.5 * (abscissas + 1.0)
    unit_weights = 0.5 * weights
    rule: list[tuple[tuple[float, float, float, float], float]] = []
    for a, wa in zip(unit_points, unit_weights):
        for b, wb in zip(unit_points, unit_weights):
            for c, wc in zip(unit_points, unit_weights):
                r = float(a)
                s = float((1.0 - a) * b)
                t = float((1.0 - a) * (1.0 - b) * c)
                barycentric = (1.0 - r - s - t, r, s, t)
                jacobian = (1.0 - a) ** 2 * (1.0 - b)
                rule.append((barycentric, float(wa * wb * wc * jacobian)))
    return tuple(rule)


@lru_cache(maxsize=None)
def tetra_lattice_points(order: int = 4) -> tuple[tuple[float, float, float, float], ...]:
    """Return a closed barycentric lattice for deterministic Jacobian checks."""
    if order < 1:
        raise ValueError("Tetrahedron lattice order must be positive.")
    points: list[tuple[float, float, float, float]] = []
    for i in range(order + 1):
        for j in range(order + 1 - i):
            for k in range(order + 1 - i - j):
                ell = order - i - j - k
                points.append((i / order, j / order, k / order, ell / order))
    return tuple(points)


@lru_cache(maxsize=None)
def triangle_duffy_rule(order: int = 5) -> tuple[tuple[tuple[float, float, float], float], ...]:
    """Return a positive tensor Gauss rule mapped to the reference triangle."""
    if order < 1:
        raise ValueError("Triangle quadrature order must be positive.")
    abscissas, weights = np.polynomial.legendre.leggauss(order)
    unit_points = 0.5 * (abscissas + 1.0)
    unit_weights = 0.5 * weights
    rule: list[tuple[tuple[float, float, float], float]] = []
    for a, weight_a in zip(unit_points, unit_weights):
        for b, weight_b in zip(unit_points, unit_weights):
            u = float(a)
            v = float((1.0 - a) * b)
            rule.append(((1.0 - u - v, u, v), float(weight_a * weight_b * (1.0 - a))))
    return tuple(rule)


def triangle_shape_functions(
    node_count: int,
    barycentric: tuple[float, float, float],
) -> tuple[np.ndarray, np.ndarray]:
    """Return T3 or T6 shape functions and derivatives on a reference face."""
    l1, l2, l3 = barycentric
    gradients = np.array([[-1.0, -1.0], [1.0, 0.0], [0.0, 1.0]])
    if node_count == 3:
        return np.asarray(barycentric), gradients
    if node_count != 6:
        raise ValueError("Triangle interpolation expects three or six nodes.")
    shape = np.array(
        [
            l1 * (2.0 * l1 - 1.0),
            l2 * (2.0 * l2 - 1.0),
            l3 * (2.0 * l3 - 1.0),
            4.0 * l1 * l2,
            4.0 * l2 * l3,
            4.0 * l3 * l1,
        ]
    )
    derivatives = np.array(
        [
            (4.0 * l1 - 1.0) * gradients[0],
            (4.0 * l2 - 1.0) * gradients[1],
            (4.0 * l3 - 1.0) * gradients[2],
            4.0 * (l1 * gradients[1] + l2 * gradients[0]),
            4.0 * (l2 * gradients[2] + l3 * gradients[1]),
            4.0 * (l3 * gradients[0] + l1 * gradients[2]),
        ]
    )
    return shape, derivatives
